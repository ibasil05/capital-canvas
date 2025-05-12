"""
Base interface for financial data providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class DataProviderInterface(ABC):
    """Abstract base class for financial data providers"""
    
    @abstractmethod
    async def get_company_profile(self, ticker: str) -> Dict[str, Any]:
        """
        Get basic information about a company.
        
        Args:
            ticker: The stock ticker symbol
            
        Returns:
            Dictionary containing company information
            
        Raises:
            Exception: If the company cannot be found or an error occurs
        """
        pass
    
    @abstractmethod
    async def get_income_statements(
        self, 
        ticker: str, 
        limit: int = 5,
        period: str = 'annual'
    ) -> List[Dict[str, Any]]:
        """
        Get income statements for a company.
        
        Args:
            ticker: The stock ticker symbol
            limit: Number of statements to retrieve (default: 5 years)
            period: 'annual' or 'quarterly'
            
        Returns:
            List of income statement data dictionaries
            
        Raises:
            Exception: If the data cannot be retrieved or an error occurs
        """
        pass
    
    @abstractmethod
    async def get_balance_sheets(
        self, 
        ticker: str, 
        limit: int = 5,
        period: str = 'annual'
    ) -> List[Dict[str, Any]]:
        """
        Get balance sheets for a company.
        
        Args:
            ticker: The stock ticker symbol
            limit: Number of statements to retrieve (default: 5 years)
            period: 'annual' or 'quarterly'
            
        Returns:
            List of balance sheet data dictionaries
            
        Raises:
            Exception: If the data cannot be retrieved or an error occurs
        """
        pass
    
    @abstractmethod
    async def get_cash_flow_statements(
        self, 
        ticker: str, 
        limit: int = 5,
        period: str = 'annual'
    ) -> List[Dict[str, Any]]:
        """
        Get cash flow statements for a company.
        
        Args:
            ticker: The stock ticker symbol
            limit: Number of statements to retrieve (default: 5 years)
            period: 'annual' or 'quarterly'
            
        Returns:
            List of cash flow statement data dictionaries
            
        Raises:
            Exception: If the data cannot be retrieved or an error occurs
        """
        pass
    
    @abstractmethod
    async def get_key_metrics(
        self, 
        ticker: str,
        period: str = 'annual'
    ) -> Dict[str, Any]:
        """
        Get key financial metrics for a company.
        
        Args:
            ticker: The stock ticker symbol
            period: 'annual' or 'quarterly'
            
        Returns:
            Dictionary containing key metrics
            
        Raises:
            Exception: If the data cannot be retrieved or an error occurs
        """
        pass
    
    @abstractmethod
    async def get_sector_peers(self, ticker: str) -> List[str]:
        """
        Get a list of peer companies in the same sector.
        
        Args:
            ticker: The stock ticker symbol
            
        Returns:
            List of ticker symbols for peer companies
            
        Raises:
            Exception: If the data cannot be retrieved or an error occurs
        """
        pass
    
    @abstractmethod
    async def get_historical_prices(
        self, 
        ticker: str,
        days: int = 365
    ) -> List[Dict[str, Any]]:
        """
        Get historical stock prices for a company.
        
        Args:
            ticker: The stock ticker symbol
            days: Number of days of history to retrieve
            
        Returns:
            List of historical price data points
            
        Raises:
            Exception: If the data cannot be retrieved or an error occurs
        """
        pass
    
    @abstractmethod
    async def get_all_company_data(self, ticker: str) -> Dict[str, Any]:
        """
        Get all necessary company data for financial modeling.
        This is a convenience method that combines multiple API calls.
        
        Args:
            ticker: The stock ticker symbol
            
        Returns:
            Dictionary containing all company financial data
            
        Raises:
            Exception: If the data cannot be retrieved or an error occurs
        """
        pass

    @abstractmethod
    async def search_companies(
        self,
        query: str,
        limit: int = 10,
        exchange: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Search for companies by name or ticker symbol.

        Args:
            query: Search query string
            limit: Maximum number of results to return (default 10)
            exchange: Optional exchange filter (e.g., 'NASDAQ')

        Returns:
            A list of matching companies, each as a dictionary

        Raises:
            Exception: If the data cannot be retrieved or an error occurs
        """
        pass

    @abstractmethod
    async def get_technical_indicator(
        self,
        ticker: str,
        indicator: str = "sma",
        interval: str = "daily",
        time_period: int = 14,
        series_type: str = "close",
    ) -> Dict[str, Any]:
        """
        Get a technical indicator series for a given ticker.

        Args:
            ticker: Stock ticker symbol
            indicator: Technical indicator name (e.g., 'sma', 'ema')
            interval: Data interval ('daily', '1hour', etc.)
            time_period: Time period for the indicator calculation
            series_type: Price series to use ('open', 'close', 'high', 'low')

        Returns:
            Dictionary containing indicator data (structure depends on provider)
        """
        pass 