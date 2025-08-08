import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '../lib/api'

export interface User {
  id: number
  email: string
  username: string
  subscription_plan: string
  credits: number
  xp_points: number
  level: number
  avatar_url?: string
  is_online?: boolean
  stats?: {
    total_trades: number
    win_rate: number
    total_profit: number
    followers_count: number
  }
  badges?: Array<{
    name: string
    icon: string
    earned_at: string
  }>
}

interface AuthState {
  user: User | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  logout: () => void
  updateUser: (userData: Partial<User>) => void
  initializeAuth: () => void
}

// Auth token interceptor is handled in api.ts

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,

      login: async (email: string, password: string) => {
        try {
          const response = await api.post('/api/auth/login', { email, password })
          const { token, user } = response.data
          
          set({ user, token })
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Login failed')
        }
      },

      register: async (email: string, username: string, password: string) => {
        try {
          const response = await api.post('/api/auth/register', { 
            email, 
            username, 
            password 
          })
          const { token, user } = response.data
          
          set({ user, token })
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Registration failed')
        }
      },

      logout: () => {
        set({ user: null, token: null })
      },

      updateUser: (userData: Partial<User>) => {
        const currentUser = get().user
        if (currentUser) {
          set({ user: { ...currentUser, ...userData } })
        }
      },

      initializeAuth: () => {
        // This will automatically load from localStorage due to persist middleware
        const { token } = get()
        if (token) {
          // Fetch fresh user data
          api.get('/api/user/profile')
            .then(response => {
              set({ user: response.data })
            })
            .catch(() => {
              // Token is invalid, logout
              get().logout()
            })
        }
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ token: state.token })
    }
  )
) 