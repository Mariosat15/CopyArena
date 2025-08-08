// @ts-ignore
import React, { useEffect, useState } from 'react'
import { useAuthStore } from '../stores/authStore'
import { useTradingStore } from '../stores/tradingStore'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { TrendingUp, Users, Trophy, Target, Zap, RefreshCw, Activity, DollarSign, PieChart, Calculator } from 'lucide-react'
import { formatCurrency } from '../lib/utils'
import { useToast } from '../hooks/use-toast'

export function DashboardPage() {
  const { user } = useAuthStore()
  const { 
    trades, 
    accountStats, 
    livePositions, 
    liveAccountStats,
    liveHistory,
    fetchTrades, 
    fetchAccountStats, 
    removeDuplicateTrades 
  } = useTradingStore()
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastMarginLevel, setLastMarginLevel] = useState<number | null>(null)
  const { toast } = useToast()

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await Promise.all([fetchTrades(), fetchAccountStats()])
      setLastUpdate(new Date())
    } finally {
      setIsRefreshing(false)
    }
  }

  // Check for margin level warnings
  useEffect(() => {
    if (accountStats?.account.margin_level !== undefined) {
      const currentMarginLevel = accountStats.account.margin_level
      
      // Check if margin level dropped to 150% or below
      if (currentMarginLevel <= 150 && (lastMarginLevel === null || lastMarginLevel > 150)) {
        toast({
          title: "⚠️ MARGIN WARNING!",
          description: `Margin Level: ${currentMarginLevel.toFixed(1)}% - Consider reducing position size!`,
          variant: "destructive",
        })
      }
      
      // Check if margin level is critically low (100% or below)
      if (currentMarginLevel <= 100 && (lastMarginLevel === null || lastMarginLevel > 100)) {
        toast({
          title: "🚨 MARGIN CALL ALERT!",
          description: `Margin Level: ${currentMarginLevel.toFixed(1)}% - Risk of position closure!`,
          variant: "destructive",
        })
      }
      
      // Check if margin level is extremely critical (50% or below)
      if (currentMarginLevel <= 50 && (lastMarginLevel === null || lastMarginLevel > 50)) {
        toast({
          title: "🚨 CRITICAL MARGIN LEVEL!",
          description: `Margin Level: ${currentMarginLevel.toFixed(1)}% - Immediate action required!`,
          variant: "destructive",
        })
      }
      
      setLastMarginLevel(currentMarginLevel)
    }
  }, [accountStats?.account.margin_level, lastMarginLevel, toast])

  useEffect(() => {
    handleRefresh()
    
    // Set up periodic refresh every 3 seconds for real-time updates
    const interval = setInterval(async () => {
      await Promise.all([fetchTrades(), fetchAccountStats()])
      setLastUpdate(new Date())
    }, 2000)
    
    return () => clearInterval(interval)
  }, [fetchTrades])

  if (!user) return null

  // Calculate live profits from EA data FIRST, then fallback to database
  const liveFloatingProfit = livePositions.length > 0 
    ? livePositions.reduce((sum, pos) => sum + (pos.profit || 0), 0)
    : 0 // Zero when no live positions

  // SIMPLE SOLUTION: Database for closed, EA for open
  const liveOpenTrades = livePositions.length                    // EA: Real-time open trades
  const dbClosedTrades = trades.filter(t => !t.is_open).length   // DB: Stable closed count
  const totalTrades = liveOpenTrades + dbClosedTrades            // Combined count

  // Use stable database count for closed trades
  const actualClosedTrades = dbClosedTrades

  const totalProfit = accountStats?.trading.total_profit ?? trades.reduce((sum, trade) => sum + trade.profit, 0)
  const historicalProfit = liveHistory.length > 0 
    ? liveHistory.reduce((sum, hist) => sum + (hist.profit || 0), 0)
    : (accountStats?.trading.historical_profit ?? trades.filter(t => !t.is_open).reduce((sum, trade) => sum + trade.profit, 0))
  const floatingProfit = livePositions.length > 0 
    ? liveFloatingProfit 
    : 0 // Zero when no live positions

  // Calculate win rate: Database for closed, EA for open
  const dbClosedWinningTrades = trades.filter(t => !t.is_open && t.profit > 0).length
  const liveWinningTrades = livePositions.filter(pos => (pos.profit || 0) > 0).length
  const totalWinningTrades = dbClosedWinningTrades + liveWinningTrades
  const winRate = totalTrades > 0 ? (totalWinningTrades / totalTrades) * 100 : 0
  // const progressToNextLevel = getProgressToNextLevel(user.xp_points, user.level) // TODO: Use for level progress

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome back, {user.username}! Here's your trading overview.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-sm text-muted-foreground">
            Last update: {lastUpdate.toLocaleTimeString()}
          </div>
                            <Button onClick={handleRefresh} variant="outline" size="sm" disabled={isRefreshing}>
                    <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                    {isRefreshing ? 'Refreshing...' : 'Refresh Trades'}
                  </Button>
                  <Button onClick={removeDuplicateTrades} variant="outline" size="sm">
                    Remove Duplicates
                  </Button>
        </div>
      </div>

      {/* Account Overview Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Balance</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(liveAccountStats?.balance ?? accountStats?.account.balance ?? 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              {liveAccountStats ? '🚀 Live' : (accountStats?.account.currency ?? 'USD')} Account Balance
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Equity</CardTitle>
            <PieChart className={`h-4 w-4 ${(liveAccountStats?.margin_level ?? accountStats?.account.margin_level ?? 0) <= 150 ? 'text-red-500' : 'text-muted-foreground'}`} />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(liveAccountStats?.margin_level ?? accountStats?.account.margin_level ?? 0) <= 150 ? 'text-red-600' : ''}`}>
              {formatCurrency(liveAccountStats?.equity ?? accountStats?.account.equity ?? 0)}
            </div>
            <p className={`text-xs ${(liveAccountStats?.margin_level ?? accountStats?.account.margin_level ?? 0) <= 150 ? 'text-red-500' : 'text-muted-foreground'}`}>
              {liveAccountStats ? '🚀 Live Equity' : ((accountStats?.account.margin_level ?? 0) <= 150 ? 'EQUITY AT RISK!' : 'Current Account Equity')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Free Margin</CardTitle>
            <Calculator className={`h-4 w-4 ${(accountStats?.account.margin_level ?? 0) <= 150 ? 'text-red-500' : 'text-muted-foreground'}`} />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(liveAccountStats?.margin_level ?? accountStats?.account.margin_level ?? 0) <= 150 ? 'text-red-600' : ''}`}>
              {formatCurrency(liveAccountStats?.free_margin ?? accountStats?.account.free_margin ?? 0)}
            </div>
            <p className={`text-xs ${(liveAccountStats?.margin_level ?? accountStats?.account.margin_level ?? 0) <= 150 ? 'text-red-500' : 'text-muted-foreground'}`}>
              {liveAccountStats ? '🚀 Live Free Margin' : ((liveAccountStats?.margin_level ?? accountStats?.account.margin_level ?? 0) <= 150 ? 'LOW FREE MARGIN!' : 'Available for Trading')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Margin Level</CardTitle>
            <Target className={`h-4 w-4 ${(accountStats?.account.margin_level ?? 0) <= 150 ? 'text-red-500' : 'text-muted-foreground'}`} />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(liveAccountStats?.margin_level ?? accountStats?.account.margin_level ?? 0) <= 150 ? 'text-red-600' : ''}`}>
              {(liveAccountStats?.margin_level ?? accountStats?.account.margin_level ?? 0).toFixed(1)}%
            </div>
            <p className={`text-xs ${(liveAccountStats?.margin_level ?? accountStats?.account.margin_level ?? 0) <= 150 ? 'text-red-500' : 'text-muted-foreground'}`}>
              {liveAccountStats ? '🚀 Live Margin Level' : ((liveAccountStats?.margin_level ?? accountStats?.account.margin_level ?? 0) <= 150 ? 'MARGIN WARNING!' : 'Current Margin Level')}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Trading Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Unrealized P&L</CardTitle>
            <TrendingUp className={`h-4 w-4 ${liveFloatingProfit !== null ? 'text-green-500' : 'text-muted-foreground'}`} />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${floatingProfit >= 0 ? 'profit-text' : 'loss-text'}`}>
              {formatCurrency(floatingProfit)}
            </div>
            <p className="text-xs text-muted-foreground">
              {livePositions.length > 0 ? '🚀 Live from EA' : 'No open positions'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Realized P&L</CardTitle>
            <Trophy className={`h-4 w-4 ${liveHistory.length > 0 ? 'text-green-500' : 'text-muted-foreground'}`} />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${historicalProfit >= 0 ? 'profit-text' : 'loss-text'}`}>
              {formatCurrency(historicalProfit)}
            </div>
            <p className="text-xs text-muted-foreground">
              {liveHistory.length > 0 ? '🚀 Live from EA history' : 'From closed trades'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${totalProfit >= 0 ? 'profit-text' : 'loss-text'}`}>
              {formatCurrency(totalProfit)}
            </div>
            <p className="text-xs text-muted-foreground">
              Realized + Unrealized
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
            <Target className={`h-4 w-4 ${liveOpenTrades > 0 ? 'text-green-500' : 'text-muted-foreground'}`} />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{winRate.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              {actualClosedTrades} closed (DB), {liveOpenTrades} live (EA)
              {liveOpenTrades > 0 && ' 🚀'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Live Trades</CardTitle>
            <Zap className={`h-4 w-4 ${livePositions.length > 0 ? 'text-green-500' : 'text-gray-400'}`} />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {livePositions.length}
            </div>
            <p className="text-xs text-muted-foreground">
              {livePositions.length > 0 ? 'Live from EA' : 'No open positions'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Trades */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Trades</CardTitle>
            <CardDescription>Your latest trading activity</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* LIVE POSITIONS from EA - Real-time data */}
              {livePositions.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-green-600 uppercase tracking-wide">🚀 Live from EA</p>
                  {livePositions.slice(0, 3).map((pos, index) => (
                    <div key={`live-${pos.ticket}-${index}`} className="flex items-center justify-between border-l-2 border-green-500 pl-3">
                      <div className="flex items-center space-x-3">
                        <div className={`w-2 h-2 rounded-full ${pos.type === 0 ? 'bg-green-500' : 'bg-red-500'}`} />
                        <div>
                          <p className="text-sm font-medium">{pos.symbol}</p>
                          <p className="text-xs text-muted-foreground">
                            {pos.type === 0 ? 'BUY' : 'SELL'} {pos.volume} lots
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className={`text-sm font-medium ${pos.profit >= 0 ? 'profit-text' : 'loss-text'}`}>
                          {formatCurrency(pos.profit)}
                        </p>
                        <Badge variant="secondary" className="bg-green-100 text-green-700">
                          LIVE
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Database trades - Historical/fallback */}
              {trades.slice(0, livePositions.length > 0 ? 2 : 5).map((trade, index) => (
                <div key={`db-${trade.id}-${trade.ticket}-${index}`} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className={`w-2 h-2 rounded-full ${trade.trade_type === 'BUY' ? 'bg-green-500' : 'bg-red-500'}`} />
                    <div>
                      <p className="text-sm font-medium">{trade.symbol}</p>
                      <p className="text-xs text-muted-foreground">
                        {trade.trade_type} {trade.volume} lots
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`text-sm font-medium ${trade.profit >= 0 ? 'profit-text' : 'loss-text'}`}>
                      {formatCurrency(trade.profit)}
                    </p>
                    <Badge variant={trade.is_open ? "secondary" : "outline"}>
                      {trade.is_open ? "Open" : "Closed"}
                    </Badge>
                  </div>
                </div>
              ))}

              {trades.length === 0 && livePositions.length === 0 && (
                <p className="text-center text-muted-foreground py-4">
                  No trades yet. Connect your MT4/MT5 to start trading.
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Achievements */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Achievements</CardTitle>
            <CardDescription>Your latest badges and milestones</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {user.badges?.slice(0, 5).map((badge, index) => (
                <div key={index} className="flex items-center space-x-3">
                  <div className="text-2xl">{badge.icon}</div>
                  <div>
                    <p className="text-sm font-medium">{badge.name}</p>
                    <p className="text-xs text-muted-foreground">
                      Earned {new Date(badge.earned_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              )) || (
                <p className="text-center text-muted-foreground py-4">
                  No badges earned yet. Start trading to unlock achievements!
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Get started with copy trading</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Button variant="outline" className="flex items-center space-x-2">
              <Users className="h-4 w-4" />
              <span>Browse Traders</span>
            </Button>
            <Button variant="outline" className="flex items-center space-x-2">
              <Trophy className="h-4 w-4" />
              <span>View Leaderboard</span>
            </Button>
            <Button variant="outline" className="flex items-center space-x-2">
              <Target className="h-4 w-4" />
              <span>Generate Report</span>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
} 