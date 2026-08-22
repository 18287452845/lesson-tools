# Repository Guidelines

## Project Purpose
- 云林智能备课工具 (Yunlin intelligent lesson-preparation workspace): one AI-generated teaching design is shared across three artifacts — lesson plan (`.docx`), student handout (`.docx`), and classroom presentation (`.pptx`).
- `CLAUDE.md` holds the product-scope and template-policy notes; read it before touching template or generation code.

## Project Structure & Module Organization
- `backend/` holds the FastAPI app (`backend/main.py`) with `api/`, `services/`, `models/`, `utils/`, and `tests/`.
- `frontend/` contains the React + TypeScript UI built with Vite; Electron wrapper lives in `frontend/electron/`.
- `storage/` is runtime data (templates, uploads, outputs, SQLite database); treat as generated, not source.
- `docs/` and root markdown files (`DOCKER_DEPLOYMENT.md`, `TEXTBOOK_DEPLOYMENT.md`, `docs/E2E_TESTING.md`) capture testing and deployment notes; the workspace skill `.agents/skills/deploy-lesson-tools/` is the authoritative deployment procedure.
- Root scripts like `start.bat`, `start.sh`, and `run_backend.py` are the preferred entry points; the Python venv lives at `.venv/`.

## Architecture Constraints
- The only supported lesson-plan template is the immutable `backend/resources/templates/yunlin_lesson_plan.docx` (id `yunlin-standard`). Do not add template upload, deletion, version history, HTML conversion, or online Office editing; the backend validates the built-in file and its Jinja variables, and generation/publishing must enforce `yunlin-standard`.
- Key modules: `backend/services/builtin_template.py` (template identity/validation), `backend/api/preparation.py` (unified preparation endpoint), `backend/services/document_renderer.py` (lesson-plan rendering), `backend/services/preparation_renderer.py` (handout/PPT rendering), `frontend/src/pages/PreparationWorkspace.tsx` (main preparation UI).
- Layering: `backend/api/` routes stay thin and delegate to `backend/services/` (business logic) with persistence in `backend/models/`. Frontend state uses zustand stores and API calls via axios.

## Build, Test, and Development Commands
- `python run_backend.py` starts the API server on `http://127.0.0.1:8000`.
- `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload` is a direct alternative.
- `npm run dev` from `frontend/` starts the UI at `http://localhost:5173`.
- `npm run build` builds the frontend for production; `npm run preview` serves the build locally.
- `npm run electron:dev` runs the desktop app (Vite + Electron).
- `.\.venv\Scripts\python.exe -m pytest backend\tests` runs the backend suite from the repo root (root `pytest.ini` sets `testpaths = backend/tests`); append `--no-cov` for a fast run.
- `npm run build` from `frontend/` also typechecks (`tsc && vite build`); `npm run electron:build` packages the desktop installer.
- `docker-compose up -d --build` brings up Dockerized services for full-stack testing.

## Coding Style & Naming Conventions
- Python code uses 4-space indentation and `snake_case` module naming (see `backend/services/`).
- React components and pages use `PascalCase` filenames (see `frontend/src/pages/`); stores and services use `camelCase`.
- No repo-wide formatter or linter configs are present; follow local file style and keep import ordering consistent.

## Testing Guidelines
- Pytest discovery uses `test_*.py` and `*_test.py`, with tests under `backend/tests/`.
- Coverage is enforced via root `pytest.ini` (`--cov-fail-under=90`, `--strict-markers`, `asyncio_mode=auto`, 300s timeout); HTML coverage lands in `htmlcov/`.
- Registered markers: `unit`, `integration`, `slow`, `api`, `service`, `database`, `ai`, `smoke`. Avoid live AI calls unless provider keys are configured.

## Commit & Pull Request Guidelines
- Commit history mixes placeholders and Conventional Commit prefixes; prefer `feat:`, `fix:`, `docs:`, or `chore:` with short, imperative summaries.
- PRs should describe intent, list test commands run, and link relevant issues.
- UI changes should include screenshots or a short GIF; API changes should note affected endpoints.

## Configuration & Security
- Copy root `.env.example` to `.env` and keep secrets (AI provider keys) out of Git.
- Treat `storage/` as generated data; do not commit database or output files.
