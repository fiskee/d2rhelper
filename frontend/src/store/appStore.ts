import { create } from 'zustand'
import type { ChatMessage, D2Character, ParsedItem, SharedStashTab } from '../types'

type View = 'dashboard' | 'search' | 'chat'

export interface TaggedItem {
  item: ParsedItem
  source: 'character' | 'mercenary' | 'stash'
  tabIndex?: number
}

interface AppState {
  view: View
  setView: (v: View) => void

  character: D2Character | null
  stashTabs: SharedStashTab[]
  characterPath: string
  loading: boolean
  error: string | null

  setCharacter: (char: D2Character, tabs: SharedStashTab[], path: string) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  clearCharacter: () => void

  allItems: TaggedItem[]

  searchQuery: string
  setSearchQuery: (q: string) => void

  chatMessages: ChatMessage[]
  chatStreaming: boolean
  addChatMessage: (msg: ChatMessage) => void
  setChatStreaming: (s: boolean) => void
  clearChat: () => void
}

export const useAppStore = create<AppState>((set) => ({
  view: 'dashboard',
  setView: (view) => set({ view }),

  character: null,
  stashTabs: [],
  characterPath: '',
  loading: false,
  error: null,

  setCharacter: (character, stashTabs, characterPath) => {
    const allItems: TaggedItem[] = [
      ...character.items.map((item) => ({ item, source: 'character' as const })),
      ...character.mercenary.items.map((item) => ({ item, source: 'mercenary' as const })),
      ...stashTabs.flatMap((t) =>
        t.items.map((item) => ({ item, source: 'stash' as const, tabIndex: t.index })),
      ),
    ]
    return set({ character, stashTabs, characterPath, allItems, loading: false, error: null })
  },
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  clearCharacter: () =>
    set({ character: null, stashTabs: [], characterPath: '', allItems: [] }),

  allItems: [],

  searchQuery: '',
  setSearchQuery: (searchQuery) => set({ searchQuery }),

  chatMessages: [],
  chatStreaming: false,
  addChatMessage: (msg) =>
    set((s) => ({ chatMessages: [...s.chatMessages, msg] })),
  setChatStreaming: (chatStreaming) => set({ chatStreaming }),
  clearChat: () => set({ chatMessages: [] }),
}))
