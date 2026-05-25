import { useState } from 'react'
import { parseCharacter, autoParse } from '../../api/client'
import { useAppStore } from '../../store/appStore'

export function FileUpload() {
  const [characterPath, setCharacterPath] = useState('')
  const [stashPath, setStashPath] = useState('')
  const [detecting, setDetecting] = useState(false)
  const { setCharacter, setLoading, setError, loading } = useAppStore()

  const handleParse = async () => {
    if (!characterPath.trim()) return
    setLoading(true)
    setError(null)
    try {
      const result = await parseCharacter(characterPath.trim(), stashPath.trim() || undefined)
      setCharacter(result.character, result.stash_tabs, characterPath.trim())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Parse failed')
      setLoading(false)
    }
  }

  const handleAutoDetect = async () => {
    setDetecting(true)
    try {
      const result = await autoParse()
      setCharacterPath(result.character_path ?? '')
      if (result.stash_path) setStashPath(result.stash_path)
    } catch {
      // silently fail, user can type manually
    }
    setDetecting(false)
  }

  return (
    <div className="flex flex-col gap-3">
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs text-d2-muted font-body">Character File (.d2s)</label>
          <button
            onClick={handleAutoDetect}
            disabled={detecting}
            className="text-[10px] text-d2-accent hover:text-d2-accent-hover transition-colors
                       cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed font-body"
          >
            {detecting ? 'Detecting...' : 'Auto-detect'}
          </button>
        </div>
        <input
          type="text"
          placeholder="/path/to/character.d2s"
          value={characterPath}
          onChange={(e) => setCharacterPath(e.target.value)}
          className="w-full bg-d2-bg border border-d2-border rounded px-3 py-2 text-sm text-d2-ink
                     placeholder:text-d2-muted focus:outline-none focus:border-d2-accent font-body"
        />
      </div>
      <div>
        <label className="block text-xs text-d2-muted mb-1 font-body">Shared Stash (.d2i) — optional</label>
        <input
          type="text"
          placeholder="/path/to/SharedStash.d2i"
          value={stashPath}
          onChange={(e) => setStashPath(e.target.value)}
          className="w-full bg-d2-bg border border-d2-border rounded px-3 py-2 text-sm text-d2-ink
                     placeholder:text-d2-muted focus:outline-none focus:border-d2-accent font-body"
        />
      </div>
      <button
        onClick={handleParse}
        disabled={!characterPath.trim() || loading}
        className="bg-d2-accent hover:bg-d2-accent-hover disabled:opacity-40 text-d2-bg font-semibold
                   px-4 py-2 rounded text-sm transition-colors cursor-pointer disabled:cursor-not-allowed font-body"
      >
        Parse Character
      </button>
    </div>
  )
}
