#!/usr/bin/env python3
"""Validate a private FOI PGN corpus and build past-only position rows."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from foi_pipeline.dataset import Source, ingest, read_yaml, write_jsonl


def source_manifest(path: Path) -> list[Source]:
    sources = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            pgn_path = Path(row["pgn_path"])
            if not pgn_path.is_absolute():
                pgn_path = (path.parent / pgn_path).resolve()
            sources.append(
                Source(
                    pgn_path,
                    row.get("source_type", "manual").strip().lower(),
                    row.get("source_url", "").strip(),
                    row.get("source_license", "").strip(),
                    row.get("source_issue", "").strip(),
                )
            )
    return sources


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--players", type=Path, default=Path("configs/players.yaml"))
    parser.add_argument("--ratings", type=Path, help="Curated historical FIDE standard-rating CSV")
    parser.add_argument("--reviews", type=Path, help="Per-game classical/OTB verification CSV")
    parser.add_argument("--source-manifest", type=Path, help="CSV listing TWIC and manual PGN files with provenance")
    parser.add_argument("--pgn", action="append", type=Path, default=[], help="Manual PGN/PGN.GZ; repeatable")
    parser.add_argument("--source-kind", choices=("manual", "twic"), default="manual")
    parser.add_argument("--source-url", default="", help="Source page or download URL for --pgn files")
    parser.add_argument("--source-license", default="", help="License/terms reference for --pgn files")
    parser.add_argument("--output-dir", type=Path, default=Path("data/validated"))
    args = parser.parse_args()

    sources = source_manifest(args.source_manifest) if args.source_manifest else []
    sources.extend(Source(path, args.source_kind, args.source_url, args.source_license) for path in args.pgn)
    if not sources:
        parser.error("provide --source-manifest or one or more --pgn paths")
    for source in sources:
        if not source.path.is_file():
            parser.error(f"PGN file does not exist: {source.path}")
    if not args.players.is_file():
        parser.error(f"player configuration not found: {args.players}")

    games, _quarantine, artifacts = ingest(
        sources,
        read_yaml(args.players),
        args.ratings,
        args.reviews,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "games.jsonl", games)
    write_jsonl(args.output_dir / "positions.jsonl", artifacts["positions"])
    write_jsonl(args.output_dir / "quarantine.jsonl", artifacts["quarantine"])
    (args.output_dir / "validation.json").write_text(
        json.dumps(artifacts["summary"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(artifacts["summary"], indent=2, ensure_ascii=False))
    return 0 if artifacts["summary"]["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
