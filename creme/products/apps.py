from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ProductsConfig(AppConfig):
    name = 'creme.products'
    verbose_name = _(u'Products and services')
