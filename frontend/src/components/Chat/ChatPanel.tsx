import { useEffect, useRef, useCallback, useState, useMemo } from 'react'
import { useAppStore } from '../../store/appStore'
import { createChatWebSocket } from '../../api/client'
import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'
import type { ParsedItem, D2Character, SharedStashTab } from '../../types'
import { getItemDisplayName } from '../../types'
import { buildContextPayload, getIdIndex, getStashTabIndex } from './contextBuilder'

type ConnectionState = 'idle' | 'connecting' | 'connected' | 'error'

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

function ContextBlock({ payload, label }: { payload: string; label: string }) {
  const [expanded, setExpanded] = useState(false)
  let parsed: unknown = payload
  try {
    parsed = JSON.parse(payload)
  } catch { /* raw string */ }

  return (
    <div className="border-b border-d2-border">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-1.5 text-xs text-d2-muted font-body hover:text-d2-ink hover:bg-d2-card transition-colors flex items-center gap-1.5 cursor-pointer"
      >
        <span className="font-mono text-[10px]">{expanded ? '\u25BC' : '\u25B6'}</span>
        {label}
      </button>
      {expanded && (
        <pre className="px-4 pb-3 text-xs text-d2-muted font-mono whitespace-pre-wrap max-h-64 overflow-y-auto border-t border-d2-border/50">
          {JSON.stringify(parsed, null, 2)}
        </pre>
      )}
    </div>
  )
}

