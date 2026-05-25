import { useEffect } from 'react'
import { useAppStore } from '../../store/appStore'
import type { TaggedItem } from '../../store/appStore'
import type { SetData } from '../../types'

interface PlayerSetProgress {
  setName: string
  owned: number
  total: number
  pieces: {
    name: string
    code: string
    base: string
    owned: boolean
    source: string | null
  }[]
}

function sourceLabel(ti: TaggedItem | undefined): string | null {
  if (!ti) return null
  if (ti.source === 'stash') {
    return `Shared stash tab ${(ti.tabIndex ?? 0) + 1}`
  }

  let charName = ''
  if (ti.characterPath) {
    const parts = ti.characterPath.split(/[/\\]/)
    charName = (parts[parts.length - 1] ?? ti.characterPath).replace(/\.d2s$/i, '')
  }

  if (ti.source === 'mercenary') {
    return charName ? `${charName} — Mercenary` : 'Mercenary'
  }

  const loc = ti.item.location
  let sub = ''
  if (loc === 1) sub = 'Equipped'
  else if (loc === 2) sub = 'Inventory'
  else if (loc === 4) sub = 'Personal stash'
  else if (loc === 3) sub = 'Horadric Cube'
  else if (loc === 6) sub = 'Belt'

  if (charName && sub) return `${charName} — ${sub}`
  if (charName) return charName
  return sub || ti.source
}

function computePlayerSets(allItems: TaggedItem[], sets: SetData[]): PlayerSetProgress[] {
  const owned: Record<string, TaggedItem> = {}
  for (const ti of allItems) {
    if (ti.item.set_name && !owned[ti.item.set_name]) {
      owned[ti.item.set_name] = ti
    }
  }

  return sets
    .map((set) => {
      const ownedCount = set.items.filter((si) => si.name in owned).length
      return {
        setName: set.name,
        owned: ownedCount,
        total: set.items.length,
        pieces: set.items.map((si) => {
          const item = owned[si.name]
          return {
            name: si.name,
            code: si.code,
            base: si.base,
            owned: item != null,
            source: sourceLabel(item),
          }
        }),
      }
    })
    .filter((s) => s.owned > 0)
    .sort((a, b) => b.owned / b.total - a.owned / a.total || b.total - a.total || a.setName.localeCompare(b.setName))
}

export function SetsView() {
  const { characterCache, stashTabs, setData, fetchSetData } = useAppStore()

  useEffect(() => {
    if (setData === null) {
      fetchSetData()
    }
  }, [setData, fetchSetData])

  if (!setData) {
    return (
      <div className="text-center text-d2-muted font-body py-12 text-sm">
        Loading set data...
      </div>
    )
  }

  const allSetItems: TaggedItem[] = []
  for (const path of Object.keys(characterCache)) {
    const char = characterCache[path]
    if (!char) continue
    for (const item of char.items) {
      if (item.set_name) {
        allSetItems.push({ item, source: 'character', characterPath: path })
      }
    }
    for (const item of char.mercenary.items) {
      if (item.set_name) {
        allSetItems.push({ item, source: 'mercenary', characterPath: path })
      }
    }
  }
  for (const tab of stashTabs) {
    for (const item of tab.items) {
      if (item.set_name) {
        allSetItems.push({ item, source: 'stash', tabIndex: tab.index })
      }
    }
  }

  const playerSets = computePlayerSets(allSetItems, setData)

  if (playerSets.length === 0) {
    return (
      <div className="text-center text-d2-muted font-body py-12">
        <div className="text-3xl mb-3">&#9876;</div>
        <p className="text-sm">No set items found across characters or stash</p>
        <p className="text-xs mt-1 text-d2-muted/60">Parse a character to start tracking set progress</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
      {playerSets.map((set) => {
        const pct = Math.round((set.owned / set.total) * 100)
        const complete = set.owned === set.total

        return (
          <div
            key={set.setName}
            className="bg-d2-surface border border-d2-border rounded-lg overflow-hidden"
          >
            <div className="px-4 py-3 border-b border-d2-border flex items-center justify-between">
              <div>
                <h3 className="text-sm font-d2 text-d2-ink">
                  {set.setName}
                </h3>
                <p className="text-xs text-d2-muted font-body mt-0.5">
                  {set.owned} / {set.total} pieces{complete && <span className="text-d2-set ml-1">&mdash; Complete!</span>}
                </p>
              </div>
            </div>

            <div className="px-2 pt-1">
              <div className="w-full h-1.5 bg-d2-bg rounded-full overflow-hidden mb-2">
                <div
                  className={`h-full rounded-full transition-all ${complete ? 'bg-d2-set' : 'bg-d2-accent'}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>

            <div className="p-3 pt-1 space-y-1">
              {set.pieces.map((piece) => (
                <div
                  key={piece.name}
                  className={`flex items-center gap-2 px-2 py-1 rounded text-sm font-body ${
                    piece.owned
                      ? 'text-d2-set'
                      : 'text-d2-muted/50'
                  }`}
                >
                  <span className="w-4 text-center text-xs">
                    {piece.owned ? '✓' : '✗'}
                  </span>
                  <span className="flex-1 truncate">
                    {piece.name}
                  </span>
                  <span className="text-xs text-d2-muted shrink-0">
                    {piece.base}
                  </span>
                  {piece.source && (
                    <span className="text-[10px] text-d2-accent/70 shrink-0 ml-1">
                      {piece.source}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
