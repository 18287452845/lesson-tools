# Repository Notes

This repository is a FastAPI + React teaching-preparation workspace.

## Product scope

- Generate a Yunlin-format lesson plan (`.docx`).
- Generate a student handout (`.docx`).
- Generate a classroom presentation (`.pptx`).
- Share one AI-generated teaching design across all requested artifacts.

## Template policy

The only supported lesson-plan template is the immutable resource at:

```text
backend/resources/templates/yunlin_lesson_plan.docx
```

Do not add template upload, deletion, version history, HTML conversion, or online Office editing. The backend must validate the built-in file and its required Jinja variables before generation. Legacy database rows may remain for history, but new generation and publishing must enforce the `yunlin-standard` template id.

## Key modules

- `backend/services/builtin_template.py`: fixed template identity, validation, checksum, and database registration.
- `backend/api/preparation.py`: unified preparation endpoint.
- `backend/services/preparation_renderer.py`: handout and PowerPoint rendering.
- `backend/services/document_renderer.py`: Yunlin lesson-plan rendering.
- `frontend/src/pages/PreparationWorkspace.tsx`: main preparation UI.

## Commands

```powershell
python run_backend.py
cd frontend; npm run dev
.\.venv\Scripts\python.exe -m pytest backend\tests --no-cov
cd frontend; npm run build
```

Runtime uploads, generated outputs, and SQLite data live in `storage/` and must not be committed.
