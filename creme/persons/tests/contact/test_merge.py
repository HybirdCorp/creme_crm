# -*- coding: utf-8 -*-

from functools import partial

from django.utils.translation import gettext as _

from creme.creme_core.models import FieldsConfig

from ..base import (
    Address,
    Contact,
    _BaseTestCase,
    skipIfCustomAddress,
    skipIfCustomContact,
)


@skipIfCustomContact
class ContactMergeTestCase(_BaseTestCase):
    @skipIfCustomAddress
    def test_merge_addresses01(self):
        user = self.login()

        create_contact = partial(Contact.objects.create, user=user)
        contact01 = create_contact(first_name='Faye', last_name='Valentine')
        contact02 = create_contact(first_name='FAYE', last_name='VALENTINE')

        create_address = Address.objects.create
        bill_addr01 = create_address(
            name='Billing address 01',
            address='BA1 - Address', po_box='BA1 - PO box',
            zipcode='BA1 - Zip code', city='BA1 - City',
            department='BA1 - Department',
            state='BA1 - State', country='BA1 - Country',
            owner=contact01,
        )
        # NB: no shipping address for contact01
        contact01.billing_address = bill_addr01
        contact01.save()

        # NB: no billing address for contact02
        ship_addr02 = create_address(
            name='Shipping address 02',
            address='SA2 - Address', po_box='SA2 - PO box',
            zipcode='SA2 - Zip code', city='SA2 - City',
            department='SA2 - Department',
            state='SA2 - State', country='SA2 - Country',
            owner=contact02,
        )
        other_addr02 = create_address(name='Other address 02', owner=contact02)

        contact02.shipping_address = ship_addr02
        contact02.save()

        url = self.build_merge_url(contact01, contact02)
        context = self.client.get(url).context

        with self.assertNoException():
            fields = context['form'].fields
            f_baddr = fields['billaddr_address']

        self.assertIn('billaddr_city', fields)
        self.assertIn('shipaddr_city', fields)
        self.assertEqual([bill_addr01.address, '', bill_addr01.address], f_baddr.initial)
        self.assertNotIn('billaddr_name', fields)
        self.assertNotIn('shipaddr_name', fields)

        response = self.client.post(
            url, follow=True,
            data={
                'user_1':      user.id,
                'user_2':      user.id,
                'user_merged': user.id,

                'first_name_1':      contact01.first_name,
                'first_name_2':      contact02.first_name,
                'first_name_merged': contact01.first_name,

                'last_name_1':      contact01.last_name,
                'last_name_2':      contact02.last_name,
                'last_name_merged': contact01.last_name,

                # Billing address
                'billaddr_address_1':      bill_addr01.address,
                'billaddr_address_2':      '',
                'billaddr_address_merged': bill_addr01.address,

                'billaddr_po_box_1':      bill_addr01.po_box,
                'billaddr_po_box_2':      '',
                'billaddr_po_box_merged': 'Merged PO box',

                'billaddr_city_1':      bill_addr01.city,
                'billaddr_city_2':      '',
                'billaddr_city_merged': 'Merged city',

                'billaddr_state_1':      bill_addr01.state,
                'billaddr_state_2':      '',
                'billaddr_state_merged': 'Merged state',

                'billaddr_zipcode_1':      bill_addr01.zipcode,
                'billaddr_zipcode_2':      '',
                'billaddr_zipcode_merged': 'Merged zipcode',

                'billaddr_country_1':      bill_addr01.country,
                'billaddr_country_2':      '',
                'billaddr_country_merged': 'Merged country',

                'billaddr_department_1':      bill_addr01.department,
                'billaddr_department_2':      '',
                'billaddr_department_merged': 'Merged department',

                # Shipping address
                'shipaddr_address_1':      '',
                'shipaddr_address_2':      ship_addr02.address,
                'shipaddr_address_merged': ship_addr02.address,

                'shipaddr_po_box_1':      '',
                'shipaddr_po_box_2':      ship_addr02.po_box,
                'shipaddr_po_box_merged': 'Merged PO box 2',

                'shipaddr_city_1':      '',
                'shipaddr_city_2':      ship_addr02.city,
                'shipaddr_city_merged': 'Merged city 2',

                'shipaddr_state_1':      '',
                'shipaddr_state_2':      ship_addr02.state,
                'shipaddr_state_merged': 'Merged state 2',

                'shipaddr_zipcode_1':      '',
                'shipaddr_zipcode_2':      ship_addr02.zipcode,
                'shipaddr_zipcode_merged': 'Merged zipcode 2',

                'shipaddr_country_1':      '',
                'shipaddr_country_2':      ship_addr02.country,
                'shipaddr_country_merged': 'Merged country 2',

                'shipaddr_department_1':      '',
                'shipaddr_department_2':      ship_addr02.department,
                'shipaddr_department_merged': 'Merged department 2',
            },
        )
        self.assertNoFormError(response)
        self.assertDoesNotExist(contact02)

        with self.assertNoException():
            contact01 = self.refresh(contact01)

        addresses = Address.objects.filter(object_id=contact01.id)
        self.assertEqual(3, len(addresses))

        self.assertIn(bill_addr01,  addresses)
        self.assertIn(ship_addr02,  addresses)
        self.assertIn(other_addr02, addresses)

        billing_address = contact01.billing_address
        self.assertEqual(bill_addr01,         billing_address)
        self.assertEqual(bill_addr01.name,    billing_address.name)
        self.assertEqual(bill_addr01.address, billing_address.address)
        self.assertEqual('Merged PO box',     billing_address.po_box)
        self.assertEqual('Merged city',       billing_address.city)
        self.assertEqual('Merged state',      billing_address.state)
        self.assertEqual('Merged zipcode',    billing_address.zipcode)
        self.assertEqual('Merged country',    billing_address.country)
        self.assertEqual('Merged department', billing_address.department)

        shipping_address = contact01.shipping_address
        self.assertEqual(ship_addr02,           shipping_address)
        self.assertEqual(contact01,             shipping_address.owner)
        self.assertEqual(ship_addr02.name,      shipping_address.name)
        self.assertEqual('Merged PO box 2',     shipping_address.po_box)
        self.assertEqual('Merged city 2',       shipping_address.city)
        self.assertEqual('Merged state 2',      shipping_address.state)
        self.assertEqual('Merged zipcode 2',    shipping_address.zipcode)
        self.assertEqual('Merged country 2',    shipping_address.country)
        self.assertEqual('Merged department 2', shipping_address.department)

    @skipIfCustomAddress
    def test_merge_addresses02(self):
        "Merging addresses -> empty addresses."
        user = self.login()

        create_contact = partial(Contact.objects.create, user=user)
        contact01 = create_contact(first_name='Faye', last_name='Valentine')
        contact02 = create_contact(first_name='FAYE', last_name='VALENTINE')

        ship_addr02 = Address.objects.create(
            name='Shipping address 02',
            address='SA2 - Address', po_box='SA2 - PO box',
            zipcode='SA2 - Zip code', city='SA2 - City',
            department='SA2 - Department',
            state='SA2 - State', country='SA2 - Country',
            owner=contact02,
        )
        contact02.shipping_address = ship_addr02
        contact02.save()

        response = self.client.post(
            self.build_merge_url(contact01, contact02),
            follow=True,
            data={
                'user_1':      user.id,
                'user_2':      user.id,
                'user_merged': user.id,

                'first_name_1':      contact01.first_name,
                'first_name_2':      contact02.first_name,
                'first_name_merged': contact01.first_name,

                'last_name_1':      contact01.last_name,
                'last_name_2':      contact02.last_name,
                'last_name_merged': contact01.last_name,

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

                # Shipping address
                'shipaddr_name_1':      '',
                'shipaddr_name_2':      ship_addr02.name,
                'shipaddr_name_merged': '',

                'shipaddr_address_1':      '',
                'shipaddr_address_2':      ship_addr02.address,
                'shipaddr_address_merged': '',

                'shipaddr_po_box_1':      '',
                'shipaddr_po_box_2':      ship_addr02.po_box,
                'shipaddr_po_box_merged': '',

                'shipaddr_city_1':      '',
                'shipaddr_city_2':      ship_addr02.city,
                'shipaddr_city_merged': '',

                'shipaddr_state_1':      '',
                'shipaddr_state_2':      ship_addr02.state,
                'shipaddr_state_merged': '',

                'shipaddr_zipcode_1':      '',
                'shipaddr_zipcode_2':      ship_addr02.zipcode,
                'shipaddr_zipcode_merged': '',

                'shipaddr_country_1':      '',
                'shipaddr_country_2':      ship_addr02.country,
                'shipaddr_country_merged': '',

                'shipaddr_department_1':      '',
                'shipaddr_department_2':      ship_addr02.department,
                'shipaddr_department_merged': '',
            },
        )
        self.assertNoFormError(response)
        self.assertDoesNotExist(contact02)

        with self.assertNoException():
            contact01 = self.refresh(contact01)

        self.assertIsNone(contact01.billing_address)

        merged_ship_addr = contact01.shipping_address
        self.assertIsNotNone(merged_ship_addr)
        self.assertEqual(ship_addr02.id, merged_ship_addr.id)
        self.assertEqual(contact01, merged_ship_addr.owner)
        self.assertFalse(merged_ship_addr.address)
        self.assertFalse(merged_ship_addr.city)

    @skipIfCustomAddress
    def test_merge_addresses03(self):
        "FieldsConfig.REQUIRED => validation on not empty addresses only."
        user = self.login()

        r_field = 'city'
        FieldsConfig.objects.create(
            content_type=Address,
            descriptions=[
                (r_field, {FieldsConfig.REQUIRED: True}),
            ],
        )

        create_contact = partial(Contact.objects.create, user=user)
        contact01 = create_contact(first_name='Faye', last_name='Valentine')
        contact02 = create_contact(first_name='FAYE', last_name='VALENTINE')

        url = self.build_merge_url(contact01, contact02)

        # ---
        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields
            last_name_f = fields['last_name']
            baddr_city_f = fields['billaddr_city']

        self.assertTrue(last_name_f.required)
        self.assertFalse(baddr_city_f.required)

        # ---
        addr_value = '6 BlackJack street'
        data = {
            'user_1':      user.id,
            'user_2':      user.id,
            'user_merged': user.id,

            'first_name_1':      contact01.first_name,
            'first_name_2':      contact02.first_name,
            'first_name_merged': contact01.first_name,

            'last_name_1':      contact01.last_name,
            'last_name_2':      contact02.last_name,
            'last_name_merged': contact01.last_name,

            # Billing address
            'billaddr_address_1':      '',
            'billaddr_address_2':      '',
            'billaddr_address_merged': addr_value,

            'billaddr_city_1':      '',
            'billaddr_city_2':      '',
            'billaddr_city_merged': '',
        }

        response2 = self.assertPOST200(url, follow=True, data=data)
        self.assertFormError(
            response2, 'form', f'billaddr_{r_field}',
            _('The field «{}» has been configured as required.').format(_('City')),
        )

        city = 'Big blue'
        response3 = self.client.post(
            url,
            follow=True,
            data={
                **data,
                'billaddr_city_merged': city,
            }
        )
        self.assertNoFormError(response3)

        with self.assertNoException():
            merged_bill_addr = self.refresh(contact01).billing_address

        self.assertEqual(addr_value, merged_bill_addr.address)
        self.assertEqual(city,       merged_bill_addr.city)

    def test_merge_user_contact01(self):
        "Merge 1 Contact which represents a user with another Contact."
        user = self.login()

        contact01 = user.linked_contact
        first_name1 = contact01.first_name
        last_name2 = 'VALENTINE'
        contact02 = Contact.objects.create(user=user, first_name='FAYE', last_name=last_name2)

        url = self.build_merge_url(contact01, contact02)
        self.assertGET200(url)

        data = {
            'user_1':      user.id,
            'user_2':      user.id,
            'user_merged': user.id,

            'first_name_1':      first_name1,
            'first_name_2':      contact02.first_name,
            'first_name_merged': first_name1,

            'last_name_1':      contact01.last_name,
            'last_name_2':      last_name2,
            'last_name_merged': last_name2,

            'email_1':      contact01.email,
            'email_2':      contact02.email,
            'email_merged': '',
        }
        response = self.assertPOST200(url, follow=True, data=data)
        self.assertFormError(
            response, 'form', None,
            _('This Contact is related to a user and must have an e-mail address.'),
        )

        response = self.client.post(
            url, follow=True, data={**data, 'email_merged': contact01.email},
        )
        self.assertNoFormError(response)

        self.assertDoesNotExist(contact02)

        with self.assertNoException():
            contact01 = self.refresh(contact01)
            user = self.refresh(user)

        self.assertEqual(user,        contact01.is_user)
        self.assertEqual(first_name1, user.first_name)
        self.assertEqual(last_name2,  user.last_name)

    def test_merge_user_contact02(self):
        "Merge 1 Contact with another one which represents a user (entity swap)."
        user = self.login()

        first_name1 = 'FAYE'
        contact01 = Contact.objects.create(
            user=user, first_name=first_name1, last_name='VALENTINE',
        )
        contact02 = user.linked_contact

        url = self.build_merge_url(contact01, contact02)
        response = self.assertGET200(url)

        with self.assertNoException():
            first_name_f = response.context['form'].fields['first_name']

        self.assertListEqual(
            [
                # The entities have been swapped (to keep the user-contact first)
                contact02.first_name,
                contact01.first_name,
                contact02.first_name,
            ],
            first_name_f.initial,
        )

        data = {
            'user_1':      user.id,
            'user_2':      user.id,
            'user_merged': user.id,

            'first_name_1':      contact02.first_name,
            'first_name_2':      first_name1,
            'first_name_merged': first_name1,

            'last_name_1':      contact02.last_name,
            'last_name_2':      contact01.last_name,
            'last_name_merged': contact01.last_name,
        }
        response = self.assertPOST200(url, follow=True, data=data)
        self.assertFormError(
            response, 'form', None,
            _('This Contact is related to a user and must have an e-mail address.'),
        )

        response = self.client.post(
            url,
            follow=True,
            data={
                **data,
                'email_1':      contact02.email,
                'email_2':      contact01.email,
                'email_merged': contact02.email,
            },
        )
        self.assertNoFormError(response)

        self.assertDoesNotExist(contact01)

        with self.assertNoException():
            contact02 = self.refresh(contact02)

        self.assertEqual(user,        contact02.is_user)
        self.assertEqual(first_name1, contact02.first_name)

    def test_merge_user_contact03(self):
        "Cannot merge 2 Contacts that represent 2 users."
        user = self.login()

        contact01 = user.linked_contact
        contact02 = self.other_user.linked_contact

        self.assertGET409(self.build_merge_url(contact01, contact02))
        self.assertGET409(self.build_merge_url(contact02, contact01))
