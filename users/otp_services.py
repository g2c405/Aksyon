
from datetime import timedelta
from .email_services import send_otp_email
from django.db import transaction
from django.utils import timezone

from .models import EmailVerificationOTP
from .utils import generate_otp, hash_otp, verify_otp


# OTP configuration
OTP_EXPIRY_MINUTES = 10
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_MAX_ATTEMPTS = 5


# Custom exceptions
class OTPError(Exception):
    pass


class OTPResendCooldown(OTPError):
    def __init__(self, retry_after):
        self.retry_after = retry_after
        super().__init__(
            f"Please wait {retry_after} seconds before requesting another OTP."
        )


class OTPNotFound(OTPError):
    pass


class OTPExpired(OTPError):
    pass


class OTPInvalid(OTPError):
    pass


class OTPMaxAttempts(OTPError):
    pass


def create_otp(user, purpose, target_value=""):
    """
    Generate and store a new OTP for a user.

    Returns:
        (otp_record, plain_otp)
    """

    if purpose not in EmailVerificationOTP.Purpose.values:
        raise ValueError("Invalid OTP purpose.")

    now = timezone.now()

    with transaction.atomic():

        # Lock the user row to prevent concurrent OTP creation.
        user.__class__.objects.select_for_update().get(pk=user.pk)

        latest_otp = (
            EmailVerificationOTP.objects
            .filter(user=user, purpose=purpose)
            .order_by("-created_at")
            .first()
        )

        # Enforce resend cooldown.
        if latest_otp:
            next_allowed_time = (
                latest_otp.created_at
                + timedelta(seconds=OTP_RESEND_COOLDOWN_SECONDS)
            )

            if now < next_allowed_time:
                retry_after = int(
                    (next_allowed_time - now).total_seconds()
                ) + 1

                raise OTPResendCooldown(retry_after)

        # Invalidate previous unused OTPs for this purpose.
        EmailVerificationOTP.objects.filter(
            user=user,
            purpose=purpose,
            consumed_at__isnull=True,
            expires_at__gt=now,
        ).update(expires_at=now)

        # Generate and hash the new OTP.
        plain_otp = generate_otp()
        hashed_otp = hash_otp(plain_otp)

        otp_record = EmailVerificationOTP.objects.create(
            user=user,
            purpose=purpose,
            code_hash=hashed_otp,
            target_value=target_value,
            expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
        )

    return otp_record, plain_otp


def verify_user_otp(user, purpose, submitted_code):
    """
    Verify the latest OTP issued for a user and purpose.

    Returns:
        The verified OTP record.

    Raises:
        OTPNotFound
        OTPExpired
        OTPInvalid
        OTPMaxAttempts
    """

    now = timezone.now()
    outcome = None
    verified_otp = None

    with transaction.atomic():

        # Always inspect the latest OTP.
        otp = (
            EmailVerificationOTP.objects
            .select_for_update()
            .filter(user=user, purpose=purpose)
            .order_by("-created_at")
            .first()
        )

        if not otp:
            outcome = "not_found"

        elif otp.consumed_at is not None:
            outcome = "not_found"

        elif otp.expires_at <= now:
            outcome = "expired"

        elif otp.attempts >= OTP_MAX_ATTEMPTS:
            outcome = "max_attempts"

        elif not verify_otp(str(submitted_code), otp.code_hash):

            otp.attempts += 1

            if otp.attempts >= OTP_MAX_ATTEMPTS:
                otp.consumed_at = now
                outcome = "max_attempts"
            else:
                outcome = "invalid"

            otp.save(update_fields=["attempts", "consumed_at"])

        else:
            otp.consumed_at = now
            otp.save(update_fields=["consumed_at"])
            verified_otp = otp

    # Raise exceptions outside the transaction so failed-attempt
    # updates are not rolled back.
    if outcome == "not_found":
        raise OTPNotFound("No active OTP was found.")

    if outcome == "expired":
        raise OTPExpired("Your OTP has expired.")

    if outcome == "invalid":
        raise OTPInvalid("The OTP you entered is incorrect.")

    if outcome == "max_attempts":
        raise OTPMaxAttempts(
            "Maximum verification attempts reached. Please request a new OTP."
        )

    return verified_otp


@transaction.atomic
def issue_otp(user, purpose, recipient, target_value=""):
    """
    Create an OTP and send it through email.

    If email delivery fails, database changes are rolled back,
    preserving the previous OTP.
    """

    otp_record, plain_otp = create_otp(
        user=user,
        purpose=purpose,
        target_value=target_value,
    )

    send_otp_email(
        user=user,
        code=plain_otp,
        purpose=purpose,
        recipient=recipient,
    )

    return otp_record
