import React, { useEffect, useState } from 'react'
import { useAuthStore } from '../stores/authStore'
import { useTradingStore } from '../stores/tradingStore'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { TrendingUp, TrendingDown, Users, Trophy, Target, Zap, RefreshCw, Activity } from 'lucide-react'
import { formatCurrency, formatPercentage, getProgressToNextLevel } from '../lib/utils'

export function DashboardPage() {
  const { user } = useAuthStore()
  const { trades, fetchTrades } = useTradingStore()
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const [isRefreshing, setIsRefreshing] = useState(false)

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await fetchTrades()
      setLastUpdate(new Date())
    } finally {
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    handleRefresh()
    
    // Set up periodic refresh every 30 seconds
    const interval = setInterval(async () => {
      await fetchTrades()
      setLastUpdate(new Date())
    }, 30000)
    
    return () => clearInterval(interval)
  }, [fetchTrades])

  if (!user) return null

  const totalProfit = trades.reduce((sum, trade) => sum + trade.profit, 0)
  const profitableTrades = trades.filter(trade => trade.profit > 0).length
  const winRate = trades.length > 0 ? (profitableTrades / trades.length) * 100 : 0
  const progressToNextLevel = getProgressToNextLevel(user.xp_points, user.level)

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
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Profit</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${totalProfit >= 0 ? 'profit-text' : 'loss-text'}`}>
              {formatCurrency(totalProfit)}
            </div>
            <p className="text-xs text-muted-foreground">
              From {trades.length} trades
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{winRate.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              {profitableTrades} winning trades
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">XP Points</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{user.xp_points.toLocaleString()}</div>
            <div className="text-xs text-muted-foreground">
              Level {user.level} • {progressToNextLevel.toFixed(0)}% to next level
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Followers</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{user.stats?.followers_count || 0}</div>
            <p className="text-xs text-muted-foreground">
              People copying your trades
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Live Status</CardTitle>
            <Activity className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">Active</div>
            <p className="text-xs text-muted-foreground">
              Auto-sync every 30s
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
              {trades.slice(0, 5).map((trade) => (
                <div key={trade.id} className="flex items-center justify-between">
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
              {trades.length === 0 && (
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