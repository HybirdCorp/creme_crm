# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class PollsConfig(CremeAppConfig):
    name = 'creme.polls'
    verbose_name = _(u'Polls')
    dependencies = ['creme.persons', 'creme.commercial']
