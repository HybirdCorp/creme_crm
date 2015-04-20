from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CremeConfigConfig(AppConfig):
    name = 'creme.creme_config'
    verbose_name = _(u'General configuration')
