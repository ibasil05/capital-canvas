"""
Response models for API endpoints.
Uses Pydantic for data validation and serialization.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field

# Company information response
class CompanyInfoResponse(BaseModel):
    """Response model for company information"""
    ticker: str = Field(..., description="Company stock ticker symbol")
    name: str = Field(..., description="Company name")
    sector: str = Field(..., description="Company sector")
    industry: str = Field(..., description="Company industry")
    description: Optional[str] = Field(None, description="Company description")
    financials_available: bool = Field(..., description="Whether financial data is available")
    latest_filing_date: Optional[str] = Field(None, description="Date of latest filing")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    
    # Additional financial metrics
    latest_revenue: Optional[float] = Field(None, description="Latest annual revenue")
    latest_ebitda: Optional[float] = Field(None, description="Latest annual EBITDA")
    latest_net_income: Optional[float] = Field(None, description="Latest annual net income")
    
    # Peers for benchmarking
    peer_companies: Optional[List[str]] = Field(
        None, 
        description="List of peer company tickers"
    )

# Model summary response (used in listing models)
class ModelSummaryResponse(BaseModel):
    """Summary information for a financial model"""
    id: str = Field(..., description="Model ID")
    ticker: str = Field(..., description="Company ticker")
    company_name: Optional[str] = Field(None, description="Company name")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    
    # Key metrics
    enterprise_value: Optional[float] = Field(None, description="Latest calculated enterprise value")
    implied_share_price: Optional[float] = Field(None, description="Implied share price from DCF")

# Financial statement item for the detailed response
class FinancialStatement(BaseModel):
    """Financial statement for a single period"""
    year: int = Field(..., description="Forecast year (0 = latest historical)")
    is_historical: bool = Field(..., description="Whether this is historical or forecast data")
    
    # Income statement items
    revenue: float = Field(..., description="Revenue")
    gross_profit: float = Field(..., description="Gross profit")
    ebitda: float = Field(..., description="EBITDA")
    operating_income: float = Field(..., description="Operating income")
    net_income: float = Field(..., description="Net income")
    
    # Balance sheet items
    total_assets: float = Field(..., description="Total assets")
    total_debt: float = Field(..., description="Total debt")
    total_equity: float = Field(..., description="Total equity")
    
    # Cash flow items
    operating_cash_flow: float = Field(..., description="Operating cash flow")
    capex: float = Field(..., description="Capital expenditures")
    free_cash_flow: float = Field(..., description="Free cash flow")
    
    # Key metrics
    growth_rate: Optional[float] = Field(None, description="Revenue growth rate")
    gross_margin: float = Field(..., description="Gross margin")
    ebitda_margin: float = Field(..., description="EBITDA margin")
    fcf_margin: float = Field(..., description="Free cash flow margin")

# Capital structure grid item
class CapitalStructureGridItem(BaseModel):
    """Single data point in the capital structure grid"""
    debt_to_ebitda: float = Field(..., description="Debt to EBITDA ratio")
    debt_to_capital: float = Field(..., description="Debt to capital ratio")
    wacc: float = Field(..., description="Weighted average cost of capital")
    credit_rating: str = Field(..., description="Implied credit rating")
    equity_irr: float = Field(..., description="Equity IRR")
    enterprise_value: float = Field(..., description="Enterprise value")
    share_price: float = Field(..., description="Implied share price")

# Trading comparables item
class TradingComp(BaseModel):
    """Trading comparable company data"""
    ticker: str = Field(..., description="Company ticker")
    name: Optional[str] = Field(None, description="Company name")
    ev_to_ebitda: float = Field(..., description="EV/EBITDA multiple")
    ev_to_revenue: float = Field(..., description="EV/Revenue multiple")
    price_to_earnings: Optional[float] = Field(None, description="P/E ratio")
    debt_to_ebitda: Optional[float] = Field(None, description="Debt/EBITDA ratio")

# LBO analysis result
class LBOAnalysisResult(BaseModel):
    """LBO analysis results"""
    entry_enterprise_value: float = Field(..., description="Entry enterprise value")
    entry_equity_value: float = Field(..., description="Entry equity value")
    exit_enterprise_value: float = Field(..., description="Exit enterprise value")
    exit_equity_value: float = Field(..., description="Exit equity value")
    equity_investment: Optional[float] = Field(None, description="Equity investment")
    debt_investment: Optional[float] = Field(None, description="Debt investment")
    equity_irr: Optional[float] = Field(None, description="Equity IRR")
    cash_on_cash_multiple: Optional[float] = Field(None, description="Cash on cash multiple")
    entry_debt_to_ebitda: Optional[float] = Field(None, description="Entry Debt/EBITDA ratio")
    exit_debt_to_ebitda: Optional[float] = Field(None, description="Exit Debt/EBITDA ratio")

# Valuation result response
class ValuationResponse(BaseModel):
    """Valuation results"""
    # DCF valuation
    dcf_enterprise_value: float = Field(..., description="DCF enterprise value")
    dcf_equity_value: float = Field(..., description="DCF equity value")
    dcf_implied_share_price: float = Field(..., description="DCF implied share price")
    
    # Trading comps valuation
    trading_comps_enterprise_value: float = Field(..., description="Trading comps enterprise value")
    trading_comps_equity_value: float = Field(..., description="Trading comps equity value")
    trading_comps_implied_share_price: float = Field(..., description="Trading comps implied share price")
    
    # LBO analysis
    lbo_analysis: LBOAnalysisResult = Field(..., description="LBO analysis results")
    
    # Trading comparables
    trading_comps: List[TradingComp] = Field(..., description="Trading comparables")
    
    # Valuation summary
    valuation_range_low: float = Field(..., description="Low end of valuation range")
    valuation_range_high: float = Field(..., description="High end of valuation range")
    consensus_target_price: Optional[float] = Field(None, description="Analyst consensus target price")

# Detailed model response
class ModelDetailResponse(BaseModel):
    """Detailed information for a financial model"""
    # Basic info
    id: str = Field(..., description="Model ID")
    ticker: str = Field(..., description="Company ticker")
    company_name: str = Field(..., description="Company name")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    
    # Model assumptions
    assumptions: Dict[str, Any] = Field(..., description="Model assumptions")
    
    # Financial statements
    financial_statements: List[FinancialStatement] = Field(
        ..., 
        description="Financial statements (historical and forecast)"
    )
    
    # Valuation results
    valuation: ValuationResponse = Field(..., description="Valuation results")
    
    # Capital structure grid
    capital_structure_grid: List[CapitalStructureGridItem] = Field(
        ..., 
        description="Capital structure grid analysis"
    )

# Export response
class ExportResponse(BaseModel):
    """Response for file export operations"""
    file_url: str = Field(..., description="URL to download the exported file")
    file_type: str = Field(..., description="File type (xlsx or pptx)")
    expires_at: Optional[datetime] = Field(None, description="URL expiration time if applicable")

class JobCreationResponse(BaseModel):
    """Response model for endpoints that initiate a background job"""
    job_id: str = Field(..., description="Unique identifier for the background job")
    status_endpoint: str = Field(..., description="Endpoint to check the status of the job")

# For /api/ticker/{symbol}/raw endpoint (FR-2)
class HistoricalPricePoint(BaseModel):
    date: str # Or datetime
    price: float

class FinancialStatementPeriod(BaseModel):
    year: int
    # Using Dict[str, Any] for flexibility, but can be strongly typed
    income_statement: Dict[str, Any]
    balance_sheet: Dict[str, Any]
    cash_flow_statement: Dict[str, Any]

class RawFinancialDataResponse(BaseModel):
    symbol: str
    normalized_filings: List[FinancialStatementPeriod] = Field(..., description="List of normalized financial statements for up to 8 fiscal years")
    prices: List[HistoricalPricePoint] = Field(..., description="Historical prices")
    # Metadata about caching could be added here if needed
    data_source: str = Field(..., description="Source of the data, e.g., 'cache' or 'api'")
    fetched_at: datetime = Field(..., description="Timestamp of when the data was fetched or generated")

# For /api/user/recent-analyses (FR-10)
class RecentAnalysisItem(BaseModel):
    ticker: str
    model_id: Optional[str] = None # If a full model was created
    analysis_type: str # e.g., "raw_data_viewed", "model_created", "quick_valuation"
    viewed_at: datetime
    # Could add a name or brief description if available
    company_name: Optional[str] = None
    model_config = {"protected_namespaces": ()}

class RecentAnalysesResponse(BaseModel):
    recent_analyses: List[RecentAnalysisItem] 