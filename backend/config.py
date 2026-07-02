"""config.py — centralised settings loaded from environment variables / .env"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # ------------------------------------------------------------------ #
    # Database — PostgreSQL (Supabase)                                    #
    # ------------------------------------------------------------------ #
    # Format: postgresql://user:password@host:port/dbname
    # Get this from Supabase → Project Settings → Database → Connection string
    database_url: str = ""

    # ------------------------------------------------------------------ #
    # Admin secret — protects the /api/admin/* endpoints                  #
    # Used to trigger instrument master reload on the live server.        #
    # Set to any long random string you choose.                           #
    # ------------------------------------------------------------------ #
    admin_secret: str = "change-this-to-a-secret-value"

    # ------------------------------------------------------------------ #
    # Upstox instrument master (public CSV, no auth needed)               #
    # ------------------------------------------------------------------ #
    instrument_master_url: str = (
        "https://assets.upstox.com/market-quote/instruments/exchange/complete.csv.gz"
    )

    # ------------------------------------------------------------------ #
    # CORS — origins allowed to call the API                              #
    # Add your Vercel frontend URL here after deployment.                 #
    # e.g. "https://mf-nav-tracker.vercel.app"                           #
    # ------------------------------------------------------------------ #
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=BASE_DIR.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
