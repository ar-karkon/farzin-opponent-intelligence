# Codex task — Publish the complete local FOI v1 project safely

You are working on the user's Ubuntu workstation, where the real implementation is located:

`/home/alireza/Project/UBUNTU/MagicalFarzin/foi_v1`

Publish the public/reproducible parts of that **existing** project to:

`https://github.com/ar-karkon/farzin-opponent-intelligence`

The remote repository is PUBLIC, already has a `main` branch, bootstrap documentation, `.gitignore`, `AGENTS.md`, and issue #1. Do not replace it with an empty or synthetic project.

## Mission and completion condition

Deliver a professional, actually working GitHub repository containing the verified FOI v1 code, installation and usage instructions, Kaggle orchestration, DSC-150M / Maia3-79M inference integrations, real-player PGN validation/benchmarking code, tests, public documentation, and **only approved/sanitized results** that actually exist locally. Complete the remote push and verify the remote content and CI. Refer to GitHub issue #1 and update its checklist.

Do not fabricate files, benchmark numbers, GPU runs, model revisions, accuracy improvements, or tests.

## Step 1 — Inspect before modifying

- Inspect the local tree, `git status`, branches, remotes, tracked and untracked files, logs, running scripts, dependencies and available reports.
- Check `git --version`, `gh auth status`, access to the correct GitHub repo and whether `gh`/GitHub CLI is configured. Authentication should use the existing authorized login flow; never request pasting a token into chat or code.
- Inspect actual project code (including notebooks, Kaggle kernels, src, scripts, configs, prompts, reports, tests). Do not assume earlier chat descriptions are an exact inventory.
- Identify which DSC/Maia runs and any real-player benchmark runs have **verifiable** local artifacts and distinguish completed/partial/failed work.

## Step 2 — Security, privacy and licensing gate BEFORE PUBLICATION

- Produce a manifest classifying all candidate files into PUBLIC, PRIVATE, THIRD-PARTY/NEEDS-LICENSE-REVIEW, or UNKNOWN.
- Exclude raw PGNs under `data/raw/pourramezanali/`, processed real-player records, full game-by-game/position-by-position predictions, private Kaggle notebook outputs, local caches, checkpoints and credentials unless redistribution has been explicitly verified and approved. Only synthetic tests and cleared aggregate reports may be released.
- Exclude all `.env`, Kaggle tokens, SSH keys, OAuth tokens, secrets, cookies, provider credentials, private notebook URLs, and sensitive log contents. Scan content and paths (including hidden files) and use `gitleaks` if available, or a robust fallback scan.
- **Do not import old local Git history blindly.** Previous commits may contain raw PGNs/secrets even when currently ignored. Build a clean publication commit series from an allowlist if needed. Scan the proposed new history before pushing.
- Do not publish real model weights or third-party source files merely because they exist locally.
- Verify upstream license/attribution and any weight-specific licenses. DSC upstream uses GPL-3.0; Maia 3 upstream uses AGPL-3.0; Stockfish upstream uses GPL-3.0. Decide based on actual incorporation/copying/linking, not project names alone. Prefer referencing/installing upstream instead of copying sources. Do not silently add an arbitrary license for owner's original code; document the decision or request authorization if a final selection is necessary.
- If private material is discovered in already public commits, stop, report the exposure and recommended credential rotation/remediation before attempting any destructive history rewrite.

## Step 3 — Safely integrate with existing remote

- Fetch/clone `ar-karkon/farzin-opponent-intelligence` into a separate **clean public-release worktree**. Keep the existing local project intact and preserve all uncommitted work.
- Start from the remote `main` that already includes `README.md`, `AGENTS.md`, `.gitignore`, `SECURITY.md`, `CONTRIBUTING.md`, `docs/PUBLICATION_POLICY.md`.
- Create a feature branch named `release/foi-v1-publication`, unless it already exists; if so inspect and reuse safely.
- Migrate only explicitly reviewed files. Use dry-run and explicit staging; do NOT stage the entire unreviewed source tree with `git add .`.
- Integrate and update the existing docs to match verified current code. No force push, no reset of user changes, no deletion of remote bootstrap commits.

