# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class EventsConfig(CremeAppConfig):
    name = 'creme.events'
    verbose_name = _(u'Events')
    dependencies = ['creme.persons', 'creme.opportunities']
