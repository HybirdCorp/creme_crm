from django.apps import apps
from rest_framework import serializers


class ContentTypeSerializer(serializers.BaseSerializer):
    def to_representation(self, contenttype):
        model = contenttype.model_class()
        app_config = apps.get_app_config(contenttype.app_label)
        return {
            "id": contenttype.id,
            "name": model._meta.verbose_name_plural,
            "application": app_config.verbose_name,
        }
