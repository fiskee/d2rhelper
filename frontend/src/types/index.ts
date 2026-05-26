export interface FileData {
  header: number
  version: number
  file_size: number
  checksum: number
  unknown: number
}

export interface CharacterStatus {
  hardcore: boolean
  died: boolean
  lord_of_destruction: boolean
  reign_of_the_warlock: boolean
}

export interface CharacterLocation {
  difficulty: string
  active: boolean
  act: number
}

export interface CharacterAttributes {
  strength: number
  dexterity: number
  vitality: number
  energy: number
  stat_points_left: number
  skill_points_left: number
  hp: number
  max_hp: number
  mana: number
  max_mana: number
  stamina: number
  max_stamina: number
  level: number
  experience: number
  gold: number
  gold_in_stash: number
}

export interface Skill {
  name: string
  level: number
}

export interface QuestData {
  difficulty: string
  den_of_evil: boolean
  radament: boolean
  golden_bird: boolean
  siege_completed: boolean
  socket_quest_available: boolean
  resistance_scroll: boolean
}

export interface WaypointStatus {
  difficulty: string
  waypoints: string[]
}

export interface ParsedItemProperty {
  index: number
  name: string
  values: number[]
  display_name: string | null
  display_text: string | null
  quality_flag: number
  order: number
}

export interface ParsedItem {
  index: number
  start_bit: number
  end_bit: number
  location: number
  position: number
  x: number
  y: number
  container: number
  code: string | null
  item_name: string | null
  display_name: string | null
  runeword_name: string | null
  unique_name: string | null
  set_name: string | null
  set_group: string | null
  weapon_damage: string | null
  raw_flags: number
  identified: boolean
  socketed: boolean
  ear: boolean
  simple: boolean
  ethereal: boolean
  personalized: boolean
  runeword: boolean
  req_level: number | null
  req_str: number | null
  req_dex: number | null
  quality: number
  level: number | null
  cnt_filled_sockets: number | null
  cnt_sockets: number | null
  stacks: number | null
  max_stacks: number | null
  socketed_items: ParsedItem[]
  properties: ParsedItemProperty[]
  parse_ok: boolean
  recovered: boolean
}

export interface Mercenary {
  alive_flag: number
  merc_id: number
  name_id: number
  type_id: number
  experience: number
  hireling_name: string | null
  hireling_subtype: string | null
  hireling_skills: string[]
  items: ParsedItem[]
}

export interface D2Character {
  parsed_at: string
  file_data: FileData
  name: string
  status: CharacterStatus
  act_progression: number
  character_type: string
  level: number
  map_id: number
  locations: CharacterLocation[]
  mercenary: Mercenary
  attributes: CharacterAttributes
  skills: Skill[]
  quest_data: QuestData[]
  waypoints: WaypointStatus[]
  raw_skill_block_start: number | null
  item_list_start: number | null
  item_count: number
  items: ParsedItem[]
  parse_warnings: string[]
}

export interface SharedStashTab {
  index: number
  version: number
  gold: number
  length_in_bytes: number
  item_count: number
  items: ParsedItem[]
}

export interface CharacterInfo {
  path: string
  name: string
  character_type: string
  level: number
  hardcore: boolean
  mtime: number | null
}

export interface CharactersResponse {
  characters: CharacterInfo[]
  stash_path: string | null
}

export interface ParseResponse {
  character: D2Character
  stash_tabs: SharedStashTab[]
}

export interface SearchResult {
  item: ParsedItem
  source: string
  tab_index?: number
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  toolCall?: { name: string; args: Record<string, unknown> }
  toolResult?: { name: string; result: unknown; ok?: boolean; error?: string }
}

export interface Chat {
  id: string
  title: string
  messages: ChatMessage[]
  characterPath: string | null
  characterType: string | null
  characterName: string | null
  chatMode: 'tools' | 'full_context'
  contextPayload: string | null
  itemIdIndex: Record<string, ParsedItem>
  itemStashTabIndex: Record<string, number>
  createdAt: number
  updatedAt: number
}

export const EQUIPMENT_SLOTS: Record<number, { name: string; area: string }> = {
  1: { name: 'Helm', area: 'helm' },
  2: { name: 'Amulet', area: 'amulet' },
  3: { name: 'Armor', area: 'armor' },
  4: { name: 'Weapon', area: 'weapon' },
  5: { name: 'Shield', area: 'shield' },
  6: { name: 'Ring R', area: 'ringr' },
  7: { name: 'Ring L', area: 'ringl' },
  8: { name: 'Belt', area: 'belt' },
  9: { name: 'Boots', area: 'boots' },
  10: { name: 'Gloves', area: 'gloves' },
  11: { name: 'Swap W', area: 'swapw' },
  12: { name: 'Swap S', area: 'swaps' },
}

export const ITEM_QUALITY_NAMES: Record<number, string> = {
  0: 'None',
  1: 'Inferior',
  2: 'Normal',
  3: 'Superior',
  4: 'Magic',
  5: 'Set',
  6: 'Rare',
  7: 'Unique',
  8: 'Craft',
}

export function getItemDisplayName(item: ParsedItem): string {
  return item.runeword_name ?? item.unique_name ?? item.set_name ?? item.display_name ?? item.item_name ?? 'Unknown Item'
}

export function getItemBaseName(item: ParsedItem): string | null {
  if (item.runeword_name || item.unique_name || item.set_name) {
    return item.item_name ?? null
  }
  return null
}

export interface SetItemData {
  name: string
  code: string
  base: string
}

export interface SetData {
  name: string
  items: SetItemData[]
}

export interface PlayerSetProgress {
  setName: string
  owned: number
  total: number
  pieces: {
    name: string
    code: string
    base: string
    owned: boolean
    source: string | null
  }[]
}
