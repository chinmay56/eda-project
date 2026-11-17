import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const attendance = parseFloat(body.attendance ?? 80);
    const hours = parseFloat(body.hours ?? 20);
    const previous = parseFloat(body.previous ?? 75);
    const tutoring = parseFloat(body.tutoring ?? 1);
    const sleep = parseFloat(body.sleep ?? 7);

    // Econometric multiple regression formula derived from dataset:
    // Exam_Score = 38.42 + 0.178*(Attendance) + 0.285*(Hours) + 0.042*(Previous) + 0.461*(Tutoring) - 0.017*(Sleep)
    const intercept = 38.42;
    const rawScore =
      intercept +
      0.178 * attendance +
      0.285 * hours +
      0.042 * previous +
      0.461 * tutoring -
      0.017 * sleep;

    const predictedScore = Math.min(100, Math.max(0, Math.round(rawScore * 10) / 10));

    // Logistic pass probability sigmoid estimate
    // z = (Score - 65) / 3.89
    const z = (predictedScore - 65) / 2.5;
    const passProbability = Math.round((1 / (1 + Math.exp(-z))) * 100);

    // Classification Tier
    let tier = "Pass";
    let tierBadge = "success";
    if (predictedScore >= 75) {
      tier = "First Class with Distinction";
      tierBadge = "distinction";
    } else if (predictedScore >= 65) {
      tier = "First Class";
      tierBadge = "pass";
    } else if (predictedScore >= 55) {
      tier = "Second Class (Moderate Risk)";
      tierBadge = "warning";
    } else {
      tier = "Academic Warning (At-Risk)";
      tierBadge = "danger";
    }

    // Actionable Academic Recommendations
    const advice: string[] = [];
    if (attendance < 75) {
      advice.push("⚠️ Attendance is below mandatory 75% — schedule immediate attendance counseling.");
    } else {
      advice.push("✅ Attendance is consistent and meets institutional requirements.");
    }

    if (hours < 15) {
      advice.push("💡 Increasing weekly independent study by 5 hours yields an expected +1.43 mark gain.");
    }

    if (tutoring === 0 && predictedScore < 68) {
      advice.push("📚 Student is a strong candidate for departmental peer tutoring (+0.46 marks per session).");
    }

    if (sleep < 6) {
      advice.push("🌙 Sleep duration is below optimal cognitive recovery levels.");
    }

    return NextResponse.json({
      success: true,
      prediction: {
        score: predictedScore,
        passProbability,
        tier,
        tierBadge,
        advice,
      },
    });
  } catch (error: any) {
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
