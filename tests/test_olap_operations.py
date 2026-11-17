"""
Unit and regression tests for OLAP analytics service.
Verifies slicing, dicing, pivot tables, and statistical aggregations match Cell 2.
"""

import pytest
import pandas as pd

from src.services.olap_analytics import OLAPAnalyticsService


class TestOLAPAnalyticsService:

    def test_regression_against_notebook_cell2(self, real_dataset: pd.DataFrame):
        """
        Verify exact equivalence with Cell 2 of the original notebook.
        """
        service = OLAPAnalyticsService(use_db_pushdown=False)
        report = service.run_all(real_dataset)

        # 1. Slicing Verification
        sliced = report.sliced_data
        assert sliced.shape == (10, 5)
        assert list(sliced.columns) == [
            "Hours_Studied", "Attendance", "Parental_Involvement",
            "Access_to_Resources", "Extracurricular_Activities"
        ]

        # 2. Dicing Verification: EXACTLY 969 STUDENTS
        diced = report.diced_data
        assert report.diced_count == 969
        assert len(diced) == 969
        assert (diced["Exam_Score"] > 70).all()
        assert (diced["Attendance"] > 80).all()

        # 3. Pivot Table Verification
        pivot = report.pivot_table
        assert pivot.loc["No", "High"] == pytest.approx(66.967391, abs=1e-5)
        assert pivot.loc["No", "Low"] == pytest.approx(66.277778, abs=1e-5)
        assert pivot.loc["No", "Medium"] == pytest.approx(66.542857, abs=1e-5)
        assert pivot.loc["Yes", "High"] == pytest.approx(67.759576, abs=1e-5)
        assert pivot.loc["Yes", "Low"] == pytest.approx(66.795493, abs=1e-5)
        assert pivot.loc["Yes", "Medium"] == pytest.approx(67.392788, abs=1e-5)

        # 4. Aggregation Verification
        agg = report.aggregation_data
        assert agg["mean"] == pytest.approx(67.235659, abs=1e-5)
        assert agg["median"] == pytest.approx(67.0, abs=1e-5)
        assert agg["min"] == pytest.approx(55.0, abs=1e-5)
        assert agg["max"] == pytest.approx(101.0, abs=1e-5)
        assert agg["std"] == pytest.approx(3.890456, abs=1e-5)
        assert agg["count"] == pytest.approx(6607.0, abs=1e-5)

    def test_custom_dicing_thresholds(self, real_dataset: pd.DataFrame):
        """Test dicing with stricter boundaries."""
        service = OLAPAnalyticsService()
        diced = service.dice_data(real_dataset, min_exam_score=90.0, min_attendance=95)
        assert len(diced) < 969
        assert (diced["Exam_Score"] > 90.0).all()
        assert (diced["Attendance"] > 95).all()

    def test_dicing_empty_result(self, real_dataset: pd.DataFrame):
        """Test dicing boundary with impossible values."""
        service = OLAPAnalyticsService()
        diced = service.dice_data(real_dataset, min_exam_score=150.0, min_attendance=150)
        assert len(diced) == 0

    def test_slicing_custom_bounds(self, real_dataset: pd.DataFrame):
        """Test custom row and column slices."""
        service = OLAPAnalyticsService()
        sliced = service.slice_data(real_dataset, rows=5, cols=3)
        assert sliced.shape == (5, 3)
