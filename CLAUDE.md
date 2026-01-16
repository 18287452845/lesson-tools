# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Intelligent Lesson Plan Assistant - An AI-powered lesson plan generation and editing tool. This is a full-stack application with a FastAPI backend, React/TypeScript frontend, and optional Electron desktop wrapper.

**Key Features**:
- Template management with Jinja2 syntax support
- Visual template editor with TipTap rich text editing
- Single and batch lesson plan generation
- Hours-based batch generation (configurable hours per lesson)
- Real-time batch task progress tracking with background processing
- AI content editing (optimize, expand, rewrite)
- Multi-provider AI support (DeepSeek, Anthropic Claude)

## Development Commands

### Backend (FastAPI + Python)

```bash
# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Start backend server (recommended)
python run_backend.py

# Alternative: Direct uvicorn command
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
cd backend
pytest

# Test API endpoints
python test_api.py

# Management scripts (cross-platform)
# Windows: start.bat | status.bat | stop.bat
# Linux/Mac: ./start.sh | ./status.sh | ./stop.sh
```

Backend runs on `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### Frontend (React + TypeScript + Vite)

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

Frontend runs on `http://localhost:5173`

### Electron Desktop App

```bash
cd frontend

# Development mode (starts both Vite and Electron)
npm run electron:dev

# Build desktop application
npm run build
npm run electron:build
```

Packaged apps are output to `frontend/dist-electron/`

### Docker Deployment

```bash
# Build and start services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Access services
# Frontend: http://localhost:8081
# Backend: http://localhost:8001
# API docs: http://localhost:8001/docs
```

See `DOCKER_DEPLOYMENT.md` for comprehensive Docker deployment guide including data persistence, troubleshooting, and production deployment.

## Architecture

### Backend Architecture

**API Layer** (`backend/api/`):
- `templates.py` - Template upload, list, delete, preview, HTML conversion, Jinja2 validation, field config
- `generate.py` - AI-powered lesson plan generation
- `lesson_plans.py` - Lesson plan retrieval and management
- `edit.py` - AI content optimization (optimize, expand, rewrite)
- `documents.py` - Document download and management
- `settings.py` - Application settings management
- `batch.py` - **Batch generation**: Chapter splitting, task creation, progress tracking, ZIP download
- `classes.py` - Class/grade management

**Service Layer** (`backend/services/`):
- `ai_provider.py` - **Multi-provider AI abstraction**. Supports both DeepSeek and Anthropic Claude via factory pattern. Each provider implements the `AIProvider` interface with `generate()` method.
- `ai_generator.py` - Lesson plan generation using AI. Constructs prompts and parses structured JSON responses.
- `ai_editor.py` - Content editing operations (optimize, expand, rewrite)
- `template_parser.py` - **Parses Word templates for Jinja2 variables** (`{{ variable }}`), loops (`{% for %}`), and conditionals (`{% if %}`). Extracts field configurations.
- `template_sync.py` - **Auto-syncs templates from `storage/templates/` folder to database on startup**
- `template_versioning.py` - Template version history management
- `document_renderer.py` - **Critical**: Uses `docxtpl` (not python-docx) for template rendering to preserve document structure.
- `document_modifier.py` - Modifies existing Word documents
- `lesson_plan_service.py` - Lesson plan business logic and data operations
- `docx_converter.py` - DOCX ↔ HTML bidirectional conversion using mammoth/htmldocx
- `jinja_protector.py` - Protects Jinja2 syntax during HTML conversion
- `chapter_splitter.py` - **Batch generation**: Splits courses into chapters based on total hours
- `batch_processor.py` - **Batch generation**: Processes batch tasks, groups lessons (2 per doc), renders combined documents
- `background_runner.py` - **Background processing**: Runs async tasks in separate threads with graceful shutdown

**Configuration** (`backend/config.py`):
- Centralized settings using Pydantic
- Supports multiple AI providers (DeepSeek, Anthropic)
- Environment variables loaded from `.env`
- Auto-creates storage directories

**Data Models** (`backend/models/`):
- `schemas.py` - Pydantic models for API request/response
- `database.py` - SQLite async database operations using aiosqlite

### Frontend Architecture

**State Management** (Zustand stores in `frontend/src/stores/`):
- `templateStore.ts` - Template selection and management
- `templateEditorStore.ts` - **Template editor state**: HTML content, metadata, variables, fields, preview
- `generatorStore.ts` - Lesson plan generation workflow
- `editorStore.ts` - Rich text editing state
- `settingsStore.ts` - Application settings

**Services** (`frontend/src/services/`):
- `api.ts` - Main API client (template, generation, AI editing, batch endpoints)
- `settingsApi.ts` - Settings API client
- `fileService.ts` - File operations (download, save)

