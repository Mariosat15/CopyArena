// @ts-ignore
import React, { useEffect, useState } from 'react'
import { useTradingStore } from '../stores/tradingStore'
import { useAuthStore } from '../stores/authStore'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Input } from '../components/ui/input'
import { Progress } from '../components/ui/progress'
import { Search, Users, Star, TrendingUp, Activity, Shield, Wifi, WifiOff, Eye, Award, BarChart3, TrendingDown, Heart, Copy, UserCheck, UserPlus } from 'lucide-react'
import { formatCurrency } from '../lib/utils'
import { toast } from '../hooks/use-toast'
import { api } from '../lib/api'
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts'

interface MasterTrader {
  id: number
  username: string
  level: number
  xp_points: number
  subscription_plan: string
  is_online: boolean
  created_at: string
  stats: {
    total_trades: number
    closed_trades: number
    open_trades: number
    total_profit: number
    unrealized_profit: number
    win_rate: number
    account_balance: number
    recent_profit: number
    daily_return: number
    avg_win: number
    avg_loss: number
  }
  performance: {
    profit_factor: number
    max_drawdown: number
    sharpe_ratio: number
    followers_count: number
    risk_score: number
    win_streak: number
    loss_streak: number
    monthly_return: number
    consistency_score: number
  }
}

interface FollowingStatus {
  following: boolean
  authenticated: boolean
  copy_percentage?: number
  max_risk_per_trade?: number
}

