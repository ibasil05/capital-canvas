"""
Main FastAPI application for CapitalCanvas backend.
"""

from fastapi import FastAPI, HTTPException, Depends, status, Body, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json
import io

from backend.auth import AuthService, get_user_from_request, require_verified_email, security
from backend.config import config
from backend.data_providers.provider_factory import get_data_provider
from backend.models.request_models import CompanyInfoRequest, CreateModelRequest, UpdateModelRequest
from backend.models.response_models import (
    CompanyInfoResponse, ModelSummaryResponse, ModelDetailResponse, ExportResponse,
    JobCreationResponse, RawFinancialDataResponse, RecentAnalysesResponse, FinancialStatementPeriod, HistoricalPricePoint, RecentAnalysisItem
)
from backend.models.financial_model import FinancialModel, ThreeStatementModel
from backend.models.valuation_engine import ValuationEngine
from backend.models.capital_structure import CapitalStructureAnalyzer
from backend.db import db # Import the Supabase client instance

# Pydantic model for the /api/config/defaults response
class DefaultConfigsResponse(BaseModel):
    default_assumptions: Dict[str, Any]
    rating_grid: List[Dict[str, Any]] # rating_grid.yml is a list of dicts

# Create FastAPI app
app = FastAPI(
    title="CapitalCanvas API",
    description="Financial modeling API for corporate valuation and capital structure analysis",
    version="1.0.0"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth request models
class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirm_password: str
    redirect_to: Optional[str] = None
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

class SignInRequest(BaseModel):
    email: EmailStr
    password: str

class EmailRequest(BaseModel):
    email: EmailStr
    redirect_to: Optional[str] = None

class VerifyTokenRequest(BaseModel):
    token: str

class PasswordUpdateRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

# Auth routes
@app.post("/auth/signup", status_code=status.HTTP_201_CREATED)
async def signup(request: SignUpRequest):
    """
    Register a new user with email verification.
    An email will be sent to verify the user's email address.
    """
    try:
        result = await AuthService.sign_up(
            email=request.email,
            password=request.password,
            confirm_password=request.confirm_password,
            redirect_to=request.redirect_to
        )
        return {
            "message": "User created successfully. Please check your email to verify your account.",
            "user_id": result.get("id")
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )

@app.post("/auth/signin", status_code=status.HTTP_200_OK)
async def signin(request: SignInRequest):
    """
    Sign in an existing user with email and password.
    Returns access token and refresh token.
    """
    try:
        result = await AuthService.sign_in(
            email=request.email,
            password=request.password
        )
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sign in: {str(e)}"
        )

