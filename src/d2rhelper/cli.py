from __future__ import annotations

import argparse
import json

from d2rhelper.db import persist_character_snapshot
from d2rhelper.llm_context import generate_llm_json
from d2rhelper.parser import CharacterParser
from d2rhelper.shared_stash_parser import SharedStashParser
from d2rhelper.ui import find_local_character_file, find_local_shared_stash_file, start_ui_server


def main() -> None:
    parser = argparse.ArgumentParser(prog="d2rhelper")
    sub = parser.add_subparsers(dest="command", required=True)

    parse_character = sub.add_parser("parse-character")
    parse_character.add_argument("file", help="Path to .d2s save file")
    parse_character.add_argument("--db", default="d2rhelper.db", help="SQLite DB path")
    parse_character.add_argument("--json", action="store_true", help="Print parsed JSON")

    parse_stash = sub.add_parser("parse-stash")
    parse_stash.add_argument("file", help="Path to .d2i shared stash file")
    parse_stash.add_argument("--json", action="store_true", help="Print parsed JSON")

    ui = sub.add_parser("ui")
    ui.add_argument("--file", help="Path to .d2s file (auto-detect if omitted)")
    ui.add_argument("--host", default="127.0.0.1")
    ui.add_argument("--port", type=int, default=8765)

    llm_json_parser = sub.add_parser("llm-json")
    llm_json_parser.add_argument("--file", help="Path to .d2s file (auto-detect if omitted)")
    llm_json_parser.add_argument("--stash", help="Path to .d2i file (auto-detect if omitted)")
    llm_json_parser.add_argument("--output", "-o", help="Output JSON file path")

    prompt_parser = sub.add_parser("prompt")
    prompt_parser.add_argument("--file", help="Path to .d2s file (auto-detect if omitted)")
    prompt_parser.add_argument("--stash", help="Path to .d2i file (auto-detect if omitted)")
    prompt_parser.add_argument("--output", "-o", help="Output file path (prints to stdout if omitted)")

    chat_parser = sub.add_parser("chat")
    chat_parser.add_argument("--file", help="Path to .d2s file (auto-detect if omitted)")
    chat_parser.add_argument("--stash", help="Path to .d2i file (auto-detect if omitted)")

    args = parser.parse_args()

    def _resolve_character_file(path_arg: str | None) -> str:
        if path_arg:
            return path_arg
        detected = find_local_character_file()
        if detected is None:
            raise SystemExit("Could not auto-detect local .d2s file, use --file")
        return str(detected)

    if args.command == "parse-character":
        character = CharacterParser().parse_file(args.file)
        snapshot_id = persist_character_snapshot(args.db, args.file, character)
        if args.json:
            print(json.dumps(character.model_dump(mode="json"), indent=2))
        print(f"Saved character snapshot {snapshot_id} to {args.db}")
    elif args.command == "parse-stash":
        tabs = SharedStashParser().parse_file(args.file)
        if args.json:
            print(json.dumps([tab.model_dump(mode="json") for tab in tabs], indent=2))
        print(f"Parsed {len(tabs)} shared stash tabs from {args.file}")
    elif args.command == "ui":
        character_file = args.file
        if not character_file:
            detected = find_local_character_file()
            if detected is None:
                raise SystemExit("Could not auto-detect local .d2s file, use --file")
            character_file = str(detected)
        start_ui_server(character_file, host=args.host, port=args.port)
    elif args.command == "llm-json":
        char_file = _resolve_character_file(args.file)
        stash_file = args.stash
        if stash_file is None:
            detected = find_local_shared_stash_file()
            stash_file = str(detected) if detected else None
        output = generate_llm_json(char_file, stash_file, args.output)
        if not args.output:
            print(output)
    elif args.command == "prompt":
        from pathlib import Path

        char_file = _resolve_character_file(args.file)
        stash_file = args.stash
        if stash_file is None:
            detected = find_local_shared_stash_file()
            stash_file = str(detected) if detected else None
        context = generate_llm_json(char_file, stash_file)
        prompt_template = Path(__file__).parent / "data" / "system_prompt.md"
        prompt = prompt_template.read_text(encoding="utf-8").replace("{CONTEXT_JSON}", context)
        if args.output:
            Path(args.output).write_text(prompt, encoding="utf-8")
            print(f"Prompt written to {args.output}")
        else:
            print(prompt)
    elif args.command == "chat":
        from d2rhelper.chat import start_chat

        char_file = _resolve_character_file(args.file)
        stash_file = args.stash
        if stash_file is None:
            detected = find_local_shared_stash_file()
            stash_file = str(detected) if detected else None
        context = generate_llm_json(char_file, stash_file)
        start_chat(context)
