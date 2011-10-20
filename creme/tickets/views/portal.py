# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.utils.translation import ugettext as _

from creme_core.views.generic import app_portal

from creme_config.utils import generate_portal_url

from tickets.models import Ticket
from tickets.models.status import OPEN_PK, CLOSED_PK


def portal(request):
    tickets = Ticket.objects
    count = tickets.count()
    closed_percentage = '%s %%' % (100.0 * tickets.filter(status=CLOSED_PK).count() / count) if count else ''

    stats = (
                (_('Number of tickets'),             count),
                (_('Number of open tickets'),        tickets.filter(status=OPEN_PK).count()),
                (_(u'Percentage of closed tickets'), closed_percentage),
            )

    return app_portal(request, 'tickets', 'tickets/portal.html', Ticket,
                      stats, config_url=generate_portal_url('tickets'))
