import React from 'react'
import { useAuthStore } from '../stores/authStore'
import { Button } from './ui/button'

import { Bell, Settings, CreditCard } from 'lucide-react'

export function Header() {
  const { user } = useAuthStore()

  const handleUpgrade = () => {
    // TODO: Open subscription modal
    console.log('Open subscription modal')
  }

  const handleBuyCredits = () => {
    // TODO: Open credits purchase modal
    console.log('Open credits modal')
  }

  return (
    <header className="border-b border-border bg-card px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-status-online rounded-full"></div>
            <span className="text-sm text-muted-foreground">Online</span>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {/* Subscription Status */}
          {user?.subscription_plan === 'free' && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleUpgrade}
              className="text-primary border-primary hover:bg-primary hover:text-primary-foreground"
            >
              Upgrade to Pro
            </Button>
          )}

          {/* Credits */}
          <div className="flex items-center space-x-2">
            <CreditCard className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">{user?.credits || 0} credits</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleBuyCredits}
              className="text-xs"
            >
              Buy More
            </Button>
          </div>

          {/* Notifications */}
          <Button variant="ghost" size="icon">
            <Bell className="h-5 w-5" />
          </Button>

          {/* Settings */}
          <Button variant="ghost" size="icon">
            <Settings className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  )
} 