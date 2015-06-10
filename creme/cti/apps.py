# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class CTIConfig(CremeAppConfig):
    name = 'creme.cti'
    verbose_name = _(u'Computer Telephony Integration')
    dependencies = ['creme.persons', 'creme.activities']
