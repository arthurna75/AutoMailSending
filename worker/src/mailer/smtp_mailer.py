"""범용 SMTP 발송기. 특정 메일 제공자(Gmail/Naver 등)에 종속되지 않고 전부 config로 구동."""

from __future__ import annotations

import logging
import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from src.app_config import EmailConfig
from src.utils.htmlclean import strip_html

logger = logging.getLogger(__name__)


def _connect(cfg: EmailConfig) -> smtplib.SMTP:
    if cfg.use_ssl:
        server = smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=15)
    else:
        server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=15)
        if cfg.use_tls:
            server.starttls()
    if cfg.username:
        server.login(cfg.username, cfg.password)
    return server


def test_connection(cfg: EmailConfig) -> tuple[bool, str]:
    """발송 없이 SMTP 연결/로그인만 확인한다. (성공여부, 오류메시지)"""
    try:
        server = _connect(cfg)
        server.quit()
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, "이메일/비밀번호(또는 앱 비밀번호)가 올바르지 않습니다."
    except (smtplib.SMTPException, socket.error, socket.timeout, OSError) as e:
        return False, f"SMTP 서버에 연결할 수 없습니다: {e}"


class SmtpMailer:
    def __init__(self, cfg: EmailConfig):
        self._cfg = cfg

    def send(self, subject: str, html_body: str, to_addrs: list[str]) -> None:
        cfg = self._cfg
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((cfg.from_name, cfg.from_addr)) if cfg.from_name else cfg.from_addr
        msg["To"] = ", ".join(to_addrs)

        msg.attach(MIMEText(strip_html(html_body), "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        server = _connect(cfg)
        try:
            server.send_message(msg, from_addr=cfg.from_addr, to_addrs=to_addrs)
            logger.info("이메일 발송 완료: %s", ", ".join(to_addrs))
        finally:
            server.quit()
