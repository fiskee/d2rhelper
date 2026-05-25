import { useMemo } from 'react'
import { useAppStore } from '../../store/appStore'
import type { TaggedItem } from '../../store/appStore'
import { getItemDisplayName, ITEM_QUALITY_NAMES, EQUIPMENT_SLOTS } from '../../types'
import { ItemCard } from '../Dashboard/ItemTable'

function getSourceLabel(tagged: TaggedItem, characterName?: string): string {
  const { item, source, tabIndex, characterPath } = tagged
  const pos = `(${item.x}, ${item.y})`
  const charLabel = characterPath ? `[${characterName ?? '?'}] ` : ''

  if (source === 'stash') {
    const tabLabel = tabIndex != null ? `Tab ${tabIndex + 1}` : 'Shared Stash'
    return `Shared Stash — ${tabLabel} ${pos}`
  }

  if (source === 'mercenary') {
    if (item.location === 1) {
      const slot = EQUIPMENT_SLOTS[item.position]
      return `${charLabel}Mercenary — ${slot?.name ?? 'Equipment'}`
    }
    return `${charLabel}Mercenary ${pos}`
  }

  if (item.location === 1) {
    const slot = EQUIPMENT_SLOTS[item.position]
    return `${charLabel}${slot?.name ?? 'Equipment'}`
  }
  if (item.location === 2) return `${charLabel}Belt ${pos}`
  if (item.location === 0 && item.container === 1) return `${charLabel}Inventory ${pos}`
  if (item.location === 0 && item.container === 4) return `${charLabel}Cube ${pos}`
  if (item.location === 0 && item.container === 5) return `${charLabel}Personal Stash ${pos}`
  if (item.location === 6) return `${charLabel}Socketed`
  return `${charLabel}${pos}`
}

function startsWord(text: string, q: string): boolean {
  try {
    return new RegExp('\\b' + q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i').test(text)
  } catch {
    return text.toLowerCase().includes(q)
  }
}

export function SearchResults() {
  const { searchQuery, allItems, character, characterCache } = useAppStore()

  function getCharName(charPath: string): string {
    return characterCache[charPath]?.name ?? '?'
  }

  const results = useMemo(() => {
    if (!searchQuery.trim() || searchQuery.length < 2) return []
    const q = searchQuery.toLowerCase().trim()

    return allItems
      .map((tagged) => {
        const { item } = tagged
        let score = 0
        const displayName = getItemDisplayName(item).toLowerCase()

        if (displayName === q) {
          score += 300
        } else if (displayName.startsWith(q)) {
          score += 200
        } else if (startsWord(displayName, q)) {
          score += 100
        } else if (displayName.includes(q)) {
          score += 30
        }

        const baseName = (item.item_name ?? '').toLowerCase()
        if (baseName === q) {
          score += 250
        } else if (baseName.startsWith(q)) {
          score += 150
        } else if (startsWord(baseName, q)) {
          score += 80
        } else if (baseName.includes(q)) {
          score += 20
        }

        const setName = (item.set_name ?? '').toLowerCase()
        if (setName === q) score += 200
        else if (setName.startsWith(q)) score += 120
        else if (startsWord(setName, q)) score += 60

        const rwName = (item.runeword_name ?? '').toLowerCase()
        if (rwName === q) score += 200
        else if (rwName.startsWith(q)) score += 120
        else if (startsWord(rwName, q)) score += 60

        const uniqName = (item.unique_name ?? '').toLowerCase()
        if (uniqName === q) score += 200
        else if (uniqName.startsWith(q)) score += 120
        else if (startsWord(uniqName, q)) score += 60

        const code = (item.code ?? '').toLowerCase()
        if (code === q) score += 40

        const qualityName = (ITEM_QUALITY_NAMES[item.quality] ?? '').toLowerCase()
        if (qualityName === q) score += 40

        for (const prop of item.properties) {
          const text = (prop.display_text ?? '').toLowerCase()
          if (!text) continue
          if (startsWord(text, q)) score += 30
        }

        return { tagged, score }
      })
      .filter((r) => r.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 50)
  }, [searchQuery, allItems])

  if (!searchQuery.trim()) {
    return (
      <div className="text-center text-d2-muted py-16 font-body">
        <div className="text-4xl mb-3">&#9876;</div>
        <p className="text-sm">Search for items across your character and stash</p>
        <p className="text-xs mt-1">Try names, properties, set bonuses, or runewords</p>
      </div>
    )
  }

  if (searchQuery.length < 2) {
    return (
      <div className="text-center text-d2-muted py-16 font-body text-sm">
        Type at least 2 characters to search
      </div>
    )
  }

  if (results.length === 0) {
    return (
      <div className="text-center text-d2-muted py-16 font-body">
        <p className="text-sm">No items found matching "{searchQuery}"</p>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-d2-muted font-body">
          {results.length} result{results.length !== 1 ? 's' : ''}
        </span>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {results.map(({ tagged }) => (
          <div key={`${tagged.source}-${tagged.tabIndex ?? ''}-${tagged.item.location}-${tagged.item.position}-${tagged.item.index}-${tagged.item.start_bit}`}>
            <div className="text-[10px] text-d2-muted mb-1 font-body tracking-wide uppercase truncate">
              {getSourceLabel(tagged, tagged.characterPath ? getCharName(tagged.characterPath) : character?.name)}
            </div>
            <ItemCard item={tagged.item} compact />
          </div>
        ))}
      </div>
    </div>
  )
}
