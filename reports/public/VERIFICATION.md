# Verified local run summary

The preserved local research workspace contains prior Kaggle GPU smoke-run logs and JSON outputs for synthetic positions. Those artifacts record completed runs on a Tesla T4 for DSC-23M with Maia 3 5M and DSC-150M with Maia 3 79M. They are not included in this public repository because raw logs and per-position model outputs have not been cleared for redistribution.

The smoke position was synthetic; no real-player games were used. This evidence verifies execution of the requested model adapters in the recorded environment only. It is not a player benchmark, accuracy result, model comparison, or claim of generalization. No aggregate player-level result is published.

The local test suite was run before migration: 7 tests passed under Python 3.14.4, python-chess 1.999, and PyYAML 6.0.3. The public CI will independently run the tests on its declared Python version.
