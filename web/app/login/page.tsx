"use client";

import { useState, type FormEvent } from "react";
import { createClient } from "@/lib/supabase/client";

type Step = "email" | "code";
type Status = "idle" | "sending" | "sent" | "verifying" | "error";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<Step>("email");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSendCode(event: FormEvent) {
    event.preventDefault();
    setStatus("sending");
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOtp({ email });
    if (error) {
      setErrorMessage(error.message);
      setStatus("error");
    } else {
      setStatus("sent");
      setStep("code");
    }
  }

  async function handleVerifyCode(event: FormEvent) {
    event.preventDefault();
    setStatus("verifying");
    const supabase = createClient();
    const { error } = await supabase.auth.verifyOtp({
      email,
      token: code.trim(),
      type: "email",
    });
    if (error) {
      setErrorMessage(error.message);
      setStatus("error");
    } else {
      window.location.href = "/dashboard";
    }
  }

  return (
    <main style={{ maxWidth: 360, margin: "80px auto", fontFamily: "sans-serif" }}>
      <h1>주요뉴스 다이제스트</h1>
      <p style={{ marginTop: 4, marginBottom: 16 }}>
        <a href="/user_guide.html" target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, color: "#555" }}>
          로그인 방법이 궁금하신가요? 사용자 가이드 보기 →
        </a>
      </p>

      {step === "email" && (
        <>
          <p>초대받은 이메일로 인증 코드를 보내드립니다.</p>
          <form onSubmit={handleSendCode}>
            <input
              type="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              style={{ width: "100%", padding: 8, marginBottom: 8 }}
            />
            <button type="submit" disabled={status === "sending"} style={{ width: "100%", padding: 8 }}>
              {status === "sending" ? "전송 중..." : "인증 코드 받기"}
            </button>
          </form>
        </>
      )}

      {step === "code" && (
        <>
          <p>
            <strong>{email}</strong>로 8자리 인증 코드를 보냈습니다. 메일에서 코드를 확인해 아래에 입력해주세요.
          </p>
          <form onSubmit={handleVerifyCode}>
            <input
              type="text"
              inputMode="numeric"
              required
              maxLength={8}
              placeholder="12345678"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              style={{ width: "100%", padding: 8, marginBottom: 8, letterSpacing: 4, fontSize: 18 }}
            />
            <button type="submit" disabled={status === "verifying"} style={{ width: "100%", padding: 8 }}>
              {status === "verifying" ? "확인 중..." : "로그인"}
            </button>
          </form>
          <p style={{ marginTop: 8 }}>
            <button
              onClick={() => setStep("email")}
              style={{ background: "none", border: "none", color: "#555", cursor: "pointer", padding: 0 }}
            >
              ← 다른 이메일로 다시 받기
            </button>
          </p>
        </>
      )}

      {status === "error" && <p style={{ color: "red" }}>{errorMessage}</p>}
    </main>
  );
}