**Pages** (`frontend/src/pages/`):
- `Home.tsx` - Landing page
- `TemplateManager.tsx` - Upload and manage templates
- `TemplateEditor.tsx` - **Visual template editor**: TipTap-based editing, Jinja2 insertion, version history
- `NewLessonPlan.tsx` - Multi-step lesson plan generation wizard
- `EditLessonPlan.tsx` - Rich text editor with TipTap
- `LessonPlanDetail.tsx` - View generated lesson plans
- `History.tsx` - Previous lesson plans
- `Settings.tsx` - AI provider and API key configuration
- `BatchGenerate.tsx` - **Batch generation wizard**: Chapter splitting, task creation
- `BatchDownloads.tsx` - **Download center**: Browse and download completed batch tasks
- `BatchTaskDetail.tsx` - **Task monitoring**: Real-time progress tracking for batch tasks
- `CachedLessonPlans.tsx` - **Template cache**: View and manage cached chapter templates
- `ClassManager.tsx` - Manage teaching classes

### Storage Structure

```
storage/
├── templates/      # User-uploaded .docx templates
├── uploads/        # Temporary upload files
├── outputs/        # Generated .docx documents
└── database.db     # SQLite database
```

**Note**: Templates placed directly in `storage/templates/` will be automatically imported to the database on backend startup via `TemplateSyncService`. Use `python import_templates.py` for manual import.

### Database Schema

SQLite database at `storage/database.db`:
- `templates` - Template metadata and field configurations
- `template_versions` - Template version history
- `lesson_plans` - Generated lesson plan records
- `batch_tasks` - Batch generation tasks (status, progress, ZIP path)
- `batch_lesson_plans` - Individual lesson plans within batch tasks
- `course_chapter_templates` - Cached chapter templates for reuse

## Key Technical Details

### Batch Generation System

**Architecture**: Hours-based generation with configurable lessons per document.

**Workflow**:
1. `POST /batch/split-chapters` - Split course into chapters based on total hours
   - Supports user-provided chapter input or AI-generated chapters
   - Caches templates in `course_chapter_templates` table for reuse
2. `POST /batch/create-task` - Create batch task and start background processing
   - Uses `BackgroundTaskRunner` to run async tasks in separate threads
   - Graceful shutdown support via `BackgroundTaskManager`
3. `GET /batch/tasks/{id}` - Poll for task progress (completed_count, failed_count)
4. `GET /batch/tasks/{id}/download` - Download ZIP when status is "completed"

**Processing** (`BatchTaskProcessor`):
- Groups lessons into documents (default: 2 lessons per document)
- Sequential document numbering: `course_name_01.docx`, `course_name_02.docx`
- Each lesson plan generated via `AIGenerator`, rendered via `DocumentRenderer`
- Individual records in `lesson_plans` and `batch_lesson_plans` tables
- All documents packaged into ZIP on completion

**Error Handling**:
- Failed lessons don't abort entire batch (continue with next document)
- Status tracking: pending → processing → completed/failed/cancelled
- Failed count incremented per failed lesson

### AI Provider System

The application supports two AI providers with unified interface:
- **DeepSeek** (default): `ai_provider=deepseek`, requires `DEEPSEEK_API_KEY`
- **Anthropic**: `ai_provider=anthropic`, requires `ANTHROPIC_API_KEY`

Configuration in `.env`:
```env
AI_PROVIDER=deepseek              # or 'anthropic'
DEEPSEEK_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx     # optional
```

Provider switching is done via `AIProviderFactory.create_provider()` which returns appropriate provider instance.

### Template System

**Template Syntax** (Jinja2):
- Variables: `{{ variable_name }}`
- Loops: `{% for item in items %}...{% endfor %}`
- Conditionals: `{% if condition %}...{% endif %}`

**Standard Fields** defined in `template_parser.py`:
- Required: subject, grade, topic, duration, teaching_goals, key_points, difficult_points, teaching_steps
- Optional: teaching_tools, teaching_methods, student_analysis, textbook_analysis, homework, blackboard_design, reflection

**Template Rendering Flow**:
1. Template uploaded → TemplateParser extracts fields → Stored with field configs
2. User fills generation form → AI generates content → Structured JSON returned
3. DocumentRenderer uses `docxtpl.DocxTemplate.render()` to fill template
4. Preserves all formatting, table structure, and styles

### Visual Template Editor

**Architecture**: TipTap-based rich text editor with Jinja2 syntax support.

**Key Endpoints** (`backend/api/templates.py`):
- `GET /templates/{id}/html` - Convert DOCX to editable HTML
- `POST /templates/{id}/save-html` - Convert HTML back to DOCX
- `POST /templates/{id}/preview-html` - Preview Jinja2 rendering
- `POST /templates/{id}/validate-jinja` - Validate Jinja2 syntax
- `GET /templates/{id}/versions` - Get version history
- `POST /templates/{id}/versions/{vid}/restore` - Restore version

**Conversion Pipeline** (`docx_converter.py`):
- DOCX → HTML: Uses `mammoth` library with Jinja2 protection
- HTML → DOCX: Uses `htmldocx` library
- `JinjaProtector` wraps Jinja2 syntax in special markers to prevent corruption

**Frontend Store** (`templateEditorStore.ts`):
- Manages HTML content, metadata, variables, field configs
- Auto-save with 3-second debounce
- Version history tracking and restore

