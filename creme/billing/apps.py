# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class BillingConfig(CremeAppConfig):
    name = 'creme.billing'
    verbose_name = _(u'Billing')
    dependencies = ['creme.persons', 'creme.products']

    def ready(self):
        super(BillingConfig, self).ready()

        from . import signals
