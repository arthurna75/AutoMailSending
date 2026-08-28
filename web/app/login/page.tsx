"use client";

import { useState, type FormEvent } from "react";
import { createClient } from "@/lib/supabase/client";

type Step = "email" | "code" | "pending";
type Status = "idle" | "sending" | "sent" | "verifying" | "error";

const ACCENT = "#1a237e";

function StepIndicator({ step }: { step: Step }) {
  const activeIndex = step === "email" ? 0 : 1; // code/pending 모두 2단계로 취급

  const steps = ["이메일 등록", "승인 확인", "로그인 완료"];

  return (
    <div style={{ display: "flex", alignItems: "center", marginBottom: 28 }}>
      {steps.map((label, index) => (
        <div key={label} style={{ display: "flex", alignItems: "center", flex: index < steps.length - 1 ? 1 : undefined }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", minWidth: 64 }}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 13,
                fontWeight: 600,
                background: index <= activeIndex ? ACCENT : "#e0e0e0",
                color: index <= activeIndex ? "#fff" : "#999",
              }}
            >
              {index + 1}
            </div>
            <span style={{ fontSize: 11, color: index <= activeIndex ? ACCENT : "#999", marginTop: 4, textAlign: "center" }}>
              {label}
            </span>
          </div>
          {index < steps.length - 1 && (
            <div style={{ flex: 1, height: 2, background: index < activeIndex ? ACCENT : "#e0e0e0", margin: "0 4px 16px" }} />
          )}
        </div>
      ))}
    </div>
  );
}

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<Step>("email");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmitEmail(event: FormEvent) {
    event.preventDefault();
    setStatus("sending");
    try {
      const response = await fetch("/api/signup-requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const body = await response.json();
      if (!response.ok) {
        setErrorMessage(body.error ?? "요청을 처리하지 못했습니다.");
        setStatus("error");
        return;
      }
      if (body.outcome === "otp_sent") {
        setStatus("sent");
        setStep("code");
      } else {
        setStatus("idle");
        setStep("pending");
      }
    } catch {
      setErrorMessage("요청을 처리하지 못했습니다. 잠시 후 다시 시도해주세요.");
      setStatus("error");
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

  function resetToEmailStep() {
    setStep("email");
    setStatus("idle");
    setErrorMessage("");
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#fafafa",
        padding: 16,
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 420,
          background: "#fff",
          borderRadius: 12,
          boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
          padding: "40px 32px",
          fontFamily: "sans-serif",
        }}
      >
        <h1 style={{ fontSize: 26, fontWeight: 700, margin: 0 }}>주요뉴스 다이제스트</h1>
        <p style={{ marginTop: 6, marginBottom: 24 }}>
          <a href="/user_guide.html" target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, color: "#555" }}>
            로그인 방법이 궁금하신가요? 사용자 가이드 보기 →
          </a>
        </p>

        <StepIndicator step={step} />

        {step === "email" && (
          <>
            <p style={{ fontSize: 15, lineHeight: 1.6 }}>
              🎉 지금은 누구나 이메일 등록으로 이용을 신청할 수 있습니다.
              <br />
              이미 등록된 이메일이면 바로 인증 코드를 보내드리고, 처음이면 운영자 승인 후 코드를 보내드립니다.
            </p>
            <form onSubmit={handleSubmitEmail}>
              <input
                type="email"
                required
                placeholder="you@example.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                style={inputStyle}
              />
              <button type="submit" disabled={status === "sending"} style={buttonStyle}>
                {status === "sending" ? "확인 중..." : "인증 코드 받기"}
              </button>
            </form>
          </>
        )}

        {step === "pending" && (
          <>
            <p style={{ fontSize: 15, lineHeight: 1.6 }}>
              <strong>{email}</strong> 신청이 접수되었습니다.
              <br />
              운영자 승인이 완료되면 같은 주소로 로그인 코드 메일을 보내드립니다.
            </p>
            <button onClick={resetToEmailStep} style={{ ...linkButtonStyle, marginTop: 8 }}>
              ← 다른 이메일로 다시 시도
            </button>
          </>
        )}

        {step === "code" && (
          <>
            <p style={{ fontSize: 15, lineHeight: 1.6 }}>
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
                style={{ ...inputStyle, letterSpacing: 4, fontSize: 18, textAlign: "center" }}
              />
              <button type="submit" disabled={status === "verifying"} style={buttonStyle}>
                {status === "verifying" ? "확인 중..." : "로그인"}
              </button>
            </form>
            <button onClick={resetToEmailStep} style={{ ...linkButtonStyle, marginTop: 12 }}>
              ← 다른 이메일로 다시 받기
            </button>
          </>
        )}

        {status === "error" && <p style={{ color: "red", fontSize: 14, marginTop: 12 }}>{errorMessage}</p>}
      </div>
    </main>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "12px 14px",
  marginBottom: 12,
  fontSize: 16,
  border: "1px solid #ccc",
  borderRadius: 8,
  boxSizing: "border-box",
};

const buttonStyle: React.CSSProperties = {
  width: "100%",
  padding: 14,
  fontSize: 16,
  fontWeight: 600,
  background: ACCENT,
  color: "#fff",
  border: "none",
  borderRadius: 8,
  cursor: "pointer",
};

const linkButtonStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  color: "#555",
  cursor: "pointer",
  padding: 0,
  fontSize: 13,
  display: "block",
};
