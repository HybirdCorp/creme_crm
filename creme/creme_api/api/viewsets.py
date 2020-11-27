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

import rest_framework
import rest_framework.renderers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from creme.creme_core.core.exceptions import SpecificProtectedError

from .authentication import ApiKeyAuthentication
from .pagination import CremeCursorPagination


class CremeApiMixin:
    pagination_class = CremeCursorPagination
    renderer_classes = [
        rest_framework.renderers.JSONRenderer,
    ]
    authentication_classes = [
        ApiKeyAuthentication,
    ]


class CremeModelViewSet(CremeApiMixin, viewsets.ModelViewSet):
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

    @action(detail=True, methods=['post'])
    def trash(self, request, pk):
        instance = self.get_object()

        try:
            instance.trash()
        except SpecificProtectedError as exc:
            raise ValidationError(str(exc))

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk):
        instance = self.get_object()

        try:
            instance.restore()
        except SpecificProtectedError as exc:
            raise ValidationError(str(exc))

        serializer = self.get_serializer(instance)
        return Response(serializer.data)
