from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "UISP Diagnostic Service"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    UISP_BASE_URL: str
    UISP_TOKEN: str
    
    OPENAI_API_KEY: str
    LLM_MODEL: str = "gpt-4o-mini"
    
    # SSH credentials for direct device access
    UBIQUITI_SSH_USERNAME: str = "ubnt"
    UBIQUITI_SSH_PASSWORD: str = "B8d7f9ub1234!"
    UBIQUITI_SSH_PORT: int = 22
    
    DATABASE_URL: str = "sqlite:///./diagnostics.db"
    
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
