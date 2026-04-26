# Agent Instructions

## Package Management
- Use `uv` exclusively. Never use `pip` or `requirements.txt`.
- After dependency changes, run `uv sync`.
- Playwright browser install: `uv run playwright install chromium`

## Running
- Entry point: `uv run python main.py`
- Tests: `uv run pytest` (add `-v` for verbose)
- Requires `.env` with at least `API_KEY` set.

## Architecture
- `main.py` delegates to `app.core.run()`.
- `app/config.py` loads settings from `.env` via `dotenv`; `get_settings()` is `@lru_cache(maxsize=1)`.
- `app/browser.py` manages Playwright Chromium and persists auth state to `auth_state.json`.
- Scrapers (`app/hh_scraper.py`, `app/habr_scraper.py`) subclass `app/base_scraper.py`.
- `app/vacancy_processor.py` uses an LLM to filter vacancies by profession and generate cover letters.
- All processing is sequential.

## Key Files / State
- `.env` — environment config (not committed).
- `auth_state.json` — saved browser session (not committed). Delete to force re-login.
- `data.json` — list of already-processed vacancy URLs (not committed).
- `resume.txt` — user resume text used in LLM prompts (not committed).
- `prompt.txt` — instructions/template for AI-generated responses (not committed).

## Testing Quirks
- `get_settings()` is cached. Tests use a fixture (`clear_settings_cache`) that calls `get_settings.cache_clear()` before/after each test. If writing new config-related tests, clear the cache or you’ll get stale values.
- Many tests rely heavily on `unittest.mock` and `tmp_path`.

## Operational Gotchas
- Scrapers depend on current site DOM/layout for hh.ru and career.habr.com. UI changes can break selectors without any code changes.
- Default LLM endpoint is `https://routerai.ru/api/v1` with model `stepfun/step-3.5-flash:free`. Override via `.env` (`API_BASE_URL`, `MODEL`).
- `HEADLESS` defaults to `true` in code but is often set to `false` in `.env` for debugging.
- `RESPONSE_LIMIT_PER_PLATFORM` defaults to `10`; empty string in `.env` means unlimited.
- The script skips vacancies that require answering employer questions.
