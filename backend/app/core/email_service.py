"""Email delivery service for registration and password reset OTP codes.

Supports (over HTTPS port 443 — works on Render Free where SMTP ports 25/465/587 are blocked):
1. Brevo HTTP API (free 300 emails/day, sends to ANY email using a single verified Gmail sender, no custom domain needed).
2. Standard SMTP with fast 6s timeout (for local dev, VPS, or paid cloud instances).
3. Resend HTTP API (for verified custom domains or sandbox self-testing).
4. Development console fallback when ENVIRONMENT is not production.
"""
from __future__ import annotations

import asyncio
import logging
import re
import smtplib
from email.message import EmailMessage
from typing import Literal

import httpx
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

OTPPurpose = Literal["REGISTER", "RESET_PASSWORD"]

_CONSUMER_MAIL_DOMAINS = (
    "@gmail.com",
    "@googlemail.com",
    "@yahoo.com",
    "@outlook.com",
    "@hotmail.com",
    "@icloud.com",
)


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


def _has_webhook_config() -> bool:
    return bool("".join(settings.MAIL_WEBHOOK_URL.split()))


def _has_brevo_config() -> bool:
    return bool(settings.BREVO_API_KEY.strip())


def _has_smtp_config() -> bool:
    return bool(
        settings.SMTP_HOST.strip()
        and settings.SMTP_USER.strip()
        and settings.SMTP_PASSWORD.strip()
    )


def _has_resend_config() -> bool:
    return bool(settings.RESEND_API_KEY.strip())


def _is_consumer_sender(email: str) -> bool:
    lowered = email.strip().lower()
    return any(lowered.endswith(domain) for domain in _CONSUMER_MAIL_DOMAINS)


def _extract_html_summary(raw_text: str) -> str:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw_text, re.IGNORECASE | re.DOTALL)
    if title_match:
        title = re.sub(r"\s+", " ", title_match.group(1)).strip()
        if title:
            return title[:160]
    stripped = re.sub(r"<[^>]+>", " ", raw_text)
    return re.sub(r"\s+", " ", stripped).strip()[:160]


async def _send_via_webhook(to_email: str, subject: str, plain_text: str, html: str) -> None:
    """Send email via HTTPS webhook (e.g. Google Apps Script MailApp Web App)."""
    webhook_url = "".join(settings.MAIL_WEBHOOK_URL.split())
    secret = settings.MAIL_WEBHOOK_SECRET.strip()
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
        resp = await client.post(
            webhook_url,
            json={
                "secret": secret,
                "to": to_email,
                "subject": subject,
                "text": plain_text,
                "html": html,
                "fromName": (settings.SMTP_FROM_NAME or "AI CareerGuide").strip(),
            },
        )
        if resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("location", "")
            loc_lower = location.lower()
            if "accounts.google.com" in loc_lower or "servicelogin" in loc_lower:
                raise RuntimeError(
                    "Google Apps Script đang để quyền 'Chỉ mình tôi'. Hãy vào script.google.com -> Triển khai -> Quản lý nội dung triển khai -> Sửa -> chọn 'Ai có quyền truy cập: Bất kỳ ai (Anyone)' rồi bấm Triển khai."
                )
            if not location:
                raise RuntimeError(f"Webhook HTTP {resp.status_code} thiếu Location chuyển hướng.")
            resp = await client.get(location, follow_redirects=True)

        raw_text = resp.text or ""
        text_lower = raw_text.lower()
        final_url_lower = str(resp.url).lower()

        if "accounts.google.com" in final_url_lower or "sign in - google accounts" in text_lower or resp.status_code in (401, 403):
            raise RuntimeError(
                "Google Apps Script chưa mở quyền 'Bất kỳ ai (Anyone)' hoặc chưa hoàn tất Ủy quyền truy cập (Advanced -> Go to ... unsafe -> Allow)."
            )
        if "script function not found: dopost" in text_lower:
            raise RuntimeError(
                "Google Apps Script chưa lưu hàm doPost. Hãy bấm Ctrl+S (Lưu) trên script.google.com rồi tạo Triển khai mới."
            )
        if "authorization is required" in text_lower or "you do not have permission" in text_lower:
            raise RuntimeError(
                "Google Apps Script chưa được cấp quyền gửi Gmail. Hãy vào script.google.com bấm Chạy (Run) hoặc Triển khai mới -> Ủy quyền truy cập -> Advanced -> Go to ... (unsafe) -> Allow."
            )
        if resp.status_code >= 400:
            clean_err = _extract_html_summary(raw_text) or f"HTTP {resp.status_code}"
            raise RuntimeError(f"Webhook HTTP {resp.status_code}: {clean_err}")

        try:
            body = resp.json()
        except ValueError as exc:
            if "<html" in text_lower or "<!doctype html" in text_lower:
                title = _extract_html_summary(raw_text) or "HTML"
                raise RuntimeError(
                    f"Google Apps Script trả về trang HTML thay vì JSON ({title}). Hãy kiểm tra quyền 'Bất kỳ ai' và URL kết thúc bằng /exec."
                ) from exc
            return

        if isinstance(body, dict) and body.get("ok") is False:
            err_detail = str(body.get("error") or "unknown")[:200]
            if "unauthorized" in err_detail.lower():
                raise RuntimeError(
                    "MAIL_WEBHOOK_SECRET trên Render không khớp với biến SECRET trong Google Apps Script."
                )
            raise RuntimeError(f"Google Apps Script báo lỗi: {err_detail}")


