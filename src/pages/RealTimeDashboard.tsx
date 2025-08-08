import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { useToast } from '../hooks/use-toast'
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Activity, 
  Users, 
  Clock,
  Wifi,
  WifiOff,
  RefreshCw
} from 'lucide-react'
import { formatCurrency, formatPercentage } from '../lib/utils'
import { api } from '../lib/api'

interface RealTimeData {
  trades: Array<{
    id: number
    ticket: string
    symbol: string
    trade_type: string
    volume: number
    open_price: number
    close_price?: number
    profit: number
    is_open: boolean
    open_time: string
    close_time?: string
    duration?: string
  }>
  analytics: {
    total_trades: number
    win_rate: number
    total_profit: number
    daily_profits: Record<string, number>
  }
  mt5_status: {
    connected: boolean
    login?: number
    server?: string
    last_sync?: string
  }
}

const RealTimeDashboard: React.FC = () => {
  const [data, setData] = useState<RealTimeData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const { toast } = useToast()

  useEffect(() => {
    loadRealTimeData()
    
    // Auto-refresh every 10 seconds
    const interval = setInterval(loadRealTimeData, 10000)
    return () => clearInterval(interval)
  }, [])

  const loadRealTimeData = async () => {
    try {
      setIsLoading(true)
      
      // Load all data in parallel
      const [tradesResponse, analyticsResponse, statusResponse] = await Promise.all([
        api.get('/api/trades/real-time'),
        api.get('/api/analytics/performance'),
        api.get('/api/mt5/status')
      ])

      setData({
        trades: tradesResponse.data,
        analytics: analyticsResponse.data,
        mt5_status: statusResponse.data
      })
      
      setLastUpdate(new Date())
      
    } catch (error) {
      console.error('Error loading real-time data:', error)
      toast({
        title: "Error",
        description: "Failed to load real-time data",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }

  const getOpenTrades = () => data?.trades.filter(t => t.is_open) || []
  const getClosedTrades = () => data?.trades.filter(t => !t.is_open) || []
  
  const getTotalUnrealizedPnL = () => {
    return getOpenTrades().reduce((sum, trade) => sum + trade.profit, 0)
  }

  const getRealizedPnL = () => {
    return getClosedTrades().reduce((sum, trade) => sum + trade.profit, 0)
  }

  if (isLoading && !data) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Real-Time Dashboard</h1>
            <p className="text-muted-foreground">Loading trading data...</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div className="h-4 bg-muted rounded w-24"></div>
                <div className="h-4 w-4 bg-muted rounded"></div>
              </CardHeader>
              <CardContent>
                <div className="h-8 bg-muted rounded w-16 mb-2"></div>
                <div className="h-3 bg-muted rounded w-32"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Real-Time Dashboard</h1>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>Last updated: {lastUpdate.toLocaleTimeString()}</span>
            {data?.mt5_status.connected ? (
              <Badge variant="online" className="ml-2">
                <Wifi className="h-3 w-3 mr-1" />
                MT5 Connected
              </Badge>
            ) : (
              <Badge variant="offline" className="ml-2">
                <WifiOff className="h-3 w-3 mr-1" />
                MT5 Disconnected
              </Badge>
            )}
          </div>
        </div>
        <Button onClick={loadRealTimeData} disabled={isLoading} size="sm">
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Open Positions</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{getOpenTrades().length}</div>
            <p className="text-xs text-muted-foreground">
              {formatCurrency(getTotalUnrealizedPnL())} unrealized
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Realized P&L</CardTitle>
            {getRealizedPnL() >= 0 ? (
              <TrendingUp className="h-4 w-4 text-green-600" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-600" />
            )}
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getRealizedPnL() >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(getRealizedPnL())}
            </div>
            <p className="text-xs text-muted-foreground">
              From {getClosedTrades().length} closed trades
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatPercentage(data?.analytics.win_rate || 0)}</div>
            <p className="text-xs text-muted-foreground">
              {data?.analytics.total_trades || 0} total trades
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Profit</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(data?.analytics.total_profit || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(data?.analytics.total_profit || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              All time performance
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Open Positions */}
      <Card>
        <CardHeader>
          <CardTitle>Open Positions ({getOpenTrades().length})</CardTitle>
          <CardDescription>
            Real-time view of your active trades
          </CardDescription>
        </CardHeader>
        <CardContent>
          {getOpenTrades().length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No open positions
            </div>
          ) : (
            <div className="space-y-3">
              {getOpenTrades().map((trade) => (
                <div key={trade.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <Badge variant={trade.trade_type === 'BUY' ? 'profit' : 'loss'}>
                      {trade.trade_type}
                    </Badge>
                    <div>
                      <p className="font-medium">{trade.symbol}</p>
                      <p className="text-sm text-muted-foreground">
                        {trade.volume} lots @ {trade.open_price}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`font-medium ${trade.profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatCurrency(trade.profit)}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {trade.duration || 'Active'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Closed Trades */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Closed Trades</CardTitle>
          <CardDescription>
            Last 10 completed trades
          </CardDescription>
        </CardHeader>
        <CardContent>
          {getClosedTrades().length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No closed trades today
            </div>
          ) : (
            <div className="space-y-3">
              {getClosedTrades().slice(0, 10).map((trade) => (
                <div key={trade.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <Badge variant={trade.trade_type === 'BUY' ? 'profit' : 'loss'}>
                      {trade.trade_type}
                    </Badge>
                    <div>
                      <p className="font-medium">{trade.symbol}</p>
                      <p className="text-sm text-muted-foreground">
                        {trade.volume} lots • {new Date(trade.close_time!).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`font-medium ${trade.profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatCurrency(trade.profit)}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {trade.open_price} → {trade.close_price}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Connection Status */}
      {!data?.mt5_status.connected && (
        <Card className="border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20">
          <CardHeader>
            <CardTitle className="text-yellow-800 dark:text-yellow-200">MT5 Not Connected</CardTitle>
            <CardDescription className="text-yellow-700 dark:text-yellow-300">
              Connect your MetaTrader 5 account to see real-time trading data
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <a href="/mt5">Connect MT5 Account</a>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default RealTimeDashboard 