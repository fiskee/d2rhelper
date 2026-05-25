import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import type { ChatMessage } from '../../types'

function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      components={{
        h1: ({ children }) => <h1 className="text-lg font-d2 text-d2-accent mt-3 mb-1">{children}</h1>,
        h2: ({ children }) => <h2 className="text-base font-d2 text-d2-accent mt-3 mb-1">{children}</h2>,
        h3: ({ children }) => <h3 className="text-sm font-d2 font-semibold text-d2-ink mt-2 mb-1">{children}</h3>,
        p: ({ children }) => <p className="my-1 leading-relaxed">{children}</p>,
        ul: ({ children }) => <ul className="list-disc list-inside my-1 space-y-0.5">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal list-inside my-1 space-y-0.5">{children}</ol>,
        li: ({ children }) => <li className="text-sm">{children}</li>,
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
            <code className="block bg-d2-bg rounded p-3 text-xs font-mono text-d2-ink overflow-x-auto my-2" {...props}>
              {children}
            </code>
          )
        },
        pre: ({ children }) => <>{children}</>,
        table: ({ children }) => (
          <div className="overflow-x-auto my-2">
            <table className="w-full border-collapse text-xs">{children}</table>
          </div>
        ),
        thead: ({ children }) => <thead className="bg-d2-bg">{children}</thead>,
        th: ({ children }) => (
          <th className="border border-d2-border px-2 py-1 text-left font-semibold text-d2-accent">{children}</th>
        ),
        td: ({ children }) => <td className="border border-d2-border px-2 py-1">{children}</td>,
        blockquote: ({ children }) => (
          <blockquote className="border-l-3 border-d2-accent/40 pl-3 my-2 italic text-d2-muted">{children}</blockquote>
        ),
        hr: () => <hr className="border-d2-border my-3" />,
        a: ({ href, children }) => (
          <a href={href} className="text-d2-accent underline hover:text-d2-accent-hover" target="_blank" rel="noopener noreferrer">
            {children}
          </a>
        ),
      }}
    >
      {content}
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
    <div className="flex-1 overflow-y-auto p-4 scrollbar-thin space-y-3">
      {messages.map((msg, i) => (
        <div
          key={i}
          className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[80%] rounded-lg px-4 py-2 text-sm ${
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
