from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class GeolocationConfig(AppConfig):
    name = 'creme.geolocation'
    verbose_name = _(u'Geolocation')
