# FOI v1 benchmark runbook

This is a local/private workflow. Do not commit identity maps, source manifests populated with private paths, rating records, validation outputs, position rows, predictions, logs, or Kaggle input datasets. Check source terms before processing or redistributing games.

## 1. Prepare verified inputs

Copy the templates to private working files: `configs/players.example.yaml`, `configs/ratings.example.csv`, `configs/source_manifest.example.csv`, and `configs/game_reviews.example.csv`. Resolve each target and opponent through FIDE IDs and documented identity sources. Use official monthly FIDE standard ratings for the game date. Record each game's classical-time-control and OTB evidence; FIDE-rated status or a PGN `TimeControl` header alone is insufficient. Unknown or unclear cases must be quarantined.

## 2. Validate locally

```bash
python scripts/validate_dataset.py \
  --players configs/players.yaml \
  --ratings configs/ratings.csv \
  --reviews configs/game_reviews.csv \
  --source-manifest configs/source_manifest.csv \
  --output-dir /private/path/foi-validated
```

For one or more user-supplied files, `--pgn path/to/file.pgn` is repeatable; provide `--source-url` and `--source-license`. Output includes game-level records, target-only position rows, quarantines, validation summary and provenance. Treat the entire output directory as private.

## 3. Split and leakage rules

Deduplicate across sources before splitting. Keep complete games together and order games chronologically; use complete events as the split unit where appropriate. The protocol's nominal 70/15/15 proportions are a target, not a reason to break game/event boundaries. Do not expose future moves, results, annotations, final opening labels or future ratings as features. Historical test games are retrospective and may occur in model pretraining corpora. A strict post-release set must be collected only after the protocol and model configuration are frozen.

## 4. Run on Kaggle

Keep the kernel and input dataset private. Attach only the validated private positions and matching validation manifest. The optional benchmark kernel verifies history/FEN/legal-move consistency before it loads models. It installs pinned upstream package revisions and downloads weights at run time. Never put Kaggle authentication material in the repository or notebook.

For synthetic GPU smoke testing, follow [Models and Kaggle](MODELS_AND_KAGGLE.md). A successful smoke run verifies wrapper execution only; it does not produce a player benchmark.

## 5. Evaluate retrieved results privately

```bash
python scripts/evaluate_benchmark.py \
  /private/path/run/predictions.jsonl \
  --validation /private/path/run/validation.json \
  --output-dir /private/path/run/evaluation
```

The evaluator checks full legal-move policy coverage, ranks ties deterministically, reports Top-1/3/5 and NLL, and resamples complete games for confidence intervals. Maia UCI top-k output alone is not a full policy and cannot support full-policy NLL. Preserve package/model revisions, hashes, game/decision counts, provenance, filters, split, compute environment and logs in the private run archive.

## 6. Publication review

Only a separately reviewed aggregate may be copied to `reports/public/`. Include the population, filters, game and decision counts, model revisions, rating/history inputs, split, possible pretraining contamination, metric definitions, game-level uncertainty and execution evidence. Never publish player-level rows, per-position predictions, raw/derived PGNs, private URLs or logs. Current public release has no player-level benchmark result.
