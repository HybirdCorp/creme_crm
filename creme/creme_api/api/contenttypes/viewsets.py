from rest_framework import viewsets
from rest_framework.schemas.openapi import AutoSchema

from .serializers import ContentTypeSerializer
from .utils import get_cremeentity_contenttype_queryset


class ContentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    retrieve:
    Retrieve a content type.

    list:
    List content types.
    """

    queryset = None
    serializer_class = ContentTypeSerializer
    schema = AutoSchema(tags=["Content Types"])

    def get_queryset(self):
        return get_cremeentity_contenttype_queryset()
