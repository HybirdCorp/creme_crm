
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers


class ContentTypeSerializer(serializers.ModelSerializer):
    """Readonly"""
    class Meta:
        model = ContentType
        fields = [
            "id",
            "app_label",
            "model",
        ]
