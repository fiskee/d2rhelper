import type { QuestData } from '../../types'

const QUEST_INFO: Record<string, { name: string; description: string }> = {
  den_of_evil: { name: 'Den of Evil', description: 'Clear the Den of Evil' },
  radament: { name: "Radament's Lair", description: 'Kill Radament' },
  golden_bird: { name: 'Golden Bird', description: 'Find the Golden Bird' },
  resistance_scroll: { name: 'Prison of Ice', description: 'Rescue Anya · Scroll of Resistance' },
}

export function QuestsPanel({ quests }: { quests: QuestData[] }) {
  return (
    <div className="bg-d2-surface border border-d2-border rounded-lg">
      <h2 className="px-4 pt-4 text-lg font-d2 text-d2-accent">Quest Progress</h2>
      <div className="p-4 space-y-4">
        {quests.map((q) => (
          <div key={q.difficulty}>
            <h3 className="text-sm font-d2 text-d2-ink capitalize mb-2">{q.difficulty}</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {Object.entries(QUEST_INFO).map(([key, info]) => {
                const completed = Boolean(q[key as keyof QuestData])
                return (
                  <div
                    key={key}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm border ${
                      completed
                        ? 'border-green-800/40 bg-green-950/20 text-green-300'
                        : 'border-d2-border bg-d2-bg text-d2-muted'
                    }`}
                  >
                    <span className={`text-xs ${completed ? 'text-green-400' : 'text-d2-border'}`}>
                      {completed ? '\u2713' : '\u25CB'}
                    </span>
                    <span>{info.name}</span>
                  </div>
                )
              })}

              <div
                className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm border ${
                  q.siege_completed
                    ? 'border-green-800/40 bg-green-950/20 text-green-300'
                    : 'border-d2-border bg-d2-bg text-d2-muted'
                }`}
              >
                <span className={`text-xs ${q.siege_completed ? 'text-green-400' : 'text-d2-border'}`}>
                  {q.siege_completed ? '\u2713' : '\u25CB'}
                </span>
                <span>Siege on Harrogath</span>
                {q.siege_completed && (
                  <span
                    className={`ml-auto px-1.5 py-0.5 rounded text-xs font-mono border ${
                      q.socket_quest_available
                        ? 'border-amber-800/40 bg-amber-950/30 text-amber-300'
                        : 'border-d2-border bg-d2-bg text-d2-muted'
                    }`}
                  >
                    {q.socket_quest_available ? 'Socket Available' : 'Socket Used'}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
