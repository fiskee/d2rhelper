import type { D2Character } from '../../types'

export function CharacterInfo({ character }: { character: D2Character }) {
  return (
    <div className="bg-d2-surface border border-d2-border rounded-lg p-4">
      <div className="mb-4">
        <h1 className="text-2xl font-d2 text-d2-accent">
          {character.status.hardcore && (
            <span className="text-d2-hardcore" title="Hardcore">HC </span>
          )}
          {character.name}
        </h1>
        <p className="text-d2-muted text-sm font-body">
          Level {character.level} {character.character_type} &middot;
          Act {character.act_progression} &middot;
          {character.status.lord_of_destruction ? 'LoD' : 'Classic'}
          {character.status.reign_of_the_warlock && ' · RotW'}
        </p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <div>
          <span className="text-d2-muted text-xs">Strength</span>
          <div className="font-mono text-d2-ink">{character.attributes.strength}</div>
        </div>
        <div>
          <span className="text-d2-muted text-xs">Dexterity</span>
          <div className="font-mono text-d2-ink">{character.attributes.dexterity}</div>
        </div>
        <div>
          <span className="text-d2-muted text-xs">Vitality</span>
          <div className="font-mono text-d2-ink">{character.attributes.vitality}</div>
        </div>
        <div>
          <span className="text-d2-muted text-xs">Energy</span>
          <div className="font-mono text-d2-ink">{character.attributes.energy}</div>
        </div>
        <div>
          <span className="text-d2-muted text-xs">Life</span>
          <div className="font-mono text-d2-ink">{character.attributes.hp}/{character.attributes.max_hp}</div>
        </div>
        <div>
          <span className="text-d2-muted text-xs">Mana</span>
          <div className="font-mono text-d2-ink">{character.attributes.mana}/{character.attributes.max_mana}</div>
        </div>
        <div>
          <span className="text-d2-muted text-xs">Gold</span>
          <div className="font-mono text-d2-accent">{character.attributes.gold.toLocaleString()}</div>
        </div>
        <div>
          <span className="text-d2-muted text-xs">Stash Gold</span>
          <div className="font-mono text-d2-accent">{character.attributes.gold_in_stash.toLocaleString()}</div>
        </div>
      </div>

      {character.parse_warnings.length > 0 && (
        <div className="mt-4 p-3 bg-d2-bg border border-amber-800/40 rounded">
          <span className="text-xs text-amber-500 font-d2">Warnings</span>
          <ul className="text-xs text-d2-muted mt-1 list-disc list-inside">
            {character.parse_warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
