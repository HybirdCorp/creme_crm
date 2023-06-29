from functools import partial

from django.utils.translation import gettext as _

from creme.creme_core.models import FieldsConfig

from ..base import (
    Address,
    Organisation,
    _BaseTestCase,
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)


@skipIfCustomOrganisation
class OrganisationMergeTestCase(_BaseTestCase):
    @skipIfCustomAddress
    def test_merge01(self):
        "Merging addresses."
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='NERV')
        orga02 = create_orga(name='Nerv')

        create_address = Address.objects.create
        bill_addr01 = create_address(
            name='Billing address 01',
            address='BA1 - Address', po_box='BA1 - PO box',
            zipcode='BA1 - Zip code', city='BA1 - City',
            department='BA1 - Department',
            state='BA1 - State', country='BA1 - Country',
            owner=orga01,
        )
        ship_addr01 = create_address(
            name='Shipping address 01',
            address='SA1 - Address', po_box='SA1 - PO box',
            zipcode='SA1 - Zip code', city='SA1 - City',
            department='SA1 - Department',
            state='SA1 - State', country='SA1 - Country',
            owner=orga01,
        )
        other_addr01 = create_address(name='Other address 01', owner=orga01)
        orga01.billing_address = bill_addr01
        orga01.shipping_address = ship_addr01
        orga01.save()

        bill_addr02 = create_address(
            name='Billing address 02',
            address='BA2 - Address', po_box='BA2 - PO box',
            zipcode='BA2 - Zip code', city='BA2 - City',
            department='BA2 - Department',
            state='BA2 - State', country='BA2 - Country',
            owner=orga02,
        )
        ship_addr02 = create_address(
            name='Shipping address 02',
            address='SA2 - Address', po_box='SA2 - PO box',
            zipcode='SA2 - Zip code', city='SA2 - City',
            department='SA2 - Department',
            state='SA2 - State', country='SA2 - Country',
            owner=orga02,
        )
        other_addr02 = create_address(name='Other address 02', owner=orga02)

        orga02.billing_address = bill_addr02
        orga02.shipping_address = ship_addr02
        orga02.save()

        url = self.build_merge_url(orga01, orga02)
        response = self.assertGET200(url)

        with self.assertNoException():
            b_city_f = response.context['form'].fields['billaddr_city']

        self.assertFalse(b_city_f.required)
        self.assertListEqual(
            [bill_addr01.city,  bill_addr02.city,  bill_addr01.city],
            b_city_f.initial,
        )

        response = self.client.post(
            url, follow=True,
            data={
                'user_1':      user.id,
                'user_2':      user.id,
                'user_merged': user.id,

                'name_1':      orga01.name,
                'name_2':      orga02.name,
                'name_merged': orga01.name,

                # Billing address
                'billaddr_address_1':      bill_addr01.address,
                'billaddr_address_2':      bill_addr02.address,
                'billaddr_address_merged': bill_addr01.address,

                'billaddr_po_box_1':      bill_addr01.po_box,
                'billaddr_po_box_2':      bill_addr02.po_box,
                'billaddr_po_box_merged': bill_addr02.po_box,

                'billaddr_city_1':      bill_addr01.city,
                'billaddr_city_2':      bill_addr02.city,
                'billaddr_city_merged': 'Merged city',

                'billaddr_state_1':      bill_addr01.state,
                'billaddr_state_2':      bill_addr02.state,
                'billaddr_state_merged': 'Merged state',

                'billaddr_zipcode_1':      bill_addr01.zipcode,
                'billaddr_zipcode_2':      bill_addr02.zipcode,
                'billaddr_zipcode_merged': 'Merged zipcode',

                'billaddr_country_1':      bill_addr01.country,
                'billaddr_country_2':      bill_addr02.country,
                'billaddr_country_merged': 'Merged country',

                'billaddr_department_1':      bill_addr01.department,
                'billaddr_department_2':      bill_addr02.department,
                'billaddr_department_merged': 'Merged department',

                # Shipping address
                'shipaddr_address_1':      ship_addr01.address,
                'shipaddr_address_2':      ship_addr02.address,
                'shipaddr_address_merged': ship_addr01.address,

                'shipaddr_po_box_1':      ship_addr01.po_box,
                'shipaddr_po_box_2':      ship_addr02.po_box,
                'shipaddr_po_box_merged': ship_addr02.po_box,

                'shipaddr_city_1':      ship_addr01.city,
                'shipaddr_city_2':      ship_addr02.city,
                'shipaddr_city_merged': 'Merged city 2',

                'shipaddr_state_1':      ship_addr01.state,
                'shipaddr_state_2':      ship_addr02.state,
                'shipaddr_state_merged': 'Merged state 2',

                'shipaddr_zipcode_1':      ship_addr01.zipcode,
                'shipaddr_zipcode_2':      ship_addr02.zipcode,
                'shipaddr_zipcode_merged': 'Merged zipcode 2',

                'shipaddr_country_1':      ship_addr01.country,
                'shipaddr_country_2':      ship_addr02.country,
                'shipaddr_country_merged': 'Merged country 2',

                'shipaddr_department_1':      ship_addr01.department,
                'shipaddr_department_2':      ship_addr02.department,
                'shipaddr_department_merged': 'Merged department 2',
            },
        )
        self.assertNoFormError(response)

        self.assertDoesNotExist(orga02)

        with self.assertNoException():
            orga01 = self.refresh(orga01)

        addresses = Address.objects.filter(object_id=orga01.id)
        self.assertEqual(4, len(addresses))

        self.assertIn(bill_addr01,  addresses)
        self.assertIn(ship_addr01,  addresses)
        self.assertIn(other_addr01, addresses)
        self.assertIn(other_addr02, addresses)

        billing_address = orga01.billing_address
        self.assertEqual(bill_addr01,         billing_address)
        self.assertEqual(bill_addr01.address, billing_address.address)
        self.assertEqual(bill_addr02.po_box,  billing_address.po_box)
        self.assertEqual('Merged city',       billing_address.city)
        self.assertEqual('Merged state',      billing_address.state)
        self.assertEqual('Merged zipcode',    billing_address.zipcode)
        self.assertEqual('Merged country',    billing_address.country)
        self.assertEqual('Merged department', billing_address.department)

        shipping_address = orga01.shipping_address
        self.assertEqual(ship_addr01,           shipping_address)
        self.assertEqual(ship_addr02.po_box,    shipping_address.po_box)
        self.assertEqual('Merged city 2',       shipping_address.city)
        self.assertEqual('Merged state 2',      shipping_address.state)
        self.assertEqual('Merged zipcode 2',    shipping_address.zipcode)
        self.assertEqual('Merged country 2',    shipping_address.country)
        self.assertEqual('Merged department 2', shipping_address.department)

        self.assertDoesNotExist(bill_addr02)
        self.assertDoesNotExist(ship_addr02)

    @skipIfCustomAddress
    def test_merge02(self):
        "Merging addresses (no existing address)."
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='NERV')
        orga02 = create_orga(name='Nerv')

        response = self.client.post(
            self.build_merge_url(orga01, orga02),
            follow=True,
            data={
                'user_1':      user.id,
                'user_2':      user.id,
                'user_merged': user.id,

                'name_1':      orga01.name,
                'name_2':      orga02.name,
                'name_merged': orga01.name,

                # Billing address
                'billaddr_name_1':      '',
                'billaddr_name_2':      '',
                'billaddr_name_merged': 'Merged name',

                'billaddr_address_1':      '',
                'billaddr_address_2':      '',
                'billaddr_address_merged': 'Merged address',

                'billaddr_po_box_1':      '',
                'billaddr_po_box_2':      '',
                'billaddr_po_box_merged': 'Merged PO box',

                'billaddr_city_1':      '',
                'billaddr_city_2':      '',
                'billaddr_city_merged': 'Merged city',

                'billaddr_state_1':      '',
                'billaddr_state_2':      '',
                'billaddr_state_merged': 'Merged state',

                'billaddr_zipcode_1':      '',
                'billaddr_zipcode_2':      '',
                'billaddr_zipcode_merged': 'Merged zipcode',

                'billaddr_country_1':      '',
                'billaddr_country_2':      '',
                'billaddr_country_merged': 'Merged country',

                'billaddr_department_1':      '',
                'billaddr_department_2':      '',
                'billaddr_department_merged': 'Merged department',
            },
        )
        self.assertNoFormError(response)

        self.assertDoesNotExist(orga02)

        with self.assertNoException():
            orga01 = self.refresh(orga01)

        address = self.get_alone_element(Address.objects.filter(object_id=orga01.id))
        self.assertEqual(orga01.billing_address, address)
        self.assertEqual(_('Billing address'),   address.name)
        self.assertEqual('Merged address',       address.address)
        self.assertEqual('Merged PO box',        address.po_box)
        self.assertEqual('Merged city',          address.city)
        self.assertEqual('Merged state',         address.state)
        self.assertEqual('Merged zipcode',       address.zipcode)
        self.assertEqual('Merged country',       address.country)
        self.assertEqual('Merged department',    address.department)

        self.assertIsNone(orga01.shipping_address)

    @skipIfCustomAddress
    def test_merge03(self):
        "Merging addresses (existing address for one Organisation)."
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='NERV')
        orga02 = create_orga(name='Nerv')

        bill_addr01 = Address.objects.create(
            name='Billing address 01',
            address='BA1 - Address', po_box='BA1 - PO box',
            zipcode='BA1 - Zip code', city='BA1 - City',
            department='BA1 - Department',
            state='BA1 - State', country='BA1 - Country',
            owner=orga01,
        )
        orga01.billing_address = bill_addr01
        orga01.save()

        response = self.client.post(
            self.build_merge_url(orga01, orga02),
            follow=True,
            data={
                'user_1':      user.id,
                'user_2':      user.id,
                'user_merged': user.id,

                'name_1':      orga01.name,
                'name_2':      orga02.name,
                'name_merged': orga01.name,

                # Billing address
                'billaddr_name_1':      '',
                'billaddr_name_2':      '',
                'billaddr_name_merged': '',

                'billaddr_address_1':      '',
                'billaddr_address_2':      '',
                'billaddr_address_merged': '',

                'billaddr_po_box_1':      '',
                'billaddr_po_box_2':      '',
                'billaddr_po_box_merged': '',

                'billaddr_city_1':      '',
                'billaddr_city_2':      '',
                'billaddr_city_merged': '',

                'billaddr_state_1':      '',
                'billaddr_state_2':      '',
                'billaddr_state_merged': '',

                'billaddr_zipcode_1':      '',
                'billaddr_zipcode_2':      '',
                'billaddr_zipcode_merged': '',

                'billaddr_country_1':      '',
                'billaddr_country_2':      '',
                'billaddr_country_merged': '',

                'billaddr_department_1':      '',
                'billaddr_department_2':      '',
                'billaddr_department_merged': '',
            },
        )
        self.assertNoFormError(response)

        self.assertDoesNotExist(orga02)

        with self.assertNoException():
            orga01 = self.refresh(orga01)

        self.assertIsNone(orga01.shipping_address)

        merged_bill_addr = orga01.billing_address
        self.assertIsNotNone(merged_bill_addr)
        self.assertEqual(bill_addr01.id, merged_bill_addr.id)
        self.assertEqual(orga01, merged_bill_addr.owner)
        self.assertFalse(merged_bill_addr.address)
        self.assertFalse(merged_bill_addr.city)

    @skipIfCustomAddress
    def test_merge04(self):
        "FieldsConfig on Address sub-field."
        user = self.login_as_root_and_get()
        FieldsConfig.objects.create(
            content_type=Address,
            descriptions=[('po_box', {FieldsConfig.HIDDEN: True})],
        )

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='NERV')
        orga02 = create_orga(name='Nerv')

        response = self.assertGET200(self.build_merge_url(orga01, orga02))

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('billaddr_name', fields)  # Exclusion is hard-coded
        self.assertIn('billaddr_city', fields)
        self.assertIn('billaddr_country', fields)
        self.assertNotIn('billaddr_po_box', fields)  # Exclusion by configuration

    @skipIfCustomAddress
    def test_merge05(self):
        "FieldsConfig on 'billing_address' FK field."
        user = self.login_as_root_and_get()

        FieldsConfig.objects.create(
            content_type=Organisation,
            descriptions=[('billing_address', {FieldsConfig.HIDDEN: True})],
        )

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='NERV')
        orga02 = create_orga(name='Nerv')

        url = self.build_merge_url(orga01, orga02)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('billaddr_name',   fields)
        self.assertNotIn('billaddr_city',   fields)
        self.assertNotIn('billaddr_po_box', fields)

        response = self.client.post(
            url,
            follow=True,
            data={
                'user_1':      user.id,
                'user_2':      user.id,
                'user_merged': user.id,

                'name_1':      orga01.name,
                'name_2':      orga02.name,
                'name_merged': orga01.name,
            },
        )
        self.assertNoFormError(response)

    @skipIfCustomAddress
    def test_merge06(self):
        "FieldsConfig on 'shipping_address' FK field."
        user = self.login_as_root_and_get()

        FieldsConfig.objects.create(
            content_type=Organisation,
            descriptions=[('shipping_address', {FieldsConfig.HIDDEN: True})],
        )

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='NERV')
        orga02 = create_orga(name='Nerv')

        response = self.assertGET200(self.build_merge_url(orga01, orga02))

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('shipaddr_name',   fields)
        self.assertNotIn('shipaddr_city',   fields)
        self.assertNotIn('shipaddr_po_box', fields)

    def test_merge07(self):
        "The first organisation is managed."
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='NERV', is_managed=True)
        orga02 = create_orga(name='Nerv')

        response = self.client.post(
            self.build_merge_url(orga01, orga02),
            follow=True,
            data={
                'user_1':      user.id,
                'user_2':      user.id,
                'user_merged': user.id,

                'name_1':      orga01.name,
                'name_2':      orga02.name,
                'name_merged': orga02.name,
            },
        )
        self.assertNoFormError(response)
        self.assertDoesNotExist(orga02)

        orga01 = self.assertStillExists(orga01)
        self.assertEqual(orga02.name, orga01.name)
        self.assertTrue(orga01.is_managed)

    def test_merge08(self):
        "The second organisation is managed => swapped."
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='NERV')
        orga02 = create_orga(name='Nerv', is_managed=True)

        response = self.assertGET200(self.build_merge_url(orga01, orga02))

        with self.assertNoException():
            initial_name = response.context['form'].fields['name'].initial[0]

        self.assertEqual(orga02.name, initial_name)

    def test_merge09(self):
        "The 2 organisations are managed => no swap."
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user, is_managed=True)
        orga01 = create_orga(name='NERV')
        orga02 = create_orga(name='Nerv')

        response = self.assertGET200(self.build_merge_url(orga01, orga02))

        with self.assertNoException():
            initial_name = response.context['form'].fields['name'].initial[0]

        self.assertEqual(orga01.name, initial_name)
