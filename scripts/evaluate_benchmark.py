#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from foi_pipeline.evaluation import evaluate, load_jsonl, report_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate identical full-policy model predictions by whole game")
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--validation", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/benchmark"))
    parser.add_argument("--bootstrap-draws", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20261118)
    args = parser.parse_args()
    metrics = evaluate(load_jsonl(args.predictions), args.bootstrap_draws, args.seed)
    validation = json.loads(args.validation.read_text(encoding="utf-8")) if args.validation else None
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "benchmark_report.md").write_text(report_markdown(metrics, validation), encoding="utf-8")
    print(
        json.dumps(
            {"status": metrics["status"], "positions": metrics.get("positions", 0), "games": metrics.get("games", 0)},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
