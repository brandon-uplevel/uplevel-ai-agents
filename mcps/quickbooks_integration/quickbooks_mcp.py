"""
QuickBooks MCP Integration for Uplevel AI Financial Intelligence Agent

This module provides a Model Context Protocol server for QuickBooks API integration,
enabling extraction of expense data, income, and financial statements for P&L generation.
"""

import asyncio
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from quickbooks import QuickBooks
from quickbooks.objects import Purchase, Item, Account, Customer, Vendor
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes
from mcp.server.fastmcp import FastMCP
import mcp.types as types
from pydantic import BaseModel, Field
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QuickBooksExpense(BaseModel):
    """Data model for QuickBooks expenses"""
    expense_id: str = Field(..., description="QuickBooks expense ID")
    description: str = Field(..., description="Expense description")
    amount: float = Field(..., description="Expense amount")
    expense_date: str = Field(..., description="Expense transaction date")
    category: Optional[str] = Field(None, description="Expense category")
    vendor: Optional[str] = Field(None, description="Vendor name")
    account: Optional[str] = Field(None, description="Account name")
    reference_number: Optional[str] = Field(None, description="Reference number")

class QuickBooksIncome(BaseModel):
    """Data model for QuickBooks income"""
    income_id: str = Field(..., description="QuickBooks income ID")
    description: str = Field(..., description="Income description")
    amount: float = Field(..., description="Income amount")
    income_date: str = Field(..., description="Income transaction date")
    customer: Optional[str] = Field(None, description="Customer name")
    account: Optional[str] = Field(None, description="Account name")
    reference_number: Optional[str] = Field(None, description="Reference number")

class QuickBooksAccount(BaseModel):
    """Data model for QuickBooks accounts"""
    account_id: str = Field(..., description="QuickBooks account ID")
    name: str = Field(..., description="Account name")
    account_type: str = Field(..., description="Account type")
    account_sub_type: Optional[str] = Field(None, description="Account sub type")
    balance: float = Field(default=0.0, description="Current balance")

class ProfitLossStatement(BaseModel):
    """Profit & Loss statement model"""
    period: str = Field(..., description="Reporting period")
    start_date: str = Field(..., description="Period start date")
    end_date: str = Field(..., description="Period end date")
    total_income: float = Field(..., description="Total income")
    total_expenses: float = Field(..., description="Total expenses")
    net_profit: float = Field(..., description="Net profit/loss")
    profit_margin: float = Field(..., description="Profit margin percentage")
    income_breakdown: List[QuickBooksIncome] = Field(default_factory=list)
    expense_breakdown: List[QuickBooksExpense] = Field(default_factory=list)

