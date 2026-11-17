"""
Unit and regression tests for statistical hypothesis testing service.
Verifies numerical equivalence with notebook Cell 0 results.
"""

import pytest
import numpy as np
import pandas as pd

from src.services.statistical_analysis import StatisticalAnalysisService, TestResult


class TestStatisticalAnalysisService:

    def test_regression_against_notebook_cell0(self, real_dataset: pd.DataFrame):
        """
        Verify exact numerical results match the original Colab notebook outputs.
        """
        service = StatisticalAnalysisService(alpha=0.05, mu=65.0, population_std=10.0)
        report = service.analyze(real_dataset, persist_to_db=False)

        # 1. Summary Information
        assert report.summary.total_students == 6607
        assert report.summary.sample_mean == pytest.approx(67.2357, abs=1e-4)
        assert report.summary.sample_std == pytest.approx(3.8905, abs=1e-4)

        # 2. One-Sample Z-Test
        assert report.z_test.test_statistic == pytest.approx(18.1722, abs=1e-4)
        assert report.z_test.p_value == pytest.approx(0.0, abs=1e-5)
        assert report.z_test.decision == "Reject H0"
        assert "Average exam score differs significantly from 65." in report.z_test.conclusion

        # 3. One-Sample T-Test
        assert report.t_test.test_statistic == pytest.approx(46.7097, abs=1e-4)
        assert report.t_test.p_value == pytest.approx(0.0, abs=1e-5)
        assert report.t_test.degrees_of_freedom == 6606
        assert report.t_test.decision == "Reject H0"
        assert "Average exam score differs significantly from 65." in report.t_test.conclusion

        # 4. Chi-Square Test of Independence
        assert report.chi2_test.test_statistic == pytest.approx(2.7338, abs=1e-4)
        assert report.chi2_test.degrees_of_freedom == 2
        assert report.chi2_test.p_value == pytest.approx(0.254894, abs=1e-5)
        assert report.chi2_test.decision == "Fail to Reject H0"
        assert "No significant association was detected." in report.chi2_test.conclusion

        # 5. Crosstab Frequencies
        table = report.crosstab_table
        assert table.loc["No", "High"] == 92
        assert table.loc["No", "Low"] == 162
        assert table.loc["No", "Medium"] == 245
        assert table.loc["Yes", "High"] == 1227
        assert table.loc["Yes", "Low"] == 1775
        assert table.loc["Yes", "Medium"] == 3106

    def test_z_test_edge_cases(self):
        """Test Z-test with known synthetic inputs."""
        service = StatisticalAnalysisService(alpha=0.05, mu=50.0, population_std=5.0)
        # Normal sample centered at 50 with n=100
        np.random.seed(42)
        sample = pd.Series(np.random.normal(50.0, 5.0, 100))
        result = service.run_one_sample_z_test(sample)

        assert isinstance(result, TestResult)
        assert result.test_name == "one_sample_z_test"
        assert -3.0 < result.test_statistic < 3.0

    def test_null_handling_in_exam_scores(self):
        """Verify that missing values in Exam_Score are dropped cleanly."""
        service = StatisticalAnalysisService(alpha=0.05, mu=65.0, population_std=10.0)
        series_with_nans = pd.Series([65.0, None, 70.0, np.nan, 75.0])
        result = service.run_one_sample_t_test(series_with_nans)

        assert result.metadata["sample_size"] == 3
        assert result.degrees_of_freedom == 2

    def test_alpha_significance_switching(self, real_dataset: pd.DataFrame):
        """Verify that decision logic respects custom alpha values."""
        # Using a very strict alpha that wouldn't reject if p > alpha
        service = StatisticalAnalysisService(alpha=1e-10, mu=65.0, population_std=10.0)
        exam_scores = real_dataset["Exam_Score"]
        # Z p-value is effectively 0 (< 1e-10), so it still rejects
        res = service.run_one_sample_z_test(exam_scores)
        assert res.decision == "Reject H0"
