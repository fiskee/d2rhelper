import type { WaypointStatus } from '../../types'

const ACTS: { act: string; waypoints: string[] }[] = [
  {
    act: 'Act I',
    waypoints: [
      'Rogue Encampment', 'Cold Plains', 'Stony Field', 'Dark Wood', 'Black Marsh',
      'Outer Cloister', 'Jail', 'Inner Cloister', 'Catacombs',
    ],
  },
  {
    act: 'Act II',
    waypoints: [
      'Lut Gholein', 'Sewers', 'Dry Hills', 'Halls of the Dead', 'Far Oasis',
      'Lost City', 'Palace Cellar', 'Arcane Sanctuary', 'Canyon of the Magi',
    ],
  },
  {
    act: 'Act III',
    waypoints: [
      'Kurast Docks', 'Spider Forest', 'Great Marsh', 'Flayer Jungle',
      'Lower Kurast', 'Kurast Bazaar', 'Upper Kurast', 'Travincal', 'Durance of Hate',
    ],
  },
  {
    act: 'Act IV',
    waypoints: [
      'Pandemonium Fortress', 'City of the Damned', 'River of Flames',
    ],
  },
  {
    act: 'Act V',
    waypoints: [
      'Harrogath', 'Frigid Highlands', 'Arreat Plateau', 'Crystalline Passage',
      'Halls of Pain', 'Glacial Trail', 'Frozen Tundra', "The Ancients' Way", 'Worldstone Keep',
    ],
  },
]

export function WaypointsPanel({ waypoints }: { waypoints: WaypointStatus[] }) {
  return (
    <div className="bg-d2-surface border border-d2-border rounded-lg">
      <h2 className="px-4 pt-4 text-lg font-d2 text-d2-accent">Waypoints</h2>
      <div className="p-4 space-y-4">
        {waypoints.map((w) => {
          const wpSet = new Set(w.waypoints)
          const total = ACTS.reduce((sum, a) => sum + a.waypoints.length, 0)
          const unlocked = ACTS.reduce((sum, a) => sum + a.waypoints.filter((n) => wpSet.has(n)).length, 0)

          return (
            <div key={w.difficulty}>
              <h3 className="text-sm font-d2 text-d2-ink capitalize mb-3">
                {w.difficulty} ({unlocked}/{total})
              </h3>
              <div className="space-y-3">
                {ACTS.map((act) => {
                  const actUnlocked = act.waypoints.filter((n) => wpSet.has(n)).length
                  return (
                    <div key={act.act}>
                      <div className="flex items-baseline gap-2 mb-1.5">
                        <span className="text-xs font-d2 text-d2-muted">{act.act}</span>
                        <span className="text-xs text-d2-muted font-mono">
                          {actUnlocked}/{act.waypoints.length}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {act.waypoints.map((name) => {
                          const active = wpSet.has(name)
                          return (
                            <span
                              key={name}
                              className={`px-2 py-0.5 rounded text-xs font-mono border ${
                                active
                                  ? 'border-blue-800/50 bg-blue-950/30 text-blue-300'
                                  : 'border-d2-border bg-d2-bg text-d2-muted opacity-50'
                              }`}
                            >
                              {name}
                            </span>
                          )
                        })}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
