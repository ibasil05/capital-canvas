"""
FinancialModelingPrep API data provider.
"""

import httpx
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status

from config import config
from data_providers.base import DataProviderInterface

class FMPProvider(DataProviderInterface):
    """FinancialModelingPrep API provider implementation"""
    
    # NOTE: This provider uses FMP API v3, which is a legacy version
    # scheduled for full retirement around 2025/2026.
    # Endpoints and functionality should be monitored and eventually
    # migrated to FMP API v4 or their stable API versions.
    BASE_URL = "https://financialmodelingprep.com/api/v3"
    
    def __init__(self):
        """Initialize with API key from environment"""
        self.api_key = config.fmp_key
        if not self.api_key:
            raise ValueError("FMP_KEY environment variable is required")
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Any:
        """
        Make a request to the FMP API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response data
            
        Raises:
            HTTPException: If the request fails
        """
        url = f"{self.BASE_URL}/{endpoint}"
        
        # Add API key to params
        params = params or {}
        params["apikey"] = self.api_key
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=30.0)
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"FMP API error: {response.text}"
                    )
                
                data = response.json()
                
                # Check for API error responses (usually empty list or error message)
                # if isinstance(data, list) and len(data) == 0:
                #     raise HTTPException(
                #         status_code=status.HTTP_404_NOT_FOUND,
                #         detail="No data found for the requested resource"
                #     )
                
                return data
                
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error connecting to FMP API: {str(e)}"
            )
    
    async def get_company_profile(self, ticker: str) -> Dict[str, Any]:
        """Get company profile information"""
        endpoint = f"profile/{ticker}"
        data = await self._make_request(endpoint)
        
        if not data or len(data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company profile not found for ticker {ticker}"
            )
        
        return data[0]
    
    async def get_income_statements(
        self, 
        ticker: str, 
        limit: int = 5,
        period: str = 'annual'
    ) -> List[Dict[str, Any]]:
        """Get income statements"""
        endpoint = "income-statement/{ticker}"
        if period.lower() == 'quarterly':
            endpoint = "income-statement/{ticker}?period=quarter"
        
        params = {"limit": limit}
        data = await self._make_request(endpoint.format(ticker=ticker), params)
        
        if not data or len(data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Income statements not found for ticker {ticker}"
            )
        
        return data
    
    async def get_balance_sheets(
        self, 
        ticker: str, 
        limit: int = 5,
        period: str = 'annual'
    ) -> List[Dict[str, Any]]:
        """Get balance sheets"""
        endpoint = "balance-sheet-statement/{ticker}"
        if period.lower() == 'quarterly':
            endpoint = "balance-sheet-statement/{ticker}?period=quarter"
        
        params = {"limit": limit}
        data = await self._make_request(endpoint.format(ticker=ticker), params)
        
        if not data or len(data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Balance sheets not found for ticker {ticker}"
            )
        
        return data
    
    async def get_cash_flow_statements(
        self, 
        ticker: str, 
        limit: int = 5,
        period: str = 'annual'
    ) -> List[Dict[str, Any]]:
        """Get cash flow statements"""
        endpoint = "cash-flow-statement/{ticker}"
        if period.lower() == 'quarterly':
            endpoint = "cash-flow-statement/{ticker}?period=quarter"
        
        params = {"limit": limit}
        data = await self._make_request(endpoint.format(ticker=ticker), params)
        
        if not data or len(data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cash flow statements not found for ticker {ticker}"
            )
        
        return data
    
    async def get_key_metrics(
        self, 
        ticker: str,
        period: str = 'annual'
    ) -> Dict[str, Any]:
        """Get key financial metrics"""
        endpoint = "key-metrics/{ticker}"
        if period.lower() == 'quarterly':
            endpoint = "key-metrics/{ticker}?period=quarter"
        
        params = {"limit": 1}  # Get most recent metrics
        data = await self._make_request(endpoint.format(ticker=ticker), params)
        
        if not data or len(data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Key metrics not found for ticker {ticker}"
            )
        
        return data[0]
    
    async def get_sector_peers(self, ticker: str, peer_limit: int = 20) -> List[str]:
        """Get sector peers"""
        # First, get the company's sector
        profile = await self.get_company_profile(ticker)
        sector = profile.get("sector")
        
        if not sector:
            return []
        
        # Get companies in the same sector
        endpoint = "stock-screener"
        params = {
            "sector": sector,
            "limit": peer_limit  # Use parameter
        }
        
        data = await self._make_request(endpoint, params)
        
        # Extract tickers and exclude the input ticker
        peers = [company["symbol"] for company in data if company["symbol"] != ticker]
        
        return peers
    
    async def get_historical_prices(
        self, 
        ticker: str,
        days: int = 365
    ) -> List[Dict[str, Any]]:
        """Get historical stock prices"""
        endpoint = f"historical-price-full/{ticker}"
        params = {"timeseries": days}
        
        data = await self._make_request(endpoint, params)
        
        if not data or "historical" not in data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Historical prices not found for ticker {ticker}"
            )
        
        return data["historical"]
    
    async def get_all_company_data(
        self, 
        ticker: str,
        statement_limit: int = 5,
        price_history_days: int = 365
    ) -> Dict[str, Any]:
        """Get all required company data"""
        # Fetch data concurrently for efficiency
        profile = await self.get_company_profile(ticker)
        income_statements = await self.get_income_statements(ticker, limit=statement_limit)
        balance_sheets = await self.get_balance_sheets(ticker, limit=statement_limit)
        cash_flows = await self.get_cash_flow_statements(ticker, limit=statement_limit)
        key_metrics = await self.get_key_metrics(ticker)
        
        # Compile all data into a single dictionary
        all_data = {
            "profile": profile,
            "income_statements": income_statements,
            "balance_sheets": balance_sheets,
            "cash_flow_statements": cash_flows,
            "key_metrics": key_metrics
        }
        
        # Add peers and historical data if available
        try:
            peers = await self.get_sector_peers(ticker)
            all_data["sector_peers"] = peers
        except Exception:
            all_data["sector_peers"] = []
        
        try:
            prices = await self.get_historical_prices(ticker, days=price_history_days)
            all_data["historical_prices"] = prices
        except Exception:
            all_data["historical_prices"] = []
        
        return all_data

    async def search_companies(
        self,
        query: str,
        limit: int = 10,
        exchange: str = ""
    ) -> List[Dict[str, Any]]:
        """Search for companies by name or ticker"""
        endpoint = "search"
        params = {
            "query": query,
            "limit": limit,
        }
        if exchange:
            params["exchange"] = exchange
        data = await self._make_request(endpoint, params)
        
        # Transform FMP response to the expected format
        transformed_results = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    transformed_results.append({
                        "ticker": item.get("symbol"),
                        "company_name": item.get("name"),
                        "exchange": item.get("stockExchange"), # Or exchangeShortName, depending on preference
                        "currency": item.get("currency")
                        # Add other relevant fields if needed by the frontend/app
                    })
                else:
                    # Log if an item in the list is not a dictionary as expected
                    print(f"Warning: FMP search_companies received a non-dict item in list: {item}")
        else:
            # Log if the FMP API did not return a list as expected
            print(f"Warning: FMP search_companies did not receive a list. Data: {data}")

        return transformed_results
    
    async def get_technical_indicator(
        self,
        ticker: str,
        indicator: str = "sma",
        interval: str = "daily",
        time_period: int = 14,
        series_type: str = "close",
    ) -> Dict[str, Any]:
        """Get technical indicator data for the given ticker"""
        # FMP endpoint pattern: technical_indicator/{interval}
        endpoint = f"technical_indicator/{interval}"
        params = {
            "symbol": ticker,
            "indicator": indicator,
            "time_period": time_period,
            "series_type": series_type,
        }
        data = await self._make_request(endpoint, params)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{indicator.upper()} data not found for ticker {ticker}"
            )
        return data 