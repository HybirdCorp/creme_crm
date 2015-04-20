from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class AssistantsConfig(AppConfig):
    name = 'creme.assistants'
    verbose_name = _(u'Assistants (Todos, Memo, ...)')
