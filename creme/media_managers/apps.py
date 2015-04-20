from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class MediaManagersConfig(AppConfig):
    name = 'creme.media_managers'
    verbose_name = _(u'Media managers')
