# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class AssistantsConfig(CremeAppConfig):
    name = 'creme.assistants'
    verbose_name = _(u'Assistants (Todos, Memo, ...)')
    dependencies = ['creme.creme_core']

    def ready(self):
        super(AssistantsConfig, self).ready()

        from . import signals
