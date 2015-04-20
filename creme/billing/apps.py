from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class BillingConfig(AppConfig):
    name = 'creme.billing'
    verbose_name = _(u'Billing')
