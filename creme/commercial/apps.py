from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CommercialConfig(AppConfig):
    name = 'creme.commercial'
    verbose_name = _(u'Commercial strategy')
