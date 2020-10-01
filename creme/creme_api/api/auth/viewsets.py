# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2020  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from django.contrib.auth import get_user_model
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.status import HTTP_204_NO_CONTENT

from creme.creme_core.models import Sandbox, SetCredentials, UserRole

from ..viewsets import CremeApiMixin
from .schemas import UserAutoSchema
from .serializers import (
    SandboxSerializer,
    SetCredentialsSerializer,
    TeamSerializer,
    UserAssignationSerializer,
    UserRoleSerializer,
    UserSerializer,
)

CremeUser = get_user_model()


class AssignOnDeleteMixin:
    def get_serializer_class(self):
        if self.request.method == 'DELETE':
            return UserAssignationSerializer
        return super().get_serializer_class()

    def perform_destroy(self, instance):
        instance.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_destroy(serializer)
        return Response(status=HTTP_204_NO_CONTENT)


class UserViewSet(CremeApiMixin, AssignOnDeleteMixin, viewsets.ModelViewSet):
    queryset = CremeUser.objects.filter(is_team=False, is_staff=False)
    serializer_class = UserSerializer
    schema = UserAutoSchema(tags=['Auth'], operation_id_base="User")


class TeamViewSet(CremeApiMixin, AssignOnDeleteMixin, viewsets.ModelViewSet):
    queryset = CremeUser.objects.filter(is_team=True, is_staff=False)
    serializer_class = TeamSerializer
    schema = UserAutoSchema(tags=['Auth'], operation_id_base="Team")


class UserRoleViewSet(CremeApiMixin, viewsets.ModelViewSet):
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer
    schema = AutoSchema(tags=['Auth'])


class SetCredentialsViewSet(CremeApiMixin, viewsets.ModelViewSet):
    queryset = SetCredentials.objects.all()
    serializer_class = SetCredentialsSerializer
    schema = AutoSchema(tags=['Auth'])


class SandboxViewSet(CremeApiMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Sandbox.objects.all()
    serializer_class = SandboxSerializer
    schema = AutoSchema(tags=['Auth'])
