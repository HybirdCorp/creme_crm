from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from creme.creme_core.core.exceptions import SpecificProtectedError

from .serializers import SimpleCremeEntitySerializer


class CremeModelViewSet(viewsets.ModelViewSet):
    LOCK_METHODS = {'POST', 'PUT' 'PATCH'}

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except SpecificProtectedError as exc:
            raise ValidationError(str(exc))

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.method in self.LOCK_METHODS:
            return queryset.select_for_update()
        return queryset


class CremeEntityViewSet(CremeModelViewSet):

    @action(methods=['post'], detail=True, serializer_class=SimpleCremeEntitySerializer)
    def trash(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            instance.trash()
        except SpecificProtectedError as exc:
            raise ValidationError(str(exc))

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(methods=['post'], detail=True, serializer_class=SimpleCremeEntitySerializer)
    def restore(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            instance.restore()
        except SpecificProtectedError as exc:
            raise ValidationError(str(exc))

        serializer = self.get_serializer(instance)
        return Response(serializer.data)
