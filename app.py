"""
Application Entry Point for Student Performance Exploratory Data Analysis (EDA) & OLAP Analytics.
Provides a comprehensive CLI interface and pipeline orchestrator integrated with PostgreSQL.
"""

import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

from src.config import app_settings, db_settings
from src.database.connection import db_manager
from src.services.data_ingestion import DataIngestionService
from src.services.statistical_analysis import StatisticalAnalysisService
from src.services.olap_analytics import OLAPAnalyticsService
from src.services.student_service import StudentService, FIELD_DEFINITIONS



def cmd_ingest(args) -> None:
    """Ingest CSV data into PostgreSQL."""
    print("=" * 65)
    print("DATA INGESTION PIPELINE")
    print("=" * 65)
    service = DataIngestionService()
    res = service.sync_to_database(force=args.force)
    print(f"Status: {res['status']}")
    print(f"Message: {res['message']}")
    if "rows_synced" in res and res["rows_synced"] > 0:
        print(f"Ingested {res['rows_synced']} records in {res.get('elapsed_ms')} ms.")
    if "total_records" in res:
        print(f"Total Database Records: {res['total_records']}")


def cmd_eda(args) -> None:
    """Perform comprehensive Exploratory Data Analysis (EDA)."""
    print("=" * 65)
    print("EXPLORATORY DATA ANALYSIS (EDA)")
    print("=" * 65)
    service = DataIngestionService()
    df = service.load_csv()

    print(f"\n1. DATASET OVERVIEW:")
    print(f"   - Total Rows:    {df.shape[0]:,}")
    print(f"   - Total Columns: {df.shape[1]}")
    print(f"   - Memory Usage:  {df.memory_usage(deep=True).sum() / 1024:.2f} KB")

    print(f"\n2. MISSING VALUES PER COLUMN:")
    missing = df.isnull().sum()
    missing_cols = missing[missing > 0]
    if len(missing_cols) == 0:
        print("   - No missing values detected across all columns.")
    else:
        for col, count in missing_cols.items():
            pct = (count / len(df)) * 100
            print(f"   - {col:25s}: {count:4d} missing ({pct:.2f}%)")

    print(f"\n3. DESCRIPTIVE STATISTICS (Continuous Variables):")
    num_cols = ["Exam_Score", "Hours_Studied", "Attendance", "Previous_Scores", "Sleep_Hours", "Tutoring_Sessions", "Physical_Activity"]
    num_df = df[num_cols].describe().T[["count", "mean", "std", "min", "50%", "max"]]
    num_df.columns = ["Count", "Mean", "Std Dev", "Min", "Median", "Max"]
    print(num_df.to_string())

    print(f"\n4. LINEAR CORRELATION WITH EXAM SCORE:")
    numeric_data = df.select_dtypes(include=[np.number])
    correlations = numeric_data.corr()["Exam_Score"].drop("Exam_Score").sort_values(ascending=False)
    for feat, corr in correlations.items():
        print(f"   - {feat:25s}: r = {corr:+.4f}")

    print(f"\n5. CATEGORICAL FACTOR BREAKDOWN (Top Predictors):")
    for cat_col in ["Parental_Involvement", "Access_to_Resources", "Motivation_Level", "Internet_Access"]:
        grp = df.groupby(cat_col)["Exam_Score"].agg(["count", "mean", "std"]).round(2)
        print(f"\n   [{cat_col}] vs Exam Score:")
        print(grp.to_string())


def cmd_stats(args) -> None:
    """Run hypothesis testing suite (Z-test, T-test, Chi-square)."""
    service = DataIngestionService()
    df = service.load_csv()

    stats_service = StatisticalAnalysisService(
        alpha=args.alpha, mu=args.mu, population_std=args.pop_std
    )
    report = stats_service.analyze(df, persist_to_db=not args.no_persist)
    print(stats_service.format_report_text(report))


