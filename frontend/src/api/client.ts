import type { CharactersResponse, ParseResponse, SearchResult, SetData } from '../types'

const API_BASE = '/api'

export async function parseCharacter(characterPath: string, stashPath?: string): Promise<ParseResponse> {
  const res = await fetch(`${API_BASE}/parse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ character_path: characterPath, stash_path: stashPath }),
  })
  if (!res.ok) {
    throw new Error(`Parse failed: ${res.statusText}`)
  }
  return res.json()
}

export async function autoParse(): Promise<ParseResponse & { character_path?: string; stash_path?: string }> {
  const res = await fetch(`${API_BASE}/parse/auto`, { method: 'POST' })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error ?? 'Auto-detect failed')
  }
  return res.json()
}

export async function listCharacters(): Promise<CharactersResponse> {
  const res = await fetch(`${API_BASE}/characters`)
  if (!res.ok) {
    throw new Error(`Character list failed: ${res.statusText}`)
  }
  return res.json()
}

export async function searchItems(
  query: string,
  characterPaths: string[],
  stashPath?: string,
): Promise<SearchResult[]> {
  const params = new URLSearchParams({ q: query })
  if (characterPaths.length > 0) {
    params.set('character_paths', JSON.stringify(characterPaths))
  }
  if (characterPaths.length === 1) {
    params.set('character_path', characterPaths[0])
  }
  if (stashPath) {
    params.set('stash_path', stashPath)
  }
  const res = await fetch(`${API_BASE}/search?${params}`)
  if (!res.ok) {
    throw new Error(`Search failed: ${res.statusText}`)
  }
  return res.json()
}

export async function getAutocomplete(query: string): Promise<string[]> {
  const params = new URLSearchParams({ q: query })
  const res = await fetch(`${API_BASE}/autocomplete?${params}`)
  if (!res.ok) {
    return []
  }
  return res.json()
}

export async function fetchSets(): Promise<SetData[]> {
  const res = await fetch(`${API_BASE}/sets`)
  if (!res.ok) {
    return []
  }
  return res.json()
}

export function createChatWebSocket(onMessage: (text: string, done: boolean) => void): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const ws = new WebSocket(`${protocol}//${window.location.host}/api/chat`)

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage(data.text ?? '', data.done ?? false)
    } catch {
      onMessage(event.data, false)
    }
  }

  return ws
}

export interface ChatSummary {
  id: string
  title: string
  character_path: string | null
  character_type: string | null
  character_name: string | null
  created_at: number
  updated_at: number
}

export async function listChats(): Promise<ChatSummary[]> {
  const res = await fetch(`${API_BASE}/chats`)
  if (!res.ok) return []
  return res.json()
}

export async function deleteChatApi(chatId: string): Promise<void> {
  await fetch(`${API_BASE}/chats/${encodeURIComponent(chatId)}`, { method: 'DELETE' })
}

export interface DBAttrs {
  name: string
  quality: 'unique' | 'set' | 'runeword' | 'base'
  base_name?: string | null
  base_code?: string | null
  set_name?: string | null
  base_hint?: string | null
  level_req?: number | null
  runes?: string[]
  type?: string | null
  code?: string | null
  properties: string[]
}

const itemLookupCache = new Map<string, DBAttrs | null>()

export async function lookupItem(name: string, itemType?: string): Promise<DBAttrs | null> {
  const key = `${itemType ?? ''}:${name.toLowerCase()}`
  if (itemLookupCache.has(key)) return itemLookupCache.get(key) ?? null
  const params = new URLSearchParams({ name })
  if (itemType) params.set('type', itemType)
  const res = await fetch(`${API_BASE}/items/lookup?${params}`)
  if (!res.ok) {
    itemLookupCache.set(key, null)
    return null
  }
  const data = await res.json()
  if (!data) {
    itemLookupCache.set(key, null)
    return null
  }
  itemLookupCache.set(key, data)
  return data
}
