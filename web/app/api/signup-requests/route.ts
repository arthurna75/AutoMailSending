import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { sendSignupRequestNotification } from "@/lib/mailer";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "요청 본문이 올바르지 않습니다." }, { status: 400 });
  }

  const rawEmail = (body as { email?: unknown } | null)?.email;
  if (typeof rawEmail !== "string" || !EMAIL_RE.test(rawEmail.trim())) {
    return NextResponse.json({ error: "이메일을 확인해주세요." }, { status: 400 });
  }
  const email = rawEmail.trim().toLowerCase();

  const supabase = createClient();
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: { shouldCreateUser: false },
  });

  if (!error) {
    return NextResponse.json({ outcome: "otp_sent" });
  }

  // shouldCreateUser:false로 인해 계정이 없어서 나는 에러로 판단되면 신규 신청으로 접수한다.
  // "Allow new users to sign up"이 꺼져 있으면 GoTrue가 400 대신 signup_disabled 코드로
  // "Signups not allowed for otp"를 돌려주는데, 이 프로젝트는 그 설정을 의도적으로 꺼두므로
  // 신규 이메일은 사실상 항상 이 경로로 들어온다.
  if (error.status === 400 || error.code === "signup_disabled") {
    const admin = createAdminClient();
    const { data: existing } = await admin
      .from("signup_requests")
      .select("id, status")
      .eq("email", email)
      .maybeSingle();

    if (!existing) {
      await admin.from("signup_requests").insert({ email });
      await sendSignupRequestNotification(email);
    } else if (existing.status === "rejected") {
      await admin
        .from("signup_requests")
        .update({ status: "pending", requested_at: new Date().toISOString(), reviewed_at: null })
        .eq("id", existing.id);
      await sendSignupRequestNotification(email);
    }
    // pending/approved면 이미 접수/승인된 상태이므로 별도 처리(알림 포함) 없이 동일한 응답을 준다.

    return NextResponse.json({ outcome: "request_pending" });
  }

  return NextResponse.json({ error: error.message }, { status: error.status ?? 500 });
}
