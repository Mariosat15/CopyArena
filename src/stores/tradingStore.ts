import { create } from 'zustand'
import { api } from '../lib/api'

export interface Trade {
  id: number
  ticket: string
  symbol: string
  trade_type: 'BUY' | 'SELL'
  volume: number
  open_price: number
  close_price?: number
  open_time: string
  close_time?: string
  profit: number
  is_open: boolean
}

export interface AccountStats {
  account: {
    login: number | null
    server: string | null
    company: string | null
    currency: string
    balance: number
    equity: number
    margin: number
    free_margin: number
    margin_level: number
  }
  trading: {
    total_trades: number
    open_trades: number
    closed_trades: number
    historical_profit: number
    floating_profit: number
    total_profit: number
    win_rate: number
  }
  status: {
    mt5_connected: boolean
    last_update: string
  }
}

export interface Trader {
  id: number
  username: string
  avatar_url?: string
  xp_points: number
  level: number
  is_online: boolean
  stats: {
    total_trades: number
    win_rate: number
    total_profit: number
    followers_count: number
  }
}

export interface Follow {
  id: number
  trader_id: number
  auto_copy: boolean
  max_trade_size: number
  risk_level: number
  created_at: string
}

interface TradingState {
  trades: Trade[]
  accountStats: AccountStats | null
  traders: Trader[]
  follows: Follow[]
  leaderboard: Trader[]
  
  // LIVE EA Data (bypasses database)
  livePositions: any[]
  liveAccountStats: any
  
  // Actions
  fetchTrades: () => Promise<void>
  fetchAccountStats: () => Promise<void>
  fetchTraders: (filters?: any) => Promise<void>
  fetchLeaderboard: (sortBy?: string) => Promise<void>
  followTrader: (traderId: number, settings: Partial<Follow>) => Promise<void>
  unfollowTrader: (traderId: number) => Promise<void>
  
  // Real-time updates
  addTrade: (trade: Trade) => void
  updateTrade: (trade: Trade) => void
  removeDuplicateTrades: () => void
  updateTraderStatus: (traderId: number, isOnline: boolean) => void
  
  // LIVE EA Data Updates
  setLivePositions: (positions: any[]) => void
  setLiveAccountStats: (stats: any) => void
}

export const useTradingStore = create<TradingState>((set) => ({
  trades: [],
  accountStats: null,
  traders: [],
  follows: [],
  leaderboard: [],
  
  // LIVE EA Data
  livePositions: [],
  liveAccountStats: null,

  fetchTrades: async () => {
    try {
      console.log('🔄 Fetching trades...')
      const response = await api.get('/api/trades')
      const trades = response.data.trades || response.data || []
      console.log(`✅ Fetched ${trades.length} trades`)
      set({ trades })
    } catch (error) {
      console.error('❌ Failed to fetch trades:', error)
    }
  },

  fetchAccountStats: async () => {
    try {
      console.log('🔄 Fetching account stats...')
      const response = await api.get('/api/account/stats')
      console.log('✅ Account stats:', response.data)
      set({ accountStats: response.data })
    } catch (error) {
      console.error('❌ Failed to fetch account stats:', error)
    }
  },

  fetchTraders: async (filters = {}) => {
    try {
      const params = new URLSearchParams(filters)
              const response = await api.get(`/api/marketplace/traders?${params}`)
      set({ traders: response.data })
    } catch (error) {
      console.error('Failed to fetch traders:', error)
    }
  },

  fetchLeaderboard: async (sortBy = 'xp_points') => {
    try {
      const response = await api.get(`/api/leaderboard?sort_by=${sortBy}`)
      set({ leaderboard: response.data })
    } catch (error) {
      console.error('Failed to fetch leaderboard:', error)
    }
  },

  followTrader: async (traderId: number, settings: Partial<Follow>) => {
    try {
      await api.post('/api/follow', {
        trader_id: traderId,
        ...settings
      })
      
      // Update local state
      const newFollow: Follow = {
        id: Date.now(), // Temporary ID
        trader_id: traderId,
        auto_copy: settings.auto_copy || false,
        max_trade_size: settings.max_trade_size || 0.01,
        risk_level: settings.risk_level || 1.0,
        created_at: new Date().toISOString()
      }
      
      set(state => ({
        follows: [...state.follows, newFollow]
      }))
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to follow trader')
    }
  },

  unfollowTrader: async (traderId: number) => {
    try {
      await api.delete(`/api/follow/${traderId}`)
      
      set(state => ({
        follows: state.follows.filter(f => f.trader_id !== traderId)
      }))
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to unfollow trader')
    }
  },

  addTrade: (trade: Trade) => {
    set(state => ({
      trades: [trade, ...state.trades]
    }))
  },

  updateTrade: (updatedTrade: Trade) => {
    set(state => {
      // First, find if this trade exists by ID
      const existingTradeIndex = state.trades.findIndex(trade => trade.id === updatedTrade.id)
      
      if (existingTradeIndex !== -1) {
        // Trade exists by ID, update it
        const newTrades = [...state.trades]
        newTrades[existingTradeIndex] = updatedTrade
        return { trades: newTrades }
      } else {
        // Trade doesn't exist by ID, check by ticket (for duplicate cleanup)
        const existingTicketIndex = state.trades.findIndex(trade => trade.ticket === updatedTrade.ticket)
        
        if (existingTicketIndex !== -1) {
          // Found by ticket, update it
          const newTrades = [...state.trades]
          newTrades[existingTicketIndex] = updatedTrade
          return { trades: newTrades }
        } else {
          // Trade doesn't exist, add it
          return { trades: [updatedTrade, ...state.trades] }
        }
      }
    })
  },

  // Add a new function to remove duplicate trades
  removeDuplicateTrades: () => {
    set(state => {
      const uniqueTrades = state.trades.reduce((acc: Trade[], current) => {
        const existingIndex = acc.findIndex(trade => trade.ticket === current.ticket)
        if (existingIndex !== -1) {
          // Keep the most recent one (higher ID or more recent update)
          if (current.id > acc[existingIndex].id) {
            acc[existingIndex] = current
          }
        } else {
          acc.push(current)
        }
        return acc
      }, [])
      
      return { trades: uniqueTrades }
    })
  },

  updateTraderStatus: (traderId: number, isOnline: boolean) => {
    set(state => ({
      traders: state.traders.map(trader =>
        trader.id === traderId ? { ...trader, is_online: isOnline } : trader
      ),
      leaderboard: state.leaderboard.map(trader =>
        trader.id === traderId ? { ...trader, is_online: isOnline } : trader
      )
    }))
  },

  // LIVE EA Data Setters
  setLivePositions: (positions: any[]) => {
    console.log('🎯 Setting LIVE positions:', positions)
    set({ livePositions: positions })
  },

  setLiveAccountStats: (stats: any) => {
    console.log('🎯 Setting LIVE account stats:', stats)
    set({ liveAccountStats: stats })
  }
})) 