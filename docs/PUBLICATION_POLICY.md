# Public Release Policy

This repository contains the **public, reproducible** parts of Farzin Opponent Intelligence, not every local working file.

## May be published after verification

- Original FOI source code, tests, CLI commands, configuration **templates**, and non-secret dependency lockfiles.
- Synthetic PGN examples and other generated fixtures that do not expose restricted real-game data.
- Audited aggregate benchmarks with model versions, data provenance, sample counts, limitations, and reproducible evaluation methods.
- Sanitized documentation, architecture diagrams, and screenshots containing no private tokens.

## Private by default

- Raw real-player PGNs and derived game-level/position-level records without verified redistribution rights.
- Kaggle credentials and private kernel URLs containing access tokens, API keys, `.env` files, logs with sensitive values.
- Large model checkpoints/weights unless redistribution is expressly permitted and appropriate provenance is preserved.
- Personalized analysis intended only for internal opponent preparation; any release requires explicit content review.
- Entire local outputs, checkpoints, caches, and experimental folders, except deliberately reviewed artifacts under `reports/public/`.

## Licensing decisions

Public visibility is not the same as an open-source license. Check the **actual contents** of the local source tree for code copied or modified from:
- [ChessDS DSC](https://github.com/ChessDS/chessds-dsc) — upstream GitHub identifies GPL-3.0.
- [Maia 3](https://github.com/CSSLab/maia3) — upstream GitHub identifies AGPL-3.0.
- [Stockfish](https://github.com/official-stockfish/Stockfish) — upstream GitHub identifies GPL-3.0.

Independently review dependencies, weights and model cards as needed. Document license notices and attribution. Do not choose a blanket repository license based solely on dependency names; determine whether upstream code is linked, copied, modified, or invoked as a separate program, and request the owner's decision when necessary.

## Publishing benchmark results

For every published number document:
1. Which game population and filtering procedure were used.
2. Number of **games** and **player decisions**, with a chronological split by full games.
3. Model identity, release/revision, rating inputs, history inputs and evaluation configuration.
4. Whether evaluated games may have been present in pretrained model training corpora.
5. Top-k definition, uncertainty estimation at game level, and whether log loss was based on a full policy.
6. Evidence of actual execution: sanitized logs, metadata, and machine-readable aggregates.

Do not imply causality, psychological traits or forecasting guarantees from descriptive chess data.
