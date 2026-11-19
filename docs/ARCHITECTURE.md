# FOI v1 architecture

## Offline pipeline

PGN acquisition + official FIDE monthly standard ratings → player identity resolution → game validation/classification → cross-source deduplication → chronological game splits → target-player decision extraction → DSC and Maia probability inference → Stockfish feature cache (optional) → personalizer training → frozen test scoring → per-player report.

### Interfaces

`BaseMovePredictor.predict(board, white_elo, black_elo, context) -> dict[str, float]`

- `board` should be a python-chess Board reconstructed from the game start and *all known previous moves*, not a FEN-only object for the history variant.
- Keys: UCI moves for every legal move; values: nonnegative probabilities summing to 1 after normalization.
- For each position, validate that predicted moves are legal. Fail loudly on NaN, missing legal moves, or invalid normalization.
- Wrap the actual repository APIs; do not assume Maia and DSC return identical Python objects.
- Record model code commit and weight revision/hash for every run.

### Personalization

Start with a **frozen** DSC-150M prior and optionally frozen Maia-3-79M.

- Baseline A: DSC only.
- Baseline B: Maia only.
- Baseline C: global ensemble fitted on population validation data, if available.
- Personalizer D: per-player L2-regularized residual logit model learned on the target's *past* games, blending probabilities and pre-move features (color, move number, position phase, pawn structure, repetition, opening familiarity, candidate properties).
- Stockfish-assisted E: add fixed-budget, precomputed legal-move engine features, using a missingness flag for moves outside MultiPV. All legal moves remain in the choice set; never add the observed move only because it is the label.
- LightGBM ranker: only after the simpler model, with probability calibration on validation data.

A possible residual policy: `p(a|s,u) = softmax_a(log(p_DSC(a|s)+epsilon) + w_u · phi(s,a))`. Use time-ordered training and penalization. Avoid per-player deep fine-tuning before establishing data sufficiency and demonstrating generalization.

### What predictions mean

A one-ply prediction with actual previous moves observed is **conditional next-move prediction**, not a forecast of the entire future game before it happens. A whole-game rollout requires sampling both players recursively and must be evaluated separately. Do not present one-step accuracy as multi-move forecast accuracy.

The tool is intended for pre-match preparation and retrospective research, **not real-time assistance during rated games**.
