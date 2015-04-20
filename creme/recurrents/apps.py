from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class RecurrentsConfig(AppConfig):
    name = 'creme.recurrents'
    verbose_name = _(u'Recurrent documents')
