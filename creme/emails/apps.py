# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class EmailsConfig(CremeAppConfig):
    name = 'creme.emails'
    verbose_name = _(u'Emails')
    dependencies = ['creme.persons', 'creme.documents', 'creme.crudity']
