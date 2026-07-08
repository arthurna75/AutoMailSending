import { createClient } from "@/lib/supabase/server";

export default async function HistoryPage() {
  const supabase = createClient();
  const { data: digests } = await supabase
    .from("digests")
    .select("id, sent_at, subject, article_count")
    .order("sent_at", { ascending: false })
    .limit(30);

  return (
    <main style={{ maxWidth: 560, margin: "40px auto", fontFamily: "sans-serif", padding: "0 16px" }}>
      <h1>발송 이력</h1>
      <p>
        <a href="/dashboard">← 설정으로 돌아가기</a>
      </p>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "1px solid #ccc" }}>
            <th>발송일시</th>
            <th>제목</th>
            <th>기사수</th>
          </tr>
        </thead>
        <tbody>
          {(digests ?? []).map((digest) => (
            <tr key={digest.id} style={{ borderBottom: "1px solid #eee" }}>
              <td>{new Date(digest.sent_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })}</td>
              <td>{digest.subject}</td>
              <td>{digest.article_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {(digests ?? []).length === 0 && <p>아직 발송 이력이 없습니다.</p>}
    </main>
  );
}
