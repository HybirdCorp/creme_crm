# -*- coding: utf-8 -*-

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CrudityConfig(AppConfig):
    name = 'creme.crudity'
    verbose_name = _(u'External data management')

    def ready(self):
        from . import signals
