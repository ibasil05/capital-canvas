import os
from dotenv import load_dotenv

def load_environment():
    """Load environment variables from .env file"""
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the .env file
    dotenv_path = os.path.join(current_dir, '.env')
    
    # Load environment variables from .env file
    load_dotenv(dotenv_path)
    
    # Add the current directory to the Python path to fix import issues
    import sys
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
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

if __name__ == "__main__":
    load_environment()
