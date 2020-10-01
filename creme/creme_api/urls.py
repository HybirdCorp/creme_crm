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

from django.apps import apps
from django.urls import path
from django.views.generic import TemplateView
from rest_framework.schemas import get_schema_view

from creme.creme_api import VERSION

creme_api_config = apps.get_app_config('creme_api')


urlpatterns = [
    path('openapi', get_schema_view(
        title="CremeCRM API",
        description="Provide a rest API to conquer the world",
        version=VERSION
    ), name='openapi-schema'),
    path('swagger-ui/', TemplateView.as_view(
        template_name='creme_api/swagger-ui.html',
        extra_context={'schema_url': 'openapi-schema'}
    ), name='swagger-ui'),
] + creme_api_config.router.urls
