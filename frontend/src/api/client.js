import axios from 'axios'

const api = axios.create({ baseURL: '' })

export const login = (username, pin) =>
  api.post('/auth/login', { username, pin })

export const logout = (session_id) =>
  api.post('/auth/logout', { session_id })

export const sendMessage = (message, session_id) =>
  api.post('/api/chat', { message, session_id })

export const getStatus = (session_id) =>
  api.post('/api/paramedic/status', { session_id })

export const getShifts = (session_id) =>
  api.post('/api/shifts/upcoming', { session_id })

export const resetConversation = (session_id) =>
  api.post('/api/reset', { session_id })
