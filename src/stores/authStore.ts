import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import axios from 'axios'

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

// Setup axios interceptor for auth token
axios.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
    }
    return Promise.reject(error)
  }
)

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,

      login: async (email: string, password: string) => {
        try {
          const response = await axios.post('/api/auth/login', { email, password })
          const { token, user } = response.data
          
          set({ user, token })
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Login failed')
        }
      },

      register: async (email: string, username: string, password: string) => {
        try {
          const response = await axios.post('/api/auth/register', { 
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
          axios.get('/api/user/profile')
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