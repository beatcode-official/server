class EmailTemplates:
    """
    A static class to generate email templates.
    """
    @staticmethod
    def verification_email(verify_url: str) -> str:
        """
        Generate an email template for email verification.

        :param verify_url: The URL to verify the email.

        :return: The email template.
        """
        return f"""
        <h1>Welcome to BeatCode!</h1>
        <p>Please verify your email address by clicking the link below:</p>
        <a href="{verify_url}">Verify Email</a>
        <p>If you did not create an account, please ignore this email.</p>
    """

    @staticmethod
    def password_reset_email(reset_url: str, expire_minutes: int) -> str:
        """
        Generate an email template for password reset.

        :param reset_url: The URL to reset the password.

        :param expire_minutes: The number of minutes before the reset link expires.
        """
        return f"""
        <h1>Reset your BeatCode password</h1>
        <p>To reset your password, click the link below:</p>
        <a href="{reset_url}">Reset Password</a>
        <p>If you did not request a password reset, please ignore this email.</p>
        <p>This link will expire in {expire_minutes} minutes.</p>
    """
