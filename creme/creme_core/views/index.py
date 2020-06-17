# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from django.db.models import Q

from ..models import BrickHomeLocation, BrickMypageLocation
from .generic.base import BricksView


class BaseHome(BricksView):
    bricks_reload_url_name = 'creme_core__reload_home_bricks'


class Home(BaseHome):
    template_name = 'creme_core/home.html'

    def get_brick_ids(self):
        user = self.request.user
        is_superuser = user.is_superuser

        role_q = (
            Q(role=None, superuser=True)
            if is_superuser else
            Q(role=user.role, superuser=False)
        )
        locs = BrickHomeLocation.objects \
                                .filter(role_q | Q(role=None, superuser=False)) \
                                .order_by('order')

        brick_ids = [loc.brick_id for loc in locs if loc.superuser] if is_superuser else \
                    [loc.brick_id for loc in locs if loc.role_id]

        if not brick_ids:
            brick_ids = [loc.brick_id for loc in locs]

        return brick_ids


class MyPage(BaseHome):
    template_name = 'creme_core/my_page.html'

    def get_brick_ids(self):
        return BrickMypageLocation.objects.filter(user=self.request.user) \
                                          .order_by('order') \
                                          .values_list('brick_id', flat=True)
