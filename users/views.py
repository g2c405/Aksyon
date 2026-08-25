from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveUpdateAPIView, RetrieveAPIView
from rest_framework.views import APIView
from .serializers import RegisterUserSerializer, UserSerializer, AdminUserSerializer, AdminUserUpdateSerializer, AdminMeSerializer
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
from .utils import generate_password_reset_token
import resend
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .serializers import ChangePasswordSerializer
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
            f"aksyon://reset-password/"
            f"{user.id}/{token}"
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

class MeView(RetrieveAPIView):
    permission_classes = [IsUser]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.user.is_staff:
            return AdminMeSerializer
        return UserSerializer


class AdminUserListView(ListAPIView):
    queryset = User.objects.all().order_by('-date_joined')
    permission_classes = [IsAdmin]
    serializer_class = AdminUserSerializer

class AdminUserView(RetrieveUpdateAPIView):
    queryset = User.objects.all()
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return AdminUserUpdateSerializer
        return AdminUserSerializer