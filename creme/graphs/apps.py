# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class GraphsConfig(CremeAppConfig):
    name = 'creme.graphs'
    verbose_name = _(u'Graphs')
    dependencies = ['creme.creme_core']
