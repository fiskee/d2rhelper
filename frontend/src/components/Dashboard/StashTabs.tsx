import { useState } from 'react'
import type { SharedStashTab } from '../../types'
import { ItemTable } from './ItemTable'

export function StashTabs({ tabs }: { tabs: SharedStashTab[] }) {
  const [activeTab, setActiveTab] = useState(0)

  if (tabs.length === 0) {
    return (
      <div className="bg-d2-surface border border-d2-border rounded-lg p-4 text-d2-muted text-sm font-body">
        No shared stash loaded
      </div>
    )
  }

  const tab = tabs[activeTab]

  return (
    <div>
      <div className="flex gap-1 mb-2 overflow-x-auto">
        {tabs.map((t, i) => (
          <button
            key={i}
            onClick={() => setActiveTab(i)}
            className={`px-3 py-1.5 text-xs rounded-t font-body transition-colors cursor-pointer whitespace-nowrap
              ${i === activeTab
                ? 'bg-d2-surface text-d2-accent border-t border-x border-d2-border'
                : 'bg-d2-bg text-d2-muted hover:text-d2-ink'
              }`}
          >
            Tab {t.index + 1}
            {t.gold > 0 && ` (${t.gold.toLocaleString()}g)`}
          </button>
        ))}
      </div>
      {tab && (
        <ItemTable items={tab.items} title={`Shared Stash Tab ${tab.index + 1} — ${tab.gold.toLocaleString()} gold · ${tab.items.length}/${tab.item_count} items`} />
      )}
    </div>
  )
}
