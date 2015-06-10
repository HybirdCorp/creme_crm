# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class ActivitiesConfig(CremeAppConfig):
    name = 'creme.activities'
    verbose_name = _(u'Activities')
    dependencies = ['creme.persons', 'creme.assistants']

    def ready(self):
        super(ActivitiesConfig, self).ready()

        from . import signals
