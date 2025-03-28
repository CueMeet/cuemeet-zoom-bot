from functools import lru_cache
from pydantic import  Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


class Settings(BaseSettings):
    """
    Configuration settings for the Zoom meeting bot.
    Uses pydantic for validation and environment variable loading.
    """

    # Logging Settings
    DEBUG: bool = Field(False, description="Logging level")
    HIGHLIGHT_PROJECT_ID: str = Field("HIGHLIGHT_PROJECT_ID", description="Logging level")
    ENVIRONMENT_NAME: str = Field("ENVIRONMENT_NAME", description="Logging level")


    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Creates and returns a cached instance of the Settings class.
    Uses environment variables and .env file for configuration.
    
    Returns:
        Settings: Configuration settings instance
    """
    load_dotenv()
    return Settings()