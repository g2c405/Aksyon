from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveUpdateAPIView, RetrieveAPIView
from rest_framework.views import APIView
from .serializers import RegisterUserSerializer, UserSerializer, PrivilegedAdminMeSerializer, AdminSerializer, AdminUserSerializer, AdminUserUpdateSerializer, AdminMeSerializer, AdminCreateSerializer, AdminUpdateSerializer
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
User = get_user_model()
from .permissions import IsUser, IsAdmin, IsPrivilegedAdmin
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render
from .utils import (
    generate_password_reset_token,
    generate_email_change_token,
    generate_contact_number_change_token
)
from django.core import signing
import resend
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .serializers import ChangePasswordSerializer, ChangeEmailSerializer, ChangeContactNumberSerializer
from .serializers import AdminCreateSerializer
from core.choices import Role
from notifications.services import create_notification
# Added for account-change notifications
from django.db import transaction
from notifications.models import Notification

from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from .models import User, EmailVerificationOTP
from .serializers import VerifyEmailOTPSerializer
from .otp_services import (
    issue_otp,
    verify_user_otp,
    OTPNotFound,
    OTPExpired,
    OTPInvalid,
    OTPMaxAttempts,
    OTPResendCooldown,
)
from django.utils import timezone
from audit_logs.services import record_activity
def create_account_change_notification(user, event):
    notification_content = {
        "email_changed": {
            "title": "Email Address Changed",
            "message": (
                "Your account email address was successfully changed. "
                "If you didn't make this change, please secure "
                "your account immediately."
            ),
        },
        "contact_changed": {
            "title": "Contact Number Changed",
            "message": (
                "Your account contact number was successfully changed. "
                "If you didn't make this change, please secure "
                "your account immediately."
            ),
        },
        "password_changed": {
            "title": "Password Changed",
            "message": (
                "Your account password was successfully changed. "
                "If you didn't make this change, please secure "
                "your account immediately."
            ),
        },
        "password_reset": {
            "title": "Password Reset Successful",
            "message": (
                "Your password was successfully reset. "
                "If you didn't make this change, please secure "
                "your account immediately."
            ),
        },
    }

    content = notification_content[event]

    return create_notification(
        user=user,
        notification_type="user_warning",
        title=content["title"],
        message=content["message"],
    )


