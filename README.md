# Farzin Opponent Intelligence (FOI)

**Research tools for predicting human chess moves and evaluating opponent-specific behavior.**

FOI investigates how accurately human-move prediction models can anticipate decisions by professional over-the-board chess players. The project aims to support reproducible baselines, player-level error analysis, and carefully validated personalization.

> **Release status:** Repository initialized. The existing local FOI v1 implementation and reproducible research materials are being prepared for publication. This README must be updated from the verified source tree before the first usable release.

## Scope

- Ingest and validate chess PGNs, player identities, dates, and time controls.
- Evaluate identical positions with **ChessDS DSC** and **Maia 3**.
- Report Top-1/Top-3/Top-5 accuracy, plus full-policy NLL where supported.
- Keep complete games and tournament boundaries intact across chronological splits.
- Summarize chess behavior with interpretable, position-based features and Stockfish analysis.
- Enable reproducible, **private** Kaggle GPU inference when a user has their own credentials.

## Evaluation safeguards

Historical game holdouts **do not automatically prove** that a pretrained model has never seen those games. We report that limitation explicitly. We distinguish tested model execution from independently evaluated player prediction and do not present hypothetical numbers as measurements.

## Publication and privacy

Only redistributable source code, synthetic fixtures, publishable aggregate statistics, and permission-cleared materials belong in this public repository. Raw PGNs without clear redistribution rights, credentials, proprietary datasets, model weights, and confidential analysis outputs are excluded by default. See [Publication Policy](docs/PUBLICATION_POLICY.md) and [Security](SECURITY.md).

## Third-party software

ChessDS DSC, Maia 3, and Stockfish are independent upstream projects. Follow their individual copyright and license terms; including references to a project does not incorporate its source code or grant redistribution rights to its weights or datasets.

## Developer instructions

See [AGENTS.md](AGENTS.md) for the FOI v1 migration, testing, and public-release requirements. Installation and reproduction commands will be added only after verification against the local implementation.

## License

No license has yet been selected for the original FOI code. Public visibility alone does not grant reuse permission. The project owner will finalize a license after reviewing third-party dependencies and any copied or modified upstream code.
