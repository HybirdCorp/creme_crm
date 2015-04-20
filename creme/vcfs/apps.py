from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class VCFsConfig(AppConfig):
    name = 'creme.vcfs'
    verbose_name = _(u'Vcfs')
