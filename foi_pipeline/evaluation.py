from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _check_policy(row: dict[str, Any], model: str) -> dict[str, float]:
    policy = row["models"][model]["probabilities"]
    legal = set(row["legal_moves_uci"])
    if set(policy) != legal:
        raise ValueError(f"{model} policy coverage differs from legal moves for {row['sample_id']}")
    values = [float(value) for value in policy.values()]
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError(f"Invalid {model} probability for {row['sample_id']}")
    if abs(sum(values) - 1.0) > 1e-5:
        raise ValueError(f"{model} legal-move probabilities do not sum to one for {row['sample_id']}")
    if row["actual_move_uci"] not in legal:
        raise ValueError(f"Observed move is illegal for {row['sample_id']}")
    return {move: float(prob) for move, prob in policy.items()}


def _position_metrics(rows: list[dict[str, Any]], model: str) -> dict[str, Any]:
    if not rows:
        return {"positions": 0, "games": 0, "top1": None, "top3": None, "top5": None, "nll": None}
    top_hits = {1: [], 3: [], 5: []}
    nlls = []
    for row in rows:
        policy = _check_policy(row, model)
        ranking = sorted(policy, key=lambda move: (-policy[move], move))
        actual = row["actual_move_uci"]
        for k in top_hits:
            top_hits[k].append(float(actual in ranking[:k]))
        nlls.append(-math.log(max(policy[actual], 1e-15)))
    return {
        "positions": len(rows),
        "games": len({row["game_id"] for row in rows}),
        "top1": sum(top_hits[1]) / len(rows),
        "top3": sum(top_hits[3]) / len(rows),
        "top5": sum(top_hits[5]) / len(rows),
        "nll": sum(nlls) / len(rows),
    }


def _bootstrap_ci(rows: list[dict[str, Any]], model: str, draws: int, seed: int) -> dict[str, list[float] | None]:
    if not rows:
        return {metric: None for metric in ("top1", "top3", "top5", "nll")}
    by_game: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_game[row["game_id"]].append(row)
    game_ids = sorted(by_game)
    if len(game_ids) < 2:
        return {metric: None for metric in ("top1", "top3", "top5", "nll")}
    rng = random.Random(seed)
    samples: dict[str, list[float]] = {metric: [] for metric in ("top1", "top3", "top5", "nll")}
    for _ in range(draws):
        selected = [rng.choice(game_ids) for _ in game_ids]
        draw_rows = [row for game_id in selected for row in by_game[game_id]]
        metrics = _position_metrics(draw_rows, model)
        for metric in samples:
            samples[metric].append(float(metrics[metric]))
    return {
        metric: [sorted(values)[int(0.025 * (draws - 1))], sorted(values)[int(0.975 * (draws - 1))]]
        for metric, values in samples.items()
    }


