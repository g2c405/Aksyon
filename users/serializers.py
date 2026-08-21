from rest_framework import serializers
from django.contrib.auth import get_user_model
User = get_user_model()
from django.contrib.auth.password_validation import validate_password
from .utils import generate_email_verification_token
from django.core.mail import send_mail
from django.conf import settings
class RegisterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'password',
            'contact_number',
            'residential_barangay')

    def validate_password(self, value):
        validate_password(value)
        return value
    def create(self, validated_data):
       user = User.objects.create_user(**validated_data)
       token = generate_email_verification_token(user)
       verification_url = (
            f"http://api.aksyon.online/api/users/"
            f"verify-email/{user.id}/{token}/"
        )
       send_mail(
           subject="Verify your email",
           message=(
                "Welcome!\n\n"
                "Please verify your email by opening the link below:\n\n"
                f"{verification_url}\n\n"
                "You must verify your email before you can log in."),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
       return user


class AdminRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    class Meta:
        model = User
        fields = (
            "username",
            "email",
            'first_name',
            'last_name',
            "password",
            'contact_number',
            "assigned_barangay",
        )

    def validate_password(self, value):
            validate_password(value)
            return value

    def validate(self, attrs):
        if not attrs.get("assigned_barangay"):
            raise serializers.ValidationError({
                "assigned_barangay":
                    "An admin must be assigned to a barangay."
            })

        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            **validated_data,
            role=User.Role.ADMIN,
        )

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name','last_name','username','email', 'contact_number', 'residential_barangay')

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'username', 'email', 'contact_number', 'residential_barangay', 'is_active', 'date_joined')

class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'is_active')  # keep it limited

class AdminMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'contact_number',
            'assigned_barangay',
        )