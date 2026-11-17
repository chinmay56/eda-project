"""
OLAP Analytics Service.
Performs multidimensional slicing, dicing, pivoting, and aggregation.
Supports both in-memory vectorized Pandas execution and direct PostgreSQL pushdown.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import pandas as pd

from src.database.connection import db_manager
from src.database.repository import StudentRepository


@dataclass
class OLAPAnalysisReport:
    sliced_data: pd.DataFrame
    diced_data: pd.DataFrame
    diced_count: int
    pivot_table: pd.DataFrame
    aggregation_data: pd.Series


class OLAPAnalyticsService:
    """Service providing high-performance OLAP operations on student data."""

    def __init__(self, use_db_pushdown: bool = False):
        self.use_db_pushdown = use_db_pushdown

    def slice_data(self, df: Optional[pd.DataFrame] = None, rows: int = 10, cols: int = 5) -> pd.DataFrame:
        """Slicing operation: extracts a submatrix by rows and columns."""
        if self.use_db_pushdown and db_manager.is_available:
            return StudentRepository.slice_data(limit=rows, offset=0)

        if df is None:
            raise ValueError("DataFrame required for in-memory slicing.")
        return df.iloc[0:rows, 0:cols]

    def dice_data(
        self,
        df: Optional[pd.DataFrame] = None,
        min_exam_score: float = 70.0,
        min_attendance: int = 80
    ) -> pd.DataFrame:
        """
        Dicing operation: filters multidimensional records meeting both thresholds.
        Exam_Score > 70 AND Attendance > 80.
        """
        if self.use_db_pushdown and db_manager.is_available:
            return StudentRepository.dice_data(min_exam_score, min_attendance)

        if df is None:
            raise ValueError("DataFrame required for in-memory dicing.")
        return df[(df["Exam_Score"] > min_exam_score) & (df["Attendance"] > min_attendance)]

    def create_pivot_table(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Pivot table: cross-tabulates mean Exam_Score across
        Internet_Access (rows) and Motivation_Level (columns).
        """
        if self.use_db_pushdown and db_manager.is_available:
            return StudentRepository.pivot_internet_vs_motivation()

        if df is None:
            raise ValueError("DataFrame required for in-memory pivot.")
        return pd.pivot_table(
            df,
            values="Exam_Score",
            index="Internet_Access",
            columns="Motivation_Level",
            aggfunc="mean"
        )

    def aggregate_exam_scores(self, df: Optional[pd.DataFrame] = None) -> pd.Series:
        """
        Aggregation operation: computes mean, median, min, max, std, count
        on Exam_Score.
        """
        if self.use_db_pushdown and db_manager.is_available:
            agg_dict = StudentRepository.aggregate_exam_scores()
            return pd.Series(agg_dict, name="Exam_Score")

        if df is None:
            raise ValueError("DataFrame required for in-memory aggregation.")
        return df["Exam_Score"].agg(["mean", "median", "min", "max", "std", "count"])

    def run_all(self, df: pd.DataFrame) -> OLAPAnalysisReport:
        """Run complete OLAP analysis."""
        sliced = self.slice_data(df, rows=10, cols=5)
        diced = self.dice_data(df, min_exam_score=70.0, min_attendance=80)
        pivoted = self.create_pivot_table(df)
        aggregated = self.aggregate_exam_scores(df)

        return OLAPAnalysisReport(
            sliced_data=sliced,
            diced_data=diced,
            diced_count=len(diced),
            pivot_table=pivoted,
            aggregation_data=aggregated
        )

    @staticmethod
    def format_report_text(report: OLAPAnalysisReport) -> str:
        """Format output string matching notebook Cell 2."""
        lines = [
            "=" * 50,
            "STUDENT PERFORMANCE DATA ANALYSIS",
            "=" * 50,
            "",
            "1. SLICING",
            "",
            str(report.sliced_data),
            "",
            "2. DICING",
            "",
            str(report.diced_data.head(10)),
            f"\nTotal Matching Students: {report.diced_count}",
            "",
            "3. PIVOT TABLE",
            "",
            str(report.pivot_table),
            "",
            "4. AGGREGATION",
            "",
            str(report.aggregation_data),
            "",
            "ANALYSIS COMPLETED"
        ]
        return "\n".join(lines)
