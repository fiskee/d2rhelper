import { useAppStore } from '../../store/appStore'
import type { Chat } from '../../types'

function formatTime(ts: number): string {
  const diff = Date.now() - ts
  if (diff < 0) return ''
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return new Date(ts).toLocaleDateString()
}

function lastMessagePreview(chat: Chat): string | null {
  for (let i = chat.messages.length - 1; i >= 0; i--) {
    const msg = chat.messages[i]
    if (msg.role === 'user' || msg.role === 'assistant') {
      const text = msg.content.slice(0, 60).replace(/\n/g, ' ')
      return text.length < msg.content.length ? text + '...' : text
    }
  }
  return null
}

export function ChatSidebar() {
  const {
    chats,
    activeChatId,
    createChat,
    deleteChat,
    setActiveChat,
  } = useAppStore()

  const sortedChats = [...chats].sort((a, b) => b.updatedAt - a.updatedAt)

  return (
    <>
      <div className="p-2 flex flex-col gap-1.5">
        <button
          onClick={() => createChat('tools')}
          className="w-full px-3 py-1.5 text-xs font-body text-d2-ink bg-d2-accent/10 hover:bg-d2-accent/20 border border-d2-accent/30 rounded-lg transition-colors cursor-pointer"
        >
          + New Chat (Tools)
        </button>
        <button
          onClick={() => createChat('full_context')}
          className="w-full px-3 py-1.5 text-xs font-body text-d2-ink bg-d2-accent/10 hover:bg-d2-accent/20 border border-d2-accent/30 rounded-lg transition-colors cursor-pointer"
        >
          + New Chat (Full Context)
        </button>
      </div>

      {sortedChats.length === 0 && (
        <div className="px-4 py-3 text-center text-d2-muted font-body text-xs">
          No chats yet
        </div>
      )}
      {sortedChats.map((chat) => {
        const isActive = chat.id === activeChatId
        const preview = lastMessagePreview(chat)
        const characterLabel = chat.characterName
          ? `${chat.characterName} (${chat.characterType})`
          : null

        return (
          <div
            key={chat.id}
            onClick={() => setActiveChat(chat.id)}
            className={`group px-3 py-2.5 border-b border-d2-border/50 cursor-pointer transition-colors ${
              isActive
                ? 'bg-d2-accent/15 border-l-2 border-l-d2-accent'
                : 'hover:bg-d2-bg border-l-2 border-l-transparent'
            }`}
          >
            <div className="flex items-start justify-between gap-1">
              <div className="text-sm font-body text-d2-ink truncate flex-1">
                {chat.title}
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  if (confirm('Delete this chat?')) {
                    deleteChat(chat.id)
                  }
                }}
                className="opacity-0 group-hover:opacity-100 text-d2-muted hover:text-red-400 cursor-pointer text-xs shrink-0 mt-0.5 transition-opacity"
                title="Delete chat"
              >
                &times;
              </button>
            </div>
            {characterLabel && (
              <div className="text-[11px] font-body text-d2-accent/70 truncate mt-0.5">
                {characterLabel}
              </div>
            )}
            {preview && (
              <div className="text-xs text-d2-muted truncate mt-0.5 font-body">
                {preview}
              </div>
            )}
            <div className="text-[10px] text-d2-muted/60 mt-1 font-body">
              {formatTime(chat.updatedAt)}
            </div>
          </div>
        )
      })}
    </>
  )
}