@app.post("/auth/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(request: VerifyTokenRequest):
    """
    Verify a user's email address with the verification token.
    """
    try:
        result = await AuthService.verify_email(token=request.token)
        return {
            "message": "Email verified successfully",
            "user_id": result.get("id")
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify email: {str(e)}"
        )

@app.post("/auth/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification(request: EmailRequest):
    """
    Resend the email verification link to a user.
    """
    try:
        await AuthService.send_email_verification(
            email=request.email,
            redirect_to=request.redirect_to
        )
        return {"message": "Verification email sent successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send verification email: {str(e)}"
        )

@app.post("/auth/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(request: EmailRequest):
    """
    Send a password reset email to a user.
    """
    try:
        await AuthService.reset_password(
            email=request.email,
            redirect_to=request.redirect_to
        )
        return {"message": "Password reset email sent successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send password reset email: {str(e)}"
        )

@app.post("/auth/update-password", status_code=status.HTTP_200_OK)
async def update_password(request: PasswordUpdateRequest):
    """
    Update a user's password after reset using token from email.
    """
    try:
        await AuthService.update_password(
            token=request.token,
            new_password=request.new_password,
            confirm_password=request.confirm_password
        )
        return {"message": "Password updated successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update password: {str(e)}"
        )

@app.post("/auth/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    request: PasswordChangeRequest, 
    user_token: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Change a user's password when they are logged in.
    Requires current password verification.
    """
    try:
        await AuthService.change_password(
            current_password=request.current_password,
            new_password=request.new_password,
            confirm_password=request.confirm_password,
            token=user_token.credentials
        )
        return {"message": "Password changed successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change password: {str(e)}"
        )

@app.get("/auth/me", status_code=status.HTTP_200_OK)
async def get_current_user(user: Dict[str, Any] = Depends(get_user_from_request)):
    """
    Get the current authenticated user's information.
    """
    return user

@app.get("/auth/protected", status_code=status.HTTP_200_OK)
async def protected_route(user: Dict[str, Any] = Depends(require_verified_email)):
    """
    Example of a protected route that requires a verified email.
    """
    return {
        "message": "This is a protected route that requires email verification",
        "user_id": user.get("id")
    }

# Financial data API models
class CompanyLookupRequest(BaseModel):
    ticker: str

class FinancialDataRequest(BaseModel):
    ticker: str
    period: Optional[str] = "annual"
    limit: Optional[int] = 5

class HistoricalDataRequest(BaseModel):
    ticker: str
    days: Optional[int] = 365

# Financial data API routes
@app.get("/api/company/{ticker}", status_code=status.HTTP_200_OK)
async def get_company_profile(
    ticker: str,
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """
    Get company profile information for a given ticker.
    """
    try:
        data_provider = get_data_provider()
        profile = await data_provider.get_company_profile(ticker)
        return profile
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get company profile: {str(e)}"
        )

@app.get("/api/income-statements/{ticker}", status_code=status.HTTP_200_OK)
async def get_income_statements(
    ticker: str,
    period: str = "annual",
    limit: int = 5,
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """
    Get income statements for a given ticker.
    """
    try:
        data_provider = get_data_provider()
        statements = await data_provider.get_income_statements(ticker, limit, period)
        return statements
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get income statements: {str(e)}"
        )

@app.get("/api/balance-sheets/{ticker}", status_code=status.HTTP_200_OK)
async def get_balance_sheets(
    ticker: str,
    period: str = "annual",
    limit: int = 5,
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """
    Get balance sheets for a given ticker.
    """
    try:
        data_provider = get_data_provider()
        sheets = await data_provider.get_balance_sheets(ticker, limit, period)
        return sheets
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get balance sheets: {str(e)}"
        )

@app.get("/api/cash-flows/{ticker}", status_code=status.HTTP_200_OK)
async def get_cash_flows(
    ticker: str,
    period: str = "annual",
    limit: int = 5,
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """
    Get cash flow statements for a given ticker.
    """
    try:
        data_provider = get_data_provider()
        statements = await data_provider.get_cash_flow_statements(ticker, limit, period)
        return statements
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cash flow statements: {str(e)}"
        )

@app.get("/api/key-metrics/{ticker}", status_code=status.HTTP_200_OK)
async def get_key_metrics(
    ticker: str,
    period: str = "annual",
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """
    Get key financial metrics for a given ticker.
    """
    try:
        data_provider = get_data_provider()
        metrics = await data_provider.get_key_metrics(ticker, period)
        return metrics
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get key metrics: {str(e)}"
        )

@app.get("/api/peers/{ticker}", status_code=status.HTTP_200_OK)
async def get_sector_peers(
    ticker: str,
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """
    Get sector peers for a given ticker.
    """
    try:
        data_provider = get_data_provider()
        peers = await data_provider.get_sector_peers(ticker)
        return {"peers": peers}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sector peers: {str(e)}"
        )

@app.get("/api/historical-prices/{ticker}", status_code=status.HTTP_200_OK)
async def get_historical_prices(
    ticker: str,
    days: int = 365,
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """
    Get historical stock prices for a given ticker.
    """
    try:
        data_provider = get_data_provider()
        prices = await data_provider.get_historical_prices(ticker, days)
        return {"prices": prices}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get historical prices: {str(e)}"
        )

@app.get("/api/all-data/{ticker}", status_code=status.HTTP_200_OK)
async def get_all_company_data(
    ticker: str,
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """
    Get all financial data for a given ticker.
    """
    try:
        data_provider = get_data_provider()
        all_data = await data_provider.get_all_company_data(ticker)
        return all_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get all company data: {str(e)}"
        )

# Financial modeling API routes
@app.post("/api/models", status_code=status.HTTP_201_CREATED)
async def create_financial_model(
    request: CreateModelRequest,
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """
    Create a new financial model for a company.
    """
    try:
        # Get company data
        data_provider = get_data_provider()
        company_data = await data_provider.get_all_company_data(request.ticker)
        
        # Create financial model
        model = FinancialModel(
            ticker=request.ticker,
            company_data=company_data,
            assumptions=request.assumptions.dict(),
            user_id=user.get("id")
        )
        
        # Generate model and save
        model_id = await model.save()
        
        return {
            "message": "Financial model created successfully",
            "model_id": model_id
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create financial model: {str(e)}"
        )

# New /api/model endpoint for asynchronous processing
import uuid # For generating job IDs
from fastapi import BackgroundTasks # For background tasks

# Placeholder for actual model processing results storage
model_processing_jobs: Dict[str, Any] = {} 

def _update_job_progress(job_id: str, status: str, stage: Optional[str] = None, percentage: Optional[int] = None, data: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
    if job_id not in model_processing_jobs:
        model_processing_jobs[job_id] = {}
    
    model_processing_jobs[job_id]["status"] = status
    if stage is not None:
        model_processing_jobs[job_id]["stage"] = stage
    if percentage is not None:
        model_processing_jobs[job_id]["percentage"] = percentage
    if data is not None: # Only for completed status
        model_processing_jobs[job_id]["data"] = data
    if error is not None: # Only for failed status
        model_processing_jobs[job_id]["error"] = error
    model_processing_jobs[job_id]["last_updated"] = datetime.utcnow().isoformat()

async def process_model_in_background(
    job_id: str, 
    ticker: str, 
    assumptions: Dict[str, Any], # Corresponds to ModelAssumptionsRequest
    user_id: str
):
    """
    Placeholder function for the actual model processing.
    This function will run in the background.
    1. Run forecast engine
    2. Execute DCF, Comps, LBO valuation modules
    3. Perform financing optimization (FR-5) to generate capitalStructureHeatmap data
    4. Populate ModelDetailResponse structure
    5. Store the result in model_processing_jobs or a persistent store
    """
    print(f"Starting background processing for job_id: {job_id} for ticker: {ticker}")
    _update_job_progress(job_id, status="processing", stage="Initiating model generation", percentage=0)
    try:
        _update_job_progress(job_id, status="processing", stage="Fetching company data", percentage=10)
        data_provider = get_data_provider()
        company_data = await data_provider.get_all_company_data(ticker)

        if not company_data:
            _update_job_progress(job_id, status="failed", error=f"Could not retrieve comprehensive company data for ticker: {ticker}", percentage=100)
            print(f"Failed job {job_id} due to missing company data for {ticker}")
            return

        _update_job_progress(job_id, status="processing", stage="Initializing three-statement model", percentage=25)
        three_statement_model_instance = ThreeStatementModel(
            company_data=company_data,
            ticker=ticker,
        )
        _update_job_progress(job_id, status="processing", stage="Building financial projections and valuations", percentage=40)
        model_results = three_statement_model_instance.build_model(assumptions=assumptions)

        _update_job_progress(job_id, status="processing", stage="Formatting financial statements", percentage=60)
        financial_statements_list = []
        # The model_results["income_statement"] is now a list of records (dictionaries)
        # Each record contains 'year', 'is_historical', and financial items.
        # Similar for balance_sheet and cash_flow results.
        
        # Assuming income_statement, balance_sheet, and cash_flow lists are of the same length
        # and correspond to the same periods.
        num_periods = 0
        if model_results.get("income_statement") and isinstance(model_results["income_statement"], list):
            num_periods = len(model_results["income_statement"])

        for i in range(num_periods):
            is_record = model_results["income_statement"][i] if i < len(model_results.get("income_statement", [])) else {}
            bs_record = model_results["balance_sheet"][i] if i < len(model_results.get("balance_sheet", [])) else {}
            cf_record = model_results["cash_flow"][i] if i < len(model_results.get("cash_flow", [])) else {}

            revenue_val = is_record.get("revenue", 0.0)
            gross_profit_val = is_record.get("gross_profit", 0.0) # Adjusted to gross_profit from rename
            ebitda_val = is_record.get("ebitda", 0.0)
            free_cash_flow_val = cf_record.get("free_cash_flow", 0.0)

            # Determine growth rate (current revenue / previous revenue - 1)
            # Need to access previous period's revenue for growth calculation
            previous_revenue_val = 0.0
            if i > 0 and i - 1 < len(model_results.get("income_statement", [])):
                 previous_is_record = model_results["income_statement"][i-1]
                 previous_revenue_val = previous_is_record.get("revenue", 0.0)
            
            growth_rate_val = (revenue_val / previous_revenue_val - 1) if previous_revenue_val else None

            fs_item = FinancialStatement(
                year=int(is_record.get("year", 0)), # Ensure year is int
                is_historical=is_record.get("is_historical", False),
                revenue=revenue_val,
                gross_profit=gross_profit_val,
                ebitda=ebitda_val,
                operating_income=is_record.get("operating_income", 0.0),
                net_income=is_record.get("net_income", 0.0),
                total_assets=bs_record.get("total_assets", 0.0),
                total_debt=bs_record.get("total_debt", 0.0),
                total_equity=bs_record.get("total_equity", 0.0),
                operating_cash_flow=cf_record.get("operating_cash_flow", 0.0),
                capex=cf_record.get("capex", 0.0),
                free_cash_flow=free_cash_flow_val,
                growth_rate=growth_rate_val,
                gross_margin=gross_profit_val / revenue_val if revenue_val else 0,
                ebitda_margin=ebitda_val / revenue_val if revenue_val else 0,
                fcf_margin=free_cash_flow_val / revenue_val if revenue_val else 0,
            )
            financial_statements_list.append(fs_item)
        
        _update_job_progress(job_id, status="processing", stage="Fetching trading comparables", percentage=75)
        trading_comps_list = []
        try:
            valuation_engine_for_comps = ValuationEngine(
                ticker=ticker,
                company_data=company_data,
                assumptions=assumptions 
            )
            raw_comps_data = await valuation_engine_for_comps._get_trading_comps()
            for comp_data in raw_comps_data:
                trading_comps_list.append(TradingComp(**comp_data))
        except Exception as e_comps:
            print(f"Error fetching or processing trading comps for job {job_id}: {str(e_comps)}")
            # Continue without comps if they fail, maybe log a warning in results?

        _update_job_progress(job_id, status="processing", stage="Compiling final model output", percentage=85)
        processed_data_dict = {
            "id": job_id, 
            "ticker": ticker.upper(),
            "company_name": company_data.get("profile", {}).get("companyName", company_data.get("profile", {}).get("name", ticker.upper())),
            "created_at": datetime.utcnow(),
            "last_updated": datetime.utcnow(),
            "assumptions": assumptions,
            "financial_statements": [fs.dict() for fs in financial_statements_list], 
            "valuation": {
                "dcf_enterprise_value": model_results["dcf_valuation"].get("enterprise_value"),
                "dcf_equity_value": model_results["dcf_valuation"].get("equity_value"),
                "dcf_implied_share_price": model_results["dcf_valuation"].get("price_per_share"),
                "trading_comps_enterprise_value": model_results["trading_comps_valuation"].get("enterprise_value"),
                "trading_comps_equity_value": model_results["trading_comps_valuation"].get("equity_value"),
                "trading_comps_implied_share_price": model_results["trading_comps_valuation"].get("price_per_share"),
                "lbo_analysis": LBOAnalysisResult(**model_results["lbo_valuation"]).dict() if model_results.get("lbo_valuation") else None,
                "trading_comps": [tc.dict() for tc in trading_comps_list],
                "valuation_range_low": model_results["dcf_valuation"].get("price_per_share", 0) * 0.9, 
                "valuation_range_high": model_results["dcf_valuation"].get("price_per_share", 0) * 1.1, 
                "consensus_target_price": company_data.get("profile", {}).get("targetPrice", None)
            },
            "capital_structure_grid": model_results["capital_structure_grid"]
        }
        
        # Validate with ModelDetailResponse before storing in job status
        validated_model_detail = ModelDetailResponse(**processed_data_dict)

        _update_job_progress(job_id, status="processing", stage="Saving model to database", percentage=95)
        # Store the full result in Supabase, then update job status
        # The job_id from uuid can be used as the model_id for the database
        await db.create_model(
            model_id=job_id, # Use the generated job_id as model_id
            user_id=user_id,
            ticker=ticker.upper(),
            assumptions=assumptions,
            results=validated_model_detail.dict(), # Store the validated and Pydantic-parsed model output
            # Add company_name to the create_model call if the table supports it
            # and if it's readily available. For now, assuming create_model in db.py doesn't require it separately.
            company_name=validated_model_detail.company_name # Pass company name if db.create_model supports it
        )
        
        _update_job_progress(job_id, status="completed", stage="Model generation complete", percentage=100, data=validated_model_detail.dict())
        print(f"Finished background processing for job_id: {job_id}")

    except Exception as e:
        print(f"Error processing job {job_id}: {str(e)}")
        _update_job_progress(job_id, status="failed", error=str(e), percentage=100, stage="Error during processing")


@app.post("/api/model", response_model=JobCreationResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_model_analysis_job(
    request: CreateModelRequest,
    background_tasks: BackgroundTasks,
    user: Dict[str, Any] = Depends(require_verified_email) # Assuming authentication is needed
):
    """
    Accepts model creation parameters, initiates a background job for processing,
    and returns a job ID.
    """
    job_id = str(uuid.uuid4())
    
    # Add the processing to background tasks
    background_tasks.add_task(
        process_model_in_background,
        job_id,
        request.ticker,
        request.assumptions.dict(), # Pass assumptions as dict
        user.get("id") 
    )
    
    # Add to recent analyses (FR-10)
    await add_user_recent_analysis(
        user_id=user.get("id"),
        ticker=request.ticker.upper(), # Ensure ticker is upper
        analysis_type="model_creation_initiated",
        viewed_at=datetime.utcnow(), # Pass viewed_at
        model_id=job_id,
        company_name=request.ticker # TODO: Get company name if easily available or after profile fetch
    )
    
    status_endpoint = f"/api/model/status/{job_id}" # Example status endpoint
    
    return JobCreationResponse(job_id=job_id, status_endpoint=status_endpoint)

# Placeholder endpoint to check job status - to be used by /ws/progress/{job_id} later
@app.get("/api/model/status/{job_id}")
async def get_model_job_status(job_id: str):
    job = model_processing_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

# FR-8: WebSocket endpoint for progress updates
@app.websocket("/ws/progress/{job_id}")
async def websocket_progress_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()
    print(f"WebSocket connection established for job_id: {job_id}")
    try:
        while True:
            job_details = model_processing_jobs.get(job_id)
            if not job_details:
                await websocket.send_json({"status": "error", "stage": "Job not found", "percentage": 0, "message": "Job not found"})
                break # Exit loop if job is not found
            
            current_status = job_details.get("status")
            current_stage = job_details.get("stage", "Processing...")
            current_percentage = job_details.get("percentage", 0)
            error_message = job_details.get("error")
            
            progress_message = {
                "job_id": job_id,
                "status": current_status,
                "stage": current_stage,
                "percentage": current_percentage,
                "message": f"Job stage: {current_stage} ({current_percentage}%)" if current_status == "processing" else f"Job {current_status}",
                "data": job_details.get("data") if current_status == "completed" else None,
                "error": error_message if current_status == "failed" else None
            }
            await websocket.send_json(progress_message)
            
            if current_status in ["completed", "failed"]:
                break # Exit loop if job is finished
            
            # Poll for updates every few seconds
            # In a more advanced setup, this could use a publish/subscribe mechanism (e.g., Redis Pub/Sub)
            # to avoid polling and push updates instantly when job status changes.
            import asyncio
            await asyncio.sleep(2) # Poll every 2 seconds
            
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for job_id: {job_id}")
    except Exception as e:
        print(f"Error in WebSocket for job_id {job_id}: {str(e)}")
        try:
            # Attempt to send an error message to the client if the connection is still open
            await websocket.send_json({"status": "error", "message": f"An internal error occurred: {str(e)}"})
        except Exception as send_error:
            print(f"Could not send WebSocket error message: {send_error}")
    finally:
        # Ensure the WebSocket is closed if it hasn't been already
        # await websocket.close() # Handled by FastAPI on disconnect or exception from handler
        print(f"WebSocket closing for job_id: {job_id}")

@app.get("/api/models", status_code=status.HTTP_200_OK)
async def list_financial_models(
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """
    List all financial models for the current user.
    """
    try:
        user_id = user.get("id")
        models = await FinancialModel.list_models(user_id)
        return models
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list financial models: {str(e)}"
        )

@app.get("/api/models/{model_id}", status_code=status.HTTP_200_OK)
async def get_financial_model(
    model_id: str,
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """
    Get a specific financial model by ID.
    """
    try:
        user_id = user.get("id")
        model = await FinancialModel.get_model(model_id, user_id)
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Financial model with ID {model_id} not found"
            )
            
        return model
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get financial model: {str(e)}"
        )

@app.put("/api/models/{model_id}", status_code=status.HTTP_200_OK)
async def update_financial_model(
    model_id: str,
    request: UpdateModelRequest,
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """
    Update an existing financial model.
    """
    try:
        user_id = user.get("id")
        
        # Load existing model
        model = await FinancialModel.get_model(model_id, user_id)
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Financial model with ID {model_id} not found"
            )
            
        # Update assumptions and regenerate model
        updated_model = await FinancialModel.update_model(
            model_id=model_id,
            user_id=user_id,
            new_assumptions=request.assumptions.dict()
        )
        
        return {
            "message": "Financial model updated successfully",
            "model_id": model_id
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update financial model: {str(e)}"
        )

@app.delete("/api/models/{model_id}", status_code=status.HTTP_200_OK)
async def delete_financial_model(
    model_id: str,
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """
    Delete a financial model.
    """
    try:
        user_id = user.get("id")
        success = await FinancialModel.delete_model(model_id, user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Financial model with ID {model_id} not found"
            )
            
        return {
            "message": "Financial model deleted successfully"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete financial model: {str(e)}"
        )

@app.post("/api/models/{model_id}/export", status_code=status.HTTP_200_OK)
async def export_financial_model(
    model_id: str,
    format: str = "xlsx",
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """
    Export a financial model to Excel or PowerPoint.
    """
    try:
        user_id = user.get("id")
        
        # Check if model exists
        model = await FinancialModel.get_model(model_id, user_id)
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Financial model with ID {model_id} not found"
            )
        
        # Validate format
        if format.lower() not in ["xlsx", "pptx"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid export format. Supported formats are 'xlsx' and 'pptx'"
            )
            
        # Generate export
        from backend.exports import export_model
        export_url = await export_model(model_id, format.lower(), user_id)
        
        return {
            "file_url": export_url,
            "file_type": format.lower()
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export financial model: {str(e)}"
        )

@app.post("/api/capital-structure/optimize/{model_id}", status_code=status.HTTP_200_OK)
async def optimize_capital_structure(
    model_id: str,
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """
    Find the optimal capital structure for a company.
    """
    try:
        user_id = user.get("id")
        
        # Check if model exists
        model = await FinancialModel.get_model(model_id, user_id)
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Financial model with ID {model_id} not found"
            )
            
        # Run capital structure optimization
        analyzer = CapitalStructureAnalyzer(model)
        optimal_structure = await analyzer.find_optimal_structure()
        
        return optimal_structure
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to optimize capital structure: {str(e)}"
        )

@app.post("/api/valuation/quick", status_code=status.HTTP_200_OK)
async def quick_valuation(
    request: CompanyInfoRequest,
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """
    Perform a quick valuation analysis for a company using default assumptions.
    """
    try:
        # Get company data
        data_provider = get_data_provider()
        company_data = await data_provider.get_all_company_data(request.ticker)
        
        # Use default assumptions for quick valuation
        valuation_engine = ValuationEngine(
            ticker=request.ticker,
            company_data=company_data
        )
        
        # Run valuation with default assumptions
        valuation = await valuation_engine.run_valuation()
        
        return valuation
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform quick valuation: {str(e)}"
        )

# New endpoint for default configurations
@app.get("/api/config/defaults", response_model=DefaultConfigsResponse, status_code=status.HTTP_200_OK)
async def get_all_default_configurations(user: Dict[str, Any] = Depends(require_verified_email)):
    """
    Get all default configurations for the application, including
    financial model assumptions and credit rating grids.
    This endpoint requires authentication.
    """
    try:
        return DefaultConfigsResponse(
            default_assumptions=config.default_assumptions,
            rating_grid=config.rating_grid
        )
    except Exception as e:
        # Log the exception e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve default configurations: {str(e)}"
        )

# Technical and search endpoints
@app.get("/api/search", status_code=status.HTTP_200_OK)
async def search_companies_endpoint(
    q: str | None = None,
    query: str | None = None,
    limit: int = 10,
    exchange: str = "",
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """Search for companies by name or ticker symbol"""
    search_term = q or query
    if not search_term:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing search query parameter"
        )
    try:
        data_provider = get_data_provider()
        results = await data_provider.search_companies(search_term, limit, exchange)
        return results
    except AttributeError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Search functionality is not available for the selected data provider"
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search companies: {str(e)}"
        )

@app.get("/api/technical-indicators/{ticker}", status_code=status.HTTP_200_OK)
async def get_technical_indicator_endpoint(
    ticker: str,
    indicator: str = "sma",
    interval: str = "daily",
    time_period: int = 14,
    series_type: str = "close",
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """Get technical indicator series for a ticker"""
    try:
        data_provider = get_data_provider()
        data = await data_provider.get_technical_indicator(
            ticker,
            indicator,
            interval,
            time_period,
            series_type,
        )
        return data
    except AttributeError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Technical indicator functionality is not available for the selected data provider"
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get technical indicator: {str(e)}"
        )

# Dashboard endpoints (stub implementations for MVP)
@app.get("/api/dashboard/summary", status_code=status.HTTP_200_OK)
async def dashboard_summary(user: Dict[str, Any] = Depends(require_verified_email)):
    """Return a high-level portfolio/dashboard summary (placeholder)."""
    # For a side-project MVP, we return static examples. Replace with real aggregation later.
    return {
        "totalValue": 1000000,
        "annualizedReturn": 0.12,
        "activePositions": 8,
        "cashBalance": 25000,
    }


@app.get("/api/dashboard/performance-history", status_code=status.HTTP_200_OK)
async def dashboard_performance_history(user: Dict[str, Any] = Depends(require_verified_email)):
    """Return sample portfolio performance history for charts (placeholder)."""
    today = datetime.utcnow().date()
    history = [
        {
            "date": (today - timedelta(days=i)).isoformat(),
            "portfolioValue": 1000000 + i * 5000,
            "benchmarkValue": 1000000 + i * 4000,
        }
        for i in range(30)
    ][::-1]  # oldest first
    return history


@app.get("/api/dashboard/recent-activity", status_code=status.HTTP_200_OK)
async def dashboard_recent_activity(user: Dict[str, Any] = Depends(require_verified_email)):
    """Return recent activity items (placeholder)."""
    now = datetime.utcnow()
    activities = [
        {
            "id": "act1",
            "date": (now - timedelta(days=1)).isoformat(),
            "type": "Buy",
            "description": "Bought 100 shares of AAPL",
            "amount": 18500,
            "currency": "USD",
        },
        {
            "id": "act2",
            "date": (now - timedelta(days=3)).isoformat(),
            "type": "Dividend",
            "description": "Dividend from MSFT",
            "amount": 320,
            "currency": "USD",
        },
    ]
    return activities

# FR-2: Endpoint to get raw financial data and cache it
# Placeholder for database interaction (e.g., using SQLModel or SQLAlchemy)
async def get_cached_raw_data(symbol: str) -> Optional[RawFinancialDataResponse]:
    raw_filing_db = await db.get_raw_filing(ticker=symbol)
    if raw_filing_db and raw_filing_db.get("json_data"):
        try:
            # Assuming json_data in DB stores the RawFinancialDataResponse structure
            # The db.get_raw_filing already checks for age (24h)
            cached_data_content = json.loads(raw_filing_db["json_data"])
            return RawFinancialDataResponse(
                **cached_data_content, 
                data_source="cache", 
                fetched_at=datetime.fromisoformat(raw_filing_db["fetched_at"].replace('Z', '+00:00'))
            )
        except Exception as e:
            print(f"Error parsing cached data for {symbol}: {e}")
            return None
    return None

async def cache_raw_data(symbol: str, data: RawFinancialDataResponse):
    # Exclude fields that are dynamically set or part of the cache wrapper itself
    data_to_cache = data.dict(exclude={"data_source", "fetched_at"})
    await db.upsert_raw_filing(ticker=symbol, filing_data=data_to_cache)

@app.get("/api/ticker/{symbol}/raw", response_model=RawFinancialDataResponse)
async def get_raw_ticker_data(
    symbol: str,
    user: Dict[str, Any] = Depends(require_verified_email)
):
    """
    Fetches last 8 fiscal years of IS/BS/CF and prices for a ticker.
    Caches data in Postgres and returns normalized JSON.
    FR-2
    """
    cached_data = await get_cached_raw_data(symbol)
    if cached_data:
        return cached_data

    # If not in cache or cache expired, fetch from data provider
    print(f"Fetching fresh data for {symbol} from provider...")
    try:
        data_provider = get_data_provider()
        
        # Fetch 8 years of data
        income_statements_raw = await data_provider.get_income_statements(symbol, limit=8, period='annual')
        balance_sheets_raw = await data_provider.get_balance_sheets(symbol, limit=8, period='annual')
        cash_flows_raw = await data_provider.get_cash_flow_statements(symbol, limit=8, period='annual')
        prices_raw = await data_provider.get_historical_prices(symbol, days=365*8) # Approx 8 years of daily prices

        # Normalize into FinancialStatementPeriod
        # This requires matching years across the three statements.
        # For simplicity, assume they are ordered chronologically (oldest first) and align by index.
        # A more robust solution would key by year and merge.
        normalized_filings = []
        num_years = min(len(income_statements_raw), len(balance_sheets_raw), len(cash_flows_raw))
        
        # Assuming the provider returns data with the most recent year first.
        # We need to map them, perhaps using the 'year' field if available or fiscal year.
        # Let's assume for now the data provider gives a 'year' field in each statement item.
        
        # Create a dictionary to hold statements keyed by year for easier merging
        statements_by_year: Dict[int, Dict[str, Any]] = {}

        def process_statements(raw_statements: List[Dict[str,Any]], statement_type: str):
            for stmt in raw_statements:
                year = stmt.get('year', stmt.get('date',[:4])) # Attempt to get year
                if isinstance(year, str): year = int(year[:4]) # Convert if string like YYYY-MM-DD
                if year not in statements_by_year:
                    statements_by_year[year] = {}
                statements_by_year[year][statement_type] = stmt

        process_statements(income_statements_raw, "income_statement")
        process_statements(balance_sheets_raw, "balance_sheet")
        process_statements(cash_flows_raw, "cash_flow_statement")
        
        # Sort years and take the latest up to 8
        sorted_years = sorted(statements_by_year.keys(), reverse=True)[:8]

        for year_val in sorted_years:
            year_data = statements_by_year[year_val]
            normalized_filings.append(
                FinancialStatementPeriod(
                    year=year_val,
                    income_statement=year_data.get("income_statement", {}),
                    balance_sheet=year_data.get("balance_sheet", {}),
                    cash_flow_statement=year_data.get("cash_flow_statement", {})
                )
            )
        normalized_filings.sort(key=lambda x: x.year) # Ensure chronological order for response

        # Normalize prices
        prices = [
            HistoricalPricePoint(date=price_data.get('date'), price=price_data.get('close', price_data.get('price')))
            for price_data in prices_raw if price_data.get('date') and (price_data.get('close') is not None or price_data.get('price') is not None)
        ]
        
        current_time = datetime.utcnow()
        response_data = RawFinancialDataResponse(
            symbol=symbol.upper(),
            normalized_filings=normalized_filings,
            prices=prices,
            data_source="api", # Or determine if partly from cache in a full implementation
            fetched_at=current_time
        )

        await cache_raw_data(symbol, response_data) # Placeholder cache call
        
        # Add to recent analyses (FR-10)
        user_id = user.get("id")
        if user_id:
            # Attempt to get company name from profile, if already fetched or fetch quickly
            # For now, just using ticker
            company_profile_data = await data_provider.get_company_profile(symbol)
            company_name_from_profile = company_profile_data.get("companyName", company_profile_data.get("name", symbol.upper()))
            await add_user_recent_analysis(
                user_id=user_id,
                ticker=symbol.upper(), 
                analysis_type="raw_data_viewed", 
                viewed_at=current_time,
                company_name=company_name_from_profile
            )

        return response_data

    except Exception as e:
        # Log error e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch or process raw data for {symbol}: {str(e)}"
        )

# FR-10: Store and retrieve recent user analyses
# In-memory user_recent_analyses is removed as we will use the database.
MAX_RECENT_ANALYSES = 5 # Defined in get_user_recent_analyses if needed

async def add_user_recent_analysis(user_id: str, ticker: str, analysis_type: str, viewed_at: datetime, company_name: Optional[str] = None, model_id: Optional[str] = None):
    """Adds user activity to the database."""
    try:
        await db.add_user_activity(
            user_id=user_id,
            ticker=ticker,
            analysis_type=analysis_type,
            viewed_at=viewed_at.isoformat(),
            company_name=company_name,
            model_id=model_id
        )
    except Exception as e:
        print(f"Error in add_user_recent_analysis: {e}") # Log error, don't let it break the main flow

@app.get("/api/user/recent-analyses", response_model=RecentAnalysesResponse)
async def get_user_recent_analyses(
    user: Dict[str, Any] = Depends(require_verified_email)
):
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found")

    recent_items: List[RecentAnalysisItem] = []
    try:
        # Fetch from the new user_activities table
        activities_raw = await db.list_user_activities(user_id=user_id, limit=MAX_RECENT_ANALYSES) # MAX_RECENT_ANALYSES is 5
        
        for activity_raw in activities_raw:
            recent_items.append(
                RecentAnalysisItem(
                    ticker=activity_raw["ticker"],
                    model_id=activity_raw.get("model_id"),
                    analysis_type=activity_raw["analysis_type"],
                    viewed_at=datetime.fromisoformat(activity_raw["viewed_at"].replace('Z', '+00:00')) if isinstance(activity_raw["viewed_at"], str) else activity_raw["viewed_at"],
                    company_name=activity_raw.get("company_name")
                )
            )
    except Exception as e:
        print(f"Error fetching recent activities from DB for user {user_id}: {e}")
        # Optionally, could raise HTTPException or return empty if critical
        
    return RecentAnalysesResponse(recent_analyses=recent_items)

# FR-8 & API Design: Updated export endpoints to stream files
@app.get("/api/export/{model_id}/excel", response_class=StreamingResponse)
async def stream_excel_export(
    model_id: str, 
    user: Dict[str, Any] = Depends(require_verified_email)
):
    user_id = user.get("id")
    model_data = await db.get_model(model_id=model_id, user_id=user_id)
    
    if not model_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found or access denied")

    ticker = model_data.get("ticker", "model")
    company_name_for_file = model_data.get("company_name", ticker).replace(' ', '_')
    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_name = f"{company_name_for_file}_Financial_Model_{timestamp_str}.xlsx"

    from backend.exports.excel_export import generate_excel_export
    try:
        # Ensure results_json is parsed if it's a string
        results_json_data = model_data["results_json"]
        if isinstance(results_json_data, str):
            results_json_data = json.loads(results_json_data)
        
        file_content_bytes = await generate_excel_export(results_json_data)
    except Exception as gen_e:
        print(f"Error generating Excel for model {model_id}: {gen_e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate Excel file: {str(gen_e)}")

    await add_user_recent_analysis(
        user_id=user_id,
        ticker=ticker,
        analysis_type="excel_export_generated",
        viewed_at=datetime.utcnow(),
        company_name=model_data.get("company_name", ticker),
        model_id=model_id
    )
    
    return StreamingResponse(
        io.BytesIO(file_content_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={file_name}"}
    )

@app.get("/api/export/{model_id}/ppt", response_class=StreamingResponse)
async def stream_ppt_export(
    model_id: str, 
    user: Dict[str, Any] = Depends(require_verified_email)
):
    user_id = user.get("id")
    model_data = await db.get_model(model_id=model_id, user_id=user_id)
    
    if not model_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found or access denied")

    ticker = model_data.get("ticker", "model")
    company_name_for_file = model_data.get("company_name", ticker).replace(' ', '_')
    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_name = f"{company_name_for_file}_Presentation_{timestamp_str}.pptx"

    from backend.exports.ppt_export import generate_ppt_export
    try:
        results_json_data = model_data["results_json"]
        if isinstance(results_json_data, str):
            results_json_data = json.loads(results_json_data)

        file_content_bytes = await generate_ppt_export(results_json_data)
    except Exception as gen_e:
        print(f"Error generating PowerPoint for model {model_id}: {gen_e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PowerPoint file: {str(gen_e)}")

    await add_user_recent_analysis(
        user_id=user_id,
        ticker=ticker,
        analysis_type="ppt_export_generated",
        viewed_at=datetime.utcnow(),
        company_name=model_data.get("company_name", ticker),
        model_id=model_id
    )

    return StreamingResponse(
        io.BytesIO(file_content_bytes),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f"attachment; filename={file_name}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 