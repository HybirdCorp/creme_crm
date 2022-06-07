from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.authentication import (
    BaseAuthentication,
    get_authorization_header,
)

from creme.creme_api.models import Token


class TokenAuthentication(BaseAuthentication):
    """
    Token based authentication
    """

    keyword = "token"
    errors = {
        "empty": _("Invalid token header. No credentials provided."),
        "too_long": _("Invalid token header. Token string should not contain spaces."),
        "encoding": _(
            "Invalid token header. Token string should not contain invalid characters."
        ),
        "invalid": _("Incorrect authentication credentials."),
        "expired": _("Incorrect authentication credentials. Token has expired."),
    }

    def authentication_failure(self, code):
        return exceptions.AuthenticationFailed(detail=self.errors[code], code=code)

    def authenticate(self, request):
        request.token = None
        request.application = None

        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            raise self.authentication_failure("empty")
        elif len(auth) > 2:
            raise self.authentication_failure("too_long")

        try:
            token_code = auth[1].decode()
        except UnicodeError:
            raise self.authentication_failure("encoding")

        try:
            token = Token.objects.select_related("application").get(code=token_code)
        except Token.DoesNotExist:
            raise self.authentication_failure("invalid")

        if not token.application.can_authenticate(request=request):
            raise self.authentication_failure("invalid")

        if token.is_expired():
            raise self.authentication_failure("expired")

        request.token = token
        request.application = token.application

        return token.user, token

    def authenticate_header(self, request):
        return self.keyword
