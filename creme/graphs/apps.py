from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class GraphsConfig(AppConfig):
    name = 'creme.graphs'
    verbose_name = _(u'Graphs')
