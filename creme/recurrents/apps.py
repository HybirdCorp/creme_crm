# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class RecurrentsConfig(CremeAppConfig):
    name = 'creme.recurrents'
    verbose_name = _(u'Recurrent documents')
    dependencies = ['creme.creme_core']
