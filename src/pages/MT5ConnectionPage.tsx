import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Progress } from '../components/ui/progress'
import { useToast } from '../hooks/use-toast'
import { 
  Download, 
  Copy, 
  CheckCircle, 
  AlertCircle, 
  ExternalLink, 
  Play,
  Smartphone,
  Shield,
  Zap,
  Users,
  BarChart3,
  Settings,
  RefreshCw
} from 'lucide-react'
import { api } from '../lib/api'

interface MT5Status {
  connected: boolean
  login?: number
  server?: string
  last_sync?: string
  message?: string
}

const MT5ConnectionPage: React.FC = () => {
  const [apiKey, setApiKey] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [setupStep, setSetupStep] = useState(1)
  const [status, setStatus] = useState<MT5Status | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const { toast } = useToast()

  useEffect(() => {
    fetchUserData()
    loadMT5Status()
    
    // Poll status every 30 seconds
    const interval = setInterval(loadMT5Status, 30000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    // Update setup step based on actual status
    if (isConnected) {
      setSetupStep(4) // Fully connected
    } else if (apiKey && apiKey !== 'Failed to load API key') {
      setSetupStep(1) // API key available
    } else {
      setSetupStep(1) // Starting state
    }
  }, [isConnected, apiKey])

  const fetchUserData = async () => {
    try {
      const response = await api.get('/api/user/profile', {
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      })
      setApiKey(response.data.user.api_key || '')
    } catch (error: any) {
      console.error('Failed to fetch user data:', error)
      setApiKey('Failed to load API key')
      toast({
        title: "API Key Load Error",
        description: "Failed to load your API key. Please refresh the page.",
        variant: "destructive"
      })
    }
  }

  const loadMT5Status = async () => {
    try {
      const response = await api.get('/api/mt5/status')
      setStatus(response.data)
      setIsConnected(response.data.connected)
      if (response.data.connected && setupStep < 4) {
        setSetupStep(4)
      }
    } catch (error) {
      console.error('Failed to load MT5 status:', error)
      setStatus({ connected: false, message: 'Unable to check connection status' })
    }
  }

  const regenerateApiKey = async () => {
    try {
      setIsLoading(true)
      const response = await api.post('/api/user/regenerate-api-key')
      setApiKey(response.data.api_key)
      await fetchUserData()
      toast({
        title: "New API Key Generated!",
        description: "Your API key has been updated. Use this in your Windows Client.",
      })
    } catch (error) {
      toast({
        title: "Failed to regenerate API key",
        description: "Please try again later.",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }

  const downloadClient = async () => {
    try {
      setIsLoading(true)
      const response = await api.get('/api/client/download', {
        responseType: 'blob'
      })
      
      const blob = new Blob([response.data], { type: 'application/octet-stream' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'CopyArenaClient.exe'
      link.click()
      window.URL.revokeObjectURL(url)
      
      toast({
        title: "Windows Client Downloaded!",
        description: "CopyArena Windows Client has been downloaded. Run the executable to connect your MT5.",
      })
      
      setSetupStep(Math.max(setupStep, 2))
    } catch (error) {
      toast({
        title: "Download Failed",
        description: "Failed to download Windows Client. Please try again.",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }

  const copyApiKey = () => {
    navigator.clipboard.writeText(apiKey)
    toast({
      title: "API Key Copied!",
      description: "Your API key has been copied to clipboard.",
    })
  }

  const getStepStatus = (step: number) => {
    if (setupStep > step) return 'completed'
    if (setupStep === step) return 'current'
    return 'pending'
  }

  const getProgressPercentage = () => {
    return Math.min((setupStep / 4) * 100, 100)
  }

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <div className="text-center space-y-4">
        <div className="flex items-center justify-center space-x-3">
          <div className="p-3 bg-blue-100 rounded-full">
            <Smartphone className="w-8 h-8 text-blue-600" />
          </div>
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              MT5 Connection Setup
            </h1>
            <p className="text-xl text-muted-foreground">
              Connect your MetaTrader 5 to CopyArena in just 3 simple steps
            </p>
          </div>
        </div>
        
        {/* Connection Status Banner */}
        <div className={`p-4 rounded-xl border-2 ${
          isConnected 
            ? 'bg-green-900/20 border-green-500/30' 
            : 'bg-amber-900/20 border-amber-500/30'
        }`}>
          <div className="flex items-center justify-center space-x-3">
            {isConnected ? (
              <>
                <CheckCircle className="w-6 h-6 text-green-400" />
                <div className="text-center">
                  <p className="font-semibold text-green-400">MT5 Connected Successfully!</p>
                  {status?.login && (
                    <p className="text-sm text-green-300">
                      Account: {status.login} | Server: {status.server}
                    </p>
                  )}
                </div>
              </>
            ) : (
              <>
                <AlertCircle className="w-6 h-6 text-amber-400" />
                <div className="text-center">
                  <p className="font-semibold text-amber-400">MT5 Not Connected</p>
                  <p className="text-sm text-amber-300">
                    Follow the steps below to connect your MT5 terminal
                  </p>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="max-w-md mx-auto">
          <div className="flex justify-between mb-2">
            <span className="text-sm font-medium text-muted-foreground">Setup Progress</span>
            <span className="text-sm font-medium text-blue-600">{Math.round(getProgressPercentage())}%</span>
          </div>
          <Progress value={getProgressPercentage()} className="h-3" />
        </div>
      </div>

      {/* Benefits Section */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-blue-500/30 bg-blue-900/20 backdrop-blur-sm">
          <CardContent className="p-4 text-center">
            <Shield className="w-8 h-8 text-blue-400 mx-auto mb-2" />
            <h3 className="font-semibold text-blue-300">Secure</h3>
            <p className="text-sm text-blue-200">End-to-end encryption</p>
          </CardContent>
        </Card>
        <Card className="border-green-500/30 bg-green-900/20 backdrop-blur-sm">
          <CardContent className="p-4 text-center">
            <Zap className="w-8 h-8 text-green-400 mx-auto mb-2" />
            <h3 className="font-semibold text-green-300">Fast Setup</h3>
            <p className="text-sm text-green-200">Ready in 3 minutes</p>
          </CardContent>
        </Card>
        <Card className="border-purple-500/30 bg-purple-900/20 backdrop-blur-sm">
          <CardContent className="p-4 text-center">
            <BarChart3 className="w-8 h-8 text-purple-400 mx-auto mb-2" />
            <h3 className="font-semibold text-purple-300">Real-time</h3>
            <p className="text-sm text-purple-200">Live trade tracking</p>
          </CardContent>
        </Card>
        <Card className="border-orange-500/30 bg-orange-900/20 backdrop-blur-sm">
          <CardContent className="p-4 text-center">
            <Users className="w-8 h-8 text-orange-400 mx-auto mb-2" />
            <h3 className="font-semibold text-orange-300">Copy Trading</h3>
            <p className="text-sm text-orange-200">Share & earn</p>
          </CardContent>
        </Card>
      </div>

      {/* Setup Steps */}
      <div className="max-w-4xl mx-auto space-y-6">
        
        {/* Step 1: Get API Key */}
        <Card className={`border-2 backdrop-blur-sm ${
          getStepStatus(1) === 'completed' ? 'border-green-500/30 bg-green-900/20' :
          getStepStatus(1) === 'current' ? 'border-blue-500/30 bg-blue-900/20' :
          'border-gray-500/30 bg-gray-900/20'
        }`}>
          <CardHeader>
            <CardTitle className="flex items-center space-x-3">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center text-lg font-bold ${
                getStepStatus(1) === 'completed' ? 'bg-green-500 text-white' :
                getStepStatus(1) === 'current' ? 'bg-blue-500 text-white' :
                'bg-gray-200 text-gray-600'
              }`}>
                {getStepStatus(1) === 'completed' ? <CheckCircle className="w-6 h-6" /> : '1'}
              </div>
              <div>
                <h3 className="text-xl font-bold">Your Secure API Key</h3>
                <p className="text-sm text-muted-foreground font-normal">
                  This unique key connects your Windows Client to your CopyArena account
                </p>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-600/30">
              <div className="flex items-center justify-between">
                <div className="flex-1 mr-4">
                  <p className="text-sm font-medium text-gray-300 mb-1">Your API Key:</p>
                  <code className="text-sm bg-gray-900/80 text-gray-100 px-3 py-2 rounded border border-gray-600/30 font-mono break-all">
                    {apiKey || 'Loading...'}
                  </code>
                </div>
                <div className="flex space-x-2">
                  <Button onClick={copyApiKey} size="sm" variant="outline">
                    <Copy className="w-4 h-4 mr-1" />
                    Copy
                  </Button>
                  <Button onClick={regenerateApiKey} size="sm" variant="outline" disabled={isLoading}>
                    <RefreshCw className={`w-4 h-4 mr-1 ${isLoading ? 'animate-spin' : ''}`} />
                    New Key
                  </Button>
                </div>
              </div>
            </div>
            <div className="bg-blue-900/30 border border-blue-500/30 p-3 rounded-lg">
              <p className="text-sm text-blue-300">
                <Shield className="w-4 h-4 inline mr-1" />
                <strong>Security:</strong> This key is unique to your account and cannot be used by others.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Step 2: Download Windows Client */}
        <Card className={`border-2 backdrop-blur-sm ${
          getStepStatus(2) === 'completed' ? 'border-green-500/30 bg-green-900/20' :
          getStepStatus(2) === 'current' ? 'border-blue-500/30 bg-blue-900/20' :
          'border-gray-500/30 bg-gray-900/20'
        }`}>
          <CardHeader>
            <CardTitle className="flex items-center space-x-3">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center text-lg font-bold ${
                getStepStatus(2) === 'completed' ? 'bg-green-500 text-white' :
                getStepStatus(2) === 'current' ? 'bg-blue-500 text-white' :
                'bg-gray-200 text-gray-600'
              }`}>
                {getStepStatus(2) === 'completed' ? <CheckCircle className="w-6 h-6" /> : '2'}
              </div>
              <div>
                <h3 className="text-xl font-bold">Download Windows Client</h3>
                <p className="text-sm text-muted-foreground font-normal">
                  Get our secure application that connects your MT5 to CopyArena
                </p>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg border border-gray-600/30">
              <div className="flex items-center space-x-4">
                <div className="p-3 bg-blue-500/20 rounded-full">
                  <Download className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <h4 className="font-semibold text-gray-100">CopyArenaClient.exe</h4>
                  <p className="text-sm text-gray-400">
                    Windows application • 37MB • No Python required
                  </p>
                </div>
              </div>
              <Button onClick={downloadClient} disabled={isLoading} className="flex items-center space-x-2">
                <Download className="w-4 h-4" />
                <span>Download</span>
              </Button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="p-3 bg-green-900/30 rounded-lg border border-green-500/30">
                <p className="text-sm text-green-300">
                  ✅ <strong>No Python</strong><br />
                  <span className="text-green-200">Everything included</span>
                </p>
              </div>
              <div className="p-3 bg-blue-900/30 rounded-lg border border-blue-500/30">
                <p className="text-sm text-blue-300">
                  🔒 <strong>Secure Auth</strong><br />
                  <span className="text-blue-200">Web-based login</span>
                </p>
              </div>
              <div className="p-3 bg-purple-900/30 rounded-lg border border-purple-500/30">
                <p className="text-sm text-purple-300">
                  ⚡ <strong>Easy Setup</strong><br />
                  <span className="text-purple-200">Just double-click</span>
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Step 3: Run & Connect */}
        <Card className={`border-2 backdrop-blur-sm ${
          getStepStatus(3) === 'completed' ? 'border-green-500/30 bg-green-900/20' :
          getStepStatus(3) === 'current' ? 'border-blue-500/30 bg-blue-900/20' :
          'border-gray-500/30 bg-gray-900/20'
        }`}>
          <CardHeader>
            <CardTitle className="flex items-center space-x-3">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center text-lg font-bold ${
                getStepStatus(3) === 'completed' ? 'bg-green-500 text-white' :
                getStepStatus(3) === 'current' ? 'bg-blue-500 text-white' :
                'bg-gray-200 text-gray-600'
              }`}>
                {getStepStatus(3) === 'completed' ? <CheckCircle className="w-6 h-6" /> : '3'}
              </div>
              <div>
                <h3 className="text-xl font-bold">Connect Your MT5</h3>
                <p className="text-sm text-muted-foreground font-normal">
                  Run the client and authenticate with your CopyArena credentials
                </p>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-600/30">
                <h4 className="font-semibold mb-3 flex items-center text-gray-100">
                  <Play className="w-4 h-4 mr-2 text-blue-400" />
                  Launch Steps:
                </h4>
                <ol className="space-y-2 text-sm text-gray-300">
                  <li className="flex items-start">
                    <span className="bg-blue-500/20 text-blue-300 rounded-full w-5 h-5 flex items-center justify-center text-xs mr-2 mt-0.5">1</span>
                    Double-click <code className="bg-gray-900/80 text-gray-100 px-1 rounded">CopyArenaClient.exe</code>
                  </li>
                  <li className="flex items-start">
                    <span className="bg-blue-500/20 text-blue-300 rounded-full w-5 h-5 flex items-center justify-center text-xs mr-2 mt-0.5">2</span>
                    Enter your CopyArena email & password
                  </li>
                  <li className="flex items-start">
                    <span className="bg-blue-500/20 text-blue-300 rounded-full w-5 h-5 flex items-center justify-center text-xs mr-2 mt-0.5">3</span>
                    Click "Connect to MT5"
                  </li>
                  <li className="flex items-start">
                    <span className="bg-blue-500/20 text-blue-300 rounded-full w-5 h-5 flex items-center justify-center text-xs mr-2 mt-0.5">4</span>
                    Start trading - data syncs automatically!
                  </li>
                </ol>
              </div>
              <div className="p-4 bg-amber-900/30 rounded-lg border border-amber-500/30">
                <h4 className="font-semibold mb-3 flex items-center text-amber-300">
                  <Settings className="w-4 h-4 mr-2" />
                  Requirements:
                </h4>
                <ul className="space-y-2 text-sm text-amber-200">
                  <li className="flex items-center">
                    <CheckCircle className="w-4 h-4 mr-2 text-amber-400" />
                    Windows 10/11 (64-bit)
                  </li>
                  <li className="flex items-center">
                    <CheckCircle className="w-4 h-4 mr-2 text-amber-400" />
                    MetaTrader 5 installed
                  </li>
                  <li className="flex items-center">
                    <CheckCircle className="w-4 h-4 mr-2 text-amber-400" />
                    Internet connection
                  </li>
                  <li className="flex items-center">
                    <CheckCircle className="w-4 h-4 mr-2 text-amber-400" />
                    CopyArena account
                  </li>
                </ul>
              </div>
            </div>
            
            {!isConnected && (
              <div className="bg-blue-900/30 p-4 rounded-lg border border-blue-500/30">
                <p className="text-sm text-blue-300">
                  💡 <strong>Pro Tip:</strong> Keep the Windows Client running while you trade to ensure real-time data synchronization with CopyArena.
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Step 4: Success */}
        {isConnected && (
          <Card className="border-2 border-green-500/30 bg-green-900/20 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-full bg-green-500 flex items-center justify-center">
                  <CheckCircle className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-green-400">Connected Successfully! 🎉</h3>
                  <p className="text-sm text-green-300 font-normal">
                    Your MT5 is now synchronized with CopyArena
                  </p>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-600/30">
                  <h4 className="font-semibold mb-2 text-green-300">Connection Details:</h4>
                  <div className="space-y-1 text-sm text-gray-300">
                    <p><strong className="text-gray-200">Account:</strong> {status?.login}</p>
                    <p><strong className="text-gray-200">Server:</strong> {status?.server}</p>
                    <p><strong className="text-gray-200">Last Sync:</strong> {status?.last_sync ? new Date(status.last_sync).toLocaleString() : 'Never'}</p>
                  </div>
                </div>
                <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-600/30">
                  <h4 className="font-semibold mb-2 text-green-300">What's Next:</h4>
                  <ul className="space-y-1 text-sm text-green-200">
                    <li>✅ Your trades appear automatically</li>
                    <li>✅ Real-time performance tracking</li>
                    <li>✅ Copy trading features enabled</li>
                    <li>✅ Analytics & reporting active</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Help Section */}
      <Card className="max-w-4xl mx-auto border-gray-500/30 bg-gray-900/20 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <ExternalLink className="w-5 h-5 text-blue-400" />
            <span className="text-gray-100">Need Help?</span>
          </CardTitle>
          <CardDescription className="text-gray-400">
            Having trouble with the setup? We're here to help!
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-4 border border-gray-600/30 bg-gray-800/50 rounded-lg">
              <div className="p-2 bg-blue-500/20 rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-3">
                <ExternalLink className="w-6 h-6 text-blue-400" />
              </div>
              <h4 className="font-semibold mb-2 text-gray-100">Documentation</h4>
              <p className="text-sm text-gray-400 mb-3">
                Detailed setup guides and troubleshooting
              </p>
              <Button variant="outline" size="sm">
                View Docs
              </Button>
            </div>
            <div className="text-center p-4 border border-gray-600/30 bg-gray-800/50 rounded-lg">
              <div className="p-2 bg-green-500/20 rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-3">
                <Users className="w-6 h-6 text-green-400" />
              </div>
              <h4 className="font-semibold mb-2 text-gray-100">Community</h4>
              <p className="text-sm text-gray-400 mb-3">
                Join our community for support and tips
              </p>
              <Button variant="outline" size="sm">
                Join Discord
              </Button>
            </div>
            <div className="text-center p-4 border border-gray-600/30 bg-gray-800/50 rounded-lg">
              <div className="p-2 bg-purple-500/20 rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-3">
                <AlertCircle className="w-6 h-6 text-purple-400" />
              </div>
              <h4 className="font-semibold mb-2 text-gray-100">Support</h4>
              <p className="text-sm text-gray-400 mb-3">
                Direct support for technical issues
              </p>
              <Button variant="outline" size="sm">
                Contact Support
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default MT5ConnectionPage