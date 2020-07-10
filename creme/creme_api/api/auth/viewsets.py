from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from creme.creme_api.api.schemas import CremeSchema
from creme.creme_core.models import SetCredentials, UserRole

from .serializers import (
    DeleteUserSerializer,
    PasswordSerializer,
    SetCredentialsCreateSerializer,
    SetCredentialsSerializer,
    TeamSerializer,
    UserRoleSerializer,
    UserSerializer,
)

CremeUser = get_user_model()


class UserViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  # mixins.DestroyModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    """
    create:
    POST /users

    retrieve:
    GET /users/{userId}

    update:
    PUT /users/{userId}

    partial_update:
    PATCH /users/{userId}

    list:
    GET /users

    """
    queryset = CremeUser.objects.filter(is_team=False, is_staff=False)
    serializer_class = UserSerializer
    schema = CremeSchema(tags=["Users"], operation_id_base="Users")

    @action(methods=['post'], detail=True, serializer_class=PasswordSerializer)
    def set_password(self, request, pk):
        """
        post:
        POST /users/{userId}/set_password
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(
        methods=['post'],
        detail=True,
        serializer_class=DeleteUserSerializer,
        url_path="delete",
        url_name="delete",
        name="delete",
    )
    def _delete(self, request, pk):
        """
        post:
        POST /users/{userId}/delete
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TeamViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  # mixins.DestroyModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    """
    create:
    POST /teams

    retrieve:
    GET /teams/{teamId}

    update:
    PUT /teams/{teamId}

    partial_update:
    PATCH /teams/{teamId}

    list:
    GET /teams

    """
    queryset = CremeUser.objects.filter(is_team=True, is_staff=False)
    serializer_class = TeamSerializer
    schema = CremeSchema(tags=["Teams"], operation_id_base="Teams")

    @action(
        methods=['post'],
        detail=True,
        serializer_class=DeleteUserSerializer,
        url_path="delete",
        url_name="delete",
        name="delete",
    )
    def _delete(self, request, pk):
        """
        post:
        POST /teams/{teamId}/delete
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserRoleViewSet(mixins.CreateModelMixin,
                      mixins.RetrieveModelMixin,
                      mixins.UpdateModelMixin,
                      mixins.DestroyModelMixin,
                      mixins.ListModelMixin,
                      viewsets.GenericViewSet):
    """

    create:
    POST /roles

    retrieve:
    GET /roles/{roleId}

    update:
    PUT /roles/{roleId}

    partial_update:
    PATCH /roles/{roleId}

    destroy:
    DELETE /roles/{roleId}

    list:
    GET /roles

    """
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer
    schema = CremeSchema(tags=["Roles"])

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as e:
            raise PermissionDenied(e.args[0]) from e


class SetCredentialsViewSet(mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin,
                            mixins.DestroyModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    """

    create:
    POST /credentials

    retrieve:
    GET /credentials/{credentialId}

    update:
    PUT /credentials/{credentialId}

    partial_update:
    PATCH /credentials/{credentialId}

    destroy:
    DELETE /credentials/{credentialId}

    list:
    GET /credentials

    """
    queryset = SetCredentials.objects.all()
    serializer_class = SetCredentialsSerializer
    schema = CremeSchema(tags=["Credentials"])

    def get_serializer_class(self):
        if self.action == 'create':
            return SetCredentialsCreateSerializer
        return super().get_serializer_class()
