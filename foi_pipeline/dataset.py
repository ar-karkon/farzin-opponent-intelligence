from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import chess
import chess.pgn
import yaml

POST_RELEASE_DATE = date(2026, 10, 24)


@dataclass(frozen=True)
class Source:
    path: Path
    kind: str
    url: str = ""
    license: str = ""
    issue: str = ""


def read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return data


def read_csv(path: Path | None) -> list[dict[str, str]]:
    if path is None:
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "verified"}


def _clean_name(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def build_identity_maps(config: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    by_id: dict[str, dict[str, Any]] = {}
    by_name: dict[str, str] = {}
    entries = list(config.get("identity_map", []))
    entries += [
        {
            "fide_id": player["fide_id"],
            "canonical_name": player.get("display_name", ""),
            "aliases": player.get("aliases", []),
            "verification_source": player.get("verification_source", ""),
        }
        for player in config.get("players", [])
        if player.get("fide_id")
    ]
    for item in entries:
        fide_id = str(item.get("fide_id", "")).strip()
        source = str(item.get("verification_source", "")).strip()
        if not fide_id or not source:
            continue
        by_id[fide_id] = item
        for name in [item.get("canonical_name", ""), *item.get("aliases", [])]:
            if name:
                key = _clean_name(str(name))
                if key in by_name and by_name[key] != fide_id:
                    raise ValueError(f"Ambiguous player alias in identity map: {name}")
                by_name[key] = fide_id
    return by_id, by_name


def _resolve_player(header_id: str, header_name: str, by_id: dict[str, Any], by_name: dict[str, str]) -> str | None:
    raw_id = str(header_id or "").strip()
    if raw_id and raw_id in by_id:
        return raw_id
    return by_name.get(_clean_name(str(header_name or "")))


def load_ratings(path: Path | None) -> dict[str, list[tuple[date, int, str]]]:
    ratings: dict[str, list[tuple[date, int, str]]] = {}
    for row in read_csv(path):
        fide_id = row.get("fide_id", "").strip()
        month = row.get("month", "").strip()
        try:
            rating = int(row.get("standard_elo", ""))
            month_date = date.fromisoformat(month + "-01")
        except (ValueError, TypeError):
            continue
        if fide_id and row.get("source_url", "").strip():
            ratings.setdefault(fide_id, []).append((month_date, rating, row["source_url"].strip()))
    for entries in ratings.values():
        entries.sort(key=lambda entry: entry[0])
    return ratings


def rating_at(
    ratings: dict[str, list[tuple[date, int, str]]], fide_id: str, game_date: date
) -> tuple[int | None, str | None]:
    eligible = [entry for entry in ratings.get(fide_id, []) if entry[0] <= game_date.replace(day=1)]
    if not eligible:
        return None, None
    _month, rating, source = eligible[-1]
    return rating, source


def read_pgn(path: Path):
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8-sig", errors="replace") as handle:
        index = 0
        while True:
            game = chess.pgn.read_game(handle)
            if game is None:
                break
            yield index, game
            index += 1


def _game_key(game_date: date, white_id: str, black_id: str, moves: list[str]) -> str:
    content = "|".join((game_date.isoformat(), white_id, black_id, " ".join(moves)))
    return hashlib.sha256(content.encode()).hexdigest()


def _review_index(rows: list[dict[str, str]]) -> dict[tuple[str, int], dict[str, str]]:
    result = {}
    for row in rows:
        try:
            key = (str(Path(row["source_file"]).resolve()), int(row["game_index"]))
        except (KeyError, ValueError):
            continue
        result[key] = row
    return result


def _validate_game(
    game, identity_by_id, identity_by_name, rating_table, targets: set[str], review: dict[str, str], source: Source
):
    reasons: list[str] = []
    headers = game.headers
    try:
        game_date = date.fromisoformat(str(headers.get("UTCDate", headers.get("Date", ""))).replace(".", "-"))
        if "????" in game_date.isoformat():
            raise ValueError
    except ValueError:
        game_date = None
        reasons.append("missing_or_invalid_date")

    white_id = _resolve_player(
        headers.get("WhiteFideId", headers.get("WhiteFIDEId", "")),
        headers.get("White", ""),
        identity_by_id,
        identity_by_name,
    )
    black_id = _resolve_player(
        headers.get("BlackFideId", headers.get("BlackFIDEId", "")),
        headers.get("Black", ""),
        identity_by_id,
        identity_by_name,
    )
    for side, resolved_id, name in (
        ("white", white_id, headers.get("White", "")),
        ("black", black_id, headers.get("Black", "")),
    ):
        declared_id = str(headers.get(f"{side.title()}FideId", headers.get(f"{side.title()}FIDEId", ""))).strip()
        name_id = identity_by_name.get(_clean_name(str(name or "")))
        if declared_id and name_id and declared_id != name_id:
            reasons.append(f"{side}_fide_id_name_mismatch")
    if not white_id or not black_id:
        reasons.append("unverified_player_identity")
    if white_id and black_id and not ({white_id, black_id} & targets):
        reasons.append("no_target_player")
    if game.errors:
        reasons.append("pgn_parse_error")
    variant = str(headers.get("Variant", "Standard")).strip().casefold()
    if variant not in {"standard", "chess"}:
        reasons.append("unsupported_chess_variant")
    if not headers.get("Result") or headers.get("Result") == "*":
        reasons.append("incomplete_game")

    tc_verified = _bool(review.get("time_control_classical_verified", "")) and bool(
        review.get("classification_source", "").strip()
    )
    venue_verified = _bool(review.get("venue_otb_verified", "")) and bool(review.get("venue_source", "").strip())
    if not tc_verified:
        reasons.append("classical_time_control_unverified")
    if not venue_verified:
        reasons.append("otb_venue_unverified")
    if not source.url:
        reasons.append("missing_source_url")
    if not source.license:
        reasons.append("missing_source_license")
    if not game_date or not white_id or not black_id:
        return None, reasons

    white_rating, white_rating_source = rating_at(rating_table, white_id, game_date)
    black_rating, black_rating_source = rating_at(rating_table, black_id, game_date)
    if white_rating is None or black_rating is None:
        reasons.append("missing_historical_standard_rating")
    elif white_rating < 2400 or black_rating < 2400:
        reasons.append("below_primary_rating_threshold")

    board = game.board()
    normalized_moves = []
    for move in game.mainline_moves():
        if move not in board.legal_moves:
            reasons.append("illegal_move")
            break
        normalized_moves.append(move.uci())
        board.push(move)
    if not normalized_moves:
        reasons.append("empty_game")

    digest = _game_key(game_date, white_id, black_id, normalized_moves)
    game_id = "game_" + digest[:20]
    record = {
        "game_id": game_id,
        "date": game_date.isoformat(),
        "event": headers.get("Event", ""),
        "event_id": review.get("event_id", ""),
        "round": headers.get("Round", ""),
        "white_name_raw": headers.get("White", ""),
        "black_name_raw": headers.get("Black", ""),
        "white_fide_id": white_id,
        "black_fide_id": black_id,
        "white_elo_at_game": white_rating,
        "black_elo_at_game": black_rating,
        "rating_sources": {"white": white_rating_source, "black": black_rating_source},
        "result": headers.get("Result", ""),
        "time_control": headers.get("TimeControl", ""),
        "time_control_header_missing": not bool(headers.get("TimeControl", "").strip()),
        "time_control_verified": tc_verified,
        "time_control_evidence": review.get("classification_source", ""),
        "venue_verified": venue_verified,
        "venue_evidence": review.get("venue_source", ""),
        "pgn": game.accept(chess.pgn.StringExporter(headers=True, variations=False, comments=False)),
        "source_url": source.url,
        "source_type": source.kind,
        "source_license": source.license,
        "source_issue": source.issue or review.get("source_issue", ""),
        "source_file": str(source.path),
        "checksum": digest,
        "quality_flags": [],
        "split": "quarantine",
        "_moves_uci": normalized_moves,
    }
    return record, reasons


def _assign_splits(records: list[dict[str, Any]]) -> None:
    pre_release = [record for record in records if date.fromisoformat(record["date"]) < POST_RELEASE_DATE]
    dates = sorted({record["date"] for record in pre_release})
    if dates:
        train_end = max(1, int(len(dates) * 0.70))
        validation_end = max(train_end + 1, int(len(dates) * 0.85))
        validation_end = min(validation_end, len(dates))
        train_dates = set(dates[:train_end])
        validation_dates = set(dates[train_end:validation_end])
        for record in pre_release:
            record["split"] = (
                "train"
                if record["date"] in train_dates
                else "validation"
                if record["date"] in validation_dates
                else "historical_test"
            )
    for record in records:
        if date.fromisoformat(record["date"]) >= POST_RELEASE_DATE:
            record["split"] = "post_release_test"


def _phase(board: chess.Board) -> str:
    weights = {chess.QUEEN: 4, chess.ROOK: 2, chess.BISHOP: 1, chess.KNIGHT: 1}
    phase = sum(
        len(board.pieces(piece_type, color)) * weight
        for piece_type, weight in weights.items()
        for color in (chess.WHITE, chess.BLACK)
    )
    if board.fullmove_number <= 10:
        return "opening"
    if phase <= 6 or (
        not board.pieces(chess.QUEEN, chess.WHITE) and not board.pieces(chess.QUEEN, chess.BLACK) and phase <= 10
    ):
        return "endgame"
    return "middlegame"


def extract_positions(record: dict[str, Any], target_ids: set[str]) -> list[dict[str, Any]]:
    board = chess.Board()
    prior_fens = [board.fen()]
    positions = []
    moves = record["_moves_uci"]
    for ply, uci in enumerate(moves):
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            raise ValueError(f"Illegal move {uci} in {record['game_id']} at ply {ply}")
        fide_id = record["white_fide_id"] if board.turn == chess.WHITE else record["black_fide_id"]
        if fide_id in target_ids:
            prior_moves = [past.uci() for past in board.move_stack]
            opening_prefix = " ".join(prior_moves[:8]) or "startpos"
            positions.append(
                {
                    "sample_id": f"{record['game_id']}_ply_{ply}",
                    "game_id": record["game_id"],
                    "date": record["date"],
                    "target_fide_id": fide_id,
                    "target_color": "white" if board.turn == chess.WHITE else "black",
                    "ply_index": ply,
                    "fen_before": board.fen(),
                    "prior_moves_uci": prior_moves,
                    "prior_positions_fen": prior_fens[:-1][-7:],
                    "legal_moves_uci": sorted(move.uci() for move in board.legal_moves),
                    "actual_move_uci": uci,
                    "white_elo_at_game": record["white_elo_at_game"],
                    "black_elo_at_game": record["black_elo_at_game"],
                    "phase": _phase(board),
                    "opening_key": opening_prefix,
                    "opening_familiarity": "unknown",
                    "split": record["split"],
                    "model_input_context_version": "foi-v1-past-only-history-v1",
                }
            )
        board.push(move)
        prior_fens.append(board.fen())
    return positions


def ingest(
    sources: Iterable[Source], players_config: dict[str, Any], ratings_path: Path | None, reviews_path: Path | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    identity_by_id, identity_by_name = build_identity_maps(players_config)
    targets = {str(player["fide_id"]) for player in players_config.get("players", []) if player.get("fide_id")}
    ratings = load_ratings(ratings_path)
    reviews = _review_index(read_csv(reviews_path))
    accepted: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    seen: dict[str, dict[str, Any]] = {}
    exclusion_counts: Counter[str] = Counter()
    parsed_count = 0
    for source in sources:
        for index, game in read_pgn(source.path):
            parsed_count += 1
            review = reviews.get((str(source.path.resolve()), index), {})
            record, reasons = _validate_game(game, identity_by_id, identity_by_name, ratings, targets, review, source)
            if record is None:
                quarantined.append({"source_file": str(source.path), "game_index": index, "reasons": reasons})
            else:
                record["quality_flags"] = reasons.copy()
                for reason in reasons:
                    exclusion_counts[reason] += 1
                if reasons:
                    quarantined.append({**record, "reasons": reasons})
                else:
                    prior = seen.get(record["checksum"])
                    if prior:
                        prior.setdefault("duplicate_sources", []).append(
                            {"url": record["source_url"], "file": record["source_file"]}
                        )
                        exclusion_counts["duplicate_game"] += 1
                    else:
                        seen[record["checksum"]] = record
                        accepted.append(record)
    _assign_splits(accepted)
    positions = [position for record in accepted for position in extract_positions(record, targets)]
    all_game_ids = {record["game_id"] for record in accepted}
    assert all(position["game_id"] in all_game_ids for position in positions)
    splits_by_game: dict[str, set[str]] = {}
    for position in positions:
        splits_by_game.setdefault(position["game_id"], set()).add(position["split"])
    if any(len(splits) != 1 for splits in splits_by_game.values()):
        raise AssertionError("Game split leakage detected")
    summary = {
        "status": "validated" if accepted else "no_eligible_games",
        "parsed_games": parsed_count,
        "eligible_games": len(accepted),
        "quarantined_games": len(quarantined),
        "target_positions": len(positions),
        "targets_configured": len(targets),
        "exclusions": dict(sorted(exclusion_counts.items())),
        "game_splits": dict(Counter(record["split"] for record in accepted)),
        "position_splits": dict(Counter(position["split"] for position in positions)),
        "real_player_data_ingested": bool(accepted and targets),
    }
    for record in accepted:
        record.pop("_moves_uci", None)
    return accepted, quarantined, {"summary": summary, "positions": positions, "quarantine": quarantined}


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
