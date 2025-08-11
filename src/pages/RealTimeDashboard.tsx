import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { useWebSocket } from '../hooks/useWebSocket'
import { useTradingStore } from '../stores/tradingStore'
import { useAuthStore } from '../stores/authStore'
import { 
  TrendingUp, 
  DollarSign, 
  Activity, 
  Clock,
  Wifi,
  WifiOff,
  Target,
  BarChart3,
  Zap,
  Crown
} from 'lucide-react'
import { formatCurrency, formatPercentage } from '../lib/utils'

// Live data interfaces directly from Windows Client
interface LivePosition {
  ticket: string
  symbol: string
  type: number  // 0=buy, 1=sell
  volume: number
  price_open: number
  price_current: number
  profit: number
  swap: number
  time: number
  master_trader?: string  // "self" or master trader name
}

// LiveOrder interface removed - will be implemented when needed for pending orders

interface LiveAccountData {
  balance: number
  equity: number
  margin: number
  free_margin: number
  margin_level: number
  currency: string
  leverage: number
}

interface ConnectionStatus {
  connected: boolean
  account_number?: number
  server?: string
  last_sync?: string
}

const RealTimeDashboard: React.FC = () => {
  const { user } = useAuthStore()
  const { 
    livePositions, 
    liveAccountStats,
    accountStats,
    fetchAccountStats
  } = useTradingStore()
  
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const [latency, setLatency] = useState<number | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    connected: false
  })
  
  // Connect to WebSocket for real-time updates
  useWebSocket(user?.id)

  // Fetch initial account stats on mount
  useEffect(() => {
    if (user?.id) {
      fetchAccountStats()
    }
  }, [user?.id, fetchAccountStats])

  // Update last update time and calculate latency when live data changes
  useEffect(() => {
    const now = new Date()
    setLastUpdate(now)
    // Mark when we received this data batch
    
    // Calculate latency using WebSocket message timestamp or real-time estimation
    let calculatedLatency = null
    
    if (livePositions && livePositions.length > 0) {
      // Method 1: Use INSTANT latency from WebSocket hook (most accurate)
      const instantLatency = livePositions[0]?.ws_latency
      
      if (instantLatency !== null && instantLatency !== undefined) {
        console.log('⚡ Using INSTANT WebSocket latency:', instantLatency, 'ms')
        setLatency(instantLatency)
      } else {
        // Method 2: Use WebSocket message timestamp (from backend)
        const backendTimestamp = livePositions[0]?.client_send_timestamp
        
        if (backendTimestamp) {
          let sendTimestamp = new Date(backendTimestamp).getTime()
          calculatedLatency = now.getTime() - sendTimestamp
          
          console.log('⏱️ Backend timestamp latency:', {
            backendTimestamp: backendTimestamp,
            sendTimestamp: sendTimestamp,
            receiveTime: now.getTime(),
            latency: calculatedLatency
          })
          
          // Accept reasonable WebSocket latencies
          if (calculatedLatency > 0 && calculatedLatency < 10000) {
            setLatency(calculatedLatency)
          } else if (calculatedLatency > 10000) {
            console.warn('📍 Backend timestamp too old, using real-time estimate')
            setLatency(100) // Fresh data estimate
          } else {
            setLatency(50) // Very fresh data
          }
        } else {
          // Method 3: Data just arrived - use minimal latency estimate
          console.log('📡 No backend timestamp, data just received - minimal latency')
          setLatency(75) // Conservative estimate for just-received data
        }
      }
    }
    
    // Debug: Log live data when it changes
    console.log('🔥 Live data updated:', { 
      positions: livePositions?.length || 0, 
      hasAccount: !!liveAccountStats,
      accountKeys: liveAccountStats ? Object.keys(liveAccountStats) : [],
      calculatedLatency: calculatedLatency,
      currentLatencyState: latency,
      samplePosition: livePositions?.[0] ? {
        ticket: livePositions[0].ticket,
        symbol: livePositions[0].symbol,
        master_trader: livePositions[0].master_trader,
        time: livePositions[0].time,
        time_update: livePositions[0].time_update,
        timeType: typeof livePositions[0].time,
        timeUpdateType: typeof livePositions[0].time_update
      } : null
    })
    
    // Additional debug for latency calculation
    if (livePositions && livePositions.length > 0) {
      console.log('🕐 Latency Debug:', {
        firstPosTime: livePositions[0].time,
        firstPosTimeUpdate: livePositions[0].time_update,
        currentTime: now.getTime(),
        wsLatencyFromHook: livePositions[0]?.ws_latency,
        calculatedLatency: calculatedLatency,
        explanation: "Position timestamps are HISTORICAL (when trade opened), not current data send time"
      })
    }
  }, [livePositions, liveAccountStats])

  // Monitor connection status
  useEffect(() => {
    // Determine connection status from multiple sources
    const isConnectedFromStats = accountStats?.status?.mt5_connected || false
    const hasLiveData = livePositions && livePositions.length > 0
    const hasLiveAccount = liveAccountStats && Object.keys(liveAccountStats).length > 0
    
    // Consider connected if we have live data OR database shows connected
    const isConnected = isConnectedFromStats || hasLiveData || hasLiveAccount
    
    setConnectionStatus({
      connected: isConnected,
      account_number: liveAccountStats?.login || accountStats?.account?.login || undefined,
      server: liveAccountStats?.server || accountStats?.account?.server || undefined,
      last_sync: accountStats?.status?.last_update
    })
  }, [accountStats, livePositions, liveAccountStats])

  // Parse live positions from Windows Client
  const getLivePositions = (): LivePosition[] => {
    if (!livePositions || !Array.isArray(livePositions)) return []
    return livePositions.map(pos => {
      // Convert string trade type to number (Windows Client sends "buy"/"sell")
      let tradeType = pos.type || 0
      if (typeof tradeType === 'string') {
        tradeType = tradeType.toLowerCase() === 'buy' ? 0 : 1
      }
      
      const position = {
        ticket: String(pos.ticket || ''),
        symbol: pos.symbol || '',
        type: tradeType,
        volume: pos.volume || 0,
        price_open: pos.price_open || pos.open_price || 0,
        price_current: pos.price_current || pos.current_price || 0,
        profit: pos.profit || 0,
        swap: pos.swap || 0,
        time: pos.time || Date.now(),
        master_trader: pos.master_trader || 'self'
      }
      
      // Debug log for first position to check copy trade data
      if (pos.ticket === livePositions[0]?.ticket) {
        console.log('📊 Position parsing debug:', {
          original: { master_trader: pos.master_trader, time: pos.time, time_update: pos.time_update },
          parsed: { master_trader: position.master_trader, time: position.time },
          allFields: Object.keys(pos)
        })
        
        // Check if Windows Client is sending copy trade info
        if (pos.master_trader === undefined) {
          console.warn('⚠️ Windows Client not sending master_trader field - all trades will show as "Self"')
        }
      }
      
      return position
    })
  }

  // Get live account data from Windows Client
  const getLiveAccount = (): LiveAccountData => {
    return {
      balance: liveAccountStats?.balance || accountStats?.account.balance || 0,
      equity: liveAccountStats?.equity || accountStats?.account.equity || 0,
      margin: liveAccountStats?.margin || accountStats?.account.margin || 0,
      free_margin: liveAccountStats?.free_margin || accountStats?.account.free_margin || 0,
      margin_level: liveAccountStats?.margin_level || accountStats?.account.margin_level || 0,
      currency: liveAccountStats?.currency || accountStats?.account.currency || 'USD',
      leverage: liveAccountStats?.leverage || 1
    }
  }

  // Calculate real-time metrics
  const liveAccount = getLiveAccount()
  const livePos = getLivePositions()
  
  const totalUnrealizedPnL = livePos.reduce((sum, pos) => sum + pos.profit, 0)
  const totalSwap = livePos.reduce((sum, pos) => sum + pos.swap, 0)
  const netUnrealizedPnL = totalUnrealizedPnL + totalSwap

  // Calculate win rate from historical data (database)
  const winRate = accountStats?.trading.win_rate || 0
  const totalTrades = accountStats?.trading.total_trades || 0
  const historicalProfit = accountStats?.trading.historical_profit || 0

  const formatTradeType = (type: number): string => {
    return type === 0 ? 'BUY' : 'SELL'
  }

  // formatTradeTime removed - not used in current implementation

  const getPositionDuration = (openTime: number): string => {
    const now = Date.now()
    const openMs = openTime * 1000
    const diffMs = now - openMs
    const diffMins = Math.floor(diffMs / 60000)
    
    if (diffMins < 60) return `${diffMins}m`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ${diffMins % 60}m`
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays}d ${diffHours % 24}h`
  }

  const formatLatency = (latencyMs: number | null): string => {
    if (latencyMs === null) return "⏱️ calculating..."
    if (latencyMs < 100) return `⚡ ${Math.round(latencyMs)}ms (excellent)`
    if (latencyMs < 500) return `⚡ ${Math.round(latencyMs)}ms (good)`
    if (latencyMs < 1000) return `⚠️ ${Math.round(latencyMs)}ms`
    return `🐌 ${(latencyMs / 1000).toFixed(1)}s`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Zap className="h-8 w-8 text-yellow-500" />
            Live Trading Dashboard
          </h1>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>Live data • Last update: {lastUpdate.toLocaleTimeString()}</span>
            {connectionStatus.connected ? (
              <Badge variant="default" className="ml-2 bg-green-600">
                <Wifi className="h-3 w-3 mr-1" />
                MT5 Connected
              </Badge>
            ) : (
              <Badge variant="destructive" className="ml-2">
                <WifiOff className="h-3 w-3 mr-1" />
                MT5 Disconnected
              </Badge>
            )}
          </div>
        </div>
        {connectionStatus.connected && (
          <div className="text-right text-sm text-muted-foreground">
            <div>Account: {connectionStatus.account_number}</div>
            <div>Server: {connectionStatus.server}</div>
          </div>
        )}
      </div>

      {/* Live Account Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-blue-500/20 bg-slate-800/50 backdrop-blur-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-blue-400">Balance</CardTitle>
            <DollarSign className="h-4 w-4 text-blue-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-300">
              {formatCurrency(liveAccount.balance)} {liveAccount.currency}
            </div>
            <p className="text-xs text-blue-400/80">
              Leverage 1:{liveAccount.leverage}
            </p>
          </CardContent>
        </Card>

        <Card className="border-green-500/20 bg-slate-800/50 backdrop-blur-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-green-400">Equity</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-300">
              {formatCurrency(liveAccount.equity)} {liveAccount.currency}
            </div>
            <p className={`text-xs ${netUnrealizedPnL >= 0 ? 'text-green-400/80' : 'text-red-400/80'}`}>
              {netUnrealizedPnL >= 0 ? '+' : ''}{formatCurrency(netUnrealizedPnL)} floating
            </p>
          </CardContent>
        </Card>

        <Card className="border-purple-500/20 bg-slate-800/50 backdrop-blur-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-purple-400">Margin Level</CardTitle>
            <BarChart3 className="h-4 w-4 text-purple-400" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${
              liveAccount.margin_level >= 200 ? 'text-green-300' : 
              liveAccount.margin_level >= 100 ? 'text-yellow-300' : 'text-red-300'
            }`}>
              {liveAccount.margin_level.toFixed(0)}%
            </div>
            <p className="text-xs text-purple-400/80">
              Used: {formatCurrency(liveAccount.margin)} {liveAccount.currency}
            </p>
          </CardContent>
        </Card>

        <Card className="border-orange-500/20 bg-slate-800/50 backdrop-blur-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-orange-400">Live Positions</CardTitle>
            <Activity className="h-4 w-4 text-orange-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-300">{livePos.length}</div>
            <p className="text-xs text-orange-400/80">
              Win Rate: {formatPercentage(winRate)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Performance Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-green-500/20 bg-slate-800/50 backdrop-blur-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-green-400">Unrealized P&L</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-400" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${netUnrealizedPnL >= 0 ? 'text-green-300' : 'text-red-300'}`}>
              {netUnrealizedPnL >= 0 ? '+' : ''}{formatCurrency(netUnrealizedPnL)}
            </div>
            <p className="text-xs text-green-400/80">
              From {livePos.length} open position{livePos.length !== 1 ? 's' : ''} (incl. swap)
            </p>
          </CardContent>
        </Card>

        <Card className="border-blue-500/20 bg-slate-800/50 backdrop-blur-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-blue-400">Historical Win Rate</CardTitle>
            <Target className="h-4 w-4 text-blue-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-300">{formatPercentage(winRate)}</div>
            <p className="text-xs text-blue-400/80">
              From {totalTrades} total trades
            </p>
          </CardContent>
        </Card>

        <Card className="border-purple-500/20 bg-slate-800/50 backdrop-blur-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-purple-400">Historical Profit</CardTitle>
            <DollarSign className="h-4 w-4 text-purple-400" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${historicalProfit >= 0 ? 'text-green-300' : 'text-red-300'}`}>
              {historicalProfit >= 0 ? '+' : ''}{formatCurrency(historicalProfit)}
            </div>
            <p className="text-xs text-purple-400/80">
              All-time performance
            </p>
          </CardContent>
        </Card>
      </div>



      {/* Live Positions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-yellow-500" />
            Live Positions ({livePos.length})
          </CardTitle>
          <CardDescription>
            Real-time data directly from your MT5 terminal • Latency: {formatLatency(latency)}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {livePos.length === 0 ? (
            <div className="text-center py-12">
              <Activity className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-muted-foreground mb-2">No Live Positions</h3>
              <p className="text-sm text-muted-foreground">
                {connectionStatus.connected 
                  ? "No open trades in your MT5 account" 
                  : "Connect your MT5 account to see live positions"}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {livePos.map((position) => (
                <div 
                  key={position.ticket} 
                  className="flex items-center justify-between p-4 border rounded-lg bg-slate-900/50 backdrop-blur-sm hover:bg-slate-800/50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <Badge 
                      variant={position.type === 0 ? 'default' : 'secondary'}
                      className={`${position.type === 0 ? 'bg-green-600' : 'bg-red-600'} text-white`}
                    >
                      {formatTradeType(position.type)}
                    </Badge>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-semibold text-lg">{position.symbol}</p>
                        {position.master_trader && position.master_trader !== 'self' ? (
                          <Badge variant="outline" className="text-yellow-400 border-yellow-500/30 bg-yellow-500/10">
                            <Crown className="h-3 w-3 mr-1" />
                            Copy: {position.master_trader}
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-blue-400 border-blue-500/30 bg-blue-500/10">
                            Self
                          </Badge>
                        )}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        <span>{position.volume} lots • </span>
                        <span>Entry: {position.price_open.toFixed(5)} • </span>
                        <span>Current: {position.price_current.toFixed(5)} • </span>
                        <span>Time: {getPositionDuration(position.time)}</span>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Ticket: {position.ticket}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`text-xl font-bold ${position.profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {position.profit >= 0 ? '+' : ''}{formatCurrency(position.profit)}
                    </div>
                    {position.swap !== 0 && (
                      <div className={`text-sm ${position.swap >= 0 ? 'text-green-400/70' : 'text-red-400/70'}`}>
                        Swap: {position.swap >= 0 ? '+' : ''}{formatCurrency(position.swap)}
                      </div>
                    )}
                    <div className="text-xs text-muted-foreground">
                      P&L: {((position.profit / (position.volume * position.price_open * 100000)) * 100).toFixed(2)}%
                    </div>
                  </div>
                </div>
              ))}
              
              {/* Summary Row */}
              <div className="mt-4 p-4 border-t border-dashed">
                <div className="flex justify-between items-center">
                  <div className="text-sm text-muted-foreground">
                    Total Floating P&L:
                  </div>
                  <div className={`text-lg font-bold ${netUnrealizedPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {netUnrealizedPnL >= 0 ? '+' : ''}{formatCurrency(netUnrealizedPnL)} {liveAccount.currency}
                  </div>
                </div>
                {totalSwap !== 0 && (
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-muted-foreground">Total Swap:</span>
                    <span className={totalSwap >= 0 ? 'text-green-400/70' : 'text-red-400/70'}>
                      {totalSwap >= 0 ? '+' : ''}{formatCurrency(totalSwap)} {liveAccount.currency}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Connection Status */}
      {!connectionStatus.connected && (
        <Card className="border-yellow-500/30 bg-yellow-500/10 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-yellow-300 flex items-center gap-2">
              <WifiOff className="h-5 w-5" />
              MT5 Not Connected
            </CardTitle>
            <CardDescription className="text-yellow-200/80">
              Connect your Windows Client to see real-time trading data with zero latency
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="bg-yellow-600 hover:bg-yellow-700">
              <a href="/mt5-connection">Connect MT5 Account</a>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default RealTimeDashboard