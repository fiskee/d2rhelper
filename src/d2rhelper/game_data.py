from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "game.db"

_instances: dict[Path, GameData] = {}


def _sanitize_column(name: str) -> str:
    name = name.strip()
    if not name:
        return "_blank"
    name = name.lower()
    name = name.replace("*", "x_")
    name = re.sub(r"[ .\-]", "_", name)
    name = re.sub(r"__+", "_", name)
    name = name.strip("_")
    if not name:
        return "_blank"
    if name[0].isdigit():
        name = "c_" + name
    return name


def _dedup_columns(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    result: list[str] = []
    for name in names:
        if name in seen:
            seen[name] += 1
            result.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 0
            result.append(name)
    return result


def _parse_tsv(text: str) -> tuple[list[str], list[list[str]]]:
    lines = text.splitlines()
    if not lines:
        return [], []
    original_headers = lines[0].split("\t")
    rows: list[list[str]] = []
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        values = line.split("\t")
        rows.append(values)
    return original_headers, rows


def build_game_db(file_data: dict[str, bytes], db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")

    conn.execute(
        "CREATE TABLE IF NOT EXISTS _meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    conn.execute("DELETE FROM _meta WHERE key LIKE 'headers:%'")

    for filename, raw_bytes in file_data.items():
        table_name = Path(filename).stem
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            continue

        original_headers, rows = _parse_tsv(text)
        if not original_headers:
            continue

        sanitized = _dedup_columns([_sanitize_column(h) for h in original_headers])

        conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')

        col_defs = ", ".join(f'"{c}" TEXT' for c in sanitized)
        conn.execute(f'CREATE TABLE "{table_name}" ({col_defs})')

        conn.execute(
            "INSERT OR REPLACE INTO _meta VALUES (?, ?)",
            (f"headers:{table_name}", json.dumps(original_headers)),
        )

        placeholders = ", ".join("?" for _ in sanitized)
        quoted_cols = ", ".join(f'"{c}"' for c in sanitized)
        sql = f'INSERT INTO "{table_name}" ({quoted_cols}) VALUES ({placeholders})'

        batch: list[list[str]] = []
        for row in rows:
            padded = list(row) + [""] * (len(sanitized) - len(row))
            batch.append(padded[: len(sanitized)])
            if len(batch) >= 500:
                conn.executemany(sql, batch)
                batch.clear()
        if batch:
            conn.executemany(sql, batch)

    conn.execute("INSERT OR REPLACE INTO _meta VALUES ('db_version', '1')")
    conn.commit()
    conn.close()


def build_game_db_from_txt(txt_dir: str | Path, db_path: Path) -> None:
    txt_dir = Path(txt_dir)
    file_data: dict[str, bytes] = {}
    for file_path in sorted(txt_dir.glob("*.txt")):
        file_data[file_path.name] = file_path.read_bytes()
    build_game_db(file_data, db_path)


class GameData:
    def __init__(self, db_path: str | Path | None = None) -> None:
        db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        if not db_path.exists():
            raise FileNotFoundError(
                f"Game data database not found at {db_path}. "
                "Run the extraction script to build it from your D2R installation."
            )
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._headers: dict[str, list[str]] = {}
        self._load_headers()

        self._tooltips: dict[str, str] = self._build_tooltips()
        self._runewords: dict[str, dict[str, str]] = self._build_runewords()
        self._unique_names: dict[int, str] = self._build_unique_names()
        self._set_names: dict[int, str] = self._build_set_names()

    @classmethod
    def get_instance(cls, db_path: str | Path | None = None) -> GameData:
        path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        if path not in _instances:
            _instances[path] = cls(path)
        return _instances[path]

    def _load_headers(self) -> None:
        rows = self.conn.execute(
            "SELECT key, value FROM _meta WHERE key LIKE 'headers:%'"
        ).fetchall()
        for row in rows:
            table = row["key"].removeprefix("headers:")
            self._headers[table] = json.loads(row["value"])

    def _row_to_dict(self, row: sqlite3.Row, table: str) -> dict[str, str]:
        headers = self._headers.get(table, [])
        result: dict[str, str] = {}
        for i, header in enumerate(headers):
            if i < len(row):
                result[header] = str(row[i])
            else:
                result[header] = ""
        return result

    def _build_tooltips(self) -> dict[str, str]:
        rows = self.conn.execute("SELECT * FROM properties").fetchall()
        if not rows:
            return {}
        headers = self._headers.get("properties", [])
        stat_indices = [i for i, h in enumerate(headers) if h.startswith("stat")]
        try:
            tooltip_idx = headers.index("*Tooltip")
        except ValueError:
            return {}
        result: dict[str, str] = {}
        for row in rows:
            tooltip = str(row[tooltip_idx])
            if not tooltip:
                continue
            for idx in stat_indices:
                val = str(row[idx])
                if val:
                    result.setdefault(val, tooltip)
        return result

    def _build_runewords(self) -> dict[str, dict[str, str]]:
        rows = self.conn.execute("SELECT * FROM runes").fetchall()
        result: dict[str, dict[str, str]] = {}
        for row in rows:
            if row["complete"] != "1":
                continue
            rune_str = row["x_runesused"]
            if not rune_str:
                continue
            result[rune_str] = {
                "id": row["name"],
                "name": row["x_rune_name"],
                "rune_string": rune_str,
            }
        return result

    def _build_unique_names(self) -> dict[int, str]:
        rows = self.conn.execute(
            "SELECT * FROM uniqueitems WHERE \"spawnable\" = '1'"
        ).fetchall()
        result: dict[int, str] = {}
        for row in rows:
            uid = row["x_id"]
            if not uid:
                continue
            result[int(uid)] = row["index"]
        return result

    def _build_set_names(self) -> dict[int, str]:
        rows = self.conn.execute("SELECT * FROM setitems").fetchall()
        result: dict[int, str] = {}
        for row in rows:
            sid = row["x_id"]
            if not sid:
                continue
            result[int(sid)] = row["index"]
        return result

    def skill_name(self, skill_id: int) -> str | None:
        row = self.conn.execute(
            'SELECT "skill" FROM skills WHERE "x_id" = ?', (skill_id,)
        ).fetchone()
        if row is None:
            return None
        return row["skill"]

    def skill_class_name(self, skill_id: int) -> str | None:
        row = self.conn.execute(
            'SELECT pc."player_class" FROM skills s '
            'JOIN playerclass pc ON pc."code" = s."charclass" '
            'WHERE s."x_id" = ?',
            (skill_id,),
        ).fetchone()
        if row is None:
            return None
        return row["player_class"]

    def skill_offsets(self, class_name: str) -> list[tuple[int, str]]:
        char_row = self.conn.execute(
            'SELECT "code" FROM playerclass WHERE "player_class" = ?',
            (class_name,),
        ).fetchone()
        if char_row is None:
            return []
        char_code = char_row["code"]
        rows = self.conn.execute(
            'SELECT "skill" FROM skills WHERE "charclass" = ? ORDER BY CAST("x_id" AS INTEGER)',
            (char_code,),
        ).fetchall()
        return [(i, r["skill"]) for i, r in enumerate(rows)]

    def class_name_by_id(self, class_id: int) -> str | None:
        classes = self.player_classes()
        if 0 <= class_id < len(classes):
            return classes[class_id][1]
        return None

    def player_classes(self) -> list[tuple[int, str, str]]:
        rows = self.conn.execute(
            'SELECT "player_class", "code" FROM playerclass '
            'WHERE "code" != \'\' ORDER BY rowid'
        ).fetchall()
        return [(i, r["player_class"], r["code"]) for i, r in enumerate(rows)]

    def weapon_by_code(self, code: str) -> dict[str, str] | None:
        return self._lookup_by_code("weapons", code)

    def armor_by_code(self, code: str) -> dict[str, str] | None:
        return self._lookup_by_code("armor", code)

    def misc_by_code(self, code: str) -> dict[str, str] | None:
        return self._lookup_by_code("misc", code)

    def _lookup_by_code(self, table: str, code: str) -> dict[str, str] | None:
        row = self.conn.execute(
            f'SELECT * FROM "{table}" WHERE "code" = ?', (code,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_dict(row, table)

    def item_stat_cost(self, stat_id: int) -> dict[str, str] | None:
        row = self.conn.execute(
            'SELECT * FROM itemstatcost WHERE "x_id" = ?', (stat_id,)
        ).fetchone()
        if row is None:
            return None
        save_add = int(row["save_add"] or 0)
        if save_add == -1:
            save_add = 0
        return {
            "id": str(stat_id),
            "stat": row["stat"],
            "save_bits": str(int(row["save_bits"] or 0)),
            "save_add": str(save_add),
            "save_param_bits": str(int(row["save_param_bits"] or -1)),
            "desc_priority": str(int(row["descpriority"] or 0)),
            "desc_str_pos": row["descstrpos"],
        }

    def runeword_by_string(self, rune_string: str) -> dict[str, str] | None:
        return self._runewords.get(rune_string)

    def property_tooltip(self, stat: str) -> str | None:
        return self._tooltips.get(stat)

    def unique_name(self, uid: int) -> str | None:
        return self._unique_names.get(uid)

    def set_name(self, sid: int) -> str | None:
        return self._set_names.get(sid)

    def hireling_by_id(self, type_id: int) -> dict[str, str] | None:
        row = self.conn.execute(
            'SELECT * FROM hireling WHERE "id" = ? LIMIT 1', (str(type_id),)
        ).fetchone()
        if row is None:
            return None
        skills = []
        for col in ("skill1", "skill2", "skill3", "skill4", "skill5", "skill6"):
            val = (row[col] or "").strip()
            if val:
                skills.append(val)
        return {
            "hireling": row["hireling"] or "",
            "x_subtype": row["x_subtype"] or "",
            "skills": skills,
        }