def cmd_olap(args) -> None:
    """Run OLAP multidimensional operations (Slicing, Dicing, Pivot Table, Aggregations)."""
    service = DataIngestionService()
    df = service.load_csv()

    olap_service = OLAPAnalyticsService(use_db_pushdown=args.pushdown)
    report = olap_service.run_all(df)
    print(olap_service.format_report_text(report))


def cmd_benchmark(args) -> None:
    """Run computational complexity & memory benchmarks."""
    import time
    import tracemalloc

    print("=" * 65)
    print("COMPUTATIONAL COMPLEXITY & PERFORMANCE BENCHMARK")
    print("=" * 65)

    csv_path = app_settings.data_path

    # 1. Baseline Naive Pipeline (Uncached double-read + redundant memory allocations)
    def naive_run():
        tracemalloc.start()
        t0 = time.perf_counter()
        d1 = pd.read_csv(csv_path)
        exam1 = d1["Exam_Score"].dropna()
        _ = exam1.mean()
        _ = exam1.std(ddof=1)
        d2 = pd.read_csv(csv_path)
        _ = d2.iloc[0:10, 0:5]
        _ = d2[(d2["Exam_Score"] > 70) & (d2["Attendance"] > 80)]
        _ = pd.pivot_table(d2, values="Exam_Score", index="Internet_Access", columns="Motivation_Level", aggfunc="mean")
        t1 = time.perf_counter()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return (t1 - t0) * 1000, peak / 1024

    # 2. Optimized Pipeline (Single-pass shared memory + vectorized)
    def optimized_run():
        tracemalloc.start()
        t0 = time.perf_counter()
        df = pd.read_csv(csv_path)
        stats_svc = StatisticalAnalysisService()
        _ = stats_svc.analyze(df, persist_to_db=False)
        olap_svc = OLAPAnalyticsService()
        _ = olap_svc.run_all(df)
        t1 = time.perf_counter()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return (t1 - t0) * 1000, peak / 1024

    naive_times, naive_mems = [], []
    opt_times, opt_mems = [], []

    iterations = args.iterations
    print(f"Executing {iterations} profiling iterations per workload...")
    for _ in range(iterations):
        t, m = naive_run()
        naive_times.append(t)
        naive_mems.append(m)

        t, m = optimized_run()
        opt_times.append(t)
        opt_mems.append(m)

    avg_n_time, avg_n_mem = float(np.mean(naive_times)), float(np.mean(naive_mems))
    avg_o_time, avg_o_mem = float(np.mean(opt_times)), float(np.mean(opt_mems))
    speedup = avg_n_time / avg_o_time
    mem_saving = ((avg_n_mem - avg_o_mem) / avg_n_mem) * 100

    print(f"\n1. NAIVE (Original Notebook Multi-pass / Double I/O):")
    print(f"   - Average Latency:  {avg_n_time:.2f} ms")
    print(f"   - Peak Heap Memory: {avg_n_mem:.2f} KB")

    print(f"\n2. OPTIMIZED (Single-Pass Vectorized Pipeline):")
    print(f"   - Average Latency:  {avg_o_time:.2f} ms")
    print(f"   - Peak Heap Memory: {avg_o_mem:.2f} KB")

    print(f"\n3. GAINS:")
    print(f"   - Execution Speedup:          {speedup:.2f}x faster")
    print(f"   - Memory Footprint Reduction: {mem_saving:.1f}% less memory")
    print("=" * 65)


def cmd_run_all(args) -> None:
    """Run complete pipeline end-to-end."""
    print("=" * 65)
    print("STUDENT PERFORMANCE EDA & OLAP WORKFLOW")
    print("=" * 65)

    # 1. Ingestion
    cmd_ingest(args)
    print()

    # 2. EDA
    cmd_eda(args)
    print()

    # 3. Statistical Analysis
    args.alpha = 0.05
    args.mu = 65.0
    args.pop_std = 10.0
    args.no_persist = False
    cmd_stats(args)
    print()

    # 4. OLAP Analysis
    args.pushdown = False
    cmd_olap(args)
    print()

    # 5. Computational Benchmark
    args.iterations = 5
    cmd_benchmark(args)
    print("\nEnd-to-End Workflow successfully completed!")


