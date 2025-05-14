"""
Supabase storage integration for file exports.
"""

import os
from typing import Dict, Any, Optional
from db import SupabaseClient, STORAGE_BUCKET

class StorageClient:
    """Client for handling file storage operations"""
    
    @classmethod
    async def upload_file(cls, user_id: str, file_name: str, file_data: bytes) -> str:
        """
        Upload a file to Supabase storage.
        
        Args:
            user_id: ID of the user uploading the file
            file_name: Name of the file to upload
            file_data: Binary file data to upload
            
        Returns:
            Public URL of the uploaded file
        """
        return await SupabaseClient.upload_export_file(user_id, file_name, file_data)

storage = StorageClient()