### Document Export Fix

**Critical**: The document renderer MUST use `docxtpl` library, not `python-docx`:
- `python-docx` does simple text replacement and destroys table structure
- `docxtpl` is a proper Jinja2 template engine that preserves formatting
- See `WORD_EXPORT_FIX.md` for detailed explanation and test results

### Frontend-Backend Communication

- CORS configured for `localhost:5173-5178` ports
- Static files served from `/static` endpoint (maps to `storage/outputs/`)
- File downloads via `/api/documents/download/{filename}`
- All API endpoints prefixed with `/api`

## Environment Setup

Required `.env` file in project root:
```env
# AI Provider
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxx

# Optional Anthropic
ANTHROPIC_API_KEY=sk-ant-xxx

# Optional overrides
API_HOST=0.0.0.0
API_PORT=8000
AI_MODEL=deepseek-chat              # Override default model
AI_MAX_TOKENS=4096
AI_TEMPERATURE=0.7
```

## Testing

```bash
# Backend unit tests
cd backend
pytest

# Run specific test categories
pytest -m unit              # Fast, isolated unit tests only
pytest -m integration       # Integration tests
pytest -m api               # API endpoint tests
pytest -m service           # Service layer tests
pytest -m "not slow"        # Skip slow tests
pytest -m "not ai"          # Skip tests requiring AI API keys
pytest -m smoke             # Quick smoke tests

# With coverage report
pytest --cov=backend --cov-report=html --cov-report=term-missing

# API integration tests
python test_api.py

# Template debugging
python debug_template.py
python check_templates.py

# Document rendering test (validates docxtpl fix)
python test_docxtpl.py

# Document template test
python test_renderer.py
```

**Test Markers** (defined in `pytest.ini`):
- `unit` - Fast, isolated unit tests
- `integration` - Integration tests (may use external services)
- `slow` - Slow tests (database, file I/O, AI calls)
- `api` - API endpoint tests
- `service` - Service layer tests
- `database` - Database operation tests
- `ai` - Tests requiring AI provider API keys
- `smoke` - Quick smoke tests for basic functionality

## Template Import Scripts

```bash
# Automatically import templates from storage/templates/
python import_templates.py

# Simplified template import
python import_templates_simple.py

# Sync templates now (forces re-sync)
python sync_templates_now.py

# Fix template paths in database
python fix_template_paths.py
```

**Note**: Templates in `storage/templates/` are automatically imported on backend startup via `TemplateSyncService`. Manual scripts are provided for troubleshooting or bulk imports.

## Additional Documentation

- `README.md` - Comprehensive Chinese language project overview, setup guide, and user manual
- `DOCKER_DEPLOYMENT.md` - Complete Docker deployment guide with troubleshooting and production tips
- `DOCKER_QUICKREF.md` - Quick Docker command reference
- `docs/E2E_TESTING.md` - End-to-end testing documentation
- `.env.example` - Environment variable template with all configuration options

## Common Development Patterns

### Adding a new AI operation:
1. Add prompt template to appropriate service (`ai_generator.py` or `ai_editor.py`)
2. Create API endpoint in `backend/api/` with Pydantic schema
3. Use `generate_with_ai()` helper function or `AIProviderFactory`
4. Add corresponding frontend API call in `services/api.ts`
5. Wire up UI component to call the API

### Adding a new template field:
1. Update `STANDARD_FIELDS` in `backend/services/template_parser.py`
2. Add field to Pydantic schemas in `backend/models/schemas.py`
3. Update TypeScript types in `frontend/src/types/index.ts`
4. Add to generation prompt in `ai_generator.py`

### Running background tasks:
```python
from backend.services.background_runner import run_in_background

# Start task in background (returns thread immediately)
run_in_background(
    processor.process_batch_task(task_id),
    name=f"batch-task-{task_id}",
)
```

### Debugging template rendering:
- Use `test_docxtpl.py` to compare template vs output structure
- Check that template uses correct Jinja2 syntax
- Verify data structure matches template variables
- Ensure using `docxtpl.DocxTemplate`, not `docx.Document`

### Working with batch generation:
- Chapter templates are cached in `course_chapter_templates` table
- Use `ChapterSplitter` for AI-powered chapter splitting
- Batch tasks run in background via `BackgroundTaskRunner`
- Document grouping is configurable (default 2 lessons per document)
- Progress can be polled via `GET /batch/tasks/{task_id}`

### Cross-platform Development:
- Always use `pathlib.Path` for file path operations
- Use `platform.system()` to detect OS: "Windows", "Linux", "Darwin" (macOS)
- Virtual environment paths: `venv/Scripts/` (Windows) vs `venv/bin/` (Linux/Mac)
- Shell commands:
  - Windows: Use `.bat` files with `@echo off`, `tasklist`, `taskkill`, `netstat`
  - Linux/Mac: Use `.sh` files with `ps`, `netstat`, `kill`
- Management scripts available in project root for both platforms
