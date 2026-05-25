import { useState, useRef, useMemo } from 'react'
import { useAppStore } from '../../store/appStore'
import { getItemDisplayName } from '../../types'

export function SearchBar() {
  const { searchQuery, setSearchQuery, allItems } = useAppStore()
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [selectedIdx, setSelectedIdx] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)

  const suggestions = useMemo(() => {
    if (searchQuery.length < 2) return []
    const q = searchQuery.toLowerCase()
    const seen = new Set<string>()
    const matches: string[] = []

    for (const tagged of allItems) {
      const { item } = tagged
      const names = [
        getItemDisplayName(item),
        item.item_name,
        item.set_name,
        item.runeword_name,
        item.unique_name,
      ].filter((n): n is string => !!n)

      for (const name of names) {
        const lower = name.toLowerCase()
        if (lower.includes(q) && !seen.has(lower)) {
          seen.add(lower)
          matches.push(name)
        }
      }

      if (matches.length >= 8) break
    }

    matches.sort((a, b) => {
      const aExact = a.toLowerCase() === q
      const bExact = b.toLowerCase() === q
      if (aExact !== bExact) return aExact ? -1 : 1
      const aStarts = a.toLowerCase().startsWith(q)
      const bStarts = b.toLowerCase().startsWith(q)
      if (aStarts !== bStarts) return aStarts ? -1 : 1
      return 0
    })

    return matches.slice(0, 8)
  }, [searchQuery, allItems])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showSuggestions || suggestions.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIdx((prev) => Math.min(prev + 1, suggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIdx((prev) => Math.max(prev - 1, -1))
    } else if (e.key === 'Enter' && selectedIdx >= 0) {
      setSearchQuery(suggestions[selectedIdx])
      setShowSuggestions(false)
    } else if (e.key === 'Escape') {
      setShowSuggestions(false)
    }
  }

  return (
    <div className="relative">
      <div className="relative">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-d2-muted"
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          placeholder="Search items, sets, runewords, properties..."
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value)
            setShowSuggestions(true)
            setSelectedIdx(-1)
          }}
          onFocus={() => setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
          onKeyDown={handleKeyDown}
          className="w-full bg-d2-surface border border-d2-border rounded-lg pl-10 pr-4 py-3 text-sm text-d2-ink
                     placeholder:text-d2-muted focus:outline-none focus:border-d2-accent font-body"
        />
      </div>
      {showSuggestions && suggestions.length > 0 && (
        <div className="absolute z-10 top-full mt-1 w-full bg-d2-surface border border-d2-border rounded-lg shadow-lg overflow-hidden">
          {suggestions.map((s, i) => (
            <div
              key={s}
              className={`px-4 py-2 text-sm cursor-pointer font-body
                ${i === selectedIdx ? 'bg-d2-accent/20 text-d2-accent' : 'text-d2-ink hover:bg-d2-bg'}`}
              onMouseDown={() => {
                setSearchQuery(s)
                setShowSuggestions(false)
              }}
            >
              {s}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
