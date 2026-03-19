"""
Core configuration settings for the AI Product Manager application.
"""
import os
from typing import Optional, List, Union
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    APP_NAME: str = "AI Product Manager"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # API
    API_V1_STR: str = "/api/v1"
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # CORS
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001", 
            "http://localhost:3002",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:3002"
        ],
        env="CORS_ORIGINS"
    )
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as a list, handling both string and list inputs."""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(',') if origin.strip()]
        return self.CORS_ORIGINS
    
    # LLM Configuration (Groq - Fast API)
    GROQ_API_KEY: Optional[str] = Field(default=None, env="GROQ_API_KEY")
    GROQ_MODEL: str = Field(default="llama3-8b-8192", env="GROQ_MODEL")
    
    # Agent Configuration
    MAX_RETRIES: int = Field(default=3, env="MAX_RETRIES")
    RETRY_DELAY: float = Field(default=1.0, env="RETRY_DELAY")
    AGENT_TIMEOUT: int = Field(default=300, env="AGENT_TIMEOUT")  # 5 minutes
    
    # Memory System
    MEMORY_ENABLED: bool = Field(default=True, env="MEMORY_ENABLED")
    MEMORY_STORE_PATH: str = Field(default="memory_store.json", env="MEMORY_STORE_PATH")
    MEMORY_MAX_AGE_DAYS: int = Field(default=30, env="MEMORY_MAX_AGE_DAYS")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REQUESTS: int = Field(default=10, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_PERIOD: int = Field(default=60, env="RATE_LIMIT_PERIOD")  # seconds
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")  # json or text
    
    # File Upload/Export
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB
    EXPORT_DIR: str = Field(default="exports", env="EXPORT_DIR")
    
    # Monitoring
    OBSERVABILITY_ENABLED: bool = Field(default=True, env="OBSERVABILITY_ENABLED")
    METRICS_ENABLED: bool = Field(default=True, env="METRICS_ENABLED")
    
    # Database (for future use)
    DATABASE_URL: Optional[str] = Field(default=None, env="DATABASE_URL")
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

        # Allow legacy keys in .env without crashing startup
        extra = "ignore"


# Global settings instance
settings = Settings()
