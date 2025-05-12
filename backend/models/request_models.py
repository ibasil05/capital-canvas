"""
Request models for API validation.
Uses Pydantic for data validation and conversion.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
import re

class CompanyInfoRequest(BaseModel):
    """Request model for fetching company information"""
    ticker: str = Field(..., description="Company stock ticker symbol")
    
    @validator('ticker')
    def validate_ticker(cls, v):
        """Validate ticker format"""
        if not isinstance(v, str):
            raise ValueError("Ticker must be a string")
        
        # Validate ticker format (uppercase letters, numbers, and some special chars)
        if not re.match(r'^[A-Z0-9.\-]+$', v.upper()):
            raise ValueError("Invalid ticker format")
        
        return v.upper()  # Always convert to uppercase

class ModelAssumptionsRequest(BaseModel):
    """
    Request model for financial model assumptions.
    Used for both creating new models and updating existing ones.
    """
    # Growth assumptions
    revenue_growth_rates: List[float] = Field(
        ..., 
        description="Annual revenue growth rates for the forecast period"
    )
    terminal_growth_rate: float = Field(
        ..., 
        description="Long-term growth rate used for terminal value",
        ge=0.01,
        le=0.05
    )
    
    # Margin assumptions
    gross_margins: List[float] = Field(
        ..., 
        description="Gross margin forecasts"
    )
    ebitda_margins: List[float] = Field(
        ..., 
        description="EBITDA margin forecasts"
    )
    
    # Working capital assumptions
    receivable_days: float = Field(
        ..., 
        description="Days of sales outstanding",
        ge=0
    )
    inventory_days: float = Field(
        ..., 
        description="Days of inventory outstanding",
        ge=0
    )
    payable_days: float = Field(
        ..., 
        description="Days of payables outstanding",
        ge=0
    )
    
    # Capital expenditure assumptions
    capex_percent_revenue: float = Field(
        ..., 
        description="Capital expenditure as percentage of revenue",
        ge=0
    )
    
    # Valuation assumptions
    discount_rate: float = Field(
        ..., 
        description="Weighted average cost of capital (WACC)",
        ge=0.05,
        le=0.25
    )
    tax_rate: float = Field(
        ..., 
        description="Effective tax rate",
        ge=0,
        le=0.5
    )
    
    # Trading comps assumptions
    ev_to_ebitda_multiple: float = Field(
        ..., 
        description="EV/EBITDA multiple for terminal value",
        ge=1
    )
    
    # LBO assumptions
    lbo_exit_multiple: float = Field(
        ..., 
        description="Exit EV/EBITDA multiple for LBO",
        ge=1
    )
    lbo_years: int = Field(
        ..., 
        description="LBO holding period in years",
        ge=3,
        le=10
    )
    debt_to_ebitda: float = Field(
        ..., 
        description="Initial leverage ratio (Debt/EBITDA)",
        ge=0
    )
    
    # Advanced assumptions (optional)
    custom_assumptions: Optional[Dict[str, Any]] = Field(
        None,
        description="Any additional custom assumptions"
    )
    
    # Validators
    @validator('revenue_growth_rates')
    def validate_growth_rates(cls, v):
        """Validate growth rates"""
        if not v or len(v) < 1:
            raise ValueError("At least one growth rate is required")
        return v
    
    @validator('gross_margins', 'ebitda_margins')
    def validate_margins(cls, v):
        """Validate margins"""
        if not v or len(v) < 1:
            raise ValueError("At least one margin value is required")
            
        # Check margins are between 0% and 100%
        for margin in v:
            if margin < 0 or margin > 1:
                raise ValueError("Margins must be between 0 and 1 (0% to 100%)")
        
        return v

class CreateModelRequest(BaseModel):
    """Request model for creating a new financial model"""
    ticker: str = Field(..., description="Company stock ticker symbol")
    assumptions: ModelAssumptionsRequest = Field(
        ..., 
        description="Financial model assumptions"
    )
    
    @validator('ticker')
    def validate_ticker(cls, v):
        """Validate ticker format"""
        if not isinstance(v, str):
            raise ValueError("Ticker must be a string")
        
        # Validate ticker format (uppercase letters, numbers, and some special chars)
        if not re.match(r'^[A-Z0-9.\-]+$', v.upper()):
            raise ValueError("Invalid ticker format")
        
        return v.upper()  # Always convert to uppercase

class UpdateModelRequest(BaseModel):
    """Request model for updating an existing financial model"""
    assumptions: ModelAssumptionsRequest = Field(
        ..., 
        description="Updated financial model assumptions"
    ) 