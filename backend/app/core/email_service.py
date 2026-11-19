"""Email delivery service for registration and password reset OTP codes.

Supports:
1. Resend HTTP API (recommended on Render Free where outbound SMTP ports may be blocked).
2. Standard SMTP with STARTTLS (port 587) or SSL (port 465) via asyncio.to_thread.
3. Development console fallback when ENVIRONMENT is not production.
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Literal

import httpx
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

OTPPurpose = Literal["REGISTER", "RESET_PASSWORD"]


def _build_otp_content(otp_code: str, purpose: OTPPurpose, expire_minutes: int) -> tuple[str, str, str]:
    if purpose == "REGISTER":
        subject = f"[AI CareerGuide] Mã xác nhận đăng ký tài khoản: {otp_code}"
        title = "Xác nhận địa chỉ Email đăng ký"
        intro = (
            "Cảm ơn bạn đã đăng ký tài khoản tại <strong>AI CareerGuide</strong>. "
            "Vui lòng nhập mã xác nhận 6 chữ số dưới đây để hoàn tất kích hoạt tài khoản:"
        )
    else:
        subject = f"[AI CareerGuide] Mã xác nhận đặt lại mật khẩu: {otp_code}"
        title = "Yêu cầu đặt lại mật khẩu"
        intro = (
            "Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản <strong>AI CareerGuide</strong> của bạn. "
            "Vui lòng nhập mã xác nhận 6 chữ số dưới đây để tạo mật khẩu mới:"
        )

    plain_text = (
        f"{title}\n\n"
        f"Mã xác nhận của bạn là: {otp_code}\n"
        f"Mã có hiệu lực trong {expire_minutes} phút.\n"
        "Tuyệt đối không chia sẻ mã này cho bất kỳ ai. Nếu bạn không thực hiện yêu cầu này, hãy bỏ qua email."
    )

    html = f"""<!DOCTYPE html>
<html lang="vi">
<body style="margin:0;padding:24px;background:#f0f9ff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#0f172a;">
  <div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:20px;border:1px solid #e2e8f0;padding:32px;">
    <div style="font-size:13px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;color:#0284c7;">AI CAREERGUIDE</div>
    <h1 style="margin:10px 0 12px;font-size:22px;line-height:1.3;color:#0f172a;">{title}</h1>
    <p style="margin:0 0 20px;font-size:14px;line-height:1.6;color:#475569;">{intro}</p>
    <div style="margin:20px 0;padding:18px;border-radius:16px;background:#f0f9ff;border:1px solid #bae6fd;text-align:center;">
      <span style="font-size:32px;font-weight:900;letter-spacing:0.28em;color:#0369a1;">{otp_code}</span>
    </div>
    <p style="margin:0 0 8px;font-size:13px;color:#475569;">Mã có hiệu lực trong <strong>{expire_minutes} phút</strong> và chỉ sử dụng được một lần.</p>
    <p style="margin:0;font-size:12px;color:#94a3b8;">Không chia sẻ mã này cho bất kỳ ai. Nếu bạn không yêu cầu, hãy bỏ qua email này.</p>
  </div>
</body>
</html>"""
    return subject, plain_text, html


def _send_via_smtp_sync(to_email: str, subject: str, plain_text: str, html: str) -> None:
    sender_email = (settings.SMTP_FROM_EMAIL or settings.SMTP_USER).strip()
    sender_header = f"{settings.SMTP_FROM_NAME} <{sender_email}>" if settings.SMTP_FROM_NAME else sender_email

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_header
    msg["To"] = to_email
    msg.set_content(plain_text)
    msg.add_alternative(html, subtype="html")

    if settings.SMTP_PORT == 465:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            server.ehlo()
            if settings.SMTP_USE_TLS:
                server.starttls()
                server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)


async def _send_via_resend(to_email: str, subject: str, plain_text: str, html: str) -> None:
    sender_email = (settings.SMTP_FROM_EMAIL or "onboarding@resend.dev").strip()
    sender_header = f"{settings.SMTP_FROM_NAME} <{sender_email}>" if settings.SMTP_FROM_NAME else sender_email

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": sender_header,
                "to": [to_email],
                "subject": subject,
                "text": plain_text,
                "html": html,
            },
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Resend API failed with HTTP {resp.status_code}")


async def send_otp_email(to_email: str, otp_code: str, purpose: OTPPurpose) -> str:
    """Send a 6-digit OTP email. Returns delivery channel ('resend' | 'smtp' | 'dev_log')."""
    subject, plain_text, html = _build_otp_content(otp_code, purpose, settings.OTP_EXPIRE_MINUTES)

    if settings.RESEND_API_KEY.strip():
        try:
            await _send_via_resend(to_email, subject, plain_text, html)
            return "resend"
        except Exception as exc:
            logger.error("Failed to deliver OTP via Resend (%s)", type(exc).__name__)
            raise HTTPException(
                503,
                "Không thể gửi email xác nhận lúc này. Vui lòng thử lại sau ít phút.",
            ) from None

    if settings.SMTP_HOST.strip() and settings.SMTP_USER.strip() and settings.SMTP_PASSWORD.strip():
        try:
            await asyncio.to_thread(_send_via_smtp_sync, to_email, subject, plain_text, html)
            return "smtp"
        except Exception as exc:
            logger.error("Failed to deliver OTP via SMTP (%s)", type(exc).__name__)
            raise HTTPException(
                503,
                "Không thể gửi email xác nhận qua máy chủ SMTP. Vui lòng kiểm tra cấu hình hoặc thử lại sau.",
            ) from None

    if settings.ENVIRONMENT.lower() in {"production", "prod"}:
        logger.error("Email provider not configured in production (set RESEND_API_KEY or SMTP_*).")
        raise HTTPException(
            503,
            "Dịch vụ gửi email xác nhận chưa được cấu hình trên máy chủ. Vui lòng cấu hình RESEND_API_KEY hoặc SMTP.",
        )

    logger.warning("[DEV OTP] purpose=%s to=%s code=%s", purpose, to_email, otp_code)
    return "dev_log"
