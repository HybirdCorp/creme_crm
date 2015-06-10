# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class ReportsConfig(CremeAppConfig):
    name = 'creme.reports'
    verbose_name = _(u'Reports')
    dependencies = ['creme.creme_core']
