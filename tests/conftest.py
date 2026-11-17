"""
Pytest fixtures and configuration.
"""

import pytest
import pandas as pd
from pathlib import Path

from src.config import app_settings
from src.services.data_ingestion import DataIngestionService


@pytest.fixture(scope="session")
def real_dataset() -> pd.DataFrame:
    """Load the full 6,607-row student performance dataset."""
    service = DataIngestionService()
    return service.load_csv()


@pytest.fixture
def synthetic_sample() -> pd.DataFrame:
    """Create a minimal synthetic student DataFrame for unit testing."""
    data = {
        "Hours_Studied": [20, 25, 15, 30, 10],
        "Attendance": [85, 95, 75, 90, 60],
        "Parental_Involvement": ["Low", "Medium", "High", "Medium", "Low"],
        "Access_to_Resources": ["High", "Medium", "Low", "High", "Low"],
        "Extracurricular_Activities": ["No", "Yes", "No", "Yes", "No"],
        "Sleep_Hours": [7, 8, 6, 7, 5],
        "Previous_Scores": [70, 85, 60, 92, 55],
        "Motivation_Level": ["Low", "High", "Medium", "High", "Low"],
        "Internet_Access": ["Yes", "Yes", "No", "Yes", "No"],
        "Tutoring_Sessions": [1, 2, 0, 3, 0],
        "Family_Income": ["Medium", "High", "Low", "High", "Low"],
        "Teacher_Quality": ["Medium", "High", "Low", "High", "Low"],
        "School_Type": ["Public", "Public", "Private", "Public", "Private"],
        "Peer_Influence": ["Neutral", "Positive", "Negative", "Positive", "Neutral"],
        "Physical_Activity": [3, 4, 2, 5, 1],
        "Learning_Disabilities": ["No", "No", "No", "No", "Yes"],
        "Parental_Education_Level": ["High School", "College", "Postgraduate", "College", "High School"],
        "Distance_from_Home": ["Near", "Moderate", "Far", "Near", "Far"],
        "Gender": ["Male", "Female", "Male", "Female", "Male"],
        "Exam_Score": [68.0, 75.0, 62.0, 80.0, 58.0],
    }
    return pd.DataFrame(data)
