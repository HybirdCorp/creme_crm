from functools import partial

from django.test.utils import override_settings
from django.urls import reverse

from creme.creme_core.models import Relation
from creme.persons import constants
from creme.persons.models import LegalForm, Sector, StaffSize

from ..base import (
    Address,
    Contact,
    Organisation,
    _PersonsTestCase,
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)


@skipIfCustomOrganisation
class OrganisationTestCase(_PersonsTestCase):
    # TODO: separated test case?
    def test_staff_size(self):
        count = StaffSize.objects.count()

        create_size = StaffSize.objects.create
        size1 = create_size(size='4 and a dog')
        size2 = create_size(size='1 wolf & 1 cub')
        self.assertEqual(count + 1, size1.order)
        self.assertEqual(count + 2, size2.order)

    def _build_managed_orga(self, user, name='Bebop'):
        return Organisation.objects.create(user=user, name=name, is_managed=True)

    def test_manager_filter_managed_by_creme(self):
        user = self.login_as_root_and_get()

        mng_orga1 = self._build_managed_orga(user=user)
        mng_orga2 = self._build_managed_orga(user=user, name='NERV')
        orga = Organisation.objects.create(user=user, name='Seele')

        with self.assertNumQueries(1):
            qs1 = Organisation.objects.filter_managed_by_creme()
            mng_orgas = {*qs1}

        self.assertIn(mng_orga1, mng_orgas)
        self.assertIn(mng_orga2, mng_orgas)
        self.assertNotIn(orga,   mng_orgas)

        # Test request-cache
        with self.assertNumQueries(0):
            qs2 = Organisation.objects.filter_managed_by_creme()
            [*qs2]  # NOQA

        self.assertEqual(id(qs1), id(qs2))

    def test_empty_fields(self):
        user = self.login_as_root_and_get()

        with self.assertNoException():
            orga = Organisation.objects.create(user=user, name='Nerv')

        self.assertEqual('', orga.description)

        self.assertEqual('', orga.phone)
        self.assertEqual('', orga.fax)
        self.assertEqual('', orga.email)
        self.assertEqual('', orga.url_site)

        self.assertEqual('', orga.annual_revenue)

        self.assertEqual('', orga.siren)
        self.assertEqual('', orga.naf)
        self.assertEqual('', orga.siret)
        self.assertEqual('', orga.rcs)

        self.assertEqual('', orga.tvaintra)
        self.assertEqual('', orga.eori)

    @skipIfCustomAddress
    def test_clone(self):
        "Addresses are problematic."
        user = self.login_as_root_and_get()

        bebop = Organisation.objects.create(user=user, name='Bebop')

        create_address = partial(
            Address.objects.create,
            address='XXX',
            city='Red city', state='North', zipcode='111',
            country='Mars', department='Dome #12',
            owner=bebop,
        )
        bebop.billing_address  = create_address(name='Hideout #1')
        bebop.shipping_address = create_address(name='Hideout #2')
        bebop.save()

        for i in range(3, 5):
            create_address(name=f'Hideout #{i}')

        url = reverse('creme_core__clone_entity')
        self.assertEqual(url, bebop.get_clone_absolute_url())

        self.assertPOST200(url, data={'id': bebop.id}, follow=True)
        cloned = Organisation.objects.order_by('-id').first()

        self.assertEqual(bebop.name, cloned.name)
        self.assertFalse(cloned.is_managed)

        self.assertEqual(bebop.id, bebop.billing_address.object_id)
        self.assertEqual(bebop.id, bebop.shipping_address.object_id)

        self.assertEqual(cloned.id, cloned.billing_address.object_id)
        self.assertEqual(cloned.id, cloned.shipping_address.object_id)

        addresses   = [*Address.objects.filter(object_id=bebop.id)]
        c_addresses = [*Address.objects.filter(object_id=cloned.id)]
        self.assertEqual(4, len(addresses))
        self.assertEqual(4, len(c_addresses))

        addresses_map   = {a.name: a for a in addresses}
        c_addresses_map = {a.name: a for a in c_addresses}
        self.assertEqual(4, len(addresses_map))
        self.assertEqual(4, len(c_addresses_map))

        for ident, address in addresses_map.items():
            address2 = c_addresses_map.get(ident)
            self.assertIsNotNone(address2, ident)
            self.assertAddressOnlyContentEqual(address, address2)

    # def test_clone__managed(self):  # DEPRECATED
    #     "Do not clone 'is_managed'."
    #     user = self.login_as_root_and_get()
    #     bebop = Organisation.objects.create(user=user, name='Bebop', is_managed=True)
    #     self.assertPOST409(
    #         bebop.get_clone_absolute_url(), data={'id': bebop.id}, follow=True,
    #     )
    #
    #     cloned = bebop.clone()
    #     self.assertEqual(bebop.name, cloned.name)
    #     self.assertFalse(cloned.is_managed)
    #
    # @skipIfCustomAddress
    # def test_clone__method(self):  # DEPRECATED
    #     "Addresses are problematic."
    #     user = self.login_as_root_and_get()
    #
    #     bebop = Organisation.objects.create(user=user, name='Bebop')
    #
    #     create_address = partial(
    #         Address.objects.create,
    #         address='XXX',
    #         city='Red city', state='North', zipcode='111',
    #         country='Mars', department='Dome #12',
    #         owner=bebop,
    #     )
    #     bebop.billing_address  = create_address(name='Hideout #1')
    #     bebop.shipping_address = create_address(name='Hideout #2')
    #     bebop.save()
    #
    #     for i in range(3, 5):
    #         create_address(name=f'Hideout #{i}')
    #
    #     self.assertEqual(
    #         reverse('creme_core__clone_entity'),
    #         bebop.get_clone_absolute_url(),
    #     )
    #
    #     cloned = bebop.clone()
    #
    #     self.assertEqual(bebop.name, cloned.name)
    #     self.assertFalse(cloned.is_managed)
    #
    #     self.assertEqual(bebop.id, bebop.billing_address.object_id)
    #     self.assertEqual(bebop.id, bebop.shipping_address.object_id)
    #
    #     self.assertEqual(cloned.id, cloned.billing_address.object_id)
    #     self.assertEqual(cloned.id, cloned.shipping_address.object_id)
    #
    #     addresses   = [*Address.objects.filter(object_id=bebop.id)]
    #     c_addresses = [*Address.objects.filter(object_id=cloned.id)]
    #     self.assertEqual(4, len(addresses))
    #     self.assertEqual(4, len(c_addresses))
    #
    #     addresses_map   = {a.name: a for a in addresses}
    #     c_addresses_map = {a.name: a for a in c_addresses}
    #     self.assertEqual(4, len(addresses_map))
    #     self.assertEqual(4, len(c_addresses_map))
    #
    #     for ident, address in addresses_map.items():
    #         address2 = c_addresses_map.get(ident)
    #         self.assertIsNotNone(address2, ident)
    #         self.assertAddressOnlyContentEqual(address, address2)

    def test_get_employees(self):
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Bebop')
        orga2 = create_orga(name='Red tail')

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Spike',   last_name='Spiegel')
        c2 = create_contact(first_name='Jet',     last_name='Black')
        c3 = create_contact(first_name='Faye',    last_name='Valentine')
        c4 = create_contact(first_name='Edward',  last_name='Wong')
        c5 = create_contact(first_name='Number2', last_name='Droid', is_deleted=True)

        create_relation = partial(
            Relation.objects.create,
            user=user, type_id=constants.REL_SUB_EMPLOYED_BY,
        )
        create_relation(subject_entity=c1, object_entity=orga1)
        create_relation(subject_entity=c2, object_entity=orga1)
        create_relation(subject_entity=c3, object_entity=orga1, type_id=constants.REL_SUB_MANAGES)
        create_relation(subject_entity=c4, object_entity=orga2)
        create_relation(subject_entity=c5, object_entity=orga1)

        self.assertListEqual([c2, c1], [*orga1.get_employees()])

    def test_get_managers(self):
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Bebop')
        orga2 = create_orga(name='Red tail')

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Spike',   last_name='Spiegel')
        c2 = create_contact(first_name='Jet',     last_name='Black')
        c3 = create_contact(first_name='Faye',    last_name='Valentine')
        c4 = create_contact(first_name='Edward',  last_name='Wong')
        c5 = create_contact(first_name='Number2', last_name='Droid', is_deleted=True)

        create_relation = partial(
            Relation.objects.create,
            user=user, type_id=constants.REL_SUB_MANAGES,
        )
        create_relation(subject_entity=c1, object_entity=orga1)
        create_relation(subject_entity=c2, object_entity=orga1)
        create_relation(
            subject_entity=c3, object_entity=orga1, type_id=constants.REL_SUB_EMPLOYED_BY,
        )
        create_relation(subject_entity=c4, object_entity=orga2)
        create_relation(subject_entity=c5, object_entity=orga1)

        self.assertListEqual([c2, c1], [*orga1.get_managers()])

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete(self):
        user = self.login_as_root_and_get()
        orga01 = Organisation.objects.create(user=user, name='Nerv')
        url = orga01.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        with self.assertNoException():
            orga01 = self.refresh(orga01)

        self.assertIs(orga01.is_deleted, True)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(orga01)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete__one_managed(self):
        "Cannot delete the last managed organisation."
        self.login_as_root()

        managed_orga = self.get_alone_element(Organisation.objects.filter(is_managed=True))
        self.assertPOST409(managed_orga.get_delete_absolute_url())  # follow=True
        self.assertStillExists(managed_orga)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete__several_managed(self):
        "A managed organisation can be deleted if it's not the last one."
        user = self.login_as_root_and_get()

        managed_orga = Organisation.objects.create(user=user, name='Nerv', is_managed=True)
        url = managed_orga.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        with self.assertNoException():
            managed_orga = self.refresh(managed_orga)

        self.assertIs(managed_orga.is_deleted, True)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(managed_orga)

    def test_delete_sector__set_null(self):
        "Set to NULL."
        user = self.login_as_root_and_get()
        hunting = Sector.objects.create(title='Bounty hunting')
        bebop = Organisation.objects.create(user=user, name='Bebop', sector=hunting)

        response = self.client.post(reverse(
            'creme_config__delete_instance',
            args=('persons', 'sector', hunting.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Sector).job
        job.type.execute(job)
        self.assertDoesNotExist(hunting)

        bebop = self.assertStillExists(bebop)
        self.assertIsNone(bebop.sector)

    def test_delete_sector__replace(self):
        "Set to another value."
        user = self.login_as_root_and_get()
        sector2 = Sector.objects.first()
        hunting = Sector.objects.create(title='Bounty hunting')
        bebop = Organisation.objects.create(user=user, name='Bebop', sector=hunting)

        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('persons', 'sector', hunting.id),
            ),
            data={'replace_persons__organisation_sector': sector2.id},
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Sector).job
        job.type.execute(job)
        self.assertDoesNotExist(hunting)

        bebop = self.assertStillExists(bebop)
        self.assertEqual(sector2, bebop.sector)

    def test_delete_legal_form__set_null(self):
        "Set to NULL."
        user = self.login_as_root_and_get()
        band = LegalForm.objects.create(title='Bounty hunting band')
        bebop = Organisation.objects.create(user=user, name='Bebop', legal_form=band)

        response = self.client.post(reverse(
            'creme_config__delete_instance',
            args=('persons', 'legal_form', band.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(LegalForm).job
        job.type.execute(job)
        self.assertDoesNotExist(band)

        bebop = self.assertStillExists(bebop)
        self.assertIsNone(bebop.legal_form)

    def test_delete_legal_form__replace(self):
        "Set to another value."
        user = self.login_as_root_and_get()
        lform2 = LegalForm.objects.first()
        band = LegalForm.objects.create(title='Bounty hunting band')
        bebop = Organisation.objects.create(user=user, name='Bebop', legal_form=band)

        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('persons', 'legal_form', band.id)
            ),
            data={'replace_persons__organisation_legal_form': lform2.id},
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(LegalForm).job
        job.type.execute(job)
        self.assertDoesNotExist(band)

        bebop = self.assertStillExists(bebop)
        self.assertEqual(lform2, bebop.legal_form)

    def test_delete_staff_size__set_null(self):
        "Set to NULL."
        user = self.login_as_root_and_get()
        size = StaffSize.objects.create(size='4 and a dog')
        bebop = Organisation.objects.create(user=user, name='Bebop', staff_size=size)

        response = self.client.post(reverse(
            'creme_config__delete_instance',
            args=('persons', 'staff_size', size.id)
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(StaffSize).job
        job.type.execute(job)
        self.assertDoesNotExist(size)

        bebop = self.assertStillExists(bebop)
        self.assertIsNone(bebop.staff_size)

    def test_delete_staff_size__replace(self):
        "Set to another value."
        user = self.login_as_root_and_get()
        size2 = StaffSize.objects.first()
        size = StaffSize.objects.create(size='4 and a dog')
        bebop = Organisation.objects.create(user=user, name='Bebop', staff_size=size)

        response = self.client.post(
            reverse(
                'creme_config__delete_instance', args=('persons', 'staff_size', size.id)
            ),
            data={'replace_persons__organisation_staff_size': size2.id},
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(StaffSize).job
        job.type.execute(job)
        self.assertDoesNotExist(size)

        bebop = self.assertStillExists(bebop)
        self.assertEqual(size2, bebop.staff_size)
