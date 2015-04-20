from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CTIConfig(AppConfig):
    name = 'creme.cti'
    verbose_name = _(u'Computer Telephony Integration')