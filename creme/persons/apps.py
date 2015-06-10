# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class PersonsConfig(CremeAppConfig):
    name = 'creme.persons'
    verbose_name = _(u'Accounts and Contacts')
    dependencies = ['creme.creme_core']

    def ready(self):
        super(PersonsConfig, self).ready()

        # self.get_model() ??
        from django.contrib.auth import get_user_model

        from . import signals
        from .models.contact import _get_linked_contact

        get_user_model().linked_contact = property(_get_linked_contact)