export function ChatPanel() {
  const {
    activeChatId,
    chats,
    chatStreaming,
    includeAllCharactersInChat,
    setIncludeAllCharactersInChat,
    characterCache,
    character,
    stashTabs,
    addMessageToChat,
    setChatStreaming,
    setChatContextPayload,
  } = useAppStore()

  const activeChat = useMemo(
    () => chats.find((c) => c.id === activeChatId) ?? null,
    [chats, activeChatId],
  )

  const wsRef = useRef<WebSocket | null>(null)
  const streamingAccRef = useRef('')
  const [streamingText, setStreamingText] = useState('')
  const connectingRef = useRef(false)
  const skipNextRef = useRef(false)
  const [connectionState, setConnectionState] = useState<ConnectionState>('idle')

  const connect = useCallback(() => {
    const chatId = useAppStore.getState().activeChatId
    if (!chatId) return
    if (connectingRef.current) return
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return
    }

    connectingRef.current = true
    setConnectionState('connecting')
    skipNextRef.current = true

    const ws = createChatWebSocket((text, done) => {
      if (skipNextRef.current) {
        skipNextRef.current = false
        if (done) return
      }
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

      const state = useAppStore.getState()
      const contextPayload = buildContextPayload({
        character: state.character,
        stashTabs: state.stashTabs,
        characterCache: state.characterCache,
        includeAllCharactersInChat: state.includeAllCharactersInChat,
        activeCharacterPath: state.activeCharacterPath,
      })

      const itemIndex = buildItemIndex(
        state.character,
        state.stashTabs,
        state.characterCache,
        state.includeAllCharactersInChat,
        state.activeCharacterPath,
      )
      useAppStore.getState().setItemIndex(itemIndex)
      useAppStore.getState().setChatIdIndex(chatId, getIdIndex(), getStashTabIndex())

      contextPayload.chat_id = chatId
      const contextJson = JSON.stringify(contextPayload, null, 2)
      setChatContextPayload(chatId, contextJson)

      ws.send(JSON.stringify({ type: 'context', payload: JSON.stringify(contextPayload) }))
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
  }, [addMessageToChat, setChatStreaming, setChatContextPayload])

  useEffect(() => {
    if (!activeChat || !activeChat.itemIdIndex || Object.keys(activeChat.itemIdIndex).length === 0) return
    useAppStore.getState().setIdIndex(activeChat.itemIdIndex)
    useAppStore.getState().setStashTabIndex(activeChat.itemStashTabIndex)
  }, [activeChat])

  useEffect(() => {
    if (!activeChatId) return
    connect()
    return () => {
      setChatStreaming(false)
      streamingAccRef.current = ''
      setStreamingText('')
      connectingRef.current = false
      if (wsRef.current) {
        wsRef.current.onopen = null
        wsRef.current.onclose = null
        wsRef.current.onerror = null
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [activeChatId, includeAllCharactersInChat, connect, setChatStreaming])

  const handleSend = useCallback((message: string) => {
    const chatId = useAppStore.getState().activeChatId
    if (!chatId) return
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      addMessageToChat(chatId, { role: 'user', content: message })
      setChatStreaming(true)
      wsRef.current.send(JSON.stringify({ type: 'message', payload: message }))
    }
  }, [addMessageToChat, setChatStreaming])

  const messages = activeChat?.messages ?? []
  const charCount = Object.keys(characterCache).length

  const previewPayload = useMemo(() => {
    if (connectionState !== 'idle' || !activeChatId || !character) return null
    const ctx = buildContextPayload({
      character,
      stashTabs,
      characterCache,
      includeAllCharactersInChat,
      activeCharacterPath: useAppStore.getState().activeCharacterPath,
    })
    return JSON.stringify(ctx, null, 2)
  }, [connectionState, activeChatId, character, stashTabs, characterCache, includeAllCharactersInChat])

  return (
    <div className="flex flex-col h-full bg-d2-surface border border-d2-border rounded-lg overflow-hidden">
      <div className="px-4 py-2 border-b border-d2-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-d2 text-d2-accent">
            {activeChat?.title ?? 'Chat'}
          </h2>
          {connectionState === 'connected' && (
            <span className="w-2 h-2 rounded-full bg-green-500 inline-block" title="Connected" />
          )}
        </div>
        <label className="flex items-center gap-1.5 cursor-pointer select-none">
          <span className="text-[10px] text-d2-muted font-body">
            {includeAllCharactersInChat ? 'All characters' : 'Active character only'}
          </span>
          <button
            onClick={() => setIncludeAllCharactersInChat(!includeAllCharactersInChat)}
            disabled={charCount <= 1}
            className={`relative w-7 h-4 rounded-full transition-colors cursor-pointer ${
              includeAllCharactersInChat ? 'bg-d2-accent' : 'bg-d2-border'
            } ${charCount <= 1 ? 'opacity-30 cursor-not-allowed' : ''}`}
          >
            <span
              className={`absolute top-0.5 left-0.5 w-3 h-3 rounded-full bg-d2-bg transition-transform ${
                includeAllCharactersInChat ? 'translate-x-3' : ''
              }`}
            />
          </button>
        </label>
      </div>

        {connectionState === 'connecting' && (
          <div className="px-4 py-2 text-xs text-d2-accent font-body bg-d2-accent/10 border-b border-d2-accent/20">
            Connecting...
          </div>
        )}

        {connectionState === 'error' && (
          <div className="px-4 py-2 text-xs text-red-400 font-body bg-red-900/10 border-b border-red-800/20 flex items-center justify-between">
            <span>Cannot connect. Is the backend running on port 8000?</span>
            <button
              onClick={connect}
              className="text-d2-accent hover:text-d2-accent-hover cursor-pointer ml-2"
            >
              Retry
            </button>
          </div>
        )}

        {connectionState === 'idle' && previewPayload && (
          <ContextBlock payload={previewPayload} label="Preview system context (refresh page to update)" />
        )}

        {connectionState === 'connected' && activeChat?.contextPayload && (
          <ContextBlock payload={activeChat.contextPayload} label="System context sent to LLM" />
        )}

        <MessageList messages={messages} />
        {chatStreaming && (
          <div className="px-4 py-3 border-t border-d2-border">
            {streamingText ? (
              <div className="text-sm text-d2-ink font-body">
                <div className="whitespace-pre-wrap break-words">{streamingText}</div>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-d2-muted">
                <span className="font-body text-xs">Thinking</span>
                <span className="flex gap-0.5">
                  <span className="w-1 h-1 rounded-full bg-d2-accent animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1 h-1 rounded-full bg-d2-accent animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1 h-1 rounded-full bg-d2-accent animate-bounce" style={{ animationDelay: '300ms' }} />
                </span>
              </div>
            )}
          </div>
        )}
        <ChatInput onSend={handleSend} disabled={chatStreaming || connectionState !== 'connected'} />
    </div>
  )
}
