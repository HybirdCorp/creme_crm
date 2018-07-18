# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2018  Hybird
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

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class GeolocationConfig(CremeAppConfig):
    name = 'creme.geolocation'
    verbose_name = _(u'Geolocation')
    dependencies = ['creme.persons']
    credentials = CremeAppConfig.CRED_NONE

    def all_apps_ready(self):
        # super(GeolocationConfig, self).all_apps_ready()
        super().all_apps_ready()

        from . import signals

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(bricks.GoogleDetailMapBrick,
                                bricks.GoogleFilteredMapBrick,
                                bricks.GoogleNeighboursMapBrick,
                               )

    def register_setting_keys(self, setting_key_registry):
        from . import setting_keys

        setting_key_registry.register(setting_keys.NEIGHBOURHOOD_DISTANCE,
                                      setting_keys.GOOGLE_API_KEY,
                                     )
