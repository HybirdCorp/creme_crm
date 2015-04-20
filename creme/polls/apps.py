from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class PollsConfig(AppConfig):
    name = 'creme.polls'
    verbose_name = _(u'Polls')
