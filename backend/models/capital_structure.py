"""
Capital structure grid analysis to find optimal capital structures.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple

class CapitalStructureGrid:
    """Capital structure grid analysis model"""
    
    def __init__(
        self,
        income_statement: pd.DataFrame,
        balance_sheet: pd.DataFrame,
        cash_flow: pd.DataFrame,
        base_discount_rate: float,
        tax_rate: float
    ):
        """
        Initialize the capital structure grid model.
        
        Args:
            income_statement: Projected income statement
            balance_sheet: Projected balance sheet
            cash_flow: Projected cash flow statement
            base_discount_rate: Base weighted average cost of capital (WACC)
            tax_rate: Effective tax rate
        """
        self.income_statement = income_statement
        self.balance_sheet = balance_sheet
        self.cash_flow = cash_flow
        self.base_discount_rate = base_discount_rate
        self.tax_rate = tax_rate
        
        # Define leverage ranges for analysis
        self.debt_to_ebitda_range = np.linspace(0, 8, 9)  # 0x to 8x debt/EBITDA
        self.debt_to_capital_range = np.linspace(0, 0.8, 9)  # 0% to 80% debt/capital
        
        # Credit rating parameters
        self.ratings = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]
        self.rating_spreads = {
            "AAA": 0.005,  # 50 bps
            "AA": 0.0075,  # 75 bps
            "A": 0.01,  # 100 bps
            "BBB": 0.015,  # 150 bps
            "BB": 0.03,  # 300 bps
            "B": 0.045,  # 450 bps
            "CCC": 0.065,  # 650 bps
        }
        self.debt_to_ebitda_thresholds = {
            "AAA": 1.0,
            "AA": 1.5,
            "A": 2.0,
            "BBB": 3.0,
            "BB": 4.5,
            "B": 6.0,
            "CCC": 7.5
        }
    
    def calculate(self) -> List[Dict[str, Any]]:
        """
        Calculate the capital structure grid.
        
        Returns:
            List of dictionaries with capital structure scenarios
        """
        # Get EBITDA and other key metrics
        ebitda = self.income_statement["ebitda"].iloc[1]  # Forward EBITDA
        
        # Create grid datapoints
        grid_points = []
        
        # Loop through leverage scenarios
        for debt_to_ebitda in self.debt_to_ebitda_range:
            # Calculate debt and relevant metrics
            debt = ebitda * debt_to_ebitda
            
            # Calculate implied enterprise value (simplified)
            ev_to_ebitda_multiple = 8.0  # Example multiple
            enterprise_value = ebitda * ev_to_ebitda_multiple
            
            # Calculate equity value and debt-to-capital ratio
            equity_value = enterprise_value - debt
            if equity_value <= 0:
                continue  # Skip negative equity scenarios
                
            debt_to_capital = debt / (debt + equity_value)
            
            # Calculate credit rating and cost of debt
            credit_rating = self._determine_credit_rating(debt_to_ebitda)
            cost_of_debt = self._calculate_cost_of_debt(credit_rating)
            
            # Calculate WACC
            wacc = self._calculate_wacc(debt_to_capital, cost_of_debt)
            
            # Calculate equity IRR (simplified)
            debt_to_capital_effect = (debt_to_capital * 2)  # Simplified leverage effect
            equity_irr = self.base_discount_rate + debt_to_capital_effect
            
            # Calculate implied share price (simplified)
            shares_outstanding = 100000000  # Example value
            share_price = equity_value / shares_outstanding
            
            # Add to grid points
            grid_points.append({
                "debt_to_ebitda": debt_to_ebitda,
                "debt_to_capital": debt_to_capital,
                "debt": debt,
                "equity_value": equity_value,
                "enterprise_value": enterprise_value,
                "wacc": wacc,
                "cost_of_debt": cost_of_debt,
                "credit_rating": credit_rating,
                "equity_irr": equity_irr,
                "share_price": share_price
            })
        
        return grid_points
    
    def _determine_credit_rating(self, debt_to_ebitda: float) -> str:
        """
        Determine the credit rating based on debt to EBITDA ratio.
        
        Args:
            debt_to_ebitda: Debt to EBITDA ratio
            
        Returns:
            Credit rating
        """
        for rating, threshold in sorted(self.debt_to_ebitda_thresholds.items(), key=lambda x: x[1]):
            if debt_to_ebitda <= threshold:
                return rating
                
        return "CCC"  # Default to lowest rating if above all thresholds
    
    def _calculate_cost_of_debt(self, credit_rating: str) -> float:
        """
        Calculate the cost of debt based on credit rating.
        
        Args:
            credit_rating: Credit rating
            
        Returns:
            Cost of debt (decimal)
        """
        # Risk-free rate plus credit spread
        risk_free_rate = 0.035  # 3.5% risk-free rate
        
        # Get the spread for the rating
        spread = self.rating_spreads.get(credit_rating, 0.065)  # Default to CCC if not found
        
        # Cost of debt
        cost_of_debt = risk_free_rate + spread
        
        # Apply tax shield
        after_tax_cost_of_debt = cost_of_debt * (1 - self.tax_rate)
        
        return after_tax_cost_of_debt
    
    def _calculate_wacc(self, debt_to_capital: float, cost_of_debt: float) -> float:
        """
        Calculate the weighted average cost of capital.
        
        Args:
            debt_to_capital: Debt to capital ratio
            cost_of_debt: After-tax cost of debt
            
        Returns:
            WACC (decimal)
        """
        # Cost of equity (using a simplified CAPM)
        # As leverage increases, cost of equity increases due to financial risk
        equity_to_capital = 1 - debt_to_capital
        leverage_premium = debt_to_capital * 0.1  # Simplified leverage effect on equity premium
        cost_of_equity = self.base_discount_rate + leverage_premium
        
        # WACC formula: (E/V * Re) + (D/V * Rd * (1-T))
        # Since cost_of_debt is already after-tax, we can simplify:
        wacc = (equity_to_capital * cost_of_equity) + (debt_to_capital * cost_of_debt)
        
        return wacc 