# Third-party software and model notices

This repository does not bundle third-party source code, model weights, or a Stockfish executable. The optional Kaggle scripts install or download dependencies when run.

| Component | Use in FOI | Upstream license reported by repository | Source |
|---|---|---|---|
| ChessDS DSC inference package | Optional DSC model inference | GPL-3.0 | [ChessDS/chessds-dsc](https://github.com/ChessDS/chessds-dsc) |
| Maia 3 inference package | Optional Maia comparison | AGPL-3.0 | [CSSLab/maia3](https://github.com/CSSLab/maia3) |
| Stockfish | Optional external engine for analysis features | GPL-3.0 | [official-stockfish/Stockfish](https://github.com/official-stockfish/Stockfish) |
| python-chess | PGN parsing and board/move handling | GPL-3.0-or-later | [niklasf/python-chess](https://github.com/niklasf/python-chess) |
| PyYAML | YAML configuration parsing | MIT | [yaml/pyyaml](https://github.com/yaml/pyyaml) |

Upstream repository metadata was checked on 2026-11-19. This is attribution and a pointer to the upstream terms, not legal advice or a compatibility determination. Review license files, package terms, model cards, and weight-specific terms for the exact revisions you use. No model weights are redistributed here.

FOI's original project code has no selected blanket license in this release. No `LICENSE` file is provided, and public visibility does not grant a reuse license. The repository owner should select a project license after reviewing the implications of the dependencies and optional integrations.
