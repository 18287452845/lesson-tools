# Repository Guidelines

## Project Structure & Module Organization
- `backend/` holds the FastAPI app (`backend/main.py`) with `api/`, `services/`, `models/`, `utils/`, and `tests/`.
- `frontend/` contains the React + TypeScript UI built with Vite; Electron wrapper lives in `frontend/electron/`.
- `storage/` is runtime data (templates, uploads, outputs, SQLite database); treat as generated, not source.
- `docs/` and root markdown files capture deployment and operational notes.
- Root scripts like `start.bat`, `start.sh`, and `run_backend.py` are the preferred entry points.

## Build, Test, and Development Commands
- `python run_backend.py` starts the API server on `http://127.0.0.1:8000`.
- `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload` is a direct alternative.
- `npm run dev` from `frontend/` starts the UI at `http://localhost:5173`.
- `npm run build` builds the frontend for production; `npm run preview` serves the build locally.
- `npm run electron:dev` runs the desktop app (Vite + Electron).
- `cd backend && pytest` runs the backend test suite with coverage thresholds.
- `docker-compose up -d --build` brings up Dockerized services for full-stack testing.

## Coding Style & Naming Conventions
- Python code uses 4-space indentation and `snake_case` module naming (see `backend/services/`).
- React components and pages use `PascalCase` filenames (see `frontend/src/pages/`); stores and services use `camelCase`.
- No repo-wide formatter or linter configs are present; follow local file style and keep import ordering consistent.

## Testing Guidelines
- Pytest discovery uses `test_*.py` and `*_test.py`, with tests under `backend/tests/`.
- Coverage is enforced via `pytest.ini` (`--cov-fail-under=60`); expect HTML coverage in `htmlcov/`.
- Use markers like `unit`, `integration`, or `ai` to scope runs; avoid live AI calls unless keys are configured.

## Commit & Pull Request Guidelines
- Commit history mixes placeholders and Conventional Commit prefixes; prefer `feat:`, `fix:`, `docs:`, or `chore:` with short, imperative summaries.
- PRs should describe intent, list test commands run, and link relevant issues.
- UI changes should include screenshots or a short GIF; API changes should note affected endpoints.

## Configuration & Security
- Copy `.env.example` or `backend/.env.example` to `.env` and keep secrets out of Git.
- Treat `storage/` as generated data; do not commit database or output files.
