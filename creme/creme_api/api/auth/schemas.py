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

from rest_framework import serializers
from rest_framework.schemas.openapi import AutoSchema


class UserAutoSchema(AutoSchema):
    """
    Allow DELETE method to have a payload.
    """
    def get_request_body(self, path, method):
        if method == 'DELETE':
            self.request_media_types = self.map_parsers(path, method)

            serializer = self.get_serializer(path, method)

            if not isinstance(serializer, serializers.Serializer):
                item_schema = {}
            else:
                item_schema = self._get_reference(serializer)

            return {
                'content': {
                    ct: {'schema': item_schema}
                    for ct in self.request_media_types
                }
            }
        return super().get_request_body(path, method)

    def get_components(self, path, method):
        """
        Return components with their properties from the serializer.
        """

        if method.lower() == 'delete':
            serializer = self.get_serializer(path, method)

            if not isinstance(serializer, serializers.Serializer):
                return {}

            component_name = self.get_component_name(serializer)

            content = self.map_serializer(serializer)
            return {component_name: content}
        return super().get_components(path, method)
