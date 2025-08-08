import { useEffect, useRef } from 'react'
import { useTradingStore } from '../stores/tradingStore'
import { useAuthStore } from '../stores/authStore'
import { toast } from '../hooks/use-toast'

export const useWebSocket = (userId?: number) => {
  const socketRef = useRef<WebSocket | null>(null)
  const { addTrade, updateTrade, updateTraderStatus } = useTradingStore()
  const { updateUser } = useAuthStore()

  useEffect(() => {
    if (!userId) return

    // Create native WebSocket connection
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    const isNetworkAccess = window.location.hostname.startsWith('192.168.') || window.location.hostname.startsWith('10.') || window.location.hostname.startsWith('172.')
    const isProduction = !isLocalhost && !isNetworkAccess
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = isProduction ? window.location.host : `${window.location.hostname}:8002`
    const wsUrl = `${wsProtocol}//${wsHost}/ws/user/${userId}`
    const socket = new WebSocket(wsUrl)

    socketRef.current = socket

    // Connection events
    socket.onopen = () => {
      console.log('Connected to WebSocket server')
      toast({
        title: "Connected",
        description: "Real-time updates enabled",
      })
    }

    socket.onclose = () => {
      console.log('Disconnected from WebSocket server')
      toast({
        title: "Disconnected",
        description: "Real-time updates disabled",
        variant: "destructive",
      })
    }

    socket.onerror = (error) => {
      console.error('WebSocket error:', error)
      toast({
        title: "Connection Error",
        description: "Failed to establish real-time connection",
        variant: "destructive",
      })
    }

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('Received WebSocket message:', data)

        switch (data.type) {
          case 'trade_new':
            // New trade added
            addTrade(data.data)
            toast({
              title: "New Trade Opened! 📈",
              description: `${data.data.symbol} ${data.data.trade_type} ${data.data.volume} lots`,
              variant: "default",
            })
            break

          case 'trade_updated':
            // Existing trade updated (P&L change) - silently update
            updateTrade(data.data)
            // No toast for trade updates - too frequent, just update the UI
            break

          case 'trade_closed':
            // Trade was closed
            updateTrade(data.data)
            toast({
              title: "Trade Closed! 🎯",
              description: data.data.message,
              variant: data.data.profit >= 0 ? "default" : "destructive",
            })
            break

          case 'trade_update':
            // Legacy trade update (keep for backwards compatibility)
            if (data.data.is_open) {
              updateTrade(data.data)
            } else {
              addTrade(data.data)
            }
            toast({
              title: "Trade Update",
              description: `${data.data.symbol} ${data.data.trade_type}: ${data.data.profit > 0 ? '+' : ''}$${data.data.profit.toFixed(2)}`,
              variant: data.data.profit > 0 ? "default" : "destructive",
            })
            break

          case 'account_update':
            console.log('Account update:', data.data)
            // Refresh account stats when account updates (silently)
            useTradingStore.getState().fetchAccountStats()
            // No toast notification for account updates - too frequent
            break

          case 'positions_update':
            console.log('🚀 LIVE Positions from EA:', data.data)
            // Update UI DIRECTLY with EA data (not database)
            useTradingStore.getState().setLivePositions(data.data)
            // Also update account stats
            useTradingStore.getState().fetchAccountStats()
            break

          case 'account_update':
            console.log('🚀 LIVE Account from EA:', data.data)
            // Update UI DIRECTLY with EA account data
            useTradingStore.getState().setLiveAccountStats(data.data)
            break

          case 'positions_updated':
            console.log('🚀 LIVE positions updated:', data.data)
            // Show toast for new trades
            if (data.data?.new > 0) {
              toast({
                title: "New Trade Opened! 📈",
                description: `${data.data.new} new trade(s) detected`,
              })
            }
            // Show toast and refresh data for closed trades
            if (data.data?.closed > 0) {
              toast({
                title: "Trades Closed! 🔒",
                description: `${data.data.closed} trade(s) were closed`,
              })
              // Refresh database trades to update closed count
              useTradingStore.getState().fetchTrades()
            }
            break

          case 'all_trades_closed':
            console.log('🔒 All trades closed:', data.data)
            // Clear live positions and refresh data
            useTradingStore.getState().setLivePositions([])
            useTradingStore.getState().fetchTrades()
            useTradingStore.getState().fetchAccountStats()
            toast({
              title: "All Trades Closed! 🔒",
              description: `${data.data.closed} trade(s) were closed`,
            })
            break

          case 'orders_update':
            console.log('Orders update:', data.data)
            // Refresh account stats when orders change
            useTradingStore.getState().fetchAccountStats()
            break

          case 'history_update':
            console.log('🚀 LIVE History from EA:', data.data)
            // Update UI DIRECTLY with EA history data (closed trades)
            useTradingStore.getState().setLiveHistory(data.data)
            break

          case 'connection_status':
            console.log('EA connection status:', data.data)
            // Force refresh all data when EA connects/reconnects
            if (data.data.is_connected) {
              console.log('🚀 EA connected - refreshing all data')
              useTradingStore.getState().fetchTrades()
              useTradingStore.getState().fetchAccountStats()
              toast({
                title: "MT5 Connected! 🎯",
                description: "Your EA is now sending live trading data",
              })
            }
            break

          case 'xp_update':
            updateUser({ xp_points: data.data.new_total })
            toast({
              title: "XP Gained!",
              description: `+${data.data.xp_gained} XP`,
            })
            break

          case 'level_up':
            updateUser({ level: data.data.new_level })
            toast({
              title: "Level Up! 🎉",
              description: `You reached level ${data.data.new_level}!`,
            })
            break

          case 'badge_earned':
            toast({
              title: "Badge Earned! 🏆",
              description: `You earned: ${data.data.name}`,
            })
            break

          case 'copy_trade':
            addTrade(data.data.trade)
            toast({
              title: "Trade Copied",
              description: data.data.message,
            })
            break

          case 'margin_warning':
            // Margin level warning with different severity levels
            let title, description
            
            if (data.data.severity === 'critical') {
              title = "🚨 CRITICAL MARGIN LEVEL!"
              description = `${data.data.message} - Immediate action required!`
            } else if (data.data.severity === 'high') {
              title = "🚨 MARGIN CALL ALERT!"
              description = `${data.data.message} - Risk of position closure!`
            } else {
              title = "⚠️ MARGIN WARNING!"
              description = `${data.data.message} - Consider reducing position size!`
            }
            
            toast({
              title,
              description,
              variant: "destructive",
            })
            break

          case 'trades_synced':
            // Refresh trades data when sync is complete (silently)
            console.log('Trades synced:', data.data)
            
            // Always refresh data, but only show toast for significant changes
            const { fetchTrades, fetchAccountStats, removeDuplicateTrades } = useTradingStore.getState()
            Promise.all([fetchTrades(), fetchAccountStats()])
            
            // Only show toast for new or removed trades (not just updates)
            if (data.data.new_trades > 0 || (data.data.removed_trades && data.data.removed_trades > 0)) {
              toast({
                title: "Trades Synced! ✅",
                description: `${data.data.new_trades} new, ${data.data.removed_trades || 0} removed`,
                variant: "default",
              })
            }
            
            // Remove any duplicates after sync
            setTimeout(() => removeDuplicateTrades(), 1000)
            break

          case 'leaderboard_update':
            // Refresh leaderboard data
            console.log('Leaderboard update:', data)
            break

          case 'ping':
            // Send pong response
            socket.send(JSON.stringify({ type: 'pong', timestamp: new Date().toISOString() }))
            break

          case 'pong':
            // Connection is alive
            console.log('Received pong from server')
            break

          default:
            console.log('Unknown message type:', data.type)
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }

    // Send ping every 30 seconds to keep connection alive
    const pingInterval = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'ping', timestamp: new Date().toISOString() }))
      }
    }, 30000)

    // Cleanup on unmount
    return () => {
      clearInterval(pingInterval)
      if (socket.readyState === WebSocket.OPEN) {
        socket.close()
      }
    }
  }, [userId, addTrade, updateTrade, updateTraderStatus, updateUser])

  return socketRef.current
} 