from rest_framework import mixins, parsers, renderers, viewsets
from rest_framework.response import Response

from creme.creme_api.api.schemas import CremeSchema
from creme.creme_api.models import Token

from .serializers import TokenSerializer


class TokenViewSet(mixins.CreateModelMixin,
                   viewsets.GenericViewSet):
    """
    create:
    Create a token.

    """
    throttle_classes = []
    permission_classes = []
    parser_classes = [
        parsers.FormParser,
        parsers.MultiPartParser,
        parsers.JSONParser,
    ]
    renderer_classes = [
        renderers.JSONRenderer,
    ]
    serializer_class = TokenSerializer
    schema = CremeSchema(tags=["Tokens"])

    # TODO: revoke_token ?
    # TODO: introspect ?

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.validated_data['application']
        token = Token.objects.create(application=application)
        return Response({'token': token.code})
