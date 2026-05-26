import { CharacterInfo } from './CharacterInfo'
import { EquipmentGrid, MercenaryGrid } from './EquipmentGrid'
import { ItemTable } from './ItemTable'
import { StashTabs } from './StashTabs'
import { QuestsPanel } from './QuestsPanel'
import { WaypointsPanel } from './WaypointsPanel'
import { SkillsPanel } from './SkillsPanel'

import type { D2Character, SharedStashTab } from '../../types'

function getCategoryItems(character: D2Character) {
  const equipped = character.items.filter((i) => i.location === 1)
  const belt = character.items
    .filter((i) => i.location === 2)
    .sort((a, b) => a.position - b.position)
  const inventory = character.items
    .filter((i) => i.location === 0 && i.container === 1)
    .sort((a, b) => a.y - b.y || a.x - b.x)
  const cube = character.items
    .filter((i) => i.location === 0 && i.container === 4)
    .sort((a, b) => a.y - b.y || a.x - b.x)
  const personalStash = character.items
    .filter((i) => i.location === 0 && i.container === 5)
    .sort((a, b) => a.y - b.y || a.x - b.x)
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

      <SkillsPanel skills={character.skills} skillPointsLeft={character.attributes.skill_points_left} />

      <QuestsPanel quests={character.quest_data} />

      <WaypointsPanel waypoints={character.waypoints} />

      <div className="bg-d2-surface border border-d2-border rounded-lg">
        <h2 className="px-4 pt-4 text-lg font-d2 text-d2-accent">Equipment</h2>
        <EquipmentGrid items={cats.equipped} />
      </div>

      <div className="bg-d2-surface border border-d2-border rounded-lg">
        <div className="px-4 pt-4 flex items-center justify-between">
          <h2 className="text-lg font-d2 text-d2-accent">Mercenary</h2>
          <div className="flex gap-3 text-xs text-d2-muted font-mono">
            {character.mercenary.hireling_name ? (
              <>
                <span className="text-d2-ink">{character.mercenary.hireling_name}{character.mercenary.hireling_subtype ? ` (${character.mercenary.hireling_subtype})` : ''}</span>
                {character.mercenary.hireling_skills.length > 0 && (
                  <span>{character.mercenary.hireling_skills.join(' / ')}</span>
                )}
              </>
            ) : (
              <span>Type: {character.mercenary.type_id}</span>
            )}
            <span>Exp: {character.mercenary.experience.toLocaleString()}</span>
          </div>
        </div>
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
