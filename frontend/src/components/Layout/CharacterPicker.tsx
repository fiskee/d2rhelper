import { useState } from 'react'
import { useAppStore } from '../../store/appStore'

export function CharacterPicker() {
  const {
    characters,
    characterCache,
    activeCharacterPath,
    stashPath,
    loading,
    fetchCharacters,
    parseAndSetActive,
    setError,
  } = useAppStore()

  const [detecting, setDetecting] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [manualPath, setManualPath] = useState('')
  const [manualStash, setManualStash] = useState('')

  const handleDetect = async () => {
    setDetecting(true)
    await fetchCharacters()
    setDetecting(false)
  }

  const handleSelect = (path: string) => {
    if (path === activeCharacterPath) return
    parseAndSetActive(path)
  }

  const handleManualParse = async () => {
    if (!manualPath.trim()) return
    try {
      await parseAndSetActive(manualPath.trim(), manualStash.trim() || null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Parse failed')
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs text-d2-muted font-body">Characters</label>
          <button
            onClick={handleDetect}
            disabled={detecting}
            className="text-[10px] text-d2-accent hover:text-d2-accent-hover transition-colors
                       cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed font-body"
          >
            {detecting ? 'Detecting...' : 'Auto-detect'}
          </button>
        </div>

        {characters.length > 0 ? (
          <select
            value={activeCharacterPath ?? ''}
            onChange={(e) => handleSelect(e.target.value)}
            disabled={loading}
            className="w-full bg-d2-bg border border-d2-border rounded px-3 py-2 text-sm text-d2-ink
                       focus:outline-none focus:border-d2-accent font-body cursor-pointer
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <option value="" disabled>Select a character</option>
            {characters.map((c) => {
              const cached = characterCache[c.path]
              const displayLevel = cached ? cached.level : c.level
              const prefix = c.hardcore ? '[HC] ' : ''
              return (
                <option key={c.path} value={c.path}>
                  {prefix}{c.name} ({c.character_type}, lvl {displayLevel})
                </option>
              )
            })}
          </select>
        ) : (
          <div className="text-xs text-d2-muted font-body py-2 px-3 bg-d2-surface/50 border border-d2-border rounded">
            Click "Auto-detect" to find your D2R characters, or use the manual path option below.
          </div>
        )}
      </div>

      <button
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="text-[10px] text-d2-muted hover:text-d2-ink transition-colors text-left cursor-pointer font-body"
      >
        {showAdvanced ? 'Hide manual path' : 'Manual path input'}
      </button>

      {showAdvanced && (
        <div className="flex flex-col gap-2">
          <div>
            <label className="block text-xs text-d2-muted mb-1 font-body">Character File (.d2s)</label>
            <input
              type="text"
              placeholder="/path/to/character.d2s"
              value={manualPath}
              onChange={(e) => setManualPath(e.target.value)}
              className="w-full bg-d2-bg border border-d2-border rounded px-3 py-2 text-sm text-d2-ink
                         placeholder:text-d2-muted focus:outline-none focus:border-d2-accent font-body"
            />
          </div>
          <div>
            <label className="block text-xs text-d2-muted mb-1 font-body">
              Shared Stash (.d2i) — optional
              {stashPath && (
                <span className="text-d2-accent ml-1">(detected: {stashPath.split('/').pop()?.split('\\').pop()})</span>
              )}
            </label>
            <input
              type="text"
              placeholder={stashPath ?? '/path/to/SharedStash.d2i'}
              value={manualStash}
              onChange={(e) => setManualStash(e.target.value)}
              className="w-full bg-d2-bg border border-d2-border rounded px-3 py-2 text-sm text-d2-ink
                         placeholder:text-d2-muted focus:outline-none focus:border-d2-accent font-body"
            />
          </div>
          <button
            onClick={handleManualParse}
            disabled={!manualPath.trim() || loading}
            className="bg-d2-accent hover:bg-d2-accent-hover disabled:opacity-40 text-d2-bg font-semibold
                       px-4 py-2 rounded text-sm transition-colors cursor-pointer disabled:cursor-not-allowed font-body"
          >
            Parse Character
          </button>
        </div>
      )}
    </div>
  )
}
