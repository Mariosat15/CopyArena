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
  api_key?: string
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
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  logout: () => void
  updateUser: (userData: Partial<User>) => void
  initializeAuth: () => Promise<void>
  checkAuth: () => Promise<boolean>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: async (email: string, password: string) => {
        try {
          console.log('Attempting login with:', email)
          const response = await api.post('/api/auth/login', { 
            email: email.trim(), 
            password 
          })
          console.log('Login response:', response.data)
          
          const { token, user, message } = response.data
          
          // Set authorization header for future requests
          api.defaults.headers.common['Authorization'] = `Bearer ${token}`
          
          set({ 
            user, 
            token, 
            isAuthenticated: true 
          })
          
          console.log('✅ Login successful:', message)
        } catch (error: any) {
          console.error('❌ Login failed:', error.response?.data?.detail || error.message)
          throw new Error(error.response?.data?.detail || 'Login failed')
        }
      },

      register: async (email: string, username: string, password: string) => {
        try {
          console.log('Attempting registration:', { email, username })
          const response = await api.post('/api/auth/register', { 
            email: email.trim(), 
            username: username.trim(), 
            password 
          })
          console.log('Register response:', response.data)
          
          const { token, user, message } = response.data
          
          // Set authorization header for future requests
          api.defaults.headers.common['Authorization'] = `Bearer ${token}`
          
          set({ 
            user, 
            token, 
            isAuthenticated: true 
          })
          
          console.log('✅ Registration successful:', message)
        } catch (error: any) {
          console.error('❌ Registration failed:', error.response?.data?.detail || error.message)
          throw new Error(error.response?.data?.detail || 'Registration failed')
        }
      },

      logout: () => {
        // Call logout endpoint
        api.post('/api/auth/logout').catch(console.error)
        
        // Clear authorization header
        delete api.defaults.headers.common['Authorization']
        
        // Clear all auth data
        set({ 
          user: null, 
          token: null, 
          isAuthenticated: false 
        })
        
        // Clear session data as well
        localStorage.removeItem('copyarena_session_id')
        localStorage.removeItem('copyarena_user_id')
        localStorage.removeItem('copyarena_api_key')
        
        console.log('✅ Logged out successfully')
      },

      updateUser: (userData: Partial<User>) => {
        const currentUser = get().user
        if (currentUser) {
          set({ user: { ...currentUser, ...userData } })
        }
      },

      checkAuth: async (): Promise<boolean> => {
        const { token } = get()
        if (!token) {
          return false
        }

        try {
          // Set the authorization header
          api.defaults.headers.common['Authorization'] = `Bearer ${token}`
          
          // Try to get user profile to verify token
          const response = await api.get('/api/user/profile')
          
          if (response.data.user) {
            set({ 
              user: response.data.user, 
              isAuthenticated: true 
            })
            console.log('✅ Authentication verified for:', response.data.user.username)
            return true
          }
        } catch (error) {
          console.log('❌ Token invalid, clearing auth data')
          get().logout()
        }
        
        return false
      },

      initializeAuth: async () => {
        const { token } = get()
        
        if (token) {
          console.log('🔄 Checking stored authentication...')
          const isValid = await get().checkAuth()
          if (isValid) {
            return
          }
        }
        
        console.log('❌ No valid authentication found')
        set({ 
          user: null, 
          token: null, 
          isAuthenticated: false 
        })
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        token: state.token,
        user: state.user 
      })
    }
  )
) 