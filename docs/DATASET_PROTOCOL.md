# Dataset protocol — FIDE professional OTB classical chess

## 1. Acquisition

Primary: The Week in Chess PGNs and official organizer/federation published games. Preserve the original PGN and event/source URL. Respect licensing, robots restrictions, and rights before mirroring or redistributing files. Use official FIDE historical monthly standard rating lists to reconstruct rating context at the game date; the present-day rating is not a valid substitute.

## 2. Player identity

All target identities must be resolved to a FIDE ID with provenance. If PGN lacks FIDE ID, verify via event, federation, historical name variants and dates; quarantine ambiguous cases for manual review. Always retain original strings and resolved IDs separately.

## 3. Game filters

- Strict primary cohort: both participants ≥ 2400 FIDE standard at the game's date, classical time control, over-the-board venue, legal parseable moves, known date, verified target identity.
- Exploratory cohort: target FIDE standard 2200–2399, separately reported; do not mix its results with primary cohort.
- FIDE rated alone is **not proof of classical**; exclude rapid/blitz/Armageddon, online and unclear controls from the strict cohort. Confirm using PGN TimeControl, official event description, or a documented manual source check. Record confidence and evidence.
- Reject illegal/unparseable games; partial moves are explicitly marked and used only if their earlier moves can be verified.
- Exact dedup across sources using normalized moves + player identities + date; investigate collisions, variations, and transpositions instead of silent overwrites.

## 4. Game-level schema

`game_id`, `event`, `event_id`, `round`, `date`, `white_name_raw`, `black_name_raw`, `white_fide_id`, `black_fide_id`, `white_elo_at_game`, `black_elo_at_game`, `white`, `black`, `result`, `time_control`, `time_control_verified`, `venue_verified`, `pgn`, `source_url`, `source_license`, `source_issue`, `checksum`, `quality_flags`, `split`.

## 5. Position-level schema

`sample_id`, `game_id`, `date`, `target_fide_id`, `target_color`, `ply_index`, `fen_before`, `prior_moves_uci`, `legal_moves_uci`, `actual_move_uci`, `white_elo_at_game`, `black_elo_at_game`, `phase`, `opening_familiarity`, `split`, `model_input_context_version`.

- Use target player's turns ONLY in per-target datasets.
- `prior_moves_uci` must end immediately before `actual_move_uci`; never reveal a future move as a feature.
- Position extraction may reconstruct board states from original PGN when inference is run, so history inputs work.
- PGN result, final ECO/opening labels derived from **future** moves, total game length, and post-game annotations are prohibited prediction features.
- Time left on clock is missing unless verified per-ply clock data exists. Do not impute as known.

## 6. Chronological splitting and contamination

- Deduplicate globally **before** splitting.
- Historical development split per target: earliest 70% games train, next 15% validation, latest 15% retrospective test. If two targets meet in one game, that game gets one globally consistent split (or is excluded from conflicting cross-player experiments).
- Historical test may overlap *public models' original pretraining data*, even if held out from *our own* personalizer. Label it `retrospective`.
- Strict external test: games played from **2026-10-24** onward, after the published release date of DSC (2026-10-23). Keep these sealed until all modeling decisions are frozen, and test only on games that meet all cohort filters. If too few games exist, report `insufficient post-release sample`, not a credible precision claim.
- For current ongoing players, record predictions for future games before the actual moves become available; this is the cleanest prospective evaluation.
- Keep games fully grouped in each split, never randomly split individual positions. Report weighted-by-move and macro-averaged-by-game measures separately.

## 7. Size targets, not invented holdings

Start with 3 professional players. Aim for about 150–400 high-quality games for each; proceed with an honest small-sample prototype if fewer are available. Aim for at least 20 clean test games/player before prominently displaying individual accuracy and confidence intervals; 20 is a practical minimum, not evidence of statistical precision. Use rolling-origin analysis for sparse players.