# Create your views here.

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)

        if user.email_verified:
            return Response(
                {"detail": "Email address is already verified."},
                status=status.HTTP_200_OK,
            )

        serializer = VerifyEmailOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"]

        try:
            verify_user_otp(
                user=user,
                purpose=EmailVerificationOTP.Purpose.REGISTRATION,
                submitted_code=code,
            )

        except OTPNotFound:
            return Response(
                {"detail": "No active verification code was found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except OTPExpired:
            return Response(
                {"detail": "Your verification code has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except OTPInvalid:
            return Response(
                {"detail": "The verification code is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except OTPMaxAttempts:
            return Response(
                {
                    "detail": (
                        "Maximum verification attempts reached. "
                        "Please request a new code."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.email_verified = True
        user.save(update_fields=["email_verified"])

        return Response(
            {"detail": "Email address successfully verified."},
            status=status.HTTP_200_OK,
        )

class ResendRegistrationOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)

        if user.email_verified:
            return Response(
                {"detail": "Email address is already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            issue_otp(
                user=user,
                purpose=EmailVerificationOTP.Purpose.REGISTRATION,
                recipient=user.email,
            )

        except OTPResendCooldown as error:
            return Response(
                {
                    "detail": str(error),
                    "retry_after": error.retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(error.retry_after)},
            )

        return Response(
            {"detail": "A new verification code has been sent."},
            status=status.HTTP_200_OK,
        )

class ResendEmailChangeOTPView(APIView):
    permission_classes = [IsUser | IsPrivilegedAdmin]

    def post(self, request):
        otp = (
            EmailVerificationOTP.objects
            .filter(
                user=request.user,
                purpose=EmailVerificationOTP.Purpose.EMAIL_CHANGE,
                consumed_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )

        if not otp or not otp.target_value:
            return Response(
                {"detail": "No pending email change was found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            issue_otp(
                user=request.user,
                purpose=EmailVerificationOTP.Purpose.EMAIL_CHANGE,
                recipient=otp.target_value,
                target_value=otp.target_value,
            )

        except OTPResendCooldown as error:
            return Response(
                {
                    "detail": str(error),
                    "retry_after": error.retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(error.retry_after)},
            )

        return Response(
            {"detail": "A new verification code has been sent."},
            status=status.HTTP_200_OK,
        )



class LoginView(ObtainAuthToken):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(
            username=username,
            password=password,
        )

        if user is None:
            inactive_user = User.objects.filter(
                username=username,
                is_active=False,
            ).first()

            if inactive_user and inactive_user.check_password(password or ""):
                return Response(
                    {
                        "detail": (
                            "Your account has been disabled. "
                            "Please contact your barangay administrator."
                        ),
                        "code": "account_disabled",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.email_verified:
            return Response(
                {
                    "detail": "Please verify your email before logging in."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        token, created = Token.objects.get_or_create(user=user)

        return Response({"token": token.key})


class RegisterView(CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterUserSerializer


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response(
            {"message": "Logout successful."},
            status=status.HTTP_200_OK
        )


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response(
                {"detail": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {
                    "message": (
                        "If an account with that email exists, "
                        "a password reset link has been sent."
                    )
                },
                status=status.HTTP_200_OK,
            )

        token = generate_password_reset_token(user)

        reset_url = (
            f"{settings.BACKEND_URL}/api/users/"
            f"reset-password-page/{user.id}/{token}/"
        )

        resend.api_key = settings.RESEND_API_KEY

        resend.Emails.send({
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [user.email],
            "subject": "Reset your Aksyon password",
            "text": (
                "We received a request to reset your password.\n\n"
                "Open the link below to reset it:\n\n"
                f"{reset_url}\n\n"
                "If you did not request this, you can safely ignore "
                "this email."
            ),
        })

        return Response(
            {
                "message": (
                    "If an account with that email exists, "
                    "a password reset link has been sent."
                )
            },
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    permission_classes = [IsUser | IsAdmin]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            request.user.set_password(
                serializer.validated_data["new_password"]
            )

            request.user.save(
                update_fields=["password"]
            )

            create_account_change_notification(
                request.user,
                "password_changed",
            )

        return Response(
            {
                "detail": "Password changed successfully."
            },
            status=status.HTTP_200_OK,
        )


class ChangeEmailView(APIView):
    permission_classes = [IsUser | IsPrivilegedAdmin]

    def post(self, request):
        serializer = ChangeEmailSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        new_email = serializer.validated_data["new_email"]

        try:
            issue_otp(
                user=request.user,
                purpose=EmailVerificationOTP.Purpose.EMAIL_CHANGE,
                recipient=new_email,
                target_value=new_email,
            )

        except OTPResendCooldown as error:
            return Response(
                {
                    "detail": str(error),
                    "retry_after": error.retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(error.retry_after)},
            )

        return Response(
            {
                "detail": (
                    "A verification code has been sent to your new email address."
                )
            },
            status=status.HTTP_200_OK,
        )

class VerifyEmailChangeView(APIView):
    permission_classes = [IsUser | IsPrivilegedAdmin]

    def post(self, request):
        serializer = VerifyEmailOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"]

        try:
            otp = verify_user_otp(
                user=request.user,
                purpose=EmailVerificationOTP.Purpose.EMAIL_CHANGE,
                submitted_code=code,
            )

        except OTPNotFound:
            return Response(
                {"detail": "No active verification code was found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except OTPExpired:
            return Response(
                {"detail": "Your verification code has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except OTPInvalid:
            return Response(
                {"detail": "The verification code is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except OTPMaxAttempts:
            return Response(
                {
                    "detail": (
                        "Maximum verification attempts reached. "
                        "Please request a new code."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_email = otp.target_value

        if not new_email:
            return Response(
                {"detail": "The verification request is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(email__iexact=new_email).exclude(
            pk=request.user.pk
        ).exists():
            return Response(
                {"detail": "This email address is already in use."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.email = new_email
        request.user.save(update_fields=["email"])

        create_account_change_notification(
            request.user,
            "email_changed",
        )

        return Response(
            {"detail": "Email address successfully updated."},
            status=status.HTTP_200_OK,
        )

class ChangeContactNumberView(APIView):
    permission_classes = [IsUser | IsPrivilegedAdmin]

    def post(self, request):
        serializer = ChangeContactNumberSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        new_contact_number = serializer.validated_data["new_contact_number"]

        if not request.user.email:
            return Response(
                {"detail": "Your account does not have a registered email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(
            contact_number=new_contact_number
        ).exclude(pk=request.user.pk).exists():
            return Response(
                {"detail": "This contact number is already in use."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            issue_otp(
                user=request.user,
                purpose=EmailVerificationOTP.Purpose.CONTACT_CHANGE,
                recipient=request.user.email,
                target_value=new_contact_number,
            )

        except OTPResendCooldown as error:
            return Response(
                {
                    "detail": str(error),
                    "retry_after": error.retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(error.retry_after)},
            )

        return Response(
            {
                "detail": (
                    "A verification code has been sent to your registered email address."
                )
            },
            status=status.HTTP_200_OK,
        )

class VerifyContactNumberChangeView(APIView):
    permission_classes = [IsUser | IsPrivilegedAdmin]

    def post(self, request):
        serializer = VerifyEmailOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"]

        try:
            otp = verify_user_otp(
                user=request.user,
                purpose=EmailVerificationOTP.Purpose.CONTACT_CHANGE,
                submitted_code=code,
            )

        except OTPNotFound:
            return Response(
                {"detail": "No active verification code was found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except OTPExpired:
            return Response(
                {"detail": "Your verification code has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except OTPInvalid:
            return Response(
                {"detail": "The verification code is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except OTPMaxAttempts:
            return Response(
                {
                    "detail": (
                        "Maximum verification attempts reached. "
                        "Please request a new code."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_contact_number = otp.target_value

        if not new_contact_number:
            return Response(
                {"detail": "The verification request is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(
            contact_number=new_contact_number
        ).exclude(pk=request.user.pk).exists():
            return Response(
                {"detail": "This contact number is already in use."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.contact_number = new_contact_number
        request.user.save(update_fields=["contact_number"])

        create_account_change_notification(
            request.user,
            "contact_changed",
        )

        return Response(
            {"detail": "Contact number successfully updated."},
            status=status.HTTP_200_OK,
        )

class ResendContactNumberChangeOTPView(APIView):
    permission_classes = [IsUser | IsPrivilegedAdmin]

    def post(self, request):
        otp = (
            EmailVerificationOTP.objects
            .filter(
                user=request.user,
                purpose=EmailVerificationOTP.Purpose.CONTACT_CHANGE,
            )
            .order_by("-created_at")
            .first()
        )

        if not otp or otp.consumed_at is not None or not otp.target_value:
            return Response(
                {"detail": "No pending contact number change was found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not request.user.email:
            return Response(
                {"detail": "Your account does not have a registered email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            issue_otp(
                user=request.user,
                purpose=EmailVerificationOTP.Purpose.CONTACT_CHANGE,
                recipient=request.user.email,
                target_value=otp.target_value,
            )

        except OTPResendCooldown as error:
            return Response(
                {
                    "detail": str(error),
                    "retry_after": error.retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(error.retry_after)},
            )

        return Response(
            {"detail": "A new verification code has been sent."},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        user_id = request.data.get("user_id")
        token = request.data.get("token")
        new_password = request.data.get("new_password")

        if not user_id or not token or not new_password:
            return Response(
                {"detail": "Required fields are missing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "Invalid password reset request."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(
            user,
            token,
        ):
            return Response(
                {
                    "detail": (
                        "This password reset link is invalid "
                        "or has expired."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response(
                {"detail": e.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            user.set_password(new_password)

            user.save(
                update_fields=["password"]
            )

            create_account_change_notification(
                user,
                "password_reset",
            )

        return Response(
            {
                "message": "Password has been reset successfully."
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetPageView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, user_id, token):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return render(
                request,
                "users/password_reset.html",
                {
                    "success": False,
                    "invalid_link": True,
                    "message": "This password reset link is invalid.",
                },
                status=400,
            )

        if not default_token_generator.check_token(user, token):
            return render(
                request,
                "users/password_reset.html",
                {
                    "success": False,
                    "invalid_link": True,
                    "message": (
                        "This password reset link is invalid "
                        "or has expired. Please request a new one."
                    ),
                },
                status=400,
            )

        return render(
            request,
            "users/password_reset.html",
            {
                "success": False,
                "invalid_link": False,
            },
        )

    def post(self, request, user_id, token):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return render(
                request,
                "users/password_reset.html",
                {
                    "success": False,
                    "invalid_link": True,
                    "message": "This password reset link is invalid.",
                },
                status=400,
            )

        if not default_token_generator.check_token(user, token):
            return render(
                request,
                "users/password_reset.html",
                {
                    "success": False,
                    "invalid_link": True,
                    "message": (
                        "This password reset link is invalid "
                        "or has expired. Please request a new one."
                    ),
                },
                status=400,
            )

        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not new_password or not confirm_password:
            message = "Please fill in both password fields."
        elif new_password != confirm_password:
            message = "The passwords do not match."
        else:
            try:
                validate_password(new_password, user)
            except ValidationError as error:
                message = " ".join(error.messages)
            else:
                with transaction.atomic():
                    user.set_password(new_password)

                    user.save(
                        update_fields=["password"]
                    )

                    create_account_change_notification(
                        user,
                        "password_reset",
                    )

                return render(
                    request,
                    "users/password_reset.html",
                    {"success": True},
                )

        return render(
            request,
            "users/password_reset.html",
            {
                "success": False,
                "invalid_link": False,
                "message": message,
            },
            status=400,
        )


class MeView(RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.user.role == Role.ADMIN:
            return AdminMeSerializer
        elif self.request.user.role == Role.PRIVILEGED_ADMIN:
            return PrivilegedAdminMeSerializer
        return UserSerializer


class AdminUserListView(ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        return User.objects.filter(
            residential_barangay=self.request.user.assigned_barangay
        ).order_by("-date_joined")



class AdminUserView(RetrieveUpdateAPIView):
    permission_classes = [IsAdmin]

    def get_queryset(self):
        return User.objects.filter(
            residential_barangay=self.request.user.assigned_barangay
        )

    @transaction.atomic
    def perform_update(self, serializer):
        instance = serializer.instance

        old_values = {
            "is_active": instance.is_active,
            "email": instance.email,
            "suspension_reason": instance.suspension_reason,
            "suspension_detail": instance.suspension_detail,
            "suspension_notes": instance.suspension_notes,
        }

        user = serializer.save()

        changes = {}

        # Track account activation status.
        if old_values["is_active"] != user.is_active:
            changes["is_active"] = {
                "from": old_values["is_active"],
                "to": user.is_active,
            }

        # Track email changes.
        if old_values["email"] != user.email:
            changes["email"] = {
                "from": old_values["email"],
                "to": user.email,
            }

        # Track suspension-related changes.
        for field in (
            "suspension_reason",
            "suspension_detail",
            "suspension_notes",
        ):
            old_value = old_values[field]
            new_value = getattr(user, field)

            if old_value != new_value:
                changes[field] = {
                    "from": old_value,
                    "to": new_value,
                }

        # Do not create logs for unchanged submissions.
        if not changes:
            return

        # Determine the appropriate audit action.
        if old_values["is_active"] and not user.is_active:
            action = "RESIDENT_ACCOUNT_SUSPENDED"
            description = (
                f"Suspended resident account {user.username}"
            )

        elif not old_values["is_active"] and user.is_active:
            action = "RESIDENT_ACCOUNT_REACTIVATED"
            description = (
                f"Reactivated resident account {user.username}"
            )

        else:
            action = "RESIDENT_ACCOUNT_UPDATED"
            description = (
                f"Updated resident account {user.username}"
            )

        record_activity(
            actor=self.request.user,
            action=action,
            target_type="User",
            target_id=user.id,
            description=description,
            changes=changes,
        )



class AdminCreateView(CreateAPIView):
    permission_classes = [IsPrivilegedAdmin]
    serializer_class = AdminCreateSerializer


class AdminListView(ListAPIView):
    queryset = User.objects.filter(
        role=Role.ADMIN
    ).order_by("-date_joined")

    permission_classes = [IsPrivilegedAdmin]
    serializer_class = AdminSerializer


class AdminRetrieveUpdateView(RetrieveUpdateAPIView):
    queryset = User.objects.filter(
        role=Role.ADMIN
    )

    permission_classes = [IsPrivilegedAdmin]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return AdminUpdateSerializer

        return AdminSerializer