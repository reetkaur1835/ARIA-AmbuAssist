import axios from 'axios'

const api = axios.create({ baseURL: '' })

export const login = (username, pin) =>
  api.post('/auth/login', { username, pin })

export const logout = (session_id) =>
  api.post('/auth/logout', { session_id })

export const chatStream = (message, session_id) =>
  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id }),
  })

export const getStatus = (session_id) =>
  api.post('/api/paramedic/status', { session_id })

export const getShifts = (session_id) =>
  api.post('/api/shifts/upcoming', { session_id })

export const resetConversation = (session_id) =>
  api.post('/api/reset', { session_id })
