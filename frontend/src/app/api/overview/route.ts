import { NextResponse } from "next/server";
import { queryDb } from "@/lib/db";

export async function GET() {
  try {
    // 1. Core KPIs - 100% computed from PostgreSQL
    const kpiQuery = `
      SELECT 
        COUNT(*)::int AS total_students,
        ROUND(AVG(exam_score)::numeric, 2) AS mean_score,
        ROUND(AVG(attendance)::numeric, 1) AS mean_attendance,
        ROUND(AVG(hours_studied)::numeric, 1) AS mean_hours,
        COUNT(CASE WHEN exam_score >= 65 THEN 1 END)::int AS pass_count,
        ROUND((COUNT(CASE WHEN exam_score >= 65 THEN 1 END)::numeric / NULLIF(COUNT(*), 0) * 100), 1) AS pass_rate,
        COUNT(CASE WHEN exam_score < 60 THEN 1 END)::int AS at_risk_count,
        ROUND((COUNT(CASE WHEN exam_score < 60 THEN 1 END)::numeric / NULLIF(COUNT(*), 0) * 100), 1) AS at_risk_pct,
        ROUND(STDDEV_SAMP(exam_score)::numeric, 2) AS std_score,
        MIN(exam_score) AS min_score,
        MAX(exam_score) AS max_score
      FROM students;
    `;
    const kpiRows = await queryDb(kpiQuery);
    const kpis = kpiRows[0];

    // 2. Score Distribution (Histogram Buckets) - live query
    const histQuery = `
      SELECT 
        bucket,
        COUNT(*)::int as count
      FROM (
        SELECT 
          CASE 
            WHEN exam_score < 55 THEN '45-54'
            WHEN exam_score < 60 THEN '55-59'
            WHEN exam_score < 65 THEN '60-64'
            WHEN exam_score < 70 THEN '65-69'
            WHEN exam_score < 75 THEN '70-74'
            WHEN exam_score < 80 THEN '75-79'
            ELSE '80-100'
          END AS bucket,
          CASE 
            WHEN exam_score < 55 THEN 1
            WHEN exam_score < 60 THEN 2
            WHEN exam_score < 65 THEN 3
            WHEN exam_score < 70 THEN 4
            WHEN exam_score < 75 THEN 5
            WHEN exam_score < 80 THEN 6
            ELSE 7
          END AS sort_order
        FROM students
      ) b
      GROUP BY bucket, sort_order
      ORDER BY sort_order;
    `;
    const distribution = await queryDb(histQuery);

    // 3. Live Pearson Correlations dynamically computed by PostgreSQL
    const corrQuery = `
      SELECT 
        ROUND(CORR(exam_score, attendance)::numeric, 4) AS attendance,
        ROUND(CORR(exam_score, hours_studied)::numeric, 4) AS hours_studied,
        ROUND(CORR(exam_score, previous_scores)::numeric, 4) AS previous_scores,
        ROUND(CORR(exam_score, tutoring_sessions)::numeric, 4) AS tutoring_sessions,
        ROUND(CORR(exam_score, physical_activity)::numeric, 4) AS physical_activity,
        ROUND(CORR(exam_score, sleep_hours)::numeric, 4) AS sleep_hours
      FROM students;
    `;
    const corrRow = (await queryDb(corrQuery))[0];
    const correlations = [
      { factor: "Attendance Percentage", r: parseFloat(corrRow.attendance || 0), impact: "Primary Success Driver" },
      { factor: "Hours Studied / Wk", r: parseFloat(corrRow.hours_studied || 0), impact: "Strong Positive Driver" },
      { factor: "Previous Exam Scores", r: parseFloat(corrRow.previous_scores || 0), impact: "Moderate Correlation" },
      { factor: "Tutoring Sessions", r: parseFloat(corrRow.tutoring_sessions || 0), impact: "Positive Correlation" },
      { factor: "Physical Activity", r: parseFloat(corrRow.physical_activity || 0), impact: "Low Correlation" },
      { factor: "Sleep Hours", r: parseFloat(corrRow.sleep_hours || 0), impact: "Neutral / Invariant" },
    ].sort((a, b) => b.r - a.r);

    // 4. Performance by School Type
    const schoolQuery = `
      SELECT 
        school_type,
        COUNT(*)::int AS count,
        ROUND(AVG(exam_score)::numeric, 2) AS mean_score,
        ROUND(AVG(attendance)::numeric, 1) AS mean_attendance
      FROM students
      GROUP BY school_type
      ORDER BY school_type;
    `;
    const bySchool = await queryDb(schoolQuery);

    // 5. Performance by Motivation Level
    const motivationQuery = `
      SELECT 
        motivation_level,
        COUNT(*)::int AS count,
        ROUND(AVG(exam_score)::numeric, 2) AS mean_score
      FROM students
      GROUP BY motivation_level
      ORDER BY mean_score DESC;
    `;
    const byMotivation = await queryDb(motivationQuery);

    return NextResponse.json({
      success: true,
      data: {
        kpis,
        distribution,
        correlations,
        bySchool,
        byMotivation,
      },
    });
  } catch (error: any) {
    console.error("Overview API error:", error);
    return NextResponse.json(
      { success: false, error: error.message || "Failed to fetch overview metrics" },
      { status: 500 }
    );
  }
}
