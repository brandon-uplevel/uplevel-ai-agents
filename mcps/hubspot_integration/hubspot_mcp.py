"""
HubSpot MCP Integration for Uplevel AI Financial Intelligence Agent

This module provides a Model Context Protocol server for HubSpot API integration,
enabling extraction of deals, revenue data, and contact information for P&L generation.
"""

import asyncio
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
from hubspot import HubSpot
from hubspot.crm.deals import ApiException as DealsApiException
from hubspot.crm.contacts import ApiException as ContactsApiException
from mcp.server.fastmcp import FastMCP
import mcp.types as types
from pydantic import BaseModel, Field
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HubSpotDeal(BaseModel):
    """Data model for HubSpot deals"""
    deal_id: str = Field(..., description="HubSpot deal ID")
    deal_name: str = Field(..., description="Deal name/title")
    amount: float = Field(default=0.0, description="Deal amount in USD")
    close_date: Optional[str] = Field(None, description="Deal close date")
    deal_stage: str = Field(..., description="Current deal stage")
    pipeline: str = Field(default="default", description="Sales pipeline")
    owner_id: Optional[str] = Field(None, description="Deal owner ID")
    created_date: str = Field(..., description="Deal creation date")

class HubSpotContact(BaseModel):
    """Data model for HubSpot contacts"""
    contact_id: str = Field(..., description="HubSpot contact ID")
    email: str = Field(..., description="Contact email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    company: Optional[str] = Field(None, description="Company name")

class RevenueReport(BaseModel):
    """Revenue analysis report"""
    period: str = Field(..., description="Reporting period")
    total_revenue: float = Field(..., description="Total closed-won revenue")
    deal_count: int = Field(..., description="Number of closed deals")
    average_deal_size: float = Field(..., description="Average deal value")
    pipeline_value: float = Field(..., description="Current pipeline value")
    closed_deals: List[HubSpotDeal] = Field(default_factory=list)

class HubSpotMCPServer:
    """HubSpot MCP Server for financial intelligence"""
    
    def __init__(self, access_token: str = None):
        self.access_token = access_token or os.getenv("HUBSPOT_ACCESS_TOKEN")
        if not self.access_token:
            raise ValueError("HubSpot access token not provided")
            
        self.api_client = HubSpot(access_token=self.access_token)
        self.mcp = FastMCP("HubSpot MCP Server")
        self._setup_tools()
        
    def _setup_tools(self):
        """Register MCP tools"""
        
        @self.mcp.tool()
        async def get_closed_deals(
            date_range: str = "current_month",
            amount_gte: float = 0.0
        ) -> Dict[str, Any]:
            """
            Fetch closed-won deals for revenue calculation
            
            Args:
                date_range: Period to analyze (current_month, last_month, last_quarter, ytd)
                amount_gte: Minimum deal amount filter
            """
            try:
                start_date, end_date = self._parse_date_range(date_range)
                deals = await self._fetch_deals_by_criteria(
                    deal_stage="closedwon",
                    start_date=start_date,
                    end_date=end_date,
                    amount_gte=amount_gte
                )
                
                total_revenue = sum(deal.amount for deal in deals)
                avg_deal_size = total_revenue / len(deals) if deals else 0
                
                return {
                    "success": True,
                    "data": {
                        "period": date_range,
                        "total_revenue": total_revenue,
                        "deal_count": len(deals),
                        "average_deal_size": avg_deal_size,
                        "deals": [deal.dict() for deal in deals]
                    }
                }
            except Exception as e:
                logger.error(f"Error fetching closed deals: {e}")
                return {"success": False, "error": str(e)}
        
        @self.mcp.tool()
        async def get_pipeline_value(pipeline_id: str = "default") -> Dict[str, Any]:
            """
            Calculate current pipeline value for forecasting
            
            Args:
                pipeline_id: HubSpot pipeline ID (default uses default pipeline)
            """
            try:
                deals = await self._fetch_deals_by_criteria(
                    deal_stage="open",
                    pipeline_id=pipeline_id
                )
                
                pipeline_value = sum(deal.amount for deal in deals)
                weighted_value = sum(
                    deal.amount * self._get_stage_probability(deal.deal_stage)
                    for deal in deals
                )
                
                return {
                    "success": True,
                    "data": {
                        "pipeline_value": pipeline_value,
                        "weighted_value": weighted_value,
                        "deal_count": len(deals),
                        "deals": [deal.dict() for deal in deals]
                    }
                }
            except Exception as e:
                logger.error(f"Error calculating pipeline value: {e}")
                return {"success": False, "error": str(e)}
        
        @self.mcp.tool()
        async def generate_revenue_report(
            period: str = "current_month",
            include_pipeline: bool = True
        ) -> Dict[str, Any]:
            """
            Generate comprehensive revenue report for P&L analysis
            
            Args:
                period: Reporting period
                include_pipeline: Whether to include pipeline forecasting
            """
            try:
                # Get closed deals for actual revenue
                closed_deals_response = await get_closed_deals(period)
                if not closed_deals_response["success"]:
                    return closed_deals_response
                
                closed_data = closed_deals_response["data"]
                
                # Optionally get pipeline data
                pipeline_data = {}
                if include_pipeline:
                    pipeline_response = await get_pipeline_value()
                    if pipeline_response["success"]:
                        pipeline_data = pipeline_response["data"]
                
                report = RevenueReport(
                    period=period,
                    total_revenue=closed_data["total_revenue"],
                    deal_count=closed_data["deal_count"],
                    average_deal_size=closed_data["average_deal_size"],
                    pipeline_value=pipeline_data.get("pipeline_value", 0),
                    closed_deals=[HubSpotDeal(**deal) for deal in closed_data["deals"]]
                )
                
                return {
                    "success": True,
                    "data": report.dict(),
                    "generated_at": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error generating revenue report: {e}")
                return {"success": False, "error": str(e)}
    
    async def _fetch_deals_by_criteria(
        self, 
        deal_stage: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        amount_gte: float = 0.0,
        pipeline_id: str = None
    ) -> List[HubSpotDeal]:
        """Fetch deals matching specific criteria"""
        
        try:
            deals_api = self.api_client.crm.deals
            
            # Build properties to fetch
            properties = [
                "dealname", "amount", "closedate", "dealstage",
                "pipeline", "hubspot_owner_id", "createdate"
            ]
            
            # Build filters
            filters = []
            
            if deal_stage:
                if deal_stage == "open":
                    # Open deals (not closed-won or closed-lost)
                    filters.extend([
                        {"propertyName": "dealstage", "operator": "NEQ", "value": "closedwon"},
                        {"propertyName": "dealstage", "operator": "NEQ", "value": "closedlost"}
                    ])
                else:
                    filters.append({
                        "propertyName": "dealstage",
                        "operator": "EQ",
                        "value": deal_stage
                    })
            
            if start_date:
                filters.append({
                    "propertyName": "closedate",
                    "operator": "GTE",
                    "value": int(start_date.timestamp() * 1000)
                })
            
            if end_date:
                filters.append({
                    "propertyName": "closedate",
                    "operator": "LTE", 
                    "value": int(end_date.timestamp() * 1000)
                })
            
            if amount_gte > 0:
                filters.append({
                    "propertyName": "amount",
                    "operator": "GTE",
                    "value": str(amount_gte)
                })
            
            # Search request
            search_request = {
                "properties": properties,
                "limit": 100,
                "after": 0
            }
            
            if filters:
                search_request["filterGroups"] = [{"filters": filters}]
            
            # Execute search with pagination
            all_deals = []
            after = 0
            
            while True:
                search_request["after"] = after
                
                try:
                    response = deals_api.search_api.do_search(
                        public_object_search_request=search_request
                    )
                    
                    # Process results
                    for result in response.results:
                        deal_data = self._process_deal_properties(result.properties)
                        if deal_data:
                            all_deals.append(HubSpotDeal(**deal_data))
                    
                    # Check for more pages
                    if not hasattr(response, 'paging') or not response.paging:
                        break
                    
                    after = response.paging.next.after if response.paging.next else None
                    if not after:
                        break
                        
                except DealsApiException as e:
                    logger.error(f"HubSpot API error: {e}")
                    break
                    
                # Rate limiting
                await asyncio.sleep(0.1)
            
            logger.info(f"Retrieved {len(all_deals)} deals")
            return all_deals
            
        except Exception as e:
            logger.error(f"Error fetching deals: {e}")
            return []
    
    def _process_deal_properties(self, properties: Dict) -> Optional[Dict]:
        """Process raw HubSpot deal properties into clean data"""
        
        try:
            # Extract and clean deal data
            deal_data = {
                "deal_id": properties.get("hs_object_id", ""),
                "deal_name": properties.get("dealname", "Unnamed Deal"),
                "amount": float(properties.get("amount", "0") or "0"),
                "close_date": properties.get("closedate"),
                "deal_stage": properties.get("dealstage", "unknown"),
                "pipeline": properties.get("pipeline", "default"),
                "owner_id": properties.get("hubspot_owner_id"),
                "created_date": properties.get("createdate", "")
            }
            
            return deal_data
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Error processing deal properties: {e}")
            return None
    
    def _parse_date_range(self, date_range: str) -> tuple[datetime, datetime]:
        """Parse date range string into start and end dates"""
        
        now = datetime.now()
        
        if date_range == "current_month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Next month, day 1, minus 1 day = last day of current month
            next_month = start_date.replace(month=start_date.month + 1) if start_date.month < 12 else start_date.replace(year=start_date.year + 1, month=1)
            end_date = next_month - timedelta(days=1)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        elif date_range == "last_month":
            # First day of current month
            first_current = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Last day of previous month
            end_date = first_current - timedelta(days=1)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            # First day of previous month
            start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        elif date_range == "last_quarter":
            # Calculate last complete quarter
            current_quarter = (now.month - 1) // 3 + 1
            if current_quarter == 1:
                # Last quarter of previous year
                start_date = datetime(now.year - 1, 10, 1, 0, 0, 0)
                end_date = datetime(now.year - 1, 12, 31, 23, 59, 59, 999999)
            else:
                quarter_start_month = (current_quarter - 2) * 3 + 1
                start_date = datetime(now.year, quarter_start_month, 1, 0, 0, 0)
                end_date = datetime(now.year, quarter_start_month + 2, 1, 0, 0, 0) + timedelta(days=32)
                end_date = end_date.replace(day=1) - timedelta(days=1)
                end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        elif date_range == "ytd":
            start_date = datetime(now.year, 1, 1, 0, 0, 0)
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        else:
            # Default to current month
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = start_date.replace(month=start_date.month + 1) if start_date.month < 12 else start_date.replace(year=start_date.year + 1, month=1)
            end_date = next_month - timedelta(days=1)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return start_date, end_date
    
    def _get_stage_probability(self, stage: str) -> float:
        """Get probability multiplier for deal stages (for weighted pipeline)"""
        
        stage_probabilities = {
            "appointmentscheduled": 0.1,
            "qualifiedtobuy": 0.25,
            "presentationscheduled": 0.4,
            "decisionmakerboughtin": 0.6,
            "contractsent": 0.8,
            "closedwon": 1.0,
            "closedlost": 0.0
        }
        
        return stage_probabilities.get(stage.lower(), 0.3)  # Default 30%

    def get_mcp_app(self):
        """Get the MCP application for deployment"""
        return self.mcp

    def run(self, host: str = "localhost", port: int = 8001):
        """Run the HubSpot MCP server"""
        self.mcp.run(host=host, port=port)

# Factory function for easy integration
def create_hubspot_mcp_server(access_token: str = None) -> HubSpotMCPServer:
    """Create and configure HubSpot MCP server"""
    return HubSpotMCPServer(access_token)

if __name__ == "__main__":
    # Development server
    server = create_hubspot_mcp_server()
    server.run()
