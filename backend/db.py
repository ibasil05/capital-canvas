"""
Database client for Supabase integration.
Handles all interactions with Supabase tables and storage.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import uuid # For generating job_id

from supabase import create_client, Client
from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder # <--- ADDED IMPORT

from config import config

# Define table names as constants to avoid hardcoding
TABLE_RAW_FILINGS = "raw_filings"
TABLE_MODELS = "models"
STORAGE_BUCKET = "exports"
TABLE_USER_ACTIVITIES = "user_activities"
TABLE_EXPORT_JOBS = "export_jobs"

# Database client singleton
class SupabaseClient:
    """Singleton client for Supabase database and storage access"""
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Get or create the Supabase client instance"""
        if cls._instance is None:
            url = config.supabase_url
            key = config.supabase_service_key
            cls._instance = create_client(url, key)
        return cls._instance
    
    @classmethod
    async def get_raw_filing(cls, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get raw filing data for a ticker.
        Returns None if no filing exists or if it's older than 24 hours.
        """
        client = cls.get_client()
        
        # Calculate the timestamp for 24 hours ago
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        
        try:
            response = client.table(TABLE_RAW_FILINGS) \
                .select("*") \
                .eq("ticker", ticker.upper()) \
                .execute()
            
            if not response.data:
                return None
            
            filing = response.data[0]
            
            # Check if the filing is older than 24 hours
            fetched_at = datetime.fromisoformat(filing["fetched_at"].replace('Z', '+00:00'))
            if fetched_at < one_day_ago:
                return None
                
            return filing
            
        except Exception as e:
            print(f"Error fetching raw filing for ticker {ticker}: {e}")
            return None
    
    @classmethod
    async def upsert_raw_filing(cls, ticker: str, filing_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert or update raw filing data for a ticker.
        """
        client = cls.get_client()
        
        # Prepare the data for upsert
        upsert_data = {
            "ticker": ticker.upper(),
            "json_data": json.dumps(filing_data),
            "fetched_at": datetime.utcnow().isoformat()
        }
        
        try:
            response = client.table(TABLE_RAW_FILINGS) \
                .upsert(upsert_data, on_conflict="ticker") \
                .execute()
                
            if not response.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to store filing data"
                )
                
            return response.data[0]
            
        except Exception as e:
            print(f"Error storing raw filing for ticker {ticker}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )
    
    @classmethod
    async def get_model(cls, model_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get a model by ID, ensuring it belongs to the user.
        """
        client = cls.get_client()
        
        try:
            response = client.table(TABLE_MODELS) \
                .select("*") \
                .eq("id", model_id) \
                .eq("user_id", user_id) \
                .execute()
                
            if not response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Model not found or does not belong to the user"
                )
                
            return response.data[0]
            
        except Exception as e:
            print(f"Error fetching model {model_id} for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )
    
    @classmethod
    async def list_user_models(cls, user_id: str) -> List[Dict[str, Any]]:
        """
        List all models belonging to a user.
        """
        client = cls.get_client()
        
        try:
            response = client.table(TABLE_MODELS) \
                .select("id, ticker, company_name, created_at") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .execute()
                
            return response.data
            
        except Exception as e:
            print(f"Error listing models for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )
    
    @classmethod
    async def create_model(
        cls, 
        model_id: str,
        user_id: str, 
        ticker: str, 
        assumptions: Dict[str, Any], 
        results: Dict[str, Any],
        company_name: Optional[str] = None,
        model_name: str = None
    ) -> Dict[str, Any]:
        """
        Create a new financial model for a user.
        """
        client = cls.get_client()
        
        # Prepare the data for insertion
        model_data = {
            "id": model_id,
            "user_id": user_id,
            "ticker": ticker.upper(),
            "assumptions_json": json.dumps(jsonable_encoder(assumptions)),
            "results_json": json.dumps(jsonable_encoder(results)),
            "company_name": company_name,
            "model_name": model_name or f"Model {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        try:
            response = client.table(TABLE_MODELS) \
                .insert(model_data) \
                .execute()
                
            if not response.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to store model data"
                )
                
            return response.data[0]
            
        except Exception as e:
            print(f"Error creating model for user {user_id}, ticker {ticker}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )
    
    @classmethod
    async def update_model(
        cls, 
        model_id: str, 
        user_id: str, 
        assumptions: Dict[str, Any], 
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing financial model.
        """
        client = cls.get_client()
        
        # Prepare the data for update
        update_data = {
            "assumptions_json": json.dumps(assumptions),
            "results_json": json.dumps(results),
        }
        
        try:
            response = client.table(TABLE_MODELS) \
                .update(update_data) \
                .eq("id", model_id) \
                .eq("user_id", user_id) \
                .execute()
                
            if not response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Model not found or does not belong to the user"
                )
                
            return response.data[0]
            
        except Exception as e:
            print(f"Error updating model {model_id} for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )
    
    @classmethod
    async def delete_model(cls, model_id: str, user_id: str) -> bool:
        """
        Delete a financial model.
        """
        client = cls.get_client()
        
        try:
            response = client.table(TABLE_MODELS) \
                .delete() \
                .eq("id", model_id) \
                .eq("user_id", user_id) \
                .execute()
                
            return len(response.data) > 0
            
        except Exception as e:
            print(f"Error deleting model {model_id} for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )
    
    @classmethod
    async def upload_export_file(
        cls, 
        user_id: str, 
        file_name: str, 
        file_data: bytes
    ) -> str:
        """
        Upload an export file to Supabase Storage.
        Returns the public URL of the file.
        """
        client = cls.get_client()
        
        # Create a timestamped file path to avoid overwriting
        timestamp = int(time.time())
        file_path = f"{user_id}/{timestamp}_{file_name}"
        
        try:
            response = client.storage.from_(STORAGE_BUCKET) \
                .upload(file_path, file_data, {"content-type": "application/octet-stream"})
                
            # Get the public URL
            file_url = client.storage.from_(STORAGE_BUCKET).get_public_url(file_path)
            
            return file_url
            
        except Exception as e:
            print(f"Error uploading export file for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Storage error: {str(e)}"
            )

    @classmethod
    async def add_user_activity(
        cls,
        user_id: str,
        ticker: str,
        analysis_type: str,
        company_name: Optional[str] = None,
        model_id: Optional[str] = None,
        viewed_at: Optional[str] = None,
    ) -> None:
        """Add a record to the user_activities table."""
        client = cls.get_client()
        activity_data = {
            "user_id": user_id,
            "ticker": ticker.upper(),
            "analysis_type": analysis_type,
            "company_name": company_name,
            "model_id": model_id,
            "viewed_at": viewed_at or datetime.utcnow().isoformat()
        }
        try:
            response = client.table(TABLE_USER_ACTIVITIES).insert(activity_data).execute()
            if response.data:
                print(f"Added user activity: {activity_data}")
            else:
                print(f"Failed to add user activity, response: {response}") # Log if insert fails
        except Exception as e:
            print(f"Error adding user activity to DB: {e}")
            # Optionally re-raise or handle, for now just printing

    @classmethod
    async def list_user_activities(
        cls, 
        user_id: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """List recent activities for a user."""
        client = cls.get_client()
        try:
            response = client.table(TABLE_USER_ACTIVITIES)\
                .select("ticker, model_id, analysis_type, viewed_at, company_name")\
                .eq("user_id", user_id)\
                .order("viewed_at", desc=True)\
                .limit(limit)\
                .execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error listing user activities for user {user_id}: {e}")
            return []

    @classmethod
    async def create_export_job(cls, user_id: str, model_id: str, export_type: str) -> Optional[str]:
        """Creates a new export job in the database and returns its ID."""
        job_id = str(uuid.uuid4())
        try:
            response = cls.get_client().table(TABLE_EXPORT_JOBS).insert({
                'job_id': job_id,
                'user_id': user_id,
                'model_id': model_id,
                'export_type': export_type,
                'status': 'pending',
                'progress': 0
            }).execute()
            
            # Assuming Supabase client returns error in response.error if insert fails
            if hasattr(response, 'error') and response.error:
                print(f"Error creating export job in DB: {response.error.message if response.error else 'Unknown error'}")
                return None
            # Check if data was returned and if it's a list (common for Supabase insert)
            if response.data and isinstance(response.data, list) and len(response.data) > 0:
                 # Supabase often returns the inserted row(s) in data[0]
                # We just need to confirm it worked and return the job_id we generated
                return job_id
            elif response.data: # If data is not None/empty but not as expected list
                print(f"Unexpected response data structure creating export job: {response.data}")
                return job_id # Still assume it worked if no error
            else: # No data and no explicit error could also be an issue depending on client version
                print(f"No data returned creating export job and no explicit error. Response: {response}")
                return None # Or raise an exception

        except Exception as e:
            print(f"Exception during create_export_job: {e}")
            return None

    @classmethod
    async def update_export_job_status(
        cls,
        job_id: str, 
        status: str, 
        progress: Optional[int] = None, 
        file_url: Optional[str] = None, 
        error_message: Optional[str] = None
    ):
        """Updates the status, progress, file_url, or error_message of an export job."""
        update_data = {'status': status}
        if progress is not None:
            update_data['progress'] = progress
        if file_url is not None:
            update_data['file_url'] = file_url
        if error_message is not None:
            update_data['error_message'] = error_message
        
        try:
            cls.get_client().table(TABLE_EXPORT_JOBS).update(update_data).eq('job_id', job_id).execute()
        except Exception as e:
            print(f"Exception updating export job {job_id} status: {e}")

    @classmethod
    async def get_export_job_details(cls, job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves details for a specific export job for a user, respecting RLS."""
        try:
            # RLS should handle user_id check, but explicit user_id in query is good practice for non-RLS bypass scenarios
            response = cls.get_client().table(TABLE_EXPORT_JOBS).select('*').eq('job_id', job_id).eq('user_id', user_id).maybe_single().execute()
            return response.data if response.data else None
        except Exception as e:
            print(f"Exception getting export job details for {job_id}: {e}")
            return None
            
    @classmethod
    async def get_export_job_progress_for_websocket(cls, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves progress, status, and file_url for a job.
        This is intended for the WebSocket which might operate with service_role or specific auth.
        If WebSocket connections are per-user authenticated and RLS is strict, this might need user_id too.
        For now, assumes job_id is globally unique and the WebSocket handler manages auth context if any.
        """
        try:
            response = cls.get_client().table(TABLE_EXPORT_JOBS).select('job_id, status, progress, file_url, error_message').eq('job_id', job_id).maybe_single().execute()
            return response.data if response.data else None
        except Exception as e:
            print(f"Exception getting export job progress for websocket for job_id {job_id}: {e}")
            return None
            
    @classmethod
    async def get_model_by_id(cls, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a model by its ID.
        Returns None if the model doesn't exist.
        """
        try:
            response = cls.get_client().table('models').select('*').eq('id', model_id).maybe_single().execute()
            return response.data if response.data else None
        except Exception as e:
            print(f"Exception getting model by ID {model_id}: {e}")
            return None

# Create a global instance for importing elsewhere
db = SupabaseClient