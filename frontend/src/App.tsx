import { useEffect, useState } from 'react'
import { useAppStore } from './store/appStore'
import { AppShell } from './components/Layout/AppShell'
import { Dashboard } from './components/Dashboard/Dashboard'
import { SearchView } from './components/Search/SearchView'
import { ChatPanel } from './components/Chat/ChatPanel'
import { SetsView } from './components/Sets/SetsView'

function App() {
  const { view, character, stashTabs } = useAppStore()
  const [init, setInit] = useState(useAppStore.persist.hasHydrated())

  useEffect(() => {
    const unsub = useAppStore.persist.onFinishHydration(() => setInit(true))
    return unsub
  }, [])

  useEffect(() => {
    if (!init) return

    const state = useAppStore.getState()
    const path = state.activeCharacterPath

    if (path && state.characterCache[path]) {
      state.setActiveCharacterPath(path)
    }

    state.fetchCharacters().then(() => {
      const s = useAppStore.getState()
      if (s.activeCharacterPath && !s.characterCache[s.activeCharacterPath]) {
        s.setActiveCharacterPath(s.activeCharacterPath)
        s.parseAndSetActive(s.activeCharacterPath)
      }
    })

    state.fetchChatsFromBackend()
  }, [init])

  return (
    <AppShell>
      {view === 'dashboard' && character && (
        <Dashboard character={character} stashTabs={stashTabs} />
      )}
      {view === 'search' && <SearchView />}
      {view === 'chat' && (
        <div className="h-[calc(100vh-3rem)]">
          <ChatPanel />
        </div>
      )}
      {view === 'sets' && <SetsView />}
    </AppShell>
  )
}

export default App
