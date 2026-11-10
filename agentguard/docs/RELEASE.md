# GitHub workflow and release process

## Upload as a new repository

### GitHub browser

1. Create a new repository named `agentguard` **without** adding README/.gitignore/license (provided here).
2. Upload the contents of this project directory (not the parent ZIP itself), preserving `.github/workflows/ci.yml`.
3. Commit to `main`, then open **Actions** and inspect `AgentGuard CI`.
4. Optionally add a GitHub Actions badge using your actual GitHub username.

### Git CLI (recommended)

```bash
cd agentguard
git init -b main
git add .
git commit -m "feat: initial AgentGuard end-to-end MVP"
git remote add origin https://github.com/YOUR_USERNAME/agentguard.git
git push -u origin main
```

If you have GitHub CLI: `gh repo create agentguard --public --source=. --remote=origin --push` after making the local commit (don't do both methods).

## CI design

`ci.yml` runs automatically on pushes to `main`, pull requests, and manually:

1. **Python checks:** compileall + Ruff lint + pytest API/evaluator integration tests.
2. **React checks:** `npm ci` and `npm run build` (TypeScript + Vite).
3. **Browser smoke:** starts a SQLite/eager FastAPI server, installs Playwright Chromium and opens the actual React dashboard.

CI secrets are not required for the simulated MVP. Use repository secrets and ephemeral environments for future cloud integrations. Avoid running arbitrary pull request agent code in a trusted GitHub Actions runner.

## Branch and review model

- `main` is the integration branch.
- For each feature, branch `feat/<feature>`, run tests, open a pull request.
- Require CI checks before merging.
- Add CODEOWNERS and GitHub branch protection once collaborators join.

## Manual release verification

```bash
docker compose up --build -d
python scripts/smoke_test.py
curl -f http://127.0.0.1:8000/health
```

Expected: vulnerable version receives lower score than hardened, comparison lists fixed failures, dashboard displays traces. Stop with `docker compose down`.

## Future CD

Only after adding real identity, migrations, secrets, network isolation and production settings should you create a separate deployment workflow using OIDC short-lived credentials, environment protection, vulnerability scanning and signed images.

## CI gate CLI

For future staging use, once a run ID is available:

```bash
python scripts/release_gate.py \
  --base-url https://agentguard-staging.example.com \
  --run-id YOUR_RUN_UUID \
  --api-key "$AGENTGUARD_API_KEY" \
  --minimum-score 90 --maximum-critical 0
```

Exit codes: 0 pass, 1 failed policy, 2 unavailable/incomplete evaluation. Never put the API key literal into workflow logs or committed source.
