import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { get, set, del } from 'idb-keyval'
import type { StateStorage } from 'zustand/middleware'
import { parseCharacter, listCharacters, fetchSets, listChats, deleteChatApi } from '../api/client'
import type { Chat, ChatMessage, CharacterInfo, D2Character, ParsedItem, SetData, SharedStashTab } from '../types'

type View = 'dashboard' | 'search' | 'chat' | 'sets'

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

function makeChat(state: {
  activeCharacterPath: string | null
  character: D2Character | null
}, mode: 'tools' | 'full_context' = 'tools'): Chat {
  return {
    id: crypto.randomUUID(),
    title: 'New Chat',
    messages: [],
    characterPath: state.activeCharacterPath,
    characterType: state.character?.character_type ?? null,
    characterName: state.character?.name ?? null,
    chatMode: mode,
    contextPayload: null,
    itemIdIndex: {},
    itemStashTabIndex: {},
    createdAt: Date.now(),
    updatedAt: Date.now(),
  }
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

  chats: Chat[]
  activeChatId: string | null
  chatStreaming: boolean
  includeAllCharactersInChat: boolean
  itemIndex: Record<string, ParsedItem[]>
  idIndex: Record<string, ParsedItem>
  stashTabIndex: Record<string, number>

  createChat: (mode?: 'tools' | 'full_context') => void
  deleteChat: (id: string) => void
  setActiveChat: (id: string) => void
  addMessageToChat: (chatId: string, msg: ChatMessage) => void
  setChatStreaming: (s: boolean) => void
  setChatContextPayload: (chatId: string, payload: string) => void
  setChatIdIndex: (chatId: string, idIndex: Record<string, ParsedItem>, stashTabIndex: Record<string, number>) => void
  setIncludeAllCharactersInChat: (v: boolean) => void
  setItemIndex: (idx: Record<string, ParsedItem[]>) => void
  setIdIndex: (idx: Record<string, ParsedItem>) => void
  setStashTabIndex: (idx: Record<string, number>) => void
  fetchChatsFromBackend: () => Promise<void>
  refreshCharacter: () => Promise<void>

  setData: SetData[] | null
  fetchSetData: () => Promise<void>
}

