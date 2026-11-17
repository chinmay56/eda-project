"""
Integration tests for PostgreSQL connection, schema, repositories, and transaction integrity.
"""

import pytest
import pandas as pd

from src.database.connection import db_manager
from src.database.repository import StudentRepository, AnalyticsRepository
from src.services.data_ingestion import DataIngestionService


@pytest.mark.skipif(not db_manager.is_available, reason="PostgreSQL database is not reachable")
class TestDatabaseIntegration:

    @classmethod
    def setup_class(cls):
        """Ensure schema is created and test records are populated."""
        db_manager.initialize_schema()
        # Ingest data if not already present
        if StudentRepository.count() == 0:
            svc = DataIngestionService()
            df = svc.load_csv()
            StudentRepository.bulk_insert_from_dataframe(df)

    def test_database_connection_and_version(self):
        """Verify live connection pool and valid PostgreSQL version."""
        assert db_manager.is_available is True
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                ver = cur.fetchone()[0]
                assert "PostgreSQL" in ver

    def test_student_count(self):
        """Verify student count matches 6,607 records."""
        count = StudentRepository.count()
        assert count == 6607

    def test_db_pushed_slicing(self):
        """Verify database-pushed slicing returns expected shape."""
        sliced = StudentRepository.slice_data(limit=10, offset=0)
        assert len(sliced) == 10
        assert "Hours_Studied" in sliced.columns

    def test_db_pushed_dicing_equivalence(self):
        """
        Verify database-pushed dicing query produces EXACTLY 969 students,
        matching the notebook's in-memory filter.
        """
        diced = StudentRepository.dice_data(min_exam_score=70.0, min_attendance=80)
        assert len(diced) == 969
        assert (diced["Exam_Score"] > 70.0).all()
        assert (diced["Attendance"] > 80).all()

    def test_db_pushed_pivot(self):
        """Verify database-pushed pivot table returns exact mean scores."""
        pivot = StudentRepository.pivot_internet_vs_motivation()
        assert pivot.shape == (2, 3)
        assert pivot.loc["No", "High"] == pytest.approx(66.967391, abs=1e-4)
        assert pivot.loc["Yes", "Medium"] == pytest.approx(67.392788, abs=1e-4)

    def test_db_pushed_aggregation(self):
        """Verify database-pushed aggregation returns matching metrics."""
        agg = StudentRepository.aggregate_exam_scores()
        assert agg["count"] == 6607.0
        assert agg["mean"] == pytest.approx(67.235659, abs=1e-4)
        assert agg["median"] == pytest.approx(67.0, abs=1e-4)
        assert agg["min"] == pytest.approx(55.0, abs=1e-4)
        assert agg["max"] == pytest.approx(101.0, abs=1e-4)
        assert agg["std"] == pytest.approx(3.890456, abs=1e-4)

    def test_transaction_rollback_integrity(self):
        """Verify that transactions cleanly roll back on failures."""
        initial_count = StudentRepository.count()
        with pytest.raises(Exception):
            with db_manager.transaction() as conn:
                with conn.cursor() as cur:
                    # Insert a row with an invalid attendance (> 100 violates CHECK constraint)
                    cur.execute("""
                        INSERT INTO students (
                            hours_studied, attendance, parental_involvement, access_to_resources,
                            extracurricular_activities, sleep_hours, previous_scores, motivation_level,
                            internet_access, tutoring_sessions, family_income, school_type,
                            peer_influence, physical_activity, learning_disabilities, gender, exam_score
                        ) VALUES (
                            10, 999, 'Low', 'Low', 'No', 7, 50, 'Low', 'No', 0, 'Low', 'Public',
                            'Neutral', 2, 'No', 'Male', 50.0
                        );
                    """)
        # Ensure count has not changed
        assert StudentRepository.count() == initial_count

    def test_statistical_persistence(self):
        """Verify saving and retrieving statistical hypothesis test results."""
        res_id = AnalyticsRepository.save_statistical_result(
            test_name="unit_test_z_test",
            null_hypothesis="H0: mu = 65",
            test_statistic=18.1722,
            p_value=0.0,
            decision="Reject H0",
            conclusion="Significant deviation.",
            metadata={"source": "pytest"}
        )
        assert res_id > 0
        latest = AnalyticsRepository.get_latest_statistical_results()
        assert any(r["test_name"] == "unit_test_z_test" for r in latest)

    def test_student_crud_and_csv_sync(self):
        """Verify student CRUD operations and automated CSV synchronization."""
        from src.services.student_service import StudentService
        from src.config import app_settings

        initial_count = StudentRepository.count()

        # 1. Add student
        add_res = StudentService.add_student({
            "hours_studied": 25,
            "attendance": 90,
            "exam_score": 85.0,
            "motivation_level": "High",
            "gender": "Female"
        }, sync_csv=True)
        assert add_res["status"] == "success"
        sid = add_res["student_id"]
        assert StudentRepository.count() == initial_count + 1

        # 2. Get student
        student = StudentService.get_student(sid)
        assert student is not None
        assert student["exam_score"] == 85.0
        assert student["motivation_level"] == "High"

        # 3. Update student
        upd_res = StudentService.update_student(sid, {"exam_score": 92.5, "attendance": 98}, sync_csv=True)
        assert upd_res["status"] == "success"
        updated_student = StudentService.get_student(sid)
        assert updated_student["exam_score"] == 92.5
        assert updated_student["attendance"] == 98

        # 4. Delete student (clean up)
        del_res = StudentService.delete_student(sid, sync_csv=True)
        assert del_res["status"] == "success"
        assert StudentRepository.count() == initial_count
        assert StudentService.get_student(sid) is None

        # Verify CSV has exactly initial_count records
        df = pd.read_csv(app_settings.data_path)
        assert len(df) == initial_count

