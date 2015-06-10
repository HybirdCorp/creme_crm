# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class CommercialConfig(CremeAppConfig):
    name = 'creme.commercial'
    verbose_name = _(u'Commercial strategy')
    dependencies = ['creme.persons', 'creme.opportunities']

    def ready(self):
        super(CommercialConfig, self).ready()

        from . import signals
