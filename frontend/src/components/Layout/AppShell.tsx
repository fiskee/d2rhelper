import type { ReactNode } from 'react'
import { useState, useEffect } from 'react'
import { useAppStore } from '../../store/appStore'
import { CharacterPicker } from './CharacterPicker'
import { ChatSidebar } from '../Chat/ChatSidebar'

type View = 'dashboard' | 'search' | 'chat' | 'sets' | 'planner'

const NAV_ITEMS: { view: View; label: string; icon: string }[] = [
  { view: 'dashboard', label: 'Dashboard', icon: '◆' },
  { view: 'search', label: 'Search', icon: '⌕' },
  { view: 'sets', label: 'Sets', icon: '◈' },
  { view: 'planner', label: 'Planner', icon: '✦' },
  { view: 'chat', label: 'Chat', icon: '💬' },
]

export function AppShell({ children }: { children: ReactNode }) {
  const { view, setView, character, loading, error, createChat, activeChatId } = useAppStore()
  const [warningsOpen, setWarningsOpen] = useState(false)
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex h-screen bg-d2-bg">
      <aside className="w-64 bg-d2-surface border-r border-d2-border flex flex-col shrink-0">
        <div className="px-4 py-4 border-b border-d2-border">
          <h1 className="text-xl font-d2 font-bold text-d2-accent tracking-wide">D2R Helper</h1>
          <p className="text-[10px] text-d2-muted font-body mt-0.5">Diablo II: Resurrected</p>
        </div>

        <div className="p-3 border-b border-d2-border">
          <CharacterPicker />
        </div>

        {error && (
          <div className="px-3 py-2 bg-red-900/20 border-b border-red-800/30 text-xs text-red-400 font-body">
            {error}
          </div>
        )}

        {loading && (
          <div className="px-3 py-2 bg-d2-accent/10 border-b border-d2-accent/20 text-xs text-d2-accent font-body">
            Parsing...
          </div>
        )}

        <nav className="p-3 flex flex-col gap-1">
          {NAV_ITEMS.map(({ view: v, label, icon }) => (
            <button
              key={v}
              onClick={() => {
                if (v === 'chat' && !activeChatId) {
                  createChat()
                }
                setView(v)
              }}
              disabled={!character && v !== 'sets'}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors cursor-pointer
                disabled:opacity-30 disabled:cursor-not-allowed font-body
                ${view === v
                  ? 'bg-d2-accent/20 text-d2-accent'
                  : 'text-d2-muted hover:text-d2-ink hover:bg-d2-bg'
                }`}
            >
              <span className="w-5 text-center">{icon}</span>
              {label}
            </button>
          ))}
        </nav>

        {view === 'chat' && (
          <div className="flex-1 overflow-y-auto scrollbar-thin min-h-0">
            <ChatSidebar />
          </div>
        )}

        {character && (
          <div className="p-3 border-t border-d2-border">
            {character.status.hardcore && (
              <div className="text-xs text-red-400 font-body mb-0.5">Hardcore</div>
            )}
            <div className="text-[10px] text-d2-muted font-body">
              Updated{' '}
              {(() => {
                const parsedMs = new Date(character.parsed_at).getTime()
                const diff = Math.max(0, now - parsedMs)
                const secs = Math.floor(diff / 1000)
                if (secs < 60) return 'just now'
                const mins = Math.floor(secs / 60)
                if (mins < 60) return `${mins}m ago`
                const hours = Math.floor(mins / 60)
                return `${hours}h ago`
              })()}
            </div>
            {Array.isArray(character.parse_warnings) && character.parse_warnings.length > 0 && (
              <div
                className="text-[10px] text-amber-500 mt-1 font-body cursor-pointer hover:text-amber-500/80 select-none"
                onClick={() => setWarningsOpen(!warningsOpen)}
              >
                ⚠ {character.parse_warnings.length} warning{character.parse_warnings.length !== 1 ? 's' : ''}
                {warningsOpen && (
                  <ul className="text-xs text-d2-muted mt-1 list-disc list-inside space-y-0.5">
                    {character.parse_warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        )}
      </aside>

      <main className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="p-6 max-w-6xl mx-auto">
          {!character && view !== 'sets' ? (
            <div className="flex items-center justify-center h-full min-h-[60vh]">
              <div className="text-center text-d2-muted font-body">
                <div className="text-5xl mb-4">&#9876;</div>
                <p className="text-lg font-d2 text-d2-accent">D2R Helper</p>
                <p className="text-sm mt-2">Drop a character file path to get started</p>
              </div>
            </div>
          ) : (
            children
          )}
        </div>
      </main>
    </div>
  )
}
