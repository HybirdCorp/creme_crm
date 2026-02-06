from functools import partial

from django.core.exceptions import ValidationError
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.core.exceptions import SpecificProtectedError
from creme.creme_core.models import CremeUser, Relation
from creme.creme_core.tests.base import skipIfCustomUser
from creme.documents.tests.base import skipIfCustomDocument
from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES
from creme.persons.models import Civility, Position, Sector

from ..base import (
    Address,
    Contact,
    Organisation,
    _PersonsTestCase,
    skipIfCustomAddress,
    skipIfCustomContact,
    skipIfCustomOrganisation,
)


@skipIfCustomContact
class ContactTestCase(_PersonsTestCase):
    def test_empty_fields(self):
        user = self.login_as_root_and_get()

        with self.assertNoException():
            contact = Contact.objects.create(user=user, last_name='Spiegel')

        self.assertEqual('', contact.first_name)
        self.assertEqual('', contact.description)
        self.assertEqual('', contact.skype)
        self.assertEqual('', contact.phone)
        self.assertEqual('', contact.mobile)
        self.assertEqual('', contact.email)
        self.assertEqual('', contact.url_site)
        self.assertEqual('', contact.full_position)

    def test_str(self):
        first_name = 'Spike'
        last_name  = 'Spiegel'
        build_contact = partial(Contact, last_name=last_name)
        self.assertEqual(last_name, str(build_contact()))
        self.assertEqual(last_name, str(build_contact(first_name='')))
        self.assertEqual(
            _('{first_name} {last_name}').format(
                first_name=first_name,
                last_name=last_name,
            ),
            str(build_contact(first_name=first_name)),
        )

        captain = Civility.objects.create(title='Captain')  # No shortcut
        self.assertEqual(
            _('{first_name} {last_name}').format(
                first_name=first_name,
                last_name=last_name,
            ),
            str(build_contact(first_name=first_name, civility=captain)),
        )

        captain.shortcut = shortcut = 'Cpt'
        captain.save()
        self.assertEqual(
            _('{civility} {first_name} {last_name}').format(
                civility=shortcut,
                first_name=first_name,
                last_name=last_name,
            ),
            str(build_contact(first_name=first_name, civility=captain)),
        )

    def test_clean_unique_user_email(self):
        user1 = self.create_user(0)
        user2 = self.create_user(1)

        contact2 = user2.linked_contact
        contact2.email = user1.email

        with self.assertRaises(ValidationError) as cm:
            contact2.clean()

        self.assertValidationError(
            cm.exception,
            messages={
                'email': _(
                    'This Contact is related to a user and an active user '
                    'already uses this email address.'
                ),
            },
        )

        # Ignore inactive ---
        user1.is_active = False
        user1.save()

        with self.assertNoException():
            contact2.clean()

        # Ignore own user ---
        contact2.email = user2.email

        with self.assertNoException():
            contact2.clean()

    def test_is_user(self):
        "Property 'linked_contact'."
        user = self.create_user()

        with self.assertNumQueries(0):
            rel_contact = user.linked_contact

        contact = self.get_object_or_fail(Contact, is_user=user)
        self.assertEqual(contact, rel_contact)

        user = self.refresh(user)  # Clean cache

        with self.assertNumQueries(1):
            user.linked_contact  # NOQA

        with self.assertNumQueries(0):
            user.linked_contact  # NOQA

        self.assertHasAttr(user, 'get_absolute_url')
        self.assertEqual(contact.get_absolute_url(), user.get_absolute_url())

    def test_is_user__errors(self):
        """Contact.clean() + integrity of User."""
        user = self.login_as_root_and_get()
        contact = user.linked_contact
        last_name = contact.last_name
        first_name = contact.first_name

        contact.email = ''
        contact.first_name = ''
        contact.save()

        user = self.refresh(user)
        self.assertEqual('',         user.first_name)
        self.assertEqual(last_name,  user.last_name)
        self.assertEqual('',         user.email)

        with self.assertRaises(ValidationError) as cm1:
            contact.full_clean()

        self.assertValidationError(
            cm1.exception,
            messages={
                'first_name': _(
                    'This Contact is related to a user and must have a first name.'
                ),
            },
        )

        # ---
        contact.first_name = first_name

        with self.assertRaises(ValidationError) as cm2:
            contact.full_clean()

        self.assertValidationError(
            cm2.exception,
            messages={
                'email': _(
                    'This Contact is related to a user and must have an email address.'
                ),
            },
        )

    @skipIfCustomAddress
    def test_clone(self):
        "Addresses & is_user are problematic."
        user = self.login_as_root_and_get()
        naruto = self.get_object_or_fail(Contact, is_user=user)

        create_address = partial(
            Address.objects.create,
            city='Konoha', state='Konoha', zipcode='111',
            country='The land of fire', department="Ninjas' homes",
            owner=naruto,
        )
        naruto.billing_address = create_address(
            name="Naruto's", address='Home', po_box='000',
        )
        naruto.shipping_address = create_address(
            name="Naruto's", address='Home (second entry)', po_box='001',
        )
        naruto.save()

        for i in range(5):
            create_address(name=f'Secret Cave #{i}', address=f'Cave #{i}', po_box='XXX')

        kage_bunshin = self.clone(naruto)
        self.assertEqual(naruto.first_name, kage_bunshin.first_name)
        self.assertEqual(naruto.last_name, kage_bunshin.last_name)
        self.assertIsNone(kage_bunshin.is_user)  # <====

        self.assertEqual(naruto.id, naruto.billing_address.object_id)
        self.assertEqual(naruto.id, naruto.shipping_address.object_id)

        self.assertEqual(kage_bunshin.id, kage_bunshin.billing_address.object_id)
        self.assertEqual(kage_bunshin.id, kage_bunshin.shipping_address.object_id)

        addresses   = [*Address.objects.filter(object_id=naruto.id)]
        c_addresses = [*Address.objects.filter(object_id=kage_bunshin.id)]
        self.assertEqual(7, len(addresses))
        self.assertEqual(7, len(c_addresses))

        addresses_map   = {a.address: a for a in addresses}
        c_addresses_map = {a.address: a for a in c_addresses}
        self.assertEqual(7, len(addresses_map))
        self.assertEqual(7, len(c_addresses_map))

        for ident, address in addresses_map.items():
            address2 = c_addresses_map.get(ident)
            self.assertIsNotNone(address2, ident)
            self.assertAddressOnlyContentEqual(address, address2)

    # @skipIfCustomAddress
    # def test_clone__method(self):  # DEPRECATED
    #     "Addresses & is_user are problematic."
    #     user = self.login_as_root_and_get()
    #     naruto = self.get_object_or_fail(Contact, is_user=user)
    #
    #     create_address = partial(
    #         Address.objects.create,
    #         city='Konoha', state='Konoha', zipcode='111',
    #         country='The land of fire', department="Ninjas' homes",
    #         owner=naruto,
    #     )
    #     naruto.billing_address = create_address(
    #         name="Naruto's", address='Home', po_box='000',
    #     )
    #     naruto.shipping_address = create_address(
    #         name="Naruto's", address='Home (second entry)', po_box='001',
    #     )
    #     naruto.save()
    #
    #     for i in range(5):
    #         create_address(name=f'Secret Cave #{i}', address=f'Cave #{i}', po_box='XXX')
    #
    #     kage_bunshin = naruto.clone()
    #
    #     self.assertEqual(naruto.first_name, kage_bunshin.first_name)
    #     self.assertEqual(naruto.last_name, kage_bunshin.last_name)
    #     self.assertIsNone(kage_bunshin.is_user)  # <====
    #
    #     self.assertEqual(naruto.id, naruto.billing_address.object_id)
    #     self.assertEqual(naruto.id, naruto.shipping_address.object_id)
    #
    #     self.assertEqual(kage_bunshin.id, kage_bunshin.billing_address.object_id)
    #     self.assertEqual(kage_bunshin.id, kage_bunshin.shipping_address.object_id)
    #
    #     addresses   = [*Address.objects.filter(object_id=naruto.id)]
    #     c_addresses = [*Address.objects.filter(object_id=kage_bunshin.id)]
    #     self.assertEqual(7, len(addresses))
    #     self.assertEqual(7, len(c_addresses))
    #
    #     addresses_map   = {a.address: a for a in addresses}
    #     c_addresses_map = {a.address: a for a in c_addresses}
    #     self.assertEqual(7, len(addresses_map))
    #     self.assertEqual(7, len(c_addresses_map))
    #
    #     for ident, address in addresses_map.items():
    #         address2 = c_addresses_map.get(ident)
    #         self.assertIsNotNone(address2, ident)
    #         self.assertAddressOnlyContentEqual(address, address2)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete(self):
        user = self.login_as_root_and_get()
        naruto = Contact.objects.create(user=user, first_name='Naruto', last_name='Uzumaki')
        url = naruto.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        with self.assertNoException():
            naruto = self.refresh(naruto)

        self.assertIs(naruto.is_deleted, True)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(naruto)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete_is_user(self):
        "Can not delete if the Contact corresponds to a user."
        self.login_as_root()
        user = self.create_user()
        contact = user.linked_contact

        with self.assertRaises(SpecificProtectedError):
            contact.trash()

        Contact.objects.filter(id=contact.id).update(is_deleted=True)
        self.assertPOST409(contact.get_delete_absolute_url(), follow=True)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_trash_is_user(self):
        "Can not trash if the Contact corresponds to a user."
        self.login_as_root()
        user = self.create_user()
        self.assertPOST409(user.linked_contact.get_delete_absolute_url(), follow=True)

    def test_delete_civility__set_null(self):
        "Set to NULL."
        user = self.login_as_root_and_get()
        captain = Civility.objects.create(title='Captain')
        harlock = Contact.objects.create(
            user=user, first_name='Harlock', last_name='Matsumoto', civility=captain,
        )

        response = self.client.post(reverse(
            'creme_config__delete_instance', args=('persons', 'civility', captain.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Civility).job
        job.type.execute(job)
        self.assertDoesNotExist(captain)

        harlock = self.assertStillExists(harlock)
        self.assertIsNone(harlock.civility)

    def test_delete_civility__replace(self):
        "Set to another value."
        user = self.login_as_root_and_get()
        civ2 = Civility.objects.first()
        captain = Civility.objects.create(title='Captain')
        harlock = Contact.objects.create(
            user=user, first_name='Harlock', last_name='Matsumoto', civility=captain,
        )

        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('persons', 'civility', captain.id)
            ),
            data={'replace_persons__contact_civility': civ2.id},
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Civility).job
        job.type.execute(job)
        self.assertDoesNotExist(captain)

        harlock = self.assertStillExists(harlock)
        self.assertEqual(civ2, harlock.civility)

    def test_delete_position__set_null(self):
        "Set to NULL."
        user = self.login_as_root_and_get()
        captain = Position.objects.create(title='Captain')
        harlock = Contact.objects.create(
            user=user, first_name='Harlock', last_name='Matsumoto', position=captain,
        )

        response = self.client.post(reverse(
            'creme_config__delete_instance',
            args=('persons', 'position', captain.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Position).job
        job.type.execute(job)
        self.assertDoesNotExist(captain)

        harlock = self.assertStillExists(harlock)
        self.assertIsNone(harlock.position)

    def test_delete_position__replace(self):
        "Set to another value."
        user = self.login_as_root_and_get()
        pos2 = Position.objects.first()
        captain = Position.objects.create(title='Captain')
        harlock = Contact.objects.create(
            user=user, first_name='Harlock', last_name='Matsumoto', position=captain,
        )

        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('persons', 'position', captain.id),
            ),
            data={'replace_persons__contact_position': pos2.id},
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Position).job
        job.type.execute(job)
        self.assertDoesNotExist(captain)

        harlock = self.assertStillExists(harlock)
        self.assertEqual(pos2, harlock.position)

    def test_delete_sector__set_null(self):
        "Set to NULL."
        user = self.login_as_root_and_get()
        piracy = Sector.objects.create(title='Piracy')
        harlock = Contact.objects.create(
            user=user, first_name='Harlock', last_name='Matsumoto', sector=piracy,
        )

        response = self.client.post(reverse(
            'creme_config__delete_instance',
            args=('persons', 'sector', piracy.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Sector).job
        job.type.execute(job)
        self.assertDoesNotExist(piracy)

        harlock = self.assertStillExists(harlock)
        self.assertIsNone(harlock.sector)

    def test_delete_sector__replace(self):
        "Set to another value."
        user = self.login_as_root_and_get()
        sector2 = Sector.objects.first()
        piracy = Sector.objects.create(title='Piracy')
        harlock = Contact.objects.create(
            user=user, first_name='Harlock', last_name='Matsumoto', sector=piracy,
        )

        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('persons', 'sector', piracy.id)
            ),
            data={'replace_persons__contact_sector': sector2.id},
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Sector).job
        job.type.execute(job)
        self.assertDoesNotExist(piracy)

        harlock = self.assertStillExists(harlock)
        self.assertEqual(sector2, harlock.sector)

    @skipIfCustomDocument
    def test_delete_image(self):
        "Set to NULL."
        user = self.login_as_root_and_get()
        image = self._create_image(user=user)
        harlock = Contact.objects.create(user=user, last_name='Matsumoto', image=image)

        image.delete()

        self.assertDoesNotExist(image)
        self.assertIsNone(self.refresh(harlock).image)

    def test_user_linked_contact(self):
        first_name = 'Deunan'
        last_name = 'Knut'
        count = Contact.objects.count()
        user = CremeUser.objects.create(
            username='dknut', last_name=last_name, first_name=first_name,
        )
        self.assertEqual(count + 1, Contact.objects.count())

        with self.assertNoException():
            contact = user.linked_contact

        self.assertIsInstance(contact, Contact)
        self.assertEqual(first_name, contact.first_name)
        self.assertEqual(last_name,  contact.last_name)

    def test_user_linked_contact__team(self):
        user = self.create_user(
            username='dknut', is_team=True, last_name='Knut', first_name='Deunan',
        )

        with self.assertNoException():
            contact = user.linked_contact

        self.assertIsNone(contact)

    def test_user_linked_contact__is_staff(self):
        count = Contact.objects.count()
        user = self.create_user(
            username='dknut', is_staff=True, last_name='Knut', first_name='Deunan',
        )
        self.assertEqual(count, Contact.objects.count())

        with self.assertNoException():
            contact = user.linked_contact

        self.assertIsNone(contact)

    def test_user_delete_is_user(self):
        "Manage Contact.is_user field: Contact is no more related to deleted user."
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        contact = user.linked_contact
        other_contact = other_user.linked_contact

        create_contact = Contact.objects.create
        deunan = create_contact(
            user=user, first_name='Deunan', last_name='Knut',
        )
        briareos = create_contact(
            user=other_user, first_name='Briareos', last_name='Hecatonchires',
        )

        self.assertNoFormError(self.client.post(
            reverse('creme_config__delete_user', args=(other_user.id,)),
            data={'to_user': user.id}
        ))
        self.assertDoesNotExist(other_user)
        self.assertStillExists(contact)

        other_contact = self.assertStillExists(other_contact)
        self.assertIsNone(other_contact.is_user)
        self.assertEqual(user, other_contact.user)

        self.assertStillExists(deunan)
        self.assertEqual(user, self.assertStillExists(briareos).user)

    @skipIfCustomOrganisation
    def test_get_employers(self):
        user = self.login_as_root_and_get()

        create_contact = partial(Contact.objects.create, user=user)
        deunan   = create_contact(first_name='Deunan',   last_name='Knut')
        briareos = create_contact(first_name='Briareos', last_name='Hecatonchires')

        create_orga = partial(Organisation.objects.create, user=user)
        eswat   = create_orga(name='ESWAT')
        olympus = create_orga(name='Olympus')
        deleted = create_orga(name='Deleted', is_deleted=True)
        club    = create_orga(name='Cyborg club')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=deunan,   type_id=REL_SUB_EMPLOYED_BY, object_entity=eswat)
        create_rel(subject_entity=deunan,   type_id=REL_SUB_MANAGES,     object_entity=olympus)
        create_rel(subject_entity=deunan,   type_id=REL_SUB_EMPLOYED_BY, object_entity=deleted)
        create_rel(subject_entity=briareos, type_id=REL_SUB_EMPLOYED_BY, object_entity=club)

        self.assertListEqual(
            [eswat, olympus],
            [*deunan.get_employers()],
        )

    @skipIfCustomUser
    def test_command_create_staffuser(self):
        from django.core.management import call_command

        from creme.creme_core.management.commands.creme_createstaffuser import (
            Command as StaffCommand,
        )

        super_user1 = self.get_alone_element(
            CremeUser.objects.filter(is_superuser=True, is_staff=False)
        )

        # This superuser should not be used
        username2 = 'kirika'
        self.assertLess(username2, super_user1.username)
        CremeUser.objects.create(
            username=username2, email='kirika@noir.jp',
            first_name='Kirika', last_name='Yumura',
            is_superuser=True,
        )

        username = 'staff1'
        first_name = 'John'
        last_name = 'Staffman'
        email = 'staffman@acme.com'

        with self.assertNoException():
            call_command(
                StaffCommand(),
                verbosity=0,
                interactive=False,
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
            )

        user = self.get_object_or_fail(CremeUser, username=username)
        self.assertEqual(first_name, user.first_name)
        self.assertEqual(last_name,  user.last_name)
        self.assertEqual(email,      user.email)
        self.assertIs(user.is_superuser, True)
        self.assertIs(user.is_staff, True)

        self.assertFalse(Contact.objects.filter(is_user=user))
