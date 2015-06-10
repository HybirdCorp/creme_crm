# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class VCFsConfig(CremeAppConfig):
    name = 'creme.vcfs'
    verbose_name = _(u'Vcfs')
    dependencies = ['creme.persons']
