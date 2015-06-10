# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class TicketsConfig(CremeAppConfig):
    name = 'creme.tickets'
    verbose_name = _(u'Tickets')
    dependencies = ['creme.creme_core']
