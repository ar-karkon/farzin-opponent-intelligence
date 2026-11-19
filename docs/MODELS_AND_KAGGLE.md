# Models and Kaggle

## DSC

The maintained Kaggle scripts use the upstream `chessds-dsc` inference package and DSC-150M weights. The wrapper supplies a `python-chess` board with its complete move history and explicit FIDE rating, classical time-control and OTB inputs. It verifies that the returned policy covers every legal move and sums to one. DSC upstream identifies its code as GPL-3.0; the repository downloads it rather than copying its source or weights.

## Maia 3

Maia 3 79M is an optional comparison model. Standard UCI MultiPV gives a ranked shortlist, not a probability for every legal move. The smoke kernel reports top-five-only output and does not calculate NLL from it. The benchmark adapter calls the pinned Maia Python model and legal-move mask to derive a full legal-move policy; it depends on internal APIs, so pin and re-verify the source revision before each run. Maia 3 upstream identifies its code as AGPL-3.0. No Maia source or checkpoint is included here.

## Stockfish

Stockfish can provide fixed-budget position and candidate-move features in a separate analysis step. It is an engine, not a human move-probability model. Install a compatible binary separately, record its version and options, and follow upstream GPL-3.0 obligations. Do not commit the binary or derived per-player records.

## Kaggle smoke run

Install the Kaggle CLI and authenticate through Kaggle's supported local flow. Keep the credentials outside this repository. Generate metadata and push the smoke kernel:

```bash
python scripts/configure_kaggle.py --username YOUR_KAGGLE_USERNAME
kaggle kernels push -p kaggle
kaggle kernels status YOUR_KAGGLE_USERNAME/foi-v1-gpu-smoke
kaggle kernels output YOUR_KAGGLE_USERNAME/foi-v1-gpu-smoke -p /private/path/foi-smoke-output
```

The script targets a single synthetic position and has `real_fide_games_used: 0`. The metadata generator requests a private kernel, GPU and internet; confirm account policy and metadata before running. Model package/weight downloads happen only in Kaggle. Kernel execution and real-player benchmarking are not part of CPU CI.

## Private benchmark run

The benchmark entry point is `kaggle_benchmark/foi_v1_benchmark.py`. Validate permitted source data locally with `scripts/validate_dataset.py`; attach only the resulting private positions to a private Kaggle kernel. Keep all validation outputs, predictions, logs and reports private. Retrieve outputs to a private directory, then evaluate with `scripts/evaluate_benchmark.py`. Do not attach public datasets or publish the kernel. The benchmark emits game-level uncertainty intervals and records model/package revisions and artifact hashes when available.

The local research logs show completed synthetic GPU smoke checks on Kaggle Tesla T4 for the small and full model variants. This confirms the model wrappers ran for the synthetic fixture only; it does not establish player accuracy, external generalization, or a reproducible public benchmark. Evidence is summarized in `reports/public/VERIFICATION.md`; detailed private artifacts remain withheld.

## Model-data limitations

All historical test results are retrospective unless the games were played after a frozen protocol and model release and meet every cohort filter. Pretraining contamination is unknown. Keep full-game splits chronological, use current decision context only, and report sample sizes at both game and player-decision level. No fine-tuning experiment is started by these workflows.
