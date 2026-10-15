"""
StockUp Pulse - Core Configuration
AMD Hackathon ACT III (Track: Reinvent Commerce)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "StockUp Pulse"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # AMD ROCm / vLLM Endpoint
    AMD_ROCM_HOST: str = ""
    AMD_ROCM_API_KEY: str = ""
    AMD_ROCM_MODEL: str = "Qwen/Qwen2.5-VL-7B-Instruct"
    AMD_ROCM_DEVICE: str = "not_configured"
    AMD_ROCM_VERSION: str = "not_configured"
    
    # Evolus Building Blocks
    EVOLUS_API_KEY: str = ""
    EVOLUS_ENDPOINT: str = "https://api.evolus.ai/v1"
    
    # WhatsApp / Twilio
    WHATSAPP_PROVIDER: str = "twilio"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_NUMBER: str = "whatsapp:+14155238886"
    OWNER_PHONE_NUMBER: str = "whatsapp:+27821234567"
    
    # Non-negotiables & Resilience
    EXTERNAL_TIMEOUT_SECONDS: float = 30.0
    MAX_RETRIES: int = 1
    DETERMINISTIC_SEED: int = 42
    
    # Spaza Shop Defaults
    STORE_NAME: str = "Sunnyside Spaza"
    STORE_CURRENCY: str = "ZAR"
    DEFAULT_BUDGET: float = 3000.00
    DEFAULT_HORIZON_DAYS: int = 14
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[1] / ".env", extra="allow")

settings = Settings()
