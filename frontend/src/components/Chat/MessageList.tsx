import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import type { ChatMessage } from '../../types'
import { useAppStore } from '../../store/appStore'
import { lookupItem } from '../../api/client'
import type { DBAttrs } from '../../api/client'
import { ItemLink, AreaLink } from './ItemTooltip'

function ItemLinkResolver({ name, itemType }: { name: string; itemType: string }) {
  const itemIndex = useAppStore((s) => s.itemIndex)
  const [dbItem, setDbItem] = useState<DBAttrs | null | undefined>(undefined)
  const matches = itemType === '' ? (itemIndex[name.toLowerCase()] ?? []) : []

  useEffect(() => {
    if (itemType !== '') {
      let cancelled = false
      lookupItem(name, itemType).then((data) => {
        if (!cancelled) setDbItem(data)
      })
      return () => { cancelled = true }
    }
    if (itemType === '' && matches.length === 0) {
      let cancelled = false
      lookupItem(name).then((data) => {
        if (!cancelled) setDbItem(data)
      })
      return () => { cancelled = true }
    }
  }, [name, itemType, matches.length])

  // Type specified — API only
  if (itemType !== '') {
    if (dbItem === undefined) return <span>{name}</span>
    if (dbItem) return <ItemLink name={name} dbItem={dbItem} />
    return <span>{name}</span>
  }

  // Auto — check player items first
  if (matches.length === 1) {
    return <ItemLink name={name} playerItem={matches[0]} />
  }

  if (matches.length > 1) return <span>{name}</span>

  if (dbItem === undefined) return <span>{name}</span>
  if (dbItem) return <ItemLink name={name} dbItem={dbItem} />
  return <span>{name}</span>
}

function PlayerItemLink({ name, itemId }: { name: string; itemId: string }) {
  const idIndex = useAppStore((s) => s.idIndex)
  const item = idIndex[itemId]
  if (!item) return <span>{name}</span>
  return <ItemLink name={name} playerItem={item} />
}

function MarkdownContent({ content }: { content: string }) {
  const processed = content
    .replace(/\]\(item:/g, '](#item:')
    .replace(/\]\(area: "([^"]*)"\)/g, '](#area "$1")')
  return (
    <ReactMarkdown
      components={{
        h1: ({ children }) => <h1 className="text-lg font-d2 text-d2-accent" style={{ marginTop: 16, marginBottom: 10 }}>{children}</h1>,
        h2: ({ children }) => <h2 className="text-base font-d2 text-d2-accent" style={{ marginTop: 16, marginBottom: 10 }}>{children}</h2>,
        h3: ({ children }) => <h3 className="text-sm font-d2 font-semibold text-d2-ink" style={{ marginTop: 14, marginBottom: 8 }}>{children}</h3>,
        p: ({ children }) => <p style={{ marginTop: 10, marginBottom: 10, lineHeight: 1.7 }}>{children}</p>,
        ul: ({ children }) => <ul className="list-disc list-inside" style={{ marginTop: 10, marginBottom: 10 }}>{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal list-inside" style={{ marginTop: 10, marginBottom: 10 }}>{children}</ol>,
        li: ({ children }) => <li className="text-sm" style={{ marginBottom: 4 }}>{children}</li>,
        strong: ({ children }) => <strong className="font-semibold text-d2-ink">{children}</strong>,
        em: ({ children }) => <em className="italic text-d2-ink/80">{children}</em>,
        code: ({ className, children, ...props }) => {
          const isInline = !className
          if (isInline) {
            return (
              <code className="bg-d2-bg px-1.5 py-0.5 rounded text-xs font-mono text-d2-accent" {...props}>
                {children}
              </code>
            )
          }
          return (
            <code className="block bg-d2-bg rounded p-3 text-xs font-mono text-d2-ink overflow-x-auto" style={{ marginTop: 10, marginBottom: 10 }} {...props}>
              {children}
            </code>
          )
        },
        pre: ({ children }) => <>{children}</>,
        table: ({ children }) => (
          <div className="overflow-x-auto" style={{ marginTop: 10, marginBottom: 10 }}>
            <table className="w-full border-collapse text-xs">{children}</table>
          </div>
        ),
        thead: ({ children }) => <thead className="bg-d2-bg">{children}</thead>,
        th: ({ children }) => (
          <th className="border border-d2-border px-2 py-1 text-left font-semibold text-d2-accent">{children}</th>
        ),
        td: ({ children }) => <td className="border border-d2-border px-2 py-1">{children}</td>,
        blockquote: ({ children }) => (
          <blockquote className="border-l-3 border-d2-accent/40 pl-3 italic text-d2-muted" style={{ marginTop: 10, marginBottom: 10 }}>{children}</blockquote>
        ),
        hr: () => <hr className="border-d2-border" style={{ marginTop: 12, marginBottom: 12 }} />,
        a: ({ href, title, children }) => {
          if (href && href.startsWith('#item:p:')) {
            const itemId = href.slice('#item:p:'.length)
            const name = String(children ?? '')
            if (!name) return null
            return <PlayerItemLink name={name} itemId={itemId} />
          }
          if (href && href.startsWith('#item:')) {
            const itemType = href.slice('#item:'.length)
            const name = String(children ?? '')
            if (!name) return null
            return <ItemLinkResolver name={name} itemType={itemType} />
          }
          if (href === '#area' && title) {
            const name = String(children ?? '')
            if (!name) return null
            const info = title.replace(/&amp;/g, '&')
            return <AreaLink name={name} info={info} />
          }
          return (
            <a href={href} className="text-d2-accent underline hover:text-d2-accent-hover" target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          )
        },
      }}
    >
      {processed}
    </ReactMarkdown>
  )
}

export function MessageList({ messages }: { messages: ChatMessage[] }) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-d2-muted font-body">
        <div className="text-center">
          <div className="text-3xl mb-3">&#9876;</div>
          <p className="text-sm">Ask about your character, items, builds, or farming strategies</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 scrollbar-thin space-y-4">
      {messages.map((msg, i) => (
        <div
          key={i}
          className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
              className={`max-w-[80%] rounded-lg px-4 py-3 text-sm ${
              msg.role === 'user'
                ? 'bg-d2-accent text-d2-bg font-body'
                : 'bg-d2-surface border border-d2-border text-d2-ink font-body'
            }`}
          >
            {msg.role === 'user' ? (
              <div className="whitespace-pre-wrap break-words">{msg.content}</div>
            ) : (
              <MarkdownContent content={msg.content || '...'} />
            )}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
