/**
 * MT5 Web Connector - Connects to user's local MT5 terminal via HTTP API
 * This runs in the user's browser and connects to their local MT5 installation
 */

export interface MT5AccountInfo {
  login: number
  server: string
  name: string
  company: string
  currency: string
  balance: number
  equity: number
  margin: number
  free_margin: number
  margin_level: number
  profit: number
}

export interface MT5Position {
  ticket: number
  symbol: string
  type: 'BUY' | 'SELL'
  volume: number
  price_open: number
  price_current: number
  sl: number
  tp: number
  profit: number
  swap: number
  comment: string
  time_open: number
}

export interface MT5Connection {
  isConnected: boolean
  lastUpdate: number
  error?: string
}

export class MT5WebConnector {
  private baseUrl: string = 'http://localhost:8080' // MT5 Web API port
  private isConnected: boolean = false
  private accountInfo: MT5AccountInfo | null = null
  private positions: MT5Position[] = []
  private connectionTimeout: number = 5000

  constructor(port: number = 8080) {
    this.baseUrl = `http://localhost:${port}`
  }

  /**
   * Test connection to local MT5 terminal
   */
  async testConnection(): Promise<boolean> {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), this.connectionTimeout)
      
      const response = await fetch(`${this.baseUrl}/api/ping`, {
        method: 'GET',
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)
      
      if (response.ok) {
        this.isConnected = true
        return true
      }
      return false
    } catch (error) {
      console.error('MT5 connection failed:', error)
      this.isConnected = false
      return false
    }
  }

  /**
   * Get account information from local MT5
   */
  async getAccountInfo(): Promise<MT5AccountInfo | null> {
    if (!await this.testConnection()) {
      throw new Error('MT5 terminal not connected. Please ensure MT5 is running and Web API is enabled.')
    }

    try {
      const response = await fetch(`${this.baseUrl}/api/account`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      })

      if (response.ok) {
        this.accountInfo = await response.json()
        return this.accountInfo
      }
      
      throw new Error('Failed to get account info')
    } catch (error) {
      console.error('Failed to get MT5 account info:', error)
      throw error
    }
  }

  /**
   * Get current positions from local MT5
   */
  async getPositions(): Promise<MT5Position[]> {
    if (!await this.testConnection()) {
      throw new Error('MT5 terminal not connected')
    }

    try {
      const response = await fetch(`${this.baseUrl}/api/positions`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      })

      if (response.ok) {
        this.positions = await response.json()
        return this.positions
      }
      
      throw new Error('Failed to get positions')
    } catch (error) {
      console.error('Failed to get MT5 positions:', error)
      throw error
    }
  }

  /**
   * Send account data to your backend
   */
  async syncToBackend(backendUrl: string, userId: number): Promise<void> {
    try {
      const accountInfo = await this.getAccountInfo()
      const positions = await this.getPositions()

      const data = {
        userId,
        accountInfo,
        positions,
        timestamp: Date.now()
      }

      const response = await fetch(`${backendUrl}/api/mt5/sync`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth-token')}`
        },
        body: JSON.stringify(data)
      })

      if (!response.ok) {
        throw new Error('Failed to sync with backend')
      }
    } catch (error) {
      console.error('Backend sync failed:', error)
      throw error
    }
  }

  /**
   * Start real-time monitoring
   */
  startMonitoring(intervalMs: number = 5000, onUpdate?: (data: any) => void): () => void {
    const interval = setInterval(async () => {
      try {
        const accountInfo = await this.getAccountInfo()
        const positions = await this.getPositions()
        
        if (onUpdate) {
          onUpdate({ accountInfo, positions, timestamp: Date.now() })
        }
      } catch (error) {
        console.error('Monitoring error:', error)
      }
    }, intervalMs)

    return () => clearInterval(interval)
  }

  /**
   * Get connection status
   */
  getConnectionStatus(): MT5Connection {
    return {
      isConnected: this.isConnected,
      lastUpdate: Date.now(),
      error: this.isConnected ? undefined : 'MT5 terminal not connected'
    }
  }
}

// Default instance
export const mt5WebConnector = new MT5WebConnector()

// Helper functions
export const connectToMT5 = async (): Promise<boolean> => {
  return await mt5WebConnector.testConnection()
}

export const getMT5AccountInfo = async (): Promise<MT5AccountInfo | null> => {
  return await mt5WebConnector.getAccountInfo()
}

export const getMT5Positions = async (): Promise<MT5Position[]> => {
  return await mt5WebConnector.getPositions()
} 