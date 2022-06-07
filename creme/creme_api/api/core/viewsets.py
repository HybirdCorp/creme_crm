from django.db.models import ProtectedError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from creme.creme_api.api.core.exceptions import UnprocessableEntity

from .serializers import SimpleCremeEntitySerializer


class CremeModelViewSet(viewsets.ModelViewSet):
    LOCK_METHODS = {"POST", "PUT" "PATCH"}

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as exc:
            raise UnprocessableEntity(str(exc), code="protected")

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.method in self.LOCK_METHODS:
            return queryset.select_for_update()
        return queryset


class CremeEntityViewSet(CremeModelViewSet):
    @action(methods=["post"], detail=True, serializer_class=SimpleCremeEntitySerializer)
    def trash(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            instance.trash()
        except ProtectedError as exc:
            raise UnprocessableEntity(str(exc), code="protected")

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(methods=["post"], detail=True, serializer_class=SimpleCremeEntitySerializer)
    def restore(self, request, *args, **kwargs):
        instance = self.get_object()

        instance.restore()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(methods=["post"], detail=True)
    def clone(self, request, *args, **kwargs):
        instance = self.get_object()

        new = instance.clone()

        serializer = self.get_serializer(new)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
