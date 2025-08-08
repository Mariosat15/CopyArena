import React from 'react' // eslint-disable-line @typescript-eslint/no-unused-vars
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import { useWebSocket } from './hooks/useWebSocket'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { DashboardPage } from './pages/DashboardPage'
import { MarketplacePage } from './pages/MarketplacePage'
import { LeaderboardPage } from './pages/LeaderboardPage'
import { ProfilePage } from './pages/ProfilePage'
import { ReportsPage } from './pages/ReportsPage'
import MT5ConnectionPage from './pages/MT5ConnectionPage'
import { Layout } from './components/Layout'
import { Toaster } from './components/ui/toaster'
import { useEffect, useState } from 'react'
import { sessionService } from './lib/sessionService'

function App() {
  const { user, initializeAuth } = useAuthStore()
  const [sessionInitialized, setSessionInitialized] = useState(false)
  
  // Initialize session and auth state on app load
  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Initialize session first
        await sessionService.initializeSession()
        setSessionInitialized(true)
        
        // Then initialize auth
        initializeAuth()
      } catch (error) {
        console.error('Failed to initialize app:', error)
        // Fallback to auth initialization even if session fails
        initializeAuth()
        setSessionInitialized(true)
      }
    }
    
    initializeApp()
  }, [initializeAuth])

  // Setup WebSocket connection for authenticated users
  useWebSocket(user?.id)

  // Show loading while session is initializing
  if (!sessionInitialized) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Initializing your trading session...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={!user ? <LoginPage /> : <Navigate to="/dashboard" />} />
        <Route path="/register" element={!user ? <RegisterPage /> : <Navigate to="/dashboard" />} />
        
        {/* Protected routes */}
        <Route path="/" element={user ? <Layout /> : <Navigate to="/login" />}>
          <Route index element={<Navigate to="/dashboard" />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="marketplace" element={<MarketplacePage />} />
          <Route path="leaderboard" element={<LeaderboardPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="mt5" element={<MT5ConnectionPage />} />
        </Route>
        
        {/* Fallback */}
        <Route path="*" element={<Navigate to={user ? "/dashboard" : "/login"} />} />
      </Routes>
      
      <Toaster />
    </div>
  )
}

export default App 