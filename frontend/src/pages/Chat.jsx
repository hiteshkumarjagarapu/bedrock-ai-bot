import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../api/api.js'
import Sidebar from '../components/Sidebar.jsx'
import ChatWindow from '../components/ChatWindow.jsx'
import useStreamChat from '../hooks/useStreamChat.js'

export default function Chat() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const { send, stop, streaming } = useStreamChat()
  const [messages, setMessages] = useState([])
  const [refreshKey, setRefreshKey] = useState(0)
  const activeSession = useRef(sessionId || null)

  useEffect(() => {
    activeSession.current = sessionId || null
    if (streaming) return // don't clobber messages while a response streams in
    if (!sessionId) {
      setMessages([])
      return
    }
    api.get(`/chat/history/${sessionId}`).then((r) => setMessages(r.data.messages))
  }, [sessionId]) // eslint-disable-line react-hooks/exhaustive-deps

  const patchLast = (fn) =>
    setMessages((prev) => prev.map((m, i) => (i === prev.length - 1 ? fn(m) : m)))

  const onSend = (query) => {
    setMessages((prev) => [...prev, { role: 'user', content: query }, { role: 'assistant', content: '' }])
    send(query, {
      sessionId: activeSession.current,
      onSession: (id) => {
        if (!activeSession.current) {
          activeSession.current = id
          navigate(`/chat/${id}`, { replace: true })
          setRefreshKey((k) => k + 1)
        }
      },
      onSources: (sources) => patchLast((m) => ({ ...m, sources })),
      onToken: (t) => patchLast((m) => ({ ...m, content: m.content + t })),
      onError: (msg) => patchLast((m) => ({ ...m, content: msg, error: true })),
    })
  }

  return (
    <div className="flex">
      <Sidebar activeId={sessionId} refreshKey={refreshKey} />
      <ChatWindow messages={messages} streaming={streaming} onSend={onSend} onStop={stop} />
    </div>
  )
}
