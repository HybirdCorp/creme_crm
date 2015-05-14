# -*- coding: utf-8 -*-

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ActivitiesConfig(AppConfig):
    name = 'creme.activities'
    verbose_name = _(u'Activities')

    def ready(self):
        from . import signals
