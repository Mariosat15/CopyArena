import { create } from 'zustand'
import axios from 'axios'

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
  traders: Trader[]
  follows: Follow[]
  leaderboard: Trader[]
  
  // Actions
  fetchTrades: () => Promise<void>
  fetchTraders: (filters?: any) => Promise<void>
  fetchLeaderboard: (sortBy?: string) => Promise<void>
  followTrader: (traderId: number, settings: Partial<Follow>) => Promise<void>
  unfollowTrader: (traderId: number) => Promise<void>
  
  // Real-time updates
  addTrade: (trade: Trade) => void
  updateTrade: (trade: Trade) => void
  updateTraderStatus: (traderId: number, isOnline: boolean) => void
}

export const useTradingStore = create<TradingState>((set, get) => ({
  trades: [],
  traders: [],
  follows: [],
  leaderboard: [],

  fetchTrades: async () => {
    try {
      const response = await axios.get('/api/trades')
      set({ trades: response.data })
    } catch (error) {
      console.error('Failed to fetch trades:', error)
    }
  },

  fetchTraders: async (filters = {}) => {
    try {
      const params = new URLSearchParams(filters)
      const response = await axios.get(`/api/marketplace/traders?${params}`)
      set({ traders: response.data })
    } catch (error) {
      console.error('Failed to fetch traders:', error)
    }
  },

  fetchLeaderboard: async (sortBy = 'xp_points') => {
    try {
      const response = await axios.get(`/api/leaderboard?sort_by=${sortBy}`)
      set({ leaderboard: response.data })
    } catch (error) {
      console.error('Failed to fetch leaderboard:', error)
    }
  },

  followTrader: async (traderId: number, settings: Partial<Follow>) => {
    try {
      await axios.post('/api/follow', {
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
      await axios.delete(`/api/follow/${traderId}`)
      
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
    set(state => ({
      trades: state.trades.map(trade => 
        trade.id === updatedTrade.id ? updatedTrade : trade
      )
    }))
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
  }
})) 