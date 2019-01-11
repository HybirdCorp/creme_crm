# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from ..models import BrickHomeLocation, BrickMypageLocation

from .generic.base import BricksView


class BaseHome(BricksView):
    bricks_reload_url_name = 'creme_core__reload_home_bricks'


class Home(BaseHome):
    template_name = 'creme_core/home.html'

    def get_brick_ids(self):
        return BrickHomeLocation.objects.order_by('order') \
                                        .values_list('brick_id', flat=True)


class MyPage(BaseHome):
    template_name = 'creme_core/my_page.html'

    def get_brick_ids(self):
        return BrickMypageLocation.objects.filter(user=self.request.user) \
                                          .order_by('order') \
                                          .values_list('brick_id', flat=True)