const idbStorage: StateStorage = {
  getItem: async (name: string) => {
    const value = await get(name)
    return value ?? null
  },
  setItem: async (name: string, value: string) => {
    await set(name, value)
  },
  removeItem: async (name: string) => {
    await del(name)
  },
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
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
            characters: data.characters.length > 0 ? data.characters : get().characters,
            stashPath: data.stash_path ?? get().stashPath,
            loading: false,
          })
        } catch (err) {
          set({ error: err instanceof Error ? err.message : 'Failed to list characters', loading: false })
        }
      },

      fetchChatsFromBackend: async () => {
        try {
          const backendChats = await listChats()
          if (backendChats.length === 0) return
          const existing = get().chats
          const existingIds = new Set(existing.map((c) => c.id))
          const newChats = backendChats
            .filter((bc) => !existingIds.has(bc.id))
            .map((bc) => ({
              id: bc.id,
              title: bc.title,
              messages: [],
              chatMode: 'tools' as const,
              contextPayload: null,
              itemIdIndex: {},
              itemStashTabIndex: {},
              characterPath: bc.character_path,
              characterType: bc.character_type,
              characterName: bc.character_name,
              createdAt: bc.created_at,
              updatedAt: bc.updated_at,
            }))
          if (newChats.length > 0) {
            set((s) => ({
              chats: [...newChats, ...s.chats],
            }))
          }
        } catch {
          // backend unavailable, use local data
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

      chats: [],
      activeChatId: null,
      chatStreaming: false,
      includeAllCharactersInChat: false,
      itemIndex: {},
      idIndex: {},
      stashTabIndex: {},

      createChat: (mode: 'tools' | 'full_context' = 'tools') => {
        const chat = makeChat(get(), mode)
        set((s) => {
          let chats = s.chats
          if (s.activeChatId) {
            const current = chats.find((c) => c.id === s.activeChatId)
            if (current && current.messages.length === 0) {
              chats = chats.filter((c) => c.id !== current.id)
            }
          }
          return { chats: [...chats, chat], activeChatId: chat.id }
        })
      },

      deleteChat: (id) => {
        set((s) => {
          const chats = s.chats.filter((c) => c.id !== id)
          const activeChatId = s.activeChatId === id
            ? (chats.length > 0 ? chats[chats.length - 1].id : null)
            : s.activeChatId
          return { chats, activeChatId }
        })
        deleteChatApi(id).catch(() => {})
      },

      setActiveChat: (id) => {
        set((s) => {
          let chats = s.chats
          const currentId = s.activeChatId
          if (currentId && currentId !== id) {
            const current = chats.find((c) => c.id === currentId)
            if (current && current.messages.length === 0) {
              chats = chats.filter((c) => c.id !== currentId)
            }
          }
          return { chats, activeChatId: id }
        })
      },

      addMessageToChat: (chatId, msg) =>
        set((s) => ({
          chats: s.chats.map((c) => {
            if (c.id !== chatId) return c
            const isFirstUserMessage = c.messages.length === 0 && msg.role === 'user'
            return {
              ...c,
              title: isFirstUserMessage
                ? (msg.content.length > 40 ? msg.content.slice(0, 40) + '...' : msg.content)
                : c.title,
              messages: [...c.messages, msg],
              updatedAt: Date.now(),
            }
          }),
        })),

      setChatStreaming: (chatStreaming) => set({ chatStreaming }),

      setChatContextPayload: (chatId, payload) =>
        set((s) => ({
          chats: s.chats.map((c) => (c.id === chatId ? { ...c, contextPayload: payload } : c)),
        })),

      setIncludeAllCharactersInChat: (includeAllCharactersInChat) => set({ includeAllCharactersInChat }),

      setItemIndex: (itemIndex) => set({ itemIndex }),

      setIdIndex: (idIndex) => set({ idIndex }),

      setStashTabIndex: (stashTabIndex) => set({ stashTabIndex }),

      setChatIdIndex: (chatId, idIndex, stashTabIndex) =>
        set((s) => {
          const existingChat = s.chats.find((c) => c.id === chatId)
          const mergedIdIndex = { ...existingChat?.itemIdIndex, ...idIndex }
          const mergedStashIndex = { ...existingChat?.itemStashTabIndex, ...stashTabIndex }
          return {
            idIndex: mergedIdIndex,
            stashTabIndex: mergedStashIndex,
            chats: s.chats.map((c) =>
              c.id === chatId
                ? { ...c, itemIdIndex: mergedIdIndex, itemStashTabIndex: mergedStashIndex }
                : c,
            ),
          }
        }),

      setData: null,
      fetchSetData: async () => {
        try {
          const data = await fetchSets()
          set({ setData: data })
        } catch {
          // keep stale data if any
        }
      },

      refreshCharacter: async () => {
        const state = get()
        const path = state.activeCharacterPath
        if (!path) return
        try {
          const sp = state.stashPath
          const result = await parseCharacter(path, sp ?? undefined)
          const character = result.character
          const tabs = result.stash_tabs
          const newCache = { ...get().characterCache, [path]: character }
          const allItems = deriveAllItems(newCache, tabs, path, get().searchAllCharacters)
          set({
            characterCache: newCache,
            stashTabs: tabs,
            character,
            allItems,
          })
        } catch {
          // file temporarily unreadable, keep stale data
        }
      },
    }),
    {
      name: 'd2rhelper-chat-storage-v2',
      storage: createJSONStorage(() => idbStorage),
      onRehydrateStorage: () => {
        return () => {
          const store = useAppStore.getState()
          get('d2rhelper-chat-storage').then((raw) => {
            if (!raw || typeof raw !== 'string') return
            try {
              const parsed = JSON.parse(raw)
              const oldChats = parsed?.state?.chats
              if (oldChats && oldChats.length > 0) {
                const existingIds = new Set(store.chats.map((c: Chat) => c.id))
                const newChats = oldChats.filter((c: Chat) => !existingIds.has(c.id))
                if (newChats.length > 0) {
                  useAppStore.setState({ chats: [...newChats, ...store.chats] })
                }
              }
            } catch { /* ignore parse errors */ }
            del('d2rhelper-chat-storage')
          })
        }
      },
      partialize: (state) => {
        const nonEmptyChats = state.chats.filter((c) => c.messages.length > 0)
        const activeId = nonEmptyChats.some((c) => c.id === state.activeChatId)
          ? state.activeChatId
          : (nonEmptyChats.length > 0 ? nonEmptyChats[nonEmptyChats.length - 1].id : null)
        return {
          chats: nonEmptyChats,
          activeChatId: activeId,
          activeCharacterPath: state.activeCharacterPath,
          character: state.character,
          characterCache: state.characterCache,
          stashTabs: state.stashTabs,
          stashPath: state.stashPath,
          characters: state.characters,
          view: state.view,
          searchQuery: state.searchQuery,
          searchAllCharacters: state.searchAllCharacters,
          includeAllCharactersInChat: state.includeAllCharactersInChat,
        }
      },
    },
  ),
)
