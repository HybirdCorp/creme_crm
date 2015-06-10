# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class CremeConfigConfig(CremeAppConfig):
    name = 'creme.creme_config'
    verbose_name = _(u'General configuration')
    dependencies = ['creme.creme_core']
