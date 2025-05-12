"""
Factory for creating data provider instances.
Selects the appropriate provider based on available API keys.
"""

from typing import Optional

from backend.config import config
from backend.data_providers.base import DataProviderInterface
from backend.data_providers.fmp_provider import FMPProvider
from backend.data_providers.sec_provider import SECProvider

def get_data_provider() -> DataProviderInterface:
    """
    Get the appropriate data provider based on available API keys.
    
    Returns:
        DataProviderInterface implementation
        
    Raises:
        ValueError: If no suitable API key is available
    """
    # Prefer FMP first if available
    if config.fmp_key:
        return FMPProvider()
    
    # Fall back to SEC API if available
    if config.sec_api_key:
        return SECProvider()
    
    # If we get here, no API key is available
    raise ValueError(
        "No financial data API key is available. "
        "Please set either FMP_KEY or SEC_API_KEY in environment variables."
    ) 