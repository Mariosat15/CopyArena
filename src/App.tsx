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
import { useEffect } from 'react'

function App() {
  const { user, initializeAuth } = useAuthStore()
  
  // Initialize auth state on app load
  useEffect(() => {
    initializeAuth()
  }, [initializeAuth])

  // Setup WebSocket connection for authenticated users
  useWebSocket(user?.id)

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