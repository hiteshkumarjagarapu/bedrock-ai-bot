import { useCallback, useRef, useState } from 'react'
import { API_URL } from '../api/api.js'

/** POSTs to /chat and parses the SSE stream (fetch, since EventSource can't POST). */
export default function useStreamChat() {
  const [streaming, setStreaming] = useState(false)
  const abortRef = useRef(null)

  const send = useCallback(async (query, { sessionId, docIds, onToken, onSources, onSession, onError } = {}) => {
    setStreaming(true)
    abortRef.current = new AbortController()
    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ query, session_id: sessionId || null, doc_ids: docIds?.length ? docIds : null }),
        signal: abortRef.current.signal,
      })
      if (res.status === 401) {
        localStorage.removeItem('token')
        window.location.href = '/login'
        return
      }
      if (!res.ok) throw new Error(`Request failed (${res.status})`)

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const events = buffer.split('\n\n')
        buffer = events.pop()
        for (const evt of events) {
          const line = evt.trim()
          if (!line.startsWith('data:')) continue
          const data = line.slice(5).trim()
          if (data === '[DONE]') return
          const msg = JSON.parse(data)
          if (msg.type === 'token') onToken?.(msg.content)
          else if (msg.type === 'sources') onSources?.(msg.sources)
          else if (msg.type === 'session') onSession?.(msg.session_id)
          else if (msg.type === 'error') onError?.(msg.message)
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') onError?.(e.message)
    } finally {
      setStreaming(false)
    }
  }, [])

  const stop = useCallback(() => abortRef.current?.abort(), [])
  return { send, stop, streaming }
}
