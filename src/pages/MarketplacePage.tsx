// @ts-ignore
import React, { useEffect, useState } from 'react'
import { useTradingStore } from '../stores/tradingStore'
import { useAuthStore } from '../stores/authStore'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Input } from '../components/ui/input'
import { Search, Users, Star } from 'lucide-react'
import { formatCurrency } from '../lib/utils'
import { toast } from '../hooks/use-toast'

export function MarketplacePage() {
  const { user } = useAuthStore()
  const { traders, fetchTraders, followTrader, unfollowTrader, follows } = useTradingStore()
  const [searchTerm, setSearchTerm] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    fetchTraders()
  }, [fetchTraders])

  const filteredTraders = traders.filter(trader =>
    trader.username.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleFollow = async (traderId: number) => {
    if (user?.subscription_plan === 'free') {
      toast({
        title: "Upgrade Required",
        description: "Copy trading requires a Pro or Elite subscription.",
        variant: "destructive"
      })
      return
    }

    setIsLoading(true)
    try {
      await followTrader(traderId, {
        auto_copy: false,
        max_trade_size: 0.01,
        risk_level: 1.0
      })
      toast({
        title: "Success",
        description: "You are now following this trader.",
      })
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleUnfollow = async (traderId: number) => {
    setIsLoading(true)
    try {
      await unfollowTrader(traderId)
      toast({
        title: "Success",
        description: "You have unfollowed this trader.",
      })
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }

  const isFollowing = (traderId: number) => {
    return follows.some(follow => follow.trader_id === traderId)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Trader Marketplace</h1>
        <p className="text-muted-foreground">
          Discover and follow successful traders to copy their strategies.
        </p>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search traders by username..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Traders Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredTraders.map((trader) => (
          <Card key={trader.id} className="relative">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-primary rounded-full flex items-center justify-center">
                    <span className="text-primary-foreground font-semibold">
                      {trader.username.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <CardTitle className="text-lg">{trader.username}</CardTitle>
                    <div className="flex items-center space-x-2">
                      <Badge variant="secondary">Level {trader.level}</Badge>
                      <div className={`w-2 h-2 rounded-full ${trader.is_online ? 'status-online' : 'status-offline'}`} />
                    </div>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Stats */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Total Profit</p>
                    <p className={`font-semibold ${trader.stats.total_profit >= 0 ? 'profit-text' : 'loss-text'}`}>
                      {formatCurrency(trader.stats.total_profit)}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Win Rate</p>
                    <p className="font-semibold">{trader.stats.win_rate.toFixed(1)}%</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Trades</p>
                    <p className="font-semibold">{trader.stats.total_trades}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Followers</p>
                    <p className="font-semibold">{trader.stats.followers_count}</p>
                  </div>
                </div>

                {/* XP */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-muted-foreground">XP Points</span>
                    <span className="text-sm font-medium">{trader.xp_points.toLocaleString()}</span>
                  </div>
                </div>

                {/* Action Button */}
                <div className="pt-2">
                  {trader.id === user?.id ? (
                    <Badge variant="outline" className="w-full justify-center">
                      This is you
                    </Badge>
                  ) : isFollowing(trader.id) ? (
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={() => handleUnfollow(trader.id)}
                      disabled={isLoading}
                    >
                      <Users className="h-4 w-4 mr-2" />
                      Following
                    </Button>
                  ) : (
                    <Button
                      className="w-full"
                      onClick={() => handleFollow(trader.id)}
                      disabled={isLoading}
                    >
                      <Star className="h-4 w-4 mr-2" />
                      Follow
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredTraders.length === 0 && (
        <Card>
          <CardContent className="text-center py-12">
            <Users className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No traders found</h3>
            <p className="text-muted-foreground">
              {searchTerm ? 'Try adjusting your search terms.' : 'No traders available at the moment.'}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
} 