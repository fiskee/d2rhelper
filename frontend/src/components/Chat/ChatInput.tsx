import { useState } from 'react'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState('')

  const handleSend = () => {
    const msg = input.trim()
    if (!msg || disabled) return
    onSend(msg)
    setInput('')
  }

  return (
    <div className="border-t border-d2-border p-3 flex gap-2">
      <input
        type="text"
        placeholder="Ask about your character..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
          }
        }}
        disabled={disabled}
        className="flex-1 bg-d2-bg border border-d2-border rounded-lg px-3 py-2 text-sm text-d2-ink
                   placeholder:text-d2-muted focus:outline-none focus:border-d2-accent font-body
                   disabled:opacity-50"
      />
      <button
        onClick={handleSend}
        disabled={disabled || !input.trim()}
        className="bg-d2-accent hover:bg-d2-accent-hover disabled:opacity-40 text-d2-bg font-semibold
                   px-4 py-2 rounded-lg text-sm transition-colors cursor-pointer disabled:cursor-not-allowed font-body"
      >
        Send
      </button>
    </div>
  )
}
