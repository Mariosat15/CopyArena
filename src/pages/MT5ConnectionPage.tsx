import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import { useToast } from '../hooks/use-toast'
import { Activity, AlertCircle, CheckCircle, Settings, Wifi, WifiOff } from 'lucide-react'
import { api } from '../lib/api'

interface MT5Status {
  connected: boolean
  login?: number
  server?: string
  last_sync?: string
  message?: string
}

interface ConnectionForm {
  login: string
  password: string
  server: string
}

const MT5ConnectionPage: React.FC = () => {
  const [status, setStatus] = useState<MT5Status | null>(null)
  const [isConnecting, setIsConnecting] = useState(false)
  const [isSyncing, setIsSyncing] = useState(false)
  const [showConnectionForm, setShowConnectionForm] = useState(false)
  const [debugInfo, setDebugInfo] = useState<any>(null)
  const [isDebugging, setIsDebugging] = useState(false)
  const [tradeTestInfo, setTradeTestInfo] = useState<any>(null)
  const [isTestingTrades, setIsTestingTrades] = useState(false)
  const [isCleaningUp, setIsCleaningUp] = useState(false)
  const [connectionForm, setConnectionForm] = useState<ConnectionForm>({
    login: '',
    password: '',
    server: ''
  })
  const { toast } = useToast()

  // Load MT5 status on mount
  useEffect(() => {
    loadMT5Status()
    
    // Poll status every 30 seconds
    const interval = setInterval(loadMT5Status, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadMT5Status = async () => {
    try {
      const response = await api.get('/api/mt5/status')
      setStatus(response.data)
    } catch (error) {
      console.error('Error loading MT5 status:', error)
      toast({
        title: "Error",
        description: "Failed to load MT5 status",
        variant: "destructive"
      })
    }
  }

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsConnecting(true)

    try {
      const response = await api.post('/api/mt5/connect', {
        login: parseInt(connectionForm.login),
        password: connectionForm.password,
        server: connectionForm.server
      })

      toast({
        title: "Success",
        description: response.data.message,
        variant: "default"
      })

      setShowConnectionForm(false)
      setConnectionForm({ login: '', password: '', server: '' })
      
      // Reload status after a short delay
      setTimeout(loadMT5Status, 2000)
      
    } catch (error: any) {
      toast({
        title: "Connection Failed",
        description: error.response?.data?.detail || "Failed to connect to MT5",
        variant: "destructive"
      })
    } finally {
      setIsConnecting(false)
    }
  }

  const handleSync = async () => {
    setIsSyncing(true)

    try {
      const response = await api.post('/api/mt5/sync')
      
      toast({
        title: "Sync Started",
        description: response.data.message,
        variant: "default"
      })
      
      // Reload status after sync
      setTimeout(loadMT5Status, 3000)
      
    } catch (error: any) {
      toast({
        title: "Sync Failed",
        description: error.response?.data?.detail || "Failed to sync trades",
        variant: "destructive"
      })
    } finally {
      setIsSyncing(false)
    }
  }

  const handleDebug = async () => {
    setIsDebugging(true)

    try {
      const response = await api.get('/api/mt5/debug')
      setDebugInfo(response.data)
      
      toast({
        title: "Debug Info Retrieved",
        description: "Check the debug information below",
        variant: "default"
      })
      
    } catch (error: any) {
      toast({
        title: "Debug Failed",
        description: error.response?.data?.detail || "Failed to get debug info",
        variant: "destructive"
      })
    } finally {
      setIsDebugging(false)
    }
  }

  const handleTestTrades = async () => {
    setIsTestingTrades(true)

    try {
      const response = await api.get('/api/mt5/test-trades')
      setTradeTestInfo(response.data)
      
      toast({
        title: "Trade Test Completed",
        description: `Found ${response.data.positions_count || 0} positions and ${response.data.deals_count || 0} deals`,
        variant: "default"
      })
      
    } catch (error: any) {
      toast({
        title: "Trade Test Failed",
        description: error.response?.data?.detail || "Failed to test trades",
        variant: "destructive"
      })
    } finally {
      setIsTestingTrades(false)
    }
  }

  const handleCleanup = async () => {
    setIsCleaningUp(true)

    try {
      const response = await api.post('/api/mt5/cleanup')
      
      toast({
        title: "Cleanup Completed! 🧹",
        description: `${response.data.cleaned_trades} duplicate/orphaned trades cleaned`,
        variant: "default"
      })
      
      // Force refresh the frontend trade store
      const { useTradingStore } = await import('../stores/tradingStore')
      const { fetchTrades, removeDuplicateTrades } = useTradingStore.getState()
      
      // Refresh trades and remove duplicates
      await fetchTrades()
      setTimeout(() => removeDuplicateTrades(), 500)
      
      // Reload status after cleanup
      setTimeout(loadMT5Status, 2000)
      
    } catch (error: any) {
      toast({
        title: "Cleanup Failed",
        description: error.response?.data?.detail || "Failed to cleanup trades",
        variant: "destructive"
      })
    } finally {
      setIsCleaningUp(false)
    }
  }

  const getStatusIcon = () => {
    if (!status) return <AlertCircle className="h-5 w-5 text-gray-500" />
    return status.connected 
      ? <Wifi className="h-5 w-5 text-green-500" />
      : <WifiOff className="h-5 w-5 text-red-500" />
  }

  const getStatusBadge = () => {
    if (!status) return <Badge variant="secondary">Loading...</Badge>
    return status.connected 
      ? <Badge variant="online">Connected</Badge>
      : <Badge variant="offline">Disconnected</Badge>
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">MT5 Connection</h1>
        <p className="text-muted-foreground">
          Connect your MetaTrader 5 account to start real-time trading data sync
        </p>
      </div>

      {/* Connection Status Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {getStatusIcon()}
            Connection Status
          </CardTitle>
          <CardDescription>
            Current status of your MT5 connection
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Status:</span>
              {getStatusBadge()}
            </div>
            
            {status?.login && (
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Account:</span>
                <span className="text-sm text-muted-foreground">{status.login}</span>
              </div>
            )}
            
            {status?.server && (
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Server:</span>
                <span className="text-sm text-muted-foreground">{status.server}</span>
              </div>
            )}
            
            {status?.last_sync && (
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Last Sync:</span>
                <span className="text-sm text-muted-foreground">
                  {new Date(status.last_sync).toLocaleString()}
                </span>
              </div>
            )}

            {status?.message && !status.connected && (
              <div className="flex items-center gap-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                <AlertCircle className="h-4 w-4 text-yellow-600" />
                <span className="text-sm text-yellow-800 dark:text-yellow-200">
                  {status.message}
                </span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Connection Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Connection Setup
            </CardTitle>
            <CardDescription>
              Configure or update your MT5 connection
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!showConnectionForm ? (
              <Button 
                onClick={() => setShowConnectionForm(true)}
                className="w-full"
              >
                {status?.connected ? 'Update Connection' : 'Setup Connection'}
              </Button>
            ) : (
              <form onSubmit={handleConnect} className="space-y-4">
                <div>
                  <label className="text-sm font-medium">MT5 Login</label>
                  <Input
                    type="number"
                    placeholder="Enter your MT5 login number"
                    value={connectionForm.login}
                    onChange={(e) => setConnectionForm(prev => ({ ...prev, login: e.target.value }))}
                    required
                  />
                </div>
                
                <div>
                  <label className="text-sm font-medium">Password</label>
                  <Input
                    type="password"
                    placeholder="Enter your MT5 password"
                    value={connectionForm.password}
                    onChange={(e) => setConnectionForm(prev => ({ ...prev, password: e.target.value }))}
                    required
                  />
                </div>
                
                <div>
                  <label className="text-sm font-medium">Server</label>
                  <Input
                    type="text"
                    placeholder="e.g., MetaQuotes-Demo"
                    value={connectionForm.server}
                    onChange={(e) => setConnectionForm(prev => ({ ...prev, server: e.target.value }))}
                    required
                  />
                </div>
                
                <div className="flex gap-2">
                  <Button 
                    type="submit" 
                    disabled={isConnecting}
                    className="flex-1"
                  >
                    {isConnecting ? 'Connecting...' : 'Connect'}
                  </Button>
                  <Button 
                    type="button" 
                    variant="outline"
                    onClick={() => setShowConnectionForm(false)}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Trade Sync & Debug
            </CardTitle>
            <CardDescription>
              Manually sync your trading data and debug connection
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Button 
                onClick={handleSync}
                disabled={!status?.connected || isSyncing}
                className="w-full"
                variant={status?.connected ? "default" : "secondary"}
              >
                {isSyncing ? 'Syncing...' : 'Sync Trades'}
              </Button>
              
              <Button 
                onClick={handleDebug}
                disabled={isDebugging}
                className="w-full"
                variant="outline"
              >
                {isDebugging ? 'Getting Debug Info...' : 'Debug Connection'}
              </Button>
              
              <Button 
                onClick={handleTestTrades}
                disabled={isTestingTrades}
                className="w-full"
                variant="outline"
              >
                {isTestingTrades ? 'Testing Trades...' : 'Test Live Trades'}
              </Button>
              
              <Button 
                onClick={handleCleanup}
                disabled={isCleaningUp}
                className="w-full"
                variant="outline"
              >
                {isCleaningUp ? 'Cleaning Up...' : 'Cleanup Duplicate Trades'}
              </Button>
            </div>
            
            {!status?.connected && (
              <p className="text-sm text-muted-foreground mt-2">
                Connect your MT5 account first to enable sync
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Instructions */}
      <Card>
        <CardHeader>
          <CardTitle>How to Connect</CardTitle>
          <CardDescription>
            Follow these steps to connect your MT5 account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ol className="list-decimal list-inside space-y-2 text-sm">
            <li>Open your MetaTrader 5 terminal</li>
            <li>Note your account login number (visible in the top-left corner)</li>
            <li>Enter your login credentials in the form above</li>
            <li>Make sure your MT5 terminal is running for real-time updates</li>
            <li>Your trades will automatically sync every few minutes</li>
          </ol>
          
          <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-medium text-blue-800 dark:text-blue-200">
                Security Note
              </span>
            </div>
            <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
              Your credentials are encrypted and stored securely. We only read trading data - no trades are executed through our platform.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Debug Information */}
      {debugInfo && (
        <Card>
          <CardHeader>
            <CardTitle>Debug Information</CardTitle>
            <CardDescription>
              Technical details about MT5 connection
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium">MT5 Initialized:</span>
                  <Badge variant={debugInfo.mt5_initialized ? "online" : "offline"} className="ml-2">
                    {debugInfo.mt5_initialized ? "Yes" : "No"}
                  </Badge>
                </div>
                <div>
                  <span className="font-medium">Bridge Connected:</span>
                  <Badge variant={debugInfo.bridge_connected ? "online" : "offline"} className="ml-2">
                    {debugInfo.bridge_connected ? "Yes" : "No"}
                  </Badge>
                </div>
              </div>

              {debugInfo.account_info && (
                <div>
                  <h4 className="font-medium mb-2">Account Information:</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm bg-muted p-3 rounded">
                    <div>Login: {debugInfo.account_info.login}</div>
                    <div>Server: {debugInfo.account_info.server}</div>
                    <div>Balance: ${debugInfo.account_info.balance?.toFixed(2) || 'N/A'}</div>
                    <div>Equity: ${debugInfo.account_info.equity?.toFixed(2) || 'N/A'}</div>
                    <div>Currency: {debugInfo.account_info.currency || 'N/A'}</div>
                    <div>Positions: {debugInfo.positions_count}</div>
                  </div>
                </div>
              )}

              {debugInfo.error && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-red-600" />
                    <span className="font-medium text-red-800 dark:text-red-200">Error</span>
                  </div>
                  <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                    {debugInfo.error}
                  </p>
                </div>
              )}

              <Button 
                onClick={() => setDebugInfo(null)}
                variant="outline"
                size="sm"
              >
                Clear Debug Info
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Trade Test Results */}
      {tradeTestInfo && (
        <Card>
          <CardHeader>
            <CardTitle>Live Trade Test Results</CardTitle>
            <CardDescription>
              Direct trades fetched from your MT5 terminal
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium">Open Positions:</span>
                  <Badge variant="secondary" className="ml-2">
                    {tradeTestInfo.positions_count}
                  </Badge>
                </div>
                <div>
                  <span className="font-medium">Recent Deals:</span>
                  <Badge variant="secondary" className="ml-2">
                    {tradeTestInfo.deals_count}
                  </Badge>
                </div>
              </div>

              {tradeTestInfo.positions && tradeTestInfo.positions.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Open Positions:</h4>
                  <div className="space-y-2">
                    {tradeTestInfo.positions.map((pos: any, index: number) => (
                      <div key={index} className="p-3 bg-muted rounded border">
                        <div className="flex justify-between items-start">
                          <div>
                            <div className="font-medium">{pos.symbol} - {pos.type}</div>
                            <div className="text-sm text-muted-foreground">
                              Volume: {pos.volume} lots @ {pos.price_open}
                            </div>
                            <div className="text-sm text-muted-foreground">
                              Ticket: {pos.ticket}
                            </div>
                          </div>
                          <div className="text-right">
                            <div className={`font-medium ${pos.profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              ${pos.profit.toFixed(2)}
                            </div>
                            <div className="text-sm text-muted-foreground">
                              Current: {pos.price_current}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {tradeTestInfo.recent_deals && tradeTestInfo.recent_deals.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Recent Deals (Last 10):</h4>
                  <div className="space-y-2">
                    {tradeTestInfo.recent_deals.map((deal: any, index: number) => (
                      <div key={index} className="p-2 bg-muted rounded text-sm">
                        <div className="flex justify-between">
                          <span>{deal.symbol} {deal.type} {deal.volume}</span>
                          <span className={deal.profit >= 0 ? 'text-green-600' : 'text-red-600'}>
                            ${deal.profit.toFixed(2)}
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {new Date(deal.time).toLocaleString()} - Ticket: {deal.ticket}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {tradeTestInfo.error && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-red-600" />
                    <span className="font-medium text-red-800 dark:text-red-200">Error</span>
                  </div>
                  <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                    {tradeTestInfo.error}
                  </p>
                </div>
              )}

              <Button 
                onClick={() => setTradeTestInfo(null)}
                variant="outline"
                size="sm"
              >
                Clear Test Results
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default MT5ConnectionPage 