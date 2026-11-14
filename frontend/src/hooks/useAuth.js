import { useCallback, useState } from 'react'
import api from '../api/api.js'

export default function useAuth() {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem('user') || 'null'))

  const authenticate = useCallback(async (mode, payload) => {
    const { data } = await api.post(`/auth/${mode}`, payload)
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.user))
    setUser(data.user)
  }, [])

  const login = (email, password) => authenticate('login', { email, password })
  const register = (name, email, password) => authenticate('register', { name, email, password })

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
  }, [])

  return { user, isAuthenticated: !!localStorage.getItem('token'), login, register, logout }
}
