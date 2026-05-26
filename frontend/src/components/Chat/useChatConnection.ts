import { useCallback, useEffect, useRef, useState } from 'react'
import { createChatWebSocket } from '../../api/client'
import { useAppStore } from '../../store/appStore'
import type { D2Character, ParsedItem, SharedStashTab } from '../../types'
import { getItemDisplayName } from '../../types'
import { buildContextBundle } from './contextBuilder'

export type ConnectionState = 'idle' | 'connecting' | 'connected' | 'error'

function buildItemIndex(
  character: D2Character | null,
  stashTabs: SharedStashTab[],
  characterCache: Record<string, D2Character>,
  includeAll: boolean,
  activePath: string | null,
): Record<string, ParsedItem[]> {
  const index: Record<string, ParsedItem[]> = {}

  function indexItems(items: ParsedItem[]) {
    for (const item of items) {
      const names: string[] = []
      const display = getItemDisplayName(item)
      if (display) names.push(display.toLowerCase())
      if (item.item_name) names.push(item.item_name.toLowerCase())
      if (item.runeword_name) names.push(item.runeword_name.toLowerCase())
      if (item.unique_name) names.push(item.unique_name.toLowerCase())
      if (item.set_name) names.push(item.set_name.toLowerCase())
      if (item.code) names.push(item.code.toLowerCase())

      for (const n of names) {
        if (!index[n]) index[n] = []
        index[n].push(item)
      }
    }
  }

  if (character) {
    indexItems(character.items)
    indexItems(character.mercenary.items)
  }

  for (const tab of stashTabs) {
    indexItems(tab.items)
  }

  if (includeAll) {
    for (const [path, char] of Object.entries(characterCache)) {
      if (path === activePath) continue
      indexItems(char.items)
      indexItems(char.mercenary.items)
    }
  }

  return index
}

