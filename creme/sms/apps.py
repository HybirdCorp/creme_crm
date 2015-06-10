# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class SMSConfig(CremeAppConfig):
    name = 'creme.sms'
    verbose_name = _(u'SMS')
    dependencies = ['creme.persons']
