from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from creme.creme_api.models import Application


class TokenSerializer(serializers.Serializer):
    default_error_messages = {
        "authentication_failure": _("Unable to log in with provided credentials.")
    }

    application_id = serializers.UUIDField(label=_("Application ID"), write_only=True)
    application_secret = serializers.CharField(
        label=_("Application secret"), style={"input_type": "password"}, write_only=True
    )

    token = serializers.CharField(label=_("Token"), read_only=True)
    token_type = serializers.CharField(label=_("Token type"), read_only=True)
    expires_in = serializers.IntegerField(label=_("Expires in"), read_only=True)

    def validate(self, attrs):
        application_id = attrs["application_id"]
        application_secret = attrs["application_secret"]

        application = Application.authenticate(
            application_id,
            application_secret,
            request=self.context["request"],
        )
        if not application:
            self.fail("authentication_failure")

        attrs["application"] = application

        return attrs