def cmd_view(args) -> None:
    """View student record or list students."""
    if getattr(args, "id", None) is not None:
        student = StudentService.get_student(args.id)
        if not student:
            print(f"Error: Student #{args.id} not found in database.")
        else:
            print(StudentService.format_student_card(student))
    else:
        limit = getattr(args, "limit", 10)
        offset = getattr(args, "offset", 0)
        students = StudentService.list_students(limit=limit, offset=offset)
        print("=" * 65)
        print(f"STUDENT RECORDS (Offset: {offset}, Limit: {limit})")
        print("=" * 65)
        for s in students:
            print(f"ID #{s['id']:<5} | Score: {s['exam_score']:<5} | Att: {s['attendance']:<3}% | Study: {s['hours_studied']:<2}h | Motivation: {s['motivation_level']}")


def cmd_update(args) -> None:
    """Update fields of an existing student record."""
    updates = {}
    if getattr(args, "exam_score", None) is not None:
        updates["exam_score"] = args.exam_score
    if getattr(args, "attendance", None) is not None:
        updates["attendance"] = args.attendance
    if getattr(args, "hours_studied", None) is not None:
        updates["hours_studied"] = args.hours_studied
    if getattr(args, "previous_scores", None) is not None:
        updates["previous_scores"] = args.previous_scores
    if getattr(args, "motivation_level", None) is not None:
        updates["motivation_level"] = args.motivation_level
    if getattr(args, "internet_access", None) is not None:
        updates["internet_access"] = args.internet_access
    if getattr(args, "tutoring_sessions", None) is not None:
        updates["tutoring_sessions"] = args.tutoring_sessions
    if getattr(args, "sleep_hours", None) is not None:
        updates["sleep_hours"] = args.sleep_hours

    if not updates:
        print("Error: No update fields provided. Run with --help to see available fields, or run 'python app.py manage' for interactive mode.")
        return

    res = StudentService.update_student(args.id, updates, sync_csv=not getattr(args, "no_sync", False))
    if res["status"] == "success":
        print("=" * 65)
        print(f"UPDATE SUCCESSFUL: {res['message']}")
        print("=" * 65)
        if res.get("csv_synced"):
            print("CSV file (data/StudentPerformanceFactors.csv) synchronized successfully.")
        print(StudentService.format_student_card(res["record"]))
    else:
        print(f"Update failed: {res['message']}")


def cmd_add(args) -> None:
    """Add a new student record."""
    data = {}
    if getattr(args, "exam_score", None) is not None:
        data["exam_score"] = args.exam_score
    if getattr(args, "attendance", None) is not None:
        data["attendance"] = args.attendance
    if getattr(args, "hours_studied", None) is not None:
        data["hours_studied"] = args.hours_studied
    if getattr(args, "previous_scores", None) is not None:
        data["previous_scores"] = args.previous_scores
    if getattr(args, "motivation_level", None) is not None:
        data["motivation_level"] = args.motivation_level
    if getattr(args, "internet_access", None) is not None:
        data["internet_access"] = args.internet_access
    if getattr(args, "tutoring_sessions", None) is not None:
        data["tutoring_sessions"] = args.tutoring_sessions
    if getattr(args, "sleep_hours", None) is not None:
        data["sleep_hours"] = args.sleep_hours
    if getattr(args, "gender", None) is not None:
        data["gender"] = args.gender

    res = StudentService.add_student(data, sync_csv=not getattr(args, "no_sync", False))
    if res["status"] == "success":
        print("=" * 65)
        print(f"ADD SUCCESSFUL: {res['message']}")
        print("=" * 65)
        if res.get("csv_synced"):
            print("CSV file synchronized successfully.")
        print(StudentService.format_student_card(res["record"]))
    else:
        print(f"Add failed: {res['message']}")


