"""
Configuration module for the Student Performance Analytics & ML System.
Loads environment variables safely with robust fallback defaults.
"""

import os
from pathlib import Path
from urllib.parse import quote_plus
from pydantic import Field
from pydantic_settings import BaseSettings

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent


class DatabaseSettings(BaseSettings):
    host: str = Field(default="localhost", alias="DB_HOST")
    port: int = Field(default=5432, alias="DB_PORT")
    name: str = Field(default="student_performance_db", alias="DB_NAME")
    user: str = Field(default="postgres", alias="DB_USER")
    password: str = Field(default="", alias="DB_PASSWORD")
    pool_min: int = Field(default=1, alias="DB_POOL_MIN")
    pool_max: int = Field(default=10, alias="DB_POOL_MAX")
    sslmode: str = Field(default="prefer", alias="DB_SSLMODE")

    @property
    def connection_uri(self) -> str:
        """Construct PostgreSQL connection URI for SQLAlchemy / Psycopg."""
        pwd_part = f":{quote_plus(self.password)}" if self.password else ""
        return f"postgresql+psycopg2://{self.user}{pwd_part}@{self.host}:{self.port}/{self.name}"

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


class AppSettings(BaseSettings):
    env: str = Field(default="development", alias="APP_ENV")
    data_path: Path = Field(
        default=BASE_DIR / "data" / "StudentPerformanceFactors.csv",
        alias="DATA_PATH"
    )
    model_dir: Path = Field(
        default=BASE_DIR / "models",
        alias="MODEL_DIR"
    )
    model_filename: str = Field(
        default="exam_score_model.joblib",
        alias="MODEL_FILENAME"
    )
    random_seed: int = Field(default=42, alias="RANDOM_SEED")

    @property
    def model_path(self) -> Path:
        return self.model_dir / self.model_filename

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


db_settings = DatabaseSettings()
app_settings = AppSettings()
