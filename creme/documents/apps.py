from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class DocumentsConfig(AppConfig):
    name = 'creme.documents'
    verbose_name = _(u'Documents')
