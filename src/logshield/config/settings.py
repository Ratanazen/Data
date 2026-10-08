"""
Configuration Management for LogShield
"""

from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Automatically load local .env if present
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(BASE_DIR / ".env")

class LogShieldSettings(BaseSettings):
    """Application-wide configuration settings with environment override support."""
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General Environment
    APP_ENV: Literal["development", "staging", "production"] = "development"
    MODE: Literal["local", "hadoop", "streaming"] = "local"
    LOG_LEVEL: str = "INFO"

    # Filesystem & Data Paths
    BASE_DIR: Path = BASE_DIR
    DATA_ROOT: Path = BASE_DIR / "data"
    RAW_LOG_PATH: Path = BASE_DIR / "data" / "raw" / "server.log"
    FALLBACK_RAW_LOG_PATH: Path = BASE_DIR / "server.log"
    BRONZE_PATH: Path = BASE_DIR / "data" / "bronze"
    SILVER_PATH: Path = BASE_DIR / "data" / "silver"
    GOLD_PATH: Path = BASE_DIR / "data" / "gold"
    QUARANTINE_PATH: Path = BASE_DIR / "data" / "quarantine"

    # Hadoop HDFS
    HDFS_NAMENODE: str = "hdfs://localhost:9000"
    HDFS_LOG_PATH: str = "/logs/server.log"

    # Apache Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC: str = "logs"
    KAFKA_CONSUMER_GROUP: str = "logshield-stream-group"

    # Apache Spark / PySpark Configuration
    SPARK_APP_NAME: str = "LogShield-Analytics"
    SPARK_MASTER: str = "local[*]"
    SPARK_DRIVER_MEMORY: str = "2g"
    SPARK_EXECUTOR_MEMORY: str = "2g"
    SPARK_SHUFFLE_PARTITIONS: int = 10

    # FastAPI REST Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = False

    # Dashboard Port
    DASHBOARD_PORT: int = 8080

    def get_effective_raw_log(self) -> Path:
        """Returns the active raw log path, falling back to repository root server.log if needed."""
        if self.RAW_LOG_PATH.exists():
            return self.RAW_LOG_PATH
        if self.FALLBACK_RAW_LOG_PATH.exists():
            return self.FALLBACK_RAW_LOG_PATH
        return self.RAW_LOG_PATH

    def ensure_directories(self) -> None:
        """Idempotently ensures all runtime data directories exist."""
        for p in (self.DATA_ROOT, self.BRONZE_PATH, self.SILVER_PATH, self.GOLD_PATH, self.QUARANTINE_PATH):
            p.mkdir(parents=True, exist_ok=True)

# Global settings instance
settings = LogShieldSettings()
settings.ensure_directories()

def get_settings() -> LogShieldSettings:
    """Return the global settings instance."""
    return settings

