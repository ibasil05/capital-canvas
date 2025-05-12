"""
SEC API data provider implementation.
Uses sec-api.io to fetch SEC filings data.
"""

import httpx
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status

from backend.config import config
from backend.data_providers.base import DataProviderInterface

class SECProvider(DataProviderInterface):
    """SEC API provider implementation (sec-api.io)"""
    
    BASE_URL = "https://api.sec-api.io"
    FILING_URL = f"{BASE_URL}/xbrl"
    COMPANY_URL = f"{BASE_URL}/company"
    
    def __init__(self):
        """Initialize with API key from environment"""
        self.api_key = config.sec_api_key
        if not self.api_key:
            raise ValueError("SEC_API_KEY environment variable is required")
    
    async def _make_request(self, url: str, json_data: Dict[str, Any] = None) -> Any:
        """
        Make a request to the SEC API.
        
        Args:
            url: Full API URL
            json_data: JSON payload for POST request
            
        Returns:
            JSON response data
            
        Raises:
            HTTPException: If the request fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                if json_data:
                    response = await client.post(url, json=json_data, headers=headers, timeout=60.0)
                else:
                    response = await client.get(url, headers=headers, timeout=30.0)
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"SEC API error: {response.text}"
                    )
                
                try:
                    return response.json()
                except httpx.JSONDecodeError as e:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"SEC API response is not valid JSON: {str(e)} - Response text: {response.text}"
                    )
                
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error connecting to SEC API: {str(e)}"
            )
    
    async def get_company_profile(self, ticker: str) -> Dict[str, Any]:
        """Get company profile information"""
        url = f"{self.COMPANY_URL}?ticker={ticker}"
        data = await self._make_request(url)
        
        if not data or "error" in data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company profile not found for ticker {ticker}"
            )
        
        # Extract relevant company information
        profile = {
            "ticker": data.get("ticker", ticker),
            "name": data.get("name", ""),
            "cik": data.get("cik", ""),
            "sic": data.get("sic", ""),
            "sicDescription": data.get("sicDescription", ""),
            "industry": data.get("sicDescription", ""),
            "sector": data.get("sector", "")
        }
        
        return profile
    
    async def _get_filing(self, ticker: str, form_type: str, offset: int = 0) -> Dict[str, Any]:
        """
        Get a specific filing based on offset from the most recent.
        
        Args:
            ticker: The stock ticker symbol
            form_type: SEC form type (e.g., '10-K', '10-Q')
            offset: 0-indexed offset from the most recent filing (0 is the most recent).
            
        Returns:
            Filing data or empty dict if not found
        """
        query = {
            "query": {
                "query_string": {
                    "query": f"ticker:{ticker} AND formType:\"{form_type}\""
                }
            },
            "from": offset, # Use offset for pagination
            "size": 1,       # We want a single filing
            "sort": [{"filedAt": {"order": "desc"}}]
        }
        
        # Get filing URLs from search
        search_url = f"{self.BASE_URL}/query"
        search_results = await self._make_request(search_url, query)
        
        if not search_results or "filings" not in search_results or len(search_results["filings"]) == 0:
            return {}
        
        # Get the most recent filing
        filing_url = search_results["filings"][0].get("xbrlJson")
        if not filing_url:
            return {}
        
        # Fetch the XBRL data
        filing_data = await self._make_request(filing_url)
        
        return filing_data
    
    async def _extract_income_statement(self, filing: Dict[str, Any]) -> Dict[str, Any]:
        """Extract income statement data from filing"""
        if not filing or "IncomeStatement" not in filing:
            return {}
        
        income_data = filing["IncomeStatement"]
        
        # Map SEC API fields to standardized format
        statement = {
            "date": filing.get("FiscalPeriod", {}).get("endDate", ""),
            "period": filing.get("FiscalPeriod", {}).get("periodType", ""),
            "revenue": income_data.get("Revenue", 0),
            "costOfRevenue": income_data.get("CostOfRevenue", 0),
            "grossProfit": income_data.get("GrossProfit", 0),
            "operatingIncome": income_data.get("OperatingIncome", 0),
            "netIncome": income_data.get("NetIncome", 0),
            "eps": income_data.get("EarningsPerShare", 0),
            "ebitda": income_data.get("EBITDA", 0)
        }
        
        return statement
    
    async def _extract_balance_sheet(self, filing: Dict[str, Any]) -> Dict[str, Any]:
        """Extract balance sheet data from filing"""
        if not filing or "BalanceSheet" not in filing:
            return {}
        
        balance_data = filing["BalanceSheet"]
        
        # Map SEC API fields to standardized format
        statement = {
            "date": filing.get("FiscalPeriod", {}).get("endDate", ""),
            "period": filing.get("FiscalPeriod", {}).get("periodType", ""),
            "totalAssets": balance_data.get("Assets", 0),
            "totalCurrentAssets": balance_data.get("CurrentAssets", 0),
            "totalNonCurrentAssets": balance_data.get("NonCurrentAssets", 0),
            "totalLiabilities": balance_data.get("Liabilities", 0),
            "totalCurrentLiabilities": balance_data.get("CurrentLiabilities", 0),
            "totalNonCurrentLiabilities": balance_data.get("NonCurrentLiabilities", 0),
            "totalEquity": balance_data.get("StockholdersEquity", 0)
        }
        
        return statement
    
    async def _extract_cash_flow(self, filing: Dict[str, Any]) -> Dict[str, Any]:
        """Extract cash flow data from filing"""
        if not filing or "CashFlow" not in filing:
            return {}
        
        cash_flow_data = filing["CashFlow"]
        
        # Map SEC API fields to standardized format
        statement = {
            "date": filing.get("FiscalPeriod", {}).get("endDate", ""),
            "period": filing.get("FiscalPeriod", {}).get("periodType", ""),
            "operatingCashFlow": cash_flow_data.get("OperatingCashFlow", 0),
            "investingCashFlow": cash_flow_data.get("InvestingCashFlow", 0),
            "financingCashFlow": cash_flow_data.get("FinancingCashFlow", 0),
            "freeCashFlow": cash_flow_data.get("FreeCashFlow", 0),
            "capitalExpenditures": cash_flow_data.get("CapitalExpenditure", 0)
        }
        
        return statement
    
    async def get_income_statements(
        self, 
        ticker: str, 
        limit: int = 5,
        period: str = 'annual'
    ) -> List[Dict[str, Any]]:
        """Get income statements from 10-K filings"""
        form_type = "10-K" if period.lower() == 'annual' else "10-Q"
        
        # Get multiple filings
        statements = []
        for i in range(limit):
            try:
                filing = await self._get_filing(ticker, form_type, i)
                income_statement = await self._extract_income_statement(filing)
                if income_statement:
                    statements.append(income_statement)
            except Exception as e:
                # Log error but continue with available data
                print(f"Error fetching {form_type} #{i+1} for {ticker}: {e}")
        
        if not statements:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Income statements not found for ticker {ticker}"
            )
        
        return statements
    
    async def get_balance_sheets(
        self, 
        ticker: str, 
        limit: int = 5,
        period: str = 'annual'
    ) -> List[Dict[str, Any]]:
        """Get balance sheets from 10-K filings"""
        form_type = "10-K" if period.lower() == 'annual' else "10-Q"
        
        # Get multiple filings
        statements = []
        for i in range(limit):
            try:
                filing = await self._get_filing(ticker, form_type, i)
                balance_sheet = await self._extract_balance_sheet(filing)
                if balance_sheet:
                    statements.append(balance_sheet)
            except Exception as e:
                # Log error but continue with available data
                print(f"Error fetching {form_type} #{i+1} for {ticker}: {e}")
        
        if not statements:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Balance sheets not found for ticker {ticker}"
            )
        
        return statements
    
    async def get_cash_flow_statements(
        self, 
        ticker: str, 
        limit: int = 5,
        period: str = 'annual'
    ) -> List[Dict[str, Any]]:
        """Get cash flow statements from 10-K filings"""
        form_type = "10-K" if period.lower() == 'annual' else "10-Q"
        
        # Get multiple filings
        statements = []
        for i in range(limit):
            try:
                filing = await self._get_filing(ticker, form_type, i)
                cash_flow = await self._extract_cash_flow(filing)
                if cash_flow:
                    statements.append(cash_flow)
            except Exception as e:
                # Log error but continue with available data
                print(f"Error fetching {form_type} #{i+1} for {ticker}: {e}")
        
        if not statements:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cash flow statements not found for ticker {ticker}"
            )
        
        return statements
    
    async def get_key_metrics(
        self, 
        ticker: str,
        period: str = 'annual'
    ) -> Dict[str, Any]:
        """Get key financial metrics from most recent filing"""
        # NOTE: sec-api.io offers a dedicated "Outstanding Shares & Public Float" API.
        # Future enhancement: Utilize this for more direct and potentially accurate shares data.
        form_type = "10-K" if period.lower() == 'annual' else "10-Q"
        filing = await self._get_filing(ticker, form_type)
        
        if not filing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Financial metrics not found for ticker {ticker}"
            )
        
        # Extract financial statement data
        income_statement = await self._extract_income_statement(filing)
        balance_sheet = await self._extract_balance_sheet(filing)
        cash_flow = await self._extract_cash_flow(filing)
        
        # Attempt to extract shares outstanding from XBRL data
        # Common tags for shares outstanding (can be expanded)
        shares_outstanding_tags = [
            "EntityCommonStockSharesOutstanding",
            "WeightedAverageNumberOfSharesOutstandingBasicAndDiluted",
            "WeightedAverageNumberOfDilutedSharesOutstanding",
            "SharesOutstanding" # A more generic one
        ]
        shares_outstanding = 0
        
        # Potential parent keys where XBRL facts might be stored by sec-api.io
        # This needs verification against their actual XBRL-to-JSON output structure.
        potential_xbrl_fact_parent_keys = [
            "FilingValues", # Original assumption
            "facts", 
            "instance", 
            "data", # Common for general data objects
            None # Check top-level of filing object directly
        ]

        found_shares = False
        for parent_key in potential_xbrl_fact_parent_keys:
            if found_shares:
                break
            
            fact_container = filing
            if parent_key:
                fact_container = filing.get(parent_key)

            if isinstance(fact_container, dict):
                for tag in shares_outstanding_tags:
                    if tag in fact_container:
                        try:
                            # Value might be directly a number or nested in a {'value': number} dict
                            raw_value = fact_container[tag]
                            if isinstance(raw_value, dict) and "value" in raw_value:
                                shares_val = raw_value.get("value")
                            else:
                                shares_val = raw_value
                            
                            shares_outstanding = float(shares_val)
                            if shares_outstanding > 0:
                                found_shares = True
                                break
                        except (ValueError, TypeError, AttributeError):
                            continue # Ignore if value is not a valid number or structure mismatch
        
        # Fallback if shares_outstanding is still 0 and EPS is available
        # This is an approximation if direct shares count isn't found
        if shares_outstanding == 0 and income_statement.get("eps", 0) != 0 and income_statement.get("netIncome", 0) != 0:
            try:
                # Approximate shares = Net Income / EPS
                shares_outstanding = abs(income_statement["netIncome"] / income_statement["eps"])
            except ZeroDivisionError:
                shares_outstanding = 0

        # Calculate key metrics
        revenue = income_statement.get("revenue", 0)
        net_income = income_statement.get("netIncome", 0)
        operating_cash_flow = cash_flow.get("operatingCashFlow", 0)
        free_cash_flow = cash_flow.get("freeCashFlow", 0) # Assuming FCF is in extracted cash_flow data
        total_assets = balance_sheet.get("totalAssets", 0)
        total_equity = balance_sheet.get("totalEquity", 0)
        total_liabilities = balance_sheet.get("totalLiabilities", 0)
        
        metrics = {
            "date": income_statement.get("date", filing.get("FiscalPeriod", {}).get("endDate", "")),
            "period": income_statement.get("period", filing.get("FiscalPeriod", {}).get("periodType", "")),
            "sharesOutstanding": shares_outstanding,
            "revenuePerShare": revenue / shares_outstanding if shares_outstanding else 0,
            "netIncomePerShare": income_statement.get("eps", net_income / shares_outstanding if shares_outstanding else 0),
            "operatingCashFlowPerShare": operating_cash_flow / shares_outstanding if shares_outstanding else 0,
            "freeCashFlowPerShare": free_cash_flow / shares_outstanding if shares_outstanding else 0, # FCF might need to be calculated if not direct
            "returnOnAssets": net_income / total_assets if total_assets else 0,
            "returnOnEquity": net_income / total_equity if total_equity else 0,
            "debtToEquity": total_liabilities / total_equity if total_equity else 0,
            # Add other relevant metrics from statements if needed
            "marketCap": None # Market Cap typically requires current stock price, not available from SEC filings directly
        }
        
        return metrics
    
    async def get_sector_peers(self, ticker: str) -> List[str]:
        """
        Get a list of peer companies in the same sector.
        Limited implementation for SEC API.
        """
        # SEC API doesn't directly provide peer data, returning empty list
        return []
    
    async def get_historical_prices(
        self, 
        ticker: str,
        days: int = 365
    ) -> List[Dict[str, Any]]:
        """
        Get historical stock prices.
        SEC API doesn't provide historical prices directly,
        so this is a placeholder that returns empty data.
        """
        # SEC API doesn't provide historical prices
        return []
    
    async def get_all_company_data(self, ticker: str, filings_limit: int = 5) -> Dict[str, Any]:
        """Get all required company data"""
        # Get company profile first
        profile = await self.get_company_profile(ticker)
        
        # Fetch all filings for this company
        form_types = ["10-K", "10-Q"]
        filings = {}
        
        for form_type in form_types:
            for i in range(filings_limit):  # Use parameter - Get last N filings of each type
                try:
                    # Fetch the i-th most recent filing (0-indexed)
                    filing = await self._get_filing(ticker, form_type, offset=i) 
                    if filing:
                        # Ensure unique filing_id if multiple filings of same type are fetched
                        filing_id = f"{form_type}_offset_{i}" 
                        filings[filing_id] = filing
                    else:
                        # If a specific filing (e.g., the 5th 10-K) doesn't exist, stop trying for this form_type
                        break 
                except Exception as e:
                    print(f"Error fetching {form_type} #{i+1} for {ticker}: {e}")
                    break # Stop for this form_type on error
        
        # Extract financial statements
        income_statements = []
        balance_sheets = []
        cash_flows = []
        
        for filing_id, filing in filings.items():
            income_statement = await self._extract_income_statement(filing)
            if income_statement:
                income_statements.append(income_statement)
                
            balance_sheet = await self._extract_balance_sheet(filing)
            if balance_sheet:
                balance_sheets.append(balance_sheet)
                
            cash_flow = await self._extract_cash_flow(filing)
            if cash_flow:
                cash_flows.append(cash_flow)
        
        # Compile all data
        all_data = {
            "profile": profile,
            "income_statements": income_statements,
            "balance_sheets": balance_sheets,
            "cash_flow_statements": cash_flows,
            "filings": filings,  # Include raw filings for detailed processing
            "sector_peers": [],  # SEC API doesn't provide peer data
            "historical_prices": []  # SEC API doesn't provide price data
        }
        
        return all_data

    async def search_companies(
        self,
        query: str,
        limit: int = 10,
        exchange: str = ""
    ) -> List[Dict[str, Any]]:
        """SEC API does not support company search; return empty list"""
        return []

    async def get_technical_indicator(
        self,
        ticker: str,
        indicator: str = "sma",
        interval: str = "daily",
        time_period: int = 14,
        series_type: str = "close",
    ) -> Dict[str, Any]:
        """SEC API does not provide technical indicators; raise not implemented"""
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Technical indicator data not available from SEC provider"
        ) 