"""
Valuation engine implementations for DCF, Trading Comps, and LBO.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from backend.data_providers.provider_factory import get_data_provider

class DCFValuation:
    """Discounted Cash Flow valuation model"""
    
    def __init__(
        self,
        income_statement: pd.DataFrame,
        cash_flow: pd.DataFrame,
        balance_sheet: pd.DataFrame,
        discount_rate: float,
        terminal_growth_rate: float,
        tax_rate: float,
        company_data: Dict[str, Any]
    ):
        """
        Initialize the DCF model.
        
        Args:
            income_statement: Projected income statement
            cash_flow: Projected cash flow statement
            balance_sheet: Projected balance sheet
            discount_rate: WACC (weighted average cost of capital)
            terminal_growth_rate: Long-term growth rate
            tax_rate: Effective tax rate
            company_data: Raw company data from API
        """
        self.income_statement = income_statement
        self.cash_flow = cash_flow
        self.balance_sheet = balance_sheet
        self.discount_rate = discount_rate
        self.terminal_growth_rate = terminal_growth_rate
        self.tax_rate = tax_rate
        self.company_data = company_data
    
    def calculate(self) -> Dict[str, Any]:
        """
        Calculate enterprise and equity value using DCF method.
        
        Returns:
            Dictionary with valuation results
        """
        # Get the forecast period free cash flows
        # Exclude the terminal year (last row)
        forecast_fcf = self.cash_flow["free_cash_flow"].iloc[:-1].values
        
        # Calculate terminal value
        terminal_year_fcf = self.cash_flow["free_cash_flow"].iloc[-2]  # Second to last year
        terminal_value = self._calculate_terminal_value(terminal_year_fcf)
        
        # Discount the cash flows
        forecast_years = len(forecast_fcf)
        discount_factors = np.array([(1 + self.discount_rate) ** -t for t in range(1, forecast_years + 1)])
        
        # PV of forecast period FCF
        pv_forecast_fcf = np.sum(forecast_fcf * discount_factors)
        
        # PV of terminal value
        pv_terminal_value = terminal_value * discount_factors[-1]
        
        # Enterprise value
        enterprise_value = pv_forecast_fcf + pv_terminal_value
        
        # Get net debt from balance sheet (most recent period)
        net_debt = self.balance_sheet["total_debt"].iloc[0] - self.cash_flow["cash"].iloc[0] if "cash" in self.cash_flow else self.balance_sheet["total_debt"].iloc[0]
        
        # Equity value
        equity_value = enterprise_value - net_debt
        
        # Get shares outstanding from company profile
        shares_outstanding = self._get_shares_outstanding()
        
        # Price per share
        price_per_share = equity_value / shares_outstanding if shares_outstanding > 0 else 0
        
        return {
            "enterprise_value": enterprise_value,
            "equity_value": equity_value,
            "price_per_share": price_per_share,
            "shares_outstanding": shares_outstanding,
            "terminal_value": terminal_value,
            "pv_forecast_fcf": pv_forecast_fcf,
            "pv_terminal_value": pv_terminal_value,
            "terminal_growth_rate": self.terminal_growth_rate,
            "discount_rate": self.discount_rate
        }
    
    def _calculate_terminal_value(self, final_year_fcf: float) -> float:
        """
        Calculate terminal value using the perpetuity growth method.
        
        Args:
            final_year_fcf: Free cash flow in the final forecast year
            
        Returns:
            Terminal value
        """
        # Terminal value = FCF * (1 + g) / (WACC - g)
        # Where g is the terminal growth rate
        return final_year_fcf * (1 + self.terminal_growth_rate) / (self.discount_rate - self.terminal_growth_rate)
    
    def _get_shares_outstanding(self) -> float:
        """
        Get the latest shares outstanding from company data.
        
        Returns:
            Number of shares outstanding
        """
        # Extract shares outstanding from company profile
        profile = self.company_data.get("profile", {})
        
        # Different APIs provide shares outstanding in different formats
        shares_outstanding = 0
        
        # Try FMP format
        if "mktCap" in profile and "price" in profile and profile.get("price") is not None and profile["price"] > 0:
            # Calculate from market cap and price
            shares_outstanding = profile["mktCap"] / profile["price"]
        
        # Try alternate fields that might contain shares data
        elif "shareOutstanding" in profile:
            shares_outstanding = profile["shareOutstanding"]
        elif "sharesOutstanding" in profile:
            shares_outstanding = profile["sharesOutstanding"]
        
        # Try key metrics if available
        elif "key_metrics" in self.company_data:
            metrics = self.company_data["key_metrics"]
            if isinstance(metrics, dict) and "sharesOutstanding" in metrics:
                shares_outstanding = metrics["sharesOutstanding"]
            elif isinstance(metrics, list) and len(metrics) > 0 and "sharesOutstanding" in metrics[0]:
                shares_outstanding = metrics[0]["sharesOutstanding"]
        
        # Ensure a valid positive number
        return max(1, float(shares_outstanding))


class TradingCompsValuation:
    """Trading comparables valuation model"""
    
    def __init__(
        self,
        income_statement: pd.DataFrame,
        balance_sheet: pd.DataFrame,
        ev_to_ebitda_multiple: float,
        company_data: Dict[str, Any]
    ):
        """
        Initialize the Trading Comps model.
        
        Args:
            income_statement: Projected income statement
            balance_sheet: Projected balance sheet
            ev_to_ebitda_multiple: EV/EBITDA multiple for valuation
            company_data: Raw company data from API
        """
        self.income_statement = income_statement
        self.balance_sheet = balance_sheet
        self.ev_to_ebitda_multiple = ev_to_ebitda_multiple
        self.company_data = company_data
    
    def calculate(self) -> Dict[str, Any]:
        """
        Calculate enterprise and equity value using trading comps method.
        
        Returns:
            Dictionary with valuation results
        """
        # Use next year's EBITDA for forward multiple valuation
        forward_ebitda = self.income_statement["ebitda"].iloc[1]
        
        # Calculate enterprise value
        enterprise_value = forward_ebitda * self.ev_to_ebitda_multiple
        
        # Get net debt from balance sheet (most recent period)
        net_debt = self.balance_sheet["total_debt"].iloc[0]
        
        # Equity value
        equity_value = enterprise_value - net_debt
        
        # Get shares outstanding from company profile
        shares_outstanding = self._get_shares_outstanding()
        
        # Price per share
        price_per_share = equity_value / shares_outstanding if shares_outstanding > 0 else 0
        
        # Calculate other common multiples
        ev_to_revenue = enterprise_value / self.income_statement["revenue"].iloc[1]
        price_to_earnings = equity_value / self.income_statement["net_income"].iloc[1]
        
        return {
            "enterprise_value": enterprise_value,
            "equity_value": equity_value,
            "price_per_share": price_per_share,
            "shares_outstanding": shares_outstanding,
            "ev_to_ebitda": self.ev_to_ebitda_multiple,
            "ev_to_revenue": ev_to_revenue,
            "price_to_earnings": price_to_earnings,
            "forward_ebitda": forward_ebitda
        }
    
    def _get_shares_outstanding(self) -> float:
        """
        Get the latest shares outstanding from company data.
        
        Returns:
            Number of shares outstanding
        """
        # Extract shares outstanding from company profile
        profile = self.company_data.get("profile", {})
        
        # Different APIs provide shares outstanding in different formats
        shares_outstanding = 0
        
        # Try FMP format
        if "mktCap" in profile and "price" in profile and profile.get("price") is not None and profile["price"] > 0:
            # Calculate from market cap and price
            shares_outstanding = profile["mktCap"] / profile["price"]
        
        # Try alternate fields that might contain shares data
        elif "shareOutstanding" in profile:
            shares_outstanding = profile["shareOutstanding"]
        elif "sharesOutstanding" in profile:
            shares_outstanding = profile["sharesOutstanding"]
        
        # Try key metrics if available
        elif "key_metrics" in self.company_data:
            metrics = self.company_data["key_metrics"]
            if isinstance(metrics, dict) and "sharesOutstanding" in metrics:
                shares_outstanding = metrics["sharesOutstanding"]
            elif isinstance(metrics, list) and len(metrics) > 0 and "sharesOutstanding" in metrics[0]:
                shares_outstanding = metrics[0]["sharesOutstanding"]
        
        # Ensure a valid positive number
        return max(1, float(shares_outstanding))


class LBOValuation:
    """Leveraged Buyout valuation model"""
    
    def __init__(
        self,
        income_statement: pd.DataFrame,
        cash_flow: pd.DataFrame,
        balance_sheet: pd.DataFrame,
        exit_multiple: float,
        holding_period_years: int,
        debt_to_ebitda: float,
        discount_rate: float,
        tax_rate: float,
        company_data: Dict[str, Any]
    ):
        """
        Initialize the LBO model.
        
        Args:
            income_statement: Projected income statement
            cash_flow: Projected cash flow statement
            balance_sheet: Projected balance sheet
            exit_multiple: EV/EBITDA multiple at exit
            holding_period_years: Investment horizon in years
            debt_to_ebitda: Initial leverage ratio
            discount_rate: Required rate of return
            tax_rate: Effective tax rate
            company_data: Raw company data from API
        """
        self.income_statement = income_statement
        self.cash_flow = cash_flow
        self.balance_sheet = balance_sheet
        self.exit_multiple = exit_multiple
        self.holding_period_years = holding_period_years
        self.debt_to_ebitda = debt_to_ebitda
        self.discount_rate = discount_rate
        self.tax_rate = tax_rate
        self.company_data = company_data
    
    def calculate(self) -> Dict[str, Any]:
        """
        Calculate LBO returns and exit values.
        
        Returns:
            Dictionary with LBO analysis results
        """
        # Current EBITDA and enterprise value
        current_ebitda = self.income_statement["ebitda"].iloc[0]
        entry_ev = current_ebitda * self.exit_multiple  # Assuming entry at the same multiple as exit
        
        # Calculate initial debt and equity
        initial_debt = current_ebitda * self.debt_to_ebitda
        initial_equity = entry_ev - initial_debt
        
        # Exit EBITDA (using the value at the holding period year)
        exit_year = min(self.holding_period_years, len(self.income_statement) - 1)
        exit_ebitda = self.income_statement["ebitda"].iloc[exit_year]
        
        # Exit enterprise value
        exit_ev = exit_ebitda * self.exit_multiple
        
        # Debt repayment from free cash flow
        debt_repayment = np.sum(self.cash_flow["free_cash_flow"].iloc[1:exit_year+1])
        remaining_debt = max(0, initial_debt - debt_repayment)
        
        # Exit equity value
        exit_equity = exit_ev - remaining_debt
        
        # Calculate returns
        equity_irr = self._calculate_irr(initial_equity, exit_equity, self.holding_period_years)
        cash_on_cash = exit_equity / initial_equity
        
        # Calculate leverage ratios
        entry_debt_to_ebitda = initial_debt / current_ebitda
        exit_debt_to_ebitda = remaining_debt / exit_ebitda if exit_ebitda > 0 else 0
        
        # Get shares outstanding from company data
        shares_outstanding = self._get_shares_outstanding()
        entry_price_per_share = initial_equity / shares_outstanding if shares_outstanding > 0 else 0
        exit_price_per_share = exit_equity / shares_outstanding if shares_outstanding > 0 else 0
        
        return {
            "entry_enterprise_value": entry_ev,
            "entry_equity_value": initial_equity,
            "entry_debt": initial_debt,
            "exit_enterprise_value": exit_ev,
            "exit_equity_value": exit_equity,
            "remaining_debt": remaining_debt,
            "equity_irr": equity_irr,
            "cash_on_cash": cash_on_cash,
            "entry_debt_to_ebitda": entry_debt_to_ebitda,
            "exit_debt_to_ebitda": exit_debt_to_ebitda,
            "exit_multiple": self.exit_multiple,
            "holding_period_years": self.holding_period_years,
            "shares_outstanding": shares_outstanding,
            "entry_price_per_share": entry_price_per_share,
            "exit_price_per_share": exit_price_per_share
        }
    
    def _calculate_irr(self, initial_investment: float, exit_value: float, years: int) -> float:
        """
        Calculate the internal rate of return.
        
        Args:
            initial_investment: Initial equity investment (negative cash flow)
            exit_value: Exit equity value (positive cash flow)
            years: Holding period in years
            
        Returns:
            IRR as a decimal
        """
        # Simplified IRR calculation using the formula for a single cash flow at exit
        # IRR = (Exit Value / Initial Investment) ^ (1/years) - 1
        return (exit_value / initial_investment) ** (1 / years) - 1
    
    def _get_shares_outstanding(self) -> float:
        """
        Get the latest shares outstanding from company data.
        
        Returns:
            Number of shares outstanding
        """
        # Extract shares outstanding from company profile
        profile = self.company_data.get("profile", {})
        
        # Different APIs provide shares outstanding in different formats
        shares_outstanding = 0
        
        # Try FMP format
        if "mktCap" in profile and "price" in profile and profile.get("price") is not None and profile["price"] > 0:
            # Calculate from market cap and price
            shares_outstanding = profile["mktCap"] / profile["price"]
        
        # Try alternate fields that might contain shares data
        elif "shareOutstanding" in profile:
            shares_outstanding = profile["shareOutstanding"]
        elif "sharesOutstanding" in profile:
            shares_outstanding = profile["sharesOutstanding"]
        
        # Try key metrics if available
        elif "key_metrics" in self.company_data:
            metrics = self.company_data["key_metrics"]
            if isinstance(metrics, dict) and "sharesOutstanding" in metrics:
                shares_outstanding = metrics["sharesOutstanding"]
            elif isinstance(metrics, list) and len(metrics) > 0 and "sharesOutstanding" in metrics[0]:
                shares_outstanding = metrics[0]["sharesOutstanding"]
        
        # Ensure a valid positive number
        return max(1, float(shares_outstanding))


class ValuationEngine:
    """Main engine for running various valuation models"""
    
    def __init__(
        self,
        ticker: str,
        company_data: Dict[str, Any],
        forecast_years: int = 5,
        assumptions: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the valuation engine.
        
        Args:
            ticker: Company stock ticker symbol
            company_data: Raw data from the financial data provider API
            forecast_years: Number of years to forecast (default: 5)
            assumptions: Custom model assumptions (optional)
        """
        self.ticker = ticker
        self.company_data = company_data
        self.forecast_years = forecast_years
        self.assumptions = assumptions or self._get_default_assumptions()
        self.data_provider = get_data_provider()
        
        # Initialize statement data frames
        self.income_statement = None
        self.balance_sheet = None
        self.cash_flow = None
        
        # Prepare historical data
        self._prepare_historical_data()
        
        # Generate forecast
        self._generate_forecast()
    
    async def run_valuation(self) -> Dict[str, Any]:
        """
        Run all valuation models and combine results.
        
        Returns:
            Dictionary with combined valuation results
        """
        # Run DCF valuation
        dcf_valuation = DCFValuation(
            income_statement=self.income_statement,
            cash_flow=self.cash_flow,
            balance_sheet=self.balance_sheet,
            discount_rate=self.assumptions["discount_rate"],
            terminal_growth_rate=self.assumptions["terminal_growth_rate"],
            tax_rate=self.assumptions["tax_rate"],
            company_data=self.company_data
        )
        dcf_results = dcf_valuation.calculate()
        
        # Run trading comps valuation
        trading_comps_valuation = TradingCompsValuation(
            income_statement=self.income_statement,
            balance_sheet=self.balance_sheet,
            ev_to_ebitda_multiple=self.assumptions["ev_to_ebitda_multiple"],
            company_data=self.company_data
        )
        trading_comps_results = trading_comps_valuation.calculate()
        
        # Run LBO valuation
        lbo_valuation = LBOValuation(
            income_statement=self.income_statement,
            cash_flow=self.cash_flow,
            balance_sheet=self.balance_sheet,
            exit_multiple=self.assumptions["lbo_exit_multiple"],
            holding_period_years=self.assumptions["lbo_years"],
            debt_to_ebitda=self.assumptions["debt_to_ebitda"],
            discount_rate=self.assumptions["discount_rate"],
            tax_rate=self.assumptions["tax_rate"],
            company_data=self.company_data
        )
        lbo_results = lbo_valuation.calculate()
        
        # Compile trading comparables from peers if available
        trading_comps = await self._get_trading_comps()
        
        # Calculate valuation range
        valuation_range = self._calculate_valuation_range(
            dcf_price=dcf_results["price_per_share"],
            comps_price=trading_comps_results["price_per_share"]
        )
        
        # Combine all valuation results
        return {
            "ticker": self.ticker,
            "company_name": self._get_company_name(),
            "dcf_valuation": dcf_results,
            "trading_comps_valuation": trading_comps_results,
            "lbo_valuation": lbo_results,
            "trading_comps": trading_comps,
            "valuation_range": valuation_range,
            "shares_outstanding": dcf_results["shares_outstanding"],
            "assumptions": self.assumptions
        }
    
    def _prepare_historical_data(self):
        """Extract and normalize historical financial data from API response"""
        # Extract historical statements
        income_statements = self.company_data.get("income_statements", [])
        balance_sheets = self.company_data.get("balance_sheets", [])
        cash_flow_statements = self.company_data.get("cash_flow_statements", [])
        
        # Convert to pandas DataFrames and normalize column names
        # This will need customization based on the specific API response format
        # The implementation below is a simplified example
        
        # Format depends on the API provider being used
        # This example assumes standardized format from our data providers
        
        # Create income statement DataFrame
        income_df = pd.DataFrame(income_statements)
        if not income_df.empty:
            # Rename columns to standardized names if needed
            income_df = income_df.rename(columns={
                "revenue": "revenue",
                "grossProfit": "gross_profit",
                "ebitda": "ebitda",
                "netIncome": "net_income",
                # Add more mappings as needed
            })
            
            # Ensure required columns exist
            for col in ["revenue", "gross_profit", "ebitda", "net_income"]:
                if col not in income_df.columns:
                    income_df[col] = 0
        else:
            # Create empty DataFrame with required columns
            income_df = pd.DataFrame({
                "revenue": [],
                "gross_profit": [],
                "ebitda": [],
                "net_income": []
            })
        
        # Create balance sheet DataFrame
        balance_df = pd.DataFrame(balance_sheets)
        if not balance_df.empty:
            # Rename columns to standardized names if needed
            balance_df = balance_df.rename(columns={
                "totalAssets": "total_assets",
                "totalLiabilities": "total_liabilities",
                "totalDebt": "total_debt",
                "totalEquity": "total_equity",
                # Add more mappings as needed
            })
            
            # Ensure required columns exist
            for col in ["total_assets", "total_liabilities", "total_debt", "total_equity"]:
                if col not in balance_df.columns:
                    balance_df[col] = 0
        else:
            # Create empty DataFrame with required columns
            balance_df = pd.DataFrame({
                "total_assets": [],
                "total_liabilities": [],
                "total_debt": [],
                "total_equity": []
            })
        
        # Create cash flow DataFrame
        cash_flow_df = pd.DataFrame(cash_flow_statements)
        if not cash_flow_df.empty:
            # Rename columns to standardized names if needed
            cash_flow_df = cash_flow_df.rename(columns={
                "operatingCashFlow": "operating_cash_flow",
                "capitalExpenditure": "capex",
                "freeCashFlow": "free_cash_flow",
                "cashAtEndOfPeriod": "cash",
                # Add more mappings as needed
            })
            
            # Ensure required columns exist
            for col in ["operating_cash_flow", "capex", "free_cash_flow", "cash"]:
                if col not in cash_flow_df.columns:
                    cash_flow_df[col] = 0
        else:
            # Create empty DataFrame with required columns
            cash_flow_df = pd.DataFrame({
                "operating_cash_flow": [],
                "capex": [],
                "free_cash_flow": [],
                "cash": []
            })
        
        # Store historical data
        self.historical_income = income_df
        self.historical_balance = balance_df
        self.historical_cash_flow = cash_flow_df
    
    def _generate_forecast(self):
        """Generate financial forecasts based on historical data and assumptions"""
        # Create forecast DataFrames
        income_df = pd.DataFrame()
        balance_df = pd.DataFrame()
        cash_flow_df = pd.DataFrame()
        
        # Get historical values to use as base for forecasting
        if not self.historical_income.empty:
            latest_revenue = self.historical_income["revenue"].iloc[0]
            latest_ebitda = self.historical_income["ebitda"].iloc[0]
            latest_net_income = self.historical_income["net_income"].iloc[0]
        else:
            # Fallback to zero if no historical data
            latest_revenue = 0
            latest_ebitda = 0
            latest_net_income = 0
        
        if not self.historical_balance.empty:
            latest_total_assets = self.historical_balance["total_assets"].iloc[0]
            latest_total_debt = self.historical_balance["total_debt"].iloc[0]
            latest_total_equity = self.historical_balance["total_equity"].iloc[0]
        else:
            # Fallback to zero if no historical data
            latest_total_assets = 0
            latest_total_debt = 0
            latest_total_equity = 0
        
        if not self.historical_cash_flow.empty:
            latest_operating_cash_flow = self.historical_cash_flow["operating_cash_flow"].iloc[0]
            latest_capex = self.historical_cash_flow["capex"].iloc[0]
            latest_free_cash_flow = self.historical_cash_flow["free_cash_flow"].iloc[0]
            latest_cash = self.historical_cash_flow["cash"].iloc[0]
        else:
            # Fallback to zero if no historical data
            latest_operating_cash_flow = 0
            latest_capex = 0
            latest_free_cash_flow = 0
            latest_cash = 0
        
        # Generate forecast
        for year in range(self.forecast_years + 1):  # +1 for terminal year
            # === INCOME STATEMENT ===
            # Revenue forecast
            if year == 0:
                revenue = latest_revenue
            elif year < len(self.assumptions["revenue_growth_rates"]):
                prev_revenue = income_df.loc[year - 1, "revenue"]
                growth_rate = self.assumptions["revenue_growth_rates"][year - 1]
                revenue = prev_revenue * (1 + growth_rate)
            else:
                # Use terminal growth rate for years beyond explicit forecast
                prev_revenue = income_df.loc[year - 1, "revenue"]
                revenue = prev_revenue * (1 + self.assumptions["terminal_growth_rate"])
            
            # Margin-based items
            if year == 0:
                gross_profit = latest_revenue * self.assumptions["gross_margins"][0]
                ebitda = latest_revenue * self.assumptions["ebitda_margins"][0]
            elif year < len(self.assumptions["gross_margins"]) and year < len(self.assumptions["ebitda_margins"]):
                gross_profit = revenue * self.assumptions["gross_margins"][min(year, len(self.assumptions["gross_margins"]) - 1)]
                ebitda = revenue * self.assumptions["ebitda_margins"][min(year, len(self.assumptions["ebitda_margins"]) - 1)]
            else:
                # Use last available margin for years beyond explicit forecast
                gross_profit = revenue * self.assumptions["gross_margins"][-1]
                ebitda = revenue * self.assumptions["ebitda_margins"][-1]
            
            # Net income (simplified)
            depreciation = ebitda * 0.2  # Assumption: D&A is 20% of EBITDA
            ebit = ebitda - depreciation
            interest_expense = latest_total_debt * 0.05  # Assumption: 5% interest rate
            pre_tax_income = ebit - interest_expense
            tax = pre_tax_income * self.assumptions["tax_rate"]
            net_income = pre_tax_income - tax
            
            # === CASH FLOW ===
            # Operating cash flow (simplified)
            operating_cash_flow = net_income + depreciation
            
            # Capital expenditures
            capex = -revenue * self.assumptions["capex_percent_revenue"]  # Negative as it's cash outflow
            
            # Free cash flow
            free_cash_flow = operating_cash_flow + capex
            
            # Cash balance (simplified)
            if year == 0:
                cash = latest_cash
            else:
                prev_cash = cash_flow_df.loc[year - 1, "cash"]
                cash = prev_cash + free_cash_flow
            
            # === BALANCE SHEET ===
            # Assets (simplified)
            if year == 0:
                total_assets = latest_total_assets
            else:
                prev_assets = balance_df.loc[year - 1, "total_assets"]
                total_assets = prev_assets + free_cash_flow  # Simplified: assets grow by FCF
            
            # Debt (constant for simplicity)
            total_debt = latest_total_debt
            
            # Equity (balancing item)
            total_equity = total_assets - total_debt
            total_liabilities = total_debt  # Simplified: all liabilities are debt
            
            # Add to DataFrames
            income_df.loc[year, "revenue"] = revenue
            income_df.loc[year, "gross_profit"] = gross_profit
            income_df.loc[year, "ebitda"] = ebitda
            income_df.loc[year, "depreciation"] = depreciation
            income_df.loc[year, "ebit"] = ebit
            income_df.loc[year, "interest_expense"] = interest_expense
            income_df.loc[year, "pre_tax_income"] = pre_tax_income
            income_df.loc[year, "tax"] = tax
            income_df.loc[year, "net_income"] = net_income
            
            cash_flow_df.loc[year, "operating_cash_flow"] = operating_cash_flow
            cash_flow_df.loc[year, "capex"] = capex
            cash_flow_df.loc[year, "free_cash_flow"] = free_cash_flow
            cash_flow_df.loc[year, "cash"] = cash
            
            balance_df.loc[year, "total_assets"] = total_assets
            balance_df.loc[year, "total_liabilities"] = total_liabilities
            balance_df.loc[year, "total_debt"] = total_debt
            balance_df.loc[year, "total_equity"] = total_equity
        
        # Store forecast DataFrames
        self.income_statement = income_df
        self.balance_sheet = balance_df
        self.cash_flow = cash_flow_df
    
    def _get_default_assumptions(self) -> Dict[str, Any]:
        """Get default model assumptions"""
        return {
            "revenue_growth_rates": [0.05, 0.05, 0.04, 0.03, 0.03],
            "terminal_growth_rate": 0.02,
            "gross_margins": [0.40, 0.40, 0.41, 0.41, 0.42],
            "ebitda_margins": [0.15, 0.15, 0.16, 0.16, 0.17],
            "receivable_days": 45,
            "inventory_days": 60,
            "payable_days": 30,
            "capex_percent_revenue": 0.05,
            "discount_rate": 0.10,
            "tax_rate": 0.25,
            "ev_to_ebitda_multiple": 10.0,
            "lbo_exit_multiple": 8.0,
            "lbo_years": 5,
            "debt_to_ebitda": 4.0
        }
    
    def _get_company_name(self) -> str:
        """Extract company name from company data"""
        profile = self.company_data.get("profile", {})
        return profile.get("name", self.ticker)
    
    async def _get_trading_comps(self) -> List[Dict[str, Any]]:
        """
        Get trading comparables data for peer companies.
        
        Returns:
            List of dictionaries with peer company data
        """
        peers = self.company_data.get("sector_peers", [])
        trading_comps = []
        
        if not self.data_provider: # Should always be initialized, but as a safe guard
            print("Warning: Data provider not available in ValuationEngine for fetching trading comps.")
            return trading_comps

        for peer_ticker in peers[:5]:  # Limit to top 5 peers for performance
            try:
                peer_profile = await self.data_provider.get_company_profile(peer_ticker)
                peer_metrics_list = await self.data_provider.get_key_metrics(peer_ticker, period='annual') # FMP returns list
                
                # FMP key_metrics usually returns a list with one item for the most recent period
                peer_metrics = {}
                if isinstance(peer_metrics_list, list) and len(peer_metrics_list) > 0:
                    peer_metrics = peer_metrics_list[0]
                elif isinstance(peer_metrics_list, dict): # SEC provider might return dict directly
                    peer_metrics = peer_metrics_list

                name = peer_profile.get("companyName", peer_profile.get("name", peer_ticker))
                
                # FMP specific field names, SEC might differ or not provide all
                ev_to_ebitda = peer_metrics.get("enterpriseValueOverEBITDA", 0.0)
                ev_to_revenue = peer_metrics.get("evToSales", peer_metrics.get("enterpriseValueOverSales", 0.0))
                price_to_earnings = peer_metrics.get("peRatio", peer_metrics.get("priceEarningsRatio", 0.0))
                debt_to_ebitda = peer_metrics.get("debtToEbitda", 0.0)

                trading_comps.append({
                    "ticker": peer_ticker,
                    "name": name,
                    "ev_to_ebitda": float(ev_to_ebitda) if ev_to_ebitda else 0.0,
                    "ev_to_revenue": float(ev_to_revenue) if ev_to_revenue else 0.0,
                    "price_to_earnings": float(price_to_earnings) if price_to_earnings else 0.0,
                    "debt_to_ebitda": float(debt_to_ebitda) if debt_to_ebitda else 0.0
                })
            except Exception as e:
                print(f"Warning: Could not fetch data for peer {peer_ticker}: {e}")
                # Optionally append with placeholder/default values if a peer fails
                trading_comps.append({
                    "ticker": peer_ticker,
                    "name": peer_ticker,
                    "ev_to_ebitda": 0.0,
                    "ev_to_revenue": 0.0,
                    "price_to_earnings": 0.0,
                    "debt_to_ebitda": 0.0
                })
        
        return trading_comps
    
    def _calculate_valuation_range(self, dcf_price: float, comps_price: float) -> Dict[str, float]:
        """
        Calculate valuation range based on different methods.
        
        Args:
            dcf_price: Price per share from DCF valuation
            comps_price: Price per share from trading comps valuation
            
        Returns:
            Dictionary with valuation range metrics
        """
        # Calculate range based on DCF and comps valuation
        min_price = min(dcf_price, comps_price) * 0.9  # 10% below minimum
        max_price = max(dcf_price, comps_price) * 1.1  # 10% above maximum
        avg_price = (dcf_price + comps_price) / 2
        
        return {
            "min_price": min_price,
            "max_price": max_price,
            "avg_price": avg_price,
            "dcf_price": dcf_price,
            "comps_price": comps_price
        } 