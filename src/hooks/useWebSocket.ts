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
    const wsUrl = `ws://127.0.0.1:8000/ws/user/${userId}`
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
          case 'trade_update':
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
            toast({
              title: "Account Update",
              description: `Balance: $${data.data.balance?.toFixed(2) || 'N/A'}`,
            })
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

          case 'trades_synced':
            // Refresh trades data when sync is complete
            console.log('Trades synced:', data.data)
            toast({
              title: "Trades Synced! ✅",
              description: data.data.message,
              variant: "default",
            })
            // Trigger trades refresh in the trading store
            const { fetchTrades } = useTradingStore.getState()
            fetchTrades()
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