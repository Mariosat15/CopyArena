// @ts-ignore
import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { cn } from '../lib/utils'
import { 
  LayoutDashboard, 
  Users, 
  Trophy, 
  User, 
  FileText, 
  LogOut,
  Zap,
  Cable
} from 'lucide-react'
import { Button } from './ui/button'
import { Badge } from './ui/badge'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Marketplace', href: '/marketplace', icon: Users },
  { name: 'Leaderboard', href: '/leaderboard', icon: Trophy },
  { name: 'MT5 Connection', href: '/mt5', icon: Cable },
  { name: 'Profile', href: '/profile', icon: User },
  { name: 'Reports', href: '/reports', icon: FileText },
]

export function Sidebar() {
  const location = useLocation()
  const { user, logout } = useAuthStore()

  return (
    <div className="w-64 bg-card border-r border-border flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-border">
        <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
          <Zap className="h-8 w-8" />
          CopyArena
        </h1>
      </div>

      {/* User Info */}
      {user && (
        <div className="p-6 border-b border-border">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-primary rounded-full flex items-center justify-center">
              <span className="text-primary-foreground font-semibold">
                {user.username ? user.username.charAt(0).toUpperCase() : 'U'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user.username || 'Loading...'}</p>
                              <div className="flex items-center space-x-2 mt-1">
                  <Badge variant="secondary">Level {user.level ?? 1}</Badge>
                  <Badge variant="outline">{user.subscription_plan ?? 'free'}</Badge>
                </div>
            </div>
          </div>
          
          {/* XP and Credits */}
          <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">XP</p>
              <p className="font-semibold">{user.xp_points ? user.xp_points.toLocaleString() : '0'}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Credits</p>
              <p className="font-semibold">{user.credits ?? 0}</p>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href
          return (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                'flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent'
              )}
            >
              <item.icon className="h-5 w-5" />
              <span>{item.name}</span>
            </Link>
          )
        })}
      </nav>

      {/* Logout */}
      <div className="p-4 border-t border-border">
        <Button
          variant="ghost"
          className="w-full justify-start"
          onClick={logout}
        >
          <LogOut className="h-5 w-5 mr-3" />
          Logout
        </Button>
      </div>
    </div>
  )
} 