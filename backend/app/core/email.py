"""
SMTP email sender for OTP verification codes.

Configure via .env or environment variables:
  SMTP_ENABLED=true
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=yourapp@gmail.com
  SMTP_PASSWORD=your-app-password
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings


def send_otp_email(to_email: str, otp_code: str) -> bool:
    """
    Send the OTP verification code to the student's email.
    Returns True on success, False on failure (never raises — caller handles fallback).
    """
    if not settings.SMTP_ENABLED:
        print(f"[EMAIL] SMTP disabled — OTP for {to_email}: {otp_code}")
        return False

    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print(f"[EMAIL] SMTP credentials not set — OTP for {to_email}: {otp_code}")
        return False

    subject = f"Your Face Attendance OTP: {otp_code}"

    html_body = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 480px; margin: 0 auto;
                border: 2px solid #0D1B2A; padding: 0;">
        <div style="background: #0D1B2A; padding: 20px 24px;">
            <h1 style="color: #D4A843; margin: 0; font-size: 20px;">Face Attendance System</h1>
        </div>
        <div style="padding: 24px;">
            <p style="color: #333; font-size: 15px; margin-top: 0;">
                Your one-time verification code is:
            </p>
            <div style="background: #F5F0E8; border: 2px solid #0D1B2A; padding: 16px;
                        text-align: center; margin: 16px 0;">
                <span style="font-family: 'Courier New', monospace; font-size: 36px;
                             font-weight: bold; color: #0D1B2A; letter-spacing: 8px;">
                    {otp_code}
                </span>
            </div>
            <p style="color: #666; font-size: 13px;">
                This code expires in <strong>5 minutes</strong>. Do not share it with anyone.
            </p>
            <p style="color: #666; font-size: 13px;">
                If you did not request this code, please ignore this email.
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="color: #999; font-size: 11px; margin-bottom: 0;">
                Sent to {to_email} — MUJ Face Attendance System
            </p>
        </div>
        <div style="height: 4px; background: linear-gradient(to right, #C1392B, #D4A843, #0D1B2A);"></div>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"
    msg["To"] = to_email

    # Plain text fallback
    msg.attach(MIMEText(
        f"Your Face Attendance OTP is: {otp_code}\n\nExpires in 5 minutes.\nDo not share this code.",
        "plain",
    ))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
        print(f"[EMAIL] OTP sent to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send to {to_email}: {e}")
        return False
