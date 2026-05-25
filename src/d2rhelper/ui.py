from __future__ import annotations

import html
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from d2rhelper.casc import find_latest_save_file
from d2rhelper.models import D2Character, ParsedItem, SharedStashTab
from d2rhelper.parser import CharacterParser
from d2rhelper.shared_stash_parser import SharedStashParser


def find_local_character_file() -> Path | None:
    return find_latest_save_file("d2s")


def find_local_shared_stash_file() -> Path | None:
    candidate = find_latest_save_file("d2i")
    if candidate and "SharedStash" in candidate.name:
        return candidate

    from d2rhelper.casc import find_d2_save_files

    files = []
    for f in find_d2_save_files("d2i"):
        if "SharedStash" in f.name:
            files.append(f)
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]


def start_ui_server(character_file: str, host: str = "127.0.0.1", port: int = 8765) -> None:
    character = CharacterParser().parse_file(character_file)
    shared_stash_file = find_local_shared_stash_file()
    shared_stash_tabs = SharedStashParser().parse_file(shared_stash_file) if shared_stash_file else []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/":
                self.send_response(404)
                self.end_headers()
                return

            body = render_character_page(character, character_file, shared_stash_file, shared_stash_tabs)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

    server = HTTPServer((host, port), Handler)
    print(f"UI running at http://{host}:{port}")
    print("Press Ctrl+C to stop")
    server.serve_forever()


def render_items_table(items: list[ParsedItem]) -> str:
    item_rows = []
    for item in items:
        stacks_display = f"x{item.stacks}" if item.stacks else "-"
        props = "<br>".join(
            html.escape(p.display_text or f"{p.name}: {p.values}") for p in item.properties if p.display_text != ""
        ) or "-"
        item_rows.append(
            "<tr>"
            f"<td>{item.index}</td>"
            f"<td>{'recovered' if item.recovered else ('ok' if item.parse_ok else 'failed')}</td>"
            f"<td>{html.escape(str(item.code))}</td>"
            f"<td>{html.escape(item.item_name or '-')}</td>"
            f"<td>{stacks_display}</td>"
            f"<td>{html.escape(item.runeword_name or item.unique_name or item.set_name or '-')}</td>"
            f"<td>{html.escape(item.weapon_damage or '-')}</td>"
            f"<td>{html.escape(', '.join(si.item_name or si.code or '?' for si in item.socketed_items) or '-')}</td>"
            f"<td>{item.quality.name}</td>"
            f"<td>{item.simple}</td>"
            f"<td>{item.identified}</td>"
            f"<td>{item.socketed}</td>"
            f"<td>{item.location}/{item.position}/{item.container}</td>"
            f"<td>{item.x},{item.y}</td>"
            f"<td>{item.level if item.level is not None else '-'}</td>"
            f"<td>{item.cnt_filled_sockets if item.cnt_filled_sockets is not None else '-'}</td>"
            f"<td>{props}</td>"
            "</tr>"
        )
    return f"""
      <table>
        <thead>
          <tr>
            <th>#</th><th>Status</th><th>Code</th><th>Base Item</th><th>Stacks</th><th>Special</th><th>Weapon Damage</th><th>Socketed</th><th>Quality</th><th>Simple</th><th>Ident</th><th>Sock</th>
            <th>Loc/Pos/Cont</th><th>X,Y</th><th>Lvl</th><th>FilledSockets</th><th>Properties</th>
          </tr>
        </thead>
        <tbody>
          {''.join(item_rows) if item_rows else '<tr><td colspan="17">No items</td></tr>'}
        </tbody>
      </table>
"""


def section_card(title: str, items: list[ParsedItem]) -> str:
    return f"""
    <div class=\"card\">
      <h2>{html.escape(title)} <span class=\"muted\">({len(items)})</span></h2>
      {render_items_table(items)}
    </div>
"""


ITEM_SLOT_NAMES = {
    1: "Helm",
    2: "Amulet",
    3: "Armor",
    4: "Weapon",
    5: "Shield",
    6: "Ring R",
    7: "Ring L",
    8: "Belt",
    9: "Boots",
    10: "Gloves",
    11: "Swap W",
    12: "Swap S",
}

