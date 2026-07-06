import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "주요뉴스 다이제스트 설정",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
