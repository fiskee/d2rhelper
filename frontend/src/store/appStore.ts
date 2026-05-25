import { create } from 'zustand'
import { parseCharacter, listCharacters } from '../api/client'
import type { ChatMessage, CharacterInfo, D2Character, ParsedItem, SharedStashTab } from '../types'

type View = 'dashboard' | 'search' | 'chat'

export interface TaggedItem {
  item: ParsedItem
  source: 'character' | 'mercenary' | 'stash'
  tabIndex?: number
  characterPath?: string
}

function deriveAllItems(
  characterCache: Record<string, D2Character>,
  stashTabs: SharedStashTab[],
  activeCharacterPath: string | null,
  searchAll: boolean,
): TaggedItem[] {
  const result: TaggedItem[] = []

  const paths = searchAll
    ? Object.keys(characterCache)
    : (activeCharacterPath ? [activeCharacterPath] : [])

  for (const path of paths) {
    const char = characterCache[path]
    if (!char) continue
    for (const item of char.items) {
      result.push({ item, source: 'character', characterPath: path })
    }
    for (const item of char.mercenary.items) {
      result.push({ item, source: 'mercenary', characterPath: path })
    }
  }

  for (const tab of stashTabs) {
    for (const item of tab.items) {
      result.push({ item, source: 'stash', tabIndex: tab.index })
    }
  }

  return result
}

interface AppState {
  view: View
  setView: (v: View) => void

  characters: CharacterInfo[]
  stashPath: string | null
  characterCache: Record<string, D2Character>
  stashTabs: SharedStashTab[]
  activeCharacterPath: string | null

  character: D2Character | null
  allItems: TaggedItem[]

  loading: boolean
  error: string | null

  searchAllCharacters: boolean

  fetchCharacters: () => Promise<void>
  parseAndSetActive: (path: string, stashPath?: string | null) => Promise<void>
  setActiveCharacterPath: (path: string | null) => void
  setSearchAllCharacters: (v: boolean) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void

  searchQuery: string
  setSearchQuery: (q: string) => void

  chatMessages: ChatMessage[]
  chatStreaming: boolean
  addChatMessage: (msg: ChatMessage) => void
  setChatStreaming: (s: boolean) => void
  clearChat: () => void
}

export const useAppStore = create<AppState>((set, get) => ({
  view: 'dashboard',
  setView: (view) => set({ view }),

  characters: [],
  stashPath: null,
  characterCache: {},
  stashTabs: [],
  activeCharacterPath: null,

  character: null,
  allItems: [],

  loading: false,
  error: null,

  searchAllCharacters: false,

  fetchCharacters: async () => {
    set({ loading: true, error: null })
    try {
      const data = await listCharacters()
      set({
        characters: data.characters,
        stashPath: data.stash_path ?? get().stashPath,
        loading: false,
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to list characters', loading: false })
    }
  },

  parseAndSetActive: async (path, overrideStashPath) => {
    const state = get()
    if (state.characterCache[path] && state.activeCharacterPath === path) {
      return
    }

    if (state.characterCache[path]) {
      const character = state.characterCache[path]
      const allItems = deriveAllItems(state.characterCache, state.stashTabs, path, state.searchAllCharacters)
      set({ activeCharacterPath: path, character, allItems, loading: false, error: null })
      return
    }

    set({ loading: true, error: null })
    try {
      const sp = overrideStashPath ?? get().stashPath
      const result = await parseCharacter(path, sp ?? undefined)
      const character = result.character
      const tabs = result.stash_tabs
      const newCache = { ...get().characterCache, [path]: character }
      const useTabs = get().stashTabs.length > 0 ? get().stashTabs : tabs
      const allItems = deriveAllItems(newCache, useTabs, path, get().searchAllCharacters)
      set({
        characterCache: newCache,
        stashTabs: useTabs,
        activeCharacterPath: path,
        character,
        allItems,
        loading: false,
        error: null,
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Parse failed', loading: false })
    }
  },

  setActiveCharacterPath: (path) => {
    const state = get()
    if (!path) {
      set({ activeCharacterPath: null, character: null, allItems: [], error: null })
      return
    }
    const character = state.characterCache[path] ?? null
    const allItems = deriveAllItems(state.characterCache, state.stashTabs, path, state.searchAllCharacters)
    set({ activeCharacterPath: path, character, allItems, error: null })
  },

  setSearchAllCharacters: (searchAllCharacters) => {
    const state = get()
    const allItems = deriveAllItems(
      state.characterCache,
      state.stashTabs,
      state.activeCharacterPath,
      searchAllCharacters,
    )
    set({ searchAllCharacters, allItems })
  },

  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),

  searchQuery: '',
  setSearchQuery: (searchQuery) => set({ searchQuery }),

  chatMessages: [],
  chatStreaming: false,
  addChatMessage: (msg) =>
    set((s) => ({ chatMessages: [...s.chatMessages, msg] })),
  setChatStreaming: (chatStreaming) => set({ chatStreaming }),
  clearChat: () => set({ chatMessages: [] }),
}))
