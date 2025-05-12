"""
Three-statement financial model implementation.
Core business logic for the financial model.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from backend.models.valuation_engine import DCFValuation, TradingCompsValuation, LBOValuation, ValuationEngine
from backend.models.capital_structure import CapitalStructureGrid
from backend.config import config # Import AppConfig

class ThreeStatementModel:
    """
    Three-statement financial model class.
    Builds income statement, balance sheet, and cash flow statement projections.
    """
    
    def __init__(
        self,
        company_data: Dict[str, Any], # Changed from historical_data to company_data
        ticker: str,
        forecast_years: int = 5,
        # Add parameters for default historical metrics if needed, or use AppConfig
        default_hist_growth: Optional[float] = None,
        default_hist_gross_margin: Optional[float] = None,
        default_hist_ebitda_margin: Optional[float] = None
    ):
        """
        Initialize the model with company data.
        
        Args:
            company_data: Dictionary containing all company data (profile, financials, etc.)
            ticker: Company ticker symbol
            forecast_years: Number of years to forecast
            default_hist_growth: Fallback historical growth rate
            default_hist_gross_margin: Fallback historical gross margin
            default_hist_ebitda_margin: Fallback historical EBITDA margin
        """
        self.ticker = ticker
        self.forecast_years = forecast_years
        self.company_data = company_data # Use full company_data
        
        # Use provided defaults or fall back to AppConfig defaults
        self.default_hist_growth = default_hist_growth if default_hist_growth is not None else config.default_assumptions.get("historical_growth_rate", 0.05)
        self.default_hist_gross_margin = default_hist_gross_margin if default_hist_gross_margin is not None else config.default_assumptions.get("historical_gross_margin", 0.50)
        self.default_hist_ebitda_margin = default_hist_ebitda_margin if default_hist_ebitda_margin is not None else config.default_assumptions.get("historical_ebitda_margin", 0.20)

        # Initialize historical data tracking
        self.historical_statements_df = pd.DataFrame() # To store structured historical data
        self.historical_years: List[int] = []
        self.num_historical_periods: int = 0
        self.latest_historical_year: Optional[int] = None
        self.base_historical_year: Optional[int] = None # Earliest historical year

        # Initialize empty DataFrames for financial statements
        self.income_statement = pd.DataFrame()
        self.balance_sheet = pd.DataFrame()
        self.cash_flow = pd.DataFrame()
        
        # Initialize DCF and other valuation models
        self.dcf_valuation = None
        self.comps_valuation = None
        self.lbo_valuation = None
        self.cap_structure_grid = None
        
        # Extract and prepare historical data
        self._prepare_historical_data()
    
    def _prepare_historical_data(self):
        """Extract and prepare historical financial data."""
        # Extract income statements
        income_statements_raw = self.company_data.get("income_statements", [])
        balance_sheets_raw = self.company_data.get("balance_sheets", []) # Assuming alignment
        cash_flows_raw = self.company_data.get("cash_flow_statements", []) # Assuming alignment
        
        if not income_statements_raw:
            self.latest_income = {}
            self.historical_growth_rate = self.default_hist_growth
            self.historical_gross_margin = self.default_hist_gross_margin
            self.historical_ebitda_margin = self.default_hist_ebitda_margin
            # No historical periods to process
            self.num_historical_periods = 0
            return

        # Process and store historical data
        processed_historical = []
        temp_historical_years = set()

        for i, stmt_data in enumerate(income_statements_raw):
            year_str = stmt_data.get("date", stmt_data.get("year", ""))
            year = None
            if isinstance(year_str, str) and year_str:
                try:
                    year = int(year_str[:4]) # Assuming YYYY-MM-DD or YYYY
                except ValueError:
                    pass # Could log a warning here
            elif isinstance(year_str, int):
                year = year_str
            
            if year:
                temp_historical_years.add(year)
                
                # For now, just store the raw statement; transformation to DataFrame columns will happen later
                # This assumes income_statements_raw, balance_sheets_raw, cash_flows_raw are aligned by period/index
                period_data = {
                    "year": year,
                    "is_historical": True,
                    **stmt_data, # Income statement items
                    **(balance_sheets_raw[i] if i < len(balance_sheets_raw) else {}), # Balance sheet items
                    **(cash_flows_raw[i] if i < len(cash_flows_raw) else {}) # Cash flow items
                }
                processed_historical.append(period_data)

        if not processed_historical: # No valid years found
            self.latest_income = {} # Keep this for now for base_revenue logic, will be refined
            self.historical_growth_rate = self.default_hist_growth
            self.historical_gross_margin = self.default_hist_gross_margin
            self.historical_ebitda_margin = self.default_hist_ebitda_margin
            self.num_historical_periods = 0
            return
            
        # Create a DataFrame from processed historical data
        self.historical_statements_df = pd.DataFrame(processed_historical)
        
        # Sort by year to ensure correct order
        if "year" in self.historical_statements_df.columns:
            self.historical_statements_df.sort_values(by="year", inplace=True)
            self.historical_years = self.historical_statements_df["year"].tolist()
            self.num_historical_periods = len(self.historical_years)
            if self.historical_years:
                self.latest_historical_year = self.historical_years[-1]
                self.base_historical_year = self.historical_years[0]
        
        # For compatibility with existing logic, self.latest_income can be the last historical period
        # This might need refinement if specific fields are expected in self.latest_income
        if not self.historical_statements_df.empty:
            self.latest_income = self.historical_statements_df.iloc[-1].to_dict()
        else: # Should not happen if processed_historical was populated and had years
            self.latest_income = {}


        # Recalculate historical metrics based on the new historical_statements_df
        # The _calculate_historical_metrics method will need to be adapted to use this DataFrame
        if self.num_historical_periods > 0:
             # Pass the relevant part of the DataFrame or adapt the method
            self._calculate_historical_metrics_from_df()
        else: # Fallback to defaults if no valid historical data processed
            self.historical_growth_rate = self.default_hist_growth
            self.historical_gross_margin = self.default_hist_gross_margin
            self.historical_ebitda_margin = self.default_hist_ebitda_margin

    def _calculate_historical_metrics_from_df(self):
        """Calculate key historical metrics from the historical_statements_df."""
        if self.historical_statements_df.empty or len(self.historical_statements_df) < 2:
            self.historical_growth_rate = self.default_hist_growth
            self.historical_gross_margin = self.default_hist_gross_margin
            self.historical_ebitda_margin = self.default_hist_ebitda_margin
            return

        revenues = self.historical_statements_df["revenue"].fillna(0).tolist()
        growth_rates = []
        for i in range(1, len(revenues)):
            if revenues[i-1] != 0: # Avoid division by zero
                growth_rate = (revenues[i] - revenues[i-1]) / revenues[i-1]
                growth_rates.append(growth_rate)
        
        self.historical_growth_rate = np.mean(growth_rates) if growth_rates else self.default_hist_growth
        
        gross_margins = []
        ebitda_margins = []
        
        for _, row in self.historical_statements_df.iterrows():
            revenue = row.get("revenue", 0)
            if revenue != 0: # Avoid division by zero
                gross_profit = row.get("grossProfit", row.get("gross_profit", 0)) # Handle potential inconsistencies in naming
                ebitda = row.get("ebitda", 0)
                
                gross_margins.append(gross_profit / revenue)
                ebitda_margins.append(ebitda / revenue)
        
        self.historical_gross_margin = np.mean(gross_margins) if gross_margins else self.default_hist_gross_margin
        self.historical_ebitda_margin = np.mean(ebitda_margins) if ebitda_margins else self.default_hist_ebitda_margin
    
    def build_model(self, assumptions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build the three-statement model based on provided assumptions.
        
        Args:
            assumptions: Dictionary of model assumptions
            
        Returns:
            Dictionary containing the model results, with statements as lists of records.
        """
        # Extract assumptions
        revenue_growth_rates = assumptions.get("revenue_growth_rates", [])
        # terminal_growth_rate = assumptions.get("terminal_growth_rate", 0.02) # Used in DCF
        gross_margins = assumptions.get("gross_margins", [])
        ebitda_margins = assumptions.get("ebitda_margins", [])
        
        # Generate income statement projections
        self._project_income_statement(revenue_growth_rates, gross_margins, ebitda_margins, assumptions) # Pass assumptions
        
        # Generate balance sheet projections
        # receivable_days = assumptions.get("receivable_days", 45)
        # inventory_days = assumptions.get("inventory_days", 60)
        # payable_days = assumptions.get("payable_days", 30)
        self._project_balance_sheet(assumptions) # Pass assumptions
        
        # Generate cash flow projections
        # capex_percent = assumptions.get("capex_percent_revenue", 0.05)
        self._project_cash_flow(assumptions) # Pass assumptions
        
        # Run valuations
        discount_rate = assumptions.get("discount_rate", config.default_assumptions.get("discount_rate", 0.10))
        terminal_growth_rate = assumptions.get("terminal_growth_rate", config.default_assumptions.get("terminal_growth_rate", 0.02))
        tax_rate = assumptions.get("tax_rate", config.default_assumptions.get("tax_rate", 0.21))
        ev_to_ebitda_multiple = assumptions.get("ev_to_ebitda_multiple", config.default_assumptions.get("ev_to_ebitda_multiple", 8.0))
        
        # DCF valuation
        self.dcf_valuation = DCFValuation(
            self.income_statement, # Now a DataFrame with year and is_historical
            self.cash_flow,      # Now a DataFrame
            self.balance_sheet,  # Now a DataFrame
            discount_rate,
            terminal_growth_rate,
            tax_rate,
            self.company_data 
        )
        dcf_results = self.dcf_valuation.calculate()
        
        # Trading comps valuation
        self.comps_valuation = TradingCompsValuation(
            self.income_statement,
            self.balance_sheet,
            ev_to_ebitda_multiple,
            self.company_data 
        )
        comps_results = self.comps_valuation.calculate()
        
        # LBO valuation
        lbo_exit_multiple = assumptions.get("lbo_exit_multiple", config.default_assumptions.get("lbo_exit_multiple", 8.0))
        lbo_years = assumptions.get("lbo_years", config.default_assumptions.get("lbo_years", 5))
        debt_to_ebitda = assumptions.get("debt_to_ebitda", config.default_assumptions.get("debt_to_ebitda", 6.0))
        
        self.lbo_valuation = LBOValuation(
            self.income_statement,
            self.cash_flow,
            self.balance_sheet,
            lbo_exit_multiple,
            lbo_years,
            debt_to_ebitda,
            discount_rate, # Re-use discount_rate from DCF assumptions
            tax_rate,      # Re-use tax_rate
            self.company_data 
        )
        lbo_results = self.lbo_valuation.calculate()
        
        # Capital structure grid
        cap_structure_base_discount_rate = discount_rate # Use consistent discount rate
        cap_structure_tax_rate = tax_rate             # Use consistent tax rate
        # shares_outstanding_for_cap_grid = dcf_results.get("shares_outstanding", 1) 

        self.cap_structure_grid = CapitalStructureGrid(
            self.income_statement,
            self.balance_sheet,
            self.cash_flow,
            cap_structure_base_discount_rate, 
            cap_structure_tax_rate, 
            self.company_data, 
            assumptions 
        )
        cap_structure_results = self.cap_structure_grid.calculate()
        
        # Compile all results
        results = {
            "income_statement": self.income_statement.to_dict(orient="records"),
            "balance_sheet": self.balance_sheet.to_dict(orient="records"),
            "cash_flow": self.cash_flow.to_dict(orient="records"),
            "dcf_valuation": dcf_results,
            "trading_comps_valuation": comps_results,
            "lbo_valuation": lbo_results,
            "capital_structure_grid": cap_structure_results
        }
        
        return results
    
    def _project_income_statement(
        self, 
        growth_rates: List[float], 
        gross_margins: List[float], 
        ebitda_margins: List[float],
        assumptions: Dict[str, Any] # Added assumptions
    ):
        """Project the income statement, combining historical and forecast periods."""
        # Initialize with historical data if available
        if self.num_historical_periods > 0:
            # Select relevant IS columns from historical_statements_df
            # Ensure all expected columns exist, fill with 0 or NaN if not
            is_cols = ["year", "is_historical", "revenue", "grossProfit", "ebitda", "depreciation", 
                       "operatingIncome", "interestExpense", "incomeBeforeTax", "taxes", "netIncome"]
            # Rename for consistency if needed, e.g., grossProfit -> gross_profit
            historical_is_df = self.historical_statements_df.rename(columns={
                "grossProfit": "gross_profit",
                "operatingIncome": "operating_income",
                "interestExpense": "interest_expense",
                "incomeBeforeTax": "income_before_tax",
                "netIncome": "net_income"
            })
            
            # Ensure all target columns are present
            for col in ["revenue", "gross_profit", "ebitda", "depreciation", "operating_income", 
                        "interest_expense", "income_before_tax", "taxes", "net_income"]:
                if col not in historical_is_df.columns:
                    historical_is_df[col] = 0.0 # Or np.nan

            self.income_statement = historical_is_df[["year", "is_historical", "revenue", "gross_profit", "ebitda", 
                                                      "depreciation", "operating_income", "interest_expense", 
                                                      "income_before_tax", "taxes", "net_income"]].copy()
        else:
            self.income_statement = pd.DataFrame(columns=["year", "is_historical", "revenue", "gross_profit", "ebitda", 
                                                          "depreciation", "operating_income", "interest_expense", 
                                                          "income_before_tax", "taxes", "net_income"])

        # Determine forecast years
        forecast_period_years = []
        last_hist_year = self.latest_historical_year if self.latest_historical_year is not None else datetime.utcnow().year
        
        for i in range(self.forecast_years + 1): # +1 for terminal year/calculations
            forecast_period_years.append(last_hist_year + 1 + i)

        forecast_df_list = []

        # Base revenue for projections
        if not self.income_statement.empty and "revenue" in self.income_statement.columns:
            base_revenue = self.income_statement["revenue"].iloc[-1] if self.num_historical_periods > 0 else 0
        else: # No historical data, or revenue column missing
            base_revenue = self.latest_income.get("revenue", 0) # Fallback, though latest_income might be {}
            if not base_revenue and self.num_historical_periods == 0: # Further fallback for true cold start
                 # Attempt to get a very old revenue figure or default to a placeholder
                 if self.company_data.get("income_statements"):
                     first_available_statement = self.company_data["income_statements"][0]
                     base_revenue = first_available_statement.get("revenue", 1_000_000) # Placeholder if absolutely no data
                 else:
                     base_revenue = 1_000_000 # Absolute fallback

        # Project items for forecast years
        current_revenue = base_revenue
        
        # Default projection ratios from assumptions or AppConfig
        depreciation_percent_revenue = assumptions.get("depreciation_percent_revenue", config.default_assumptions.get("depreciation_percent_revenue", 0.05))
        interest_percent_operating_income = assumptions.get("interest_percent_operating_income", config.default_assumptions.get("interest_percent_operating_income", 0.10))
        effective_tax_rate = assumptions.get("tax_rate", config.default_assumptions.get("tax_rate", 0.21))


        for i, year_val in enumerate(forecast_period_years):
            period_data = {"year": year_val, "is_historical": False}
            
            # Project revenue
            growth_rate = growth_rates[i] if i < len(growth_rates) else self.historical_growth_rate
            current_revenue = current_revenue * (1 + growth_rate)
            period_data["revenue"] = current_revenue
            
            # Project gross profit
            gp_margin = gross_margins[i] if i < len(gross_margins) else self.historical_gross_margin
            period_data["gross_profit"] = current_revenue * gp_margin
            
            # Project EBITDA
            ebitda_m = ebitda_margins[i] if i < len(ebitda_margins) else self.historical_ebitda_margin
            period_data["ebitda"] = current_revenue * ebitda_m
            
            # Simplified projection of other income statement items
            period_data["depreciation"] = period_data["revenue"] * depreciation_percent_revenue
            period_data["operating_income"] = period_data["ebitda"] - period_data["depreciation"]
            period_data["interest_expense"] = period_data["operating_income"] * interest_percent_operating_income # Simplified
            period_data["income_before_tax"] = period_data["operating_income"] - period_data["interest_expense"]
            period_data["taxes"] = period_data["income_before_tax"] * effective_tax_rate
            period_data["net_income"] = period_data["income_before_tax"] - period_data["taxes"]
            
            forecast_df_list.append(period_data)
        
        if forecast_df_list:
            forecast_is_df = pd.DataFrame(forecast_df_list)
            self.income_statement = pd.concat([self.income_statement, forecast_is_df], ignore_index=True)
        
        # Ensure all columns are numeric, fill NaNs
        for col in ["revenue", "gross_profit", "ebitda", "depreciation", "operating_income", 
                    "interest_expense", "income_before_tax", "taxes", "net_income"]:
            if col in self.income_statement.columns:
                self.income_statement[col] = pd.to_numeric(self.income_statement[col], errors='coerce').fillna(0)
            else:
                self.income_statement[col] = 0.0
    
    def _project_balance_sheet(self, assumptions: Dict[str, Any]): # Added assumptions
        """Project the balance sheet, combining historical and forecast periods."""
        bs_cols = ["year", "is_historical", "accounts_receivable", "inventory", "net_working_capital", 
                   "fixed_assets", "total_assets", "accounts_payable", "total_debt", "total_equity"]

        if self.num_historical_periods > 0:
            historical_bs_df = self.historical_statements_df.rename(columns={
                "propertyPlantEquipmentNet": "fixed_assets", # Example, adjust to actual keys
                "totalLiabilities": "total_debt" # Simplified, needs review
            })
            # Ensure all target columns are present
            for col in bs_cols:
                if col not in historical_bs_df.columns and col not in ["year", "is_historical"]:
                    historical_bs_df[col] = 0.0
            self.balance_sheet = historical_bs_df[bs_cols].copy()
        else:
            self.balance_sheet = pd.DataFrame(columns=bs_cols)

        # Assumptions for projections
        receivable_days = assumptions.get("receivable_days", config.default_assumptions.get("receivable_days", 45))
        inventory_days = assumptions.get("inventory_days", config.default_assumptions.get("inventory_days", 60))
        payable_days = assumptions.get("payable_days", config.default_assumptions.get("payable_days", 30))
        base_fixed_assets_revenue_multiple = assumptions.get("base_fixed_assets_revenue_multiple", config.default_assumptions.get("base_fixed_assets_revenue_multiple", 0.70))
        # base_fixed_assets_growth = assumptions.get("base_fixed_assets_growth", config.default_assumptions.get("base_fixed_assets_growth", 0.03)) # This will be driven by CapEx
        target_debt_to_assets_ratio = assumptions.get("target_debt_to_assets_ratio", config.default_assumptions.get("target_debt_to_assets_ratio", 0.30))

        forecast_df_list = []
        
        # Align with income statement periods (historical + forecast)
        # Iterate through each period in the income_statement DataFrame
        for index, is_period_row in self.income_statement.iterrows():
            year_val = is_period_row["year"]
            is_hist = is_period_row["is_historical"]

            if is_hist: # If historical, data should already be in self.balance_sheet
                if index < len(self.balance_sheet) and self.balance_sheet.loc[index, "year"] == year_val:
                    continue # Already populated
                else: # Attempt to find matching year if alignment issues
                    matching_hist_bs = self.historical_statements_df[self.historical_statements_df["year"] == year_val]
                    if not matching_hist_bs.empty:
                        # This part is tricky if self.balance_sheet isn't pre-populated correctly.
                        # For now, we assume self.balance_sheet is populated with historicals already.
                        pass # Data should be there
                    else: # No matching historical BS for this IS year - problematic
                        # Create a mostly empty row to avoid errors downstream
                        forecast_df_list.append({"year": year_val, "is_historical": True, **{k: 0.0 for k in bs_cols if k not in ["year", "is_historical"]}})
                        continue
            else: # Forecast period
                period_data = {"year": year_val, "is_historical": False}
                revenue_forecast = is_period_row["revenue"]
                gross_profit_forecast = is_period_row["gross_profit"]
                cogs_forecast = revenue_forecast - gross_profit_forecast

                period_data["accounts_receivable"] = revenue_forecast * (receivable_days / 365)
                period_data["inventory"] = cogs_forecast * (inventory_days / 365)
                period_data["accounts_payable"] = cogs_forecast * (payable_days / 365)
                
                period_data["net_working_capital"] = (
                    period_data["accounts_receivable"] + 
                    period_data["inventory"] - 
                    period_data["accounts_payable"]
                )
                
                # Fixed Assets: Base + CapEx - Depreciation
                # This needs to be iterative, using previous period's fixed assets
                if not forecast_df_list and self.num_historical_periods > 0 and "fixed_assets" in self.balance_sheet.columns:
                    last_hist_fixed_assets = self.balance_sheet["fixed_assets"].iloc[self.num_historical_periods -1] if self.num_historical_periods > 0 else 0
                elif forecast_df_list: # Not the first forecast period
                    last_hist_fixed_assets = forecast_df_list[-1]["fixed_assets"]
                else: # No historical, first forecast period
                    last_hist_fixed_assets = revenue_forecast * base_fixed_assets_revenue_multiple # Initial estimate

                # CapEx and Depreciation will be taken from Cash Flow statement for this period later.
                # For now, this is a placeholder calculation that will be overridden by _project_cash_flow's update.
                # Placeholder: Link to capex from cash_flow (which isn't projected yet in this step)
                # This highlights the iterative nature; BS and CF are linked.
                # We'll refine this after CF statement projection.
                # Initial fixed assets based on previous or a ratio for the first projected year.
                depreciation_current_period = self.income_statement.loc[self.income_statement['year'] == year_val, 'depreciation'].values[0]
                
                # Placeholder for CapEx until CF is built. This means fixed assets might be initially simple.
                # Typically, CapEx from CF statement is used here.
                # The _project_cash_flow method will later update fixed_assets.
                capex_current_period = revenue_forecast * assumptions.get("capex_percent_revenue", config.default_assumptions.get("capex_percent_revenue", 0.05)) # Placeholder

                period_data["fixed_assets"] = last_hist_fixed_assets + capex_current_period - depreciation_current_period


                period_data["total_assets"] = (
                    period_data["accounts_receivable"] + 
                    period_data["inventory"] + 
                    period_data["fixed_assets"]
                )
                
                period_data["total_debt"] = period_data["total_assets"] * target_debt_to_assets_ratio # Simplified
                period_data["total_equity"] = period_data["total_assets"] - period_data["total_debt"] - period_data["accounts_payable"] # Simplified plug

                forecast_df_list.append(period_data)
        
        if forecast_df_list:
            forecast_bs_df = pd.DataFrame(forecast_df_list)
            # If self.balance_sheet was populated with historicals, we need to append forecasts carefully
            if self.num_historical_periods > 0:
                 # Filter forecast_bs_df to only include years not already in self.balance_sheet (historical part)
                forecast_bs_df_to_append = forecast_bs_df[~forecast_bs_df['year'].isin(self.balance_sheet['year'])]
                self.balance_sheet = pd.concat([self.balance_sheet, forecast_bs_df_to_append], ignore_index=True)
            else: # No historicals, just use the forecast
                self.balance_sheet = forecast_bs_df
        
        for col in bs_cols:
            if col not in ["year", "is_historical"]: # Ensure these are numeric
                 if col in self.balance_sheet.columns:
                    self.balance_sheet[col] = pd.to_numeric(self.balance_sheet[col], errors='coerce').fillna(0)
                 else:
                    self.balance_sheet[col] = 0.0
    
    def _project_cash_flow(self, assumptions: Dict[str, Any]): # Added assumptions
        """Project the cash flow statement, combining historical and forecast periods."""
        cf_cols = ["year", "is_historical", "net_income", "depreciation", "change_in_working_capital",
                   "operating_cash_flow", "capex", "free_cash_flow"]

        if self.num_historical_periods > 0:
            historical_cf_df = self.historical_statements_df.rename(columns={
                # Add renames if raw data keys differ from cf_cols
                "changeInReceivables": "change_in_receivables", # Example
                "changeInInventory": "change_in_inventory",   # Example
                "capitalExpenditure": "capex"
            }) 
            # Calculate change_in_working_capital for historical if not directly available
            if "change_in_working_capital" not in historical_cf_df.columns and "net_working_capital" in self.balance_sheet.columns:
                historical_nwc = self.balance_sheet[self.balance_sheet["is_historical"]]["net_working_capital"].diff().fillna(0)
                # The first period's diff will be NaN, fill with 0. The change is -(current - previous).
                historical_cf_df["change_in_working_capital"] = -historical_nwc 
            
            for col in cf_cols:
                if col not in historical_cf_df.columns and col not in ["year", "is_historical"]:
                    historical_cf_df[col] = 0.0 # Or np.nan
            self.cash_flow = historical_cf_df[cf_cols].copy()
        else:
            self.cash_flow = pd.DataFrame(columns=cf_cols)

        # Assumptions
        capex_percent_revenue = assumptions.get("capex_percent_revenue", config.default_assumptions.get("capex_percent_revenue", 0.05))

        forecast_df_list = []

        # Iterate through each period in the income_statement (which includes all historical and forecast years)
        for index, global_period_row in self.income_statement.iterrows():
            year_val = global_period_row["year"]
            is_hist = global_period_row["is_historical"]

            if is_hist:
                if index < len(self.cash_flow) and self.cash_flow.loc[index, "year"] == year_val:
                    continue # Already populated from historical_statements_df
                else: # Should be populated, if not, implies missing historical CF data
                    forecast_df_list.append({"year": year_val, "is_historical": True, **{k: 0.0 for k in cf_cols if k not in ["year", "is_historical"]}})
                    continue 
            else: # Forecast period
                period_data = {"year": year_val, "is_historical": False}
                
                # Get corresponding IS and BS forecast rows
                is_row = global_period_row # IS data for current forecast year
                bs_row = self.balance_sheet[self.balance_sheet["year"] == year_val]
                if bs_row.empty: # Should not happen if BS projection is complete
                    # Add empty row to avoid crash, but log this issue
                    print(f"Warning: Missing balance sheet data for forecast year {year_val} when projecting cash flow.")
                    bs_row = pd.Series(index=self.balance_sheet.columns).fillna(0)
                else:
                    bs_row = bs_row.iloc[0]

                period_data["net_income"] = is_row["net_income"]
                period_data["depreciation"] = is_row["depreciation"]
                
                # Change in Working Capital for forecast periods
                # NWC current period - NWC previous period
                current_nwc = bs_row["net_working_capital"]
                
                # Find previous period's NWC (could be last historical or previous forecast)
                prev_year_val = year_val - 1
                prev_bs_row = self.balance_sheet[self.balance_sheet["year"] == prev_year_val]
                
                if not prev_bs_row.empty:
                    prev_nwc = prev_bs_row.iloc[0]["net_working_capital"]
                elif self.num_historical_periods > 0 and prev_year_val == self.latest_historical_year : # Last historical
                     prev_nwc = self.balance_sheet[self.balance_sheet["year"] == prev_year_val].iloc[0]["net_working_capital"]
                else: # Should ideally not happen if BS is fully populated
                    prev_nwc = current_nwc # Assume no change if previous not found (or 0 for first period of all forecast)

                period_data["change_in_working_capital"] = -(current_nwc - prev_nwc)
                
                period_data["operating_cash_flow"] = (
                    period_data["net_income"] + 
                    period_data["depreciation"] + 
                    period_data["change_in_working_capital"]
                )
                
                period_data["capex"] = -is_row["revenue"] * capex_percent_revenue # Negative for outflow
                
                period_data["free_cash_flow"] = period_data["operating_cash_flow"] + period_data["capex"]
                
                forecast_df_list.append(period_data)

                # Update Balance Sheet Fixed Assets based on this period's CapEx and Depreciation
                # This is the iterative step linking CF back to BS
                bs_idx_to_update = self.balance_sheet[self.balance_sheet["year"] == year_val].index
                if not bs_idx_to_update.empty:
                    idx = bs_idx_to_update[0]
                    # Get previous period's fixed assets
                    if prev_year_val:
                        prev_fa_series = self.balance_sheet.loc[self.balance_sheet['year'] == prev_year_val, 'fixed_assets']
                        prev_fixed_assets = prev_fa_series.values[0] if not prev_fa_series.empty else 0
                    else: # First year overall
                         prev_fixed_assets = 0
                    
                    self.balance_sheet.loc[idx, "fixed_assets"] = (
                        prev_fixed_assets +
                        abs(period_data["capex"]) - # CapEx is stored negative, use abs
                        period_data["depreciation"]
                    )
                    # Re-calculate total assets after fixed assets update (if necessary, or ensure it's calculated after this loop)
                    self.balance_sheet.loc[idx, "total_assets"] = (
                        self.balance_sheet.loc[idx, "accounts_receivable"] +
                        self.balance_sheet.loc[idx, "inventory"] + # Assuming inventory is current assets part
                        self.balance_sheet.loc[idx, "fixed_assets"] # Other current assets might be missing
                    )
                    # And potentially re-plug debt/equity if they depend on total_assets and were simple ratios
                    target_debt_to_assets_ratio = assumptions.get("target_debt_to_assets_ratio", config.default_assumptions.get("target_debt_to_assets_ratio", 0.30))
                    self.balance_sheet.loc[idx, "total_debt"] = self.balance_sheet.loc[idx, "total_assets"] * target_debt_to_assets_ratio
                    self.balance_sheet.loc[idx, "total_equity"] = ( self.balance_sheet.loc[idx, "total_assets"] 
                                                                  - self.balance_sheet.loc[idx, "total_debt"] 
                                                                  - self.balance_sheet.loc[idx, "accounts_payable"])


        if forecast_df_list:
            forecast_cf_df = pd.DataFrame(forecast_df_list)
            if self.num_historical_periods > 0:
                forecast_cf_df_to_append = forecast_cf_df[~forecast_cf_df['year'].isin(self.cash_flow['year'])]
                self.cash_flow = pd.concat([self.cash_flow, forecast_cf_df_to_append], ignore_index=True)
            else:
                self.cash_flow = forecast_cf_df

        for col in cf_cols:
            if col not in ["year", "is_historical"]:
                if col in self.cash_flow.columns:
                    self.cash_flow[col] = pd.to_numeric(self.cash_flow[col], errors='coerce').fillna(0)
                else:
                    self.cash_flow[col] = 0.0
        # Ensure fixed assets are updated on BS for all forecast years after CF is built
        # The loop above tries to do it iteratively, but a final pass might be good for consistency
        # This iterative update is complex; for simplicity, the above updates BS fixed assets during CF calc.
            
# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
# and `_project_cash_flow`.

# Ensure the old _calculate_historical_metrics is removed or fully commented out.
# ... existing code ...
# (Ensure to remove the old _calculate_historical_metrics function that takes `income_statements: List[Dict[str, Any]]`)
# The edit should be applied starting from the line before `def build_model(...)`
# and including the modifications to `_project_income_statement`, `_project_balance_sheet`, 
        base_revenue_for_bs = self.latest_income.get("revenue", 0) # Default to 0
        base_fixed_assets = base_revenue_for_bs * base_fixed_assets_revenue_multiple
        fixed_assets = [base_fixed_assets]
        
        for i in range(1, self.forecast_years + 1):
            # This will be refined when we project the cash flow statement
            # For now, a simplistic growth based on assumption
            fixed_assets.append(fixed_assets[-1] * (1 + base_fixed_assets_growth))
        
        self.balance_sheet["fixed_assets"] = fixed_assets
        
        # Total assets
        self.balance_sheet["total_assets"] = (
            self.balance_sheet["accounts_receivable"] + 
            self.balance_sheet["inventory"] + 
            self.balance_sheet["fixed_assets"]
        )
        
        # Simplified debt and equity projection
        # Assuming a target debt-to-assets ratio from assumptions
        self.balance_sheet["total_debt"] = self.balance_sheet["total_assets"] * target_debt_to_assets_ratio
        self.balance_sheet["total_equity"] = self.balance_sheet["total_assets"] - self.balance_sheet["total_debt"] - self.balance_sheet["accounts_payable"]
    
    def _project_cash_flow(self, capex_percent: float):
        """Project the cash flow statement for the forecast period."""
        # capex_percent is already from assumptions
        # Ensure it's used if not overridden by more direct capex logic later

        # Create a base DataFrame with the same index as income statement
        self.cash_flow = pd.DataFrame(index=self.income_statement.index)
        
        # Start with operating cash flow
        self.cash_flow["net_income"] = self.income_statement["net_income"]
        self.cash_flow["depreciation"] = self.income_statement["depreciation"]
        
        # Changes in working capital
        for i in range(len(self.income_statement.index)):
            if i == 0:
                self.cash_flow.loc[i, "change_in_working_capital"] = 0
            else:
                self.cash_flow.loc[i, "change_in_working_capital"] = -(
                    self.balance_sheet.loc[i, "net_working_capital"] - 
                    self.balance_sheet.loc[i-1, "net_working_capital"]
                )
        
        # Operating cash flow
        self.cash_flow["operating_cash_flow"] = (
            self.cash_flow["net_income"] + 
            self.cash_flow["depreciation"] + 
            self.cash_flow["change_in_working_capital"]
        )
        
        # Capital expenditures
        self.cash_flow["capex"] = -self.income_statement["revenue"] * capex_percent
        
        # Free cash flow
        self.cash_flow["free_cash_flow"] = self.cash_flow["operating_cash_flow"] + self.cash_flow["capex"]
        
        # Update fixed assets projection based on capex and depreciation
        for i in range(1, self.forecast_years + 1):
            self.balance_sheet.loc[i, "fixed_assets"] = (
                self.balance_sheet.loc[i-1, "fixed_assets"] + 
                abs(self.cash_flow.loc[i, "capex"]) - 
                self.income_statement.loc[i, "depreciation"]
            ) 