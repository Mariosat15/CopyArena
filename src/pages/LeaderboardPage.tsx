// @ts-ignore
import React, { useEffect, useState } from 'react'
import { useTradingStore } from '../stores/tradingStore'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Trophy, Medal, Award, TrendingUp, Users, Target } from 'lucide-react'
import { formatCurrency } from '../lib/utils'

type SortOption = 'xp_points' | 'total_profit' | 'followers_count'

export function LeaderboardPage() {
  const { leaderboard, fetchLeaderboard } = useTradingStore()
  const [sortBy, setSortBy] = useState<SortOption>('xp_points')

  useEffect(() => {
    fetchLeaderboard(sortBy)
  }, [fetchLeaderboard, sortBy])

  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1:
        return <Trophy className="h-6 w-6 text-yellow-500" />
      case 2:
        return <Medal className="h-6 w-6 text-gray-400" />
      case 3:
        return <Award className="h-6 w-6 text-orange-500" />
      default:
        return <span className="text-lg font-bold text-muted-foreground">#{rank}</span>
    }
  }

  const getSortLabel = (sort: SortOption) => {
    switch (sort) {
      case 'xp_points':
        return 'XP Points'
      case 'total_profit':
        return 'Total Profit'
      case 'followers_count':
        return 'Followers'
    }
  }

  const getSortValue = (trader: any, sort: SortOption) => {
    switch (sort) {
      case 'xp_points':
        return trader.xp_points.toLocaleString()
      case 'total_profit':
        return formatCurrency(trader.total_profit)
      case 'followers_count':
        return trader.followers_count.toString()
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Leaderboard</h1>
        <p className="text-muted-foreground">
          See how you rank against other traders in the community.
        </p>
      </div>

      {/* Sort Options */}
      <Card>
        <CardHeader>
          <CardTitle>Sort By</CardTitle>
          <CardDescription>Choose how to rank traders</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {(['xp_points', 'total_profit', 'followers_count'] as SortOption[]).map((option) => (
              <Button
                key={option}
                variant={sortBy === option ? "default" : "outline"}
                onClick={() => setSortBy(option)}
                className="flex items-center space-x-2"
              >
                {option === 'xp_points' && <TrendingUp className="h-4 w-4" />}
                {option === 'total_profit' && <Target className="h-4 w-4" />}
                {option === 'followers_count' && <Users className="h-4 w-4" />}
                <span>{getSortLabel(option)}</span>
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Leaderboard */}
      <Card>
        <CardHeader>
          <CardTitle>Rankings</CardTitle>
          <CardDescription>
            Ranked by {getSortLabel(sortBy).toLowerCase()}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {leaderboard.map((trader, index) => {
              const rank = index + 1
              return (
                <div
                  key={trader.id}
                  className={`flex items-center justify-between p-4 rounded-lg border ${
                    rank <= 3 ? 'bg-muted/50' : ''
                  }`}
                >
                  <div className="flex items-center space-x-4">
                    {/* Rank */}
                    <div className="flex-shrink-0 w-12 flex justify-center">
                      {getRankIcon(rank)}
                    </div>

                    {/* Trader Info */}
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-primary rounded-full flex items-center justify-center">
                        <span className="text-primary-foreground font-semibold">
                          {trader.username.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <h3 className="font-semibold">{trader.username}</h3>
                          <div className={`w-2 h-2 rounded-full ${trader.is_online ? 'status-online' : 'status-offline'}`} />
                        </div>
                        <div className="flex items-center space-x-2 mt-1">
                          <Badge variant="secondary">Level {trader.level}</Badge>
                          {rank <= 3 && (
                            <Badge variant="outline" className="text-xs">
                              Top {rank}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Stats */}
                  <div className="text-right">
                    <div className="text-lg font-bold">
                      {getSortValue(trader, sortBy)}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {sortBy === 'xp_points' && `Level ${trader.level}`}
                      {sortBy === 'total_profit' && `${trader.stats?.total_trades || 0} trades`}
                      {sortBy === 'followers_count' && 'followers'}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {leaderboard.length === 0 && (
            <div className="text-center py-12">
              <Trophy className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No rankings available</h3>
              <p className="text-muted-foreground">
                Be the first to start trading and climb the leaderboard!
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Achievement Info */}
      <Card>
        <CardHeader>
          <CardTitle>How Rankings Work</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div className="flex items-start space-x-3">
              <TrendingUp className="h-5 w-5 text-primary mt-0.5" />
              <div>
                <h4 className="font-semibold">XP Points</h4>
                <p className="text-muted-foreground">
                  Earned from profitable trades. 1 USD profit = 10 XP.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <Target className="h-5 w-5 text-primary mt-0.5" />
              <div>
                <h4 className="font-semibold">Total Profit</h4>
                <p className="text-muted-foreground">
                  Cumulative profit from all completed trades.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <Users className="h-5 w-5 text-primary mt-0.5" />
              <div>
                <h4 className="font-semibold">Followers</h4>
                <p className="text-muted-foreground">
                  Number of traders copying your strategies.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
} 