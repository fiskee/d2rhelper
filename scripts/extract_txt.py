#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from d2rhelper.casc import CASCLIB_PATH, KNOWN_TXT_FILES, CascStorage, find_d2r_path
from d2rhelper.game_data import DEFAULT_DB_PATH, build_game_db


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract game data from Diablo II: Resurrected CASC archives into a SQLite database."
    )
    parser.add_argument(
        "--d2r-path",
        help="Path to D2R installation directory (default: auto-detect or $D2R_PATH)",
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to write the SQLite database to",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List known .txt files without extracting",
    )
    parser.add_argument(
        "files",
        nargs="*",
        default=None,
        help="Specific .txt files to extract (default: all known files)",
    )

    args = parser.parse_args()

    if args.list:
        for f in KNOWN_TXT_FILES:
            print(f)
        return

    d2r_path = args.d2r_path or find_d2r_path()
    if not d2r_path:
        print(
            "Error: Cannot find D2R installation. Set D2R_PATH env var or use --d2r-path.",
            file=sys.stderr,
        )
        sys.exit(1)

    filter_files = set(args.files) if args.files else None

    file_data: dict[str, bytes] = {}
    with CascStorage(d2r_path) as storage:
        for filename in KNOWN_TXT_FILES:
            if filter_files and filename not in filter_files:
                continue
            casc_path = f"{CASCLIB_PATH}/{filename}"
            try:
                data = storage.read_file(casc_path)
                file_data[filename] = data
            except FileNotFoundError:
                print(f"Warning: file not found in CASC: {filename}", file=sys.stderr)
                continue

    if not file_data:
        print("No files were extracted.", file=sys.stderr)
        sys.exit(1)

    db_path = Path(args.db_path)
    build_game_db(file_data, db_path)

    print(f"Built database at {db_path.resolve()} with {len(file_data)} tables:")
    for name in sorted(file_data):
        print(f"  {Path(name).stem}")


if __name__ == "__main__":
    main()
