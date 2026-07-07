import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

const GITHUB_REPO = "arthurna75/AutoMailSending";
const GITHUB_REF = "master";

export async function POST(request: Request) {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "로그인이 필요합니다." }, { status: 401 });
  }

  let settings: unknown;
  try {
    settings = await request.json();
  } catch {
    return NextResponse.json({ error: "요청 본문이 올바르지 않습니다." }, { status: 400 });
  }
  const keywords = (settings as { keywords?: unknown } | null)?.keywords;
  if (!Array.isArray(keywords) || keywords.length === 0) {
    return NextResponse.json({ error: "키워드를 먼저 입력해주세요." }, { status: 400 });
  }

  const token = process.env.GITHUB_DISPATCH_TOKEN;
  if (!token) {
    return NextResponse.json(
      { error: "서버에 GITHUB_DISPATCH_TOKEN이 설정되어 있지 않습니다." },
      { status: 500 }
    );
  }

  const response = await fetch(
    `https://api.github.com/repos/${GITHUB_REPO}/actions/workflows/worker.yml/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ref: GITHUB_REF,
        inputs: {
          user_id: user.id,
          test_send: "true",
          settings_json: JSON.stringify(settings),
        },
      }),
    }
  );

  if (!response.ok) {
    const detail = await response.text();
    return NextResponse.json(
      { error: `GitHub 워크플로우 트리거 실패 (status=${response.status}): ${detail}` },
      { status: 502 }
    );
  }

  return NextResponse.json({ status: "queued" });
}
