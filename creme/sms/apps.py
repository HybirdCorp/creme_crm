from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class SMSConfig(AppConfig):
    name = 'creme.sms'
    verbose_name = _(u'SMS')
