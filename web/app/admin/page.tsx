"use client";

import { useEffect, useState } from "react";

type SignupRequest = {
  id: number;
  email: string;
  status: "pending" | "approved" | "rejected";
  requested_at: string;
  reviewed_at: string | null;
};

type Status = "loading" | "ready" | "error";

const STATUS_LABEL: Record<SignupRequest["status"], { text: string; color: string }> = {
  pending: { text: "대기", color: "#b26a00" },
  approved: { text: "승인", color: "#2e7d32" },
  rejected: { text: "거절", color: "#999" },
};

export default function AdminPage() {
  const [requests, setRequests] = useState<SignupRequest[]>([]);
  const [status, setStatus] = useState<Status>("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const [processingId, setProcessingId] = useState<number | null>(null);

  async function load() {
    setStatus("loading");
    try {
      const response = await fetch("/api/admin/signup-requests");
      const body = await response.json();
      if (!response.ok) {
        setErrorMessage(body.error ?? "목록을 불러오지 못했습니다.");
        setStatus("error");
        return;
      }
      setRequests(body.requests);
      setStatus("ready");
    } catch {
      setErrorMessage("목록을 불러오지 못했습니다.");
      setStatus("error");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleAction(id: number, action: "approve" | "reject") {
    setProcessingId(id);
    try {
      const response = await fetch("/api/admin/signup-requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, action }),
      });
      const body = await response.json();
      if (!response.ok) {
        alert(body.error ?? "처리에 실패했습니다.");
        return;
      }
      await load();
    } finally {
      setProcessingId(null);
    }
  }

  const pending = requests.filter((r) => r.status === "pending");
  const history = requests.filter((r) => r.status !== "pending");

  return (
    <main style={{ maxWidth: 720, margin: "60px auto", fontFamily: "sans-serif", padding: "0 16px" }}>
      <h1 style={{ fontSize: 22 }}>가입 요청 관리</h1>
      <p style={{ color: "#666", fontSize: 14, marginBottom: 24 }}>
        승인하면 계정이 생성되고 로그인 코드 메일이 바로 발송됩니다. 거절하면 계정이 생성되지 않습니다.
      </p>

      {status === "loading" && <p>불러오는 중...</p>}
      {status === "error" && <p style={{ color: "red" }}>{errorMessage}</p>}

      {status === "ready" && (
        <>
          <h2 style={{ fontSize: 16, marginTop: 24 }}>대기 중 ({pending.length})</h2>
          {pending.length === 0 ? (
            <p style={{ color: "#666", fontSize: 14 }}>대기 중인 요청이 없습니다.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: 32 }}>
              <thead>
                <tr>
                  <th style={thStyle}>이메일</th>
                  <th style={thStyle}>요청일시</th>
                  <th style={thStyle}>액션</th>
                </tr>
              </thead>
              <tbody>
                {pending.map((row) => (
                  <tr key={row.id}>
                    <td style={tdStyle}>{row.email}</td>
                    <td style={tdStyle}>{new Date(row.requested_at).toLocaleString()}</td>
                    <td style={tdStyle}>
                      <button
                        onClick={() => handleAction(row.id, "approve")}
                        disabled={processingId === row.id}
                        style={{ ...buttonStyle, marginRight: 8, background: "#1a237e", color: "#fff" }}
                      >
                        승인
                      </button>
                      <button
                        onClick={() => handleAction(row.id, "reject")}
                        disabled={processingId === row.id}
                        style={{ ...buttonStyle, background: "#eee" }}
                      >
                        거절
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <h2 style={{ fontSize: 16 }}>처리 이력</h2>
          {history.length === 0 ? (
            <p style={{ color: "#666", fontSize: 14 }}>처리된 요청이 없습니다.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={thStyle}>이메일</th>
                  <th style={thStyle}>상태</th>
                  <th style={thStyle}>요청일시</th>
                  <th style={thStyle}>처리일시</th>
                </tr>
              </thead>
              <tbody>
                {history.map((row) => (
                  <tr key={row.id}>
                    <td style={tdStyle}>{row.email}</td>
                    <td style={{ ...tdStyle, color: STATUS_LABEL[row.status].color }}>
                      {STATUS_LABEL[row.status].text}
                    </td>
                    <td style={tdStyle}>{new Date(row.requested_at).toLocaleString()}</td>
                    <td style={tdStyle}>{row.reviewed_at ? new Date(row.reviewed_at).toLocaleString() : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </main>
  );
}

const thStyle: React.CSSProperties = {
  textAlign: "left",
  borderBottom: "1px solid #ddd",
  padding: 8,
  fontSize: 13,
  color: "#666",
};

const tdStyle: React.CSSProperties = {
  borderBottom: "1px solid #eee",
  padding: 8,
  fontSize: 14,
};

const buttonStyle: React.CSSProperties = {
  padding: "6px 12px",
  borderRadius: 4,
  border: "none",
  cursor: "pointer",
  fontSize: 13,
};
