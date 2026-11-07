from django.contrib.auth.tokens import default_token_generator
from django.core import signing
import secrets
from django.contrib.auth.hashers import make_password, check_password

def generate_email_verification_token(user):
    return default_token_generator.make_token(user)


def generate_password_reset_token(user):
    return default_token_generator.make_token(user)


def generate_email_change_token(user, new_email):
    return signing.dumps(
        {
            "user_id": user.id,
            "new_email": new_email,
        },
        salt="email-change",
    )

from django.core import signing


def generate_contact_number_change_token(user, new_contact_number):
    return signing.dumps(
        {
            "user_id": user.pk,
            "new_contact_number": new_contact_number,
        },
        salt="contact-number-change",
    )

def generate_otp():
    """
    Generate a cryptographically secure 6-digit numeric OTP.
    Leading zeroes are preserved.
    """
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(code):
    """
    Hash an OTP before storing it in the database.
    """
    return make_password(code)


def verify_otp(code, code_hash):
    """
    Check whether the submitted OTP matches its stored hash.
    """
    return check_password(code, code_hash)
