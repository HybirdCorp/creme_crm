################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from django.http import Http404

from creme.creme_core.utils.unicode_collation import collator
from creme.creme_core.views.bricks import BricksReloading
from creme.creme_core.views.generic import BricksView

from .. import registry


class Portal(BricksView):
    template_name = 'creme_config/portal.html'
    permissions = 'creme_config'
    bricks_reload_url_name = 'creme_config__reload_portal_bricks'

    config_registry = registry.config_registry

    def get_bricks(self):
        # return [*self.config_registry.portal_bricks]
        return {'main': [*self.config_registry.portal_bricks]}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        sort_key = collator.sort_key
        context['app_configs'] = sorted(
            (app_reg for app_reg in self.config_registry.apps() if not app_reg.is_empty),
            key=(lambda app: sort_key(app.verbose_name)),
        )

        return context


class PortalBricksReloading(BricksReloading):
    permissions = 'creme_config'
    config_registry = registry.config_registry

    def get_bricks(self):
        bricks = []
        allowed_bricks = {brick.id: brick for brick in self.config_registry.portal_bricks}

        for brick_id in self.get_brick_ids():
            try:
                brick = allowed_bricks[brick_id]
            except KeyError as e:
                raise Http404(f'Invalid brick id "{brick_id}"') from e

            bricks.append(brick)

        return bricks
