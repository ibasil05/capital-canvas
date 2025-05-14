"""
Authentication module for CapitalCanvas backend.
Verifies Supabase JWT tokens and provides user information.
"""

from typing import Optional, Dict, Any
import httpx
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import config

# Security scheme for JWT tokens
security = HTTPBearer()

class AuthService:
    """Service for handling authentication with Supabase"""
    
    @staticmethod
    async def verify_token(token: str) -> Dict[str, Any]:
        """
        Verify a JWT token with Supabase auth API.
        Returns user information if valid, raises HTTPException if invalid.
        """
        url = f"{config.supabase_url}/auth/v1/user"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "apikey": config.supabase_anon_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid authentication token"
                    )
                
                return response.json()
                
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service unavailable"
            )
    
    @staticmethod
    async def sign_up(email: str, password: str, confirm_password: str, redirect_to: Optional[str] = None) -> Dict[str, Any]:
        """
        Sign up a new user with email verification.
        
        Args:
            email: User's email address
            password: User's password
            confirm_password: Password confirmation (must match password)
            redirect_to: Optional URL to redirect to after email verification
            
        Returns:
            Response from Supabase
            
        Raises:
            HTTPException: If sign up fails or passwords don't match
        """
        # Validate that passwords match
        if password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match"
            )
        
        # Validate password strength
        if len(password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        url = f"{config.supabase_url}/auth/v1/signup"
        
        headers = {
            "apikey": config.supabase_anon_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "email": email,
            "password": password,
            "data": {}
        }
        
        # Add redirect URL if provided
        if redirect_to:
            payload["redirect_to"] = redirect_to
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code not in (200, 201):
                    error = response.json().get("error_description", "Sign up failed")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error
                    )
                
                return response.json()
                
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication service unavailable: {str(e)}"
            )
    
    @staticmethod
    async def sign_in(email: str, password: str) -> Dict[str, Any]:
        """
        Sign in a user with email and password.
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            Response from Supabase with access token and user info
            
        Raises:
            HTTPException: If sign in fails
        """
        url = f"{config.supabase_url}/auth/v1/token?grant_type=password"
        
        headers = {
            "apikey": config.supabase_anon_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "email": email,
            "password": password
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code != 200:
                    error = response.json().get("error_description", "Invalid login credentials")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=error
                    )
                
                return response.json()
                
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service unavailable"
            )
    
    @staticmethod
    async def send_email_verification(email: str, redirect_to: Optional[str] = None) -> Dict[str, Any]:
        """
        Send an email verification link to a user.
        
        Args:
            email: User's email address
            redirect_to: Optional URL to redirect to after email verification
            
        Returns:
            Response from Supabase
            
        Raises:
            HTTPException: If sending the verification email fails
        """
        url = f"{config.supabase_url}/auth/v1/recover"
        
        headers = {
            "apikey": config.supabase_anon_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "email": email,
            "type": "signup"
        }
        
        # Add redirect URL if provided
        if redirect_to:
            payload["redirect_to"] = redirect_to
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code != 200:
                    error = response.json().get("error_description", "Failed to send verification email")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error
                    )
                
                return response.json()
                
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service unavailable"
            )
    
    @staticmethod
    async def verify_email(token: str) -> Dict[str, Any]:
        """
        Verify a user's email address with the verification token.
        
        Args:
            token: Email verification token
            
        Returns:
            Response from Supabase
            
        Raises:
            HTTPException: If verification fails
        """
        url = f"{config.supabase_url}/auth/v1/verify"
        
        headers = {
            "apikey": config.supabase_anon_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "token": token,
            "type": "signup"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code != 200:
                    error = response.json().get("error_description", "Email verification failed")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error
                    )
                
                return response.json()
                
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service unavailable"
            )
    
    @staticmethod
    async def reset_password(email: str, redirect_to: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a password reset email to a user.
        
        Args:
            email: User's email address
            redirect_to: Optional URL to redirect to after password reset
            
        Returns:
            Response from Supabase
            
        Raises:
            HTTPException: If sending the reset email fails
        """
        url = f"{config.supabase_url}/auth/v1/recover"
        
        headers = {
            "apikey": config.supabase_anon_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "email": email,
            "type": "recovery"
        }
        
        # Add redirect URL if provided
        if redirect_to:
            payload["redirect_to"] = redirect_to
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code != 200:
                    error = response.json().get("error_description", "Failed to send password reset email")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error
                    )
                
                return response.json()
                
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service unavailable"
            )
            
    @staticmethod
    async def update_password(token: str, new_password: str, confirm_password: str) -> Dict[str, Any]:
        """
        Update a user's password after reset.
        
        Args:
            token: Password reset token from email
            new_password: New password
            confirm_password: Confirmation of new password
            
        Returns:
            Response from Supabase
            
        Raises:
            HTTPException: If password update fails or passwords don't match
        """
        # Validate that passwords match
        if new_password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match"
            )
        
        # Validate password strength
        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        url = f"{config.supabase_url}/auth/v1/user"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "apikey": config.supabase_anon_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "password": new_password
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(url, json=payload, headers=headers)
                
                if response.status_code != 200:
                    error = response.json().get("error_description", "Failed to update password")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error
                    )
                
                return response.json()
                
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service unavailable"
            )
    
    @staticmethod
    async def change_password(
        current_password: str,
        new_password: str,
        confirm_password: str,
        token: str
    ) -> Dict[str, Any]:
        """
        Change a user's password when they are logged in.
        
        Args:
            current_password: Current password for verification
            new_password: New password
            confirm_password: Confirmation of new password
            token: User's access token
            
        Returns:
            Response from Supabase
            
        Raises:
            HTTPException: If password change fails, current password is invalid,
                          or new passwords don't match
        """
        # Validate that new passwords match
        if new_password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New passwords do not match"
            )
        
        # Validate password strength
        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # First verify the current password
        try:
            # Get user's email from token
            user_data = await AuthService.verify_token(token)
            email = user_data.get("email")
            
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unable to verify user identity"
                )
            
            # Try to sign in with current password to verify it
            try:
                await AuthService.sign_in(email, current_password)
            except HTTPException:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Current password is incorrect"
                )
            
            # Update to new password
            url = f"{config.supabase_url}/auth/v1/user"
            
            headers = {
                "Authorization": f"Bearer {token}",
                "apikey": config.supabase_anon_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "password": new_password
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.put(url, json=payload, headers=headers)
                
                if response.status_code != 200:
                    error = response.json().get("error_description", "Failed to update password")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error
                    )
                
                return response.json()
                
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service unavailable"
            )
    
    @staticmethod
    async def check_email_verification_status(user_id: str) -> bool:
        """
        Check if a user's email address has been verified.
        
        Args:
            user_id: User's ID
            
        Returns:
            True if email is verified, False otherwise
            
        Raises:
            HTTPException: If the check fails
        """
        url = f"{config.supabase_url}/auth/v1/user"
        
        headers = {
            "apikey": config.supabase_service_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Failed to check email verification status"
                    )
                
                user_data = response.json()
                return user_data.get("email_confirmed_at") is not None
                
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service unavailable"
            )
    
    @staticmethod
    async def get_user_from_request(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> Dict[str, Any]:
        """
        Extract and verify the JWT token from the request.
        Returns user information if valid, raises HTTPException if invalid.
        """
        return await AuthService.verify_token(credentials.credentials)
    
    @staticmethod
    async def get_user_id_from_request(
        user: Dict[str, Any] = Depends(get_user_from_request)
    ) -> str:
        """
        Extract the user ID from the authenticated user information.
        """
        return user["id"]


# Create dependency functions for FastAPI
async def get_user_from_request(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Extract and verify the JWT token from the request.
    Returns user information if valid, raises HTTPException if invalid.
    """
    return await AuthService.verify_token(credentials.credentials)


async def get_user_id_from_request(
    user: Dict[str, Any] = Depends(get_user_from_request)
) -> str:
    """
    Extract the user ID from the authenticated user information.
    """
    return user["id"]


async def require_verified_email(
    user: Dict[str, Any] = Depends(get_user_from_request)
) -> Dict[str, Any]:
    """
    Ensure the user has a verified email address.
    Raises an exception if the email is not verified.
    
    Args:
        user: User data from request
        
    Returns:
        User data if email is verified
        
    Raises:
        HTTPException: If email is not verified
    """
    if user.get("email_confirmed_at") is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required. Please verify your email address."
        )
    return user


# Create an instance for importing elsewhere
auth_service = AuthService 