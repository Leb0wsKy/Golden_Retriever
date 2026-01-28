"""
Application configuration settings.

Uses Pydantic Settings for environment variable management
and configuration validation. Supports Qdrant Cloud deployment.
"""

from typing import List, Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden via environment variables or .env file.
    Environment variables take precedence over .env file values.
    
    Attributes:
        APP_NAME: Name of the application.
        APP_VERSION: Current version of the application.
        APP_DESCRIPTION: API description for documentation.
        ENVIRONMENT: Deployment environment (dev/staging/prod).
        DEBUG: Enable debug mode (auto-set based on environment).
        HOST: Server host address.
        PORT: Server port number.
        ALLOWED_ORIGINS: CORS allowed origins.
        QDRANT_URL: Qdrant Cloud cluster URL.
        QDRANT_API_KEY: Qdrant Cloud API key.
        QDRANT_COLLECTION: Default Qdrant collection name.
        EMBEDDING_MODEL: Sentence transformer model name.
        EMBEDDING_DIMENSION: Vector embedding dimension.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # ===================
    # API Metadata
    # ===================
    APP_NAME: str = Field(
        default="Golden Retriever",
        description="Application name displayed in API docs"
    )
    APP_VERSION: str = Field(
        default="0.1.0",
        description="API version"
    )
    APP_DESCRIPTION: str = Field(
        default="AI-powered rail conflict resolution system using vector similarity search and digital twin simulation",
        description="API description for documentation"
    )
    
    # ===================
    # Environment Settings
    # ===================
    ENVIRONMENT: Literal["dev", "staging", "prod"] = Field(
        default="dev",
        description="Deployment environment"
    )
    HOST: str = Field(
        default="0.0.0.0",
        description="Server host address"
    )
    PORT: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Server port number"
    )
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins"
    )
    
    # ===================
    # Qdrant Settings (supports both local and cloud)
    # ===================
    QDRANT_HOST: str = Field(
        default="localhost",
        description="Qdrant host (for local deployments)"
    )
    QDRANT_PORT: int = Field(
        default=6333,
        description="Qdrant port (for local deployments)"
    )
    QDRANT_URL: Optional[str] = Field(
        default=None,
        description="Qdrant Cloud cluster URL (overrides host/port if set)"
    )
    QDRANT_API_KEY: Optional[str] = Field(
        default=None,
        description="Qdrant Cloud API key for authentication"
    )
    QDRANT_COLLECTION: str = Field(
        default="rail_conflicts",
        description="Default collection name for storing conflict vectors"
    )
    QDRANT_TIMEOUT: int = Field(
        default=30,
        description="Qdrant client timeout in seconds"
    )
    
    # ===================
    # Embedding Settings
    # ===================
    EMBEDDING_MODEL: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence transformer model name from HuggingFace"
    )
    EMBEDDING_DIMENSION: int = Field(
        default=384,
        description="Vector embedding dimension (must match model output)"
    )
    EMBEDDING_CACHE_DIR: Optional[str] = Field(
        default=None,
        description="Directory to cache downloaded models"
    )
    
    # ===================
    # AI Service Integration
    # ===================
    AI_SERVICE_URL: Optional[str] = Field(
        default="http://localhost:5001",
        description="AI Service URL for embedding generation"
    )
    AI_SERVICE_ENABLED: bool = Field(
        default=True,
        description="Use AI Service for embeddings (fallback to local if unavailable)"
    )
    AI_SERVICE_TIMEOUT: int = Field(
        default=5,
        description="AI Service request timeout in seconds"
    )
    
    # ===================
    # Transitland API Settings
    # ===================
    TRANSITLAND_API_KEY: Optional[str] = Field(
        default=None,
        description="Transitland API key for schedule data (get from https://www.transit.land/)"
    )
    TRANSITLAND_CACHE_TTL: int = Field(
        default=3600,
        description="Cache TTL for schedule data in seconds"
    )
    
    # Schedule-based conflict generation settings
    SCHEDULE_CONFLICT_RATIO: float = Field(
        default=0.7,
        ge=0,
        le=1,
        description="Ratio of schedule-based vs synthetic conflicts (0-1)"
    )
    MIN_PLATFORM_TURNAROUND: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Minimum minutes between trains on same platform"
    )
    MIN_HEADWAY_SECONDS: int = Field(
        default=180,
        ge=60,
        le=600,
        description="Minimum headway in seconds between consecutive trains"
    )
    
    # ===================
    # Simulation Settings
    # ===================
    SIMULATION_TIMEOUT: int = Field(
        default=30,
        description="Maximum simulation time in seconds"
    )
    MAX_RECOMMENDATIONS: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of recommendations to return"
    )
    
    # ===================
    # Computed Properties
    # ===================
    @computed_field
    @property
    def DEBUG(self) -> bool:
        """Debug mode is enabled in dev environment."""
        return self.ENVIRONMENT == "dev"
    
    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT == "prod"
    
    @computed_field
    @property
    def qdrant_requires_auth(self) -> bool:
        """Check if Qdrant requires API key authentication."""
        return self.QDRANT_API_KEY is not None and len(self.QDRANT_API_KEY) > 0


class DevelopmentSettings(Settings):
    """Development environment settings with sensible defaults."""
    
    ENVIRONMENT: Literal["dev", "staging", "prod"] = "dev"
    

class ProductionSettings(Settings):
    """Production environment settings with stricter defaults."""
    
    ENVIRONMENT: Literal["dev", "staging", "prod"] = "prod"
    ALLOWED_ORIGINS: List[str] = []  # Must be explicitly configured


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings singleton instance.
    
    Uses lru_cache to ensure only one Settings instance exists.
    The instance is created on first call and reused thereafter.
    
    Returns:
        Settings: Application settings singleton.
    
    Example:
        >>> from app.core.config import get_settings
        >>> settings = get_settings()
        >>> print(settings.APP_NAME)
        'Golden Retriever'
    """
    return Settings()


def clear_settings_cache() -> None:
    """
    Clear the settings cache.
    
    Useful for testing when you need to reload settings.
    """
    get_settings.cache_clear()


# ===================
# Global Settings Singleton
# ===================
# This singleton can be imported anywhere in the application:
#   from app.core.config import settings
settings = get_settings()
