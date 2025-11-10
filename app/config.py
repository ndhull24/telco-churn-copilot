from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Telco Churn & Complaint Copilot (T3C)"
    APP_VERSION: str = "0.1.0"
    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

settings = Settings()