def cmd_delete(args) -> None:
    """Delete a student record by ID."""
    student = StudentService.get_student(args.id)
    if not student:
        print(f"Error: Student #{args.id} does not exist.")
        return

    if not getattr(args, "yes", False):
        print(StudentService.format_student_card(student))
        confirm = input(f"Are you sure you want to delete student #{args.id}? (yes/no): ").strip().lower()
        if confirm not in ["yes", "y"]:
            print("Deletion cancelled.")
            return

    res = StudentService.delete_student(args.id, sync_csv=not getattr(args, "no_sync", False))
    if res["status"] == "success":
        print("=" * 65)
        print(f"DELETE SUCCESSFUL: {res['message']}")
        print("=" * 65)
        if res.get("csv_synced"):
            print(f"CSV file synchronized. Total remaining records: {res.get('total_records')}")
    else:
        print(f"Delete failed: {res['message']}")


def cmd_sync_csv(args) -> None:
    """Export current PostgreSQL database records to CSV."""
    print("=" * 65)
    print("CSV SYNCHRONIZATION")
    print("=" * 65)
    res = StudentService.sync_db_to_csv()
    print(res["message"])


def cmd_manage(args) -> None:
    """Interactive CLI menu for user-driven student data operations."""
    print("=" * 65)
    print("STUDENT DATA MANAGEMENT & INTERACTIVE CRUD CONSOLE")
    print("=" * 65)
    print("PostgreSQL <-> CSV Automated Synchronization: ACTIVE\n")

    while True:
        print("\nOPTIONS:")
        print("  [1] View Student by ID")
        print("  [2] List / Browse Students (Paginated)")
        print("  [3] Update Student Record")
        print("  [4] Add New Student Record")
        print("  [5] Delete Student Record")
        print("  [6] Synchronize Database to CSV File")
        print("  [7] Exit")

        choice = input("\nEnter choice [1-7]: ").strip()
        if choice == "1":
            sid_str = input("Enter Student ID: ").strip()
            if not sid_str.isdigit():
                print("Error: ID must be a positive integer.")
                continue
            student = StudentService.get_student(int(sid_str))
            if not student:
                print(f"Student #{sid_str} not found.")
            else:
                print(StudentService.format_student_card(student))

        elif choice == "2":
            offset_str = input("Enter starting offset (default 0): ").strip()
            offset = int(offset_str) if offset_str.isdigit() else 0
            students = StudentService.list_students(limit=10, offset=offset)
            print(f"\nShowing records {offset + 1} to {offset + len(students)}:")
            for s in students:
                print(f"  ID #{s['id']:<5} | Score: {s['exam_score']:<5} | Att: {s['attendance']:<3}% | Study: {s['hours_studied']:<2}h | Motivation: {s['motivation_level']}")

        elif choice == "3":
            sid_str = input("Enter Student ID to update: ").strip()
            if not sid_str.isdigit():
                print("Error: ID must be a positive integer.")
                continue
            sid = int(sid_str)
            student = StudentService.get_student(sid)
            if not student:
                print(f"Student #{sid} not found.")
                continue

            print("\nCurrent Record:")
            print(StudentService.format_student_card(student))
            print("\nAvailable fields to update:")
            print("  exam_score, attendance, hours_studied, previous_scores,")
            print("  motivation_level, internet_access, tutoring_sessions, sleep_hours,")
            print("  parental_involvement, access_to_resources, family_income, teacher_quality,")
            print("  school_type, peer_influence, physical_activity, learning_disabilities,")
            print("  parental_education_level, distance_from_home, gender")

            field = input("\nEnter field name to update: ").strip().lower()
            if field not in FIELD_DEFINITIONS:
                print(f"Invalid field '{field}'.")
                continue
            spec = FIELD_DEFINITIONS[field]
            prompt_extra = f" (Options: {spec.get('options')})" if "options" in spec else f" (Range: {spec.get('min')}-{spec.get('max')})"
            new_val = input(f"Enter new value for {field}{prompt_extra}: ").strip()

            res = StudentService.update_student(sid, {field: new_val}, sync_csv=True)
            if res["status"] == "success":
                print(f"\nSUCCESS: {res['message']}")
                if res.get("csv_synced"):
                    print("CSV file (data/StudentPerformanceFactors.csv) updated automatically.")
                print(StudentService.format_student_card(res["record"]))
            else:
                print(f"\nERROR: {res['message']}")

        elif choice == "4":
            print("\nEnter new student details (press ENTER to accept default):")
            record_data = {}
            for field, spec in FIELD_DEFINITIONS.items():
                prompt = f"  {spec['label']} [default: {spec['default']}]: "
                val = input(prompt).strip()
                if val:
                    record_data[field] = val
            res = StudentService.add_student(record_data, sync_csv=True)
            if res["status"] == "success":
                print(f"\nSUCCESS: {res['message']}")
                if res.get("csv_synced"):
                    print("CSV file updated automatically.")
                print(StudentService.format_student_card(res["record"]))
            else:
                print(f"\nERROR: {res['message']}")

        elif choice == "5":
            sid_str = input("Enter Student ID to delete: ").strip()
            if not sid_str.isdigit():
                print("Error: ID must be a positive integer.")
                continue
            sid = int(sid_str)
            student = StudentService.get_student(sid)
            if not student:
                print(f"Student #{sid} not found.")
                continue
            print(StudentService.format_student_card(student))
            confirm = input(f"Are you sure you want to PERMANENTLY delete student #{sid}? (yes/no): ").strip().lower()
            if confirm in ["yes", "y"]:
                res = StudentService.delete_student(sid, sync_csv=True)
                print(f"\n{res['message']}")
                if res.get("csv_synced"):
                    print(f"CSV synchronized. Remaining records: {res.get('total_records')}")
            else:
                print("Deletion cancelled.")

        elif choice == "6":
            res = StudentService.sync_db_to_csv()
            print(f"\n{res['message']}")

        elif choice in ["7", "exit", "quit", "q"]:
            print("Exiting interactive management console. Goodbye!")
            break
        else:
            print("Invalid option. Please choose 1-7.")


