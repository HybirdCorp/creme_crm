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

from django.utils.translation import gettext_lazy as _

from creme.creme_api.api.routers import creme_api_router
from creme.creme_core.apps import CremeAppConfig


class CremeApiConfig(CremeAppConfig):
    name = 'creme.creme_api'
    verbose_name = _('Creme Api')
    dependencies = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.router = creme_api_router

    def register_creme_config(self, config_registry):
        from . import models

        register_model = config_registry.register_model
        register_model(models.ApiKey, 'api_key')

    def register_endpoint(self, endpoint, viewset):
        self.router.register(endpoint, viewset, basename=f'creme_api-{endpoint}')

    def all_apps_ready(self):
        super().all_apps_ready()

        import creme.creme_api.api.contenttypes.viewsets

        self.register_endpoint(
            "contenttypes",
            creme.creme_api.api.contenttypes.viewsets.ContentTypeViewSet)

        import creme.creme_api.api.auth.viewsets

        self.register_endpoint(
            "users",
            creme.creme_api.api.auth.viewsets.UserViewSet)
        self.register_endpoint(
            "teams",
            creme.creme_api.api.auth.viewsets.TeamViewSet)
        self.register_endpoint(
            "roles",
            creme.creme_api.api.auth.viewsets.UserRoleViewSet)
        self.register_endpoint(
            "credentials",
            creme.creme_api.api.auth.viewsets.SetCredentialsViewSet)
        self.register_endpoint(
            "sandboxes",
            creme.creme_api.api.auth.viewsets.SandboxViewSet)

        import creme.creme_api.api.persons.viewsets

        self.register_endpoint(
            "contacts",
            creme.creme_api.api.persons.viewsets.ContactViewSet)
        self.register_endpoint(
            "organisations",
            creme.creme_api.api.persons.viewsets.OrganisationViewSet)
        self.register_endpoint(
            "addresses",
            creme.creme_api.api.persons.viewsets.AddressViewSet)
        self.register_endpoint(
            "civilities",
            creme.creme_api.api.persons.viewsets.CivilityViewSet)
        self.register_endpoint(
            "positions",
            creme.creme_api.api.persons.viewsets.PositionViewSet)
        self.register_endpoint(
            "staffsizes",
            creme.creme_api.api.persons.viewsets.StaffSizeViewSet)
        self.register_endpoint(
            "legalforms",
            creme.creme_api.api.persons.viewsets.LegalFormViewSet)
        self.register_endpoint(
            "sectors",
            creme.creme_api.api.persons.viewsets.SectorViewSet)
