# Publication manifest

## Published after review

- Original FOI pipeline, validation, evaluation and Kaggle orchestration source that does not contain private player records or bundled third-party source.
- Empty/example configuration templates and schemas.
- Existing synthetic tests, plus publication-safety checks and CI configuration.
- Architecture, dataset/evaluation protocol, installation, Kaggle/model and license documentation.
- A short public verification summary of prior synthetic-only Kaggle GPU smoke runs.

## Withheld from the public tree

- All local `data/raw/**` and `data/processed/**`, including the supplied real-player PGN, candidate/validation/train/test PGNs, processed game manifests, event verification records, and all derived games/positions/labels.
- All player-specific reports and benchmark outputs under `reports/` and private Kaggle output directories. This includes per-position predictions, individual behavior analysis, reports, metrics, logs and run metadata.
- Kaggle private dataset payloads and account-specific kernel metadata; only a generic example metadata file is published.
- Target-specific config, local ratings, source manifests, review ledgers, credentials, caches, bytecode and local software binaries.
- Scripts dedicated to one supplied player's private corpus and behavioral analysis. Generic validator/evaluator code is published.

## Third-party / license review

No upstream model source, weights, or Stockfish binary is copied into the repository. Optional packages are fetched from their upstreams at runtime. Upstream license identifiers and notices are recorded in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). No blanket license was added for FOI original code.

## Unknown or not cleared

No local real-player dataset or position-level result has been cleared for redistribution; all are withheld. The exact redistribution terms for the user's supplied PGN are unknown. Model-weight-specific terms should be checked for the exact upstream revision before any weight redistribution; this release contains no weights.