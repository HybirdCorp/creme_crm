# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from creme.creme_core.views.generic import app_portal

from creme.creme_config.utils import generate_portal_url

#from ..models import Act
from .. import get_act_model, get_strategy_model


def portal(request):
    Act = get_act_model()
    Strategy = get_strategy_model()
    stats = ((_('Number of commercial actions'),    Act.objects.count()),
             (_('Number of commercial strategies'), Strategy.objects.count()),
            )

    return app_portal(request, 'commercial', 'commercial/portal.html', Act,
                      stats, config_url=generate_portal_url('commercial'),
                     )
