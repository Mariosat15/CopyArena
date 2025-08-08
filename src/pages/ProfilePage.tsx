// @ts-ignore
import React, { useState, useEffect } from 'react'
import { useAuthStore } from '../stores/authStore'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Progress } from '../components/ui/progress'
import { Download, Copy, CheckCircle, AlertCircle, ExternalLink } from 'lucide-react'
import { useToast } from '../hooks/use-toast'
import api from '../lib/api'

export default function ProfilePage() {
  const { user } = useAuthStore()
  const { toast } = useToast()
  const [apiKey, setApiKey] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [setupStep, setSetupStep] = useState(1)

  useEffect(() => {
    fetchUserData()
  }, [])

  const fetchUserData = async () => {
    try {
      const response = await api.get('/api/auth/session')
      setApiKey(response.data.user.api_key)
      
      // Check connection status
      const statsResponse = await api.get('/api/account/stats')
      setIsConnected(statsResponse.data.is_connected)
    } catch (error) {
      console.error('Error fetching user data:', error)
    }
  }

  const copyApiKey = () => {
    navigator.clipboard.writeText(apiKey)
    toast({
      title: "API Key Copied!",
      description: "Your API key has been copied to clipboard.",
    })
  }

  const downloadEA = async () => {
    try {
      const response = await api.get('/api/ea/download', {
        responseType: 'blob'
      })
      
      const blob = new Blob([response.data], { type: 'text/plain' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'CopyArenaConnector.mq5'
      link.click()
      window.URL.revokeObjectURL(url)
      
      toast({
        title: "EA Downloaded!",
        description: "CopyArena Expert Advisor has been downloaded.",
      })
      
      setSetupStep(2)
    } catch (error) {
      toast({
        title: "Download Failed",
        description: "Failed to download EA. Please try again.",
        variant: "destructive"
      })
    }
  }

  const getProgressPercentage = (level: number) => {
    return ((level % 10) / 10) * 100
  }

  const getUserStats = () => {
    // Mock stats - in real app, fetch from API
    return {
      totalTrades: 45,
      winRate: 73.5,
      totalProfit: 2847.50,
      followers: 28,
      following: 12
    }
  }

  const stats = getUserStats()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Profile & Setup</h1>
          <p className="text-muted-foreground">
            Manage your account and connect your MT5 terminal
          </p>
        </div>
        <div className="flex items-center space-x-2">
          {isConnected ? (
            <Badge variant="default" className="bg-green-500">
              <CheckCircle className="w-4 h-4 mr-1" />
              Connected
            </Badge>
          ) : (
            <Badge variant="secondary" className="bg-red-500 text-white">
              <AlertCircle className="w-4 h-4 mr-1" />
              Not Connected
            </Badge>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Info */}
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Profile</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium">Username</label>
                <p className="text-lg">{user?.username}</p>
              </div>
              <div>
                <label className="text-sm font-medium">Email</label>
                <p className="text-lg">{user?.email}</p>
              </div>
              <div>
                <label className="text-sm font-medium">Subscription</label>
                <Badge variant="outline">{user?.subscription_plan?.toUpperCase()}</Badge>
              </div>
              <div>
                <label className="text-sm font-medium">Level</label>
                <div className="flex items-center space-x-2">
                  <span className="text-lg font-bold">{user?.level}</span>
                  <Progress value={getProgressPercentage(user?.level || 1)} className="flex-1" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Stats Card */}
          <Card>
            <CardHeader>
              <CardTitle>Trading Stats</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Total Trades</p>
                  <p className="text-2xl font-bold">{stats.totalTrades}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Win Rate</p>
                  <p className="text-2xl font-bold text-green-600">{stats.winRate}%</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Profit</p>
                  <p className="text-2xl font-bold text-green-600">${stats.totalProfit}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Followers</p>
                  <p className="text-2xl font-bold">{stats.followers}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Setup Instructions */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <span>MT5 Connection Setup</span>
                <Badge className="ml-2" variant={isConnected ? "default" : "secondary"}>
                  {isConnected ? "Connected" : "Setup Required"}
                </Badge>
              </CardTitle>
              <CardDescription>
                Connect your MT5 terminal to CopyArena using our Expert Advisor
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Step 1: Get API Key */}
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    setupStep >= 1 ? 'bg-blue-500 text-white' : 'bg-gray-200'
                  }`}>
                    1
                  </div>
                  <h3 className="font-semibold">Your API Key</h3>
                </div>
                <div className="ml-10 space-y-2">
                  <p className="text-sm text-muted-foreground">
                    Copy your unique API key to connect your EA to your account:
                  </p>
                  <div className="flex items-center space-x-2 p-3 bg-gray-50 rounded-lg">
                    <code className="flex-1 text-sm font-mono">{apiKey}</code>
                    <Button size="sm" variant="outline" onClick={copyApiKey}>
                      <Copy className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>

              {/* Step 2: Download EA */}
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    setupStep >= 2 ? 'bg-blue-500 text-white' : 'bg-gray-200'
                  }`}>
                    2
                  </div>
                  <h3 className="font-semibold">Download Expert Advisor</h3>
                </div>
                <div className="ml-10 space-y-2">
                  <p className="text-sm text-muted-foreground">
                    Download our custom Expert Advisor for MT5:
                  </p>
                  <Button onClick={downloadEA} className="flex items-center space-x-2">
                    <Download className="w-4 h-4" />
                    <span>Download CopyArenaConnector.mq5</span>
                  </Button>
                </div>
              </div>

              {/* Step 3: Install EA */}
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    setupStep >= 3 ? 'bg-blue-500 text-white' : 'bg-gray-200'
                  }`}>
                    3
                  </div>
                  <h3 className="font-semibold">Install in MT5</h3>
                </div>
                <div className="ml-10 space-y-2">
                  <p className="text-sm text-muted-foreground">
                    Follow these steps to install the EA in your MT5 terminal:
                  </p>
                  <ol className="list-decimal list-inside space-y-1 text-sm">
                    <li>Open your MT5 terminal</li>
                    <li>Press <kbd className="px-2 py-1 bg-gray-100 rounded">F4</kbd> to open MetaEditor</li>
                    <li>Go to <strong>File → Open Data Folder</strong></li>
                    <li>Navigate to <strong>MQL5 → Experts</strong></li>
                    <li>Copy the downloaded <code>CopyArenaConnector.mq5</code> file here</li>
                    <li>Return to MT5 and refresh the Navigator (F5)</li>
                  </ol>
                  <Button variant="outline" size="sm" onClick={() => setSetupStep(4)}>
                    <CheckCircle className="w-4 h-4 mr-2" />
                    EA Installed
                  </Button>
                </div>
              </div>

              {/* Step 4: Configure EA */}
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    setupStep >= 4 ? 'bg-blue-500 text-white' : 'bg-gray-200'
                  }`}>
                    4
                  </div>
                  <h3 className="font-semibold">Configure & Activate</h3>
                </div>
                <div className="ml-10 space-y-2">
                  <p className="text-sm text-muted-foreground">
                    Configure the EA with your API key:
                  </p>
                  <ol className="list-decimal list-inside space-y-1 text-sm">
                    <li>Drag <strong>CopyArenaConnector</strong> from Navigator to any chart</li>
                    <li>In the EA settings, paste your API key in the <strong>API_Key</strong> field</li>
                    <li>Make sure <strong>Allow WebRequest</strong> is enabled in MT5 settings</li>
                    <li>Add <strong>https://copyarena-backend.onrender.com</strong> to allowed URLs</li>
                    <li>Click <strong>OK</strong> to activate the EA</li>
                  </ol>
                  <div className="p-3 bg-blue-50 rounded-lg">
                    <p className="text-sm">
                      <strong>Note:</strong> The EA will automatically sync your trading data to CopyArena every 5 seconds.
                      You'll see connection status in the MT5 logs.
                    </p>
                  </div>
                </div>
              </div>

              {/* Step 5: Verify Connection */}
              {setupStep >= 4 && (
                <div className="space-y-3">
                  <div className="flex items-center space-x-2">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                      isConnected ? 'bg-green-500 text-white' : 'bg-gray-200'
                    }`}>
                      5
                    </div>
                    <h3 className="font-semibold">Verify Connection</h3>
                  </div>
                  <div className="ml-10 space-y-2">
                    <p className="text-sm text-muted-foreground">
                      Check if your EA is connected successfully:
                    </p>
                    {isConnected ? (
                      <div className="p-3 bg-green-50 rounded-lg flex items-center space-x-2">
                        <CheckCircle className="w-5 h-5 text-green-500" />
                        <span className="text-sm text-green-700">
                          Great! Your MT5 account is connected and sending data to CopyArena.
                        </span>
                      </div>
                    ) : (
                      <div className="p-3 bg-yellow-50 rounded-lg flex items-center space-x-2">
                        <AlertCircle className="w-5 h-5 text-yellow-500" />
                        <span className="text-sm text-yellow-700">
                          Waiting for connection... Make sure the EA is running and check MT5 logs for any errors.
                        </span>
                      </div>
                    )}
                    <Button variant="outline" size="sm" onClick={fetchUserData}>
                      Refresh Status
                    </Button>
                  </div>
                </div>
              )}

              {/* Troubleshooting */}
              <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                <h4 className="font-semibold mb-2">Troubleshooting</h4>
                <ul className="text-sm space-y-1 text-muted-foreground">
                  <li>• Make sure MT5 AutoTrading is enabled (green button in toolbar)</li>
                  <li>• Check that WebRequest URLs include our server in MT5 settings</li>
                  <li>• Verify your internet connection is stable</li>
                  <li>• Check MT5 Expert logs for connection errors</li>
                </ul>
                <Button variant="link" size="sm" className="mt-2 p-0">
                  <ExternalLink className="w-4 h-4 mr-1" />
                  View Detailed Setup Guide
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
} 