"""Private FOI v1 inference kernel. It refuses to infer without attached private positions."""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import subprocess
import sys
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path("/kaggle/working") if Path("/kaggle/working").is_dir() else Path.cwd()
PIN_DSC = "git+https://github.com/ChessDS/chessds-dsc.git@v0.1.0"
PIN_MAIA = "git+https://github.com/CSSLab/maia3.git@1e13597c42d4858b7cfd7cfdae01e297263364b2"
PIN_MAIA_WEIGHT_REVISION = "a107d6ceb7b298cb04ae1da4edffe2939858b894"


def write_json(name: str, payload: dict) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_positions() -> Path | None:
    requested = os.environ.get("FOI_POSITIONS_PATH")
    if requested and Path(requested).is_file():
        return Path(requested)
    root = Path("/kaggle/input")
    if not root.exists():
        return None
    mode_files = sorted(root.glob("**/run_mode.json"))
    mode = json.loads(mode_files[0].read_text(encoding="utf-8")).get("mode") if mode_files else ""
    mode_to_file = {"smoke100": "positions_smoke100.jsonl", "validation": "positions_validation.jsonl", "test": "positions_test.jsonl"}
    preferred = mode_to_file.get(mode)
    if preferred:
        matches = sorted(root.glob(f"**/{preferred}"))
    else:
        matches = sorted(root.glob("**/positions.jsonl"))
    if len(matches) > 1:
        raise RuntimeError(f"Expected one private positions file for mode {mode or 'default'}, found {len(matches)}")
    return matches[0] if matches else None


def install_model_dependencies() -> None:
    for package in ("python-chess>=1.999", "safetensors", "huggingface_hub", PIN_DSC, PIN_MAIA):
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", package])


def package_version(name: str) -> str | None:
    import importlib.metadata
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def package_source(name: str) -> dict | None:
    import importlib.metadata
    try:
        raw = importlib.metadata.distribution(name).read_text("direct_url.json")
        return json.loads(raw) if raw else None
    except importlib.metadata.PackageNotFoundError:
        return None


def artifact_record(path: Path | None, requested_revision: str) -> dict:
    if path is None or not path.is_file():
        return {"requested_revision": requested_revision, "sha256": None}
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return {"requested_revision": requested_revision, "file_name": path.name, "sha256": digest.hexdigest()}


def policy_maia(engine, board, white_elo: int, black_elo: int, torch, maia_uci) -> dict[str, float]:
    """Read official model move logits and apply Maia's official legal mask before softmax."""
    engine.self_elo = white_elo if board.turn else black_elo
    engine.oppo_elo = black_elo if board.turn else white_elo
    tokens = engine._tokens_from_history(engine.history).unsqueeze(0).to(engine.cfg.device)
    self_elos = torch.tensor([engine.self_elo], dtype=torch.long, device=engine.cfg.device)
    oppo_elos = torch.tensor([engine.oppo_elo], dtype=torch.long, device=engine.cfg.device)
    legal_mask = maia_uci.get_legal_moves_mask(board, engine.all_moves_dict)
    if not bool(legal_mask.any()):
        raise ValueError("Maia legal move mask is empty")
    with torch.no_grad():
        with torch.autocast("cuda", enabled=bool(engine.cfg.use_amp and str(engine.cfg.device).startswith("cuda"))):
            logits_move, _value_logits, _ponder = engine.model(tokens, self_elos, oppo_elos)
        logits = logits_move[0].float().masked_fill(~legal_mask.to(engine.cfg.device), float("-inf"))
        probabilities = torch.softmax(logits, dim=-1).cpu()
    result = {}
    for index in torch.nonzero(legal_mask, as_tuple=False).flatten().tolist():
        move = engine._move_from_index(index)
        if move is None:
            raise ValueError(f"Maia produced unmappable legal policy index {index}")
        result[move.uci()] = float(probabilities[index])
    if set(result) != {move.uci() for move in board.legal_moves}:
        raise ValueError("Maia policy does not cover every legal move")
    return result


def rank(policy: dict[str, float]) -> list[str]:
    return sorted(policy, key=lambda move: (-policy[move], move))


