"""
Zentrale Konfiguration für die Anwendung.
Unterstützt verschiedene Umgebungen (dev, staging, production).
"""
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn


class Settings(BaseSettings):
    """Anwendungs-Konfiguration mit Environment-Variables Support."""
    
    # App Settings
    app_name: str = Field(default="SocialHabit API", description="Name der Anwendung")
    app_version: str = Field(default="2.0.0", description="API Version")
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Umgebung"
    )
    debug: bool = Field(default=False, description="Debug-Modus")
    
    # Server Settings
    host: str = Field(default="0.0.0.0", description="Server Host")
    port: int = Field(default=8000, description="Server Port")
    workers: int = Field(default=4, description="Anzahl der Worker-Prozesse")
    
    # Database
    database_url: PostgresDsn = Field(
        default="postgresql://mauro:1234@localhost:5432/socialhabit",
        description="PostgreSQL Connection String"
    )
    db_pool_size: int = Field(default=20, description="Connection Pool Größe")
    db_max_overflow: int = Field(default=10, description="Max Pool Overflow")
    db_pool_timeout: int = Field(default=30, description="Pool Timeout in Sekunden")
    db_pool_recycle: int = Field(default=3600, description="Connection Recycle Time")
    db_echo: bool = Field(default=False, description="SQL Logging")
    
    # Security
    secret_key: str = Field(
        default="change-this-in-production-to-a-secure-random-string",
        description="Secret Key für Token-Generierung"
    )
    algorithm: str = Field(default="HS256", description="JWT Algorithm")
    access_token_expire_minutes: int = Field(default=43200, description="Token Lifetime (30 Tage)")
    
    # CORS Settings
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Erlaubte CORS Origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="CORS Credentials")
    cors_allow_methods: list[str] = Field(default=["*"], description="Erlaubte HTTP Methods")
    cors_allow_headers: list[str] = Field(default=["*"], description="Erlaubte Headers")
    
    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Log Level"
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log Format"
    )
    log_file: str | None = Field(default=None, description="Log-Datei (optional)")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=False, description="Rate Limiting aktivieren")
    rate_limit_per_minute: int = Field(default=60, description="Requests pro Minute")
    
    # APNs (Push Notifications)
    apns_enabled: bool = Field(default=False, description="APNs aktiviert")
    apns_key_path: str | None = Field(default=None, description="Pfad zum APNs Key")
    apns_key_id: str | None = Field(default=None, description="APNs Key ID")
    apns_team_id: str | None = Field(default=None, description="APNs Team ID")
    apns_topic: str | None = Field(default=None, description="APNs Topic (Bundle ID)")
    apns_use_sandbox: bool = Field(default=True, description="APNs Sandbox verwenden")
    
    # Feature Flags
    feature_admin_panel: bool = Field(default=True, description="Admin Panel aktiviert")
    feature_push_notifications: bool = Field(default=False, description="Push Notifications")
    feature_email_notifications: bool = Field(default=False, description="Email Notifications")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def is_production(self) -> bool:
        """Prüft ob Production-Umgebung."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Prüft ob Development-Umgebung."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Gibt singleton Settings-Instanz zurück.
    Cached für bessere Performance.
    """
    return Settings()


# Globale Settings-Instanz für einfachen Import
settings = get_settings()
