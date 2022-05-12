from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from creme.creme_core.models import CremeEntity


class CremeEntityRelatedField(serializers.RelatedField):
    queryset = CremeEntity.objects.all()
    default_error_messages = {
        "required": _("This field is required."),
        "does_not_exist": _('Invalid pk "{pk_value}" - object does not exist.'),
        "incorrect_type": _("Incorrect type. Expected pk value, received {data_type}."),
    }

    def use_pk_only_optimization(self):
        return True

    def to_internal_value(self, data):
        try:
            creme_entity = self.get_queryset().get(pk=data)
            return creme_entity.get_real_entity()
        except ObjectDoesNotExist:
            self.fail("does_not_exist", pk_value=data)
        except (TypeError, ValueError):
            self.fail("incorrect_type", data_type=type(data).__name__)

    def to_representation(self, value):
        return value.pk


class SimpleCremeEntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CremeEntity
        fields = [
            "id",
            "uuid",
            "created",
            "modified",
            "is_deleted",
        ]


class CremeEntitySerializer(SimpleCremeEntitySerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all())

    class Meta(SimpleCremeEntitySerializer.Meta):
        model = CremeEntity
        fields = SimpleCremeEntitySerializer.Meta.fields + [
            "user",
            "description",
        ]
