# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Intelligent Lesson Plan Assistant - An AI-powered lesson plan generation and editing tool. This is a full-stack application with a FastAPI backend, React/TypeScript frontend, and optional Electron desktop wrapper.

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

## Architecture

### Backend Architecture

**API Layer** (`backend/api/`):
- `templates.py` - Template upload, list, delete, preview
- `generate.py` - AI-powered lesson plan generation
- `edit.py` - AI content optimization (optimize, expand, rewrite)
- `documents.py` - Document download and management
- `settings.py` - Application settings management

**Service Layer** (`backend/services/`):
- `ai_provider.py` - **Multi-provider AI abstraction**. Supports both DeepSeek and Anthropic Claude via factory pattern. Each provider implements the `AIProvider` interface with `generate()` method.
- `ai_generator.py` - Lesson plan generation using AI. Constructs prompts and parses structured JSON responses.
- `ai_editor.py` - Content editing operations (optimize, expand, rewrite)
- `template_parser.py` - **Parses Word templates for Jinja2 variables** (`{{ variable }}`), loops (`{% for %}`), and conditionals (`{% if %}`). Extracts field configurations.
- `document_renderer.py` - **Critical**: Uses `docxtpl` (not python-docx) for template rendering to preserve document structure. See WORD_EXPORT_FIX.md for details.
- `document_modifier.py` - Modifies existing Word documents
- `lesson_plan_parser.py` - Parses lesson plan content

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
- `generatorStore.ts` - Lesson plan generation workflow
- `editorStore.ts` - Rich text editing state
- `settingsStore.ts` - Application settings

**Services** (`frontend/src/services/`):
- `api.ts` - Main API client (template, generation, AI editing endpoints)
- `settingsApi.ts` - Settings API client
- `fileService.ts` - File operations (download, save)

**Pages** (`frontend/src/pages/`):
- `Home.tsx` - Landing page
- `TemplateManager.tsx` - Upload and manage templates
- `NewLessonPlan.tsx` - Multi-step lesson plan generation wizard
- `EditLessonPlan.tsx` - Rich text editor with TipTap
- `LessonPlanDetail.tsx` - View generated lesson plans
- `History.tsx` - Previous lesson plans
- `Settings.tsx` - AI provider and API key configuration

### Storage Structure

```
storage/
├── templates/      # User-uploaded .docx templates
├── uploads/        # Temporary upload files
├── outputs/        # Generated .docx documents
└── database.db     # SQLite database
```

## Key Technical Details

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

## Database

SQLite database at `storage/database.db`:
- `templates` table - Template metadata and field configurations
- `lesson_plans` table - Generated lesson plan records
- Async operations via aiosqlite
- Auto-initialized on app startup via `lifespan` context manager

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

### Debugging template rendering:
- Use `test_docxtpl.py` to compare template vs output structure
- Check that template uses correct Jinja2 syntax
- Verify data structure matches template variables
- Ensure using `docxtpl.DocxTemplate`, not `docx.Document`
