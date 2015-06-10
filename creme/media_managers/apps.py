# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class MediaManagersConfig(CremeAppConfig):
    name = 'creme.media_managers'
    verbose_name = _(u'Media managers')
    dependencies = ['creme.creme_core']