def main():
    parser = argparse.ArgumentParser(
        description="Student Performance EDA & OLAP Analytics (VS Code + PostgreSQL)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Ingest
    p_ingest = subparsers.add_parser("ingest", help="Sync dataset into PostgreSQL")
    p_ingest.add_argument("--force", action="store_true", help="Force overwrite existing table")

    # EDA
    p_eda = subparsers.add_parser("eda", help="Run descriptive statistics, missing value analysis, and correlations")

    # Stats
    p_stats = subparsers.add_parser("stats", help="Run hypothesis tests (Z-test, T-test, Chi-square)")
    p_stats.add_argument("--alpha", type=float, default=0.05, help="Significance level")
    p_stats.add_argument("--mu", type=float, default=65.0, help="Hypothesized mean")
    p_stats.add_argument("--pop-std", type=float, default=10.0, help="Assumed population std")
    p_stats.add_argument("--no-persist", action="store_true", help="Do not save to database")

    # OLAP
    p_olap = subparsers.add_parser("olap", help="Run slicing, dicing, pivot, and aggregations")
    p_olap.add_argument("--pushdown", action="store_true", help="Push execution down to PostgreSQL")

    # Benchmark
    p_bench = subparsers.add_parser("benchmark", help="Run performance benchmarks")
    p_bench.add_argument("--iterations", type=int, default=10, help="Profiling iterations")

    # Run All
    p_all = subparsers.add_parser("all", help="Run complete pipeline end-to-end")
    p_all.add_argument("--force", action="store_true", help="Force overwrite existing DB data")

    # Interactive Management Console
    subparsers.add_parser("manage", help="Interactive terminal prompt to search, view, update, add, delete records")

    # View
    p_view = subparsers.add_parser("view", help="View student by ID or list students")
    p_view.add_argument("--id", type=int, help="Student ID to view")
    p_view.add_argument("--limit", type=int, default=10, help="Pagination limit")
    p_view.add_argument("--offset", type=int, default=0, help="Pagination offset")

    # Update
    p_upd = subparsers.add_parser("update", help="Update fields for a student record")
    p_upd.add_argument("--id", type=int, required=True, help="Student ID to update")
    p_upd.add_argument("--exam-score", type=float, help="Updated exam score")
    p_upd.add_argument("--attendance", type=int, help="Updated attendance percentage")
    p_upd.add_argument("--hours-studied", type=int, help="Updated study hours")
    p_upd.add_argument("--previous-scores", type=int, help="Updated previous scores")
    p_upd.add_argument("--motivation-level", type=str, help="Updated motivation level (Low/Medium/High)")
    p_upd.add_argument("--internet-access", type=str, help="Updated internet access (Yes/No)")
    p_upd.add_argument("--tutoring-sessions", type=int, help="Updated tutoring sessions")
    p_upd.add_argument("--sleep-hours", type=int, help="Updated sleep hours")
    p_upd.add_argument("--no-sync", action="store_true", help="Do not sync update to CSV file")

    # Add
    p_add = subparsers.add_parser("add", help="Add a new student record")
    p_add.add_argument("--exam-score", type=float, default=70.0, help="Exam score")
    p_add.add_argument("--attendance", type=int, default=80, help="Attendance percentage")
    p_add.add_argument("--hours-studied", type=int, default=20, help="Study hours")
    p_add.add_argument("--previous-scores", type=int, default=75, help="Previous scores")
    p_add.add_argument("--motivation-level", type=str, default="Medium", help="Motivation level")
    p_add.add_argument("--internet-access", type=str, default="Yes", help="Internet access")
    p_add.add_argument("--tutoring-sessions", type=int, default=1, help="Tutoring sessions")
    p_add.add_argument("--sleep-hours", type=int, default=7, help="Sleep hours")
    p_add.add_argument("--gender", type=str, default="Female", help="Gender")
    p_add.add_argument("--no-sync", action="store_true", help="Do not sync addition to CSV file")

    # Delete
    p_del = subparsers.add_parser("delete", help="Delete a student record by ID")
    p_del.add_argument("--id", type=int, required=True, help="Student ID to delete")
    p_del.add_argument("--yes", "-y", action="store_true", help="Bypass confirmation prompt")
    p_del.add_argument("--no-sync", action="store_true", help="Do not sync deletion to CSV file")

    # Sync CSV
    subparsers.add_parser("sync-csv", help="Synchronize PostgreSQL database table to CSV")

    args = parser.parse_args()

    if args.command == "ingest":
        cmd_ingest(args)
    elif args.command == "eda":
        cmd_eda(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "olap":
        cmd_olap(args)
    elif args.command == "benchmark":
        cmd_benchmark(args)
    elif args.command == "all":
        cmd_run_all(args)
    elif args.command == "manage":
        cmd_manage(args)
    elif args.command == "view":
        cmd_view(args)
    elif args.command == "update":
        cmd_update(args)
    elif args.command == "add":
        cmd_add(args)
    elif args.command == "delete":
        cmd_delete(args)
    elif args.command == "sync-csv":
        cmd_sync_csv(args)
    else:
        # Default action when run with no arguments: run end-to-end pipeline
        args.force = False
        cmd_run_all(args)


if __name__ == "__main__":
    main()

