"""
Financial Intelligence Agent for Uplevel AI

This agent combines HubSpot revenue data with QuickBooks expense data to provide
comprehensive financial intelligence, P&L generation, and business forecasting.
"""

import asyncio
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from google.adk import Agent
from google.adk.memory import InMemoryMemoryService
from pydantic import BaseModel, Field
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinancialQuery(BaseModel):
    """Model for financial query requests"""
    query: str = Field(..., description="User's financial question")
    period: str = Field(default="current_month", description="Analysis period")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

class FinancialResponse(BaseModel):
    """Model for financial response"""
    answer: str = Field(..., description="Response to user query")
    data: Dict[str, Any] = Field(default_factory=dict, description="Supporting data")
    analysis: Dict[str, Any] = Field(default_factory=dict, description="Financial analysis")
    recommendations: List[str] = Field(default_factory=list, description="Action recommendations")

class ComprehensivePL(BaseModel):
    """Comprehensive P&L combining HubSpot and QuickBooks data"""
    period: str = Field(..., description="Reporting period")
    start_date: str = Field(..., description="Period start")
    end_date: str = Field(..., description="Period end")
    
    # Revenue (from HubSpot)
    total_revenue: float = Field(..., description="Total closed revenue")
    revenue_deals: int = Field(..., description="Number of closed deals")
    average_deal_size: float = Field(..., description="Average deal value")
    pipeline_value: float = Field(default=0.0, description="Pipeline forecast")
    
    # Expenses (from QuickBooks)
    total_expenses: float = Field(..., description="Total expenses")
    expense_count: int = Field(..., description="Number of expense transactions")
    
    # Profitability Analysis
    net_profit: float = Field(..., description="Net profit/loss")
    profit_margin: float = Field(..., description="Profit margin percentage")
    break_even_point: float = Field(..., description="Break-even revenue needed")
    
    # Forecast
    projected_revenue: float = Field(default=0.0, description="Projected revenue")
    projected_expenses: float = Field(default=0.0, description="Projected expenses")
    projected_profit: float = Field(default=0.0, description="Projected profit")
    
    generated_at: str = Field(..., description="Report generation timestamp")

