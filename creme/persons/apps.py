from django.apps import AppConfig

from django.utils.translation import ugettext_lazy as _


class PersonsConfig(AppConfig):
    name = 'creme.persons'
    verbose_name = _(u'Accounts and Contacts')

    def ready(self):
        # self.get_model() ??
        from django.contrib.auth import get_user_model
        from creme.persons.models.contact import _get_linked_contact

        get_user_model().linked_contact = property(_get_linked_contact)
