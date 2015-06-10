# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class MobileConfig(CremeAppConfig):
    name = 'creme.mobile'
    verbose_name = _(u'Mobile')
    dependencies = ['creme.persons', 'creme.activities']
