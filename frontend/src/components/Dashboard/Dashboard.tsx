import { CharacterInfo } from './CharacterInfo'
import { EquipmentGrid, MercenaryGrid } from './EquipmentGrid'
import { ItemTable } from './ItemTable'
import { StashTabs } from './StashTabs'

import type { D2Character, SharedStashTab } from '../../types'

function getCategoryItems(character: D2Character) {
  const equipped = character.items.filter((i) => i.location === 1)
  const belt = character.items.filter((i) => i.location === 2)
  const inventory = character.items.filter((i) => i.location === 0 && i.container === 1)
  const cube = character.items.filter((i) => i.location === 0 && i.container === 4)
  const personalStash = character.items.filter((i) => i.location === 0 && i.container === 5)
  const socketed = character.items.filter((i) => i.location === 6)
  const other = character.items.filter(
    (i) => ![...equipped, ...belt, ...inventory, ...cube, ...personalStash, ...socketed].includes(i),
  )
  return { equipped, belt, inventory, cube, personalStash, socketed, other }
}

export function Dashboard({
  character,
  stashTabs,
}: {
  character: D2Character
  stashTabs: SharedStashTab[]
}) {
  const cats = getCategoryItems(character)

  return (
    <div className="flex flex-col gap-4">
      <CharacterInfo character={character} />

      <div className="bg-d2-surface border border-d2-border rounded-lg">
        <h2 className="px-4 pt-4 text-lg font-d2 text-d2-accent">Equipment</h2>
        <EquipmentGrid items={cats.equipped} />
      </div>

      <div className="bg-d2-surface border border-d2-border rounded-lg">
        <h2 className="px-4 pt-4 text-lg font-d2 text-d2-accent">Mercenary</h2>
        <MercenaryGrid items={character.mercenary.items} />
      </div>

      <ItemTable items={cats.belt} title="Belt" />
      <ItemTable items={cats.inventory} title="Inventory" />
      <ItemTable items={cats.cube} title="Horadric Cube" />
      <ItemTable items={cats.personalStash} title="Personal Stash" />

      <StashTabs tabs={stashTabs} />

      <ItemTable items={cats.socketed} title="Socketed Items" />
      {cats.other.length > 0 && <ItemTable items={cats.other} title="Other / Unknown" />}
    </div>
  )
}