def _groups(rows: list[dict[str, Any]]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    result: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for field in ("target_fide_id", "phase", "target_color", "opening_key", "split"):
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            groups[str(row.get(field, "unknown"))].append(row)
        result[field] = dict(groups)
    return result


def evaluate(
    predictions: Iterable[dict[str, Any]], bootstrap_draws: int = 2000, seed: int = 20261118
) -> dict[str, Any]:
    rows = list(predictions)
    if not rows:
        return {"status": "no_predictions", "positions": 0, "models": {}}
    ids = [row["sample_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate sample_id in predictions")
    model_names = sorted(rows[0]["models"])
    if len(model_names) < 2 or any(set(row["models"]) != set(model_names) for row in rows):
        raise ValueError("Every position must have predictions from the same models")
    outputs: dict[str, Any] = {}
    for model in model_names:
        policy_rows = _position_metrics(rows, model)
        grouped = {}
        for field, buckets in _groups(rows).items():
            grouped[field] = {key: _position_metrics(bucket, model) for key, bucket in sorted(buckets.items())}
        outputs[model] = {
            **policy_rows,
            "game_bootstrap_95_ci": _bootstrap_ci(rows, model, bootstrap_draws, seed),
            "by": grouped,
            "probability_scope": "full legal-move policy",
        }
    return {
        "status": "evaluated",
        "positions": len(rows),
        "games": len({row["game_id"] for row in rows}),
        "bootstrap": {"unit": "whole game", "draws": bootstrap_draws, "seed": seed},
        "ranking": "deterministic probability descending; UCI ascending for ties",
        "models": outputs,
    }


def report_markdown(metrics: dict[str, Any], validation: dict[str, Any] | None = None) -> str:
    lines = ["# FOI v1 FIDE Classical Benchmark", "", "## Status", ""]
    if metrics.get("status") != "evaluated":
        lines.extend(["No benchmark predictions are available yet.", ""])
        if validation:
            lines.append(f"Dataset validation status: `{validation.get('status', 'unknown')}`.")
            lines.append(f"Configured target players: {validation.get('targets_configured', 0)}.")
        lines.extend(
            [
                "",
                "Real-player ingestion and benchmark scoring remain pending a verified target-player list and private PGN/rating sources.",
                "",
            ]
        )
        return "\n".join(lines)
    lines += [
        f"- Positions: {metrics['positions']}",
        f"- Games: {metrics['games']}",
        f"- Uncertainty: {metrics['bootstrap']['draws']} resamples of whole games (seed {metrics['bootstrap']['seed']})",
        "- Rankings use probability descending with UCI ascending as the deterministic tie-break.",
        "- Test-set scores are retrospective unless game dates and model training cutoffs establish otherwise.",
        "- No personalization or fine-tuning is used.",
        "",
        "## Overall results",
        "",
        "| Model | Positions | Games | Top-1 | Top-1 95% game CI | Top-3 | Top-5 | NLL | NLL 95% game CI |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model, result in metrics["models"].items():
        ci = result["game_bootstrap_95_ci"]
        top1_ci = "n/a" if ci["top1"] is None else f"{ci['top1'][0]:.4f}–{ci['top1'][1]:.4f}"
        nll_ci = "n/a" if ci["nll"] is None else f"{ci['nll'][0]:.4f}–{ci['nll'][1]:.4f}"
        lines.append(
            f"| {model} | {result['positions']} | {result['games']} | {result['top1']:.4f} | {top1_ci} | {result['top3']:.4f} | {result['top5']:.4f} | {result['nll']:.4f} | {nll_ci} |"
        )
    lines += ["", "## Coverage by player, opening, phase, color and split", ""]
    lines += [
        "| Model | Group | Value | Positions | Games | Top-1 | Top-3 | Top-5 | NLL |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model, result in metrics["models"].items():
        for field, buckets in result["by"].items():
            for key, grouped_result in buckets.items():
                lines.append(
                    f"| {model} | {field} | {key} | {grouped_result['positions']} | {grouped_result['games']} | {grouped_result['top1']:.4f} | {grouped_result['top3']:.4f} | {grouped_result['top5']:.4f} | {grouped_result['nll']:.4f} |"
                )
    if validation:
        lines += [
            "",
            "## Data validation and exclusions",
            "",
            f"- Parsed games: {validation.get('parsed_games', 0)}",
            f"- Eligible games: {validation.get('eligible_games', 0)}",
            f"- Quarantined games: {validation.get('quarantined_games', 0)}",
            "- Exclusion counts:",
        ]
        lines += [f"  - `{key}`: {value}" for key, value in validation.get("exclusions", {}).items()] or ["  - None"]
    lines += [
        "",
        "## Model inputs and limitations",
        "",
        "Both frozen models receive the same position, complete prior UCI move history, and historical standard Elo values. DSC NLL and Maia NLL are calculated only from each model's complete legal-move policy. Historical test positions are not claimed to be unseen during pretraining.",
        "",
    ]
    return "\n".join(lines)
