-- Schema: Student Performance Analytics & Machine Learning Persistence
-- Database: PostgreSQL 18+ (compatible with 12+)

-- 1. Main Student Records Table
CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    hours_studied INT NOT NULL CHECK (hours_studied >= 0),
    attendance INT NOT NULL CHECK (attendance >= 0 AND attendance <= 100),
    parental_involvement VARCHAR(32) NOT NULL,
    access_to_resources VARCHAR(32) NOT NULL,
    extracurricular_activities VARCHAR(16) NOT NULL,
    sleep_hours INT NOT NULL CHECK (sleep_hours >= 0),
    previous_scores INT NOT NULL CHECK (previous_scores >= 0 AND previous_scores <= 100),
    motivation_level VARCHAR(32) NOT NULL,
    internet_access VARCHAR(16) NOT NULL,
    tutoring_sessions INT NOT NULL CHECK (tutoring_sessions >= 0),
    family_income VARCHAR(32) NOT NULL,
    teacher_quality VARCHAR(32), -- Nullable based on dataset
    school_type VARCHAR(32) NOT NULL,
    peer_influence VARCHAR(32) NOT NULL,
    physical_activity INT NOT NULL CHECK (physical_activity >= 0),
    learning_disabilities VARCHAR(16) NOT NULL,
    parental_education_level VARCHAR(64), -- Nullable based on dataset
    distance_from_home VARCHAR(32), -- Nullable based on dataset
    gender VARCHAR(16) NOT NULL,
    exam_score DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes on Student Records
CREATE INDEX IF NOT EXISTS idx_students_exam_score ON students (exam_score);
CREATE INDEX IF NOT EXISTS idx_students_attendance ON students (attendance);
CREATE INDEX IF NOT EXISTS idx_students_exam_attendance ON students (exam_score, attendance);
CREATE INDEX IF NOT EXISTS idx_students_internet_motivation ON students (internet_access, motivation_level);

-- 2. Statistical Test Results Table
CREATE TABLE IF NOT EXISTS statistical_test_results (
    id SERIAL PRIMARY KEY,
    test_name VARCHAR(64) NOT NULL,
    null_hypothesis TEXT NOT NULL,
    test_statistic DOUBLE PRECISION NOT NULL,
    p_value DOUBLE PRECISION NOT NULL,
    degrees_of_freedom INT,
    significance_level DOUBLE PRECISION NOT NULL DEFAULT 0.05,
    decision VARCHAR(32) NOT NULL,
    conclusion TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stat_results_name ON statistical_test_results (test_name);

-- 3. OLAP Precomputed Summary Cache
CREATE TABLE IF NOT EXISTS olap_aggregations_cache (
    id SERIAL PRIMARY KEY,
    aggregation_key VARCHAR(64) UNIQUE NOT NULL,
    results JSONB NOT NULL,
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