def predict_positions(input_path: Path) -> tuple[list[dict], dict]:
    import chess
    import torch
    from chessds_dsc import DSC
    from maia3 import uci as maia_uci
    from maia3.uci import Maia3UCIEngine, parse_args

    load_started = time.monotonic()
    rows = [json.loads(line) for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError("Attached positions.jsonl is empty")
    sample_ids = [row["sample_id"] for row in rows]
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("Duplicate sample_id in positions input")
    if not torch.cuda.is_available():
        raise RuntimeError("Kaggle GPU is unavailable")
    device = "cuda"
    dsc = DSC.load("dsc-150m", device=device)
    config = parse_args(["--model", "maia3-79m", "--device", device, "--use-uci-history", "--temperature", "0", "--multipv", "5"])
    config.revision = PIN_MAIA_WEIGHT_REVISION
    maia = Maia3UCIEngine(config)
    maia.ensure_model_loaded()
    outputs = []
    model_load_seconds = time.monotonic() - load_started
    inference_started = time.monotonic()
    timings = {"dsc": [], "maia3": []}
    memory = {"dsc": {"peak_allocated_bytes": 0, "peak_reserved_bytes": 0}, "maia3": {"peak_allocated_bytes": 0, "peak_reserved_bytes": 0}}
    for row in rows:
        board = chess.Board()
        for uci_move in row["prior_moves_uci"]:
            move = chess.Move.from_uci(uci_move)
            if move not in board.legal_moves:
                raise ValueError(f"Illegal history for sample {row['sample_id']}")
            board.push(move)
        if board.fen() != row["fen_before"]:
            raise ValueError(f"FEN/history mismatch for sample {row['sample_id']}")
        legal = {move.uci() for move in board.legal_moves}
        if legal != set(row["legal_moves_uci"]):
            raise ValueError(f"Legal move list mismatch for sample {row['sample_id']}")
        white_elo = int(row["white_elo_at_game"])
        black_elo = int(row["black_elo_at_game"])
        torch.cuda.reset_peak_memory_stats()
        model_started = time.perf_counter()
        prediction = dsc.predict(board, white_elo=white_elo, black_elo=black_elo, rating_system="fide", time_control="classical", venue="otb")
        torch.cuda.synchronize()
        dsc_elapsed = time.perf_counter() - model_started
        timings["dsc"].append(dsc_elapsed)
        memory["dsc"]["peak_allocated_bytes"] = max(memory["dsc"]["peak_allocated_bytes"], torch.cuda.max_memory_allocated())
        memory["dsc"]["peak_reserved_bytes"] = max(memory["dsc"]["peak_reserved_bytes"], torch.cuda.max_memory_reserved())
        dsc_policy = {str(move): float(probability) for move, probability in prediction.moves.items()}
        if set(dsc_policy) != legal:
            raise ValueError(f"DSC policy does not cover every legal move for {row['sample_id']}")
        if abs(sum(dsc_policy.values()) - 1.0) > 1e-5:
            raise ValueError(f"DSC probabilities are not normalized for {row['sample_id']}")

        history = " ".join(row["prior_moves_uci"])
        maia.cmd_position("position startpos" + (" moves " + history if history else ""))
        torch.cuda.reset_peak_memory_stats()
        model_started = time.perf_counter()
        maia_policy = policy_maia(maia, board, white_elo, black_elo, torch, maia_uci)
        torch.cuda.synchronize()
        maia_elapsed = time.perf_counter() - model_started
        timings["maia3"].append(maia_elapsed)
        memory["maia3"]["peak_allocated_bytes"] = max(memory["maia3"]["peak_allocated_bytes"], torch.cuda.max_memory_allocated())
        memory["maia3"]["peak_reserved_bytes"] = max(memory["maia3"]["peak_reserved_bytes"], torch.cuda.max_memory_reserved())
        if abs(sum(maia_policy.values()) - 1.0) > 1e-5:
            raise ValueError(f"Maia probabilities are not normalized for {row['sample_id']}")
        models = {
            "dsc-150m": {"probabilities": dsc_policy, "ranking": rank(dsc_policy), "coverage": "full legal-move policy", "inference_seconds": dsc_elapsed},
            "maia3-79m": {"probabilities": maia_policy, "ranking": rank(maia_policy), "coverage": "full legal-move policy via pinned official Python logits", "inference_seconds": maia_elapsed},
        }
        outputs.append({**row, "models": models})
    dsc_weight_files = sorted(Path.home().glob(".cache/huggingface/hub/models--ChessDS--DSC-150M/snapshots/*/dsc-150m-v1.safetensors"))
    metadata = {
        "status": "predictions_completed",
        "created_at_unix": time.time(),
        "input_path": str(input_path),
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "positions": len(outputs),
        "games": len({row["game_id"] for row in outputs}),
        "gpu": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "packages": {"chessds-dsc": {"version": package_version("chessds-dsc"), "source": package_source("chessds-dsc")}, "maia3": {"version": package_version("maia3"), "source": package_source("maia3")}, "python-chess": package_version("python-chess")},
        "source_revisions": {"chessds-dsc": "v0.1.0", "maia3": "1e13597c42d4858b7cfd7cfdae01e297263364b2"},
        "model_artifacts": {
            "dsc": artifact_record(dsc_weight_files[-1] if dsc_weight_files else None, "ChessDS/DSC-150M:v1"),
            "maia": artifact_record(Path(maia.cfg.checkpoint_path) if maia.cfg.checkpoint_path else None, f"UofTCSSLab/Maia3-79M@{PIN_MAIA_WEIGHT_REVISION}"),
        },
        "history": "full prior UCI move history; identical positions and rating inputs for both models",
        "deterministic_ranking": "probability descending; UCI ascending for ties",
        "model_load_seconds": round(model_load_seconds, 3),
        "inference_seconds": round(time.monotonic() - inference_started, 3),
        "latency_seconds_per_position": {name: {"mean": sum(values)/len(values), "p50": sorted(values)[len(values)//2], "p95": sorted(values)[min(len(values)-1, int(.95*len(values)))], "max": max(values)} for name, values in timings.items() if values},
        "gpu_memory": memory,
        "maia_policy_adapter": "Maia3UCIEngine model logits + official legal-move mask + softmax; relies on pinned private Python internals",
        "personalization": "disabled",
    }
    return outputs, metadata


def synthetic_policy_self_test() -> dict:
    """Exercise both full-policy adapters using the already-used synthetic smoke position."""
    import chess
    import torch
    from chessds_dsc import DSC
    from maia3 import uci as maia_uci
    from maia3.uci import Maia3UCIEngine, parse_args

    if not torch.cuda.is_available():
        raise RuntimeError("Kaggle GPU is unavailable for policy adapter self-test")
    prior_moves = ["e2e4", "c7c5", "g1f3", "d7d6", "d2d4", "c5d4", "f3d4", "g8f6", "b1c3", "a7a6", "c1e3", "e7e5", "d4b3", "c8e6"]
    board = chess.Board()
    for uci_move in prior_moves:
        move = chess.Move.from_uci(uci_move)
        if move not in board.legal_moves:
            raise ValueError(f"Invalid synthetic smoke history: {uci_move}")
        board.push(move)
    # These Elo inputs belong only to this established synthetic smoke fixture.
    white_elo, black_elo = 2700, 2650
    dsc = DSC.load("dsc-150m", device="cuda")
    dsc_prediction = dsc.predict(board, white_elo=white_elo, black_elo=black_elo, rating_system="fide", time_control="classical", venue="otb")
    dsc_policy = {str(move): float(probability) for move, probability in dsc_prediction.moves.items()}
    legal = {move.uci() for move in board.legal_moves}
    if set(dsc_policy) != legal or abs(sum(dsc_policy.values()) - 1.0) > 1e-5:
        raise ValueError("DSC synthetic self-test returned an invalid full legal-move policy")

    config = parse_args(["--model", "maia3-79m", "--device", "cuda", "--use-uci-history", "--temperature", "0", "--multipv", "5"])
    config.revision = PIN_MAIA_WEIGHT_REVISION
    maia = Maia3UCIEngine(config)
    maia.ensure_model_loaded()
    maia.cmd_position("position startpos moves " + " ".join(prior_moves))
    maia_policy = policy_maia(maia, board, white_elo, black_elo, torch, maia_uci)
    if set(maia_policy) != legal or abs(sum(maia_policy.values()) - 1.0) > 1e-5:
        raise ValueError("Maia synthetic self-test returned an invalid full legal-move policy")

    def top_five(policy: dict[str, float]) -> list[dict]:
        return [{"move_uci": move, "probability": policy[move]} for move in rank(policy)[:5]]

    return {
        "status": "passed",
        "sample_is_synthetic": True,
        "real_games_used": 0,
        "position_fen": board.fen(),
        "past_moves_uci": prior_moves,
        "synthetic_rating_inputs": {"white_elo": white_elo, "black_elo": black_elo},
        "gpu": torch.cuda.get_device_name(0),
        "dsc": {"model": "dsc-150m", "legal_moves": len(legal), "probability_sum": sum(dsc_policy.values()), "coverage": "full legal move set", "top5": top_five(dsc_policy)},
        "maia3": {"model": "maia3-79m", "legal_moves": len(legal), "probability_sum": sum(maia_policy.values()), "coverage": "full legal move set", "top5": top_five(maia_policy), "adapter": "pinned official Python model move logits + legal mask + softmax"},
        "purpose": "model adapter fixture only; not a player benchmark",
    }


def _metrics(rows: list[dict], model: str) -> dict:
    if not rows:
        return {"positions": 0, "games": 0, "top1": None, "top3": None, "top5": None, "nll": None}
    hits = {k: 0 for k in (1, 3, 5)}
    nll = 0.0
    for row in rows:
        policy = row["models"][model]["probabilities"]
        if set(policy) != set(row["legal_moves_uci"]):
            raise ValueError(f"Truncated {model} policy at {row['sample_id']}")
        ranking = sorted(policy, key=lambda move: (-float(policy[move]), move))
        actual = row["actual_move_uci"]
        for k in hits:
            hits[k] += int(actual in ranking[:k])
        nll += -math.log(max(float(policy[actual]), 1e-15))
    n = len(rows)
    return {"positions": n, "games": len({row["game_id"] for row in rows}), "top1": hits[1]/n, "top3": hits[3]/n, "top5": hits[5]/n, "nll": nll/n}


def evaluate(rows: list[dict], draws: int = 2000, seed: int = 20261118) -> dict:
    groups = {field: defaultdict(list) for field in ("target_fide_id", "phase", "target_color", "opening_key", "split")}
    for row in rows:
        for field, buckets in groups.items():
            buckets[str(row.get(field, "unknown"))].append(row)
    model_results = {}
    for model in ("dsc-150m", "maia3-79m"):
        per_game = defaultdict(list)
        for row in rows:
            per_game[row["game_id"]].append(row)
        ids = sorted(per_game)
        rng = random.Random(seed)
        draws_metrics = {name: [] for name in ("top1", "top3", "top5", "nll")}
        if len(ids) > 1:
            for _ in range(draws):
                sampled = [rng.choice(ids) for _ in ids]
                sample_rows = [row for game in sampled for row in per_game[game]]
                values = _metrics(sample_rows, model)
                for name in draws_metrics:
                    draws_metrics[name].append(values[name])
        ci = {name: ([sorted(vals)[int(.025*(draws-1))], sorted(vals)[int(.975*(draws-1))]] if vals else None) for name, vals in draws_metrics.items()}
        model_results[model] = {**_metrics(rows, model), "game_bootstrap_95_ci": ci, "by": {field: {key: _metrics(bucket, model) for key, bucket in sorted(buckets.items())} for field, buckets in groups.items()}}
    return {"status": "evaluated", "positions": len(rows), "games": len({row["game_id"] for row in rows}), "bootstrap": {"unit": "whole game", "draws": draws, "seed": seed}, "models": model_results}


def markdown(metrics: dict, metadata: dict, validation: dict | None = None) -> str:
    lines = ["# FOI v1 FIDE Classical Benchmark", "", "## Run", "", f"- Positions: {metrics['positions']}", f"- Complete games: {metrics['games']}", f"- GPU: {metadata['gpu']}", f"- Model loading: {metadata['model_load_seconds']} seconds", f"- Inference: {metadata['inference_seconds']} seconds", f"- Total run: {metadata.get('elapsed_seconds_including_evaluation', metadata['inference_seconds'])} seconds", f"- Resampling: {metrics['bootstrap']['draws']} whole-game draws; seed {metrics['bootstrap']['seed']}", "- Model personalization: disabled", "- Historical test games are not assumed to be absent from pretraining.", "", "## Results", "", "| Model | Positions | Games | Top-1 | Top-1 95% game CI | Top-3 | Top-5 | NLL | NLL 95% game CI |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for model, result in metrics["models"].items():
        ci = result["game_bootstrap_95_ci"]
        top1_ci = "n/a" if ci["top1"] is None else f"{ci['top1'][0]:.4f}–{ci['top1'][1]:.4f}"
        nll_ci = "n/a" if ci["nll"] is None else f"{ci['nll'][0]:.4f}–{ci['nll'][1]:.4f}"
        lines.append(f"| {model} | {result['positions']} | {result['games']} | {result['top1']:.4f} | {top1_ci} | {result['top3']:.4f} | {result['top5']:.4f} | {result['nll']:.4f} | {nll_ci} |")
    lines += ["", "## By player, opening prefix, phase, color and split", "", "| Model | Group | Value | Positions | Games | Top-1 | Top-3 | Top-5 | NLL |", "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for model, result in metrics["models"].items():
        for field, buckets in result["by"].items():
            for key, grouped in buckets.items():
                lines.append(f"| {model} | {field} | {key} | {grouped['positions']} | {grouped['games']} | {grouped['top1']:.4f} | {grouped['top3']:.4f} | {grouped['top5']:.4f} | {grouped['nll']:.4f} |")
    lines += ["", "## Data exclusions", ""]
    if validation:
        lines += [f"- Raw games parsed: {validation.get('raw_games_independently_parsed', validation.get('parsed_games', 0))}", f"- Classical OTB games validated: {validation.get('validated_games', validation.get('eligible_games', 0))}", f"- Candidate games still unverified: {validation.get('candidate_games_still_unknown_time_control_or_venue', validation.get('quarantined_games', 0))}"]
        if validation.get("audit_classifications"):
            lines.append(f"- Preliminary audit categories: `{json.dumps(validation['audit_classifications'], ensure_ascii=False)}`")
        if validation.get("candidate_games_still_unknown_time_control_or_venue") is not None:
            lines.append(f"- Source exclusions/unknowns: one illegal/inconsistent raw game; {validation['candidate_games_still_unknown_time_control_or_venue']} candidate games remain unverified.")
    else:
        lines.append("No validation.json was attached; see the private dataset package for the source validation manifest.")
    lines += ["", "Both models received complete past move histories and the same contemporaneous ratings stored in the PGN headers. These ratings were not re-resolved against FIDE monthly archives. Ranking is deterministic; NLL uses full legal-move policies. Maia's policy adapter calls the pinned official Python model and masks illegal moves before softmax.", ""]
    return "\n".join(lines)


def main() -> None:
    start = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        input_path = find_positions()
        if input_path is None:
            install_model_dependencies()
            self_test = synthetic_policy_self_test()
            write_json("model_self_test.json", self_test)
            payload = {"status": "awaiting_private_positions", "positions": 0, "games": 0, "personalization": "disabled", "synthetic_policy_self_test": "passed", "message": "A synthetic adapter fixture passed. No player dataset or player benchmark was run. Attach the private validated positions.jsonl Dataset after verified target identities and PGNs are supplied."}
            write_json("benchmark_metadata.json", payload)
            (OUT / "benchmark_report.md").write_text("# FOI v1 FIDE Classical Benchmark\n\nStatus: awaiting a private validated positions dataset. The model policy adapters passed a synthetic fixture only; no player data, player predictions, or benchmark metrics were generated. See `model_self_test.json`.\n", encoding="utf-8")
            print("FOI_BENCHMARK_AWAITING_PRIVATE_POSITIONS", flush=True)
            return
        validation_path = input_path.parent / "validation.json"
        if not validation_path.is_file():
            validation_path = input_path.parent.parent / "validation.json"
        validation = json.loads(validation_path.read_text(encoding="utf-8")) if validation_path.is_file() else None
        install_model_dependencies()
        predictions, metadata = predict_positions(input_path)
        results = evaluate(predictions)
        metadata["status"] = "completed"
        metadata["dataset_validation"] = validation
        metadata["elapsed_seconds_including_evaluation"] = round(time.monotonic() - start, 3)
        with (OUT / "predictions.jsonl").open("w", encoding="utf-8") as handle:
            for row in predictions:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        write_json("benchmark_metadata.json", metadata)
        write_json("metrics.json", results)
        (OUT / "benchmark_report.md").write_text(markdown(results, metadata, validation), encoding="utf-8")
        print("FOI_BENCHMARK_SUCCESS", flush=True)
    except Exception as exc:
        write_json("benchmark_error.json", {"status": "error", "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc(limit=30)})
        raise


if __name__ == "__main__":
    main()
