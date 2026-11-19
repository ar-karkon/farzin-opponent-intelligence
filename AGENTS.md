# FOI v1 — instructions for coding agents

The authoritative implementation currently lives on the owner's **local machine** under `~/Project/UBUNTU/MagicalFarzin/foi_v1`. This public repository was initialized before migration. Do not assume the GitHub checkout contains working inference code until it has been inspected and integrated.

## Mission

Publish a reproducible, maintainable, well-documented FOI v1 codebase to `ar-karkon/farzin-opponent-intelligence`. Preserve the existing verified Kaggle inference implementation, and make no unverified claims about player prediction performance.

## Non-negotiable publication safeguards

1. Before **any push**, inventory all candidate files and classify them as public, private, third-party, or unknown. Private/unknown must not be published.
2. Never commit Kaggle authentication, API keys, OAuth tokens, local proxy settings with credentials, SSH keys, cookies, private environment files, or hardcoded secrets. Scan the **full commit history** as well as the working tree. If a secret has already been committed, stop publication, explain revocation and history-rewrite requirements, and ask for approval.
3. Do not publish original PGNs or processed real-player records unless their redistribution rights have been verified. Synthetic fixtures are permitted if they do not reproduce confidential data.
4. Do not redistribute model weights or third-party code without verifying licenses, attribution, and compatibility. Maia 3 and DSC have different copyleft obligations. Avoid copying third-party source when an upstream dependency suffices.
5. Keep every Kaggle kernel **private** by default. Never store real credentials in notebooks or GitHub Actions.
6. Do not force-push, delete branches, rewrite public history, or clobber pre-existing local changes. Fetch first and reconcile independently created GitHub bootstrap commits with local work. Ask for approval before destructive changes.
7. Do not claim accuracy numbers or successful tests unless supported by preserved machine-readable outputs and logs. Historical holdouts may overlap pretrained-model training data.
8. Establish separate local/private research outputs and explicitly reviewed `reports/public/` artifacts. No individual sensitive metadata in public reports.

## Engineering expectations

- Keep local inference, dataset parsing, benchmarking, and Kaggle orchestration as separately testable modules.
- Use relative paths, environment variables, configuration examples, reproducible pinned dependencies, and a CPU-only smoke test for contributors.
- Write deterministic, synthetic tests for PGN parsing, player-color identification, chronological splitting, probability normalization, and metrics.
- Create lightweight GitHub Actions that do not require GPU, Kaggle credentials, or access to private data.
- Keep the model's full-policy NLL restricted to methods exposing an actual complete legal-move probability distribution. Do not renormalize Maia's top-five outputs and call them full policy.
- Document limitations, model licenses, external weights, provenance, and reproduction instructions. Set the repository license only after reviewing compatibility and obtaining the owner's approval where needed.

## Completion evidence

Finish with the remote branch name and commit SHA, links to the published README and CI, a pass/fail checklist of local and CI tests, an explicit list of excluded private files, and the remaining blockers. Do not report completion merely because `git push` returned zero.
