
from rest_framework import serializers
from .models import EmergencyUnit


class EmergencyUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyUnit
        fields = "__all__"
