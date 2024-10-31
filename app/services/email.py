import resend
from core.config import settings
from pathlib import Path
import secrets


class EmailService:
    def __init__(self):
        resend.api_key = settings.RESEND_API_KEY
        self.from_email = settings.FROM_EMAIL

    def send_verification_email(self, to_email: str, token: str):
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

        try:
            response = resend.Emails.send({
                "from": self.from_email,
                "to": to_email,
                "subject": "Verify your BeatCode account",
                "html": f"""
                <h1>Welcome to BeatCode!</h1>
                <p>Please verify your email address by clicking the link below:</p>
                <a href="{verify_url}">Verify Email</a>
                <p>If you did not create an account, please ignore this email.</p>
            """})

            return response
        except Exception as e:
            print(f"""
Error sending email to {to_email}:
{e}
Verification Code: {token}
                  """)
            return None

    def send_password_reset_email(self, to_email: str, token: str):
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

        try:
            response = resend.Emails.send({
                "from": self.from_email,
                "to": to_email,
                "subject": "Reset your BeatCode password",
                "html": f"""
                <h1>Reset your BeatCode password</h1>
                <p>To reset your password, click the link below:</p>
                <a href="{reset_url}">Reset Password</a>
                <p>If you did not request a password reset, please ignore this email.</p>
                <p>This link will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>
            """
            })

            return response
        except Exception as e:
            print(f"""
Error sending email to {to_email}:
{e}
Reset Token: {token}
                  """)
            return None


def generate_token() -> str:
    return secrets.token_urlsafe(32)
