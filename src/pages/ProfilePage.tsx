import { useAuthStore } from '../stores/authStore'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Progress } from '../components/ui/progress'
import { Edit, Crown, CreditCard, Settings, Trophy } from 'lucide-react'
import { formatCurrency, getProgressToNextLevel } from '../lib/utils'

export function ProfilePage() {
  const { user } = useAuthStore()

  if (!user) return null

  const progressToNextLevel = getProgressToNextLevel(user.xp_points, user.level)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Profile</h1>
        <p className="text-muted-foreground">
          Manage your account and view your trading statistics.
        </p>
      </div>

      {/* Profile Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* User Info */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Profile Information</CardTitle>
              <Button variant="outline" size="sm">
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* Avatar and Basic Info */}
              <div className="flex items-center space-x-4">
                <div className="w-16 h-16 bg-primary rounded-full flex items-center justify-center">
                  <span className="text-primary-foreground text-2xl font-bold">
                    {user.username.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div>
                  <h3 className="text-2xl font-bold">{user.username}</h3>
                  <p className="text-muted-foreground">{user.email}</p>
                  <div className="flex items-center space-x-2 mt-2">
                    <Badge variant="secondary">Level {user.level}</Badge>
                    <Badge variant={user.subscription_plan === 'free' ? 'outline' : 'default'}>
                      {user.subscription_plan.charAt(0).toUpperCase() + user.subscription_plan.slice(1)}
                    </Badge>
                  </div>
                </div>
              </div>

              {/* XP Progress */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">Level Progress</span>
                  <span className="text-sm text-muted-foreground">
                    {user.xp_points.toLocaleString()} XP
                  </span>
                </div>
                <Progress value={progressToNextLevel} className="h-2" />
                <p className="text-xs text-muted-foreground mt-1">
                  {progressToNextLevel.toFixed(0)}% to Level {user.level + 1}
                </p>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-4 border rounded-lg">
                  <div className="text-2xl font-bold profit-text">
                    {formatCurrency(user.stats?.total_profit || 0)}
                  </div>
                  <p className="text-sm text-muted-foreground">Total Profit</p>
                </div>
                <div className="text-center p-4 border rounded-lg">
                  <div className="text-2xl font-bold">{user.stats?.win_rate || 0}%</div>
                  <p className="text-sm text-muted-foreground">Win Rate</p>
                </div>
                <div className="text-center p-4 border rounded-lg">
                  <div className="text-2xl font-bold">{user.stats?.total_trades || 0}</div>
                  <p className="text-sm text-muted-foreground">Total Trades</p>
                </div>
                <div className="text-center p-4 border rounded-lg">
                  <div className="text-2xl font-bold">{user.stats?.followers_count || 0}</div>
                  <p className="text-sm text-muted-foreground">Followers</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Subscription & Credits */}
        <div className="space-y-6">
          {/* Subscription */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Crown className="h-5 w-5" />
                <span>Subscription</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="text-center">
                  <Badge 
                    variant={user.subscription_plan === 'free' ? 'outline' : 'default'}
                    className="text-lg px-4 py-2"
                  >
                    {user.subscription_plan.charAt(0).toUpperCase() + user.subscription_plan.slice(1)} Plan
                  </Badge>
                </div>
                
                {user.subscription_plan === 'free' && (
                  <div className="text-center space-y-2">
                    <p className="text-sm text-muted-foreground">
                      Upgrade to unlock copy trading and AI reports
                    </p>
                    <Button className="w-full">
                      <Crown className="h-4 w-4 mr-2" />
                      Upgrade Now
                    </Button>
                  </div>
                )}

                {user.subscription_plan !== 'free' && (
                  <div className="text-center space-y-2">
                    <p className="text-sm text-muted-foreground">
                      Enjoy full access to all features
                    </p>
                    <Button variant="outline" className="w-full">
                      <Settings className="h-4 w-4 mr-2" />
                      Manage Plan
                    </Button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Credits */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <CreditCard className="h-5 w-5" />
                <span>AI Credits</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="text-center">
                  <div className="text-3xl font-bold">{user.credits}</div>
                  <p className="text-sm text-muted-foreground">Available credits</p>
                </div>
                
                <Button variant="outline" className="w-full">
                  <CreditCard className="h-4 w-4 mr-2" />
                  Buy More Credits
                </Button>
                
                <p className="text-xs text-muted-foreground text-center">
                  Use credits to generate AI reports and analytics
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Achievements */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Trophy className="h-5 w-5" />
            <span>Achievements</span>
          </CardTitle>
          <CardDescription>Badges and milestones you've earned</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {user.badges?.map((badge, index) => (
              <div key={index} className="flex items-center space-x-3 p-4 border rounded-lg">
                <div className="text-3xl">{badge.icon}</div>
                <div>
                  <h4 className="font-semibold">{badge.name}</h4>
                  <p className="text-sm text-muted-foreground">
                    Earned {new Date(badge.earned_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            )) || (
              <div className="col-span-full text-center py-8">
                <Trophy className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">No badges yet</h3>
                <p className="text-muted-foreground">
                  Start trading to unlock your first achievement!
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
} 