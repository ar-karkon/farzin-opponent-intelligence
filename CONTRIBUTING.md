# Contributing to Farzin Opponent Intelligence

Thank you for helping make chess-move prediction reproducible and useful.

## Before contributing

Read [AGENTS.md](AGENTS.md), [Publication Policy](docs/PUBLICATION_POLICY.md), and [Security](SECURITY.md). Do not upload real-player PGNs, credentials, raw prediction-level records, or weights without a rights and security review.

## What makes a good contribution

- A testable fix or feature with a clear, limited scope.
- Deterministic tests using synthetic chess positions and fixtures.
- Reproducible configuration, pinned package versions, and model revision information.
- Accurate evaluation methodology: chronological full-game splits and explicit pretrained-data exposure limitations.
- Clear documentation of any changes to Top-k metrics, probability calibration, and runtime requirements.

## Development process

1. Open an issue for a substantial proposed change.
2. Create a focused branch and implement the change.
3. Run CPU-only tests and lint locally; GPU tests are optional and should use private infrastructure.
4. Open a pull request explaining its scope, tests, data/permission review, and compatibility.
5. Do not include binary checkpoints or personal credentials in the pull request.

Install with `python -m pip install -e '.[dev]'`, then run `python -m unittest discover -s tests -p 'test_*.py'`, `ruff check .`, and `python scripts/publication_safety.py`. Tests use synthetic fixtures only. GPU/model checks are optional and must not use public data or CI credentials.

## License and attribution

An original-project license has not yet been selected. Do not assume that code in this public repository can be copied or relicensed. Preserve third-party notices and refer to each upstream project's license.
