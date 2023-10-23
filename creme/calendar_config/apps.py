################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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


class ActivitiesConfig(CremeAppConfig):
    default = True
    name = 'creme.calendar_config'
    verbose_name = _('Calendar configuration')
    dependencies = ['creme.creme_core', 'creme.activities']
    extended_app = "creme.activities"
    credentials = CremeAppConfig.CRED_NONE

    url_root = 'activities/'

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            bricks.CalendarConfigItemsBrick,
        )

    def register_creme_config(self, config_registry):
        from . import bricks

        config_registry.register_app_bricks(
            'activities',
            bricks.CalendarConfigItemsBrick,
        )
