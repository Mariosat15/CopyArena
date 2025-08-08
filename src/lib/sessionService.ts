// @ts-ignore
import React from 'react'
import { api } from './api'

interface SessionResponse {
  session_id: string
  user_id: number
  username: string
  api_key: string
  message: string
}

class SessionService {
  private static instance: SessionService
  private sessionId: string | null = null
  private userId: number | null = null
  private apiKey: string | null = null

  static getInstance(): SessionService {
    if (!SessionService.instance) {
      SessionService.instance = new SessionService()
    }
    return SessionService.instance
  }

  async initializeSession(): Promise<SessionResponse> {
    try {
      // Check if we already have a stored session
      const storedSessionId = localStorage.getItem('copyarena_session_id')
      const storedUserId = localStorage.getItem('copyarena_user_id')
      const storedApiKey = localStorage.getItem('copyarena_api_key')

      if (storedSessionId && storedUserId && storedApiKey) {
        // Try to validate existing session
        try {
          const validateResponse = await api.get('/api/auth/session')
          if (validateResponse.data.session_id === storedSessionId) {
            this.sessionId = storedSessionId
            this.userId = parseInt(storedUserId)
            this.apiKey = storedApiKey
            console.log(`✅ Session restored: ${validateResponse.data.username} (ID: ${storedSessionId})`)
            return validateResponse.data
          }
        } catch (error) {
          // Session invalid, clear storage and create new
          this.clearStoredSession()
        }
      }

      // Create new session
      const response = await api.post('/api/auth/session')
      const sessionData: SessionResponse = response.data

      this.sessionId = sessionData.session_id
      this.userId = sessionData.user_id
      this.apiKey = sessionData.api_key

      // Store session data
      localStorage.setItem('copyarena_session_id', sessionData.session_id)
      localStorage.setItem('copyarena_user_id', sessionData.user_id.toString())
      localStorage.setItem('copyarena_api_key', sessionData.api_key)

      console.log(`✅ Session initialized: ${sessionData.username} (ID: ${sessionData.session_id})`)
      return sessionData
    } catch (error) {
      console.error('❌ Failed to initialize session:', error)
      throw error
    }
  }

  private clearStoredSession(): void {
    localStorage.removeItem('copyarena_session_id')
    localStorage.removeItem('copyarena_user_id') 
    localStorage.removeItem('copyarena_api_key')
    this.sessionId = null
    this.userId = null
    this.apiKey = null
  }

  getSessionId(): string | null {
    return this.sessionId || localStorage.getItem('copyarena_session_id')
  }

  getUserId(): number | null {
    if (this.userId) return this.userId
    const stored = localStorage.getItem('copyarena_user_id')
    return stored ? parseInt(stored) : null
  }

  getApiKey(): string | null {
    return this.apiKey || localStorage.getItem('copyarena_api_key')
  }

  clearSession(): void {
    this.clearStoredSession()
  }
}

export default SessionService 