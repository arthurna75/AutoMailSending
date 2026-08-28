import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

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
  if (error.status === 400) {
    const admin = createAdminClient();
    const { data: existing } = await admin
      .from("signup_requests")
      .select("id, status")
      .eq("email", email)
      .maybeSingle();

    if (!existing) {
      await admin.from("signup_requests").insert({ email });
    } else if (existing.status === "rejected") {
      await admin
        .from("signup_requests")
        .update({ status: "pending", requested_at: new Date().toISOString(), reviewed_at: null })
        .eq("id", existing.id);
    }
    // pending/approved면 이미 접수/승인된 상태이므로 별도 처리 없이 동일한 응답을 준다.

    return NextResponse.json({ outcome: "request_pending" });
  }

  return NextResponse.json({ error: error.message }, { status: error.status ?? 500 });
}
