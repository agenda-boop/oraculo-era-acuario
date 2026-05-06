from typing import Optional, List, Dict
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_lectura_profunda: str = ""
    stripe_price_portal_sagrado: str = ""

    # ManyChat
    manychat_api_key: str = ""
    manychat_webhook_secret: str = ""

    # App
    app_env: str = "development"
    secret_key: str = "dev-secret-key"
    allowed_origins: str = "http://localhost:3000"

    @property
    def origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
