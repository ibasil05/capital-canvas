#!/usr/bin/env python
"""
Start script for the CapitalCanvas backend server.
Loads environment variables and starts the FastAPI server.
"""

import os
import sys
from pathlib import Path
import uvicorn
from dotenv import load_dotenv

def start_server():
    # Get the directory of the current file
    current_dir = Path(__file__).parent.absolute()
    
    # Load environment variables from .env file
    env_file = current_dir / ".env"
    if env_file.exists():
        print(f"Loading environment variables from {env_file}")
        load_dotenv(dotenv_path=env_file)
    else:
        print("Warning: .env file not found")
    
    # Add the current directory to Python path to fix import issues
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    # Check required environment variables
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
    ]
    
    # At least one of these API keys is required
    api_keys = ["FMP_KEY", "SEC_API_KEY"]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    if not any(os.getenv(key) for key in api_keys):
        print(f"Error: At least one of these API keys is required: {', '.join(api_keys)}")
        sys.exit(1)
    
    # Start the server
    port = 9001
    print(f"Starting server on port {port}...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=[str(current_dir)]
    )

if __name__ == "__main__":
    start_server()
