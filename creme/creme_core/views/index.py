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

from django.shortcuts import render
from django.urls import reverse

from ..auth.decorators import login_required
from ..gui.bricks import brick_registry
from ..models import BlockPortalLocation, BlockMypageLocation


def _render_home(request, template_name, brick_ids):
    return render(request, template_name,
                  context={'bricks':            list(brick_registry.get_bricks([id_ for id_ in brick_ids if id_])),
                           'bricks_reload_url': reverse('creme_core__reload_home_bricks'),
                          },
                 )


@login_required
def home(request):
    return _render_home(request, 'creme_core/home.html',
                        brick_ids=BlockPortalLocation.objects
                                                     # .filter(app_name='creme_core')
                                                     .order_by('order')
                                                     .values_list('brick_id', flat=True),
                       )


@login_required
def my_page(request):
    return _render_home(request, 'creme_core/my_page.html',
                        brick_ids=BlockMypageLocation.objects
                                                     .filter(user=request.user)
                                                     .order_by('order')
                                                     .values_list('brick_id', flat=True),
                       )
