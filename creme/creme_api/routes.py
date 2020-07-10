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

from importlib import import_module

from django.apps import apps
from rest_framework import routers

from creme.creme_core.apps import creme_app_configs
from creme.creme_core.utils.collections import OrderedSet


class CremeApiRouter(routers.DefaultRouter):
    def populate_routes(self):
        app_labels = OrderedSet(app_config.label for app_config in creme_app_configs())

        for app_label in app_labels:
            app = apps.get_app_config(app_label).name
            try:
                api_module = import_module(f'{app}.api')
            except ImportError:
                continue

            try:
                routes = api_module.routes
            except AttributeError:
                continue

            for ressource_path, viewset in routes:
                self.register(ressource_path, viewset)


creme_api_router = CremeApiRouter()
creme_api_router.populate_routes()
