"""
Three-statement financial model implementation.
Core business logic for the financial model.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from models.valuation_engine import DCFValuation, TradingCompsValuation, LBOValuation, ValuationEngine
from models.capital_structure import CapitalStructureGrid
from config import config # Import AppConfig

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
        """
        print(f"[build_model] Top: Raw assumptions received: {assumptions}")

        # Resolve assumptions for VALUATIONS first
        discount_rate = assumptions.get("discount_rate")
        if discount_rate is None: discount_rate = config.default_assumptions.get("discount_rate", {}).get("wacc", {}).get("base_case", 0.10)
        print(f"[build_model] Using discount_rate for valuations: {discount_rate}")

        terminal_growth_rate = assumptions.get("terminal_growth_rate")
        if terminal_growth_rate is None: terminal_growth_rate = config.default_assumptions.get("terminal_growth_rate", {}).get("long_term_gdp_growth", 0.02)
        print(f"[build_model] Using terminal_growth_rate for valuations: {terminal_growth_rate}")

        # This tax_rate is specifically for valuation (e.g., NOPAT calc in DCF, LBO taxes)
        valuation_tax_rate = assumptions.get("tax_rate") 
        if valuation_tax_rate is None: valuation_tax_rate = config.default_assumptions.get("tax_rate", {}).get("effective_federal_state", 0.21)
        print(f"[build_model] Using tax_rate for valuations: {valuation_tax_rate}")

        ev_to_ebitda_multiple = assumptions.get("ev_to_ebitda_multiple")
        if ev_to_ebitda_multiple is None: ev_to_ebitda_multiple = config.default_assumptions.get("trading_multiples", {}).get("ev_to_ebitda", {}).get("median", 8.0)
        print(f"[build_model] Using ev_to_ebitda_multiple for valuations: {ev_to_ebitda_multiple}")
        
        lbo_exit_multiple = assumptions.get("lbo_exit_multiple")
        if lbo_exit_multiple is None: lbo_exit_multiple = config.default_assumptions.get("lbo", {}).get("exit_multiple", 8.0)
        print(f"[build_model] Using lbo_exit_multiple for valuations: {lbo_exit_multiple}")

        lbo_years = assumptions.get("lbo_years")
        if lbo_years is None: lbo_years = config.default_assumptions.get("lbo", {}).get("holding_period_years", 5)
        print(f"[build_model] Using lbo_years for valuations: {lbo_years}")

        lbo_debt_to_ebitda = assumptions.get("debt_to_ebitda") # For LBO entry
        if lbo_debt_to_ebitda is None: lbo_debt_to_ebitda = config.default_assumptions.get("lbo", {}).get("debt_to_ebitda", {}).get("initial", 3.0)
        print(f"[build_model] Using LBO debt_to_ebitda for valuations: {lbo_debt_to_ebitda}")

        # Now, resolve assumptions for PROJECTIONS (IS, BS, CF)
        revenue_growth_rates = assumptions.get("revenue_growth_rates", []) # Already a list
        gross_margins = assumptions.get("gross_margins", []) # Already a list
        ebitda_margins = assumptions.get("ebitda_margins", []) # Already a list
        
        # This tax_rate is for projecting income statement taxes
        projection_tax_rate = assumptions.get("tax_rate") 
        if projection_tax_rate is None: projection_tax_rate = config.default_assumptions.get("tax_rate", {}).get("effective_federal_state", 0.21)
        # Ensure it's a float if it comes from form as int/str for percentage
        # However, frontend should send it as decimal (e.g., 0.21 for 21%)
        print(f"[build_model] Using tax_rate for projections: {projection_tax_rate}")

        depreciation_percent_revenue = assumptions.get("depreciation_percent_revenue")
        if depreciation_percent_revenue is None: depreciation_percent_revenue = config.default_assumptions.get("financial_ratios", {}).get("depreciation_as_percent_of_revenue", 0.05)
        print(f"[build_model] Using depreciation_percent_revenue for projections: {depreciation_percent_revenue}")

        # Interest expense is complex; this is a simplification. Real model would use debt schedule.
        interest_percent_operating_income = assumptions.get("interest_percent_operating_income", 0.10) 
        if interest_percent_operating_income is None: interest_percent_operating_income = config.default_assumptions.get("financial_ratios", {}).get("interest_expense_as_percent_of_operating_income", 0.10)
        print(f"[build_model] Using interest_percent_operating_income for projections: {interest_percent_operating_income}")

        receivable_days = assumptions.get("receivable_days")
        if receivable_days is None: receivable_days = config.default_assumptions.get("working_capital", {}).get("receivables_days", 45)
        
        inventory_days = assumptions.get("inventory_days")
        if inventory_days is None: inventory_days = config.default_assumptions.get("working_capital", {}).get("inventory_days", 60)
        
        payable_days = assumptions.get("payable_days")
        if payable_days is None: payable_days = config.default_assumptions.get("working_capital", {}).get("payable_days", 30)

        capex_percent_revenue = assumptions.get("capex_percent_revenue") 
        if capex_percent_revenue is None: capex_percent_revenue = config.default_assumptions.get("capex", {}).get("capex_as_percent_of_revenue", {}).get("maintainance", 0.05)

        base_fixed_assets_revenue_multiple = assumptions.get("base_fixed_assets_revenue_multiple")
        if base_fixed_assets_revenue_multiple is None: base_fixed_assets_revenue_multiple = config.default_assumptions.get("balance_sheet_ratios", {}).get("fixed_assets_to_revenue", 0.70)

        # `debt_ratio` from form (e.g., 30 for 30%) is used as `target_debt_to_assets_ratio` (e.g., 0.30)
        target_debt_to_assets_ratio = assumptions.get("debt_ratio") 
        if target_debt_to_assets_ratio is None: 
            target_debt_to_assets_ratio = config.default_assumptions.get("capital_structure", {}).get("target_debt_to_total_capital", 0.30)
        else: 
            target_debt_to_assets_ratio = target_debt_to_assets_ratio / 100.0 # Convert percentage to decimal
        print(f"[build_model] Using target_debt_to_assets_ratio for BS projections: {target_debt_to_assets_ratio}")

        # Generate income statement projections
        self._project_income_statement(
            revenue_growth_rates, 
            gross_margins, 
            ebitda_margins, 
            projection_tax_rate, # Use the one resolved for projections
            depreciation_percent_revenue,
            interest_percent_operating_income
        )
        
        self._project_balance_sheet(
            receivable_days,
            inventory_days,
            payable_days,
            capex_percent_revenue, 
            base_fixed_assets_revenue_multiple,
            target_debt_to_assets_ratio
        )
        
        self._project_cash_flow(capex_percent_revenue, target_debt_to_assets_ratio)
        
        # DCF valuation (uses valuation_tax_rate)
        self.dcf_valuation = DCFValuation(
            self.income_statement, 
            self.cash_flow,      
            self.balance_sheet,  
            discount_rate, # Resolved for valuations
            terminal_growth_rate, # Resolved for valuations
            valuation_tax_rate, # Resolved for valuations (e.g., for NOPAT)
            self.company_data 
        )
        dcf_results = self.dcf_valuation.calculate()
        
        # Trading comps valuation
        self.comps_valuation = TradingCompsValuation(
            self.income_statement,
            self.balance_sheet,
            ev_to_ebitda_multiple, # Resolved for valuations
            self.company_data 
        )
        comps_results = self.comps_valuation.calculate()
        
        # LBO valuation (uses valuation_tax_rate)
        self.lbo_valuation = LBOValuation(
            self.income_statement,
            self.cash_flow,
            self.balance_sheet,
            lbo_exit_multiple, # Resolved for valuations
            lbo_years, # Resolved for valuations
            lbo_debt_to_ebitda, # Resolved for valuations
            discount_rate, 
            valuation_tax_rate, # Resolved for valuations     
            self.company_data 
        )
        lbo_results = self.lbo_valuation.calculate()
        
        # Capital structure grid (uses valuation related discount_rate and tax_rate)
        self.cap_structure_grid = CapitalStructureGrid(
            self.income_statement,
            self.balance_sheet,
            self.cash_flow,
            discount_rate, 
            valuation_tax_rate 
        )
        cap_structure_results = self.cap_structure_grid.calculate()
        
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
        effective_tax_rate: float, # Changed from assumptions: Dict
        depreciation_percent_revenue: float,
        interest_percent_operating_income: float
    ):
        """Project the income statement, combining historical and forecast periods."""
        # Add this print:
        print(f"[_project_income_statement] Received growth_rates: {growth_rates}, gross_margins: {gross_margins}, ebitda_margins: {ebitda_margins}")

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
        
        # Directly use passed-in resolved assumption values
        # depreciation_percent_revenue = assumptions.get("depreciation_percent_revenue", config.default_assumptions.get("depreciation_percent_revenue", 0.05))
        # interest_percent_operating_income = assumptions.get("interest_percent_operating_income", config.default_assumptions.get("interest_percent_operating_income", 0.10))
        # effective_tax_rate = assumptions.get("tax_rate", config.default_assumptions.get("tax_rate", 0.21))

        for i, year_val in enumerate(forecast_period_years):
            period_data = {"year": year_val, "is_historical": False}
            
            # Project revenue
            growth_rate = growth_rates[i] if i < len(growth_rates) else self.historical_growth_rate
            print(f"[_project_income_statement] Year {year_val} (idx {i}): Using growth_rate: {growth_rate}. From array: {i < len(growth_rates)}. Array val: {growth_rates[i] if i < len(growth_rates) else 'N/A'}. Historical: {self.historical_growth_rate}")
            current_revenue = current_revenue * (1 + growth_rate)
            period_data["revenue"] = current_revenue
            
            # Project gross profit
            gp_margin = gross_margins[i] if i < len(gross_margins) else self.historical_gross_margin
            print(f"[_project_income_statement] Year {year_val} (idx {i}): Using gp_margin: {gp_margin}. From array: {i < len(gross_margins)}. Array val: {gross_margins[i] if i < len(gross_margins) else 'N/A'}. Historical: {self.historical_gross_margin}")
            period_data["gross_profit"] = current_revenue * gp_margin
            
            # Project EBITDA
            ebitda_m = ebitda_margins[i] if i < len(ebitda_margins) else self.historical_ebitda_margin
            print(f"[_project_income_statement] Year {year_val} (idx {i}): Using ebitda_margin: {ebitda_m}. From array: {i < len(ebitda_margins)}. Array val: {ebitda_margins[i] if i < len(ebitda_margins) else 'N/A'}. Historical: {self.historical_ebitda_margin}")
            period_data["ebitda"] = current_revenue * ebitda_m
            
            # Project depreciation
            period_data["depreciation"] = period_data["revenue"] * depreciation_percent_revenue # USE RESOLVED
            period_data["operating_income"] = period_data["ebitda"] - period_data["depreciation"]
            period_data["interest_expense"] = period_data["operating_income"] * interest_percent_operating_income # USE RESOLVED (Note: placeholder logic for interest)
            period_data["income_before_tax"] = period_data["operating_income"] - period_data["interest_expense"]
            period_data["taxes"] = period_data["income_before_tax"] * effective_tax_rate # USE RESOLVED
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
    
    def _project_balance_sheet(
        self,
        receivable_days: float,
        inventory_days: float,
        payable_days: float,
        capex_percent_revenue: float, 
        base_fixed_assets_revenue_multiple: float,
        resolved_debt_ratio_for_bs: float 
    ): 
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

        forecast_df_list = []
        
        for index, is_period_row in self.income_statement.iterrows():
            year_val = is_period_row["year"]
            is_hist = is_period_row["is_historical"]

            if is_hist:
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
                elif forecast_df_list:
                    last_hist_fixed_assets = forecast_df_list[-1]["fixed_assets"]
                else: 
                    last_hist_fixed_assets = revenue_forecast * base_fixed_assets_revenue_multiple 
                
                depreciation_current_period = self.income_statement.loc[self.income_statement['year'] == year_val, 'depreciation'].values[0]
                capex_current_period = revenue_forecast * capex_percent_revenue 
                period_data["fixed_assets"] = last_hist_fixed_assets + capex_current_period - depreciation_current_period

                period_data["total_assets"] = (
                    period_data["accounts_receivable"] + 
                    period_data["inventory"] + 
                    period_data["fixed_assets"]
                )
                
                period_data["total_debt"] = period_data["total_assets"] * resolved_debt_ratio_for_bs 
                period_data["total_equity"] = period_data["total_assets"] - period_data["total_debt"] - period_data["accounts_payable"]

                forecast_df_list.append(period_data)
        
        if forecast_df_list:
            forecast_bs_df = pd.DataFrame(forecast_df_list)
            if self.num_historical_periods > 0:
                forecast_bs_df_to_append = forecast_bs_df[~forecast_bs_df['year'].isin(self.balance_sheet['year'])]
                self.balance_sheet = pd.concat([self.balance_sheet, forecast_bs_df_to_append], ignore_index=True)
            else: 
                self.balance_sheet = forecast_bs_df
        
        # Iterative updates after initial forecast_df_list is populated and self.balance_sheet is formed
        # This section updates BS based on CF, and might have the other uses of target_debt_to_assets_ratio
        for index, global_period_row in self.income_statement.iterrows():
            year_val = global_period_row["year"]
            is_hist = global_period_row["is_historical"]
            if is_hist: continue # Only for forecast periods

            bs_indices = self.balance_sheet[self.balance_sheet["year"] == year_val].index
            if not bs_indices.empty:
                idx = bs_indices[0]
                current_bs_row = self.balance_sheet.loc[idx]

                # This block is for all forecast periods AFTER the first one in the iterative refinement
                if index > self.num_historical_periods or (self.num_historical_periods == 0 and index > 0):
                    # ... (fixed asset updates using capex/depreciation from CF would happen here or in CF projection)
                    # Re-calculate total_assets if fixed_assets changed
                    self.balance_sheet.loc[idx, "total_assets"] = (
                        current_bs_row["net_working_capital"] + # Or current_bs_row["accounts_receivable"] + current_bs_row["inventory"]
                        current_bs_row["fixed_assets"] 
                        # Potentially add other current assets if modeled explicitly
                    )
                    total_assets_updated = self.balance_sheet.loc[idx, "total_assets"]
                    # Ensure this uses the new parameter name
                    self.balance_sheet.loc[idx, "total_debt"] = total_assets_updated * resolved_debt_ratio_for_bs
                    self.balance_sheet.loc[idx, "total_equity"] = total_assets_updated - self.balance_sheet.loc[idx, "total_debt"] - current_bs_row["accounts_payable"]
                elif self.num_historical_periods == 0 and index == 0: # Very first period of a no-history model
                    # This was handled in the initial loop, but ensure consistency if re-evaluating total_debt
                    total_assets_current_period = self.balance_sheet.loc[idx, "total_assets"]
                    # Ensure this uses the new parameter name
                    self.balance_sheet.loc[idx, "total_debt"] = total_assets_current_period * resolved_debt_ratio_for_bs
                    self.balance_sheet.loc[idx, "total_equity"] = total_assets_current_period - self.balance_sheet.loc[idx, "total_debt"] - self.balance_sheet.loc[idx, "accounts_payable"]

        for col in bs_cols:
            if col not in ["year", "is_historical"]: 
                 if col in self.balance_sheet.columns:
                    self.balance_sheet[col] = pd.to_numeric(self.balance_sheet[col], errors='coerce').fillna(0)
                 else:
                    self.balance_sheet[col] = 0.0
    
    def _project_cash_flow(self, capex_percent_revenue: float, resolved_debt_ratio_for_bs: float): 
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
                
                period_data["capex"] = -is_row["revenue"] * capex_percent_revenue # USE RESOLVED, ensure negative for outflow
                
                period_data["free_cash_flow"] = period_data["operating_cash_flow"] + period_data["capex"]
                
                forecast_df_list.append(period_data)

                # Update Balance Sheet Fixed Assets based on this period's CapEx and Depreciation
            # This is the iterative step linking Cash Flow and Balance Sheet
            # Find the corresponding row in the balance sheet
            bs_indices = self.balance_sheet[self.balance_sheet["year"] == year_val].index
            if not bs_indices.empty:
                idx = bs_indices[0]
                
                if index > 0: # Not first period
                    prev_year_val = year_val - 1
                    if self.num_historical_periods > 0 and prev_year_val == self.latest_historical_year:
                        # Get last historical fixed assets
                        prev_fa_series = self.balance_sheet.loc[self.balance_sheet['year'] == prev_year_val, 'fixed_assets']
                        prev_fixed_assets = prev_fa_series.values[0] if not prev_fa_series.empty else 0
                    else:
                         prev_fixed_assets = 0
                        
                    self.balance_sheet.loc[idx, "fixed_assets"] = (
                        prev_fixed_assets +
                        period_data["capex"] +  # Already negative for outflow
                        period_data["depreciation"] # Already negative for reduction
                    )
                    
                    # Update total assets
                    self.balance_sheet.loc[idx, "total_assets"] = (
                        bs_row["net_working_capital"] +
                        self.balance_sheet.loc[idx, "fixed_assets"] # Other current assets might be missing
                    )
                    
                    # Update total debt and equity based on target debt ratio
                    total_assets = self.balance_sheet.loc[idx, "total_assets"]
                    self.balance_sheet.loc[idx, "total_debt"] = total_assets * resolved_debt_ratio_for_bs # Use new_param_name
                    self.balance_sheet.loc[idx, "total_equity"] = total_assets - self.balance_sheet.loc[idx, "total_debt"]
                else:
                    # First forecast period - initialize based on revenue
                    base_revenue_for_bs = is_row["revenue"]
                    # base_fixed_assets_revenue_multiple is already a resolved parameter passed to this method
                    # No need to call assumptions.get here.
                    # base_fixed_assets_revenue_multiple = assumptions.get("base_fixed_assets_revenue_multiple", config.default_assumptions.get("base_fixed_assets_revenue_multiple", 0.70))
                    current_fixed_assets = base_revenue_for_bs * base_fixed_assets_revenue_multiple
                    self.balance_sheet.loc[idx, "fixed_assets"] = current_fixed_assets
                    
                    # Project forward based on growth was removed as it was using an undefined variable
                    # and fixed assets should be driven by capex and depreciation primarily.
                    # The iterative updates via _project_cash_flow handle this.
                    
                    # Update total assets for the first forecast period
                    self.balance_sheet.loc[idx, "total_assets"] = (
                        self.balance_sheet.loc[idx, "net_working_capital"] + # NWC for current year already calculated
                        current_fixed_assets
                    )
                    
                    # Update total debt and equity based on target ratio for the first forecast period
                    total_assets_current_period = self.balance_sheet.loc[idx, "total_assets"]
                    self.balance_sheet.loc[idx, "total_debt"] = total_assets_current_period * resolved_debt_ratio_for_bs # Use new_param_name
                    self.balance_sheet.loc[idx, "total_equity"] = total_assets_current_period - self.balance_sheet.loc[idx, "total_debt"]

        # Combine historical and forecast periods
        if forecast_df_list:
            forecast_df = pd.DataFrame(forecast_df_list)
            if not self.cash_flow.empty:
                self.cash_flow = pd.concat([self.cash_flow, forecast_df], ignore_index=True)
            else:
                self.cash_flow = forecast_df

        # Convert numeric columns to float and fill NaN with 0
        for col in cf_cols:
            if col not in ["year", "is_historical"] and col in self.cash_flow.columns:
                self.cash_flow[col] = pd.to_numeric(self.cash_flow[col], errors='coerce').fillna(0)
    

