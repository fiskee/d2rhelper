import type { ParsedItem } from '../../types'
import { EQUIPMENT_SLOTS, getItemDisplayName, getItemBaseName } from '../../types'

function qualityBorderClass(quality: number): string {
  switch (quality) {
    case 7: return 'border-d2-unique'
    case 5: return 'border-d2-set'
    case 6: return 'border-d2-rare'
    case 4: return 'border-d2-magic'
    case 8: return 'border-d2-craft'
    default: return 'border-d2-border'
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

function ItemSlot({
  item,
  slotLabel,
  slotArea,
}: {
  item?: ParsedItem
  slotLabel: string
  slotArea: string
}) {
  if (!item) {
    return (
      <div
        className="border border-d2-border rounded-lg p-2 min-h-24 flex flex-col items-center justify-center
                   bg-d2-surface/50 text-d2-muted text-xs"
        style={{ gridArea: slotArea }}
      >
        <span className="text-[10px] uppercase tracking-wider text-d2-accent/60 font-d2">{slotLabel}</span>
        <span className="italic mt-1">(empty)</span>
      </div>
    )
  }

  const displayName = getItemDisplayName(item)
  const baseName = getItemBaseName(item)
  const reqParts: string[] = []
  if (item.req_level) reqParts.push(`Lvl ${item.req_level}`)
  if (item.req_str) reqParts.push(`Str ${item.req_str}`)
  if (item.req_dex) reqParts.push(`Dex ${item.req_dex}`)
  const socketedText = item.socketed_items
    .map((s) => s.item_name ?? s.code ?? '?')
    .join(', ')

  return (
    <div
      className={`border-2 rounded-lg p-2 min-h-24 flex flex-col text-xs bg-d2-surface
        ${qualityBorderClass(item.quality)}`}
      style={{ gridArea: slotArea }}
    >
      <span className="text-[10px] uppercase tracking-wider text-d2-accent/60 font-d2">{slotLabel}</span>
      <span className={`font-bold text-sm mt-0.5 ${qualityTextClass(item.quality)} font-d2`}>
        {item.ethereal && <span className="text-d2-muted">Eth </span>}
        {displayName}
      </span>
      {baseName && <span className="text-d2-muted text-[11px]">{baseName}</span>}
      {item.weapon_damage && <span className="text-d2-ink mt-0.5">{item.weapon_damage}</span>}
      {reqParts.length > 0 && (
        <span className="text-d2-muted mt-0.5">Req: {reqParts.join(', ')}</span>
      )}
      {item.properties
        .filter((p) => p.display_text)
        .slice(0, 4)
        .map((p, i) => (
          <span key={i} className="text-d2-magic text-[11px] leading-tight">
            {p.display_text}
          </span>
        ))}
      {socketedText && <span className="text-d2-muted text-[10px] mt-0.5">({socketedText})</span>}
    </div>
  )
}

export function EquipmentGrid({ items }: { items: ParsedItem[] }) {
  const equipped = new Map(items.map((i) => [i.position, i]))

  return (
    <div
      className="grid gap-2 p-4 mx-auto max-w-[520px]"
      style={{
        gridTemplateAreas: `
          ".      helm    amulet  ."
          "weapon armor   armor   shield"
          "gloves belt    belt    boots"
          "ringr  .       .       ringl"
          ".      swapw   swaps   ."
        `,
        gridTemplateColumns: '1fr 1fr 1fr 1fr',
      }}
    >
      {Array.from({ length: 12 }, (_, i) => i + 1).map((pos) => {
        const slot = EQUIPMENT_SLOTS[pos]
        return <ItemSlot key={pos} item={equipped.get(pos)} slotLabel={slot.name} slotArea={slot.area} />
      })}
    </div>
  )
}

export function MercenaryGrid({ items }: { items: ParsedItem[] }) {
  const equipped = new Map(items.map((i) => [i.position, i]))

  return (
    <div
      className="grid gap-2 p-4 mx-auto max-w-[520px]"
      style={{
        gridTemplateAreas: `
          ".        merc_helm    .          ."
          "merc_weapon merc_armor merc_shield ."
        `,
        gridTemplateColumns: '1fr 1fr 1fr 1fr',
      }}
    >
      <ItemSlot item={equipped.get(1)} slotLabel="Helm" slotArea="merc_helm" />
      <ItemSlot item={equipped.get(4)} slotLabel="Weapon" slotArea="merc_weapon" />
      <ItemSlot item={equipped.get(5)} slotLabel="Shield" slotArea="merc_shield" />
      <ItemSlot item={equipped.get(3)} slotLabel="Armor" slotArea="merc_armor" />
    </div>
  )
}
