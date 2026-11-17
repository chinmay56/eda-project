"""
SQLAlchemy ORM models for Student Performance System.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class StudentRecord(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hours_studied = Column(Integer, nullable=False)
    attendance = Column(Integer, nullable=False)
    parental_involvement = Column(String(32), nullable=False)
    access_to_resources = Column(String(32), nullable=False)
    extracurricular_activities = Column(String(16), nullable=False)
    sleep_hours = Column(Integer, nullable=False)
    previous_scores = Column(Integer, nullable=False)
    motivation_level = Column(String(32), nullable=False)
    internet_access = Column(String(16), nullable=False)
    tutoring_sessions = Column(Integer, nullable=False)
    family_income = Column(String(32), nullable=False)
    teacher_quality = Column(String(32), nullable=True)
    school_type = Column(String(32), nullable=False)
    peer_influence = Column(String(32), nullable=False)
    physical_activity = Column(Integer, nullable=False)
    learning_disabilities = Column(String(16), nullable=False)
    parental_education_level = Column(String(64), nullable=True)
    distance_from_home = Column(String(32), nullable=True)
    gender = Column(String(16), nullable=False)
    exam_score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    predictions = relationship("ModelPrediction", back_populates="student")

    __table_args__ = (
        CheckConstraint("hours_studied >= 0", name="chk_hours_studied"),
        CheckConstraint("attendance >= 0 AND attendance <= 100", name="chk_attendance"),
        CheckConstraint("sleep_hours >= 0", name="chk_sleep_hours"),
        CheckConstraint("previous_scores >= 0 AND previous_scores <= 100", name="chk_prev_scores"),
    )


class StatisticalTestResult(Base):
    __tablename__ = "statistical_test_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_name = Column(String(64), nullable=False, index=True)
    null_hypothesis = Column(Text, nullable=False)
    test_statistic = Column(Float, nullable=False)
    p_value = Column(Float, nullable=False)
    degrees_of_freedom = Column(Integer, nullable=True)
    significance_level = Column(Float, default=0.05, nullable=False)
    decision = Column(String(32), nullable=False)
    conclusion = Column(Text, nullable=False)
    metadata_json = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class MLModelRun(Base):
    __tablename__ = "ml_model_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(64), nullable=False)
    model_version = Column(String(32), nullable=False)
    train_samples = Column(Integer, nullable=False)
    test_samples = Column(Integer, nullable=False)
    r2_score = Column(Float, nullable=False)
    rmse = Column(Float, nullable=False)
    mae = Column(Float, nullable=False)
    cv_mean_r2 = Column(Float, nullable=True)
    hyperparameters = Column(JSONB, nullable=True)
    artifact_path = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    predictions = relationship("ModelPrediction", back_populates="run", cascade="all, delete-orphan")


class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("ml_model_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True)
    actual_score = Column(Float, nullable=True)
    predicted_score = Column(Float, nullable=False)
    residual = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    run = relationship("MLModelRun", back_populates="predictions")
    student = relationship("StudentRecord", back_populates="predictions")


class OLAPAggregationCache(Base):
    __tablename__ = "olap_aggregations_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    aggregation_key = Column(String(64), unique=True, nullable=False)
    results = Column(JSONB, nullable=False)
    computed_at = Column(DateTime(timezone=True), default=datetime.utcnow)
