import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api/api.js'

export default function Sidebar({ activeId, refreshKey }) {
  const [sessions, setSessions] = useState([])
  const [dark, setDark] = useState(document.documentElement.classList.contains('dark'))
  const navigate = useNavigate()
  const user = JSON.parse(localStorage.getItem('user') || '{}')

  useEffect(() => {
    api.get('/chat/sessions').then((r) => setSessions(r.data)).catch(() => {})
  }, [refreshKey])

  const toggleTheme = () => {
    const next = !dark
    document.documentElement.classList.toggle('dark', next)
    localStorage.setItem('theme', next ? 'dark' : 'light')
    setDark(next)
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    navigate('/login')
  }

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
      <Link to="/" className="mb-3 rounded px-2 py-2 font-semibold hover:bg-gray-100 dark:hover:bg-gray-700">
        📄 Documents
      </Link>
      <Link to="/chat" className="mb-3 rounded bg-indigo-600 px-3 py-2 text-center text-white hover:bg-indigo-700">
        + New chat
      </Link>
      <div className="flex-1 space-y-1 overflow-y-auto">
        {sessions.map((s) => (
          <Link
            key={s.id}
            to={`/chat/${s.id}`}
            className={`block truncate rounded px-2 py-1.5 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 ${
              s.id === activeId ? 'bg-gray-100 dark:bg-gray-700' : ''
            }`}
          >
            {s.title}
          </Link>
        ))}
      </div>
      <div className="mt-2 flex items-center justify-between border-t border-gray-200 pt-2 text-sm dark:border-gray-700">
        <span className="truncate">{user.name}</span>
        <div className="flex gap-2">
          <button onClick={toggleTheme} title="Toggle dark mode">{dark ? '☀️' : '🌙'}</button>
          <button onClick={logout} className="text-red-500">Logout</button>
        </div>
      </div>
    </aside>
  )
}
