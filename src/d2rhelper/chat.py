from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_SYSTEM_PROMPT = (Path(__file__).parent / "data" / "system_prompt.md").read_text(encoding="utf-8")
_DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"


def start_chat(context_json: str) -> None:
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not found in .env file.\n"
            "Copy .env.example to .env and add your Gemini API key from https://aistudio.google.com/apikey"
        )

    client = genai.Client(api_key=api_key)
    model_name = (os.getenv("GEMINI_MODEL") or _DEFAULT_GEMINI_MODEL).strip() or _DEFAULT_GEMINI_MODEL
    system_instruction = _SYSTEM_PROMPT.replace("{CONTEXT_JSON}", context_json)

    chat = client.chats.create(
        model=model_name,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
        ),
    )

    print("D2R Helper Chat — type 'quit' to exit, 'clear' to reset\n")

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if user_input.lower() == "clear":
            chat = client.chats.create(
                model=model_name,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                ),
            )
            print("Chat cleared. Context preserved.")
            continue

        print("\n", end="", flush=True)
        try:
            response = chat.send_message(user_input)
            print(response.text)
        except Exception as exc:
            print(f"Error: {exc}")
