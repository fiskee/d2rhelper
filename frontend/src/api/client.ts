import type { ParseResponse, SearchResult } from '../types'

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

export async function searchItems(
  query: string,
  characterId?: string,
): Promise<SearchResult[]> {
  const params = new URLSearchParams({ q: query })
  if (characterId) params.set('character_id', characterId)
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
