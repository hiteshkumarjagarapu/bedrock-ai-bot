import { useEffect, useRef, useState } from 'react'
import MessageBubble from './MessageBubble.jsx'

export default function ChatWindow({ messages, streaming, onSend, onStop }) {
  const [input, setInput] = useState('')
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const submit = (e) => {
    e.preventDefault()
    const q = input.trim()
    if (!q || streaming) return
    setInput('')
    onSend(q)
  }

  return (
    <div className="flex h-screen flex-1 flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto p-6">
        {messages.length === 0 && (
          <p className="mt-20 text-center text-gray-500">Ask a question about your documents.</p>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} streaming={streaming && i === messages.length - 1 && m.role === 'assistant'} />
        ))}
        <div ref={endRef} />
      </div>
      <form onSubmit={submit} className="flex gap-2 border-t border-gray-200 p-4 dark:border-gray-700">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask something…"
          className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-600 dark:bg-gray-800"
        />
        {streaming ? (
          <button type="button" onClick={onStop} className="rounded-lg bg-red-500 px-4 py-2 text-white">Stop</button>
        ) : (
          <button className="rounded-lg bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700">Send</button>
        )}
      </form>
    </div>
  )
}
