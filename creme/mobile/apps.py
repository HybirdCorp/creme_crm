from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class MobileConfig(AppConfig):
    name = 'creme.mobile'
    verbose_name = _(u'Mobile')
