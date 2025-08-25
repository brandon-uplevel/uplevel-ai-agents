import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface UserSettings {
  theme: 'light' | 'dark' | 'system'
  language: string
  notifications: {
    enabled: boolean
    email: boolean
    push: boolean
  }
  chat: {
    autoSave: boolean
    maxSessions: number
    showTimestamps: boolean
  }
  api: {
    timeout: number
    retryAttempts: number
  }
}

interface SettingsStore {
  settings: UserSettings
  updateSettings: (updates: Partial<UserSettings>) => void
  resetSettings: () => void
}

const defaultSettings: UserSettings = {
  theme: 'system',
  language: 'en',
  notifications: {
    enabled: true,
    email: false,
    push: true,
  },
  chat: {
    autoSave: true,
    maxSessions: 50,
    showTimestamps: true,
  },
  api: {
    timeout: 30000, // 30 seconds
    retryAttempts: 3,
  },
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      settings: defaultSettings,

      updateSettings: (updates: Partial<UserSettings>) => {
        set(state => ({
          settings: { ...state.settings, ...updates }
        }))
      },

      resetSettings: () => {
        set({ settings: defaultSettings })
      },
    }),
    {
      name: 'user-settings',
    }
  )
)
