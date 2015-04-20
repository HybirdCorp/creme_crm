from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class EmailsConfig(AppConfig):
    name = 'creme.emails'
    verbose_name = _(u'Emails')
