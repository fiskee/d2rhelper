# d2rhelper

Parse Diablo II: Resurrected offline save files and generate LLM-ready character context.

Inspired by [d2rsavegameparser](https://github.com/Paladijn/d2rsavegameparser/). CASC extraction powered by [CascLib](https://github.com/ladislav-zezula/CascLib).

All D2R game data tables (items, skills, runewords, properties, etc.) are extracted from the game's CASC archives into a SQLite database at `src/d2rhelper/data/game.db` via the included extraction script.

## Setup

```bash
uv sync
```

## Extract game data files

Build the SQLite database from D2R's CASC archives. This step requires a local Diablo II: Resurrected installation.

```bash
uv run python scripts/extract_txt.py
```

The script auto-detects your D2R installation. It searches in order:

1. `$D2R_PATH` environment variable (or `--d2r-path`)
2. Windows native install paths (`C:/Program Files (x86)`, `C:/Program Files`) when running on Windows
3. Steam library paths (Linux, Windows Steam, Proton compatdata)
4. Wine prefix directories (`~/.wine`, `~/.local/share/wineprefixes`)
5. Fallback: `find` from `$HOME`

Save-file auto-detection prefers likely save folders first (native Windows `%USERPROFILE%/Saved Games/Diablo II Resurrected`, then Proton/Wine roots), and only falls back to broad `C:/` or `D:/` recursive scan on Windows if no saves are found.

CascLib shared libraries for Linux (`.so`) and Windows (`.dll`) are included in the project. To rebuild them:

**Linux / macOS (native):**
```bash
bash scripts/build_casclib.sh
```

**Windows (native):**
```bat
scripts\build_casclib.bat
```

**Linux → Windows (cross-compile):**
```bash
bash scripts/build_casclib.sh windows
```

Build requirements:

| Target                 | Requirements                                                   |
|------------------------|----------------------------------------------------------------|
| Linux native           | `git`, `cmake`, `gcc`                                          |
| macOS native           | `git`, `cmake`, Xcode Command Line Tools                       |
| Windows native         | `git`, `cmake`, Visual Studio (MSVC) or MinGW                  |
| Windows cross-compile  | `git`, `cmake`, `x86_64-w64-mingw32-gcc` (mingw-w64)          |

If you need to rebuild the database after a game update, re-run the extraction script.

## Development Commands

Run lint checks:

```bash
uv run ruff check src tests
```

Run tests:

```bash
uv run pytest -q
```

Run both in one go:

```bash
uv run ruff check src tests && uv run pytest -q
```

## Architecture

Game data is stored in a SQLite database (`src/d2rhelper/data/game.db`) built at extraction time. All lookups - skills, items, runewords, properties, player classes - go through `GameData` in `src/d2rhelper/game_data.py`.

The item parsing pipeline is split into focused components:

- `src/d2rhelper/item_parser.py` - orchestration and public parser API (`ItemParser`)
- `src/d2rhelper/item_recovery.py` - bitstream recovery and re-sync heuristics
- `src/d2rhelper/item_properties.py` - item property decoding/formatting/combining
- `src/d2rhelper/item_rules.py` - item metadata rules (requirements, names, damage, runewords)

Character and stash parsing entry points remain:

- `src/d2rhelper/parser.py` - `.d2s` character parsing
- `src/d2rhelper/shared_stash_parser.py` - `.d2i` shared stash parsing

## Parse a character save

```bash
uv run d2rhelper parse-character "/path/to/Character.d2s" --db d2rhelper.db --json
```

This creates an immutable snapshot row in SQLite and stores the normalized character payload.

## Parse a shared stash file

```bash
uv run d2rhelper parse-stash "/path/to/SharedStashSoftCoreV2.d2i" --json
```

## Launch a local character UI

```bash
uv run d2rhelper ui
```

This auto-detects your latest local `.d2s` in Steam/Proton and serves a web UI at `http://127.0.0.1:8765`.

Or specify a file:

```bash
uv run d2rhelper ui --file "/path/to/Character.d2s"
```

## Generate LLM context JSON

```bash
uv run d2rhelper llm-json -o d2r_context.json
```

## Generate the full system prompt (for external LLM chat)

```bash
uv run d2rhelper prompt -o system_prompt.txt
```

Paste the output as the system message in your platform of choice to get grounded, inventory-aware D2R advice.

## Chat directly with Gemini Flash 3.5

```bash
cp .env.example .env
# Edit .env to add your GEMINI_API_KEY (and optionally GEMINI_MODEL)
uv run d2rhelper chat
```

This starts an interactive chat with Gemini Flash 3.5 by default, pre-loaded with your character context. Set `GEMINI_MODEL` to override the model. Type `quit` to exit, `clear` to reset the conversation.
