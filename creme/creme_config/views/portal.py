# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

from creme.creme_core.auth import decorators
from creme.creme_core.utils.unicode_collation import collator

from ..registry import config_registry


@decorators.login_required
@decorators.permission_required('creme_config')
def portal(request):
    sort_key = collator.sort_key
    return render(request, 'creme_config/portal.html',
                  {'app_configs': sorted(config_registry.apps(),
                                         key=lambda app: sort_key(app.verbose_name)
                                        ),
                   'app_blocks': config_registry.portalblocks,
                  }
                 )
