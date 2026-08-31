import nodemailer from "nodemailer";
import { getAdminEmails } from "@/lib/admin";

export async function sendSignupRequestNotification(email: string): Promise<void> {
  const username = process.env.SMTP_USERNAME;
  const password = process.env.SMTP_PASSWORD;
  const admins = getAdminEmails();

  if (!username || !password || admins.length === 0) {
    console.warn("[mailer] SMTP_USERNAME/PASSWORD 또는 ADMIN_EMAILS 미설정 — 가입 알림 메일 스킵");
    return;
  }

  try {
    const transporter = nodemailer.createTransport({
      host: process.env.SMTP_HOST ?? "smtp.gmail.com",
      port: Number(process.env.SMTP_PORT ?? 587),
      secure: false,
      auth: { user: username, pass: password },
    });

    await transporter.sendMail({
      from: `"주요뉴스 다이제스트" <${username}>`,
      to: admins.join(","),
      subject: `[뉴스 다이제스트] 가입 승인 요청: ${email}`,
      text: `${email} 님이 서비스 이용을 신청했습니다.\n\n승인/거절: https://web-psi-rouge-56.vercel.app/admin`,
    });
  } catch (err) {
    console.error("[mailer] 가입 알림 메일 발송 실패:", err);
  }
}