ITEM_SLOT_AREAS = {
    1: "helm",
    2: "amulet",
    3: "armor",
    4: "weapon",
    5: "shield",
    6: "ringr",
    7: "ringl",
    8: "belt",
    9: "boots",
    10: "gloves",
    11: "swapw",
    12: "swaps",
}


def render_equipped_card(items: list[ParsedItem]) -> str:
    equipped = {it.position: it for it in items}

    def slot_cell(pos: int) -> str:
        it = equipped.get(pos)
        if it is None:
            return f'<div class="eq-slot" style="grid-area:{ITEM_SLOT_AREAS.get(pos, "empty")}"><div class="eq-label">{ITEM_SLOT_NAMES.get(pos, str(pos))}</div><div class="eq-empty">(empty)</div></div>'

        if it.runeword_name:
            name = html.escape(it.runeword_name)
            base = html.escape(it.item_name or "")
        elif it.unique_name:
            name = html.escape(it.unique_name)
            base = html.escape(it.item_name or "")
        elif it.set_name:
            name = html.escape(it.set_name)
            base = html.escape(it.item_name or "")
        else:
            name = html.escape(it.display_name or it.item_name or "?")
            base = ""

        weapon_dmg = html.escape(it.weapon_damage or "")
        req_parts = []
        if it.req_level:
            req_parts.append(f"Lvl {it.req_level}")
        if it.req_str:
            req_parts.append(f"Str {it.req_str}")
        if it.req_dex:
            req_parts.append(f"Dex {it.req_dex}")
        req_text = ", ".join(req_parts)

        props_html = "".join(
            f'<div class="eq-prop">{html.escape(p.display_text or f"{p.name}: {p.values}")}</div>'
            for p in it.properties if p.display_text != ""
        )
        socketed_text = ", ".join(si.item_name or si.code or "?" for si in it.socketed_items)
        quality_class = f"eq-{it.quality.name.lower()}" if it.quality.name != "UNKNOWN" else ""

        return f"""
        <div class="eq-slot {quality_class}" style="grid-area:{ITEM_SLOT_AREAS.get(pos, "empty")}">
          <div class="eq-label">{ITEM_SLOT_NAMES.get(pos, str(pos))}</div>
          <div class="eq-item-name">{name}</div>
          {"<div class=\"eq-base\">" + base + "</div>" if base else ""}
          {"<div class=\"eq-reqs\">Requires: " + html.escape(req_text) + "</div>" if req_parts else ""}
          {"<div class=\"eq-damage\">" + weapon_dmg + "</div>" if weapon_dmg else ""}
          <div class="eq-props">{props_html}</div>
          {"<div class=\"eq-sockets\">(" + html.escape(socketed_text) + ")</div>" if socketed_text else ""}
        </div>"""

    cells = "".join(slot_cell(pos) for pos in range(1, 13))

    return f"""
    <div class=\"card\">
      <h2>Character Equipment</h2>
      <div class="equipment-grid">
        {cells}
      </div>
      <details style="margin-top:16px">
        <summary style="cursor:pointer;color:var(--accent)">Show full item table</summary>
        {render_items_table(items)}
      </details>
    </div>
"""


