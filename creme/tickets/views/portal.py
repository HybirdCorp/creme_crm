# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme_core.views.generic import app_portal

from creme_config.utils.url_generator import generate_portal_url

from tickets.models.ticket import Ticket
from tickets.models.status import OPEN_PK, CLOSED_PK


def portal(request):
    tickets = Ticket.objects
    count = tickets.all().count()
    closed_percentage = '%s %%' % (100.0 * tickets.filter(status__id=CLOSED_PK).count() / count) if count else ''

    stats = (
                (_('Nombre de ticket(s)'),            count),
                (_('Nombre de ticket(s) ouvert(s)'),  tickets.filter(status__id=OPEN_PK).count()),
                (_(u'Pourcentage de tickets fermés'), closed_percentage),
            )

    return app_portal(request, 'tickets', 'tickets/portal.html', Ticket,
                      stats, config_url=generate_portal_url('tickets'))
