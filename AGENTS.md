# Repository Guidelines

## Project Structure & Module Organization
- `app.py` (Streamlit UI), `main.py` (CLI pipeline). Variants: `app_minimal.py`, `app_improved.py`.
- `modules/`: core logic — `downloader.py`, `transcriber.py`, `analyzer.py`, `video_processor.py`, `subtitle_generator.py`.
- `utils/`: helpers and shared utilities.
- `config.py`: user‑tunable defaults (provider, clip lengths, quality).
- `downloads/`, `transcripts/`, `outputs/`: generated artifacts; do not commit.
- `requirements.txt`, `.env.example`, `.env` (local only).

## Build, Test, and Development Commands
- Create env and install: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
- Verify FFmpeg: `ffmpeg -version`.
- Run UI: `streamlit run app.py` → http://localhost:8501.
- Run CLI: `python main.py --url "https://youtu.be/..." --clips 3 --provider ollama`.
- Configure keys: `cp .env.example .env` and set `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` as needed.

## Coding Style & Naming Conventions
- Python 3.8+, 4‑space indentation, follow PEP 8 and use type hints.
- Names: functions/modules `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE` (see `config.py`).
- Keep UI concerns in `app*.py`; keep pure, testable logic in `modules/`.
- Prefer small functions, clear docstrings, and explicit returns over side effects.

## Testing Guidelines
- Framework: pytest (recommended). Place tests in `tests/`, named `test_*.py` (e.g., `tests/test_analyzer.py`).
- Focus on unit tests for `modules/`; mock network/LLM calls and isolate FFmpeg.
- Run tests: `pytest -q`. For slow/video tests, mark with `@pytest.mark.slow` and skip by default.

## Commit & Pull Request Guidelines
- Commits: imperative, concise subject (≤ 72 chars). Examples: `add streamlit UI`, `add subtitle styles`, `french language compatibility`.
- Reference issues in body (`Fixes #123`) and describe rationale/user impact.
- PRs must include: overview, before/after notes, run steps (`streamlit run app.py` or CLI command), screenshots for UI, and sample URL used.
- Avoid committing large binaries; exclude `downloads/`, `transcripts/`, `outputs/`.

## Security & Configuration Tips
- Never commit secrets; use `.env` (keep `.env.example` updated).
- Default safe settings in `config.py`; document any changes in PRs.
