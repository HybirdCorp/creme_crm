from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from creme.creme_api.models import Application


class TokenSerializer(serializers.Serializer):
    default_error_messages = {
        'authentication_failure': _('Unable to log in with provided credentials.')
    }

    client_id = serializers.UUIDField(
        label=_("Client ID"),
        write_only=True
    )
    client_secret = serializers.CharField(
        label=_("Client secret"),
        style={'input_type': 'password'},
        write_only=True
    )
    token = serializers.CharField(
        label=_("Token"),
        read_only=True
    )

    def validate(self, attrs):
        client_id = attrs["client_id"]
        client_secret = attrs["client_secret"]

        application = Application.authenticate(
            client_id, client_secret,
            request=self.context['request'],
        )
        if not application:
            self.fail('authentication_failure')

        attrs['application'] = application

        return attrs
