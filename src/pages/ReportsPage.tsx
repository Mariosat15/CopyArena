import React, { useState } from 'react'
import { useAuthStore } from '../stores/authStore'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Brain, FileText, CreditCard, TrendingUp, Users, Target } from 'lucide-react'
import { toast } from '../hooks/use-toast'

export function ReportsPage() {
  const { user } = useAuthStore()
  const [isGenerating, setIsGenerating] = useState(false)

  const reportTypes = [
    {
      id: 'trader_analysis',
      name: 'Trader Performance Analysis',
      description: 'Deep dive into a trader\'s performance, risk metrics, and strategy consistency',
      icon: TrendingUp,
      cost: 2,
      color: 'bg-blue-500'
    },
    {
      id: 'risk_assessment',
      name: 'Risk-Reward Analysis',
      description: 'Comprehensive risk evaluation and drawdown analysis',
      icon: Target,
      cost: 1,
      color: 'bg-red-500'
    },
    {
      id: 'strategy_comparison',
      name: 'Strategy Comparison',
      description: 'Compare multiple traders and their trading strategies',
      icon: Users,
      cost: 3,
      color: 'bg-green-500'
    },
    {
      id: 'market_correlation',
      name: 'Market Correlation Report',
      description: 'Analyze how trading performance correlates with market conditions',
      icon: Brain,
      cost: 2,
      color: 'bg-purple-500'
    }
  ]

  const generateReport = async (reportType: string, cost: number) => {
    if (!user) return

    if (user.credits < cost) {
      toast({
        title: "Insufficient Credits",
        description: `You need ${cost} credits to generate this report. Buy more credits to continue.`,
        variant: "destructive"
      })
      return
    }

    setIsGenerating(true)
    try {
      // TODO: Implement AI report generation for ${reportType}
      console.log(`Generating report: ${reportType}`)
      await new Promise(resolve => setTimeout(resolve, 3000)) // Simulate API call
      
      toast({
        title: "Report Generated!",
        description: "Your AI report has been generated successfully.",
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to generate report. Please try again.",
        variant: "destructive"
      })
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">AI Reports</h1>
        <p className="text-muted-foreground">
          Generate powerful AI-driven insights about trading performance and strategies.
        </p>
      </div>

      {/* Credits Info */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <CreditCard className="h-8 w-8 text-primary" />
              <div>
                <h3 className="text-lg font-semibold">Available Credits</h3>
                <p className="text-muted-foreground">Use credits to generate AI reports</p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold">{user?.credits || 0}</div>
              <Button variant="outline" size="sm" className="mt-2">
                Buy More Credits
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Report Types */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {reportTypes.map((report) => (
          <Card key={report.id} className="relative">
            <CardHeader>
              <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-lg ${report.color}`}>
                  <report.icon className="h-6 w-6 text-white" />
                </div>
                <div className="flex-1">
                  <CardTitle className="text-lg">{report.name}</CardTitle>
                  <div className="flex items-center space-x-2 mt-1">
                    <Badge variant="outline">{report.cost} credits</Badge>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground mb-4">{report.description}</p>
              
              <Button 
                className="w-full" 
                onClick={() => generateReport(report.id, report.cost)}
                disabled={isGenerating || (user?.credits || 0) < report.cost}
              >
                <Brain className="h-4 w-4 mr-2" />
                {isGenerating ? 'Generating...' : 'Generate Report'}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Recent Reports */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <FileText className="h-5 w-5" />
            <span>Recent Reports</span>
          </CardTitle>
          <CardDescription>Your previously generated AI reports</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Placeholder for recent reports */}
            <div className="text-center py-8">
              <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No reports yet</h3>
              <p className="text-muted-foreground">
                Generate your first AI report to see insights here.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* How It Works */}
      <Card>
        <CardHeader>
          <CardTitle>How AI Reports Work</CardTitle>
          <CardDescription>Understand what our AI analyzes for you</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <Brain className="h-8 w-8 text-primary mx-auto mb-3" />
              <h4 className="font-semibold mb-2">AI Analysis</h4>
              <p className="text-sm text-muted-foreground">
                Our AI processes thousands of data points from trading history
              </p>
            </div>
            <div className="text-center">
              <TrendingUp className="h-8 w-8 text-primary mx-auto mb-3" />
              <h4 className="font-semibold mb-2">Performance Insights</h4>
              <p className="text-sm text-muted-foreground">
                Get detailed analysis of risk, returns, and strategy effectiveness
              </p>
            </div>
            <div className="text-center">
              <FileText className="h-8 w-8 text-primary mx-auto mb-3" />
              <h4 className="font-semibold mb-2">Actionable Reports</h4>
              <p className="text-sm text-muted-foreground">
                Receive clear, actionable insights to improve your trading
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
} 