async def _send_via_brevo(to_email: str, subject: str, plain_text: str, html: str) -> None:
    sender_email = (settings.SMTP_FROM_EMAIL or settings.SMTP_USER).strip()
    if not sender_email:
        raise RuntimeError("BREVO requires SMTP_FROM_EMAIL (verified sender email).")
    sender_name = (settings.SMTP_FROM_NAME or "AI CareerGuide").strip()

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": settings.BREVO_API_KEY.strip(),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "sender": {"name": sender_name, "email": sender_email},
                "to": [{"email": to_email}],
                "subject": subject,
                "textContent": plain_text,
                "htmlContent": html,
            },
        )
        if resp.status_code >= 400:
            detail = ""
            try:
                body = resp.json()
                detail = str(body.get("message") or body.get("code") or "")[:200]
            except Exception:
                detail = resp.text[:200]
            raise RuntimeError(f"Brevo HTTP {resp.status_code}: {detail}")


def _send_via_smtp_sync(to_email: str, subject: str, plain_text: str, html: str) -> None:
    sender_email = (settings.SMTP_FROM_EMAIL or settings.SMTP_USER).strip()
    sender_header = f"{settings.SMTP_FROM_NAME} <{sender_email}>" if settings.SMTP_FROM_NAME else sender_email

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_header
    msg["To"] = to_email
    msg.set_content(plain_text)
    msg.add_alternative(html, subtype="html")

    # Fast 6s timeout so blocked SMTP ports (e.g. Render Free) fail quickly instead of hanging 40s+.
    if settings.SMTP_PORT == 465:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=6) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=6) as server:
            server.ehlo()
            if settings.SMTP_USE_TLS:
                server.starttls()
                server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)


async def _send_via_resend(to_email: str, subject: str, plain_text: str, html: str) -> None:
    raw_from = (settings.SMTP_FROM_EMAIL or "").strip()
    sender_email = "onboarding@resend.dev" if (not raw_from or _is_consumer_sender(raw_from)) else raw_from
    sender_header = f"{settings.SMTP_FROM_NAME} <{sender_email}>" if settings.SMTP_FROM_NAME else sender_email

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY.strip()}",
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
            detail = ""
            try:
                body = resp.json()
                detail = str(body.get("message") or body.get("name") or "")[:200]
            except Exception:
                detail = resp.text[:200]
            raise RuntimeError(f"Resend HTTP {resp.status_code}: {detail}")


async def send_otp_email(to_email: str, otp_code: str, purpose: OTPPurpose) -> str:
    """Send a 6-digit OTP email. Returns delivery channel ('brevo' | 'smtp' | 'resend' | 'dev_log')."""
    subject, plain_text, html = _build_otp_content(otp_code, purpose, settings.OTP_EXPIRE_MINUTES)

    provider_order: list[str] = []
    if _has_webhook_config():
        provider_order.append("webhook")
    if _has_brevo_config():
        provider_order.append("brevo")
    if _has_smtp_config():
        provider_order.append("smtp")
    if _has_resend_config():
        provider_order.append("resend")

    errors: list[str] = []
    for provider in provider_order:
        if provider == "webhook":
            try:
                await _send_via_webhook(to_email, subject, plain_text, html)
                return "webhook"
            except Exception as exc:
                reason = f"Webhook: {str(exc)[:260]}"
                errors.append(reason)
                logger.error("Failed to deliver OTP via %s", reason)
        elif provider == "brevo":
            try:
                await _send_via_brevo(to_email, subject, plain_text, html)
                return "brevo"
            except Exception as exc:
                reason = f"Brevo: {str(exc)[:200]}"
                errors.append(reason)
                logger.error("Failed to deliver OTP via %s", reason)
        elif provider == "smtp":
            try:
                await asyncio.to_thread(_send_via_smtp_sync, to_email, subject, plain_text, html)
                return "smtp"
            except Exception as exc:
                reason = f"SMTP ({type(exc).__name__}): {str(exc)[:180]}"
                errors.append(reason)
                logger.error("Failed to deliver OTP via %s", reason)
        elif provider == "resend":
            try:
                await _send_via_resend(to_email, subject, plain_text, html)
                return "resend"
            except Exception as exc:
                reason = f"Resend: {str(exc)[:200]}"
                errors.append(reason)
                logger.error("Failed to deliver OTP via %s", reason)

    if provider_order:
        joined = " | ".join(errors).lower()
        if "only send testing emails" in joined or "domain is not verified" in joined:
            raise HTTPException(
                503,
                "Render gói Free chặn cổng SMTP (587) và Resend dùng thử chỉ gửi được cho email chủ tài khoản. "
                "Vui lòng cấu hình BREVO_API_KEY (miễn phí 300 email/ngày qua HTTPS 443) trên Render.",
            )
        if "timeout" in joined or "timed out" in joined or "network is unreachable" in joined:
            raise HTTPException(
                503,
                "Máy chủ Render gói Free chặn kết nối cổng SMTP (587/465). "
                "Vui lòng thêm biến BREVO_API_KEY (gửi qua HTTPS 443, miễn phí 300 email/ngày) trên Render.",
            )
        primary_err = errors[0] if errors else "Không rõ nguyên nhân"
        raise HTTPException(
            503,
            f"Không thể gửi email xác nhận lúc này ({primary_err}).",
        )

    if settings.ENVIRONMENT.lower() in {"production", "prod"}:
        logger.error("Email provider not configured in production (set BREVO_API_KEY, SMTP_* or RESEND_API_KEY).")
        raise HTTPException(
            503,
            "Dịch vụ gửi email xác nhận chưa được cấu hình trên máy chủ. Vui lòng cấu hình BREVO_API_KEY hoặc SMTP.",
        )

    logger.warning("[DEV OTP] purpose=%s to=%s code=%s", purpose, to_email, otp_code)
    return "dev_log"