class QuickBooksMCPServer:
    """QuickBooks MCP Server for financial intelligence"""
    
    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        access_token: str = None,
        refresh_token: str = None,
        company_id: str = None,
        environment: str = "sandbox"
    ):
        # Configuration
        self.client_id = client_id or os.getenv("QB_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("QB_CLIENT_SECRET")
        self.access_token = access_token or os.getenv("QB_ACCESS_TOKEN")
        self.refresh_token = refresh_token or os.getenv("QB_REFRESH_TOKEN")
        self.company_id = company_id or os.getenv("QB_COMPANY_ID")
        self.environment = environment or os.getenv("QB_ENVIRONMENT", "sandbox")
        
        if not all([self.client_id, self.client_secret]):
            raise ValueError("QuickBooks client ID and secret are required")
        
        # Initialize OAuth client
        self.auth_client = AuthClient(
            client_id=self.client_id,
            client_secret=self.client_secret,
            environment=self.environment,
            redirect_uri=os.getenv("QB_REDIRECT_URI", "http://localhost:8000/callback")
        )
        
        # Initialize QuickBooks client if tokens available
        self.qb_client = None
        if self.access_token and self.company_id:
            self._initialize_qb_client()
        
        # Initialize MCP server
        self.mcp = FastMCP("QuickBooks MCP Server")
        self._setup_tools()
    
    def _initialize_qb_client(self):
        """Initialize QuickBooks API client with tokens"""
        try:
            self.qb_client = QuickBooks(
                auth_client=self.auth_client,
                refresh_token=self.refresh_token,
                company_id=self.company_id,
                minorversion=70  # API minor version
            )
            logger.info("QuickBooks client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize QuickBooks client: {e}")
            self.qb_client = None
    
    def _setup_tools(self):
        """Register MCP tools"""
        
        @self.mcp.tool()
        async def get_oauth_url() -> Dict[str, Any]:
            """
            Generate OAuth authorization URL for QuickBooks connection
            """
            try:
                auth_url = self.auth_client.get_authorization_url([Scopes.ACCOUNTING])
                state = self.auth_client.state_token
                
                return {
                    "success": True,
                    "data": {
                        "auth_url": auth_url,
                        "state": state,
                        "instructions": "Visit the auth_url to authorize access to QuickBooks"
                    }
                }
            except Exception as e:
                logger.error(f"Error generating OAuth URL: {e}")
                return {"success": False, "error": str(e)}
        
        @self.mcp.tool()
        async def complete_oauth(code: str, state: str) -> Dict[str, Any]:
            """
            Complete OAuth flow with authorization code
            
            Args:
                code: Authorization code from QuickBooks
                state: State token for CSRF protection
            """
            try:
                auth_client = AuthClient(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    environment=self.environment,
                    redirect_uri=os.getenv("QB_REDIRECT_URI", "http://localhost:8000/callback"),
                    state_token=state
                )
                
                auth_client.get_bearer_token(code)
                
                self.access_token = auth_client.access_token
                self.refresh_token = auth_client.refresh_token
                self.company_id = auth_client.company_info[0]['companyInfo'][0]['QBORealmID']
                
                # Initialize QB client with new tokens
                self._initialize_qb_client()
                
                return {
                    "success": True,
                    "data": {
                        "company_id": self.company_id,
                        "access_token_expires": auth_client.token_expiry_time,
                        "message": "OAuth completed successfully"
                    }
                }
            except Exception as e:
                logger.error(f"Error completing OAuth: {e}")
                return {"success": False, "error": str(e)}
        
        @self.mcp.tool()
        async def get_expenses(
            date_range: str = "current_month",
            category: str = None,
            amount_gte: float = 0.0
        ) -> Dict[str, Any]:
            """
            Fetch expense data from QuickBooks
            
            Args:
                date_range: Period to analyze (current_month, last_month, last_quarter, ytd)
                category: Filter by expense category
                amount_gte: Minimum expense amount filter
            """
            try:
                if not self.qb_client:
                    return {"success": False, "error": "QuickBooks not connected. Use get_oauth_url first."}
                
                start_date, end_date = self._parse_date_range(date_range)
                expenses = await self._fetch_expenses(start_date, end_date, category, amount_gte)
                
                total_expenses = sum(exp.amount for exp in expenses)
                
                return {
                    "success": True,
                    "data": {
                        "period": date_range,
                        "total_expenses": total_expenses,
                        "expense_count": len(expenses),
                        "expenses": [exp.dict() for exp in expenses]
                    }
                }
            except Exception as e:
                logger.error(f"Error fetching expenses: {e}")
                return {"success": False, "error": str(e)}
        
        @self.mcp.tool()
        async def get_income(
            date_range: str = "current_month",
            customer: str = None
        ) -> Dict[str, Any]:
            """
            Fetch income data from QuickBooks
            
            Args:
                date_range: Period to analyze
                customer: Filter by customer name
            """
            try:
                if not self.qb_client:
                    return {"success": False, "error": "QuickBooks not connected. Use get_oauth_url first."}
                
                start_date, end_date = self._parse_date_range(date_range)
                income = await self._fetch_income(start_date, end_date, customer)
                
                total_income = sum(inc.amount for inc in income)
                
                return {
                    "success": True,
                    "data": {
                        "period": date_range,
                        "total_income": total_income,
                        "income_count": len(income),
                        "income": [inc.dict() for inc in income]
                    }
                }
            except Exception as e:
                logger.error(f"Error fetching income: {e}")
                return {"success": False, "error": str(e)}
        
        @self.mcp.tool()
        async def generate_profit_loss(
            date_range: str = "current_month"
        ) -> Dict[str, Any]:
            """
            Generate comprehensive Profit & Loss statement
            
            Args:
                date_range: Reporting period
            """
            try:
                if not self.qb_client:
                    return {"success": False, "error": "QuickBooks not connected. Use get_oauth_url first."}
                
                # Get income and expenses data
                income_response = await get_income(date_range)
                expenses_response = await get_expenses(date_range)
                
                if not income_response["success"]:
                    return income_response
                if not expenses_response["success"]:
                    return expenses_response
                
                income_data = income_response["data"]
                expenses_data = expenses_response["data"]
                
                start_date, end_date = self._parse_date_range(date_range)
                
                total_income = income_data["total_income"]
                total_expenses = expenses_data["total_expenses"]
                net_profit = total_income - total_expenses
                profit_margin = (net_profit / total_income * 100) if total_income > 0 else 0
                
                pl_statement = ProfitLossStatement(
                    period=date_range,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    total_income=total_income,
                    total_expenses=total_expenses,
                    net_profit=net_profit,
                    profit_margin=profit_margin,
                    income_breakdown=[QuickBooksIncome(**inc) for inc in income_data["income"]],
                    expense_breakdown=[QuickBooksExpense(**exp) for exp in expenses_data["expenses"]]
                )
                
                return {
                    "success": True,
                    "data": pl_statement.dict(),
                    "generated_at": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error generating P&L statement: {e}")
                return {"success": False, "error": str(e)}
        
        @self.mcp.tool()
        async def get_accounts() -> Dict[str, Any]:
            """
            Fetch chart of accounts from QuickBooks
            """
            try:
                if not self.qb_client:
                    return {"success": False, "error": "QuickBooks not connected. Use get_oauth_url first."}
                
                accounts = self.qb_client.query_objects("Account")
                account_list = []
                
                for account in accounts:
                    account_data = QuickBooksAccount(
                        account_id=str(account.Id),
                        name=account.Name,
                        account_type=account.AccountType,
                        account_sub_type=getattr(account, 'AccountSubType', None),
                        balance=float(getattr(account, 'CurrentBalance', 0) or 0)
                    )
                    account_list.append(account_data)
                
                return {
                    "success": True,
                    "data": {
                        "accounts": [acc.dict() for acc in account_list],
                        "total_accounts": len(account_list)
                    }
                }
            except Exception as e:
                logger.error(f"Error fetching accounts: {e}")
                return {"success": False, "error": str(e)}
    
    async def _fetch_expenses(
        self,
        start_date: datetime,
        end_date: datetime,
        category: str = None,
        amount_gte: float = 0.0
    ) -> List[QuickBooksExpense]:
        """Fetch expense transactions from QuickBooks"""
        
        try:
            # Query for Purchase transactions (expenses)
            purchases = self.qb_client.query_objects("Purchase")
            expenses = []
            
            for purchase in purchases:
                # Filter by date range
                txn_date = datetime.strptime(purchase.TxnDate, "%Y-%m-%d")
                if not (start_date <= txn_date <= end_date):
                    continue
                
                # Process line items
                for line in purchase.Line:
                    if hasattr(line, 'Amount'):
                        amount = float(line.Amount)
                        
                        # Filter by minimum amount
                        if amount < amount_gte:
                            continue
                        
                        # Get vendor name
                        vendor_name = None
                        if hasattr(purchase, 'EntityRef') and purchase.EntityRef:
                            vendor_name = purchase.EntityRef.name
                        
                        # Get account name
                        account_name = None
                        if hasattr(line, 'AccountBasedExpenseLineDetail'):
                            account_ref = line.AccountBasedExpenseLineDetail.AccountRef
                            account_name = account_ref.name if account_ref else None
                        
                        expense = QuickBooksExpense(
                            expense_id=str(purchase.Id),
                            description=getattr(line, 'Description', '') or 'Expense',
                            amount=amount,
                            expense_date=purchase.TxnDate,
                            category=category,  # Could be enhanced with QB categories
                            vendor=vendor_name,
                            account=account_name,
                            reference_number=getattr(purchase, 'DocNumber', None)
                        )
                        
                        expenses.append(expense)
            
            logger.info(f"Retrieved {len(expenses)} expenses")
            return expenses
            
        except Exception as e:
            logger.error(f"Error fetching expenses: {e}")
            return []
    
    async def _fetch_income(
        self,
        start_date: datetime,
        end_date: datetime,
        customer: str = None
    ) -> List[QuickBooksIncome]:
        """Fetch income transactions from QuickBooks"""
        
        try:
            # Query for Invoice transactions (income)
            invoices = self.qb_client.query_objects("Invoice")
            income_list = []
            
            for invoice in invoices:
                # Filter by date range
                txn_date = datetime.strptime(invoice.TxnDate, "%Y-%m-%d")
                if not (start_date <= txn_date <= end_date):
                    continue
                
                # Get customer name
                customer_name = None
                if hasattr(invoice, 'CustomerRef') and invoice.CustomerRef:
                    customer_name = invoice.CustomerRef.name
                
                # Filter by customer if specified
                if customer and customer_name and customer.lower() not in customer_name.lower():
                    continue
                
                # Process line items
                for line in invoice.Line:
                    if hasattr(line, 'Amount'):
                        amount = float(line.Amount)
                        
                        income = QuickBooksIncome(
                            income_id=str(invoice.Id),
                            description=getattr(line, 'Description', '') or 'Income',
                            amount=amount,
                            income_date=invoice.TxnDate,
                            customer=customer_name,
                            account=None,  # Could be enhanced
                            reference_number=getattr(invoice, 'DocNumber', None)
                        )
                        
                        income_list.append(income)
            
            logger.info(f"Retrieved {len(income_list)} income entries")
            return income_list
            
        except Exception as e:
            logger.error(f"Error fetching income: {e}")
            return []
    
    def _parse_date_range(self, date_range: str) -> tuple[datetime, datetime]:
        """Parse date range string into start and end dates"""
        
        now = datetime.now()
        
        if date_range == "current_month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = start_date.replace(month=start_date.month + 1) if start_date.month < 12 else start_date.replace(year=start_date.year + 1, month=1)
            end_date = next_month - timedelta(days=1)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        elif date_range == "last_month":
            first_current = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = first_current - timedelta(days=1)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        elif date_range == "last_quarter":
            current_quarter = (now.month - 1) // 3 + 1
            if current_quarter == 1:
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
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = start_date.replace(month=start_date.month + 1) if start_date.month < 12 else start_date.replace(year=start_date.year + 1, month=1)
            end_date = next_month - timedelta(days=1)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return start_date, end_date

    def get_mcp_app(self):
        """Get the MCP application for deployment"""
        return self.mcp

    def run(self, host: str = "localhost", port: int = 8002):
        """Run the QuickBooks MCP server"""
        self.mcp.run(host=host, port=port)

# Factory function for easy integration
def create_quickbooks_mcp_server(
    client_id: str = None,
    client_secret: str = None,
    access_token: str = None,
    refresh_token: str = None,
    company_id: str = None,
    environment: str = "sandbox"
) -> QuickBooksMCPServer:
    """Create and configure QuickBooks MCP server"""
    return QuickBooksMCPServer(
        client_id=client_id,
        client_secret=client_secret,
        access_token=access_token,
        refresh_token=refresh_token,
        company_id=company_id,
        environment=environment
    )

if __name__ == "__main__":
    # Development server
    server = create_quickbooks_mcp_server()
    server.run()
