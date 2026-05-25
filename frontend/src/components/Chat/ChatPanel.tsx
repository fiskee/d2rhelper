import { useEffect, useRef, useCallback, useState } from 'react'
import { useAppStore } from '../../store/appStore'
import { createChatWebSocket } from '../../api/client'
import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'

type ConnectionState = 'idle' | 'connecting' | 'connected' | 'error'

export function ChatPanel() {
  const {
    chatMessages,
    chatStreaming,
    addChatMessage,
    setChatStreaming,
    clearChat,
    character,
    stashTabs,
  } = useAppStore()

  const wsRef = useRef<WebSocket | null>(null)
  const streamingRef = useRef('')
  const connectingRef = useRef(false)
  const mountedRef = useRef(false)
  const skipNextRef = useRef(false)
  const [connectionState, setConnectionState] = useState<ConnectionState>('idle')

  const connect = useCallback(() => {
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
      streamingRef.current += text
      if (done) {
        if (streamingRef.current.trim()) {
          addChatMessage({ role: 'assistant', content: streamingRef.current })
        }
        streamingRef.current = ''
        setChatStreaming(false)
      } else {
        setChatStreaming(true)
      }
    })

    ws.onopen = () => {
      connectingRef.current = false
      setConnectionState('connected')

      const context = JSON.stringify({
        character: character ? {
          name: character.name,
          level: character.level,
          character_type: character.character_type,
          attributes: character.attributes,
          skills: character.skills,
          items: character.items,
          mercenary: character.mercenary,
        } : null,
        stash_tabs: stashTabs,
      })
      ws.send(JSON.stringify({ type: 'context', payload: context }))
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
        if (mountedRef.current) {
          setConnectionState('error')
        }
      }
    }

    wsRef.current = ws
  }, [character, stashTabs, addChatMessage, setChatStreaming])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      setChatStreaming(false)
      streamingRef.current = ''
      connectingRef.current = false
      if (wsRef.current) {
        wsRef.current.onopen = null
        wsRef.current.onclose = null
        wsRef.current.onerror = null
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [connect, setChatStreaming])

  const handleSend = (message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      addChatMessage({ role: 'user', content: message })
      setChatStreaming(true)
      wsRef.current.send(JSON.stringify({ type: 'message', payload: message }))
    }
  }

  return (
    <div className="flex flex-col h-full bg-d2-surface border border-d2-border rounded-lg overflow-hidden">
      <div className="px-4 py-2 border-b border-d2-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-d2 text-d2-accent">Chat</h2>
          {connectionState === 'connected' && (
            <span className="w-2 h-2 rounded-full bg-green-500 inline-block" title="Connected" />
          )}
        </div>
        <button
          onClick={clearChat}
          className="text-xs text-d2-muted hover:text-d2-ink transition-colors cursor-pointer font-body"
        >
          Clear
        </button>
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

      <MessageList messages={chatMessages} />
      {chatStreaming && (
        <div className="px-4 py-3 border-t border-d2-border">
          {streamingRef.current ? (
            <div className="text-sm text-d2-ink font-body">
              <div className="whitespace-pre-wrap break-words">{streamingRef.current}</div>
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
