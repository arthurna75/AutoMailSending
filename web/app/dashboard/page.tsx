"use client";

import { useEffect, useState, type KeyboardEvent } from "react";
import { createClient } from "@/lib/supabase/client";

type Settings = {
  keywords: string[];
  per_keyword_count: number;
  total_count: number;
  source_naver_enabled: boolean;
  source_google_enabled: boolean;
  crawl_enabled: boolean;
  llm_summary_enabled: boolean;
  to_email: string | null;
  subject_template: string;
  timezone: string;
  send_time: string;
  is_active: boolean;
};

const DEFAULT_SETTINGS: Settings = {
  keywords: [],
  per_keyword_count: 5,
  total_count: 20,
  source_naver_enabled: true,
  source_google_enabled: false,
  crawl_enabled: true,
  llm_summary_enabled: true,
  to_email: null,
  subject_template: "[주요뉴스] {date} 아침 다이제스트",
  timezone: "Asia/Seoul",
  send_time: "07:00",
  is_active: true,
};

type Status = "loading" | "ready" | "saving" | "saved" | "error";
type TestSendStatus = "idle" | "sending" | "sent" | "error";

export default function DashboardPage() {
  const supabase = createClient();
  const [userId, setUserId] = useState<string | null>(null);
  const [accountEmail, setAccountEmail] = useState("");
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [keywordInput, setKeywordInput] = useState("");
  const [status, setStatus] = useState<Status>("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const [testSendStatus, setTestSendStatus] = useState<TestSendStatus>("idle");
  const [testSendMessage, setTestSendMessage] = useState("");

  useEffect(() => {
    (async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;
      setUserId(user.id);
      setAccountEmail(user.email ?? "");

      const { data } = await supabase
        .from("user_settings")
        .select("*")
        .eq("user_id", user.id)
        .maybeSingle();
      if (data) {
        const merged = { ...DEFAULT_SETTINGS, ...data };
        if (merged.source_naver_enabled && merged.source_google_enabled) {
          merged.source_google_enabled = false;
        }
        setSettings(merged);
      }
      setStatus("ready");
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function addKeyword() {
    const value = keywordInput.trim();
    if (!value || settings.keywords.includes(value)) return;
    setSettings({ ...settings, keywords: [...settings.keywords, value] });
    setKeywordInput("");
  }

  function handleKeywordKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      addKeyword();
    }
  }

  function removeKeyword(keyword: string) {
    setSettings({ ...settings, keywords: settings.keywords.filter((k) => k !== keyword) });
  }

  async function handleSave() {
    if (!userId) return;
    if (settings.keywords.length === 0) {
      setErrorMessage("키워드를 최소 1개 이상 입력해주세요.");
      setStatus("error");
      return;
    }
    setStatus("saving");
    const { error } = await supabase
      .from("user_settings")
      .upsert({ user_id: userId, ...settings }, { onConflict: "user_id" });
    if (error) {
      setErrorMessage(error.message);
      setStatus("error");
    } else {
      setStatus("saved");
    }
  }

  async function handleTestSend() {
    if (settings.keywords.length === 0) {
      setTestSendMessage("키워드를 먼저 입력해주세요.");
      setTestSendStatus("error");
      return;
    }
    setTestSendStatus("sending");
    try {
      const response = await fetch("/api/test-send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      const data = await response.json();
      if (!response.ok) {
        setTestSendMessage(data.error ?? "요청에 실패했습니다.");
        setTestSendStatus("error");
        return;
      }
      setTestSendMessage("요청했습니다. 1~2분 후 메일함을 확인해주세요.");
      setTestSendStatus("sent");
    } catch {
      setTestSendMessage("요청 중 오류가 발생했습니다.");
      setTestSendStatus("error");
    }
  }

  async function handleLogout() {
    await supabase.auth.signOut();
    window.location.href = "/login";
  }

  if (status === "loading") return <p style={{ padding: 24 }}>불러오는 중...</p>;

  return (
    <main style={{ maxWidth: 560, margin: "40px auto", fontFamily: "sans-serif", padding: "0 16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <h1>내 뉴스 다이제스트 설정</h1>
        <button onClick={handleLogout}>로그아웃</button>
      </div>

      <section style={{ marginTop: 24 }}>
        <h2>키워드</h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <input
            value={keywordInput}
            onChange={(event) => setKeywordInput(event.target.value)}
            onKeyDown={handleKeywordKeyDown}
            placeholder="키워드 입력 후 Enter"
            style={{ flex: 1, padding: 8 }}
          />
          <button onClick={addKeyword}>추가</button>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {settings.keywords.map((keyword) => (
            <span key={keyword} style={{ background: "#eee", padding: "4px 8px", borderRadius: 4 }}>
              {keyword}{" "}
              <button onClick={() => removeKeyword(keyword)} style={{ marginLeft: 4 }}>
                ×
              </button>
            </span>
          ))}
        </div>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>기사 개수</h2>
        <label>
          키워드당 최대{" "}
          <input
            type="number"
            min={1}
            max={20}
            value={settings.per_keyword_count}
            onChange={(event) =>
              setSettings({ ...settings, per_keyword_count: Number(event.target.value) })
            }
            style={{ width: 60 }}
          />
          건
        </label>
        <br />
        <label>
          전체 최대{" "}
          <input
            type="number"
            min={1}
            max={50}
            value={settings.total_count}
            onChange={(event) => setSettings({ ...settings, total_count: Number(event.target.value) })}
            style={{ width: 60 }}
          />
          건
        </label>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>소스 / 요약</h2>
        <label style={{ display: "block" }}>
          <input
            type="radio"
            name="news_source"
            checked={settings.source_naver_enabled}
            onChange={() =>
              setSettings({ ...settings, source_naver_enabled: true, source_google_enabled: false })
            }
          />{" "}
          네이버 뉴스 검색
        </label>
        <label style={{ display: "block" }}>
          <input
            type="radio"
            name="news_source"
            checked={!settings.source_naver_enabled && settings.source_google_enabled}
            onChange={() =>
              setSettings({ ...settings, source_naver_enabled: false, source_google_enabled: true })
            }
          />{" "}
          구글 뉴스 RSS
        </label>
        <label style={{ display: "block" }}>
          <input
            type="checkbox"
            checked={settings.crawl_enabled}
            onChange={(event) => setSettings({ ...settings, crawl_enabled: event.target.checked })}
          />{" "}
          본문 크롤링으로 보강
        </label>
        <label style={{ display: "block" }}>
          <input
            type="checkbox"
            checked={settings.llm_summary_enabled}
            onChange={(event) =>
              setSettings({ ...settings, llm_summary_enabled: event.target.checked })
            }
          />{" "}
          AI 요약 사용
        </label>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>발송 시각</h2>
        <label>
          시각{" "}
          <input
            type="time"
            value={settings.send_time?.slice(0, 5)}
            onChange={(event) => setSettings({ ...settings, send_time: event.target.value })}
          />
        </label>
        <br />
        <label>
          타임존{" "}
          <select
            value={settings.timezone}
            onChange={(event) => setSettings({ ...settings, timezone: event.target.value })}
          >
            <option value="Asia/Seoul">Asia/Seoul (KST)</option>
            <option value="America/Los_Angeles">America/Los_Angeles (PST/PDT)</option>
            <option value="America/New_York">America/New_York (EST/EDT)</option>
            <option value="UTC">UTC</option>
          </select>
        </label>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>수신 / 제목</h2>
        <label style={{ display: "block" }}>
          수신 이메일 (비워두면 로그인 계정 이메일: {accountEmail})
          <input
            value={settings.to_email ?? ""}
            onChange={(event) =>
              setSettings({ ...settings, to_email: event.target.value || null })
            }
            style={{ width: "100%", padding: 8 }}
          />
        </label>
        <label style={{ display: "block", marginTop: 8 }}>
          제목 템플릿 ({"{date}"}가 날짜로 치환됩니다)
          <input
            value={settings.subject_template}
            onChange={(event) => setSettings({ ...settings, subject_template: event.target.value })}
            style={{ width: "100%", padding: 8 }}
          />
        </label>
        <label style={{ display: "block", marginTop: 8 }}>
          <input
            type="checkbox"
            checked={settings.is_active}
            onChange={(event) => setSettings({ ...settings, is_active: event.target.checked })}
          />{" "}
          다이제스트 활성화
        </label>
      </section>

      <div style={{ marginTop: 24, display: "flex", gap: 8 }}>
        <button onClick={handleSave} disabled={status === "saving"} style={{ padding: "8px 16px" }}>
          {status === "saving" ? "저장 중..." : "저장"}
        </button>
        <button
          onClick={handleTestSend}
          disabled={testSendStatus === "sending" || settings.keywords.length === 0}
          style={{ padding: "8px 16px" }}
        >
          {testSendStatus === "sending" ? "요청 중..." : "지금 테스트 메일 받기"}
        </button>
      </div>
      {status === "saved" && <p style={{ color: "green" }}>저장했습니다.</p>}
      {status === "error" && <p style={{ color: "red" }}>{errorMessage}</p>}
      {testSendStatus === "sent" && <p style={{ color: "green" }}>{testSendMessage}</p>}
      {testSendStatus === "error" && <p style={{ color: "red" }}>{testSendMessage}</p>}

      <p style={{ marginTop: 24 }}>
        <a href="/history">발송 이력 보기</a>
      </p>
    </main>
  );
}
