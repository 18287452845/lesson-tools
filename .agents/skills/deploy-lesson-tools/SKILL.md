---
name: deploy-lesson-tools
description: Push validated Lesson Tools changes to GitHub and safely deploy or redeploy them to the production VPS. Use when the user asks to push, publish, deploy, redeploy, update the server, update ls.linnera.link, run Docker on my-vps, or release this repository to production. Do not use for local-only testing or generic Docker questions.
---

# Deploy Lesson Tools

Publish the intended local changes to `origin/main`, synchronize the published tree to the existing VPS checkout without losing production data or configuration, rebuild only the affected containers, and verify the public application.

## Production target

- Git remote: `origin`
- Production branch: `main`
- SSH alias: `my-vps`
- Project directory: `/opt/prj/lesson-tools`
- Public URL: `https://ls.linnera.link`
- Compose services: `backend`, `frontend`
- Containers: `lesson-tools-backend`, `lesson-tools-frontend`
- Local ports: backend `8001`, frontend `8081`

Never print `.env` values, API keys, tokens, SSH key paths, or other secrets.

## 1. Confirm publication scope

Require an explicit request to push or deploy before changing GitHub or the VPS.

Run read-only checks first:

```powershell
git status -sb
git branch --show-current
git remote -v
git diff --stat
git diff --check
git log -5 --oneline --decorate
```

- Inspect all modified and untracked files before staging.
- Treat unrelated or unexplained files as user-owned; ask before including them.
- Deploy production only from `main`. If work is on another branch, do not merge, rebase, or switch it into `main` without explicit direction.
- Run `git fetch origin` and stop for reconciliation if local `main` and `origin/main` have diverged.
- Record the file list that will be published so it can determine which images to rebuild.

## 2. Validate before committing

Run the full backend gate when backend code, tests, Python dependencies, or shared deployment files changed:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```

Require all tests to pass and the configured coverage threshold to pass. If the test run modifies tracked `.coverage`, restore it only when it was clean before this run and the change is purely generated coverage data.

Run the frontend production build when `frontend/` or frontend build configuration changed:

```powershell
Set-Location frontend
npm run build
Set-Location ..
```

Do not publish after a failed required check unless the user explicitly accepts that risk.

## 3. Commit and push

- Stage only the confirmed files, preferably with explicit paths.
- Use a short Conventional Commit message such as `fix: ...`, `feat: ...`, or `test: ...`.
- Recheck `git diff --cached --check` and `git status -sb` before committing.
- Push production with `git push origin main`.
- Verify both the local commit and `refs/heads/main` on GitHub resolve to the same SHA.
- Do not open a pull request unless requested; this repository's explicit production-publish flow pushes `main` directly.

Stop before deployment if the push fails or the remote SHA does not match.

## 4. Inspect the VPS without changing it

Use non-interactive SSH and confirm the exact target:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=15 my-vps "cd /opt/prj/lesson-tools && git status -sb && git remote -v && docker compose ps"
```

Expect that the VPS checkout may remain on an older feature branch with tracked and untracked source files from prior archive-based deployments. Do not run `git reset --hard`, `git clean`, destructive checkout commands, or a blind `git pull`.

Before overwriting source files:

- Run `git fetch origin main` on the VPS.
- Confirm `origin/main` is the SHA just pushed.
- Inspect tracked and untracked server-side source changes, excluding generated `storage/` data and known environment files.
- Determine whether any source exists only on the server. If unique server-only source cannot be accounted for, stop and report it.
- Preserve `.env`, `frontend/.env.production`, the entire `storage/` data set, and existing database backups.

## 5. Back up and synchronize the published tree

Create a root-readable deployment backup under `/opt/prj/.deployment-backups/` before synchronization. Set `umask 077`. Exclude bulky generated directories such as `.git`, `storage`, `.venv`, `frontend/node_modules`, `htmlcov`, `.pytest_cache`, `.ruff_cache`, and `.codex_tmp`; keep production configuration in the protected backup.

Save `frontend/.env.production` to a secure temporary file, then synchronize exactly from the fetched Git object rather than from local uncommitted files:

```bash
git archive --format=tar origin/main | tar -xf -
```

Restore `frontend/.env.production` immediately and remove its temporary copy. Archive extraction must not delete `storage/`, `.env`, database files, uploads, outputs, or historical backups. Tracked template assets under `storage/competition_templates/` may update from `main`.

Do not clean the VPS Git metadata merely to make `git status` look clean. The deployed runtime tree matters; report that archive synchronization leaves the old checkout metadata intact when applicable.

## 6. Build before switching containers

Keep the current healthy containers running while images build. Record the current backend and frontend image IDs so a failed switch can be rolled back.

Choose the build scope from the published file list:

- Backend only: changes under `backend/`, backend dependencies, or backend-only tests/configuration.
- Frontend only: changes under `frontend/` that affect the built application.
- Both: shared deployment files, Dockerfiles, Compose configuration, cross-stack changes, or an uncertain baseline.
- Test-only changes need no runtime rebuild unless bundled with runtime changes.

Try normal Compose builds first. If Docker's build network cannot resolve package sources, use the previously verified host-network fallback without altering runtime networking:

```bash
docker build --network=host -f backend/Dockerfile -t lesson-tools-backend .
docker build --network=host -f frontend/Dockerfile -t lesson-tools-frontend frontend
```

Build success alone does not authorize replacing an unrelated service. Switch only successfully built affected services:

```bash
docker compose up -d --no-deps --force-recreate backend
docker compose up -d --no-deps --force-recreate frontend
```

If a new container fails, retag the recorded previous image ID, recreate that service, and report the rollback.

## 7. Verify production

Require all applicable checks:

- `docker compose ps` shows both services running and healthy.
- `http://127.0.0.1:8001/health` returns `{"status":"healthy"}`.
- `https://ls.linnera.link` returns HTTP 200 from outside the container network.
- Recent backend and frontend logs contain no startup error or traceback.
- For changed runtime files, compare the GitHub `origin/main` blob, VPS file, and container file hashes.
- Local `main` is clean and synchronized with `origin/main`.

When a changed feature has a safe, non-mutating API smoke test, run it as well. Do not trigger live AI generation or mutate production data merely for a smoke test.

## 8. Report the release

Return:

- Commit SHA and message
- Branch and GitHub push result
- Tests, coverage, and frontend build results
- Rebuilt services
- Container health and public HTTP result
- Deployment backup path
- Whether VPS Git metadata remains in the prior archive-deployment state
- Any rollback or unresolved warning

Emit Git stage, commit, and push UI directives only for actions that actually succeeded.
