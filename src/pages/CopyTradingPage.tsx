// @ts-ignore
import React, { useEffect, useState } from 'react'
import { useAuthStore } from '../stores/authStore'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Progress } from '../components/ui/progress'
import { 
  Copy, 
  Users, 
  TrendingUp, 
  TrendingDown, 
  Settings, 
  Activity, 
  BarChart3, 
  CheckCircle, 
  XCircle, 
  Clock,
  AlertTriangle,
  Wifi,
  WifiOff
} from 'lucide-react'
import { formatCurrency } from '../lib/utils'
import { toast } from '../hooks/use-toast'
import { api } from '../lib/api'

interface FollowingTrader {
  follow_id: number
  master_trader: {
    id: number
    username: string
    is_online: boolean
  }
  follow_settings: {
    copy_percentage: number
    max_risk_per_trade: number
  }
  statistics: {
    total_copies: number
    successful_copies: number
    success_rate: number
    total_profit: number
  }
  created_at: string
}

interface CopyTrade {
  id: number
  master_trader: string
  master_ticket: string
  follower_ticket: string
  symbol: string
  trade_type: string
  original_volume: number
  copied_volume: number
  copy_ratio: number
  status: string
  created_at: string
  executed_at: string
  closed_at: string
  error_message: string
}

export function CopyTradingPage() {
  const { user } = useAuthStore()
  const [following, setFollowing] = useState<FollowingTrader[]>([])
  const [copyTrades, setCopyTrades] = useState<CopyTrade[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'following' | 'history'>('following')

  useEffect(() => {
    if (user) {
      fetchCopyTradingData()
    }
  }, [user])

  const fetchCopyTradingData = async () => {
    setIsLoading(true)
    try {
      const [followingResponse, historyResponse] = await Promise.all([
        api.get('/api/copy-trading/following'),
        api.get('/api/copy-trading/copy-trades')
      ])
      
      setFollowing(followingResponse.data.following || [])
      setCopyTrades(historyResponse.data.copy_trades || [])
    } catch (error) {
      console.error('Error fetching copy trading data:', error)
      toast({
        title: "Error",
        description: "Failed to load copy trading data",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'executed':
      case 'closed':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />
      case 'pending':
        return <Clock className="w-4 h-4 text-yellow-500" />
      default:
        return <AlertTriangle className="w-4 h-4 text-orange-500" />
    }
  }

  const getStatusBadge = (status: string) => {
    const variants = {
      executed: 'bg-green-100 text-green-800 border-green-300',
      closed: 'bg-blue-100 text-blue-800 border-blue-300',
      failed: 'bg-red-100 text-red-800 border-red-300',
      pending: 'bg-yellow-100 text-yellow-800 border-yellow-300'
    }
    
    return (
      <Badge 
        variant="outline" 
        className={variants[status as keyof typeof variants] || 'bg-gray-100 text-gray-800 border-gray-300'}
      >
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    )
  }

  if (!user) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent className="pt-6 text-center">
            <p>Please log in to access copy trading features.</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
            Copy Trading Dashboard
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage your copy trading activities and view performance
          </p>
        </div>
        
        <Button onClick={fetchCopyTradingData} disabled={isLoading}>
          <Activity className="w-4 h-4 mr-2" />
          {isLoading ? 'Refreshing...' : 'Refresh'}
        </Button>
      </div>

      {/* Tab Navigation */}
      <div className="flex space-x-4 border-b">
        <button
          onClick={() => setActiveTab('following')}
          className={`pb-2 px-1 border-b-2 font-medium transition-colors ${
            activeTab === 'following'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Users className="w-4 h-4 inline mr-2" />
          Following ({following.length})
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`pb-2 px-1 border-b-2 font-medium transition-colors ${
            activeTab === 'history'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <BarChart3 className="w-4 h-4 inline mr-2" />
          Copy History ({copyTrades.length})
        </button>
      </div>

      {/* Following Tab */}
      {activeTab === 'following' && (
        <div className="space-y-4">
          {isLoading ? (
            <Card>
              <CardContent className="pt-6 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
                <p>Loading your followed traders...</p>
              </CardContent>
            </Card>
          ) : following.length === 0 ? (
            <Card>
              <CardContent className="pt-6 text-center">
                <Copy className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">No Traders Followed</h3>
                <p className="text-muted-foreground mb-4">
                  Start copy trading by following master traders in the marketplace
                </p>
                <Button onClick={() => window.location.href = '/marketplace'}>
                  Browse Master Traders
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {following.map((follow) => (
                <Card key={follow.follow_id} className="relative group hover:shadow-lg transition-all duration-300">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg flex items-center gap-2">
                        {follow.master_trader.is_online ? (
                          <Wifi className="w-4 h-4 text-green-500" />
                        ) : (
                          <WifiOff className="w-4 h-4 text-gray-400" />
                        )}
                        {follow.master_trader.username}
                      </CardTitle>
                      <Badge variant="outline" className={follow.master_trader.is_online ? 'border-green-500 text-green-600' : ''}>
                        {follow.master_trader.is_online ? 'Online' : 'Offline'}
                      </Badge>
                    </div>
                  </CardHeader>
                  
                  <CardContent className="space-y-4">
                    {/* Copy Settings */}
                    <div className="bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <Settings className="w-4 h-4 text-blue-600" />
                        <span className="text-sm font-semibold text-blue-700 dark:text-blue-300">
                          Copy Settings
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div>
                          <span className="text-muted-foreground">Copy Percentage:</span>
                          <div className="font-semibold">{follow.follow_settings.copy_percentage}%</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Max Risk:</span>
                          <div className="font-semibold">{follow.follow_settings.max_risk_per_trade}%</div>
                        </div>
                      </div>
                    </div>

                    {/* Performance Stats */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="text-center p-3 bg-gradient-to-b from-background to-muted/30 rounded-lg border">
                        <div className="text-sm text-muted-foreground">Total Copies</div>
                        <div className="text-lg font-bold">{follow.statistics.total_copies}</div>
                      </div>
                      <div className="text-center p-3 bg-gradient-to-b from-background to-muted/30 rounded-lg border">
                        <div className="text-sm text-muted-foreground">Success Rate</div>
                        <div className="text-lg font-bold text-green-600">{follow.statistics.success_rate.toFixed(0)}%</div>
                      </div>
                    </div>

                    {/* Profit Display */}
                    <div className="text-center p-3 bg-gradient-to-r from-slate-900/50 to-slate-800/50 rounded-xl border border-slate-700/50">
                      <div className="text-sm text-slate-400 mb-1">Total Profit from Copying</div>
                      <div className={`text-xl font-bold ${follow.statistics.total_profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {follow.statistics.total_profit >= 0 ? (
                          <TrendingUp className="w-4 h-4 inline mr-1" />
                        ) : (
                          <TrendingDown className="w-4 h-4 inline mr-1" />
                        )}
                        {formatCurrency(follow.statistics.total_profit)}
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" className="flex-1">
                        <Settings className="w-3 h-3 mr-1" />
                        Settings
                      </Button>
                      <Button size="sm" variant="outline" className="flex-1">
                        <BarChart3 className="w-3 h-3 mr-1" />
                        History
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Copy History Tab */}
      {activeTab === 'history' && (
        <div className="space-y-4">
          {isLoading ? (
            <Card>
              <CardContent className="pt-6 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
                <p>Loading copy trade history...</p>
              </CardContent>
            </Card>
          ) : copyTrades.length === 0 ? (
            <Card>
              <CardContent className="pt-6 text-center">
                <BarChart3 className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">No Copy Trades Yet</h3>
                <p className="text-muted-foreground">
                  Your copy trade history will appear here once you start following traders
                </p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Copy Trade History</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {copyTrades.map((trade) => (
                    <div key={trade.id} className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors">
                      <div className="flex items-center gap-4">
                        {getStatusIcon(trade.status)}
                        <div>
                          <div className="font-semibold">{trade.symbol}</div>
                          <div className="text-sm text-muted-foreground">
                            From {trade.master_trader} • {trade.trade_type.toUpperCase()}
                          </div>
                        </div>
                      </div>
                      
                      <div className="text-right">
                        <div className="font-semibold">{trade.copied_volume} lots</div>
                        <div className="text-sm text-muted-foreground">
                          {new Date(trade.created_at).toLocaleDateString()}
                        </div>
                      </div>
                      
                      <div className="text-right">
                        {getStatusBadge(trade.status)}
                        {trade.follower_ticket && (
                          <div className="text-xs text-muted-foreground mt-1">
                            #{trade.follower_ticket}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}

export default CopyTradingPage
