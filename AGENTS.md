# AGENTS.md

## Fast ramp-up
- Python package lives in `src/d2rhelper`; CLI entrypoint is `d2rhelper` (`uv run d2rhelper ...`).
- API routes are in `src/d2rhelper/api.py`; major logic is in `src/d2rhelper/services/` (`chat_ws.py`, `search.py`, `parse.py`, `item_lookup.py`, `sets.py`, `game_data_provider.py`).
- `d2rhelper` mounts `frontend/dist` only if it exists; otherwise it runs API-only mode.
- Frontend is a separate Vite+React+TS app in `frontend/`; dev server proxies `/api` + WS to `http://localhost:8000`.

## Verified dev commands
- Install backend deps: `uv sync`.
- Backend lint: `uv run ruff check src tests`.
- Backend tests: `uv run pytest -q`.
- Frontend install: `npm --prefix frontend install`.
- Frontend checks/build: `npm --prefix frontend run lint` and `npm --prefix frontend run build`.
- Full-stack dev: run `uv run d2rhelper --reload` and `npm --prefix frontend run dev` in parallel.

## Data and environment gotchas
- Chat websocket requires `GEMINI_API_KEY` in `.env`; missing key returns immediate WS error and closes.
- Default chat mode is `tools`; override with `D2RHELPER_CHAT_MODE=tools|full_context`.
- `.env` is loaded at API import time (`load_dotenv()` in `api.py`).
- `src/d2rhelper/data/game.db` is required for lookups/parsing tests; regenerate with `uv run python scripts/extract_txt.py` (needs local Diablo II: Resurrected install or `D2R_PATH`).
- `scripts/extract_txt.py` and save-file auto-detection do broad filesystem probing as a fallback; avoid running casually in CI/sandboxed environments.

## Test expectations
- Tests use real fixtures in `tests/resources` (including `.d2s`/`.d2i`) and assert concrete parsed values; parser changes usually require updating many expectations.
- API coverage includes websocket flows in `tests/test_api.py` with mocked `google.genai`; avoid breaking WS event shapes (`thinking`, `tool_call`, `tool_result`, `text`, `done`) without updating tests.

## Scope boundaries
- Backend parsing/domain logic is concentrated in `parser.py`, `shared_stash_parser.py`, `item_parser.py`, `item_properties.py`, `item_recovery.py`, and `item_rules.py`.
- `scripts/build_casclib.sh` / `.bat` rebuild bundled CascLib binaries (`libcasc.so`, `Casclib.dll`); do not touch unless working on CASC extraction/runtime loading.

## Frontend persisted storage
- The Zustand store persists state to IndexedDB via `idb-keyval` under the key `d2rhelper-chat-storage-v2` (`frontend/src/store/appStore.ts`).
- Whenever the data schema changes (new fields added to models like `D2Character`, `Mercenary`, `QuestData`, etc. that are serialized into the store), bump the storage name suffix (e.g. `-v2` → `-v3`) to avoid crashes from stale cached data missing new fields.

## Chat wiring hotspots
- Frontend chat transport/state machine is in `frontend/src/components/Chat/useChatConnection.ts`; keep reconnect logic separate from context refresh.
- Frontend context payload + item id mapping is in `frontend/src/components/Chat/contextBuilder.ts`; IDs are persisted per chat (`itemIdIndex`, `itemStashTabIndex`) and must stay stable for item links/tool calls.
