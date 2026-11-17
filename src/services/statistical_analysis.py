"""
Statistical Analysis Service.
Performs rigorous hypothesis testing (Z-test, T-test, Chi-square test of independence)
matching the analytical output of the original notebook.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Tuple
import numpy as np
import pandas as pd
from scipy import stats

from src.database.connection import db_manager
from src.database.repository import AnalyticsRepository


@dataclass
class TestResult:
    __test__ = False  # Prevent pytest from treating this DTO as a test class
    test_name: str
    null_hypothesis: str
    test_statistic: float
    p_value: float
    decision: str
    conclusion: str
    degrees_of_freedom: Optional[int] = None
    significance_level: float = 0.05
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class DatasetSummary:
    total_students: int
    sample_mean: float
    sample_std: float


@dataclass
class StatisticalAnalysisReport:
    summary: DatasetSummary
    z_test: TestResult
    t_test: TestResult
    chi2_test: TestResult
    crosstab_table: pd.DataFrame


class StatisticalAnalysisService:
    """Service executing and persisting student performance hypothesis tests."""

    def __init__(self, alpha: float = 0.05, mu: float = 65.0, population_std: float = 10.0):
        self.alpha = alpha
        self.mu = mu
        self.population_std = population_std

    def run_one_sample_z_test(self, series: pd.Series) -> TestResult:
        """
        One-Sample Z-Test:
        H0: mu = 65
        H1: mu != 65
        """
        clean_series = series.dropna()
        n = len(clean_series)
        mean = float(clean_series.mean())

        z = (mean - self.mu) / (self.population_std / np.sqrt(n))
        z_p = float(2 * stats.norm.sf(abs(z)))

        decision = "Reject H0" if z_p < self.alpha else "Fail to Reject H0"
        conclusion = (
            "Average exam score differs significantly from 65."
            if z_p < self.alpha
            else "No significant difference from 65."
        )

        return TestResult(
            test_name="one_sample_z_test",
            null_hypothesis=f"Population mean equals {self.mu}",
            test_statistic=round(float(z), 4),
            p_value=round(z_p, 6),
            decision=decision,
            conclusion=conclusion,
            degrees_of_freedom=None,
            significance_level=self.alpha,
            metadata={
                "hypothesized_mean": self.mu,
                "assumed_population_std": self.population_std,
                "sample_size": n,
                "sample_mean": round(mean, 4)
            }
        )

    def run_one_sample_t_test(self, series: pd.Series) -> TestResult:
        """
        One-Sample T-Test:
        H0: mu = 65
        H1: mu != 65
        """
        clean_series = series.dropna()
        n = len(clean_series)
        t_stat, t_p = stats.ttest_1samp(clean_series, self.mu)
        t_stat = float(t_stat)
        t_p = float(t_p)

        decision = "Reject H0" if t_p < self.alpha else "Fail to Reject H0"
        conclusion = (
            "Average exam score differs significantly from 65."
            if t_p < self.alpha
            else "No significant difference from 65."
        )

        return TestResult(
            test_name="one_sample_t_test",
            null_hypothesis=f"Population mean equals {self.mu}",
            test_statistic=round(t_stat, 4),
            p_value=round(t_p, 6),
            decision=decision,
            conclusion=conclusion,
            degrees_of_freedom=n - 1,
            significance_level=self.alpha,
            metadata={
                "hypothesized_mean": self.mu,
                "sample_size": n,
                "sample_std": round(float(clean_series.std(ddof=1)), 4)
            }
        )

    def run_chi_square_test(self, df: pd.DataFrame) -> Tuple[TestResult, pd.DataFrame]:
        """
        Chi-Square Test of Independence:
        Variables: Internet Access vs Motivation Level
        """
        table = pd.crosstab(df["Internet_Access"], df["Motivation_Level"])
        chi2, chi_p, dof, expected = stats.chi2_contingency(table)
        chi2 = float(chi2)
        chi_p = float(chi_p)

        decision = "Reject H0" if chi_p < self.alpha else "Fail to Reject H0"
        conclusion = (
            "Internet Access and Motivation Level are significantly associated."
            if chi_p < self.alpha
            else "No significant association was detected."
        )

        result = TestResult(
            test_name="chi_square_independence",
            null_hypothesis="Internet Access and Motivation Level are independent",
            test_statistic=round(chi2, 4),
            p_value=round(chi_p, 6),
            decision=decision,
            conclusion=conclusion,
            degrees_of_freedom=int(dof),
            significance_level=self.alpha,
            metadata={
                "variables": ["Internet_Access", "Motivation_Level"],
                "table_shape": list(table.shape)
            }
        )
        return result, table

    def analyze(self, df: pd.DataFrame, persist_to_db: bool = True) -> StatisticalAnalysisReport:
        """Run complete statistical suite on dataframe."""
        exam_scores = df["Exam_Score"].dropna()
        summary = DatasetSummary(
            total_students=len(df),
            sample_mean=round(float(exam_scores.mean()), 4),
            sample_std=round(float(exam_scores.std(ddof=1)), 4)
        )

        z_res = self.run_one_sample_z_test(exam_scores)
        t_res = self.run_one_sample_t_test(exam_scores)
        chi2_res, crosstab_tbl = self.run_chi_square_test(df)

        if persist_to_db and db_manager.is_available:
            try:
                for res in [z_res, t_res, chi2_res]:
                    AnalyticsRepository.save_statistical_result(
                        test_name=res.test_name,
                        null_hypothesis=res.null_hypothesis,
                        test_statistic=res.test_statistic,
                        p_value=res.p_value,
                        decision=res.decision,
                        conclusion=res.conclusion,
                        degrees_of_freedom=res.degrees_of_freedom,
                        significance_level=res.significance_level,
                        metadata=res.metadata
                    )
            except Exception as e:
                # Log without halting in-memory flow
                pass

        return StatisticalAnalysisReport(
            summary=summary,
            z_test=z_res,
            t_test=t_res,
            chi2_test=chi2_res,
            crosstab_table=crosstab_tbl
        )

    @staticmethod
    def format_report_text(report: StatisticalAnalysisReport) -> str:
        """Format report matching the exact console output of the original notebook."""
        lines = [
            "=" * 55,
            "STUDENT PERFORMANCE STATISTICAL ANALYSIS",
            "=" * 55,
            "",
            "DATASET INFORMATION",
            f"Total Students: {report.summary.total_students}",
            f"Sample Mean: {report.summary.sample_mean}",
            f"Sample Standard Deviation: {report.summary.sample_std}",
            "",
            "1. ONE-SAMPLE Z-TEST",
            f"Hypothesized Mean: {report.z_test.metadata['hypothesized_mean']}",
            f"Assumed Population Standard Deviation: {report.z_test.metadata['assumed_population_std']}",
            f"Z-Statistic: {report.z_test.test_statistic}",
            f"P-Value: {report.z_test.p_value}",
            f"Decision: {report.z_test.decision}",
            f"Conclusion: {report.z_test.conclusion}",
            "",
            "2. ONE-SAMPLE T-TEST",
            f"Hypothesized Mean: {report.t_test.metadata['hypothesized_mean']}",
            f"T-Statistic: {report.t_test.test_statistic}",
            f"P-Value: {report.t_test.p_value}",
            f"Decision: {report.t_test.decision}",
            f"Conclusion: {report.t_test.conclusion}",
            "",
            "3. CHI-SQUARE TEST OF INDEPENDENCE",
            "Variables: Internet Access vs Motivation Level",
            "",
            "Observed Frequency Table:",
            str(report.crosstab_table),
            "",
            f"Chi-Square Statistic: {report.chi2_test.test_statistic}",
            f"Degrees of Freedom: {report.chi2_test.degrees_of_freedom}",
            f"P-Value: {report.chi2_test.p_value}",
            f"Decision: {report.chi2_test.decision}",
            f"Conclusion: {report.chi2_test.conclusion}",
            "",
            "=" * 55,
            f"SIGNIFICANCE LEVEL: {report.z_test.significance_level}",
            "=" * 55
        ]
        return "\n".join(lines)
