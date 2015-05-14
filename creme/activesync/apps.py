# -*- coding: utf-8 -*-

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ActivesyncConfig(AppConfig):
    name = 'creme.activesync'
    verbose_name = _(u'Mobile synchronization')

    def ready(self):
        from . import signals
