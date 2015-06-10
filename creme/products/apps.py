# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class ProductsConfig(CremeAppConfig):
    name = 'creme.products'
    verbose_name = _(u'Products and services')
    dependencies = ['creme.media_managers']
