"""
Centralized Configuration & Environment Management (Phase DEPLOY-1)
===================================================================
Location: foundation/config.py

Governs environment settings, database and storage backend selection,
strict CORS allowlists, timeouts, and fail-closed validation for
production deployments on Render and Vercel.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Load .env if present (development convenience)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    pass


class ConfigurationError(RuntimeError):
    """Raised when environment configuration violates production invariants."""


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class StorageBackend(str, Enum):
    LOCAL = "local"
    SUPABASE = "supabase"


class DatabaseBackend(str, Enum):
    LOCAL = "local"
    SUPABASE = "supabase"


class AIProviderMode(str, Enum):
    WORKBENCH = "workbench"
    LOCAL = "local"


@dataclass
class AppConfig:
    """Application configuration container with fail-closed production validation."""

    environment: str = field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development").lower().strip()
    )
    storage_backend: str = field(
        default_factory=lambda: os.getenv("STORAGE_BACKEND", "local").lower().strip()
    )
    database_backend: str = field(
        default_factory=lambda: os.getenv("DATABASE_BACKEND", "local").lower().strip()
    )
    port: int = field(
        default_factory=lambda: int(os.getenv("PORT", "5000"))
    )

    # CORS settings
    allowed_origins_raw: str = field(
        default_factory=lambda: os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://localhost:5174,http://localhost:3000,http://127.0.0.1:5173"
        )
    )

    # Supabase credentials (Backend server-only, never sent to frontend)
    supabase_url: Optional[str] = field(
        default_factory=lambda: os.getenv("SUPABASE_URL")
    )
    supabase_service_role_key: Optional[str] = field(
        default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    supabase_anon_key: Optional[str] = field(
        default_factory=lambda: os.getenv("SUPABASE_ANON_KEY")
    )
    database_url: Optional[str] = field(
        default_factory=lambda: os.getenv("DATABASE_URL")
    )

    # Storage buckets (all private)
    bucket_documents: str = "documents"
    bucket_generated: str = "generated"
    bucket_source_artifacts: str = "source-artifacts"

    # AI Provider credentials (Backend server-only)
    ai_provider_mode: str = field(
        default_factory=lambda: os.getenv("AI_PROVIDER_MODE", "workbench").lower().strip()
    )
    gemini_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY")
    )
    workbench_subscription_key: Optional[str] = field(
        default_factory=lambda: os.getenv("WORKBENCH_SUBSCRIPTION_KEY")
    )
    workbench_charge_code: Optional[str] = field(
        default_factory=lambda: os.getenv("WORKBENCH_CHARGE_CODE")
    )

    # Timeouts (explicitly separated to prevent latency hiding)
    http_request_timeout_seconds: int = 30
    gunicorn_worker_timeout_seconds: int = 120
    document_processing_timeout_seconds: int = 60
    ai_provider_timeout_seconds: int = 45

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION.value

    @property
    def allowed_origins(self) -> List[str]:
        if not self.allowed_origins_raw or self.allowed_origins_raw.strip() == "*":
            if self.is_production:
                raise ConfigurationError(
                    "ALLOWED_ORIGINS cannot be '*' or empty in production mode."
                )
            return ["*"]
        return [o.strip() for o in self.allowed_origins_raw.split(",") if o.strip()]

    def validate(self) -> None:
        """Enforces mandatory deployment invariants."""
        if self.is_production:
            if self.storage_backend != StorageBackend.SUPABASE.value:
                raise ConfigurationError(
                    f"Production environment requires STORAGE_BACKEND='supabase', got '{self.storage_backend}'"
                )
            if self.database_backend != DatabaseBackend.SUPABASE.value:
                raise ConfigurationError(
                    f"Production environment requires DATABASE_BACKEND='supabase', got '{self.database_backend}'"
                )
            if not self.supabase_url:
                raise ConfigurationError("SUPABASE_URL must be configured in production.")
            if not self.supabase_service_role_key:
                raise ConfigurationError("SUPABASE_SERVICE_ROLE_KEY must be configured in production.")
            if "*" in self.allowed_origins:
                raise ConfigurationError("Wildcard '*' CORS origin is forbidden in production.")

    def get_safe_health_dict(self) -> Dict[str, Any]:
        """Returns safe application status without exposing secrets."""
        return {
            "status": "ok",
            "environment": self.environment,
            "storage_backend": self.storage_backend,
            "database_backend": self.database_backend,
            "ai_provider_mode": self.ai_provider_mode,
            "version": "1.0.0",
        }


# Global configuration singleton
_CONFIG: Optional[AppConfig] = None


def get_config() -> AppConfig:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = AppConfig()
    return _CONFIG


def set_config(config: AppConfig) -> None:
    global _CONFIG
    _CONFIG = config