def render_mercenary_card(items: list[ParsedItem]) -> str:
    equipped = {it.position: it for it in items}

    def slot_cell(pos: int, label: str, area: str) -> str:
        it = equipped.get(pos)
        if it is None:
            return f'<div class="eq-slot" style="grid-area:{area}"><div class="eq-label">{label}</div><div class="eq-empty">(empty)</div></div>'

        if it.runeword_name:
            name = html.escape(it.runeword_name)
            base = html.escape(it.item_name or "")
        elif it.unique_name:
            name = html.escape(it.unique_name)
            base = html.escape(it.item_name or "")
        elif it.set_name:
            name = html.escape(it.set_name)
            base = html.escape(it.item_name or "")
        else:
            name = html.escape(it.display_name or it.item_name or "?")
            base = ""

        weapon_dmg = html.escape(it.weapon_damage or "")
        req_parts = []
        if it.req_level:
            req_parts.append(f"Lvl {it.req_level}")
        if it.req_str:
            req_parts.append(f"Str {it.req_str}")
        if it.req_dex:
            req_parts.append(f"Dex {it.req_dex}")
        req_text = ", ".join(req_parts)

        props_html = "".join(
            f'<div class="eq-prop">{html.escape(p.display_text or f"{p.name}: {p.values}")}</div>'
            for p in it.properties if p.display_text != ""
        )
        socketed_text = ", ".join(si.item_name or si.code or "?" for si in it.socketed_items)
        quality_class = f"eq-{it.quality.name.lower()}" if it.quality.name != "UNKNOWN" else ""

        return f"""
        <div class="eq-slot {quality_class}" style="grid-area:{area}">
          <div class="eq-label">{label}</div>
          <div class="eq-item-name">{name}</div>
          {"<div class=\"eq-base\">" + base + "</div>" if base else ""}
          {"<div class=\"eq-reqs\">Requires: " + html.escape(req_text) + "</div>" if req_parts else ""}
          {"<div class=\"eq-damage\">" + weapon_dmg + "</div>" if weapon_dmg else ""}
          <div class="eq-props">{props_html}</div>
          {"<div class=\"eq-sockets\">(" + html.escape(socketed_text) + ")</div>" if socketed_text else ""}
        </div>"""

    cells = (
        slot_cell(1, "Helm", "merc_helm")
        + slot_cell(4, "Weapon", "merc_weapon")
        + slot_cell(5, "Shield", "merc_shield")
        + slot_cell(3, "Armor", "merc_armor")
    )

    return f"""
    <div class=\"card\">
      <h2>Mercenary Equipment</h2>
      <div class="mercenary-grid">
        {cells}
      </div>
      {"<details style=\"margin-top:16px\"><summary style=\"cursor:pointer;color:var(--accent)\">Show full item table</summary>" + render_items_table(items) + "</details>" if items else ""}
    </div>
"""


def render_shared_stash_cards(tabs: list[SharedStashTab]) -> str:
    if not tabs:
        return section_card("Shared Stash", [])
    return "".join(
        section_card(f"Shared Stash Tab {tab.index + 1} - Gold {tab.gold:,} - Items {len(tab.items)}/{tab.item_count}", tab.items)
        for tab in tabs
    )


