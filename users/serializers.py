from rest_framework import serializers
from django.contrib.auth import get_user_model
User = get_user_model()
from django.contrib.auth.password_validation import validate_password
from .utils import generate_email_verification_token
import resend
from django.conf import settings
from django.db import transaction
from django.core.exceptions import ValidationError
from core.choices import Role

from django.utils import timezone
from django.db import transaction
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from core.choices import (
    Role,
    AccountSuspensionReason,
    AccountSuspensionDetail,
)
from notifications.models import Notification

SUSPENSION_DETAILS_BY_REASON = {
    AccountSuspensionReason.INAPPROPRIATE_USER_INFORMATION: {
        AccountSuspensionDetail.INAPPROPRIATE_FIRST_NAME,
        AccountSuspensionDetail.INAPPROPRIATE_LAST_NAME,
        AccountSuspensionDetail.INAPPROPRIATE_USERNAME,
        AccountSuspensionDetail.INAPPROPRIATE_PROFILE_INFORMATION,
        AccountSuspensionDetail.FALSE_CONTACT_INFORMATION,
        AccountSuspensionDetail.OTHER_DETAIL,
    },
    AccountSuspensionReason.REPORTING_SYSTEM_ABUSE: {
        AccountSuspensionDetail.FALSE_REPORTS,
        AccountSuspensionDetail.MISLEADING_DESCRIPTIONS,
        AccountSuspensionDetail.SPAM_OR_DUPLICATE_REPORTS,
        AccountSuspensionDetail.REPORT_LOCATION_MISUSE,
        AccountSuspensionDetail.OTHER_DETAIL,
    },
    AccountSuspensionReason.INAPPROPRIATE_CONTENT: {
        AccountSuspensionDetail.PROFANITY_OR_ABUSE,
        AccountSuspensionDetail.INAPPROPRIATE_MEDIA,
        AccountSuspensionDetail.HARASSMENT_OR_THREATS,
        AccountSuspensionDetail.OTHER_DETAIL,
    },
    AccountSuspensionReason.REPEATED_POLICY_VIOLATIONS: {
        AccountSuspensionDetail.REPEATED_GUIDELINE_VIOLATIONS,
        AccountSuspensionDetail.OTHER_DETAIL,
    },
    AccountSuspensionReason.OTHER: {
        AccountSuspensionDetail.OTHER_DETAIL,
    },
}

class AccountStatusUpdateMixin:
    def validate(self, attrs):
        attrs = super().validate(attrs)

        instance = self.instance
        new_is_active = attrs.get("is_active", instance.is_active)

        # Only require a reason when an active account is being disabled.
        if instance.is_active and new_is_active is False:
            reason = attrs.get("suspension_reason")
            detail = attrs.get("suspension_detail")
            notes = attrs.get("suspension_notes", "").strip()

            if not reason:
                raise serializers.ValidationError({
                    "suspension_reason": (
                        "A suspension reason is required."
                    )
                })

            if not detail:
                raise serializers.ValidationError({
                    "suspension_detail": (
                        "A specific suspension reason is required."
                    )
                })

            allowed_details = SUSPENSION_DETAILS_BY_REASON.get(reason, set())

            if detail not in allowed_details:
                raise serializers.ValidationError({
                    "suspension_detail": (
                        "This specific reason does not belong "
                        "to the selected primary reason."
                    )
                })

            if detail == AccountSuspensionDetail.OTHER_DETAIL and not notes:
                raise serializers.ValidationError({
                    "suspension_notes": (
                        "Please explain the reason when selecting Other."
                    )
                })

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        was_active = instance.is_active
        will_be_active = validated_data.get("is_active", was_active)

        # Ignore suspension fields when the account is not being disabled.
        if not was_active or will_be_active is not False:
            validated_data.pop("suspension_reason", None)
            validated_data.pop("suspension_detail", None)
            validated_data.pop("suspension_notes", None)

        if was_active and will_be_active is False:
            validated_data["suspended_at"] = timezone.now()
            validated_data["reactivated_at"] = None

        elif not was_active and will_be_active is True:
            validated_data["suspension_reason"] = ""
            validated_data["suspension_detail"] = ""
            validated_data["suspension_notes"] = ""
            validated_data["reactivated_at"] = timezone.now()

        instance = super().update(instance, validated_data)

        if was_active and not instance.is_active:
            # Invalidate the user's DRF token.
            Token.objects.filter(user=instance).delete()

            reason_label = instance.get_suspension_reason_display()
            detail_label = instance.get_suspension_detail_display()
            notes = instance.suspension_notes.strip()

            message = (
                f"Your Aksyon account has been disabled. "
                f"Reason: {reason_label}. "
                f"Details: {detail_label}."
            )

            if notes:
                message += f" Explanation: {notes}"

            Notification.objects.create(
                user=instance,
                notification_type="user_warning",
                title="Aksyon account disabled",
                message=message,
            )

        elif not was_active and instance.is_active:
            Notification.objects.create(
                user=instance,
                notification_type="user_warning",
                title="Aksyon account re-enabled",
                message=(
                    "Your Aksyon account has been re-enabled. "
                    "You can now log in again."
                ),
            )

        return instance




class RegisterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "contact_number",
            "residential_barangay",
        )

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(**validated_data)

            token = generate_email_verification_token(user)

            verification_url = (
                f"{settings.BACKEND_URL}/api/users/"
                f"verify-email/{user.id}/{token}/"
            )

            resend.api_key = settings.RESEND_API_KEY

            resend.Emails.send({
                "from": settings.DEFAULT_FROM_EMAIL,
                "to": [user.email],
                "subject": "Verify your email",
                "text": (
                    "Welcome!\n\n"
                    "Please verify your email by opening the link below:\n\n"
                    f"{verification_url}\n\n"
                    "You must verify your email before you can log in."
                ),
            })

            return user
class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True,
        required=True,
    )

    new_password = serializers.CharField(
        write_only=True,
        required=True,
    )

    def validate(self, attrs):
        user = self.context["request"].user

        current_password = attrs["current_password"]
        new_password = attrs["new_password"]

        if not user.check_password(current_password):
            raise serializers.ValidationError(
                {
                    "current_password": (
                        "Current password is incorrect."
                    )
                }
            )
        if current_password == new_password:
            raise serializers.ValidationError(
                {
                    "new_password": (
                        "New password must be different "
                        "from your current password."
                    )
                }
            )

        try:
            validate_password(
                new_password,
                user=user,
            )
        except ValidationError as error:
            raise serializers.ValidationError(
                {
                    "new_password": error.messages
                }
            )

        return attrs

class ChangeEmailSerializer(serializers.Serializer):
    new_email = serializers.EmailField(
        required=True,
    )

    def validate_new_email(self, value):
        user = self.context["request"].user

        if value.lower() == user.email.lower():
            raise serializers.ValidationError(
                "New email must be different from your current email."
            )

        if User.objects.filter(
            email__iexact=value
        ).exclude(
            pk=user.pk
        ).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )

        return value

class ChangeContactNumberSerializer(serializers.Serializer):
    contact_number = serializers.CharField(
        required=True,
        max_length=20,
        trim_whitespace=True,
    )

    def validate_contact_number(self, value):
        user = self.context["request"].user

        if not value:
            raise serializers.ValidationError(
                "Contact number is required."
            )

        if value == user.contact_number:
            raise serializers.ValidationError(
                "New contact number must be different "
                "from your current contact number."
            )

        return value

class AdminCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "contact_number",
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
            role=Role.ADMIN,
            email_verified=True,
        )

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name','last_name','username','email', 'contact_number', 'residential_barangay')

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "username",
            "email",
            "contact_number",
            "residential_barangay",
            "is_active",
            "suspension_reason",
            "suspension_detail",
            "suspension_notes",
            "suspended_at",
            "reactivated_at",
            "date_joined",
        )
class AdminUserUpdateSerializer(
    AccountStatusUpdateMixin,
    serializers.ModelSerializer,
):
    class Meta:
        model = User
        fields = (
            "email",
            "is_active",
            "suspension_reason",
            "suspension_detail",
            "suspension_notes",
        )
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

class AdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "username",
            "email",
            "contact_number",
            "assigned_barangay",
            "role",
            "is_active",
            "suspension_reason",
            "suspension_detail",
            "suspension_notes",
            "suspended_at",
            "reactivated_at",
            "date_joined",
        )

class AdminUpdateSerializer(
    AccountStatusUpdateMixin,
    serializers.ModelSerializer,
):
    class Meta:
        model = User
        fields = (
            "email",
            "is_active",
            "contact_number",
            "assigned_barangay",
            "suspension_reason",
            "suspension_detail",
            "suspension_notes",
        )

class PrivilegedAdminMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'contact_number',
            'role',
        )
