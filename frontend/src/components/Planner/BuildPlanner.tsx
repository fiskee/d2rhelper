import { useEffect, useMemo, useState } from 'react'
import { calculateSkillDamage, listClassSkills, lookupSkill } from '../../api/client'
import type { ClassSkillsResult, SkillDamageResult, SkillLookupResult } from '../../types'
import { useAppStore } from '../../store/appStore'

function parseSynergyNames(expr: string): string[] {
  const re = /skill\('([^']+)'\.blvl\)/g
  const out: string[] = []
  let match: RegExpExecArray | null = re.exec(expr)
  while (match) {
    if (!out.includes(match[1])) out.push(match[1])
    match = re.exec(expr)
  }
  return out
}

export function BuildPlanner() {
  const character = useAppStore((s) => s.character)
  const [skillsData, setSkillsData] = useState<ClassSkillsResult | null>(null)
  const [selectedSkill, setSelectedSkill] = useState('')
  const [skillLevel, setSkillLevel] = useState(20)
  const [plusSkills, setPlusSkills] = useState(0)
  const [enemyResist, setEnemyResist] = useState(0)
  const [sunder, setSunder] = useState(false)
  const [skillLookup, setSkillLookup] = useState<SkillLookupResult | null>(null)
  const [damage, setDamage] = useState<SkillDamageResult | null>(null)
  const [loading, setLoading] = useState(false)

  const className = character?.character_type ?? ''

  useEffect(() => {
    if (!className) return
    listClassSkills(className).then((data) => {
      setSkillsData(data)
      if (data && data.skills.length > 0 && !selectedSkill) {
        setSelectedSkill(data.skills[0].name)
      }
    })
  }, [className, selectedSkill])

  useEffect(() => {
    if (!className || !selectedSkill) return
    lookupSkill(selectedSkill, className).then(setSkillLookup)
  }, [className, selectedSkill])

  const synergyNames = useMemo(() => {
    if (!skillLookup) return []
    return parseSynergyNames(skillLookup.damage_formula.edmgsympercalc)
  }, [skillLookup])

  const defaultSynergyLevels = useMemo(() => {
    const map: Record<string, number> = {}
    const known = new Map((character?.skills ?? []).map((s) => [s.name, s.level]))
    for (const name of synergyNames) {
      map[name] = known.get(name) ?? 0
    }
    return map
  }, [character?.skills, synergyNames])

  const [synergyLevels, setSynergyLevels] = useState<Record<string, number>>({})

  useEffect(() => {
    setSynergyLevels(defaultSynergyLevels)
  }, [defaultSynergyLevels])

  async function runEstimate() {
    if (!className || !selectedSkill) return
    setLoading(true)
    const result = await calculateSkillDamage({
      class_name: className,
      skill_name: selectedSkill,
      skill_level: skillLevel,
      plus_skills: plusSkills,
      synergy_levels: synergyLevels,
      enemy_resist: enemyResist,
      sunder,
    })
    setDamage(result)
    setLoading(false)
  }

  return (
    <div className="space-y-4">
      <div className="bg-d2-surface border border-d2-border rounded-lg p-4">
        <h2 className="text-lg font-d2 text-d2-accent mb-3">Build Planner</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <label className="text-sm text-d2-muted font-body">
            Skill
            <select
              className="mt-1 w-full bg-d2-bg border border-d2-border rounded px-2 py-1 text-d2-ink"
              value={selectedSkill}
              onChange={(e) => setSelectedSkill(e.target.value)}
            >
              {(skillsData?.skills ?? []).map((s) => (
                <option key={s.name} value={s.name}>{s.name}</option>
              ))}
            </select>
          </label>
          <label className="text-sm text-d2-muted font-body">
            Hard Skill Level
            <input className="mt-1 w-full bg-d2-bg border border-d2-border rounded px-2 py-1 text-d2-ink" type="number" min={1} max={60} value={skillLevel} onChange={(e) => setSkillLevel(Number(e.target.value || 1))} />
          </label>
          <label className="text-sm text-d2-muted font-body">
            +Skills
            <input className="mt-1 w-full bg-d2-bg border border-d2-border rounded px-2 py-1 text-d2-ink" type="number" min={0} max={30} value={plusSkills} onChange={(e) => setPlusSkills(Number(e.target.value || 0))} />
          </label>
          <label className="text-sm text-d2-muted font-body">
            Enemy Resist %
            <input className="mt-1 w-full bg-d2-bg border border-d2-border rounded px-2 py-1 text-d2-ink" type="number" min={-100} max={200} value={enemyResist} onChange={(e) => setEnemyResist(Number(e.target.value || 0))} />
          </label>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <input id="sunder" type="checkbox" checked={sunder} onChange={(e) => setSunder(e.target.checked)} />
          <label htmlFor="sunder" className="text-sm text-d2-muted font-body">Apply sunder clamp</label>
        </div>

        {synergyNames.length > 0 && (
          <div className="mt-4">
            <h3 className="text-sm font-d2 text-d2-accent mb-2">Synergy Levels</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {synergyNames.map((name) => (
                <label key={name} className="text-xs text-d2-muted font-body">
                  {name}
                  <input
                    className="mt-1 w-full bg-d2-bg border border-d2-border rounded px-2 py-1 text-d2-ink"
                    type="number"
                    min={0}
                    max={60}
                    value={synergyLevels[name] ?? 0}
                    onChange={(e) => setSynergyLevels((s) => ({ ...s, [name]: Number(e.target.value || 0) }))}
                  />
                </label>
              ))}
            </div>
          </div>
        )}

        <button
          onClick={runEstimate}
          disabled={loading || !selectedSkill}
          className="mt-4 px-3 py-2 bg-d2-accent text-d2-bg rounded font-body text-sm hover:bg-d2-accent-hover disabled:opacity-40"
        >
          {loading ? 'Calculating...' : 'Calculate Damage'}
        </button>
      </div>

      {damage && (
        <div className="bg-d2-surface border border-d2-border rounded-lg p-4">
          <h3 className="text-base font-d2 text-d2-accent mb-2">Estimate</h3>
          <p className="text-sm text-d2-ink font-body">
            {damage.skill_name} ({damage.effective_skill_level}) {'->'} {Math.floor(damage.final_damage_min)} - {Math.floor(damage.final_damage_max)}
          </p>
          <p className="text-xs text-d2-muted font-mono mt-1">
            Base {damage.base_damage_min}-{damage.base_damage_max} | Synergy +{damage.synergy_bonus_pct}% | Resist {damage.enemy_resist_after_mods}%
          </p>
          {damage.assumptions.length > 0 && (
            <ul className="mt-2 text-xs text-d2-muted list-disc list-inside">
              {damage.assumptions.map((a, i) => <li key={i}>{a}</li>)}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
