import type { Skill } from '../../types'

export function SkillsPanel({
  skills,
  skillPointsLeft,
}: {
  skills: Skill[]
  skillPointsLeft: number
}) {
  return (
    <div className="bg-d2-surface border border-d2-border rounded-lg">
      <div className="px-4 pt-4 flex items-center justify-between">
        <h2 className="text-lg font-d2 text-d2-accent">Skills</h2>
        {skillPointsLeft > 0 && (
          <span className="text-xs font-mono text-d2-accent bg-d2-bg px-2 py-0.5 rounded border border-d2-border">
            {skillPointsLeft} unspent
          </span>
        )}
      </div>
      <div className="p-4">
        {skills.length === 0 ? (
          <p className="text-sm text-d2-muted">No skills allocated</p>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
            {skills.map((s) => (
              <div
                key={s.name}
                className="flex items-center justify-between px-3 py-1.5 rounded text-sm border border-d2-border bg-d2-bg"
              >
                <span className="text-d2-ink truncate mr-2">{s.name}</span>
                <span className="font-mono text-d2-accent shrink-0">{s.level}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
