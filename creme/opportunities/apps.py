# -*- coding: utf-8 -*-

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class OpportunitiesConfig(AppConfig):
    name = 'creme.opportunities'
    verbose_name = _(u'Opportunities')

    def ready(self):
        from . import signals
