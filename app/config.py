import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "AI Document & Invoice Processing Agent"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    
    # Storage
    BASE_DIR: Path = BASE_DIR
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    MAX_UPLOAD_SIZE_MB: int = 15
    ALLOWED_EXTENSIONS: list[str] = [".pdf", ".jpg", ".jpeg", ".png"]
    
    # Database
    DATABASE_URL: str = "sqlite:///./invoices.db"
    
    # AI Extraction Configuration
    AI_PROVIDER: str = "gemini"  # gemini, openai, anthropic, or demo
    AI_API_KEY: str = ""
    AI_MODEL: str = "gemini-1.5-flash"
    
    # Financial thresholds
    HIGH_VALUE_THRESHOLD: float = 100000.0  # INR default
    
    # OCR Settings
    TESSERACT_CMD: str = ""
    
    # Optional Alerts (Email)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ALERT_RECIPIENT_EMAIL: str = "admin@example.com"
    
    # Optional Google Sheets Integration
    GOOGLE_SHEETS_CREDENTIALS_JSON: str = ""
    GOOGLE_SHEET_ID: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
