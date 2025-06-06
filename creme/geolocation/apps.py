################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2025  Hybird
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

from creme.creme_core.apps import CremeAppConfig
from creme.persons import get_contact_model, get_organisation_model


class GeolocationConfig(CremeAppConfig):
    default = True
    name = 'creme.geolocation'
    verbose_name = _('Geolocation')
    dependencies = ['creme.persons']
    credentials = CremeAppConfig.CRED_NONE

    def ready(self):
        super().ready()
        self.register_geomarker_icons()

    def all_apps_ready(self):
        super().all_apps_ready()

        from . import signals  # NOQA

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            bricks.GoogleDetailMapBrick,
            bricks.GoogleFilteredMapBrick,
            bricks.GoogleNeighboursMapBrick,
            bricks.OpenStreetMapDetailMapBrick,
            bricks.OpenStreetMapFilteredMapBrick,
            bricks.OpenStreetMapNeighboursMapBrick,
        )

    def register_creme_config(self, config_registry):
        from . import models

        register_model = config_registry.register_model
        register_model(models.Town, 'town')
        register_model(
            models.GeoAddress, 'geoaddress',
        ).creation(
            enable_func=lambda user: False
        ).edition(
            enable_func=lambda instance, user: False
        ).deletion(
            enable_func=lambda instance, user: False
        )

    def register_setting_keys(self, setting_key_registry):
        from . import setting_keys

        setting_key_registry.register(
            # setting_keys.NEIGHBOURHOOD_DISTANCE,
            setting_keys.neighbourhood_distance_key,
            # setting_keys.GOOGLE_API_KEY,
            setting_keys.google_api_key,
            setting_keys.use_entity_icon_key,
        )

    def register_geomarker_icons(self):
        from .registry import GeoMarkerIcon, geomarker_icon_registry

        Contact = get_contact_model()
        Organisation = get_organisation_model()

        geomarker_icon_registry.register(
            Contact, GeoMarkerIcon(path='geolocation/images/marker-icon.png')
        ).register(
            Organisation, GeoMarkerIcon(path='geolocation/images/marker-icon-red.png')
        )
