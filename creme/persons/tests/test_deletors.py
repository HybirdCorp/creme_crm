from django.utils.translation import gettext as _

from creme.creme_core.core.exceptions import ConflictError
from creme.persons.deletors import ContactDeletor, OrganisationDeletor

from .base import (
    Contact,
    Organisation,
    _PersonsTestCase,
    skipIfCustomContact,
    skipIfCustomOrganisation,
)


class DeletorsTestCase(_PersonsTestCase):
    @skipIfCustomContact
    def test_contact_deletor(self):
        user = self.get_root_user()
        contact1 = Contact.objects.create(user=user, first_name='John', last_name='Doe')
        deletor = ContactDeletor()
        with self.assertNoException():
            deletor.check_permissions(user=user, entity=contact1)

        # ---
        other_user = self.create_user()
        with self.assertRaises(ConflictError) as cm:
            deletor.check_permissions(user=user, entity=other_user.linked_contact)

        self.assertEqual(
            _('A user is associated with this contact.'),
            str(cm.exception),
        )

    @skipIfCustomOrganisation
    def test_organisation_deletor(self):
        user = self.get_root_user()
        orga = Organisation.objects.create(user=user, name='Acme')
        deletor = OrganisationDeletor()

        with self.assertNoException():
            deletor.check_permissions(user=user, entity=orga)

    @skipIfCustomOrganisation
    def test_organisation_deletor__one_managed(self):
        deletor = OrganisationDeletor()
        managed = Organisation.objects.get(is_managed=True)

        with self.assertRaises(ConflictError) as cm:
            deletor.check_permissions(user=self.get_root_user(), entity=managed)

        self.assertEqual(
            _('The last managed organisation cannot be deleted.'),
            str(cm.exception),
        )

    @skipIfCustomOrganisation
    def test_organisation_deletor__several_managed(self):
        user = self.get_root_user()
        orga = Organisation.objects.create(user=user, name='Acme', is_managed=True)
        deletor = OrganisationDeletor()

        with self.assertNoException():
            deletor.check_permissions(user=user, entity=orga)
