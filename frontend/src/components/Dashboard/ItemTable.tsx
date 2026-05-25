import type { ParsedItem } from '../../types'
import { getItemDisplayName, getItemBaseName } from '../../types'

function qualityBorderClass(quality: number): string {
  switch (quality) {
    case 7: return 'border-l-d2-unique'
    case 5: return 'border-l-d2-set'
    case 6: return 'border-l-d2-rare'
    case 4: return 'border-l-d2-magic'
    case 8: return 'border-l-d2-craft'
    default: return 'border-l-d2-border'
  }
}

function qualityTextClass(quality: number): string {
  switch (quality) {
    case 7: return 'text-d2-unique'
    case 5: return 'text-d2-set'
    case 6: return 'text-d2-rare'
    case 4: return 'text-d2-magic'
    case 8: return 'text-d2-craft'
    default: return 'text-d2-ink'
  }
}

export function ItemCard({ item, compact }: { item: ParsedItem; compact?: boolean }) {
  const displayName = getItemDisplayName(item)
  const baseName = getItemBaseName(item)
  const reqParts: string[] = []
  if (item.req_level) reqParts.push(`Lvl ${item.req_level}`)
  if (item.req_str) reqParts.push(`Str ${item.req_str}`)
  if (item.req_dex) reqParts.push(`Dex ${item.req_dex}`)
  const socketedText = item.socketed_items
    .map((s) => s.item_name ?? s.code ?? '?')
    .join(', ')
  const propLimit = compact ? 3 : Infinity
  const props = item.properties.filter((p) => p.display_text)

  return (
    <div
      className={`border-l-4 rounded-lg p-3 bg-d2-surface text-sm h-full ${qualityBorderClass(item.quality)}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className={`font-bold text-sm font-d2 truncate ${qualityTextClass(item.quality)}`}>
            {item.ethereal && <span className="text-d2-muted">Eth </span>}
            {displayName}
          </div>
          {baseName && <div className="text-d2-muted text-xs truncate">{baseName}</div>}
          {item.weapon_damage && <div className="text-d2-ink text-xs mt-0.5">{item.weapon_damage}</div>}
          {reqParts.length > 0 && (
            <div className="text-d2-muted text-xs mt-0.5">Req: {reqParts.join(', ')}</div>
          )}
          {props.slice(0, propLimit).map((p, i) => (
            <div key={i} className="text-d2-magic text-xs leading-tight mt-0.5 truncate">
              {p.display_text}
            </div>
          ))}
          {props.length > propLimit && (
            <div className="text-d2-muted text-[10px] mt-0.5">+{props.length - propLimit} more</div>
          )}
          {socketedText && (
            <div className="text-d2-muted text-[10px] mt-1 truncate">Socketed: {socketedText}</div>
          )}
        </div>
        {item.stacks != null && (
          <div className="text-xs text-d2-accent font-mono whitespace-nowrap">x{item.stacks}</div>
        )}
      </div>
    </div>
  )
}

export function ItemTable({ items, title }: { items: ParsedItem[]; title: string }) {
  if (items.length === 0) return null

  return (
    <div className="bg-d2-surface border border-d2-border rounded-lg overflow-hidden">
      <div className="px-4 py-2 border-b border-d2-border flex items-center justify-between">
        <h2 className="text-sm font-d2 text-d2-accent">{title}</h2>
        <span className="text-xs text-d2-muted">{items.length}</span>
      </div>
      <div className="p-3 grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 max-h-[28rem] overflow-y-auto scrollbar-thin">
        {items.map((item) => (
          <ItemCard key={`${item.location}-${item.position}-${item.index}-${item.x}-${item.y}`} item={item} />
        ))}
      </div>
    </div>
  )
}
