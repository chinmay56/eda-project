"""
Data Ingestion Service.
Handles fast validation, streaming / chunking, and bulk loading of student performance data.
"""

import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd

from src.config import app_settings
from src.database.connection import db_manager
from src.database.repository import StudentRepository

logger = logging.getLogger(__name__)

EXPECTED_COLUMNS = [
    "Hours_Studied", "Attendance", "Parental_Involvement", "Access_to_Resources",
    "Extracurricular_Activities", "Sleep_Hours", "Previous_Scores", "Motivation_Level",
    "Internet_Access", "Tutoring_Sessions", "Family_Income", "Teacher_Quality",
    "School_Type", "Peer_Influence", "Physical_Activity", "Learning_Disabilities",
    "Parental_Education_Level", "Distance_from_Home", "Gender", "Exam_Score"
]


class DataIngestionService:
    """Service for managing dataset ingestion into PostgreSQL."""

    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = Path(data_path or app_settings.data_path)

    def load_csv(self) -> pd.DataFrame:
        """Load and validate the CSV dataset from disk."""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Dataset not found at: {self.data_path}")

        df = pd.read_csv(self.data_path)

        # Validate column schema
        missing_cols = set(EXPECTED_COLUMNS) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Dataset is missing required columns: {missing_cols}")

        return df

    def sync_to_database(self, force: bool = False) -> Dict[str, Any]:
        """
        Synchronize local dataset with PostgreSQL table.
        If table already has records and force is False, skips re-insertion.
        """
        if not db_manager.is_available:
            return {
                "status": "db_unavailable",
                "message": "PostgreSQL is not reachable. Operating in local in-memory mode.",
                "rows_synced": 0
            }

        # Ensure schema exists
        db_manager.initialize_schema()

        current_count = StudentRepository.count()
        if current_count > 0 and not force:
            logger.info("Database already contains %d student records. Skipping sync.", current_count)
            return {
                "status": "skipped",
                "message": f"Database already populated ({current_count} records). Use force=True to re-ingest.",
                "rows_synced": 0,
                "total_records": current_count
            }

        start_time = time.perf_counter()
        df = self.load_csv()

        if force and current_count > 0:
            with db_manager.transaction() as conn:
                with conn.cursor() as cur:
                    cur.execute("TRUNCATE TABLE students CASCADE;")
            logger.info("Truncated existing students table for forced sync.")

        inserted = StudentRepository.bulk_insert_from_dataframe(df)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        logger.info("Successfully ingested %d records into PostgreSQL in %.2f ms", inserted, elapsed_ms)
        return {
            "status": "success",
            "message": f"Successfully ingested {inserted} records into PostgreSQL.",
            "rows_synced": inserted,
            "elapsed_ms": round(elapsed_ms, 2),
            "total_records": StudentRepository.count()
        }
