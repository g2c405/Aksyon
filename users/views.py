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