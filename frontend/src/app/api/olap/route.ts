import { NextRequest, NextResponse } from "next/server";
import { queryDb } from "@/lib/db";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { action } = body;

    if (action === "slice") {
      const limit = Math.min(Math.max(parseInt(body.limit || 10, 10), 1), 100);
      const offset = Math.max(parseInt(body.offset || 0, 10), 0);
      const query = `
        SELECT 
          id, hours_studied, attendance, parental_involvement, 
          access_to_resources, extracurricular_activities, exam_score
        FROM students
        ORDER BY id ASC
        LIMIT $1 OFFSET $2;
      `;
      const rows = await queryDb(query, [limit, offset]);
      return NextResponse.json({ success: true, action: "slice", data: rows, count: rows.length });
    }

    if (action === "dice") {
      const minScore = parseFloat(body.minScore || 70.0);
      const minAttendance = parseInt(body.minAttendance || 80, 10);
      const minHours = parseInt(body.minHours || 15, 10);

      const query = `
        SELECT 
          id, hours_studied, attendance, parental_involvement, 
          access_to_resources, motivation_level, school_type, exam_score
        FROM students
        WHERE exam_score > $1 AND attendance > $2 AND hours_studied >= $3
        ORDER BY exam_score DESC
        LIMIT 100;
      `;
      const countQuery = `
        SELECT 
          COUNT(*)::int as total_diced,
          ROUND(AVG(exam_score)::numeric, 2) as mean_score,
          ROUND(AVG(attendance)::numeric, 1) as mean_attendance
        FROM students
        WHERE exam_score > $1 AND attendance > $2 AND hours_studied >= $3;
      `;

      const [rows, summary] = await Promise.all([
        queryDb(query, [minScore, minAttendance, minHours]),
        queryDb(countQuery, [minScore, minAttendance, minHours]),
      ]);

      return NextResponse.json({
        success: true,
        action: "dice",
        data: rows,
        summary: summary[0],
      });
    }

    if (action === "pivot") {
      // Safe allowed column list to prevent SQL injection
      const allowedCols = [
        "internet_access", "school_type", "parental_involvement",
        "family_income", "motivation_level", "access_to_resources",
        "teacher_quality", "peer_influence", "gender"
      ];

      const rowDim = allowedCols.includes(body.rowDim) ? body.rowDim : "internet_access";
      const colDim = allowedCols.includes(body.colDim) ? body.colDim : "motivation_level";
      const metric = body.metric === "attendance" ? "attendance" : "exam_score";

      const query = `
        SELECT 
          ${rowDim} AS row_val,
          ${colDim} AS col_val,
          ROUND(AVG(${metric})::numeric, 2) AS mean_value,
          COUNT(*)::int AS count
        FROM students
        WHERE ${rowDim} IS NOT NULL AND ${colDim} IS NOT NULL
        GROUP BY ${rowDim}, ${colDim}
        ORDER BY ${rowDim}, ${colDim};
      `;

      const rows = await queryDb(query);
      return NextResponse.json({ success: true, action: "pivot", data: rows, rowDim, colDim, metric });
    }

    return NextResponse.json({ success: false, error: "Invalid OLAP action" }, { status: 400 });
  } catch (error: any) {
    console.error("OLAP API error:", error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
