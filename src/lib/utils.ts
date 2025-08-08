import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

export function formatPercentage(value: number): string {
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date))
}

export function formatRelativeTime(date: string | Date): string {
  const now = new Date()
  const past = new Date(date)
  const diffInSeconds = (now.getTime() - past.getTime()) / 1000

  if (diffInSeconds < 60) {
    return 'Just now'
  } else if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60)
    return `${minutes} minute${minutes > 1 ? 's' : ''} ago`
  } else if (diffInSeconds < 86400) {
    const hours = Math.floor(diffInSeconds / 3600)
    return `${hours} hour${hours > 1 ? 's' : ''} ago`
  } else {
    const days = Math.floor(diffInSeconds / 86400)
    return `${days} day${days > 1 ? 's' : ''} ago`
  }
}

export function getXPForLevel(level: number): number {
  return level * level * 100
}

export function getProgressToNextLevel(currentXP: number, currentLevel: number): number {
  const currentLevelXP = getXPForLevel(currentLevel - 1)
  const nextLevelXP = getXPForLevel(currentLevel)
  return ((currentXP - currentLevelXP) / (nextLevelXP - currentLevelXP)) * 100
}

export function calculateRiskScore(trades: any[]): number {
  if (trades.length === 0) return 0
  
  const totalTrades = trades.length
  const lossingTrades = trades.filter(t => t.profit < 0).length
  const maxDrawdown = Math.min(...trades.map(t => t.profit))
  
  // Simple risk score calculation (0-100, lower is better)
  const lossRate = (lossingTrades / totalTrades) * 100
  const drawdownPenalty = Math.abs(maxDrawdown) / 100 // Normalize drawdown
  
  return Math.min(100, Math.round(lossRate + drawdownPenalty))
} 