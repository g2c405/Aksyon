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
)
from django.core import signing
import resend
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .serializers import ChangePasswordSerializer, ChangeEmailSerializer, ChangeContactNumberSerializer
from .serializers import AdminCreateSerializer
from core.choices import Role
# Create your views here.

class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request, user_id, token):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return render(
                request,
                "users/email_verification.html",
                {
                    "success": False,
                    "message": "This verification link is invalid.",
                },
                status=400,
            )

        if user.email_verified:
            return render(
                request,
                "users/email_verification.html",
                {
                    "success" : False,
                    "message" : "This email is already verified."
                },
                status=400,
            )

        if not default_token_generator.check_token(
            user,
            token,
        ):
            return render(
                request,
                "users/email_verification.html",
                {
                    "success" : False,
                    "message" : "This verification link is invalid or has expired."
                },
                status=400,
            )

        user.email_verified = True
        user.save(update_fields=["email_verified"])

        return render(
            request,
            "users/email_verification.html",
            {
                "success" : True
            },
            status=200,
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

        token, created = Token.objects.get_or_create(
            user=user
        )

        return Response({
            "token": token.key,
        })


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
    permission_classes = [IsUser]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        request.user.set_password(
            serializer.validated_data["new_password"]
        )

        request.user.save(
            update_fields=["password"]
        )

        return Response(
            {
                "detail": "Password changed successfully."
            },
            status=status.HTTP_200_OK,
        )

class ChangeEmailView(APIView):
    permission_classes = [IsUser]

    def post(self, request):
        serializer = ChangeEmailSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        new_email = serializer.validated_data["new_email"]

        token = generate_email_change_token(
            request.user,
            new_email,
        )

        verification_url = (
            f"{settings.BACKEND_URL}/api/users/"
            f"verify-email-change/{token}/"
        )

        resend.api_key = settings.RESEND_API_KEY

        resend.Emails.send({
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [new_email],
            "subject": "Verify your new email address",
            "text": (
                "You requested to change the email address "
                "associated with your Aksyon account.\n\n"
                "Please verify your new email address by opening "
                "the link below:\n\n"
                f"{verification_url}\n\n"
                "Your current email address will remain unchanged "
                "until you complete this verification."
            ),
        })

        return Response(
            {
                "message": (
                    "A verification link has been sent to your "
                    "new email address."
                )
            },
            status=status.HTTP_200_OK,
        )

class VerifyEmailChangeView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        try:
            data = signing.loads(
                token,
                salt="email-change",
                max_age=3600,
            )
        except signing.BadSignature:
            return render(
                request,
                "users/email_verification.html",
                {
                    "success": False,
                    "message": (
                        "This email change link is invalid "
                        "or has expired."
                    ),
                },
                status=400,
            )

        try:
            user = User.objects.get(
                pk=data["user_id"]
            )
        except User.DoesNotExist:
            return render(
                request,
                "users/email_verification.html",
                {
                    "success": False,
                    "message": "This verification link is invalid.",
                },
                status=400,
            )

        new_email = data["new_email"]

        if User.objects.filter(
            email__iexact=new_email
        ).exclude(
            pk=user.pk
        ).exists():
            return render(
                request,
                "users/email_verification.html",
                {
                    "success": False,
                    "message": (
                        "This email address is already associated "
                        "with another account."
                    ),
                },
                status=400,
            )

        user.email = new_email

        user.save(
            update_fields=["email"]
        )

        return render(
            request,
            "users/email_verification.html",
            {
                "success": True,
                "message": (
                    "Your email address has been changed successfully."
                ),
            },
            status=200,
        )

class ChangeContactNumberView(APIView):
    permission_classes = [IsUser]

    def post(self, request):
        serializer = ChangeContactNumberSerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        request.user.contact_number = (
            serializer.validated_data["contact_number"]
        )

        request.user.save(
            update_fields=["contact_number"]
        )

        return Response(
            {
                "message": (
                    "Contact number changed successfully."
                )
            },
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

        user.set_password(new_password)
        user.save(update_fields=["password"])

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
                user.set_password(new_password)
                user.save(update_fields=["password"])

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
    queryset = User.objects.all()
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return AdminUserUpdateSerializer
        return AdminUserSerializer

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