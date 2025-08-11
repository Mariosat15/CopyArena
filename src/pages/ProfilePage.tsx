import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Progress } from '../components/ui/progress'
import { useToast } from '../hooks/use-toast'
import { 
  User, 
  Mail, 
  Calendar, 
  Trophy, 
  TrendingUp, 
  DollarSign,
  Users,
  Star,
  Settings,
  Shield,
  Crown,
  Target,
  BarChart3,
  Zap,
  Edit,
  Save,
  X,
  Camera,
  Award,
  Medal,
  Flame,
  AlertCircle,
  RefreshCw
} from 'lucide-react'
import { api } from '../lib/api'

interface UserStats {
  totalTrades: number
  winRate: number
  totalProfit: number
  followers: number
  following: number
  rank: string
  level: number
  xp: number
  nextLevelXp: number
}

interface UserProfile {
  id: number
  username: string
  email: string
  subscription_plan: string
  credits: number
  xp_points: number
  level: number
  is_active: boolean
  created_at: string
  api_key: string
  is_master_trader: boolean
}

const ProfilePage: React.FC = () => {
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [stats, setStats] = useState<UserStats | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [editedUsername, setEditedUsername] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isProfileLoading, setIsProfileLoading] = useState(true)
  const [profileError, setProfileError] = useState<string | null>(null)
  const { toast } = useToast()

  useEffect(() => {
    fetchUserData()
    fetchUserStats()
  }, [])

  const fetchUserData = async () => {
    try {
      setIsProfileLoading(true)
      setProfileError(null)
      const response = await api.get('/api/user/profile')
      setProfile(response.data.user)
      setEditedUsername(response.data.user.username)
    } catch (error: any) {
      console.error('Failed to fetch user data:', error)
      setProfileError(error.response?.data?.detail || 'Failed to load profile data')
      toast({
        title: "Profile Load Error",
        description: "Failed to load your profile. Please refresh the page.",
        variant: "destructive"
      })
    } finally {
      setIsProfileLoading(false)
    }
  }

  const fetchUserStats = async () => {
    try {
      const response = await api.get('/api/user/stats')
      setStats(response.data)
    } catch (error) {
      console.error('Failed to fetch user stats:', error)
      // Fallback to default stats if API fails
      setStats({
        totalTrades: 0,
        winRate: 0,
        totalProfit: 0,
        followers: 0,
        following: 0,
        rank: 'Bronze',
        level: profile?.level || 1,
        xp: profile?.xp_points || 0,
        nextLevelXp: (profile?.level || 1) * 1000
      })
    }
  }

  const updateUsername = async () => {
    if (!editedUsername.trim()) {
      toast({
        title: "Invalid Username",
        description: "Username cannot be empty.",
        variant: "destructive"
      })
      return
    }

    try {
      setIsLoading(true)
      // Replace with actual API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      if (profile) {
        setProfile({ ...profile, username: editedUsername })
      }
      
      setIsEditing(false)
      toast({
        title: "Profile Updated!",
        description: "Your username has been updated successfully.",
      })
    } catch (error) {
      toast({
        title: "Update Failed",
        description: "Failed to update username. Please try again.",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }

  const toggleMasterTrader = async () => {
    try {
      setIsLoading(true)
      const newStatus = !profile?.is_master_trader
      const response = await api.post('/api/user/master-trader', {
        is_master_trader: newStatus
      })
      setProfile(prev => prev ? { ...prev, is_master_trader: response.data.is_master_trader } : null)
      
      toast({
        title: response.data.is_master_trader ? "Master Trader Enabled!" : "Master Trader Disabled",
        description: response.data.is_master_trader 
          ? "You can now be copied by other traders in the marketplace."
          : "You're no longer visible in the trader marketplace.",
      })
    } catch (error) {
      toast({
        title: "Update Failed",
        description: "Failed to update master trader status.",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }

  const getProgressPercentage = () => {
    if (!stats) return 0
    return (((stats.xp || 0) % 1000) / 1000) * 100
  }

  const getRankColor = (rank: string) => {
    switch (rank.toLowerCase()) {
      case 'bronze': return 'text-amber-600 bg-amber-100'
      case 'silver': return 'text-gray-600 bg-gray-100'
      case 'gold': return 'text-yellow-600 bg-yellow-100'
      case 'platinum': return 'text-purple-600 bg-purple-100'
      case 'diamond': return 'text-blue-600 bg-blue-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const getRankIcon = (rank: string) => {
    switch (rank.toLowerCase()) {
      case 'bronze': return <Medal className="w-4 h-4" />
      case 'silver': return <Award className="w-4 h-4" />
      case 'gold': return <Trophy className="w-4 h-4" />
      case 'platinum': return <Crown className="w-4 h-4" />
      case 'diamond': return <Star className="w-4 h-4" />
      default: return <Target className="w-4 h-4" />
    }
  }

  if (isProfileLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading your profile...</p>
        </div>
      </div>
    )
  }

  if (profileError || !profile) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Profile Load Error</h3>
          <p className="text-muted-foreground mb-4">{profileError || 'Failed to load profile data'}</p>
          <Button onClick={fetchUserData} disabled={isProfileLoading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${isProfileLoading ? 'animate-spin' : ''}`} />
            Retry
          </Button>
        </div>
      </div>
    )
  }

  if (!stats) {
    // Generate default stats if they fail to load
    setStats({
      totalTrades: 0,
      winRate: 0,
      totalProfit: 0,
      followers: 0,
      following: 0,
      rank: 'Bronze',
      level: profile?.level || 1,
      xp: profile?.xp_points || 0,
      nextLevelXp: (profile?.level || 1) * 1000
    })
  }

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <div className="relative bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-8 text-white overflow-hidden">
        <div className="absolute inset-0 bg-black/10"></div>
        <div className="relative z-10">
          <div className="flex flex-col md:flex-row items-start md:items-center space-y-4 md:space-y-0 md:space-x-6">
            <div className="relative">
              <div className="w-24 h-24 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-sm">
                <User className="w-12 h-12 text-white" />
              </div>
              <button className="absolute -bottom-2 -right-2 w-8 h-8 bg-blue-500 hover:bg-blue-600 rounded-full flex items-center justify-center transition-colors">
                <Camera className="w-4 h-4 text-white" />
              </button>
            </div>
            
            <div className="flex-1">
              <div className="flex items-center space-x-3 mb-2">
                {isEditing ? (
                  <div className="flex items-center space-x-2">
                    <Input
                      value={editedUsername}
                      onChange={(e) => setEditedUsername(e.target.value)}
                      className="text-xl font-bold bg-white/20 border-white/30 text-white placeholder-white/70"
                      placeholder="Enter username"
                    />
                    <Button
                      onClick={updateUsername}
                      size="sm"
                      variant="secondary"
                      disabled={isLoading}
                    >
                      <Save className="w-4 h-4" />
                    </Button>
                    <Button
                      onClick={() => {
                        setIsEditing(false)
                        setEditedUsername(profile.username)
                      }}
                      size="sm"
                      variant="outline"
                      className="border-white/30 text-white hover:bg-white/20"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                ) : (
                  <div className="flex items-center space-x-3">
                    <h1 className="text-3xl font-bold">{profile.username}</h1>
                    <Button
                      onClick={() => setIsEditing(true)}
                      size="sm"
                      variant="ghost"
                      className="text-white hover:bg-white/20"
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                  </div>
                )}
                <Badge className={`${getRankColor(stats?.rank || 'Bronze')} border-0`}>
                  {getRankIcon(stats?.rank || 'Bronze')}
                  <span className="ml-1">{stats?.rank || 'Bronze'}</span>
                </Badge>
              </div>
              
              <div className="flex flex-wrap items-center gap-4 text-white/90">
                <div className="flex items-center space-x-1">
                  <Mail className="w-4 h-4" />
                  <span>{profile.email}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Calendar className="w-4 h-4" />
                  <span>Joined {new Date(profile.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Shield className="w-4 h-4" />
                  <span className="capitalize">{profile.subscription_plan}</span>
                </div>
              </div>
            </div>

            <div className="text-right">
              <div className="text-3xl font-bold">Level {stats?.level || 1}</div>
              <div className="text-white/80">{(stats?.xp || 0).toLocaleString()} XP</div>
              <div className="w-32 mt-2">
                <Progress value={getProgressPercentage()} className="h-2 bg-white/20" />
                <div className="text-xs text-white/70 mt-1">
                  {(1000 - ((stats?.xp || 0) % 1000)).toLocaleString()} XP to next level
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Master Trader Status */}
      <Card className={`border-2 ${profile.is_master_trader ? 'border-gold bg-gradient-to-r from-yellow-50 to-orange-50' : 'border-gray-200'}`}>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className={`p-2 rounded-full ${profile.is_master_trader ? 'bg-yellow-100' : 'bg-gray-100'}`}>
                <Crown className={`w-6 h-6 ${profile.is_master_trader ? 'text-yellow-600' : 'text-gray-600'}`} />
              </div>
              <div>
                <h3 className="text-xl font-bold">Master Trader Status</h3>
                <p className="text-sm text-muted-foreground font-normal">
                  {profile.is_master_trader 
                    ? 'You\'re visible in the trader marketplace and can be copied by others'
                    : 'Enable this to allow others to copy your trades and earn from your success'
                  }
                </p>
              </div>
            </div>
            <Button
              onClick={toggleMasterTrader}
              disabled={isLoading}
              variant={profile.is_master_trader ? "outline" : "default"}
              className={profile.is_master_trader ? "border-yellow-300 text-yellow-700 hover:bg-yellow-50" : ""}
            >
              {profile.is_master_trader ? 'Disable' : 'Enable'} Master Trader
            </Button>
          </CardTitle>
        </CardHeader>
        {profile.is_master_trader && (
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center p-4 bg-slate-800/50 rounded-lg border border-yellow-500/20 backdrop-blur-sm">
                <Users className="w-8 h-8 text-yellow-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-yellow-300">{stats?.followers || 0}</div>
                <div className="text-sm text-yellow-400/80">Followers</div>
              </div>
              <div className="text-center p-4 bg-slate-800/50 rounded-lg border border-green-500/20 backdrop-blur-sm">
                <TrendingUp className="w-8 h-8 text-green-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-green-300">{stats?.winRate || 0}%</div>
                <div className="text-sm text-green-400/80">Win Rate</div>
              </div>
              <div className="text-center p-4 bg-slate-800/50 rounded-lg border border-blue-500/20 backdrop-blur-sm">
                <DollarSign className="w-8 h-8 text-blue-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-blue-300">${(stats?.totalProfit || 0).toLocaleString()}</div>
                <div className="text-sm text-blue-400/80">Total Profit</div>
              </div>
            </div>
          </CardContent>
        )}
      </Card>

      {/* Trading Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        <Card className="border-blue-500/20 bg-slate-800/50 backdrop-blur-sm">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-blue-400">Total Trades</p>
                <p className="text-3xl font-bold text-blue-300">{stats?.totalTrades || 0}</p>
              </div>
              <div className="p-3 bg-blue-500/20 rounded-full">
                <BarChart3 className="w-6 h-6 text-blue-400" />
              </div>
            </div>
            <div className="mt-4 flex items-center text-sm">
              <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
              <span className="text-green-600">+12.5% from last month</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-green-500/20 bg-slate-800/50 backdrop-blur-sm">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-green-400">Win Rate</p>
                <p className="text-3xl font-bold text-green-300">{stats?.winRate || 0}%</p>
              </div>
              <div className="p-3 bg-green-500/20 rounded-full">
                <Target className="w-6 h-6 text-green-400" />
              </div>
            </div>
            <div className="mt-4 flex items-center text-sm">
              <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
              <span className="text-green-600">+3.2% this week</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-purple-500/20 bg-slate-800/50 backdrop-blur-sm">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-purple-400">Total Profit</p>
                <p className="text-3xl font-bold text-purple-300">${(stats?.totalProfit || 0).toLocaleString()}</p>
              </div>
              <div className="p-3 bg-purple-500/20 rounded-full">
                <DollarSign className="w-6 h-6 text-purple-400" />
              </div>
            </div>
            <div className="mt-4 flex items-center text-sm">
              <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
              <span className="text-green-600">+$847.30 this month</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-orange-200 bg-orange-50">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-orange-600">Credits</p>
                <p className="text-3xl font-bold text-orange-700">{profile.credits}</p>
              </div>
              <div className="p-3 bg-orange-100 rounded-full">
                <Zap className="w-6 h-6 text-orange-600" />
              </div>
            </div>
            <div className="mt-4 flex items-center text-sm">
              <span className="text-orange-600">Available for premium features</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Account Management */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Settings className="w-5 h-5 text-blue-600" />
              <span>Account Settings</span>
            </CardTitle>
            <CardDescription>
              Manage your account preferences and security settings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <h4 className="font-medium">Two-Factor Authentication</h4>
                <p className="text-sm text-muted-foreground">Add an extra layer of security</p>
              </div>
              <Badge variant="outline" className="text-red-600 border-red-200">
                Disabled
              </Badge>
            </div>
            
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <h4 className="font-medium">Email Notifications</h4>
                <p className="text-sm text-muted-foreground">Receive trade alerts and updates</p>
              </div>
              <Badge variant="outline" className="text-green-400 border-green-500/30 bg-green-500/10">
                Enabled
              </Badge>
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <h4 className="font-medium">API Access</h4>
                <p className="text-sm text-muted-foreground">Manage your API keys and access</p>
              </div>
              <Badge variant="outline" className="text-blue-400 border-blue-500/30 bg-blue-500/10">
                Active
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Trophy className="w-5 h-5 text-yellow-600" />
              <span>Achievements</span>
            </CardTitle>
            <CardDescription>
              Your trading milestones and accomplishments
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center space-x-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="p-2 bg-yellow-100 rounded-full">
                <Flame className="w-5 h-5 text-yellow-600" />
              </div>
              <div>
                <h4 className="font-medium text-yellow-800">Hot Streak</h4>
                <p className="text-sm text-yellow-600">7 consecutive winning trades</p>
              </div>
            </div>

            <div className="flex items-center space-x-3 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg backdrop-blur-sm">
              <div className="p-2 bg-blue-500/20 rounded-full">
                <Target className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <h4 className="font-medium text-blue-300">Precision Trader</h4>
                <p className="text-sm text-blue-400/80">Maintained 70%+ win rate for 30 days</p>
              </div>
            </div>

            <div className="flex items-center space-x-3 p-3 bg-green-500/10 border border-green-500/30 rounded-lg backdrop-blur-sm">
              <div className="p-2 bg-green-500/20 rounded-full">
                <Users className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <h4 className="font-medium text-green-300">Community Leader</h4>
                <p className="text-sm text-green-400/80">100+ followers in the marketplace</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>
            Common tasks and shortcuts for your account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Button variant="outline" className="h-16 flex-col space-y-2">
              <Settings className="w-5 h-5" />
              <span className="text-sm">Settings</span>
            </Button>
            
            <Button variant="outline" className="h-16 flex-col space-y-2">
              <Shield className="w-5 h-5" />
              <span className="text-sm">Security</span>
            </Button>
            
            <Button variant="outline" className="h-16 flex-col space-y-2">
              <BarChart3 className="w-5 h-5" />
              <span className="text-sm">Analytics</span>
            </Button>
            
            <Button variant="outline" className="h-16 flex-col space-y-2">
              <Users className="w-5 h-5" />
              <span className="text-sm">Network</span>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default ProfilePage