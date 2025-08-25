import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface ChatMessage {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
  agentId?: string
  metadata?: {
    type?: 'query' | 'pl-statement' | 'analysis'
    loading?: boolean
    error?: string
  }
}

export interface ChatSession {
  id: string
  title: string
  messages: ChatMessage[]
  createdAt: Date
  updatedAt: Date
  agentId: string
}

interface ChatStore {
  // Current session
  currentSession: ChatSession | null
  sessions: ChatSession[]
  isLoading: boolean
  
  // Actions
  createSession: (agentId: string) => void
  setCurrentSession: (sessionId: string) => void
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void
  updateMessage: (messageId: string, updates: Partial<ChatMessage>) => void
  clearSessions: () => void
  deleteSession: (sessionId: string) => void
  setLoading: (loading: boolean) => void
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      currentSession: null,
      sessions: [],
      isLoading: false,

      createSession: (agentId: string) => {
        const newSession: ChatSession = {
          id: `session_${Date.now()}`,
          title: `New Chat - ${new Date().toLocaleDateString()}`,
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date(),
          agentId,
        }

        set(state => ({
          currentSession: newSession,
          sessions: [newSession, ...state.sessions]
        }))
      },

      setCurrentSession: (sessionId: string) => {
        const session = get().sessions.find(s => s.id === sessionId)
        if (session) {
          set({ currentSession: session })
        }
      },

      addMessage: (messageData) => {
        const { currentSession } = get()
        if (!currentSession) return

        const newMessage: ChatMessage = {
          ...messageData,
          id: `msg_${Date.now()}`,
          timestamp: new Date(),
        }

        const updatedSession = {
          ...currentSession,
          messages: [...currentSession.messages, newMessage],
          updatedAt: new Date(),
        }

        set(state => ({
          currentSession: updatedSession,
          sessions: state.sessions.map(s => 
            s.id === currentSession.id ? updatedSession : s
          )
        }))
      },

      updateMessage: (messageId: string, updates: Partial<ChatMessage>) => {
        const { currentSession } = get()
        if (!currentSession) return

        const updatedSession = {
          ...currentSession,
          messages: currentSession.messages.map(msg =>
            msg.id === messageId ? { ...msg, ...updates } : msg
          ),
          updatedAt: new Date(),
        }

        set(state => ({
          currentSession: updatedSession,
          sessions: state.sessions.map(s =>
            s.id === currentSession.id ? updatedSession : s
          )
        }))
      },

      clearSessions: () => {
        set({ currentSession: null, sessions: [] })
      },

      deleteSession: (sessionId: string) => {
        set(state => ({
          sessions: state.sessions.filter(s => s.id !== sessionId),
          currentSession: state.currentSession?.id === sessionId ? null : state.currentSession
        }))
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading })
      },
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({
        sessions: state.sessions,
        currentSession: state.currentSession,
      }),
    }
  )
)
