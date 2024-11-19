import resend
from core.config import settings
from services.email.templates import EmailTemplates


class EmailService:
    """
    A service class to handle sending emails using the Resend API.
    """

    def __init__(self):
        resend.api_key = settings.RESEND_API_KEY
        self.from_email = settings.FROM_EMAIL
        self.expire_minutes = settings.PASSWORD_RESET_TOKEN_EXPIRE
        self.frontend_url = settings.FRONTEND_URL

    def send_verification_email(self, to_email: str, token: str):
        """
        Send a verification email to the user's email address.

        :param to_email: The email address to send the email to.
        :param token: The verification token to include in the email.
        """
        verify_url = f"{self.frontend_url}/verify-email?token={token}"

        try:
            response = resend.Emails.send({
                "from": self.from_email,
                "to": to_email,
                "subject": "Verify your BeatCode account",
                "html": EmailTemplates.verification_email(verify_url)
            })

            return response
        except Exception as e:
            # Logging the error to allow for debugging without an actual API key
            print(f"Error sending email to {to_email}:\n{e}\nReset Token: {token}")
            return None

    def send_password_reset_email(self, to_email: str, token: str):
        """
        Send a password reset email to the user's email address.

        :param to_email: The email address to send the email to.
        :param token: The password reset token to include in the email.    
        """
        reset_url = f"{self.frontend_url}/reset-password?token={token}"

        try:
            response = resend.Emails.send({
                "from": self.from_email,
                "to": to_email,
                "subject": "Reset your BeatCode password",
                "html": EmailTemplates.password_reset_email(reset_url, self.expire_minutes)
            })

            return response
        except Exception as e:
            # Logging the error to allow for debugging without an actual API key
            print(f"Error sending email to {to_email}:\n{e}\nReset Token: {token}")
            return None


email_service = EmailService()
