# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class DocumentsConfig(CremeAppConfig):
    name = 'creme.documents'
    verbose_name = _(u'Documents')
    dependencies = ['creme.creme_core']
