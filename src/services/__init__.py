"""
Services package for Data Ingestion, Statistical Analysis, and OLAP operations.
"""

from src.services.data_ingestion import DataIngestionService
from src.services.statistical_analysis import StatisticalAnalysisService, StatisticalAnalysisReport
from src.services.olap_analytics import OLAPAnalyticsService, OLAPAnalysisReport
from src.services.student_service import StudentService

__all__ = [
    "DataIngestionService",
    "StatisticalAnalysisService",
    "StatisticalAnalysisReport",
    "OLAPAnalyticsService",
    "OLAPAnalysisReport",
    "StudentService",
]

