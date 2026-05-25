import { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import type { ParsedItem } from '../../types'
import { getItemDisplayName, getItemBaseName } from '../../types'
import type { DBAttrs } from '../../api/client'

function qualityBorder(quality: string): string {
  switch (quality) {
    case 'unique': return 'border-d2-unique'
    case 'set': return 'border-d2-set'
    case 'rare': return 'border-d2-rare'
    case 'magic': return 'border-d2-magic'
    case 'craft': return 'border-d2-craft'
    default: return 'border-d2-border'
  }
}

function qualityText(quality: string): string {
  switch (quality) {
    case 'unique': return 'text-d2-unique'
    case 'set': return 'text-d2-set'
    case 'rare': return 'text-d2-rare'
    case 'magic': return 'text-d2-magic'
    case 'craft': return 'text-d2-craft'
    default: return 'text-d2-ink'
  }
}

function playerQualityString(q: number): string {
  if (q === 7) return 'unique'
  if (q === 5) return 'set'
  if (q === 6) return 'rare'
  if (q === 4) return 'magic'
  if (q === 8) return 'craft'
  return 'base'
}

function PlayerTooltip({ item }: { item: ParsedItem }) {
  const displayName = getItemDisplayName(item)
  const baseName = getItemBaseName(item)
  const quality = playerQualityString(item.quality)
  const reqs: string[] = []
  if (item.req_level) reqs.push(`Lvl ${item.req_level}`)
  if (item.req_str) reqs.push(`Str ${item.req_str}`)
  if (item.req_dex) reqs.push(`Dex ${item.req_dex}`)
  const socketedText = item.socketed_items
    ?.map((s) => s.item_name ?? s.code ?? '?')
    .join(', ')

  return (
    <div className={`bg-d2-surface border rounded-md p-2.5 min-w-56 max-w-72 shadow-lg z-[9999] ${qualityBorder(quality)}`}>
      <div className={`font-bold text-sm font-d2 ${qualityText(quality)}`}>
        {item.ethereal && <span className="text-d2-muted">Eth </span>}
        {displayName}
      </div>
      {baseName && <div className="text-d2-muted text-xs">{baseName}</div>}
      {item.weapon_damage && (
        <div className="text-d2-ink text-xs mt-0.5">{item.weapon_damage}</div>
      )}
      {reqs.length > 0 && (
        <div className="text-d2-muted text-xs mt-0.5">Req: {reqs.join(', ')}</div>
      )}
      {item.properties
        .filter((p) => p.display_text)
        .map((p, i) => (
          <div key={i} className="text-d2-magic text-[11px] leading-tight mt-0.5">
            {p.display_text}
          </div>
        ))}
      {socketedText && (
        <div className="text-d2-muted text-[10px] mt-1">Socketed: {socketedText}</div>
      )}
    </div>
  )
}

const QUALITY_CHIP: Record<string, string> = {
  unique: 'bg-d2-unique/20 text-d2-unique',
  set: 'bg-d2-set/20 text-d2-set',
  runeword: 'bg-d2-accent/20 text-d2-accent',
  base: 'bg-d2-border/20 text-d2-muted',
}

function DBTooltip({ item }: { item: DBAttrs }) {
  return (
    <div className={`bg-d2-surface border rounded-md p-2.5 min-w-56 max-w-72 shadow-lg z-[9999] ${qualityBorder(item.quality)}`}>
      <div className="flex items-center gap-1.5">
        <span className={`text-xs px-1 py-0.5 rounded font-d2 uppercase ${QUALITY_CHIP[item.quality] ?? QUALITY_CHIP.base}`}>
          {item.quality}
        </span>
      </div>
      <div className={`font-bold text-sm font-d2 mt-1 ${qualityText(item.quality)}`}>
        {item.name}
      </div>
      {item.base_name && (
        <div className="text-d2-muted text-xs">{item.base_name}</div>
      )}
      {item.base_hint && (
        <div className="text-d2-muted text-xs mt-0.5">{item.base_hint}</div>
      )}
      {item.type && (
        <div className="text-d2-muted text-xs mt-0.5">Type: {item.type}</div>
      )}
      {item.level_req != null && (
        <div className="text-d2-muted text-xs mt-0.5">Req Lvl: {item.level_req}</div>
      )}
      {item.runes && item.runes.length > 0 && (
        <div className="text-d2-accent text-xs mt-1">
          {item.runes.join(' + ')}
        </div>
      )}
      {item.properties.length > 0 && (
        <div className="mt-1.5">
          {item.properties.map((p, i) => (
            <div key={i} className="text-d2-magic text-[11px] leading-tight mt-0.5">
              {p}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function ItemLink({
  name,
  playerItem,
  dbItem,
}: {
  name: string
  playerItem?: ParsedItem
  dbItem?: DBAttrs
}) {
  const [hovered, setHovered] = useState(false)
  const anchorRef = useRef<HTMLSpanElement>(null)
  const [pos, setPos] = useState({ top: 0, left: 0 })

  useEffect(() => {
    if (hovered && anchorRef.current) {
      const rect = anchorRef.current.getBoundingClientRect()
      const gap = 4
      const top = rect.bottom + gap
      let left = rect.left

      if (left + 288 > window.innerWidth - 8) {
        left = window.innerWidth - 296
      }
      if (left < 8) left = 8

      setPos({ top, left })
    }
  }, [hovered])

  const quality = playerItem
    ? playerQualityString(playerItem.quality)
    : (dbItem?.quality ?? 'base')

  if (!playerItem && !dbItem) return <span>{name}</span>

  return (
    <>
      <span
        ref={anchorRef}
        className={`cursor-help underline decoration-dotted underline-offset-2 ${qualityText(quality)}`}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {name}
      </span>
      {hovered &&
        createPortal(
          <div
            className="fixed pointer-events-none"
            style={{ top: pos.top, left: pos.left }}
          >
            {playerItem ? (
              <PlayerTooltip item={playerItem} />
            ) : dbItem ? (
              <DBTooltip item={dbItem} />
            ) : null}
          </div>,
          document.body,
        )      }
    </>
  )
}

export function AreaLink({ name, info }: { name: string; info: string }) {
  const [hovered, setHovered] = useState(false)
  const anchorRef = useRef<HTMLSpanElement>(null)
  const [pos, setPos] = useState({ top: 0, left: 0 })

  useEffect(() => {
    if (hovered && anchorRef.current) {
      const rect = anchorRef.current.getBoundingClientRect()
      const gap = 4
      const top = rect.bottom + gap
      let left = rect.left

      if (left + 320 > window.innerWidth - 8) {
        left = window.innerWidth - 328
      }
      if (left < 8) left = 8

      setPos({ top, left })
    }
  }, [hovered])

  return (
    <>
      <span
        ref={anchorRef}
        className="cursor-help underline decoration-dotted underline-offset-2 text-d2-accent"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {name}
      </span>
      {hovered &&
        createPortal(
          <div
            className="fixed pointer-events-none"
            style={{ top: pos.top, left: pos.left }}
          >
            <div className="bg-d2-surface border border-d2-border rounded-md p-2.5 max-w-80 shadow-lg z-[9999]">
              <div className="text-xs font-d2 text-d2-accent mb-1">{name}</div>
              <div className="text-xs text-d2-ink font-body leading-relaxed">
                {info.split('|').map((line, i) => (
                  <div key={i} className="py-0.5">{line.trim()}</div>
                ))}
              </div>
            </div>
          </div>,
          document.body,
        )}
    </>
  )
}
