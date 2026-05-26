import type { D2Character, SharedStashTab, ParsedItem, Mercenary } from '../../types'
import { getItemDisplayName, getItemBaseName, ITEM_QUALITY_NAMES, EQUIPMENT_SLOTS } from '../../types'

interface CleanItem {
  id: string
  name: string
  base?: string
  quality: string
  damage?: string
  req?: { level?: number; str?: number; dex?: number }
  sockets?: { filled: number; total: number }
  ethereal?: boolean
  properties: string[]
  socketed?: string[]
  stacks?: number
}

interface ContextBuildIndices {
  idIndex: Record<string, ParsedItem>
  stashTabIndex: Record<string, number>
}

interface ContextBundle {
  payload: Record<string, unknown>
  idIndex: Record<string, ParsedItem>
  stashTabIndex: Record<string, number>
}

function createIndexState(idOffset: number): {
  assignId: (item: ParsedItem) => string
  indices: ContextBuildIndices
} {
  let nextId = idOffset
  const indices: ContextBuildIndices = {
    idIndex: {},
    stashTabIndex: {},
  }

  const assignId = (item: ParsedItem): string => {
    const id = `i${nextId++}`
    indices.idIndex[id] = item
    return id
  }

  return { assignId, indices }
}

function itemSummary(item: ParsedItem, assignId: (item: ParsedItem) => string): CleanItem {
  const result: CleanItem = {
    id: assignId(item),
    name: getItemDisplayName(item) || item.code || 'Unknown',
    quality: ITEM_QUALITY_NAMES[item.quality] || 'Normal',
    properties: (item.properties || [])
      .filter((p) => p.display_text)
      .map((p) => p.display_text!),
  }

  const base = getItemBaseName(item)
  if (base) result.base = base

  if (item.weapon_damage) result.damage = item.weapon_damage

  const req: CleanItem['req'] = {}
  if (item.req_level) req.level = item.req_level
  if (item.req_str) req.str = item.req_str
  if (item.req_dex) req.dex = item.req_dex
  if (Object.keys(req).length > 0) result.req = req

  if (item.socketed) {
    result.sockets = {
      filled: item.cnt_filled_sockets ?? 0,
      total: item.cnt_sockets ?? 0,
    }
  }

  if (item.ethereal) result.ethereal = true

  if (item.stacks && item.stacks > 1) {
    result.stacks = item.stacks
  }

  if (item.socketed_items && item.socketed_items.length > 0) {
    result.socketed = item.socketed_items.map((s) => getItemDisplayName(s) || s.code || 'Unknown')
  }

  return result
}

function mercenarySummary(merc: Mercenary, assignId: (item: ParsedItem) => string) {
  if (!merc.hireling_name) return null
  return {
    name: merc.hireling_name,
    subtype: merc.hireling_subtype,
    skills: merc.hireling_skills,
    experience: merc.experience,
    equipment: merc.items
      .filter((i) => i.location === 1)
      .map((i) => {
        const slotName = Object.entries(EQUIPMENT_SLOTS).find(
          ([pos]) => Number(pos) === i.position,
        )?.[1]?.name
        return { slot: slotName ?? `slot_${i.position}`, item: itemSummary(i, assignId) }
      }),
  }
}

interface CategorizedItems {
  equipment: Record<string, CleanItem>
  belt: CleanItem[]
  inventory: CleanItem[]
  cube: CleanItem[]
  personal_stash: CleanItem[]
}

function categorizeItems(items: ParsedItem[], assignId: (item: ParsedItem) => string): CategorizedItems {
  const result: CategorizedItems = {
    equipment: {},
    belt: [],
    inventory: [],
    cube: [],
    personal_stash: [],
  }

  for (const item of items) {
    if (item.location === 1) {
      const slotName = Object.entries(EQUIPMENT_SLOTS).find(
        ([pos]) => Number(pos) === item.position,
      )?.[1]?.name
      result.equipment[slotName ?? `slot_${item.position}`] = itemSummary(item, assignId)
    } else if (item.location === 2) {
      result.belt.push(itemSummary(item, assignId))
    } else if (item.location === 0 && item.container === 1) {
      result.inventory.push(itemSummary(item, assignId))
    } else if (item.location === 0 && item.container === 4) {
      result.cube.push(itemSummary(item, assignId))
    } else if (item.location === 0 && item.container === 5) {
      result.personal_stash.push(itemSummary(item, assignId))
    }
  }

  return result
}

function characterSummary(c: D2Character, assignId: (item: ParsedItem) => string) {
  const cats = categorizeItems(c.items, assignId)
  return {
    name: c.name,
    level: c.level,
    character_type: c.character_type,
    status: {
      hardcore: c.status.hardcore,
      lord_of_destruction: c.status.lord_of_destruction,
      reign_of_the_warlock: c.status.reign_of_the_warlock,
    },
    act_progression: c.act_progression,
    attributes: c.attributes,
    skills: c.skills,
    quest_data: c.quest_data,
    waypoints: c.waypoints,
    locations: c.locations,
    mercenary: mercenarySummary(c.mercenary, assignId),
    equipment: cats.equipment,
    belt: cats.belt,
    inventory: cats.inventory,
    cube: cats.cube,
    personal_stash: cats.personal_stash,
  }
}

function stashTabSummary(
  tab: SharedStashTab,
  assignId: (item: ParsedItem) => string,
  stashTabIndex: Record<string, number>,
) {
  for (const item of tab.items) {
    const id = assignId(item)
    stashTabIndex[id] = tab.index
  }
  return {
    index: tab.index,
    gold: tab.gold,
    items: tab.items.map((item) => itemSummary(item, assignId)),
  }
}

export function buildContextBundle(state: {
  character: D2Character | null
  stashTabs: SharedStashTab[]
  characterCache: Record<string, D2Character>
  includeAllCharactersInChat: boolean
  activeCharacterPath: string | null
  idOffset?: number
}): ContextBundle {
  const { assignId, indices } = createIndexState(state.idOffset ?? 0)
  const char = state.character
  const payload: Record<string, unknown> = {
    character: char ? characterSummary(char, assignId) : null,
    stash_tabs: state.stashTabs.map((tab) => stashTabSummary(tab, assignId, indices.stashTabIndex)),
  }

  if (state.includeAllCharactersInChat && char) {
    const others = Object.entries(state.characterCache)
      .filter(([path]) => path !== state.activeCharacterPath)
      .map(([path, c]) => ({ path, ...characterSummary(c, assignId) }))
    if (others.length > 0) {
      payload.other_characters = others
    }
  }

  return {
    payload,
    idIndex: indices.idIndex,
    stashTabIndex: indices.stashTabIndex,
  }
}

export function buildContextPayload(state: {
  character: D2Character | null
  stashTabs: SharedStashTab[]
  characterCache: Record<string, D2Character>
  includeAllCharactersInChat: boolean
  activeCharacterPath: string | null
  idOffset?: number
}): Record<string, unknown> {
  return buildContextBundle(state).payload
}
