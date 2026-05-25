# d2rhelper

Parse and explore your Diablo II: Resurrected offline save files.

Browse character gear, search items across all characters and stash, track set item completion, and chat with an AI assistant about builds and farming strategies.

## Quick start

You need [Python 3.12+](https://www.python.org/downloads/), [git](https://git-scm.com/downloads), and a local Diablo II: Resurrected installation.

```bash
git clone https://github.com/fiskee/d2rhelper.git
cd d2rhelper
bash scripts/setup.sh
```

On Windows use `scripts\setup.bat`.

The setup script installs uv, syncs dependencies, extracts game data, and copies `.env.example` to `.env`. After it finishes, get a free API key at [Google AI Studio](https://aistudio.google.com/apikey), add it to the `.env` file, then:

```bash
uv run d2rhelper
```

Open **http://127.0.0.1:8000** in your browser.

## Features

- **Dashboard** — character stats, 12-slot equipment grid, mercenary gear, inventory, belt, personal stash, and shared stash tabs
- **Search** — instant item search with word-boundary ranking, autocomplete suggestions, and an option to search across all loaded characters
- **Sets** — track set item completion across all characters and stash, see which pieces you own and where they are (equipped, inventory, personal stash, shared stash)
- **Chat** — AI assistant powered by Gemini that knows your characters, items, and stash. Ask about builds, farming strategies, runewords, and gear upgrades. Toggle to include all characters in a single chat session
- **Multiple characters** — switch between characters, search or compare across all loaded saves
- **Session persistence** — your selected character, search queries, chat history, and view state survive page reloads

## Credits

Inspired by [d2rsavegameparser](https://github.com/Paladijn/d2rsavegameparser/). CASC extraction powered by [CascLib](https://github.com/ladislav-zezula/CascLib).
