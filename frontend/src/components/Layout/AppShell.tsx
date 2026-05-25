import type { ReactNode } from 'react'
import { useAppStore } from '../../store/appStore'
import { CharacterPicker } from './CharacterPicker'
import { ChatSidebar } from '../Chat/ChatSidebar'

type View = 'dashboard' | 'search' | 'chat' | 'sets'

const NAV_ITEMS: { view: View; label: string; icon: string }[] = [
  { view: 'dashboard', label: 'Dashboard', icon: '◆' },
  { view: 'search', label: 'Search', icon: '⌕' },
  { view: 'sets', label: 'Sets', icon: '◈' },
  { view: 'chat', label: 'Chat', icon: '💬' },
]

export function AppShell({ children }: { children: ReactNode }) {
  const { view, setView, character, loading, error, createChat } = useAppStore()

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
                if (v === 'chat') {
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
            <div className="text-xs text-d2-muted font-body truncate">
              {character.status.hardcore && <span className="text-red-400 mr-1">HC</span>}
              {character.name} — {character.character_type} Lvl {character.level}
            </div>
            {Array.isArray(character.parse_warnings) && character.parse_warnings.length > 0 && (
              <div className="text-[10px] text-amber-500 mt-1 font-body">
                ⚠ {character.parse_warnings.length} warning{character.parse_warnings.length !== 1 ? 's' : ''}
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
