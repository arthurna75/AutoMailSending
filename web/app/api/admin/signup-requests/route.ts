import { NextResponse } from "next/server";
import { createClient as createSupabaseClient } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isAdminEmail } from "@/lib/admin";

async function requireAdmin() {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return { error: NextResponse.json({ error: "로그인이 필요합니다." }, { status: 401 }) };
  }
  if (!isAdminEmail(user.email)) {
    return { error: NextResponse.json({ error: "권한이 없습니다." }, { status: 403 }) };
  }
  return { user };
}

export async function GET() {
  const guard = await requireAdmin();
  if (guard.error) return guard.error;

  const admin = createAdminClient();
  const { data, error } = await admin
    .from("signup_requests")
    .select("id, email, status, requested_at, reviewed_at")
    .order("requested_at", { ascending: false })
    .limit(200);

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
  return NextResponse.json({ requests: data });
}

export async function POST(request: Request) {
  const guard = await requireAdmin();
  if (guard.error) return guard.error;

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "요청 본문이 올바르지 않습니다." }, { status: 400 });
  }

  const id = (body as { id?: unknown } | null)?.id;
  const action = (body as { action?: unknown } | null)?.action;
  if (typeof id !== "number" || (action !== "approve" && action !== "reject")) {
    return NextResponse.json({ error: "요청 값이 올바르지 않습니다." }, { status: 400 });
  }

  const admin = createAdminClient();
  const { data: row, error: fetchError } = await admin
    .from("signup_requests")
    .select("id, email, status")
    .eq("id", id)
    .maybeSingle();

  if (fetchError) {
    return NextResponse.json({ error: fetchError.message }, { status: 500 });
  }
  if (!row) {
    return NextResponse.json({ error: "요청을 찾을 수 없습니다." }, { status: 404 });
  }
  if (row.status !== "pending") {
    return NextResponse.json({ error: "이미 처리된 요청입니다." }, { status: 409 });
  }

  if (action === "reject") {
    await admin
      .from("signup_requests")
      .update({ status: "rejected", reviewed_at: new Date().toISOString() })
      .eq("id", id);
    return NextResponse.json({ ok: true, status: "rejected" });
  }

  const { error: createError } = await admin.auth.admin.createUser({
    email: row.email,
    email_confirm: true,
  });
  if (createError && !/already registered|already exists/i.test(createError.message)) {
    return NextResponse.json({ error: createError.message }, { status: 500 });
  }

  const anon = createSupabaseClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
  const { error: otpError } = await anon.auth.signInWithOtp({ email: row.email });
  if (otpError) {
    return NextResponse.json({ error: otpError.message }, { status: 500 });
  }

  await admin
    .from("signup_requests")
    .update({ status: "approved", reviewed_at: new Date().toISOString() })
    .eq("id", id);

  return NextResponse.json({ ok: true, status: "approved" });
}
