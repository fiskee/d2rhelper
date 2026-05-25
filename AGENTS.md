# AGENTS.md

## Fast ramp-up
- Python package lives in `src/d2rhelper`; CLI entrypoint is `d2rhelper` (`uv run d2rhelper ...`).
- API server is `src/d2rhelper/api.py`; `d2rhelper` mounts `frontend/dist` only if it exists, otherwise API-only mode.
- Frontend is a separate Vite+React+TS app in `frontend/`; dev server proxies `/api` + WS to `http://localhost:8000`.

## Verified dev commands
- Install backend deps: `uv sync`.
- Backend lint: `uv run ruff check src tests`.
- Backend tests: `uv run pytest -q`.
- Frontend install: `npm --prefix frontend install`.
- Frontend checks/build: `npm --prefix frontend run lint` and `npm --prefix frontend run build`.
- Full-stack dev: run `uv run d2rhelper --reload` and `npm --prefix frontend run dev` in parallel.

## Data and environment gotchas
- Chat endpoints require `GEMINI_API_KEY` in `.env`; `api.py` calls `load_dotenv()` at import time.
- `src/d2rhelper/data/game.db` is required for lookups/parsing tests; regenerate with `uv run python scripts/extract_txt.py` (needs local Diablo II: Resurrected install or `D2R_PATH`).
- `scripts/extract_txt.py` and save-file auto-detection do broad filesystem probing as a fallback; avoid running casually in CI/sandboxed environments.

## Test expectations
- Tests use real fixtures in `tests/resources` (including `.d2s`/`.d2i`) and assert concrete parsed values; parser changes usually require updating many expectations.
- No separate typecheck/test runner config exists beyond package scripts; use the commands above as source of truth.

## Scope boundaries
- Backend parsing/domain logic is concentrated in `parser.py`, `shared_stash_parser.py`, `item_parser.py`, `item_properties.py`, `item_recovery.py`, and `item_rules.py`.
- `scripts/build_casclib.sh` / `.bat` rebuild bundled CascLib binaries (`libcasc.so`, `Casclib.dll`); do not touch unless working on CASC extraction/runtime loading.
