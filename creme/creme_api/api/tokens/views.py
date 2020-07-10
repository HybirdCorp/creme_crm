from rest_framework import parsers, renderers
from rest_framework.response import Response
from rest_framework.views import APIView

from creme.creme_api.api.schemas import CremeSchema
from creme.creme_api.models import Token

from .serializers import TokenSerializer


class TokenView(APIView):
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

    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }

    def get_serializer(self, *args, **kwargs):
        kwargs['context'] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.validated_data['application']
        token = Token.objects.create(application=application)
        return Response({'token': token.code})
