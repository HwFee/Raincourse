# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Raincourse is a 长江雨课堂 (Changjiang Rain Classroom) AI learning assistant that provides:
- WeChat QR code login with session persistence
- Course and assignment listing
- AI-powered exam answering (multiple model support)
- Question export (JSON/CSV/Excel/Markdown)
- GUI + CLI dual entry points

## Commands

### Running the Application
```bash
# GUI version (recommended)
pythonw gui.py
# or use the batch file
run_gui.bat

# CLI version
python main.py

# Debug mode (GUI with console output)
python gui.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Building EXE
```bash
build.bat
```

## Architecture

### Entry Points
- **gui.py** — GUI entry using `pywebview`. Hosts a `API` class exposed to the frontend via JavaScript bridge.
- **main.py** — CLI entry using `rich` for console UI.

### Core Modules

**`api/api.py`** — `RainAPI` class
- Wraps all 雨课堂 platform API calls (requests.Session-based)
- Methods: login, get_course_list, get_work, init_exam, get_all_question, post_test, etc.
- Uses WebSocket client for QR code login flow

**`utils/exam.py`** — Exam answering logic
- `do_work()` — Traditional answer-from-local-file mode
- `ai_do_work()` — AI-powered answering with retry, stop-event support, and report generation
- Both functions require the full API state chain: init_exam → get_token_work → get_exam_work_token → get_cache_work → get_all_question

**`utils/ai_solver.py`** — Multi-model AI solver
- Supports OpenAI-compatible and Anthropic-compatible APIs
- `AISolver.solve_question()` with retry logic

**`utils/api_config_manager.py`** — API key and provider configuration
- Manages multiple AI providers (MiniMax, OpenAI, Anthropic, DeepSeek, etc.)
- Persists to `config/api_configs.json`

**`utils/question_exporter.py`** — Export questions to JSON/CSV/Excel/Markdown

**`utils/seesion_io.py`** — Session persistence (login session storage)

**`logic.py`** — CLI menu handling (selects between features defined in utils)

### GUI Frontend
- `web/index.html` — Main HTML entry
- `web/js/app.js` — Frontend JavaScript communicating with pywebview bridge
- `web/css/style.css` — Styles

### Data Directories
- `user/` — Saved user sessions (JSON)
- `answer/` — Answer records and reports
- `exam/` — Exported exam questions/answers
- `exports/` — Exported files in various formats
- `config/` — API configuration JSON
- `logs/` — Runtime logs

## Key Patterns

### API Flow for Exam Answering
```
init_exam(course_id, work_id)
  → get_token_work / get_token_work_2 (depending on work type)
  → get_exam_work_token / get_exam_work_token_2
  → get_cache_work (already answered questions)
  → get_all_question (full question list)
  → post_test (submit answers)
```

### Work Types
- Type `5` — Regular homework (use `get_token_work`, `get_exam_work_token`)
- Type `20` — Exam activity (use `get_token_work_2`, `get_exam_work_token_2`, may need `get_pub_new_prob` first)

### GUI Backend Bridge
The `API` class in `gui.py` exposes methods to JavaScript via `@window.api.methodName`. Frontend calls these via `window.api.methodName(args)`.

### Question Types
```python
QUESTION_TYPE = {"1": "单选题", "2": "多选题", "3": "判断题", "4": "填空题"}
```

## Dependencies
- **pywebview** — GUI framework
- **requests** — HTTP client
- **rich** — CLI console formatting
- **websocket-client** — QR code login WebSocket
- **qrcode + Pillow** — QR code generation
- **openpyxl** — Excel export
