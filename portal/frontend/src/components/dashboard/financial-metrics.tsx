"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  PieChart,
  BarChart3,
  Activity
} from "lucide-react"

export function FinancialMetrics() {
  // Mock data for demonstration
  const metrics = [
    {
      title: "Total Revenue",
      value: "$45,231",
      change: "+20.1%",
      trend: "up",
      icon: DollarSign,
      description: "from last month"
    },
    {
      title: "Net Profit",
      value: "$12,234",
      change: "+12.5%",
      trend: "up", 
      icon: TrendingUp,
      description: "from last month"
    },
    {
      title: "Operating Expenses",
      value: "$32,997",
      change: "-3.2%",
      trend: "down",
      icon: PieChart,
      description: "from last month"
    },
    {
      title: "Cash Flow",
      value: "$8,945",
      change: "+8.7%",
      trend: "up",
      icon: Activity,
      description: "from last month"
    }
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Financial Overview</h2>
        <Badge variant="outline">Demo Data</Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((metric) => {
          const IconComponent = metric.icon
          const isPositive = metric.trend === "up"
          
          return (
            <Card key={metric.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {metric.title}
                </CardTitle>
                <IconComponent className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{metric.value}</div>
                <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                  {isPositive ? (
                    <TrendingUp className="h-3 w-3 text-green-500" />
                  ) : (
                    <TrendingDown className="h-3 w-3 text-red-500" />
                  )}
                  <span className={isPositive ? "text-green-500" : "text-red-500"}>
                    {metric.change}
                  </span>
                  <span>{metric.description}</span>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <BarChart3 className="h-5 w-5" />
            <span>Quick Financial Insights</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
            <h4 className="font-semibold text-blue-900">Revenue Growth</h4>
            <p className="text-sm text-blue-700">
              Your revenue has increased by 20.1% this month, indicating strong business performance.
            </p>
          </div>
          <div className="p-4 bg-green-50 rounded-lg border border-green-200">
            <h4 className="font-semibold text-green-900">Cost Optimization</h4>
            <p className="text-sm text-green-700">
              Operating expenses decreased by 3.2%, showing improved operational efficiency.
            </p>
          </div>
          <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
            <h4 className="font-semibold text-amber-900">AI Recommendation</h4>
            <p className="text-sm text-amber-700">
              Consider investing surplus cash flow into growth initiatives to maintain momentum.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Connect Your Data Sources</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground mb-4">
            This dashboard shows demo data. Connect your real financial data sources for accurate insights:
          </p>
          <div className="space-y-2">
            <Badge variant="outline">🔗 HubSpot Integration</Badge>
            <Badge variant="outline">📊 QuickBooks Integration</Badge>
            <Badge variant="outline">💳 Bank Account Sync</Badge>
            <Badge variant="outline">📈 Advanced Analytics</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
