# Evaluation and reporting contract

## Probabilities

Use untempered raw model probabilities normalized across every legal move. Do not score only the top three, renormalize over top-k, use sampling temperature, or insert the true label into a candidate shortlist. For the observed legal move y, `NLL = -log(max(p(y), epsilon))`.

## Metrics

- Top-1 and Top-3: exact UCI match at the given decision point; report legal-move ties deterministically.
- Negative log-likelihood (NLL): lower is better, measured on all scored positions.
- Top-5, Brier score and calibration plots: secondary checks.
- Report separate opening / middlegame / endgame, White / Black, familiar / novel opening, all positions / move 16+, player-level and macro-game metrics.
- Report both aggregate micro accuracy and average-per-game/per-player accuracy; do not let long games overwhelm the interpretation.

## Comparison

Paired evaluation of DSC-150M vs Maia3-79M vs personalized DSC vs optional ensemble. Use bootstrap resampling of whole games (not independent individual moves) with 2,000 draws and a fixed seed, giving confidence intervals on differences. Make explicit that each player has limited games and improvement may be inconclusive.

## Sanity checks

- Reconstruct board from PGN move history and verify the true move is legal.
- Verify probability distribution covers all legal moves and sums to 1.
- Confirm no feature can see actual future moves, result, post-game evaluation, or future FIDE ratings.
- Check exact and near duplicate games across all data sources and splits.
- Check time-control and venue classification evidence.
- Ensure model selection, calibration and hyperparameters never use sealed test labels.
- Record model version, packages, compute type, date, file hashes, seeds, and filtering counts in test manifest.

## Proposed version-1 report

Player → # verified games/decisions → data coverage → DSC top1/top3/NLL → Maia top1/top3/NLL → personalizer top1/top3/NLL → uplift and 95% game-bootstrap CI → phase/color/opening breakouts → model errors and limitations → data-contamination warning (if applicable).
