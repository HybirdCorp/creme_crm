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


class UserViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    # mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    create:
    Create a user.

    retrieve:
    Retrieve a user.

    update:
    Update a user.

    partial_update:
    Partially update a user.

    list:
    List users.

    set_password:
    Change a user's password.

    delete_user:
    Delete a user.

    """

    queryset = CremeUser.objects.filter(is_team=False, is_staff=False)
    serializer_class = UserSerializer
    schema = CremeSchema(tags=["Users"], operation_id_base="Users")

    @action(methods=["post"], detail=True, serializer_class=PasswordSerializer)
    def set_password(self, request, pk):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(
        methods=["post"],
        detail=True,
        serializer_class=DeleteUserSerializer,
        url_path="delete",
        url_name="delete",
        name="delete",
    )
    def delete_user(self, request, pk):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TeamViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    # mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    create:
    Create a team.

    retrieve:
    Retrieve a team.

    update:
    Update a team.

    partial_update:
    Partially update a team.

    list:
    List teams.

    delete_team:
    Delete a team.

    """

    queryset = CremeUser.objects.filter(is_team=True, is_staff=False)
    serializer_class = TeamSerializer
    schema = CremeSchema(tags=["Teams"], operation_id_base="Teams")

    @action(
        methods=["post"],
        detail=True,
        serializer_class=DeleteUserSerializer,
        url_path="delete",
        url_name="delete",
        name="delete",
    )
    def delete_team(self, request, pk):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserRoleViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """

    create:
    Create a role.

    retrieve:
    Retrieve a role.

    update:
    Update a role

    partial_update:
    Partially update a role

    destroy:
    Delete a role.

    list:
    List roles.

    """

    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer
    schema = CremeSchema(tags=["Roles"])

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as e:
            raise PermissionDenied(e.args[0]) from e


class SetCredentialsViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """

    create:
    Create a credential set.

    retrieve:
    Retrieve a credential set.

    update:
    Update a credential set.

    partial_update:
    Partially update a credential set.

    destroy:
    Delete a credential set.

    list:
    List credential sets.

    """

    queryset = SetCredentials.objects.all()
    serializer_class = SetCredentialsSerializer
    schema = CremeSchema(tags=["Credential Sets"])

    def get_serializer_class(self):
        if self.action == "create":
            return SetCredentialsCreateSerializer
        return super().get_serializer_class()
