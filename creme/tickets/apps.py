from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class TicketsConfig(AppConfig):
    name = 'creme.tickets'
    verbose_name = _(u'Tickets')
