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
    
    # AMD Radeon Cloud Token Factory (OpenAI-compatible API)
    AMD_ROCM_ENABLED: bool = False
    AMD_ROCM_HOST: str = "https://developer.amd.com.cn/radeon/api/v1"
    AMD_ROCM_API_KEY: str = ""
    AMD_ROCM_MODEL: str = ""
    AMD_ROCM_DEVICE: str = "not_configured"
    AMD_ROCM_VERSION: str = "not_configured"
    
    # Evolus Building Blocks
    EVOLUS_ENABLED: bool = False
    EVOLUS_API_KEY: str = ""
    EVOLUS_APPLICATION_ID: str = ""
    EVOLUS_WORKFLOW_ID: str = ""
    EVOLUS_ENDPOINT: str = "https://api.evolus.ai/api/v1"
    EVOLUS_EXECUTION_TIMEOUT_SECONDS: float = 120.0
    EVOLUS_POLL_INTERVAL_SECONDS: float = 2.0
    
    # WhatsApp / Twilio
    WHATSAPP_PROVIDER: str = "twilio"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_NUMBER: str = "whatsapp:+14155238886"
    TWILIO_WEBHOOK_ENABLED: bool = False
    TWILIO_WEBHOOK_PUBLIC_URL: str = ""
    OUTBOUND_SUPPLIER_DISPATCH_ENABLED: bool = False
    
    # Non-negotiables & Resilience
    EXTERNAL_TIMEOUT_SECONDS: float = 30.0
    MAX_RETRIES: int = 1
    DETERMINISTIC_SEED: int = 42
    SUPPLIER_LEAD_TIMES: dict[str, int] = {}
    MAX_UPLOAD_FILES: int = 5
    MAX_UPLOAD_FILE_BYTES: int = 10_485_760
    MAX_UPLOAD_TOTAL_BYTES: int = 26_214_400
    
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
