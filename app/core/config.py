from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Application settings
    app_name: str = "WhatsApp JobBot PoC"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # OpenAI settings
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    
    # Zoho CRM settings (for future integration)
    zoho_client_id: Optional[str] = None
    zoho_client_secret: Optional[str] = None
    zoho_refresh_token: Optional[str] = None
    
    # Database settings (for future use)
    database_url: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings() 