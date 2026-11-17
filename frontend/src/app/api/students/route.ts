import { NextRequest, NextResponse } from "next/server";
import { queryDb } from "@/lib/db";

// GET: Paginated list or search
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const limit = Math.min(parseInt(searchParams.get("limit") || "15", 10), 100);
    const offset = Math.max(parseInt(searchParams.get("offset") || "0", 10), 0);
    const search = searchParams.get("search")?.trim() || "";

    let query = "SELECT * FROM students";
    const params: any[] = [];

    if (search) {
      if (/^\d+$/.test(search)) {
        query += " WHERE id = $1";
        params.push(parseInt(search, 10));
      } else {
        query += " WHERE school_type ILIKE $1 OR parental_involvement ILIKE $1";
        params.push(`%${search}%`);
      }
    }

    query += ` ORDER BY id ASC LIMIT $${params.length + 1} OFFSET $${params.length + 2};`;
    params.push(limit, offset);

    const rows = await queryDb(query, params);
    const countQuery = "SELECT COUNT(*)::int as total FROM students;";
    const totalCount = (await queryDb(countQuery))[0]?.total || 0;

    return NextResponse.json({ success: true, students: rows, total: totalCount, limit, offset });
  } catch (error: any) {
    console.error("Students GET error:", error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}

// POST: Add new student
export async function POST(req: NextRequest) {
  try {
    const data = await req.json();

    const query = `
      INSERT INTO students (
        hours_studied, attendance, parental_involvement, access_to_resources,
        extracurricular_activities, sleep_hours, previous_scores, motivation_level,
        internet_access, tutoring_sessions, family_income, teacher_quality,
        school_type, peer_influence, physical_activity, learning_disabilities,
        parental_education_level, distance_from_home, gender, exam_score
      ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
        $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
      ) RETURNING id;
    `;

    const values = [
      parseInt(data.hours_studied ?? 20, 10),
      parseInt(data.attendance ?? 80, 10),
      data.parental_involvement || "Medium",
      data.access_to_resources || "Medium",
      data.extracurricular_activities || "No",
      parseInt(data.sleep_hours ?? 7, 10),
      parseInt(data.previous_scores ?? 75, 10),
      data.motivation_level || "Medium",
      data.internet_access || "Yes",
      parseInt(data.tutoring_sessions ?? 1, 10),
      data.family_income || "Medium",
      data.teacher_quality || "Medium",
      data.school_type || "Public",
      data.peer_influence || "Neutral",
      parseInt(data.physical_activity ?? 3, 10),
      data.learning_disabilities || "No",
      data.parental_education_level || "College",
      data.distance_from_home || "Near",
      data.gender || "Female",
      parseFloat(data.exam_score ?? 70.0),
    ];

    const result = await queryDb(query, values);
    const newId = result[0]?.id;

    return NextResponse.json({ success: true, message: `Student #${newId} registered successfully`, id: newId });
  } catch (error: any) {
    console.error("Students POST error:", error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}

// PUT: Update student record
export async function PUT(req: NextRequest) {
  try {
    const data = await req.json();
    const id = parseInt(data.id, 10);
    if (!id) {
      return NextResponse.json({ success: false, error: "Missing student ID" }, { status: 400 });
    }

    const query = `
      UPDATE students SET
        hours_studied = $1,
        attendance = $2,
        previous_scores = $3,
        tutoring_sessions = $4,
        exam_score = $5
      WHERE id = $6 RETURNING *;
    `;

    const values = [
      parseInt(data.hours_studied, 10),
      parseInt(data.attendance, 10),
      parseInt(data.previous_scores, 10),
      parseInt(data.tutoring_sessions, 10),
      parseFloat(data.exam_score),
      id,
    ];

    const updated = await queryDb(query, values);
    if (!updated.length) {
      return NextResponse.json({ success: false, error: `Student #${id} not found` }, { status: 404 });
    }

    return NextResponse.json({ success: true, message: `Student #${id} updated successfully`, record: updated[0] });
  } catch (error: any) {
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}

// DELETE: Delete student record
export async function DELETE(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const id = parseInt(searchParams.get("id") || "", 10);
    if (!id) {
      return NextResponse.json({ success: false, error: "Invalid student ID" }, { status: 400 });
    }

    const deleted = await queryDb("DELETE FROM students WHERE id = $1 RETURNING id;", [id]);
    if (!deleted.length) {
      return NextResponse.json({ success: false, error: `Student #${id} not found` }, { status: 404 });
    }

    return NextResponse.json({ success: true, message: `Student #${id} deleted successfully`, id });
  } catch (error: any) {
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