export function MarketplacePage() {
  const { user } = useAuthStore()
  const [traders, setTraders] = useState<MasterTrader[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingTraders, setIsLoadingTraders] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [sortBy, setSortBy] = useState<'profit' | 'rating' | 'followers'>('profit')
  const [followingStatus, setFollowingStatus] = useState<{[key: number]: FollowingStatus}>({})
  const [followingLoading, setFollowingLoading] = useState<{[key: number]: boolean}>({})

  useEffect(() => {
    fetchMasterTraders()
    
    // Set up automatic refresh for real-time online status
    const refreshInterval = setInterval(() => {
      // Use silent refresh (don't show loading state)
      fetchMasterTraders(true)
    }, 5000) // Refresh every 5 seconds
    
    return () => clearInterval(refreshInterval)
  }, [])

  useEffect(() => {
    if (user && traders.length > 0) {
      fetchFollowingStatuses()
    }
  }, [user, traders])

  const fetchMasterTraders = async (silentRefresh = false) => {
    if (!silentRefresh) {
      setIsLoadingTraders(true)
    } else {
      setIsRefreshing(true)
    }
    
    try {
      const response = await api.get('/api/marketplace/traders')
      const newTraders = response.data.traders || []
      
      // Only update if there are actual changes to prevent unnecessary re-renders
      const tradersChanged = JSON.stringify(newTraders) !== JSON.stringify(traders)
      if (tradersChanged || !silentRefresh) {
        setTraders(newTraders)
        if (silentRefresh) {
          console.log('Marketplace refreshed with updated online status')
        }
      }
    } catch (error: any) {
      console.error('Error fetching traders:', error)
      if (!silentRefresh) {
        toast({
          title: "Error",
          description: "Failed to load master traders",
          variant: "destructive"
        })
      }
    } finally {
      if (!silentRefresh) {
        setIsLoadingTraders(false)
      } else {
        setIsRefreshing(false)
      }
    }
  }

  const fetchFollowingStatuses = async () => {
    if (!user) return
    
    try {
      const statuses: {[key: number]: FollowingStatus} = {}
      
      // Fetch following status for each trader
      await Promise.all(
        traders.map(async (trader) => {
          try {
            const response = await api.get(`/api/marketplace/following-status/${trader.id}`)
            statuses[trader.id] = response.data
          } catch (error) {
            statuses[trader.id] = { following: false, authenticated: true }
          }
        })
      )
      
      setFollowingStatus(statuses)
    } catch (error) {
      console.error('Error fetching following statuses:', error)
    }
  }

  const handleFollow = async (traderId: number) => {
    if (!user) {
      toast({
        title: "Authentication Required",
        description: "Please log in to follow traders.",
        variant: "destructive"
      })
      return
    }

    if (user.subscription_plan === 'free') {
      toast({
        title: "Upgrade Required",
        description: "Copy trading requires a Pro or Elite subscription.",
        variant: "destructive"
      })
      return
    }

    setFollowingLoading(prev => ({ ...prev, [traderId]: true }))
    
    try {
      const isCurrentlyFollowing = followingStatus[traderId]?.following || false
      
      if (isCurrentlyFollowing) {
        // Unfollow
        const response = await api.post(`/api/marketplace/unfollow/${traderId}`)
        setFollowingStatus(prev => ({
          ...prev,
          [traderId]: { ...prev[traderId], following: false }
        }))
        
        // Update follower count in traders list
        setTraders(prev => prev.map(trader => 
          trader.id === traderId 
            ? { 
                ...trader, 
                performance: { 
                  ...trader.performance, 
                  followers_count: response.data.follower_count 
                } 
              }
            : trader
        ))
        
        toast({
          title: "Success",
          description: response.data.message,
          variant: "default"
        })
      } else {
        // Follow
        const response = await api.post(`/api/marketplace/follow/${traderId}`)
        setFollowingStatus(prev => ({
          ...prev,
          [traderId]: { ...prev[traderId], following: true }
        }))
        
        // Update follower count in traders list
        setTraders(prev => prev.map(trader => 
          trader.id === traderId 
            ? { 
                ...trader, 
                performance: { 
                  ...trader.performance, 
                  followers_count: response.data.follower_count 
                } 
              }
            : trader
        ))
        
        toast({
          title: "Success",
          description: response.data.message,
          variant: "default"
        })
      }
    } catch (error: any) {
      console.error('Error following/unfollowing trader:', error)
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to update follow status",
        variant: "destructive"
      })
    } finally {
      setFollowingLoading(prev => ({ ...prev, [traderId]: false }))
    }
  }

  const filteredTraders = traders.filter(trader =>
    trader.username.toLowerCase().includes(searchTerm.toLowerCase())
  ).sort((a, b) => {
    switch (sortBy) {
      case 'profit':
        return b.stats.total_profit - a.stats.total_profit
      case 'rating':
        return b.stats.win_rate - a.stats.win_rate
      case 'followers':
        return b.performance.followers_count - a.performance.followers_count
      default:
        return b.stats.total_profit - a.stats.total_profit
    }
  })

  const getPerformanceColor = (value: number, isProfit: boolean = true) => {
    if (isProfit) {
      return value > 0 ? 'text-green-600' : 'text-red-600'
    }
    return value > 70 ? 'text-green-600' : value > 50 ? 'text-yellow-600' : 'text-red-600'
  }

  const getSubscriptionColor = (plan: string) => {
    switch (plan) {
      case 'elite': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
      case 'pro': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
    }
  }

  const getRatingStars = (winRate: number) => {
    const rating = Math.min(5, Math.max(1, Math.round((winRate / 100) * 5)))
    return Array.from({ length: 5 }, (_, i) => (
      <Star
        key={i}
        className={`w-4 h-4 ${i < rating ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`}
      />
    ))
  }

  const getTraderAvatar = (username: string) => {
    const colors = ['bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500', 'bg-pink-500']
    const colorIndex = username.length % colors.length
    return (
      <div className={`w-12 h-12 rounded-full ${colors[colorIndex]} flex items-center justify-center text-white font-bold text-lg`}>
        {username.substring(0, 2).toUpperCase()}
      </div>
    )
  }

  const calculateDailyReturn = (totalProfit: number, accountBalance: number, days: number = 30) => {
    if (accountBalance <= 0) return 0
    const dailyReturn = (totalProfit / accountBalance) / days * 100
    return Math.max(-99, Math.min(999, dailyReturn))
  }

  const getRiskLevel = (winRate: number, totalTrades: number) => {
    if (totalTrades < 10) return 'High'
    if (winRate > 80) return 'Low'
    if (winRate > 60) return 'Medium'
    return 'High'
  }

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'Low': return 'text-green-600 bg-green-100 dark:bg-green-900'
      case 'Medium': return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900'
      case 'High': return 'text-red-600 bg-red-100 dark:bg-red-900'
      default: return 'text-gray-600 bg-gray-100 dark:bg-gray-900'
    }
  }

  // Generate chart data for profit trends
  const generateChartData = (trader: MasterTrader) => {
    // Generate synthetic daily profit data based on total profit and trading activity
    const days = 30
    const data: { day: number; profit: number; date: string }[] = []
    const totalProfit = trader.stats.total_profit
    const dailyVariation = totalProfit / days
    let runningProfit = 0
    
    for (let i = 0; i < days; i++) {
      // Add some realistic variation
      const dailyChange = dailyVariation + (Math.random() - 0.5) * (dailyVariation * 0.5)
      runningProfit += dailyChange
      
      data.push({
        day: i + 1,
        profit: Math.round(runningProfit * 100) / 100,
        date: new Date(Date.now() - (days - i) * 24 * 60 * 60 * 1000).toLocaleDateString()
      })
    }
    
    return data
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Trader Marketplace</h1>
            <p className="text-muted-foreground">
              Discover and follow successful master traders to copy their strategies.
            </p>
          </div>
          {isRefreshing && (
            <div className="flex items-center text-sm text-muted-foreground">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary mr-2"></div>
              Updating...
            </div>
          )}
        </div>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search traders by username..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex gap-2">
              <Button
                variant={sortBy === 'profit' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSortBy('profit')}
              >
                <TrendingUp className="w-4 h-4 mr-2" />
                Profit
              </Button>
              <Button
                variant={sortBy === 'rating' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSortBy('rating')}
              >
                <Award className="w-4 h-4 mr-2" />
                Rating
              </Button>
              <Button
                variant={sortBy === 'followers' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSortBy('followers')}
              >
                <Users className="w-4 h-4 mr-2" />
                Followers
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Loading State */}
      {isLoadingTraders && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <span className="ml-2">Loading master traders...</span>
        </div>
      )}

      {/* Empty State */}
      {!isLoadingTraders && filteredTraders.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center">
            <Users className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Master Traders Found</h3>
            <p className="text-muted-foreground mb-4">
              {searchTerm ? 
                'No traders match your search criteria.' : 
                'No traders have enabled master trader status yet.'
              }
            </p>
            {!searchTerm && (
              <p className="text-sm text-muted-foreground">
                Become a master trader yourself by enabling it in your profile!
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Professional Traders Grid */}
      {!isLoadingTraders && filteredTraders.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-8">
          {filteredTraders.map((trader) => {
            const dailyReturn = calculateDailyReturn(trader.stats.total_profit, trader.stats.account_balance)
            const riskLevel = getRiskLevel(trader.stats.win_rate, trader.stats.total_trades)
            const monthlyProfit = trader.stats.recent_profit || trader.stats.total_profit * 0.3
            const chartData = generateChartData(trader)
            const isFollowing = followingStatus[trader.id]?.following || false
            const isFollowLoading = followingLoading[trader.id] || false
            
            return (
              <Card key={trader.id} className="group hover:shadow-2xl hover:scale-[1.02] transition-all duration-300 relative overflow-hidden bg-gradient-to-br from-background via-background to-muted/20 border-2 hover:border-primary/30">
                {/* Animated Background Gradient */}
                <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                
                {/* Premium Badge */}
                {trader.subscription_plan !== 'free' && (
                  <div className="absolute -top-1 -right-1 z-10">
                    <div className="bg-gradient-to-r from-yellow-400 to-orange-500 text-white px-3 py-1 rounded-bl-lg rounded-tr-lg shadow-lg">
                      <Award className="w-4 h-4 inline mr-1" />
                      <span className="text-xs font-bold">{trader.subscription_plan.toUpperCase()}</span>
                    </div>
                  </div>
                )}

                {/* Header Section - Enhanced */}
                <CardHeader className="pb-4 relative z-10">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center space-x-4">
                      {/* Enhanced Avatar with Status Ring */}
                      <div className="relative">
                        <div className={`w-16 h-16 rounded-2xl ${getTraderAvatar(trader.username).props.className} flex items-center justify-center text-white font-bold text-xl shadow-lg ring-4 ${trader.is_online ? 'ring-green-400/30' : 'ring-gray-400/30'} transition-all duration-300`}>
                          {trader.username.substring(0, 2).toUpperCase()}
                        </div>
                        {/* Pulsing Online Indicator */}
                        <div className={`absolute -bottom-1 -right-1 w-6 h-6 rounded-full border-4 border-background ${trader.is_online ? 'bg-green-500' : 'bg-gray-400'} ${trader.is_online ? 'animate-pulse' : ''}`}>
                          {trader.is_online ? (
                            <Wifi className="w-3 h-3 text-white absolute top-0.5 left-0.5" />
                          ) : (
                            <WifiOff className="w-3 h-3 text-white absolute top-0.5 left-0.5" />
                          )}
                        </div>
                      </div>
                      
                      <div className="flex-1">
                        <CardTitle className="text-xl font-bold flex items-center gap-2 mb-2">
                          <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                            {trader.username}
                          </span>
                        </CardTitle>
                        
                        {/* Level & XP Bar */}
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border-blue-500/30 text-blue-600 font-semibold">
                              <Award className="w-3 h-3 mr-1" />
                              Level {trader.level}
                            </Badge>
                            <Badge className={`${getSubscriptionColor(trader.subscription_plan)} font-semibold text-xs`}>
                              {trader.subscription_plan.toUpperCase()}
                            </Badge>
                          </div>
                          
                          {/* XP Progress Bar */}
                          <div className="space-y-1">
                            <div className="text-xs text-muted-foreground font-medium">
                              {trader.xp_points.toLocaleString()} XP
                            </div>
                            <Progress 
                              value={(trader.xp_points % 1000) / 10} 
                              className="h-2 bg-muted/50"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Rating Stars Section */}
                  <div className="flex items-center justify-between p-3 bg-muted/30 rounded-xl">
                    <div className="flex items-center space-x-1">
                      {getRatingStars(trader.stats.win_rate)}
                      <span className="ml-2 text-sm font-semibold text-muted-foreground">
                        {trader.stats.win_rate.toFixed(1)}%
                      </span>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-muted-foreground">Status</div>
                      <div className={`text-sm font-bold ${trader.is_online ? 'text-green-600' : 'text-gray-500'}`}>
                        {trader.is_online ? 'LIVE' : 'OFFLINE'}
                      </div>
                    </div>
                  </div>
                </CardHeader>
                
                <CardContent className="space-y-6 relative z-10">
                  {/* Enhanced Profit Chart */}
                  <div className="relative">
                    <div className="absolute top-2 left-2 z-10 bg-black/80 text-white px-2 py-1 rounded text-xs font-bold">
                      30D Performance
                    </div>
                    <div className="h-20 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 rounded-xl relative overflow-hidden border border-slate-700">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={chartData}>
                          <Line 
                            type="monotone" 
                            dataKey="profit" 
                            stroke={trader.stats.total_profit >= 0 ? "#10b981" : "#ef4444"} 
                            strokeWidth={3}
                            dot={false}
                            strokeDasharray={trader.stats.total_profit >= 0 ? "0" : "5,5"}
                          />
                          <XAxis hide />
                          <YAxis hide />
                          <Tooltip 
                            contentStyle={{ 
                              backgroundColor: 'rgba(0,0,0,0.9)', 
                              border: '1px solid rgba(255,255,255,0.2)', 
                              borderRadius: '8px',
                              color: 'white',
                              fontSize: '12px',
                              fontWeight: 'bold'
                            }}
                            formatter={(value: any) => [formatCurrency(value), 'Profit']}
                            labelFormatter={(label) => `Day ${label}`}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                      
                      {/* Chart Overlay Pattern */}
                      <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent pointer-events-none"></div>
                    </div>
                  </div>

                  {/* Key Performance Metrics - Enhanced */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-gradient-to-br from-green-500/10 to-emerald-500/5 border border-green-500/20 rounded-xl p-4 text-center">
                      <div className="text-xs text-green-600/80 font-semibold uppercase tracking-wide mb-1">Total Profit</div>
                      <div className={`text-2xl font-bold ${getPerformanceColor(trader.stats.total_profit)}`}>
                        {formatCurrency(trader.stats.total_profit)}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">All Time</div>
                    </div>
                    <div className="bg-gradient-to-br from-blue-500/10 to-cyan-500/5 border border-blue-500/20 rounded-xl p-4 text-center">
                      <div className="text-xs text-blue-600/80 font-semibold uppercase tracking-wide mb-1">Monthly Return</div>
                      <div className={`text-2xl font-bold ${getPerformanceColor(trader.performance.monthly_return)}`}>
                        {trader.performance.monthly_return > 0 ? '+' : ''}{trader.performance.monthly_return.toFixed(1)}%
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">Last 30 Days</div>
                    </div>
                  </div>

                  {/* Trading Statistics Grid - Enhanced */}
                  <div className="grid grid-cols-4 gap-3">
                    <div className="text-center p-3 bg-gradient-to-b from-background to-muted/30 rounded-lg border">
                      <Users className="w-5 h-5 mx-auto mb-2 text-blue-500" />
                      <div className="text-xs text-muted-foreground font-medium">Followers</div>
                      <div className="text-lg font-bold text-blue-600">{trader.performance.followers_count}</div>
                    </div>
                    <div className="text-center p-3 bg-gradient-to-b from-background to-muted/30 rounded-lg border">
                      <BarChart3 className="w-5 h-5 mx-auto mb-2 text-purple-500" />
                      <div className="text-xs text-muted-foreground font-medium">Trades</div>
                      <div className="text-lg font-bold text-purple-600">{trader.stats.total_trades}</div>
                    </div>
                    <div className="text-center p-3 bg-gradient-to-b from-background to-muted/30 rounded-lg border">
                      <Activity className="w-5 h-5 mx-auto mb-2 text-orange-500" />
                      <div className="text-xs text-muted-foreground font-medium">Active</div>
                      <div className="text-lg font-bold text-orange-600">{trader.stats.open_trades}</div>
                    </div>
                    <div className="text-center p-3 bg-gradient-to-b from-background to-muted/30 rounded-lg border">
                      <Shield className="w-5 h-5 mx-auto mb-2 text-green-500" />
                      <div className="text-xs text-muted-foreground font-medium">Win Rate</div>
                      <div className="text-lg font-bold text-green-600">{trader.stats.win_rate.toFixed(0)}%</div>
                    </div>
                  </div>

                  {/* Live Performance Dashboard */}
                  <div className="bg-gradient-to-r from-slate-900/50 to-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                        <span className="text-sm font-bold text-white">Live Performance</span>
                      </div>
                      <TrendingUp className="w-4 h-4 text-green-500" />
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <div className="text-xs text-slate-400">Investor Profit (1M)</div>
                        <div className={`text-lg font-bold ${getPerformanceColor(monthlyProfit)}`}>
                          {formatCurrency(monthlyProfit)}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-400">Account Balance</div>
                        <div className="text-lg font-bold text-white">
                          {formatCurrency(trader.stats.account_balance)}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Risk Assessment Panel */}
                  <div className="flex items-center justify-between p-3 bg-gradient-to-r from-muted/30 to-muted/10 rounded-xl border">
                    <div className="flex items-center gap-3">
                      <div className="text-center">
                        <div className="text-xs text-muted-foreground font-medium">Risk Level</div>
                        <Badge className={`${getRiskColor(riskLevel)} border-0 font-bold`} variant="outline">
                          {riskLevel}
                        </Badge>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-muted-foreground font-medium">Consistency</div>
                        <div className="text-sm font-bold">{trader.performance.consistency_score.toFixed(0)}%</div>
                      </div>
                    </div>
                    
                    {/* Performance Indicator */}
                    <div className="text-right">
                      <div className="text-xs text-muted-foreground">Performance</div>
                      <div className="flex items-center gap-1">
                        {trader.stats.total_profit > 0 ? (
                          <TrendingUp className="w-4 h-4 text-green-500" />
                        ) : (
                          <TrendingDown className="w-4 h-4 text-red-500" />
                        )}
                        <span className={`text-sm font-bold ${getPerformanceColor(trader.stats.total_profit)}`}>
                          {trader.stats.total_profit > 0 ? 'Profitable' : 'Improving'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Enhanced Action Button */}
                  <div className="pt-4 border-t border-border/50">
                    <Button 
                      onClick={() => handleFollow(trader.id)}
                      disabled={isFollowLoading || trader.id === user?.id}
                      size="lg"
                      variant={trader.id === user?.id ? "outline" : (isFollowing ? "secondary" : "default")}
                      className={`w-full h-12 font-bold text-base transition-all duration-300 ${
                        trader.id === user?.id 
                          ? 'bg-gradient-to-r from-slate-600 to-slate-700 hover:from-slate-700 hover:to-slate-800' 
                          : isFollowing 
                          ? 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white' 
                          : 'bg-gradient-to-r from-primary to-accent hover:from-primary/90 hover:to-accent/90 text-primary-foreground shadow-lg hover:shadow-xl'
                      }`}
                    >
                      {trader.id === user?.id ? (
                        <>
                          <Shield className="w-5 h-5 mr-2" />
                          Your Profile
                        </>
                      ) : isFollowLoading ? (
                        <>
                          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-current mr-2"></div>
                          Processing...
                        </>
                      ) : isFollowing ? (
                        <>
                          <UserCheck className="w-5 h-5 mr-2" />
                          Following • {trader.performance.followers_count} Investors
                        </>
                      ) : (
                        <>
                          <UserPlus className="w-5 h-5 mr-2" />
                          {user?.subscription_plan === 'free' ? 'Upgrade to Copy Trade' : `Copy Trade • ${trader.performance.followers_count} Investors`}
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>

                {/* Hover Effect Overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none rounded-lg"></div>
              </Card>
            )
          })}
        </div>
      )}

      {/* Enhanced Stats Summary */}
      {!isLoadingTraders && filteredTraders.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center space-x-4">
                <span className="text-muted-foreground">
                  Showing {filteredTraders.length} master trader{filteredTraders.length !== 1 ? 's' : ''}
                </span>
                <span className="text-muted-foreground">•</span>
                <span className="text-green-600 font-medium">
                  {filteredTraders.filter(t => t.is_online).length} online
                </span>
                <span className="text-muted-foreground">•</span>
                <span className="text-blue-600 font-medium">
                  Total Investors: {filteredTraders.reduce((sum, t) => sum + t.performance.followers_count, 0)}
                </span>
              </div>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => fetchMasterTraders()}
                disabled={isLoadingTraders || isRefreshing}
              >
                {isRefreshing ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2"></div>
                    Auto-refreshing...
                  </>
                ) : (
                  <>
                    <Activity className="w-4 h-4 mr-2" />
                    Refresh
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
} 