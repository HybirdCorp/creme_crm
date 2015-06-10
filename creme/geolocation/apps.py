# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class GeolocationConfig(CremeAppConfig):
    name = 'creme.geolocation'
    verbose_name = _(u'Geolocation')
    dependencies = ['creme.persons']

    def ready(self):
        super(GeolocationConfig, self).ready()

        from . import signals
