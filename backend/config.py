"""
Configuration management for CapitalCanvas backend.
Handles environment variables and YAML configuration loading.
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

# Base project directories
ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"
TEMPLATE_DIR = ROOT_DIR / "templates"

# Required environment variables
REQUIRED_ENV_VARS = [
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    # At least one of these API keys is required
    ("SEC_API_KEY", "FMP_KEY"),
]

def load_env_vars() -> Dict[str, str]:
    """
    Load required environment variables and validate they exist.
    Returns a dictionary of environment variables.
    Exits with error if any required variable is missing.
    """
    env_vars = {}
    missing_vars = []
    
    for var in REQUIRED_ENV_VARS:
        # If var is a tuple, at least one of the variables must be present
        if isinstance(var, tuple):
            if not any(os.environ.get(v) for v in var):
                missing_vars.append(" or ".join(var))
            else:
                # Store all available variables from the tuple
                for v in var:
                    if v in os.environ:
                        env_vars[v] = os.environ[v]
        else:
            value = os.environ.get(var)
            if value is None:
                missing_vars.append(var)
            else:
                env_vars[var] = value
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables and restart the application.")
        sys.exit(1)
    
    # Add optional environment variables with defaults
    env_vars["PORT"] = os.environ.get("PORT", "8000")
    env_vars["HOST"] = os.environ.get("HOST", "0.0.0.0")
    env_vars["DEBUG"] = os.environ.get("DEBUG", "False").lower() == "true"
    env_vars["FRONTEND_URL"] = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    
    return env_vars


def load_yaml_config(filename: str) -> Dict[str, Any]:
    """
    Load and parse a YAML configuration file.
    
    Args:
        filename: Name of the YAML file in the config directory
        
    Returns:
        Dictionary containing the configuration
        
    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        yaml.YAMLError: If the file is not valid YAML
    """
    config_path = CONFIG_DIR / filename
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML configuration file {filename}: {e}")
        sys.exit(1)


def get_default_assumptions() -> Dict[str, Any]:
    """Load default financial model assumptions from YAML."""
    return load_yaml_config("default_assumptions.yml")


def get_rating_grid() -> Dict[str, Any]:
    """Load credit rating thresholds from YAML."""
    return load_yaml_config("rating_grid.yml")


# Application configuration class for global use
class AppConfig:
    """Application configuration singleton"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppConfig, cls).__new__(cls)
            cls._instance.env = load_env_vars()
            cls._instance.default_assumptions = get_default_assumptions()
            cls._instance.rating_grid = get_rating_grid()
        return cls._instance
    
    @property
    def debug(self) -> bool:
        """Get debug mode setting"""
        return self.env.get("DEBUG", False)
    
    @property
    def supabase_url(self) -> str:
        """Get Supabase URL"""
        return self.env["SUPABASE_URL"]
    
    @property
    def supabase_anon_key(self) -> str:
        """Get Supabase anonymous key"""
        return self.env["SUPABASE_ANON_KEY"]
    
    @property
    def supabase_service_key(self) -> str:
        """Get Supabase service role key"""
        return self.env["SUPABASE_SERVICE_ROLE_KEY"]
    
    @property
    def sec_api_key(self) -> Optional[str]:
        """Get SEC API key if available"""
        return self.env.get("SEC_API_KEY")
    
    @property
    def fmp_key(self) -> Optional[str]:
        """Get Financial Modeling Prep API key if available"""
        return self.env.get("FMP_KEY")
    
    @property
    def s3_bucket_name(self) -> Optional[str]:
        """Get S3 bucket name if configured"""
        return self.env.get("S3_BUCKET_NAME")
    
    @property
    def frontend_url(self) -> str:
        """Get frontend URL for CORS configuration"""
        return self.env.get("FRONTEND_URL", "http://localhost:3000")


# Create a global instance for importing elsewhere
config = AppConfig() 