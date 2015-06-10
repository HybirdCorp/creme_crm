# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class ActivesyncConfig(CremeAppConfig):
    name = 'creme.activesync'
    verbose_name = _(u'Mobile synchronization')
    dependencies = ['creme.persons', 'creme.activities']

    def ready(self):
        super(ActivesyncConfig, self).ready()

        from . import signals