class FinancialIntelligenceAgent:
    """AI Agent for financial intelligence and P&L analysis"""
    
    def __init__(
        self,
        hubspot_mcp_url: str = "http://localhost:8001",
        quickbooks_mcp_url: str = "http://localhost:8002"
    ):
        # Initialize base ADK agent
        self.agent = Agent(name="financial_intelligence_agent")
        
        # Configuration
        self.hubspot_mcp_url = hubspot_mcp_url
        self.quickbooks_mcp_url = quickbooks_mcp_url
        self.memory = InMemoryMemoryService()
        
        # HTTP client for MCP communication
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        logger.info("Financial Intelligence Agent initialized")
    
    @property
    def name(self) -> str:
        """Get agent name"""
        return self.agent.name if hasattr(self.agent, 'name') else "financial_intelligence_agent"
    
    async def handle_query(self, query: FinancialQuery) -> FinancialResponse:
        """Main query handler for financial questions"""
        
        try:
            # Classify query intent
            intent = self._classify_intent(query.query)
            logger.info(f"Classified query intent: {intent}")
            
            if intent == "generate_pl":
                return await self._handle_pl_request(query)
            elif intent == "forecast":
                return await self._handle_forecast_request(query)
            elif intent == "cost_analysis":
                return await self._handle_cost_analysis_request(query)
            elif intent == "revenue_analysis":
                return await self._handle_revenue_analysis_request(query)
            elif intent == "comparison":
                return await self._handle_comparison_request(query)
            else:
                return await self._handle_general_financial_query(query)
                
        except Exception as e:
            logger.error(f"Error handling query: {e}")
            return FinancialResponse(
                answer=f"I encountered an error processing your financial query: {str(e)}",
                data={},
                analysis={},
                recommendations=["Please check system connectivity and try again."]
            )
    
    async def _handle_pl_request(self, query: FinancialQuery) -> FinancialResponse:
        """Handle P&L statement generation requests"""
        
        try:
            # Generate comprehensive P&L
            pl_data = await self._generate_comprehensive_pl(query.period)
            
            # Store in memory for future reference
            memory_key = f"pl_{query.period}_{datetime.now().strftime('%Y%m%d')}"
            logger.info(f"Storing P&L data in memory with key: {memory_key}")
            
            # Create response
            answer = self._format_pl_response(pl_data)
            analysis = self._analyze_pl_performance(pl_data)
            recommendations = self._generate_pl_recommendations(pl_data)
            
            return FinancialResponse(
                answer=answer,
                data=pl_data.dict(),
                analysis=analysis,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error generating P&L: {e}")
            # Return a mock response for testing when MCP servers aren't running
            return FinancialResponse(
                answer=f"Unable to generate P&L statement: {str(e)}",
                data={},
                analysis={},
                recommendations=["Ensure HubSpot and QuickBooks MCP servers are running"]
            )
    
    async def _handle_forecast_request(self, query: FinancialQuery) -> FinancialResponse:
        """Handle forecasting requests"""
        
        try:
            # Get historical data (mock for testing)
            current_pl = await self._generate_mock_pl("current_month")
            last_month_pl = await self._generate_mock_pl("last_month", revenue=45000, expenses=28000)
            
            # Generate forecast
            forecast = self._generate_forecast(current_pl, last_month_pl, query.context.get("months", 3))
            answer = self._format_forecast_response(forecast)
            
            return FinancialResponse(
                answer=answer,
                data=forecast,
                analysis={"forecast_confidence": "medium", "trend": "stable"},
                recommendations=self._generate_forecast_recommendations(forecast)
            )
            
        except Exception as e:
            logger.error(f"Error generating forecast: {e}")
            return FinancialResponse(
                answer=f"Unable to generate forecast: {str(e)}",
                data={},
                analysis={},
                recommendations=["Check data connectivity and try again"]
            )
    
    async def _handle_cost_analysis_request(self, query: FinancialQuery) -> FinancialResponse:
        """Handle cost analysis requests"""
        
        # Mock response for testing
        expenses = {
            "total_expenses": 30000,
            "expense_count": 15,
            "period": query.period
        }
        
        analysis = self._analyze_cost_structure(expenses)
        answer = self._format_cost_analysis_response(analysis)
        
        return FinancialResponse(
            answer=answer,
            data=expenses,
            analysis=analysis,
            recommendations=self._generate_cost_recommendations(analysis)
        )
    
    async def _handle_revenue_analysis_request(self, query: FinancialQuery) -> FinancialResponse:
        """Handle revenue analysis requests"""
        
        # Mock response for testing
        revenue = {
            "total_revenue": 50000,
            "deal_count": 5,
            "pipeline_value": 75000,
            "period": query.period
        }
        
        analysis = self._analyze_revenue_performance(revenue)
        answer = self._format_revenue_analysis_response(analysis)
        
        return FinancialResponse(
            answer=answer,
            data=revenue,
            analysis=analysis,
            recommendations=self._generate_revenue_recommendations(analysis)
        )
    
    async def _handle_comparison_request(self, query: FinancialQuery) -> FinancialResponse:
        """Handle period comparison requests"""
        
        try:
            current_pl = await self._generate_mock_pl("current_month")
            last_month_pl = await self._generate_mock_pl("last_month", revenue=45000, expenses=28000)
            
            comparison = self._compare_periods(current_pl, last_month_pl)
            answer = self._format_comparison_response(comparison)
            
            return FinancialResponse(
                answer=answer,
                data=comparison,
                analysis=comparison["analysis"],
                recommendations=comparison["recommendations"]
            )
            
        except Exception as e:
            logger.error(f"Error in comparison: {e}")
            return FinancialResponse(
                answer=f"Unable to generate comparison: {str(e)}",
                data={},
                analysis={},
                recommendations=[]
            )
    
    async def _handle_general_financial_query(self, query: FinancialQuery) -> FinancialResponse:
        """Handle general financial questions"""
        
        answer = """I can help you with financial analysis and reporting. Here's what I can do:

📊 **P&L Statements**: Generate comprehensive profit & loss statements
📈 **Revenue Analysis**: Analyze sales performance and pipeline forecasts  
💰 **Cost Analysis**: Break down expenses and identify cost-saving opportunities
🔮 **Forecasting**: Predict future financial performance based on trends
📋 **Period Comparisons**: Compare financial performance across time periods

Try asking me:
- "Generate a P&L statement for this month"
- "What's our revenue forecast for next quarter?"
- "Analyze our cost structure"
- "Compare this month to last month"
"""
        
        return FinancialResponse(
            answer=answer,
            data={},
            analysis={},
            recommendations=[
                "Connect your HubSpot and QuickBooks accounts for complete analysis",
                "Review financial performance regularly",
                "Set up automated reporting"
            ]
        )
    
    async def _generate_comprehensive_pl(self, period: str) -> ComprehensivePL:
        """Generate comprehensive P&L combining HubSpot and QuickBooks data"""
        
        try:
            # Mock implementation for testing when MCP servers aren't available
            return await self._generate_mock_pl(period)
            
        except Exception as e:
            logger.error(f"Error generating P&L: {e}")
            raise
    
    async def _generate_mock_pl(self, period: str, revenue: float = 50000, expenses: float = 30000) -> ComprehensivePL:
        """Generate mock P&L for testing"""
        
        net_profit = revenue - expenses
        profit_margin = (net_profit / revenue * 100) if revenue > 0 else 0
        
        return ComprehensivePL(
            period=period,
            start_date="2024-01-01",
            end_date="2024-01-31",
            total_revenue=revenue,
            revenue_deals=5,
            average_deal_size=revenue / 5,
            pipeline_value=revenue * 1.5,
            total_expenses=expenses,
            expense_count=15,
            net_profit=net_profit,
            profit_margin=profit_margin,
            break_even_point=expenses,
            projected_revenue=revenue * 1.25,
            projected_expenses=expenses * 1.05,
            projected_profit=(revenue * 1.25) - (expenses * 1.05),
            generated_at=datetime.now().isoformat()
        )
    
    def _classify_intent(self, query: str) -> str:
        """Classify user query intent"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["p&l", "profit", "loss", "statement", "pl"]):
            return "generate_pl"
        elif any(word in query_lower for word in ["forecast", "predict", "future", "projection"]):
            return "forecast"
        elif any(word in query_lower for word in ["cost", "expense", "spending", "burn"]):
            return "cost_analysis"
        elif any(word in query_lower for word in ["revenue", "sales", "income", "deals"]):
            return "revenue_analysis"
        elif any(word in query_lower for word in ["compare", "comparison", "vs", "versus"]):
            return "comparison"
        else:
            return "general"
    
    def _format_pl_response(self, pl: ComprehensivePL) -> str:
        """Format P&L data into human-readable response"""
        
        return f"""## Profit & Loss Statement - {pl.period.title()}
**Period**: {pl.start_date} to {pl.end_date}

### 💰 Revenue
- **Total Revenue**: ${pl.total_revenue:,.2f}
- **Deals Closed**: {pl.revenue_deals}
- **Average Deal Size**: ${pl.average_deal_size:,.2f}
- **Pipeline Value**: ${pl.pipeline_value:,.2f}

### 💸 Expenses  
- **Total Expenses**: ${pl.total_expenses:,.2f}
- **Expense Transactions**: {pl.expense_count}

### 📊 Profitability
- **Net Profit**: ${pl.net_profit:,.2f}
- **Profit Margin**: {pl.profit_margin:.1f}%
- **Break-even Point**: ${pl.break_even_point:,.2f}

### 🔮 Forecast
- **Projected Revenue**: ${pl.projected_revenue:,.2f}
- **Projected Expenses**: ${pl.projected_expenses:,.2f}
- **Projected Profit**: ${pl.projected_profit:,.2f}

*Report generated: {datetime.fromisoformat(pl.generated_at).strftime('%Y-%m-%d %H:%M')}*
"""
    
    def _analyze_pl_performance(self, pl: ComprehensivePL) -> Dict[str, Any]:
        """Analyze P&L performance"""
        
        return {
            "profitability": "profitable" if pl.net_profit > 0 else "loss-making",
            "margin_health": "excellent" if pl.profit_margin > 30 else "good" if pl.profit_margin > 15 else "concerning",
            "revenue_per_deal": pl.average_deal_size,
            "expense_ratio": pl.total_expenses / pl.total_revenue if pl.total_revenue > 0 else 0,
            "growth_potential": pl.pipeline_value / pl.total_revenue if pl.total_revenue > 0 else 0
        }
    
    def _generate_pl_recommendations(self, pl: ComprehensivePL) -> List[str]:
        """Generate actionable recommendations based on P&L"""
        
        recommendations = []
        
        if pl.net_profit < 0:
            recommendations.append("🚨 Focus on reducing expenses or increasing revenue to achieve profitability")
        
        if pl.profit_margin < 15:
            recommendations.append("📊 Consider optimizing pricing strategy or reducing operational costs")
        
        if pl.pipeline_value > pl.total_revenue:
            recommendations.append("🎯 Strong pipeline! Focus on deal closure and conversion optimization")
        
        if pl.expense_count > pl.revenue_deals * 5:
            recommendations.append("💰 High expense frequency - consider expense consolidation opportunities")
        
        recommendations.append("📈 Schedule monthly P&L reviews to track performance trends")
        
        return recommendations
    
    def _generate_forecast(self, current: ComprehensivePL, previous: ComprehensivePL, months: int) -> Dict[str, Any]:
        """Generate financial forecast"""
        
        # Calculate growth rates
        revenue_growth = (current.total_revenue - previous.total_revenue) / previous.total_revenue if previous.total_revenue > 0 else 0
        expense_growth = (current.total_expenses - previous.total_expenses) / previous.total_expenses if previous.total_expenses > 0 else 0
        
        # Project future performance
        forecast_periods = []
        base_revenue = current.total_revenue
        base_expenses = current.total_expenses
        
        for month in range(1, months + 1):
            projected_revenue = base_revenue * (1 + revenue_growth) ** month
            projected_expenses = base_expenses * (1 + expense_growth) ** month
            projected_profit = projected_revenue - projected_expenses
            
            forecast_periods.append({
                "month": month,
                "revenue": projected_revenue,
                "expenses": projected_expenses,
                "profit": projected_profit,
                "margin": projected_profit / projected_revenue * 100 if projected_revenue > 0 else 0
            })
        
        return {
            "periods": forecast_periods,
            "revenue_growth_rate": revenue_growth,
            "expense_growth_rate": expense_growth,
            "break_even_month": self._calculate_break_even_month(forecast_periods)
        }
    
    def _calculate_break_even_month(self, periods: List[Dict]) -> Optional[int]:
        """Calculate when the company will break even"""
        for period in periods:
            if period["profit"] > 0:
                return period["month"]
        return None
    
    def _format_forecast_response(self, forecast: Dict[str, Any]) -> str:
        """Format forecast into readable response"""
        
        response = "## Financial Forecast\n\n"
        
        for period in forecast["periods"]:
            response += f"**Month {period['month']}**:\n"
            response += f"- Revenue: ${period['revenue']:,.2f}\n"
            response += f"- Expenses: ${period['expenses']:,.2f}\n"
            response += f"- Profit: ${period['profit']:,.2f}\n"
            response += f"- Margin: {period['margin']:.1f}%\n\n"
        
        if forecast.get("break_even_month"):
            response += f"🎯 **Break-even projected**: Month {forecast['break_even_month']}\n"
        
        return response
    
    def _analyze_cost_structure(self, expenses: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze cost structure"""
        return {
            "total_expenses": expenses.get("total_expenses", 0),
            "expense_count": expenses.get("expense_count", 0),
            "average_expense": expenses.get("total_expenses", 0) / max(expenses.get("expense_count", 1), 1)
        }
    
    def _format_cost_analysis_response(self, analysis: Dict[str, Any]) -> str:
        """Format cost analysis response"""
        return f"""## Cost Structure Analysis

**Total Expenses**: ${analysis['total_expenses']:,.2f}
**Number of Transactions**: {analysis['expense_count']}
**Average Transaction**: ${analysis['average_expense']:,.2f}
"""
    
    def _generate_cost_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate cost reduction recommendations"""
        return [
            "Review high-value expense categories for optimization opportunities",
            "Implement expense approval workflows for better control",
            "Consider vendor consolidation to negotiate better rates"
        ]
    
    def _analyze_revenue_performance(self, revenue: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze revenue performance"""
        return {
            "total_revenue": revenue.get("total_revenue", 0),
            "deal_count": revenue.get("deal_count", 0),
            "pipeline_strength": revenue.get("pipeline_value", 0) / max(revenue.get("total_revenue", 1), 1)
        }
    
    def _format_revenue_analysis_response(self, analysis: Dict[str, Any]) -> str:
        """Format revenue analysis response"""
        return f"""## Revenue Performance Analysis

**Total Revenue**: ${analysis['total_revenue']:,.2f}
**Deals Closed**: {analysis['deal_count']}
**Pipeline Strength**: {analysis['pipeline_strength']:.1f}x current revenue
"""
    
    def _generate_revenue_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate revenue optimization recommendations"""
        return [
            "Focus on converting pipeline opportunities",
            "Analyze top-performing sales channels",
            "Implement customer success programs to increase retention"
        ]
    
    def _compare_periods(self, current: ComprehensivePL, previous: ComprehensivePL) -> Dict[str, Any]:
        """Compare financial performance between periods"""
        
        revenue_change = current.total_revenue - previous.total_revenue
        revenue_change_pct = revenue_change / previous.total_revenue * 100 if previous.total_revenue > 0 else 0
        
        expense_change = current.total_expenses - previous.total_expenses
        expense_change_pct = expense_change / previous.total_expenses * 100 if previous.total_expenses > 0 else 0
        
        profit_change = current.net_profit - previous.net_profit
        
        return {
            "revenue_change": revenue_change,
            "revenue_change_pct": revenue_change_pct,
            "expense_change": expense_change,
            "expense_change_pct": expense_change_pct,
            "profit_change": profit_change,
            "analysis": {
                "revenue_trend": "growing" if revenue_change > 0 else "declining",
                "expense_trend": "increasing" if expense_change > 0 else "decreasing",
                "profitability_trend": "improving" if profit_change > 0 else "declining"
            },
            "recommendations": self._generate_comparison_recommendations(revenue_change_pct, expense_change_pct, profit_change)
        }
    
    def _format_comparison_response(self, comparison: Dict[str, Any]) -> str:
        """Format period comparison response"""
        
        return f"""## Period Comparison

**Revenue Change**: ${comparison['revenue_change']:,.2f} ({comparison['revenue_change_pct']:+.1f}%)
**Expense Change**: ${comparison['expense_change']:,.2f} ({comparison['expense_change_pct']:+.1f}%)
**Profit Change**: ${comparison['profit_change']:,.2f}

### Trends
- Revenue: {comparison['analysis']['revenue_trend']}
- Expenses: {comparison['analysis']['expense_trend']}
- Profitability: {comparison['analysis']['profitability_trend']}
"""
    
    def _generate_comparison_recommendations(self, revenue_pct: float, expense_pct: float, profit_change: float) -> List[str]:
        """Generate recommendations based on period comparison"""
        
        recommendations = []
        
        if revenue_pct < 0:
            recommendations.append("🔍 Investigate revenue decline and implement recovery strategies")
        elif revenue_pct > 20:
            recommendations.append("🚀 Excellent revenue growth! Consider scaling successful strategies")
        
        if expense_pct > revenue_pct:
            recommendations.append("⚠️ Expenses growing faster than revenue - review cost structure")
        
        if profit_change < 0:
            recommendations.append("📉 Declining profitability - focus on margin improvement")
        
        return recommendations
    
    def _generate_forecast_recommendations(self, forecast: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on forecast"""
        
        recommendations = []
        
        if forecast.get("break_even_month"):
            recommendations.append(f"🎯 Maintain current trajectory to reach break-even by month {forecast['break_even_month']}")
        else:
            recommendations.append("🚨 Forecast shows continued losses - immediate action required")
        
        if forecast.get("revenue_growth_rate", 0) < 0:
            recommendations.append("📈 Focus on revenue growth initiatives to reverse declining trend")
        
        return recommendations

# Factory function for easy integration
def create_financial_intelligence_agent(
    hubspot_mcp_url: str = "http://localhost:8001",
    quickbooks_mcp_url: str = "http://localhost:8002"
) -> FinancialIntelligenceAgent:
    """Create and configure Financial Intelligence Agent"""
    return FinancialIntelligenceAgent(hubspot_mcp_url, quickbooks_mcp_url)

if __name__ == "__main__":
    # Development testing
    async def test_agent():
        agent = create_financial_intelligence_agent()
        
        test_query = FinancialQuery(
            query="Generate a P&L statement for this month",
            period="current_month"
        )
        
        response = await agent.handle_query(test_query)
        print(response.answer)
    
    asyncio.run(test_agent())
