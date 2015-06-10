# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class CrudityConfig(CremeAppConfig):
    name = 'creme.crudity'
    verbose_name = _(u'External data management')
    dependencies = ['creme.creme_core']

    def ready(self):
        super(CrudityConfig, self).ready()

        from . import signals
