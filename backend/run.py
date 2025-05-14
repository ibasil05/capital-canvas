#!/usr/bin/env python
"""
Entry point for running the CapitalCanvas backend server.
This script handles environment setup and starts the FastAPI server.
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

def setup_environment():
    """
    Set up the environment for the backend server:
    1. Load environment variables from .env file
    2. Add the backend directory to the Python path
    """
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the .env file
    dotenv_path = os.path.join(current_dir, '.env')
    
    # Load environment variables from .env file
    load_dotenv(dotenv_path)
    
    # Print loaded variables for debugging (without revealing sensitive values)
    print("Loaded environment variables:")
    for var in ['SUPABASE_URL', 'FRONTEND_URL']:
        if os.getenv(var):
            print(f"  {var}: {os.getenv(var)}")
    
    # Check for sensitive variables without printing their values
    for var in ['SUPABASE_ANON_KEY', 'SUPABASE_SERVICE_ROLE_KEY', 'FMP_KEY', 'SEC_API_KEY']:
        if os.getenv(var):
            print(f"  {var}: [Set]")
        else:
            print(f"  {var}: [Not Set]")

def run_server():
    """
    Start the FastAPI server using Uvicorn
    """
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9000,
        reload=True
    )

if __name__ == "__main__":
    # Set up the environment
    setup_environment()
    
    # Run the server
    run_server()
