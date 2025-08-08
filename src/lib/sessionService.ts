interface SessionResponse {
  session_id: string
  user_id: number
  username: string
  message: string
}

class SessionService {
  private static instance: SessionService
  private sessionId: string | null = null
  private userId: number | null = null

  static getInstance(): SessionService {
    if (!SessionService.instance) {
      SessionService.instance = new SessionService()
    }
    return SessionService.instance
  }

  async initializeSession(): Promise<SessionResponse> {
    try {
      const response = await fetch('/api/auth/session', {
        method: 'POST',
        credentials: 'include', // Include cookies
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error('Failed to create session')
      }

      const sessionData: SessionResponse = await response.json()
      this.sessionId = sessionData.session_id
      this.userId = sessionData.user_id

      console.log(`✅ Session initialized: ${sessionData.username} (ID: ${sessionData.session_id})`)
      return sessionData
    } catch (error) {
      console.error('❌ Failed to initialize session:', error)
      throw error
    }
  }

  getSessionId(): string | null {
    return this.sessionId
  }

  getUserId(): number | null {
    return this.userId
  }

  isSessionActive(): boolean {
    return this.sessionId !== null && this.userId !== null
  }
}

export const sessionService = SessionService.getInstance() 