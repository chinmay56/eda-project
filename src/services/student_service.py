"""
Student Data Management Service.
Handles record validation, CRUD business logic, and automated CSV synchronization.
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
import pandas as pd

from src.database.connection import db_manager
from src.database.repository import StudentRepository
from src.config import app_settings

logger = logging.getLogger(__name__)

FIELD_DEFINITIONS = {
    "hours_studied": {"type": int, "label": "Hours Studied (0-60)", "min": 0, "max": 60, "default": 20},
    "attendance": {"type": int, "label": "Attendance % (0-100)", "min": 0, "max": 100, "default": 80},
    "parental_involvement": {"type": str, "label": "Parental Involvement", "options": ["Low", "Medium", "High"], "default": "Medium"},
    "access_to_resources": {"type": str, "label": "Access to Resources", "options": ["Low", "Medium", "High"], "default": "Medium"},
    "extracurricular_activities": {"type": str, "label": "Extracurricular Activities", "options": ["Yes", "No"], "default": "No"},
    "sleep_hours": {"type": int, "label": "Sleep Hours (0-24)", "min": 0, "max": 24, "default": 7},
    "previous_scores": {"type": int, "label": "Previous Scores (0-100)", "min": 0, "max": 100, "default": 75},
    "motivation_level": {"type": str, "label": "Motivation Level", "options": ["Low", "Medium", "High"], "default": "Medium"},
    "internet_access": {"type": str, "label": "Internet Access", "options": ["Yes", "No"], "default": "Yes"},
    "tutoring_sessions": {"type": int, "label": "Tutoring Sessions (>=0)", "min": 0, "max": 20, "default": 1},
    "family_income": {"type": str, "label": "Family Income", "options": ["Low", "Medium", "High"], "default": "Medium"},
    "teacher_quality": {"type": str, "label": "Teacher Quality", "options": ["Low", "Medium", "High", None], "default": "Medium", "nullable": True},
    "school_type": {"type": str, "label": "School Type", "options": ["Public", "Private"], "default": "Public"},
    "peer_influence": {"type": str, "label": "Peer Influence", "options": ["Positive", "Neutral", "Negative"], "default": "Neutral"},
    "physical_activity": {"type": int, "label": "Physical Activity Hours/Wk", "min": 0, "max": 20, "default": 3},
    "learning_disabilities": {"type": str, "label": "Learning Disabilities", "options": ["Yes", "No"], "default": "No"},
    "parental_education_level": {"type": str, "label": "Parental Education", "options": ["High School", "College", "Postgraduate", None], "default": "College", "nullable": True},
    "distance_from_home": {"type": str, "label": "Distance from Home", "options": ["Near", "Moderate", "Far", None], "default": "Near", "nullable": True},
    "gender": {"type": str, "label": "Gender", "options": ["Male", "Female"], "default": "Female"},
    "exam_score": {"type": float, "label": "Exam Score (0-100)", "min": 0.0, "max": 105.0, "default": 70.0},
}


class StudentService:
    """Service providing validated student data mutation and automatic CSV syncing."""

    @staticmethod
    def validate_value(field: str, raw_value: Any) -> Tuple[bool, Optional[str], Any]:
        """Validate and cast a raw user input value for a given field."""
        field_lower = field.lower()
        if field_lower not in FIELD_DEFINITIONS:
            return False, f"Unknown field '{field}'. Valid fields: {list(FIELD_DEFINITIONS.keys())}", None

        spec = FIELD_DEFINITIONS[field_lower]

        # Handle None / empty strings for nullable fields
        if raw_value is None or (isinstance(raw_value, str) and raw_value.strip().lower() in ["", "none", "null"]):
            if spec.get("nullable"):
                return True, None, None
            return False, f"Field '{field}' cannot be null or empty.", None

        expected_type = spec["type"]

        try:
            if expected_type == int:
                val = int(raw_value)
                if "min" in spec and val < spec["min"]:
                    return False, f"{field} must be >= {spec['min']} (got {val}).", None
                if "max" in spec and val > spec["max"]:
                    return False, f"{field} must be <= {spec['max']} (got {val}).", None
                return True, None, val

            elif expected_type == float:
                val = float(raw_value)
                if "min" in spec and val < spec["min"]:
                    return False, f"{field} must be >= {spec['min']} (got {val}).", None
                if "max" in spec and val > spec["max"]:
                    return False, f"{field} must be <= {spec['max']} (got {val}).", None
                return True, None, round(val, 2)

            elif expected_type == str:
                val_str = str(raw_value).strip()
                if "options" in spec:
                    # Case-insensitive match against allowed options
                    match = next((opt for opt in spec["options"] if opt and opt.lower() == val_str.lower()), None)
                    if match is not None:
                        return True, None, match
                    allowed = [str(o) for o in spec["options"] if o is not None]
                    return False, f"Invalid value '{val_str}' for {field}. Allowed: {allowed}", None
                return True, None, val_str

        except (ValueError, TypeError):
            return False, f"Invalid type for {field}. Expected {expected_type.__name__}.", None

        return True, None, raw_value

    @staticmethod
    def get_student(student_id: int) -> Optional[Dict[str, Any]]:
        """Fetch student record by ID."""
        if not db_manager.is_available:
            raise ConnectionError("Database is not reachable.")
        return StudentRepository.get_by_id(student_id)

    @staticmethod
    def list_students(limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """List students with pagination."""
        if not db_manager.is_available:
            raise ConnectionError("Database is not reachable.")
        return StudentRepository.list_students(limit=limit, offset=offset)

    @classmethod
    def update_student(cls, student_id: int, updates: Dict[str, Any], sync_csv: bool = True) -> Dict[str, Any]:
        """
        Validate updates, update in PostgreSQL, and optionally sync back to CSV.
        """
        if not db_manager.is_available:
            return {"status": "error", "message": "Database is not connected."}

        existing = StudentRepository.get_by_id(student_id)
        if not existing:
            return {"status": "error", "message": f"Student with ID {student_id} not found."}

        cleaned_updates: Dict[str, Any] = {}
        errors: List[str] = []

        for field, raw_val in updates.items():
            valid, err_msg, cleaned_val = cls.validate_value(field, raw_val)
            if not valid:
                errors.append(err_msg or f"Invalid value for {field}")
            else:
                cleaned_updates[field.lower()] = cleaned_val

        if errors:
            return {"status": "validation_error", "message": "; ".join(errors), "errors": errors}

        if not cleaned_updates:
            return {"status": "no_op", "message": "No valid fields provided to update."}

        updated = StudentRepository.update_student(student_id, cleaned_updates)
        if not updated:
            return {"status": "error", "message": f"Failed to update student {student_id}."}

        csv_synced = False
        if sync_csv:
            try:
                StudentRepository.export_to_csv()
                csv_synced = True
            except Exception as exc:
                logger.error("Failed to sync CSV after update: %s", exc)

        refreshed = StudentRepository.get_by_id(student_id)
        return {
            "status": "success",
            "message": f"Student #{student_id} updated successfully.",
            "student_id": student_id,
            "updated_fields": list(cleaned_updates.keys()),
            "csv_synced": csv_synced,
            "record": refreshed
        }

    @classmethod
    def add_student(cls, data: Dict[str, Any], sync_csv: bool = True) -> Dict[str, Any]:
        """
        Validate and insert a new student record, then optionally sync to CSV.
        """
        if not db_manager.is_available:
            return {"status": "error", "message": "Database is not connected."}

        cleaned_record: Dict[str, Any] = {}
        errors: List[str] = []

        # Validate provided fields or apply defaults
        for field, spec in FIELD_DEFINITIONS.items():
            raw_val = data.get(field, spec["default"])
            valid, err_msg, cleaned_val = cls.validate_value(field, raw_val)
            if not valid:
                errors.append(err_msg or f"Invalid value for {field}")
            else:
                cleaned_record[field] = cleaned_val

        if errors:
            return {"status": "validation_error", "message": "; ".join(errors), "errors": errors}

        new_id = StudentRepository.insert_student(cleaned_record)
        csv_synced = False
        if sync_csv:
            try:
                StudentRepository.export_to_csv()
                csv_synced = True
            except Exception as exc:
                logger.error("Failed to sync CSV after insert: %s", exc)

        return {
            "status": "success",
            "message": f"Student #{new_id} added successfully.",
            "student_id": new_id,
            "csv_synced": csv_synced,
            "record": StudentRepository.get_by_id(new_id)
        }

    @staticmethod
    def delete_student(student_id: int, sync_csv: bool = True) -> Dict[str, Any]:
        """
        Delete a student record by ID, then optionally sync to CSV.
        """
        if not db_manager.is_available:
            return {"status": "error", "message": "Database is not connected."}

        existing = StudentRepository.get_by_id(student_id)
        if not existing:
            return {"status": "error", "message": f"Student with ID {student_id} does not exist."}

        deleted = StudentRepository.delete_student(student_id)
        if not deleted:
            return {"status": "error", "message": f"Failed to delete student {student_id}."}

        csv_synced = False
        if sync_csv:
            try:
                StudentRepository.export_to_csv()
                csv_synced = True
            except Exception as exc:
                logger.error("Failed to sync CSV after delete: %s", exc)

        return {
            "status": "success",
            "message": f"Student #{student_id} deleted successfully.",
            "student_id": student_id,
            "csv_synced": csv_synced,
            "total_records": StudentRepository.count()
        }

    @staticmethod
    def sync_db_to_csv() -> Dict[str, Any]:
        """Manually trigger export of current PostgreSQL table to CSV."""
        if not db_manager.is_available:
            return {"status": "error", "message": "Database is not connected."}
        count = StudentRepository.export_to_csv()
        return {
            "status": "success",
            "message": f"Successfully exported {count} records to {app_settings.data_path}.",
            "exported_rows": count
        }

    @staticmethod
    def format_student_card(record: Dict[str, Any]) -> str:
        """Format a student record into a clean, human-readable terminal display."""
        lines = [
            f"+{'-' * 50}+",
            f"| STUDENT RECORD #{record.get('id', 'N/A'):<32} |",
            f"+{'-' * 50}+",
            f"|  * Exam Score:            {record.get('exam_score', 'N/A'):<22} |",
            f"|  * Attendance:            {record.get('attendance', 'N/A'):<22} |",
            f"|  * Hours Studied:         {record.get('hours_studied', 'N/A'):<22} |",
            f"|  * Previous Scores:       {record.get('previous_scores', 'N/A'):<22} |",
            f"|  * Motivation Level:      {str(record.get('motivation_level', 'N/A')):<22} |",
            f"|  * Internet Access:       {str(record.get('internet_access', 'N/A')):<22} |",
            f"|  * Tutoring Sessions:     {record.get('tutoring_sessions', 'N/A'):<22} |",
            f"|  * Sleep Hours:           {record.get('sleep_hours', 'N/A'):<22} |",
            f"|  * Physical Activity:     {record.get('physical_activity', 'N/A'):<22} |",
            f"|  * Parental Involvement:  {str(record.get('parental_involvement', 'N/A')):<22} |",
            f"|  * Access to Resources:   {str(record.get('access_to_resources', 'N/A')):<22} |",
            f"|  * Family Income:         {str(record.get('family_income', 'N/A')):<22} |",
            f"|  * Teacher Quality:       {str(record.get('teacher_quality', 'N/A')):<22} |",
            f"|  * School Type:           {str(record.get('school_type', 'N/A')):<22} |",
            f"|  * Peer Influence:        {str(record.get('peer_influence', 'N/A')):<22} |",
            f"|  * Learning Disabilities: {str(record.get('learning_disabilities', 'N/A')):<22} |",
            f"|  * Parental Education:    {str(record.get('parental_education_level', 'N/A')):<22} |",
            f"|  * Distance from Home:    {str(record.get('distance_from_home', 'N/A')):<22} |",
            f"|  * Gender:                {str(record.get('gender', 'N/A')):<22} |",
            f"+{'-' * 50}+"
        ]
        return "\n".join(lines)
