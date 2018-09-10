# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.urls import reverse
    from django.utils.translation import ugettext as _, ungettext

    from creme.creme_core.tests.views.base import CSVImportBaseTestCaseMixin
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import Relation, SetCredentials, FieldsConfig

    from .base import (_BaseTestCase, skipIfCustomAddress, skipIfCustomContact,
            skipIfCustomOrganisation, Organisation, Address, Contact)

    from .. import constants
    from ..models import StaffSize, Sector, LegalForm
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


@skipIfCustomOrganisation
class OrganisationTestCase(_BaseTestCase, CSVImportBaseTestCaseMixin):
    lv_import_data = {
            'step':     1,
            # 'document': doc.id, 'user': self.user.id,
            'name_colselect': 1,

            'sector_colselect':         0,
            'creation_date_colselect':  0,
            'staff_size_colselect':     0,
            'email_colselect':          0,
            'fax_colselect':            0,
            'phone_colselect':          0,
            'description_colselect':    0,
            'siren_colselect':          0,
            'naf_colselect':            0,
            'annual_revenue_colselect': 0,
            'url_site_colselect':       0,
            'legal_form_colselect':     0,
            'rcs_colselect':            0,
            'tvaintra_colselect':       0,
            'subject_to_vat_colselect': 0,
            'capital_colselect':        0,
            'siret_colselect':          0,

            # 'property_types', 'fixed_relations', 'dyn_relations',

            'billaddr_address_colselect':    0,   'shipaddr_address_colselect':    0,
            'billaddr_po_box_colselect':     0,   'shipaddr_po_box_colselect':     0,
            'billaddr_city_colselect':       0,   'shipaddr_city_colselect':       0,
            'billaddr_state_colselect':      0,   'shipaddr_state_colselect':      0,
            'billaddr_zipcode_colselect':    0,   'shipaddr_zipcode_colselect':    0,
            'billaddr_country_colselect':    0,   'shipaddr_country_colselect':    0,
            'billaddr_department_colselect': 0,   'shipaddr_department_colselect': 0,
        }

    def test_empty_fields(self):
        user = self.login()

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

    def test_populated_orga_uuid(self):
        first_orga = Organisation.objects.order_by('id').first()
        self.assertIsNotNone(first_orga)
        self.assertTrue(first_orga.is_managed)
        self.assertEqual(constants.UUID_FIRST_ORGA, str(first_orga.uuid))

    def test_staff_size(self):
        count = StaffSize.objects.count()

        create_size = StaffSize.objects.create
        size1 = create_size(size='4 and a dog')
        size2 = create_size(size='1 wolf & 1 cub')
        self.assertEqual(count + 1, size1.order)
        self.assertEqual(count + 2, size2.order)

    def test_createview01(self):
        user = self.login()

        url = reverse('persons__create_organisation')
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'persons/add_organisation_form.html')

        count = Organisation.objects.count()
        name  = 'Spectre'
        description = 'DESCRIPTION'
        response = self.client.post(url, follow=True,
                                    data={'user':        user.pk,
                                          'name':        name,
                                          'description': description,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(count + 1, Organisation.objects.count())

        orga = self.get_object_or_fail(Organisation, name=name)
        self.assertEqual(description, orga.description)
        self.assertIsNone(orga.billing_address)
        self.assertIsNone(orga.shipping_address)

        self.assertRedirects(response, orga.get_absolute_url())

    @skipIfCustomAddress
    def test_createview02(self):
        "With addresses"
        user = self.login()

        name = 'Bebop'

        b_address = 'Mars gate'
        b_po_box = 'Mars1233546'
        b_zipcode = '9874541'
        b_city = 'Redsand'
        b_department = 'Great crater'
        b_state = 'State#3'
        b_country = 'Terran federation'

        s_address = 'Mars gate (bis)'
        response = self.client.post(reverse('persons__create_organisation'), follow=True,
                                    data={'user': user.pk,
                                          'name': name,

                                          'billing_address-address':    b_address,
                                          'billing_address-po_box':     b_po_box,
                                          'billing_address-zipcode':    b_zipcode,
                                          'billing_address-city':       b_city,
                                          'billing_address-department': b_department,
                                          'billing_address-state':      b_state,
                                          'billing_address-country':    b_country,

                                          'shipping_address-address': s_address,
                                         }
                                   )
        self.assertNoFormError(response)

        orga = self.get_object_or_fail(Organisation, name=name)

        billing_address = orga.billing_address
        self.assertIsNotNone(billing_address)
        self.assertEqual(b_address,    billing_address.address)
        self.assertEqual(b_po_box,     billing_address.po_box)
        self.assertEqual(b_zipcode,    billing_address.zipcode)
        self.assertEqual(b_city,       billing_address.city)
        self.assertEqual(b_department, billing_address.department)
        self.assertEqual(b_state,      billing_address.state)
        self.assertEqual(b_country,    billing_address.country)

        self.assertEqual(s_address, orga.shipping_address.address)

        self.assertContains(response, b_address)
        self.assertContains(response, s_address)

    @skipIfCustomAddress
    def test_createview03(self):
        "FieldsConfig on Address sub-fields"
        user = self.login()
        FieldsConfig.create(Address,
                            descriptions=[('po_box', {FieldsConfig.HIDDEN: True})],
                           )

        response = self.assertGET200(reverse('persons__create_organisation'))

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertIn('name', fields)
        self.assertIn('billing_address-address', fields)
        self.assertNotIn('billing_address-po_box',  fields)

        name = 'Bebop'

        b_address = 'Mars gate'
        b_po_box = 'Mars1233546'
        b_zipcode = '9874541'
        b_city = 'Redsand'
        b_department = 'Great crater'
        b_state = 'State#3'
        b_country = 'Terran federation'

        response = self.client.post(reverse('persons__create_organisation'), follow=True,
                                    data={'user': user.pk,
                                          'name': name,

                                          'billing_address-address':    b_address,
                                          'billing_address-po_box':     b_po_box,  # <== should not be used
                                          'billing_address-zipcode':    b_zipcode,
                                          'billing_address-city':       b_city,
                                          'billing_address-department': b_department,
                                          'billing_address-state':      b_state,
                                          'billing_address-country':    b_country,
                                         }
                                   )
        self.assertNoFormError(response)

        orga = self.get_object_or_fail(Organisation, name=name)
        billing_address = orga.billing_address
        self.assertIsNotNone(billing_address)
        self.assertEqual(b_address,    billing_address.address)
        self.assertEqual(b_zipcode,    billing_address.zipcode)
        self.assertEqual(b_city,       billing_address.city)
        self.assertEqual(b_department, billing_address.department)
        self.assertEqual(b_state,      billing_address.state)
        self.assertEqual(b_country,    billing_address.country)

        self.assertFalse(billing_address.po_box)

    @skipIfCustomAddress
    def test_createview04(self):
        "FieldsConfig on 'billing_address' FK field"
        self.login()
        FieldsConfig.create(Organisation,
                            descriptions=[('billing_address', {FieldsConfig.HIDDEN: True})],
                           )

        response = self.assertGET200(reverse('persons__create_organisation'))

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertIn('name', fields)
        self.assertNotIn('billing_address-address', fields)
        self.assertNotIn('billing_address-po_box',  fields)

    @skipIfCustomAddress
    def test_editview01(self):
        user = self.login()

        name = 'Bebop'
        orga = Organisation.objects.create(user=user, name=name)
        url = orga.get_edit_absolute_url()
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'persons/edit_organisation_form.html')

        name += '_edited'
        zipcode = '123456'
        response = self.client.post(url, follow=True,
                                    data={'user':                    user.pk,
                                          'name':                    name,
                                          'billing_address-zipcode': zipcode,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertRedirects(response, orga.get_absolute_url())

        edited_orga = self.refresh(orga)
        self.assertEqual(name, edited_orga.name)
        self.assertIsNotNone(edited_orga.billing_address)
        self.assertEqual(zipcode, edited_orga.billing_address.zipcode)

    def test_listview(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        nerv = create_orga(name='Nerv')
        acme = create_orga(name='Acme')

        response = self.assertGET200(Organisation.get_lv_absolute_url())

        with self.assertNoException():
            orgas_page = response.context['entities']

        self.assertEqual(3, orgas_page.paginator.count)  # 3: our 2 orgas + default orga

        orgas_set = set(orgas_page.object_list)
        self.assertIn(nerv, orgas_set)
        self.assertIn(acme, orgas_set)

    @skipIfCustomAddress
    def test_clone(self):
        "Addresses are problematic"
        user = self.login()

        bebop = Organisation.objects.create(user=user, name='Bebop')

        create_address = partial(Address.objects.create, address='XXX',
                                 city='Red city', state='North', zipcode='111',
                                 country='Mars', department='Dome #12',
                                 owner=bebop,
                                )
        bebop.billing_address  = create_address(name='Hideout #1')
        bebop.shipping_address = create_address(name='Hideout #2')
        bebop.save()

        for i in range(3, 5):
            create_address(name='Hideout #{}'.format(i))

        cloned = bebop.clone()

        self.assertEqual(bebop.name, cloned.name)

        self.assertEqual(bebop.id, bebop.billing_address.object_id)
        self.assertEqual(bebop.id, bebop.shipping_address.object_id)

        self.assertEqual(cloned.id, cloned.billing_address.object_id)
        self.assertEqual(cloned.id, cloned.shipping_address.object_id)

        addresses   = list(Address.objects.filter(object_id=bebop.id))
        c_addresses = list(Address.objects.filter(object_id=cloned.id))
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

    def _build_managed_orga(self, user=None, name='Bebop'):
        return Organisation.objects.create(user=user or self.user, name=name, is_managed=True)

    def test_get_all_managed_by_creme(self):
        user = self.login()

        mng_orga1 = self._build_managed_orga()
        mng_orga2 = self._build_managed_orga(name='NERV')
        orga = Organisation.objects.create(user=user, name='Seele')

        with self.assertNumQueries(1):
            qs1 = Organisation.get_all_managed_by_creme()
            mng_orgas = set(qs1)

        self.assertIn(mng_orga1, mng_orgas)
        self.assertIn(mng_orga2, mng_orgas)
        self.assertNotIn(orga,   mng_orgas)

        # Test request-cache
        with self.assertNumQueries(0):
            qs2 = Organisation.get_all_managed_by_creme()
            list(qs2)

        self.assertEqual(id(qs1), id(qs2))

    def _become_test(self, url_name, relation_type):
        user = self.login()

        mng_orga = self._build_managed_orga()
        customer = Contact.objects.create(user=user, first_name='Jet', last_name='Black')

        response = self.assertPOST200(reverse(url_name, args=(customer.id,)), data={'id': mng_orga.id}, follow=True)
        self.assertTrue(response.redirect_chain)
        self.get_object_or_fail(Relation, subject_entity=customer, object_entity=mng_orga, type=relation_type)

    def test_become_customer01(self):
        self._become_test('persons__become_customer', constants.REL_SUB_CUSTOMER_SUPPLIER)

    @skipIfCustomContact
    def test_become_customer02(self):
        "Credentials errors"
        user = self.login(is_superuser=False)

        create_creds = partial(SetCredentials.objects.create, role=self.role)
        create_creds(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                           EntityCredentials.DELETE | EntityCredentials.UNLINK,  # Not 'LINK'
                     set_type=SetCredentials.ESET_ALL
                    )
        create_creds(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                           EntityCredentials.DELETE | EntityCredentials.LINK | EntityCredentials.UNLINK,
                     set_type=SetCredentials.ESET_OWN
                    )

        mng_orga01 = self._build_managed_orga()
        customer01 = Contact.objects.create(user=self.other_user, first_name='Jet', last_name='Black')  # Can not link it
        self.assertPOST403(reverse('persons__become_customer', args=(customer01.id,)),
                           data={'id': mng_orga01.id}, follow=True
                          )
        self.assertEqual(0, Relation.objects.filter(subject_entity=customer01.id).count())

        mng_orga02 = self._build_managed_orga(user=self.other_user)  # Can not link it
        customer02 = Contact.objects.create(user=user, first_name='Vicious', last_name='??')
        self.assertPOST403(reverse('persons__become_customer', args=(customer02.id,)),
                           data={'id': mng_orga02.id}, follow=True
                          )
        self.assertEqual(0, Relation.objects.filter(subject_entity=customer02.id).count())

    def test_become_prospect(self):
        self._become_test('persons__become_prospect', constants.REL_SUB_PROSPECT)

    def test_become_suspect(self):
        self._become_test('persons__become_suspect', constants.REL_SUB_SUSPECT)

    def test_become_inactive_customer(self):
        self._become_test('persons__become_inactive_customer', constants.REL_SUB_INACTIVE)

    def test_become_supplier(self):
        self._become_test('persons__become_supplier', constants.REL_OBJ_CUSTOMER_SUPPLIER)

    def test_leads_customers01(self):
        user = self.login()

        self._build_managed_orga()
        Organisation.objects.create(user=user, name='Nerv')

        response = self.assertGET200(reverse('persons__leads_customers'))

        with self.assertNoException():
            orgas_page = response.context['entities']

        self.assertEqual(0, orgas_page.paginator.count)

    def test_leads_customers02(self):
        user = self.login()

        mng_orga = self._build_managed_orga()

        create_orga = partial(Organisation.objects.create, user=user)
        nerv = create_orga(name='Nerv')
        acme = create_orga(name='Acme')
        fsf  = create_orga(name='FSF')

        post = partial(self.client.post, data={'id': mng_orga.id})
        post(reverse('persons__become_customer', args=(nerv.id,)))
        post(reverse('persons__become_prospect', args=(acme.id,)))
        post(reverse('persons__become_suspect',  args=(fsf.id,)))

        response = self.client.get(reverse('persons__leads_customers'))
        orgas_page = response.context['entities']

        self.assertEqual(3, orgas_page.paginator.count)

        orgas_set = set(orgas_page.object_list)
        self.assertIn(nerv, orgas_set)
        self.assertIn(acme, orgas_set)
        self.assertIn(fsf,  orgas_set)

    def test_leads_customers03(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        nerv = create_orga(name='Nerv')
        acme = create_orga(name='Acme')
        self.client.post(reverse('persons__become_customer', args=(nerv.id,)), data={'id': acme.id})

        response = self.client.get(reverse('persons__leads_customers'))
        self.assertEqual(0, response.context['entities'].paginator.count)

    @skipIfCustomAddress
    def test_merge01(self):
        "Merging addresses"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='NERV')
        orga02 = create_orga(name='Nerv')

        create_address = Address.objects.create
        bill_addr01 = create_address(name='Billing address 01',
                                     address='BA1 - Address', po_box='BA1 - PO box',
                                     zipcode='BA1 - Zip code', city='BA1 - City',
                                     department='BA1 - Department',
                                     state='BA1 - State', country='BA1 - Country',
                                     owner=orga01,
                                    )
        ship_addr01 = create_address(name='Shipping address 01',
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

        bill_addr02 = create_address(name='Billing address 02',
                                     address='BA2 - Address', po_box='BA2 - PO box',
                                     zipcode='BA2 - Zip code', city='BA2 - City',
                                     department='BA2 - Department',
                                     state='BA2 - State', country='BA2 - Country',
                                     owner=orga02,
                                    )
        ship_addr02 = create_address(name='Shipping address 02',
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
        self.assertEqual([bill_addr01.city,  bill_addr02.city,  bill_addr01.city], b_city_f.initial)

        response = self.client.post(url, follow=True,
                                    data={'user_1':      user.id,
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
                                         }
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
        "Merging addresses (no existing address)"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='NERV')
        orga02 = create_orga(name='Nerv')

        response = self.client.post(self.build_merge_url(orga01, orga02),
                                    follow=True,
                                    data={'user_1':      user.id,
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
                                         }
                                   )
        self.assertNoFormError(response)

        self.assertDoesNotExist(orga02)

        with self.assertNoException():
            orga01 = self.refresh(orga01)

        addresses = Address.objects.filter(object_id=orga01.id)
        self.assertEqual(1, len(addresses))

        address = addresses[0]
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
        "Merging addresses (existing address for one Organisation)"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='NERV')
        orga02 = create_orga(name='Nerv')

        bill_addr01 = Address.objects.create(name='Billing address 01',
                                             address='BA1 - Address', po_box='BA1 - PO box',
                                             zipcode='BA1 - Zip code', city='BA1 - City',
                                             department='BA1 - Department',
                                             state='BA1 - State', country='BA1 - Country',
                                             owner=orga01,
                                            )
        orga01.billing_address = bill_addr01
        orga01.save()

        response = self.client.post(self.build_merge_url(orga01, orga02),
                                    follow=True,
                                    data={'user_1':      user.id,
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
                                         }
                                   )
        self.assertNoFormError(response)

        self.assertDoesNotExist(orga02)

        with self.assertNoException():
            orga01 = self.refresh(orga01)

        # self.assertFalse(Address.objects.filter(object_id=orga01.id))
        # self.assertIsNone(orga01.billing_address)
        # self.assertIsNone(orga01.shipping_address)

        self.assertIsNone(orga01.shipping_address)

        merged_bill_addr = orga01.billing_address
        self.assertIsNotNone(merged_bill_addr)
        self.assertEqual(bill_addr01.id, merged_bill_addr.id)
        self.assertEqual(orga01, merged_bill_addr.owner)
        self.assertFalse(merged_bill_addr.address)
        self.assertFalse(merged_bill_addr.city)

    @skipIfCustomAddress
    def test_merge04(self):
        "FieldsConfig on Address sub-field"
        user = self.login()
        FieldsConfig.create(Address,
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
        "FieldsConfig on 'billing_address' FK field"
        user = self.login()

        FieldsConfig.create(Organisation,
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

        response = self.client.post(url, follow=True,
                                    data={'user_1':      user.id,
                                          'user_2':      user.id,
                                          'user_merged': user.id,

                                          'name_1':      orga01.name,
                                          'name_2':      orga02.name,
                                          'name_merged': orga01.name,
                                         }
                                   )
        self.assertNoFormError(response)

    @skipIfCustomAddress
    def test_merge06(self):
        "FieldsConfig on 'shipping_address' FK field"
        user = self.login()

        FieldsConfig.create(Organisation,
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
        "The first organisation is managed"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='NERV', is_managed=True)
        orga02 = create_orga(name='Nerv')

        response = self.client.post(self.build_merge_url(orga01, orga02),
                                    follow=True,
                                    data={'user_1':      user.id,
                                          'user_2':      user.id,
                                          'user_merged': user.id,

                                          'name_1':      orga01.name,
                                          'name_2':      orga02.name,
                                          'name_merged': orga02.name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertDoesNotExist(orga02)

        orga01 = self.assertStillExists(orga01)
        self.assertEqual(orga02.name, orga01.name)
        self.assertTrue(orga01.is_managed)

    def test_merge08(self):
        "The second organisation is managed => swapped"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='NERV')
        orga02 = create_orga(name='Nerv', is_managed=True)

        response = self.assertGET200(self.build_merge_url(orga01, orga02))

        with self.assertNoException():
            initial_name = response.context['form'].fields['name'].initial[0]

        self.assertEqual(orga02.name, initial_name)

    def test_merge09(self):
        "The 2 organisations are managed => no swap"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user, is_managed=True)
        orga01 = create_orga(name='NERV')
        orga02 = create_orga(name='Nerv')

        response = self.assertGET200(self.build_merge_url(orga01, orga02))

        with self.assertNoException():
            initial_name = response.context['form'].fields['name'].initial[0]

        self.assertEqual(orga01.name, initial_name)

    def test_delete01(self):
        user = self.login()
        orga01 = Organisation.objects.create(user=user, name='Nerv')
        url = orga01.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        with self.assertNoException():
            orga01 = self.refresh(orga01)

        self.assertIs(orga01.is_deleted, True)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(orga01)

    def test_delete02(self):
        "Cannot delete the last managed organisation."
        self.login()

        managed_orgas = Organisation.objects.filter(is_managed=True)
        self.assertEqual(1, len(managed_orgas))

        managed_orga = managed_orgas[0]
        self.assertPOST403(managed_orga.get_delete_absolute_url())  # follow=True
        self.assertStillExists(managed_orga)

    def test_delete03(self):
        "A managed organisation ac be deleted if it's not the last one."
        user = self.login()

        managed_orga = Organisation.objects.create(user=user, name='Nerv', is_managed=True)
        url = managed_orga.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        with self.assertNoException():
            managed_orga = self.refresh(managed_orga)

        self.assertIs(managed_orga.is_deleted, True)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(managed_orga)

    def test_delete_sector(self):
        "Set to null"
        user = self.login()
        hunting = Sector.objects.create(title='Bounty hunting')
        bebop = Organisation.objects.create(user=user, name='Bebop', sector=hunting)

        self.assertPOST200(reverse('creme_config__delete_instance', args=('persons', 'sector')),
                           data={'id': hunting.pk}
                          )
        self.assertDoesNotExist(hunting)

        bebop = self.get_object_or_fail(Organisation, pk=bebop.pk)
        self.assertIsNone(bebop.sector)

    def test_delete_legal_form(self):
        "Set to null"
        user = self.login()
        band = LegalForm.objects.create(title='Bounty hunting band')
        bebop = Organisation.objects.create(user=user, name='Bebop', legal_form=band)

        self.assertPOST200(reverse('creme_config__delete_instance', args=('persons', 'legal_form')),
                           data={'id': band.pk}
                          )
        self.assertDoesNotExist(band)

        bebop = self.get_object_or_fail(Organisation, pk=bebop.pk)
        self.assertIsNone(bebop.legal_form)

    def test_delete_staff_size(self):
        "Set to null"
        user = self.login()
        size = StaffSize.objects.create(size='4 and a dog')
        bebop = Organisation.objects.create(user=user, name='Bebop', staff_size=size)

        self.assertPOST200(reverse('creme_config__delete_instance', args=('persons', 'staff_size')),
                           data={'id': size.pk}
                          )
        self.assertDoesNotExist(size)

        bebop = self.get_object_or_fail(Organisation, pk=bebop.pk)
        self.assertIsNone(bebop.staff_size)

    @skipIfCustomAddress
    def test_csv_import01(self):
        user = self.login()

        name1 = 'Nerv'
        city1 = 'Tokyo'
        name2 = 'Gunsmith Cats'
        city2 = 'Chicago'
        lines = [(name1, city1, ''), (name2, '', city2)]

        doc = self._build_csv_doc(lines)
        response = self.client.post(self._build_import_url(Organisation),
                                    follow=True,
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=user.id,
                                              billaddr_city_colselect=2,
                                              shipaddr_city_colselect=3,
                                             )
                                   )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual([_('Import «{model}» from {doc}').format(
                                model=_('Organisation'),
                                doc=doc,
                            )
                         ],
                         job.description
                        )

        results = self._get_job_results(job)
        lines_count = len(lines)
        self.assertEqual(lines_count, len(results))
        self._assertNoResultError(results)

        billing_address = self.get_object_or_fail(Organisation, name=name1).billing_address
        self.assertIsNotNone(billing_address)
        self.assertEqual(_('Billing address'), billing_address.name)
        self.assertEqual(city1,                billing_address.city)

        shipping_address = self.get_object_or_fail(Organisation, name=name2).shipping_address
        self.assertIsNotNone(shipping_address)
        self.assertEqual(_('Shipping address'), shipping_address.name)
        self.assertEqual(city2,                 shipping_address.city)

        self.assertEqual([ungettext('{count} «{model}» has been created.',
                                    '{count} «{model}» have been created.',
                                    lines_count
                                   ).format(count=lines_count,
                                            model=_('Organisations'),
                                           ),
                          ungettext('{count} line in the file.',
                                    '{count} lines in the file.',
                                    lines_count
                                   ).format(count=lines_count),
                         ],
                         job.stats
                        )

    @skipIfCustomAddress
    def test_csv_import02(self):
        "Update (with address)"
        user = self.login()

        name = 'Bebop'
        city1 = 'Red city'
        city2 = 'Crater city'

        bebop = Organisation.objects.create(user=user, name=name)

        country = 'Mars'
        create_address = partial(Address.objects.create,
                                 address='XXX', country=country,
                                 owner=bebop,
                                )
        bebop.billing_address  = addr1 = create_address(name='Hideout #1', city=city1)
        bebop.shipping_address = addr2 = create_address(name='Hideout #2', city=city2)
        bebop.save()

        addr_count = Address.objects.count()

        address_val1 = '213 Gauss Street'
        address_val2 = '56 Einstein Avenue'
        email = 'contact@bebop.mrs'
        doc = self._build_csv_doc([(name, address_val1, address_val2, email)])
        response = self.client.post(self._build_import_url(Organisation),
                                    follow=True,
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=user.id,
                                              key_fields=['name'],
                                              email_colselect=4,
                                              billaddr_address_colselect=2,
                                              shipaddr_address_colselect=3,
                                             )
                                   )
        self.assertNoFormError(response)

        self._execute_job(response)

        bebop = self.refresh(bebop)
        self.assertEqual(email, bebop.email)

        self.assertEqual(addr_count, Address.objects.count())

        addr1 = self.refresh(addr1)
        self.assertEqual(city1, addr1.city)
        self.assertEqual(address_val1, addr1.address)
        self.assertEqual(country,      addr1.country)  # Value not erased

        addr2 = self.refresh(addr2)
        self.assertEqual(city2, addr2.city)

    @skipIfCustomAddress
    def test_csv_import03(self):
        "FieldsConfig on Address sub-field"
        user = self.login()
        FieldsConfig.create(Address,
                            descriptions=[('po_box', {FieldsConfig.HIDDEN: True})],
                           )

        name = 'Nerv'
        city = 'Tokyo'
        po_box = 'ABC123'
        doc = self._build_csv_doc([(name, city, po_box)])
        response = self.client.post(self._build_import_url(Organisation), follow=True,
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=user.id,

                                              billaddr_city_colselect=2,
                                              billaddr_po_box_colselect=3,  # Should not be used
                                             )
                                   )
        self.assertNoFormError(response)

        self._execute_job(response)
        billing_address = self.get_object_or_fail(Organisation, name=name).billing_address

        self.assertIsNotNone(billing_address)
        self.assertEqual(city, billing_address.city)
        self.assertFalse(billing_address.po_box)

    @skipIfCustomAddress
    def test_csv_import04(self):
        "FieldsConfig on 'billing_address' FK field"
        user = self.login()
        FieldsConfig.create(Organisation,
                            descriptions=[('billing_address', {FieldsConfig.HIDDEN: True})],
                           )

        name = 'Nerv'
        doc = self._build_csv_doc([(name, 'Tokyo', 'ABC123')])
        response = self.client.post(self._build_import_url(Organisation), follow=True,
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=user.id,

                                              billaddr_city_colselect=2,  # Should not be used
                                              billaddr_po_box_colselect=3,  # Should not be used
                                             )
                                   )
        self.assertNoFormError(response)

        job = self._execute_job(response)

        orga = self.get_object_or_fail(Organisation, name=name)
        self.assertIsNone(orga.billing_address)

        self._assertNoResultError(self._get_job_results(job))

    def test_set_orga_as_managed(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Bebop')
        orga2 = create_orga(name='Swordfish')
        orga3 = create_orga(name='RedTail')

        url = reverse('persons__orga_set_managed')
        self.assertGET200(url)

        response = self.client.post(url, data={'organisations': self.formfield_value_multi_creator_entity(orga1, orga2)})
        self.assertNoFormError(response)

        self.assertTrue(self.refresh(orga1).is_managed)
        self.assertTrue(self.refresh(orga2).is_managed)
        self.assertFalse(self.refresh(orga3).is_managed)

        # Managed Organisations are excluded
        response = self.assertPOST200(url, data={'organisations': '[{}]'.format(orga1.id)})
        self.assertFormError(response, 'form', 'organisations', _('This entity does not exist.'))

    def test_set_orga_as_not_managed(self):
        self.login()

        mngd_orgas = Organisation.objects.filter(is_managed=True)
        self.assertEqual(1, len(mngd_orgas))

        orga1 = mngd_orgas[0]
        orga2 = self._build_managed_orga()

        url = reverse('persons__orga_unset_managed')
        data = {'id': orga2.id}
        self.assertGET404(url)
        self.assertGET404(url, data=data)

        self.assertPOST200(url, data=data)
        self.assertFalse(self.refresh(orga2).is_managed)

        self.assertPOST409(url, data={'id': orga1.id})  # At least 1 managed organisation
        self.assertTrue(self.refresh(orga1).is_managed)
