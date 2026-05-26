# d2rhelper

This is a personal project, testing open source LLMs, feel free to use and do whatever you want, I did not write a single line of code.

Parse and explore your Diablo II: Resurrected offline save files.

Browse character gear, search items across all characters and stash, track set item completion, and chat with an AI assistant about builds and farming strategies.

## Quick start

You need [Python 3.12+](https://www.python.org/downloads/), [Node.js](https://nodejs.org/), [git](https://git-scm.com/downloads), and a local Diablo II: Resurrected installation.

```bash
git clone https://github.com/fiskee/d2rhelper.git
cd d2rhelper
bash scripts/setup.sh
```

On Windows use `scripts\setup.bat`.

The setup script installs uv, syncs dependencies, extracts game data, builds the frontend, and copies `.env.example` to `.env`. After it finishes, get a free API key at [Google AI Studio](https://aistudio.google.com/apikey), add it to the `.env` file, then:

```bash
uv run d2rhelper
```

Open **http://127.0.0.1:8000** in your browser.

## Features

- **Dashboard** - character stats, 12-slot equipment grid, mercenary gear, inventory, belt, personal stash, and shared stash tabs
- **Search** - instant item search with word-boundary ranking, autocomplete suggestions, and an option to search across all loaded characters
- **Sets** - track set item completion across all characters and stash, see which pieces you own and where they are (equipped, inventory, personal stash, shared stash)
- **Chat** - AI assistant powered by Gemini that knows your characters, items, and stash. Ask about builds, farming strategies, runewords, and gear upgrades. Toggle to include all characters in a single chat session

### Chat modes

When creating a new chat you can pick between two modes:

- **Tools** — the assistant uses tool calls to fetch character overview, search items, and get details on demand. This keeps the conversation lean and works well for targeted questions. The system prompt includes tool instructions instead of raw character JSON.
- **Full Context** — the entire character and stash snapshot is injected into the system prompt at the start of the chat. Best for broad, open-ended explorations where the assistant needs everything upfront, at the cost of a much larger prompt.

The default mode can be set with the `D2RHELPER_CHAT_MODE` environment variable (`tools` or `full_context`).
- **Multiple characters** - switch between characters, search or compare across all loaded saves
- **Session persistence** - your selected character, search queries, chat history, and view state survive page reloads

## Credits

Inspired by [d2rsavegameparser](https://github.com/Paladijn/d2rsavegameparser/). CASC extraction powered by [CascLib](https://github.com/ladislav-zezula/CascLib).