export function useChatConnection() {
  const activeChatId = useAppStore((s) => s.activeChatId)
  const includeAllCharactersInChat = useAppStore((s) => s.includeAllCharactersInChat)
  const character = useAppStore((s) => s.character)
  const stashTabs = useAppStore((s) => s.stashTabs)
  const characterCache = useAppStore((s) => s.characterCache)
  const chats = useAppStore((s) => s.chats)
  const addMessageToChat = useAppStore((s) => s.addMessageToChat)
  const setChatStreaming = useAppStore((s) => s.setChatStreaming)
  const setChatContextPayload = useAppStore((s) => s.setChatContextPayload)

  const wsRef = useRef<WebSocket | null>(null)
  const streamingAccRef = useRef('')
  const [streamingText, setStreamingText] = useState('')
  const connectingRef = useRef(false)
  const lastSentContextKeyRef = useRef('')
  const [connectionState, setConnectionState] = useState<ConnectionState>('idle')

  const sendContext = useCallback(() => {
    const chatId = useAppStore.getState().activeChatId
    const ws = wsRef.current
    if (!chatId || !ws || ws.readyState !== WebSocket.OPEN) return

    const state = useAppStore.getState()
    const contextKey = JSON.stringify({
      chatId,
      activeCharacterPath: state.activeCharacterPath,
      includeAllCharactersInChat: state.includeAllCharactersInChat,
      chatMode: state.chats.find((c) => c.id === chatId)?.chatMode ?? 'tools',
      characterName: state.character?.name ?? null,
      characterLevel: state.character?.level ?? null,
      stashTabs: state.stashTabs.length,
      otherCharacters: Object.keys(state.characterCache).length,
    })
    if (lastSentContextKeyRef.current === contextKey) return

    const existingChat = state.chats.find((c) => c.id === chatId)
    const existingIds = Object.keys(existingChat?.itemIdIndex ?? {})
      .map((k) => parseInt(k.slice(1), 10))
      .filter((n) => !isNaN(n))
    const idOffset = existingIds.length > 0 ? Math.max(...existingIds) + 1 : 0

    const contextBundle = buildContextBundle({
      character: state.character,
      stashTabs: state.stashTabs,
      characterCache: state.characterCache,
      includeAllCharactersInChat: state.includeAllCharactersInChat,
      activeCharacterPath: state.activeCharacterPath,
      idOffset,
    })

    const itemIndex = buildItemIndex(
      state.character,
      state.stashTabs,
      state.characterCache,
      state.includeAllCharactersInChat,
      state.activeCharacterPath,
    )
    useAppStore.getState().setItemIndex(itemIndex)
    useAppStore.getState().setChatIdIndex(chatId, contextBundle.idIndex, contextBundle.stashTabIndex)

    const contextPayload = contextBundle.payload
    contextPayload.chat_id = chatId
    contextPayload.chat_mode = state.chats.find((c) => c.id === chatId)?.chatMode ?? 'tools'
    const contextJson = JSON.stringify(contextPayload, null, 2)
    setChatContextPayload(chatId, contextJson)
    ws.send(JSON.stringify({ type: 'context', payload: JSON.stringify(contextPayload) }))
    lastSentContextKeyRef.current = contextKey
  }, [setChatContextPayload])

  useEffect(() => {
    sendContext()
  }, [character, stashTabs, characterCache, chats, includeAllCharactersInChat, activeChatId, sendContext])

  const connect = useCallback(() => {
    const chatId = useAppStore.getState().activeChatId
    if (!chatId) return
    if (connectingRef.current) return
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return
    }

    connectingRef.current = true
    setConnectionState('connecting')

    const ws = createChatWebSocket((data) => {
      if ('thinking' in data && data.thinking === true) {
        setChatStreaming(true)
        return
      }
      if ('thinking' in data && data.thinking === false) {
        return
      }

      if ('tool_call' in data) {
        const tc = data.tool_call
        addMessageToChat(chatId, {
          role: 'system',
          content: `${tc.name}(${Object.entries(tc.args || {}).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(', ')})`,
          toolCall: tc,
        })
        return
      }

      if ('tool_result' in data) {
        const tr = data.tool_result
        addMessageToChat(chatId, {
          role: 'system',
          content: tr.ok === false ? `Tool error: ${tr.error ?? 'Unknown error'}` : '',
          toolResult: tr,
        })
        return
      }

      const text = 'text' in data ? data.text : ''
      const done = data.done
      streamingAccRef.current += text
      setStreamingText(streamingAccRef.current)
      if (done) {
        const content = streamingAccRef.current.trim()
        streamingAccRef.current = ''
        setStreamingText('')
        if (content) {
          addMessageToChat(chatId, { role: 'assistant', content })
        }
        setChatStreaming(false)
      } else {
        setChatStreaming(true)
      }
    })

    ws.onopen = () => {
      connectingRef.current = false
      setConnectionState('connected')
      sendContext()
    }
    ws.onerror = () => {
      connectingRef.current = false
      wsRef.current = null
      setConnectionState('error')
    }
    ws.onclose = () => {
      connectingRef.current = false
      if (wsRef.current === ws) {
        wsRef.current = null
        setConnectionState('error')
      }
    }

    wsRef.current = ws
  }, [addMessageToChat, sendContext, setChatStreaming])

  useEffect(() => {
    const activeChat = chats.find((c) => c.id === activeChatId)
    if (!activeChat || !activeChat.itemIdIndex || Object.keys(activeChat.itemIdIndex).length === 0) return
    useAppStore.getState().setIdIndex(activeChat.itemIdIndex)
    useAppStore.getState().setStashTabIndex(activeChat.itemStashTabIndex)
  }, [activeChatId, chats])

  useEffect(() => {
    if (!activeChatId) return
    connect()
    return () => {
      setChatStreaming(false)
      streamingAccRef.current = ''
      setStreamingText('')
      connectingRef.current = false
      lastSentContextKeyRef.current = ''
      if (wsRef.current) {
        wsRef.current.onopen = null
        wsRef.current.onclose = null
        wsRef.current.onerror = null
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [activeChatId, connect, setChatStreaming])

  const sendMessage = useCallback((message: string) => {
    const chatId = useAppStore.getState().activeChatId
    if (!chatId) return
    if (wsRef.current?.readyState !== WebSocket.OPEN) return

    addMessageToChat(chatId, { role: 'user', content: message })
    setChatStreaming(true)
    wsRef.current.send(JSON.stringify({ type: 'message', payload: message }))
  }, [addMessageToChat, setChatStreaming])

  return {
    connectionState,
    streamingText,
    connect,
    sendMessage,
  }
}
