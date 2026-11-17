"""
Database Repository providing high-performance persistence,
parameterized queries, and bulk ingestion operations.
"""

from pathlib import Path
import json
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import psycopg2.extras
from psycopg2.extensions import connection as PgConnection
from sqlalchemy import text

from src.database.connection import db_manager


class StudentRepository:
    """Repository for CRUD, batch operations, and analytical queries on students."""

    COLUMN_NAMES = [
        "hours_studied", "attendance", "parental_involvement", "access_to_resources",
        "extracurricular_activities", "sleep_hours", "previous_scores", "motivation_level",
        "internet_access", "tutoring_sessions", "family_income", "teacher_quality",
        "school_type", "peer_influence", "physical_activity", "learning_disabilities",
        "parental_education_level", "distance_from_home", "gender", "exam_score"
    ]

    @staticmethod
    def count() -> int:
        """Count total student records in the database."""
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM students;")
                return cur.fetchone()[0]

    @staticmethod
    def bulk_insert_from_dataframe(df: pd.DataFrame, batch_size: int = 2000) -> int:
        """
        High-performance bulk insert using psycopg2 execute_values.
        Inserts thousands of records in a single round-trip.
        """
        cols = [
            "Hours_Studied", "Attendance", "Parental_Involvement", "Access_to_Resources",
            "Extracurricular_Activities", "Sleep_Hours", "Previous_Scores", "Motivation_Level",
            "Internet_Access", "Tutoring_Sessions", "Family_Income", "Teacher_Quality",
            "School_Type", "Peer_Influence", "Physical_Activity", "Learning_Disabilities",
            "Parental_Education_Level", "Distance_from_Home", "Gender", "Exam_Score"
        ]
        db_cols = [c.lower() for c in cols]

        # Prepare records with None for NaNs
        cleaned_df = df[cols].copy()
        cleaned_df = cleaned_df.where(pd.notnull(cleaned_df), None)
        tuples = [tuple(x) for x in cleaned_df.to_numpy()]

        query = f"""
            INSERT INTO students ({', '.join(db_cols)})
            VALUES %s
        """

        total_inserted = 0
        with db_manager.transaction() as conn:
            with conn.cursor() as cur:
                for i in range(0, len(tuples), batch_size):
                    batch = tuples[i:i + batch_size]
                    psycopg2.extras.execute_values(
                        cur, query, batch, template=None, page_size=len(batch)
                    )
                    total_inserted += len(batch)

        return total_inserted

    @staticmethod
    def fetch_all_as_dataframe() -> pd.DataFrame:
        """Fetch all student records into a DataFrame via SQLAlchemy engine."""
        query = text("""
            SELECT 
                hours_studied AS "Hours_Studied",
                attendance AS "Attendance",
                parental_involvement AS "Parental_Involvement",
                access_to_resources AS "Access_to_Resources",
                extracurricular_activities AS "Extracurricular_Activities",
                sleep_hours AS "Sleep_Hours",
                previous_scores AS "Previous_Scores",
                motivation_level AS "Motivation_Level",
                internet_access AS "Internet_Access",
                tutoring_sessions AS "Tutoring_Sessions",
                family_income AS "Family_Income",
                teacher_quality AS "Teacher_Quality",
                school_type AS "School_Type",
                peer_influence AS "Peer_Influence",
                physical_activity AS "Physical_Activity",
                learning_disabilities AS "Learning_Disabilities",
                parental_education_level AS "Parental_Education_Level",
                distance_from_home AS "Distance_from_Home",
                gender AS "Gender",
                exam_score AS "Exam_Score"
            FROM students
            ORDER BY id ASC;
        """)
        return pd.read_sql_query(query, db_manager.engine)

    @staticmethod
    def slice_data(limit: int = 10, offset: int = 0) -> pd.DataFrame:
        """Database-pushed slicing query."""
        query = text("""
            SELECT 
                hours_studied AS "Hours_Studied",
                attendance AS "Attendance",
                parental_involvement AS "Parental_Involvement",
                access_to_resources AS "Access_to_Resources",
                extracurricular_activities AS "Extracurricular_Activities"
            FROM students
            ORDER BY id ASC
            LIMIT :limit OFFSET :offset;
        """)
        return pd.read_sql_query(query, db_manager.engine, params={"limit": limit, "offset": offset})

    @staticmethod
    def dice_data(min_exam_score: float = 70.0, min_attendance: int = 80) -> pd.DataFrame:
        """
        Database-pushed dicing query.
        Leverages composite index on (exam_score, attendance).
        """
        query = text("""
            SELECT 
                hours_studied AS "Hours_Studied",
                attendance AS "Attendance",
                parental_involvement AS "Parental_Involvement",
                access_to_resources AS "Access_to_Resources",
                extracurricular_activities AS "Extracurricular_Activities",
                sleep_hours AS "Sleep_Hours",
                previous_scores AS "Previous_Scores",
                motivation_level AS "Motivation_Level",
                internet_access AS "Internet_Access",
                tutoring_sessions AS "Tutoring_Sessions",
                family_income AS "Family_Income",
                teacher_quality AS "Teacher_Quality",
                school_type AS "School_Type",
                peer_influence AS "Peer_Influence",
                physical_activity AS "Physical_Activity",
                learning_disabilities AS "Learning_Disabilities",
                parental_education_level AS "Parental_Education_Level",
                distance_from_home AS "Distance_from_Home",
                gender AS "Gender",
                exam_score AS "Exam_Score"
            FROM students
            WHERE exam_score > :min_score AND attendance > :min_att
            ORDER BY id ASC;
        """)
        return pd.read_sql_query(
            query, db_manager.engine, params={"min_score": min_exam_score, "min_att": min_attendance}
        )

    @staticmethod
    def pivot_internet_vs_motivation() -> pd.DataFrame:
        """Database-pushed pivot aggregation query."""
        query = text("""
            SELECT 
                internet_access AS "Internet_Access",
                motivation_level AS "Motivation_Level",
                AVG(exam_score) AS mean_score
            FROM students
            GROUP BY internet_access, motivation_level
            ORDER BY internet_access, motivation_level;
        """)
        df = pd.read_sql_query(query, db_manager.engine)
        # Reshape into exact pivot format
        pivot = df.pivot(index="Internet_Access", columns="Motivation_Level", values="mean_score")
        return pivot

    @staticmethod
    def aggregate_exam_scores() -> Dict[str, float]:
        """Database-pushed aggregation query."""
        query = """
            SELECT 
                AVG(exam_score) AS mean,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY exam_score) AS median,
                MIN(exam_score) AS min,
                MAX(exam_score) AS max,
                STDDEV_SAMP(exam_score) AS std,
                COUNT(exam_score)::FLOAT AS count
            FROM students;
        """
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                row = cur.fetchone()
                return {
                    "mean": float(row[0]),
                    "median": float(row[1]),
                    "min": float(row[2]),
                    "max": float(row[3]),
                    "std": float(row[4]),
                    "count": float(row[5]),
                }

    @staticmethod
    def get_by_id(student_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single student record by primary key id."""
        query = "SELECT * FROM students WHERE id = %s;"
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (student_id,))
                row = cur.fetchone()
                return dict(row) if row else None

    @staticmethod
    def list_students(limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """List student records with pagination."""
        query = "SELECT * FROM students ORDER BY id ASC LIMIT %s OFFSET %s;"
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (limit, offset))
                return [dict(r) for r in cur.fetchall()]

    @staticmethod
    def insert_student(record: Dict[str, Any]) -> int:
        """Insert a single student record and return generated id."""
        cols = []
        vals = []
        placeholders = []
        for k, v in record.items():
            k_lower = k.lower()
            if k_lower in StudentRepository.COLUMN_NAMES:
                cols.append(k_lower)
                vals.append(v)
                placeholders.append("%s")
        if not cols:
            raise ValueError("No valid student columns provided for insertion.")
        query = f"INSERT INTO students ({', '.join(cols)}) VALUES ({', '.join(placeholders)}) RETURNING id;"
        with db_manager.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(query, vals)
                return cur.fetchone()[0]

    @staticmethod
    def update_student(student_id: int, updates: Dict[str, Any]) -> bool:
        """Update specified columns of an existing student record."""
        set_clauses = []
        vals = []
        for k, v in updates.items():
            k_lower = k.lower()
            if k_lower in StudentRepository.COLUMN_NAMES:
                set_clauses.append(f"{k_lower} = %s")
                vals.append(v)
        if not set_clauses:
            return False
        vals.append(student_id)
        query = f"UPDATE students SET {', '.join(set_clauses)} WHERE id = %s;"
        with db_manager.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(query, vals)
                return cur.rowcount > 0

    @staticmethod
    def delete_student(student_id: int) -> bool:
        """Delete a student record by id."""
        query = "DELETE FROM students WHERE id = %s;"
        with db_manager.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (student_id,))
                return cur.rowcount > 0

    @staticmethod
    def export_to_csv(filepath: Optional[Path] = None) -> int:
        """Export all students from PostgreSQL back into the CSV file."""
        from src.config import app_settings
        target = Path(filepath or app_settings.data_path)
        df = StudentRepository.fetch_all_as_dataframe()
        df.to_csv(target, index=False)
        return len(df)


class AnalyticsRepository:
    """Repository for saving and retrieving statistical tests and ML runs."""

    @staticmethod
    def save_statistical_result(
        test_name: str,
        null_hypothesis: str,
        test_statistic: float,
        p_value: float,
        decision: str,
        conclusion: str,
        degrees_of_freedom: Optional[int] = None,
        significance_level: float = 0.05,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Insert a statistical hypothesis test result."""
        query = """
            INSERT INTO statistical_test_results (
                test_name, null_hypothesis, test_statistic, p_value,
                degrees_of_freedom, significance_level, decision,
                conclusion, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        meta_json = json.dumps(metadata) if metadata else None
        with db_manager.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (
                        test_name, null_hypothesis, test_statistic, p_value,
                        degrees_of_freedom, significance_level, decision,
                        conclusion, meta_json
                    ),
                )
                return cur.fetchone()[0]

    @staticmethod
    def get_latest_statistical_results() -> List[Dict[str, Any]]:
        """Fetch all recent statistical test results."""
        query = """
            SELECT DISTINCT ON (test_name)
                id, test_name, null_hypothesis, test_statistic, p_value,
                degrees_of_freedom, significance_level, decision,
                conclusion, metadata, created_at
            FROM statistical_test_results
            ORDER BY test_name, created_at DESC;
        """
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query)
                return [dict(r) for r in cur.fetchall()]
