# -*- coding: utf-8 -*-

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class BillingConfig(AppConfig):
    name = 'creme.billing'
    verbose_name = _(u'Billing')

    def ready(self):
        from . import signals
