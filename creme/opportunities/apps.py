# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class OpportunitiesConfig(CremeAppConfig):
    name = 'creme.opportunities'
    verbose_name = _(u'Opportunities')
    dependencies = ['creme.persons', 'creme.products']

    def ready(self):
        super(OpportunitiesConfig, self).ready()

        from . import signals
