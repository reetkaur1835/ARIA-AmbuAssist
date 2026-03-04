import { create } from 'zustand'

const useStore = create((set, get) => ({
  // ── Auth ──────────────────────────────────────
  sessionId: localStorage.getItem('aria_session') || null,
  paramedic: JSON.parse(localStorage.getItem('aria_paramedic') || 'null'),

  login: (sessionId, paramedic) => {
    localStorage.setItem('aria_session', sessionId)
    localStorage.setItem('aria_paramedic', JSON.stringify(paramedic))
    set({ sessionId, paramedic })
  },
  logout: () => {
    localStorage.removeItem('aria_session')
    localStorage.removeItem('aria_paramedic')
    set({ sessionId: null, paramedic: null, messages: [], activeForm: null, formData: {} })
  },

  // ── Chat ──────────────────────────────────────
  messages: [],        // { role: 'user'|'assistant', content: string, timestamp: Date }
  isLoading: false,
  isSpeaking: false,

  addMessage: (role, content) =>
    set(s => ({ messages: [...s.messages, { role, content, timestamp: new Date() }] })),

  setLoading: (v) => set({ isLoading: v }),
  setSpeaking: (v) => set({ isSpeaking: v }),

  // ── Form state (driven by backend responses) ──
  activeForm: null,
  formData: {},
  confirmationPending: false,
  submitted: false,

  setFormState: ({ activeForm, formData, confirmationPending, submitted }) =>
    set({ activeForm, formData, confirmationPending, submitted }),

  // ── Side panel data ───────────────────────────
  statusItems: [],
  shifts: [],

  setStatusItems: (items) => set({ statusItems: items }),
  setShifts: (shifts) => set({ shifts }),
}))

export default useStore