def render_character_page(
    character: D2Character,
    source: str,
    shared_stash_source: Path | None = None,
    shared_stash_tabs: list[SharedStashTab] | None = None,
) -> str:
    shared_stash_tabs = shared_stash_tabs or []
    equipped = [item for item in character.items if item.location == 1]
    belt = [item for item in character.items if item.location == 2]
    inventory = [item for item in character.items if item.location == 0 and item.container == 1]
    cube = [item for item in character.items if item.location == 0 and item.container == 4]
    personal_stash = [item for item in character.items if item.location == 0 and item.container == 5]
    socketed = [item for item in character.items if item.location == 6]
    other = [
        item
        for item in character.items
        if item not in equipped + belt + inventory + cube + personal_stash + socketed
    ]

    raw_json = html.escape(json.dumps(character.model_dump(mode="json"), indent=2))
    return f"""
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>D2R Helper - Character</title>
  <style>
    :root {{ --bg:#f4f1ea; --card:#fffaf2; --ink:#1f1a14; --accent:#7a4b22; --line:#d8cdbf; }}
    body {{ font-family: Georgia, 'Times New Roman', serif; margin: 0; background: radial-gradient(circle at 0 0, #fff, var(--bg)); color: var(--ink); }}
    .wrap {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
    .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 16px; margin-bottom: 16px; }}
    h1, h2 {{ margin: 0 0 12px 0; color: var(--accent); }}
    .muted {{ color: #6f6257; font-size: 0.85em; font-weight: normal; }}
    .meta {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 8px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border: 1px solid var(--line); padding: 6px; vertical-align: top; }}
    th {{ background: #f1e8db; text-align: left; }}
    pre {{ overflow: auto; background: #f7efe2; border: 1px solid var(--line); padding: 12px; border-radius: 8px; }}

    .equipment-grid {{ display: grid; grid-template-areas:
      ".      helm    amulet  ."
      "weapon armor   armor   shield"
      "gloves belt    belt    boots"
      "ringr  .       .       ringl"
      ".      swapw   swaps   .";
      grid-template-columns: 1fr 1fr 1fr 1fr;
      gap: 10px; max-width: 540px; margin: 0 auto; }}
    .eq-slot {{
      border: 2px solid var(--line); border-radius: 8px; padding: 10px; min-height: 110px;
      background: linear-gradient(135deg, #faf5eb 0%, #f0e6d3 100%);
      display: flex; flex-direction: column; font-size: 13px;
    }}
    .eq-slot.eq-unique {{ border-color: #8b6914; background: linear-gradient(135deg, #faf5eb, #f5e6c8); }}
    .eq-slot.eq-set {{ border-color: #138b13; background: linear-gradient(135deg, #f0faf0, #d3f0d3); }}
    .eq-slot.eq-rare {{ border-color: #c8b84a; background: linear-gradient(135deg, #fafae8, #f5f0d0); }}
    .eq-slot.eq-magic {{ border-color: #4a7fc8; background: linear-gradient(135deg, #f0f5fa, #d3e8f5); }}
    .eq-label {{
      font-size: 10px; text-transform: uppercase; letter-spacing: 1px;
      color: var(--accent); margin-bottom: 4px; font-weight: bold;
    }}
    .eq-item-name {{ font-weight: bold; font-size: 14px; }}
    .eq-base {{ font-size: 11px; color: #6f6257; }}
    .eq-reqs {{ font-size: 11px; color: #8b7355; }}
    .eq-damage {{ font-size: 12px; color: var(--ink); }}
    .eq-props {{ margin-top: 4px; }}
    .eq-prop {{ font-size: 11px; color: #4a7fc8; line-height: 1.4; }}
    .eq-sockets {{ font-size: 10px; color: #6f6257; margin-top: 2px; }}
    .eq-empty {{ color: #b8b0a8; font-style: italic; font-size: 12px; }}

    .mercenary-grid {{ display: grid; grid-template-areas:
      ".        merc_helm    .        ."
      "merc_weapon merc_armor merc_shield .";
      grid-template-columns: 1fr 1fr 1fr 1fr;
      gap: 10px; max-width: 540px; margin: 0 auto; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"card\">
      <h1>{html.escape(character.name)} (lvl {character.level})</h1>
      <div>Source: <code>{html.escape(source)}</code></div>
      <div>Shared stash: <code>{html.escape(str(shared_stash_source) if shared_stash_source else 'Not found')}</code></div>
      <div class=\"meta\">
        <div><b>Class</b>: {character.character_type}</div>
        <div><b>Version</b>: {character.file_data.version}</div>
        <div><b>Hardcore</b>: {character.status.hardcore}</div>
        <div><b>Died</b>: {character.status.died}</div>
        <div><b>LoD</b>: {character.status.lord_of_destruction}</div>
        <div><b>RotW</b>: {character.status.reign_of_the_warlock}</div>
        <div><b>Act Progression</b>: {character.act_progression}</div>
        <div><b>Map ID</b>: {character.map_id}</div>
        <div><b>Merc ID</b>: {character.mercenary.merc_id}</div>
        <div><b>Merc Type</b>: {character.mercenary.type_id}</div>
        <div><b>Merc XP</b>: {character.mercenary.experience}</div>
        <div><b>Parsed Items</b>: {len(character.items)} / {character.item_count}</div>
        <div><b>Merc Items</b>: {len(character.mercenary.items)}</div>
        <div><b>Shared Stash Tabs</b>: {len(shared_stash_tabs)}</div>
      </div>
    </div>

    <div class=\"card\">
      <h2>Parse Warnings</h2>
      <pre>{html.escape(chr(10).join(character.parse_warnings) if character.parse_warnings else 'None')}</pre>
    </div>

    {render_equipped_card(equipped)}
    {render_mercenary_card(character.mercenary.items)}
    {section_card('Belt', belt)}
    {section_card('Inventory / Bag', inventory)}
    {section_card('Horadric Cube', cube)}
    {section_card('Personal Stash', personal_stash)}
    {section_card('Socketed Items Listed Separately', socketed)}
    {section_card('Other / Unknown Location', other)}
    {render_shared_stash_cards(shared_stash_tabs)}

    <div class=\"card\">
      <h2>Raw Parsed JSON</h2>
      <pre>{raw_json}</pre>
    </div>
  </div>
</body>
</html>
"""
