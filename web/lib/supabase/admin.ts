import { createClient } from "@supabase/supabase-js";

// service_role 키 전용 클라이언트 — "use client" 파일에서 import하지 말 것.
// Route Handler(서버)에서만 사용: RLS를 우회해 signup_requests 조회/기록, auth.admin.createUser 호출용.
export function createAdminClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } }
  );
}