## Step 4 — Make the codebase reproducible

- Preserve existing working model wrappers and Kaggle kernel entry points rather than rewriting proven code unnecessarily.
- Organize components cleanly: source modules, scripts, Kaggle/notebook files, configs, small synthetic fixtures, tests, docs, `reports/public`. Preserve compatible CLI paths or add migration notes.
- Make paths portable: no hardcoded `/home/alireza` or temporary /tmp paths in executable defaults. Use environment/config options and examples.
- Pin or constrain working dependency versions and Python compatibility using observed environment and verification, not guessed versions. Add `pyproject.toml` / requirements lock or both as appropriate.
- Provide executable CPU-only minimal smoke tests, parser/identity validation tests, chronology and no-leakage tests, legal-move probability/top-k metrics tests, and deterministic fixtures.
- Separate optional GPU and external model downloads from CPU-only developer setup.
- Create a lightweight GitHub Actions CI for checkout, Python setup, installing minimal dependencies, syntax/lint (if configured), pytest, and a publication safety check. Never use Kaggle secrets or attempt GPU inference on ordinary CI.
- Add `.env.example`, safe config examples, an architecture overview, an accurate installation quickstart and a `make`/CLI entry if appropriate.
- Keep `.gitignore` strict enough to exclude data/model artifacts even if a user reruns experiments; review staged paths and file sizes.

## Step 5 — Research transparency and documentation

- Write a thorough English README with an accurate title, scope, current status, limitations, architecture diagram, CPU quickstart, model adapter setup, Kaggle CLI workflow, PGN import, benchmarking workflow, testing, example outputs and acknowledgments.
- Make documentation for: dataset validation, historical standard ratings, OTB/classical verification, chronological 70/15/15 split by complete game/event when possible, pretrained-data contamination, rank metrics, DSC full-policy NLL, Maia top-k-only limitation, uncertainty by game, Stockfish feature extraction, and reproducibility/provenance.
- If real-player experiments have completed, publish only verified sanitized **aggregate** outcomes supported by local JSON/log evidence and with permitted provenance. Never invent numbers. If they are incomplete, state that candidly and provide reproduction commands.
- Identify the existing Pourramezanali case study using public factual identity only where appropriate, without redistributing game data. Explain that unverified time-control data cannot be labeled proven classical OTB.

## Step 6 — Verify, publish, and report

- Run all applicable local tests. Fix real problems. Run secret checks against staged source and new commits.
- Show a final staged path list; ensure no `*.pgn`, credentials, private outputs, large binaries or accidental symlinks are present.
- Commit on `release/foi-v1-publication` with clear commit messages, push to GitHub, open a PR linked to issue #1, and inspect the actual remote diff.
- Check GitHub Actions, repair failures, and update the PR until green. Since the owner explicitly requested the full publication, merge into `main` **only when** publication safety checks pass and licensing blockers are resolved. Never bypass a branch protection or safety check.
- Verify the final remote `main`, relevant file URLs and full commit SHA. Update issue #1 accurately, closing it only if all acceptance criteria are fulfilled.
- If an authorization or legal blocker genuinely prevents safe publication, complete the safe parts, create/update the PR, and report the exact blocker instead of claiming full completion.

## Final report to owner (Persian)

Include: repo and PR links, merged/main commit hash, number and categories of published files, tests and CI status, which GPU/model tasks were actually verified, public benchmark result links (if any), intentionally excluded private files, license decisions/blockers, and how another contributor can reproduce the project.

Work autonomously through these steps. Do not ask for basic decisions already made: target repository, public visibility, existing FOI v1 project, and Kaggle GPU setup are settled. Do not start a new fine-tuning experiment; the task is secure public release of existing work.
