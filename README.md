# Student Performance Exploratory Data Analysis (EDA) & OLAP System

A high-performance, modular Python application migrated from Google Colab to VS Code, integrated with **PostgreSQL 18** and **pgAdmin**, featuring automated inferential hypothesis testing, multidimensional OLAP analytics, and database query pushdown.

---

## 📌 Architecture Overview

```
eda project/
│── student_performance_analysis.ipynb # Clean, pre-rendered Jupyter notebook
│── app.py                          # Terminal CLI runner & pipeline orchestrator
│── requirements.txt                # Lean dependency manifest (Pandas, SciPy, PostgreSQL)
│── .env                            # Active environment configuration (gitignored)
│── .env.example                    # Template environment configuration
│── .gitignore                      # Git ignore rules
│
├── data/
│   └── StudentPerformanceFactors.csv  # 6,607-record student dataset
│
├── docs/
│   ├── PROJECT_ANALYSIS.md         # Comprehensive architectural & complexity analysis
│   └── PERFORMANCE_REPORT.md       # Empirical benchmarks & optimization metrics
│
├── src/
│   ├── config.py                   # Pydantic environment configuration (RFC 3986 safe)
│   ├── database/
│   │   ├── connection.py           # SimpleConnectionPool & SQLAlchemy engine
│   │   ├── schema.sql              # Normalized DDL schema with B-Tree indexes
│   │   └── repository.py           # Parameterized queries, bulk inserts & OLAP pushdown
│   └── services/
│       ├── data_ingestion.py       # Validated bulk data ingestion
│       ├── statistical_analysis.py # Z-test, T-test, Chi-square hypothesis engine
│       └── olap_analytics.py       # Slicing, dicing, pivot tables & aggregations
│
└── tests/
    ├── conftest.py                 # Pytest fixtures & real dataset loader
    ├── test_database.py            # PostgreSQL CRUD & transaction rollback tests
    ├── test_statistical_tests.py   # Statistical invariance tests (Z-test, T-test, Chi-sq)
    └── test_olap_operations.py     # OLAP tests (exact 969 diced records)
```

---

## 🎯 Project Core Components (What to Explain to "Mam")

This project addresses five essential Data Science and Database Analytics pillars:

1. **Exploratory Data Analysis (EDA)**:
   - Evaluates continuous student metrics (Hours Studied, Attendance, Previous Scores).
   - Audits missing values and computes linear Pearson correlations with `Exam_Score`.
   - Attendance ($r = +0.5811$) and Hours Studied ($r = +0.4455$) have the strongest positive correlation with student performance.

2. **Inferential Hypothesis Testing**:
   - **One-Sample Z-Test**: $Z = 18.1722, p = 0.0$ $\to$ **Reject $H_0$** (Significant difference from hypothesized benchmark $\mu = 65.0$).
   - **One-Sample T-Test**: $T = 46.7097, p = 0.0$ $\to$ **Reject $H_0$**.
   - **Chi-Square Test of Independence**: $\chi^2 = 2.7338, \text{dof} = 2, p = 0.254894$ $\to$ **Fail to Reject $H_0$** (Internet Access and Motivation Level are statistically independent).

3. **Multidimensional OLAP (Online Analytical Processing)**:
   - **Slicing**: Subsetting a $10 \times 5$ sub-matrix across defined dimensions.
   - **Dicing**: Filtering across multiple conditions (`Exam_Score > 70` AND `Attendance > 80`). Yields exactly **969 matching students**.
   - **Pivot Table**: 2D cross-tabulation of `Internet_Access` vs `Motivation_Level` on `Exam_Score`.
   - **Aggregations**: Computing dataset-level metric summaries (Mean: 67.24, Median: 67.0, Std: 3.89).

4. **PostgreSQL Relational Storage & Query Pushdown**:
   - 6,607 student records stored in local PostgreSQL `students` table.
   - Analytics operations pushed down directly to PostgreSQL via SQL queries, achieving **$O(1)$ constant client memory** consumption.

5. **Computational Complexity & Optimization**:
   - Baseline naive Colab notebook required $2\times$ redundant disk I/O and multi-pass filtering.
   - Optimized Python pipeline uses single-pass shared memory and vectorized SIMD operations for a **20%+ memory reduction**.

---

## 🚀 How to Run in VS Code / PowerShell

Ensure your virtual environment is active:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\.venv\Scripts\Activate.ps1
```

### 1. Launch the Clean Web Dashboard (Recommended for Institution / College)
```powershell
streamlit run dashboard.py
```
This launches the modern, clean academic dashboard in your browser:
- **Executive Overview**: High-level KPIs, grade distributions, and factor correlations.
- **Cohort Analysis**: Socioeconomic & institutional factor breakdowns with boxplots.
- **Multidimensional OLAP**: Interactive Slicing, Dicing, and 2D Pivot Heatmap cross-tabs.
- **Hypothesis Testing**: Interactive Z-Test, T-Test, and Chi-Square independence evaluation.
- **Predictor & Advisory**: AI marks simulation, pass/fail probability, and personalized intervention plans.
- **Student Records (CRUD)**: Search, add, and edit student records directly in PostgreSQL.

### 2. Run Complete Workflow in Terminal
```powershell
python app.py all
```

### 3. Run Individual Modules
```powershell
# Run Exploratory Data Analysis (EDA)
python app.py eda

# Run Hypothesis Tests (Z-test, T-test, Chi-square)
python app.py stats

# Run Multidimensional OLAP (Slicing, Dicing, Pivot Table)
python app.py olap

# Run Performance Benchmark (Naive vs Optimized)
python app.py benchmark
```

### 3. Interactive Student Data Management & CRUD
Run the interactive console to view, search, update, add, or delete student records with automated CSV synchronization:
```powershell
python app.py manage
```

Or perform direct scripted operations from the command line:
```powershell
# View a specific student record
python app.py view --id 1

# Update student attributes (automatically updates PostgreSQL & CSV)
python app.py update --id 1 --exam-score 85.0 --attendance 92 --motivation-level High

# Add a new student record
python app.py add --exam-score 78.0 --attendance 85 --hours-studied 22 --gender Female

# Delete a student record
python app.py delete --id 6608 --yes

# Manually trigger export from PostgreSQL to CSV
python app.py sync-csv
```

### 4. Open the Jupyter Notebook
Open [`student_performance_analysis.ipynb`](student_performance_analysis.ipynb) in VS Code to see clean tables, markdown explanations, and pre-rendered results.

### 5. Run Automated Pytest Suite
```powershell
pytest -v
```
All 17 unit, regression, database, and CRUD synchronization tests pass in ~1.0 second.

