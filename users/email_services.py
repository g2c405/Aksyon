
import resend

from django.conf import settings

from .models import EmailVerificationOTP


def send_otp_email(user, code, purpose, recipient):
    """
    Send an OTP email based on the verification purpose.
    """

    email_content = {
        EmailVerificationOTP.Purpose.REGISTRATION: {
            "subject": "Verify your Aksyon account",
            "message": (
                "Welcome to Aksyon!\n\n"
                "Use the verification code below to verify your "
                "email address:\n\n"
                f"Your verification code: {code}\n\n"
                "This code expires in 10 minutes.\n"
                "You must verify your email before you can log in."
            ),
        },

        EmailVerificationOTP.Purpose.EMAIL_CHANGE: {
            "subject": "Verify your new Aksyon email address",
            "message": (
                "You requested to change the email address "
                "associated with your Aksyon account.\n\n"
                "Use the verification code below to confirm "
                "your new email address:\n\n"
                f"Your verification code: {code}\n\n"
                "This code expires in 10 minutes.\n"
                "Your current email address will remain unchanged "
                "until verification is completed."
            ),
        },

        EmailVerificationOTP.Purpose.CONTACT_CHANGE: {
            "subject": "Verify your Aksyon contact number change",
            "message": (
                "You requested to change the contact number "
                "associated with your Aksyon account.\n\n"
                "Use the verification code below to confirm "
                "your contact number change:\n\n"
                f"Your verification code: {code}\n\n"
                "This code expires in 10 minutes."
            ),
        },
    }

    content = email_content.get(purpose)

    if not content:
        raise ValueError("Invalid OTP email purpose.")

    resend.api_key = settings.RESEND_API_KEY

    return resend.Emails.send({
        "from": settings.DEFAULT_FROM_EMAIL,
        "to": [recipient],
        "subject": content["subject"],
        "text": content["message"],
    })
