# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.tests.views.list_view_import import CSVImportBaseTestCaseMixin
    from creme.creme_core.models import Relation, CremeProperty, SetCredentials
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME

    from .base import _BaseTestCase
    from ..models import *
    from ..constants import *
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('OrganisationTestCase',)


class OrganisationTestCase(_BaseTestCase, CSVImportBaseTestCaseMixin):
    lv_import_data = {
            'step':     1,
            #'document': doc.id, 'user': self.user.id,
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

            #'property_types', 'fixed_relations', 'dyn_relations',

            'billaddr_address_colselect':    0,   'shipaddr_address_colselect':    0,
            'billaddr_po_box_colselect':     0,   'shipaddr_po_box_colselect':     0,
            'billaddr_city_colselect':       0,   'shipaddr_city_colselect':       0,
            'billaddr_state_colselect':      0,   'shipaddr_state_colselect':      0,
            'billaddr_zipcode_colselect':    0,   'shipaddr_zipcode_colselect':    0,
            'billaddr_country_colselect':    0,   'shipaddr_country_colselect':    0,
            'billaddr_department_colselect': 0,   'shipaddr_department_colselect': 0,
        }

    def test_createview01(self):
        self.login()

        url = '/persons/organisation/add'
        self.assertGET200(url)

        count = Organisation.objects.count()
        name  = 'Spectre'
        description = 'DESCRIPTION'
        response = self.client.post(url, follow=True,
                                    data={'user':        self.user.pk,
                                          'name':        name,
                                          'description': description,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(count + 1, Organisation.objects.count())

        orga = self.get_object_or_fail(Organisation, name=name)
        self.assertEqual(description,  orga.description)
        self.assertIsNone(orga.billing_address)
        self.assertIsNone(orga.shipping_address)

        abs_url = orga.get_absolute_url()
        self.assertEqual('/persons/organisation/%s' % orga.id, abs_url)
        self.assertRedirects(response, abs_url)

    def test_editview01(self):
        self.login()

        name = 'Bebop'
        orga = Organisation.objects.create(user=self.user, name=name)
        url = '/persons/organisation/edit/%s' % orga.id
        self.assertGET200(url)

        name += '_edited'
        zipcode = '123456'
        response = self.client.post(url, follow=True,
                                    data={'user':                    self.user.pk,
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
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        nerv = create_orga(name='Nerv')
        acme = create_orga(name='Acme')

        response = self.assertGET200('/persons/organisations')

        with self.assertNoException():
            orgas_page = response.context['entities']

        self.assertEqual(3, orgas_page.paginator.count) #3: our 2 orgas + default orga

        orgas_set = set(orgas_page.object_list)
        self.assertIn(nerv, orgas_set)
        self.assertIn(acme, orgas_set)

    def test_clone(self):
        "Addresses are problematic"
        self.login()

        bebop = Organisation.objects.create(user=self.user, name='Bebop')

        create_address = partial(Address.objects.create, address='XXX',
                                 city='Red city', state='North', zipcode='111',
                                 country='Mars', department='Dome #12',
                                 content_type=ContentType.objects.get_for_model(Organisation),
                                 object_id=bebop.id
                                )
        bebop.billing_address  = create_address(name='Hideout #1')
        bebop.shipping_address = create_address(name='Hideout #2')
        bebop.save()

        for i in xrange(3, 5):
            create_address(name='Hideout #%s' % i)

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

        for ident, address in addresses_map.iteritems():
            address2 = c_addresses_map.get(ident)
            self.assertIsNotNone(address2, ident)
            self.assertAddressOnlyContentEqual(address, address2)

    def _build_managed_orga(self, user=None):
        user = user or self.user

        with self.assertNoException():
            mng_orga = Organisation.objects.create(user=user, name='Bebop')
            CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=mng_orga)

        return mng_orga

    def _become_test(self, url, relation_type):
        self.login()

        mng_orga = self._build_managed_orga()
        customer = Contact.objects.create(user=self.user, first_name='Jet', last_name='Black')

        response = self.assertPOST200(url % customer.id, data={'id': mng_orga.id}, follow=True)
        self.assertTrue(response.redirect_chain)
        self.get_object_or_fail(Relation, subject_entity=customer, object_entity=mng_orga, type=relation_type)

    def test_become_customer01(self):
        self._become_test('/persons/%s/become_customer', REL_SUB_CUSTOMER_SUPPLIER)

    def test_become_customer02(self):
        "Credentials errors"
        self.login(is_superuser=False)

        create_creds = partial(SetCredentials.objects.create, role=self.role)
        create_creds(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                           EntityCredentials.DELETE | EntityCredentials.UNLINK, #no LINK
                     set_type=SetCredentials.ESET_ALL
                    )
        create_creds(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                           EntityCredentials.DELETE | EntityCredentials.LINK | EntityCredentials.UNLINK,
                     set_type=SetCredentials.ESET_OWN
                    )

        mng_orga01 = self._build_managed_orga()
        customer01 = Contact.objects.create(user=self.other_user, first_name='Jet', last_name='Black') #can not link it
        self.assertPOST403('/persons/%s/become_customer' % customer01.id,
                           data={'id': mng_orga01.id}, follow=True
                          )
        self.assertEqual(0, Relation.objects.filter(subject_entity=customer01.id).count())

        mng_orga02 = self._build_managed_orga(user=self.other_user)  #can not link it
        customer02 = Contact.objects.create(user=self.user, first_name='Vicious', last_name='??')
        self.assertPOST403('/persons/%s/become_customer' % customer02.id,
                           data={'id': mng_orga02.id}, follow=True
                          )
        self.assertEqual(0, Relation.objects.filter(subject_entity=customer02.id).count())

    def test_become_prospect(self):
        self._become_test('/persons/%s/become_prospect', REL_SUB_PROSPECT)

    def test_become_suspect(self):
        self._become_test('/persons/%s/become_suspect', REL_SUB_SUSPECT)

    def test_become_inactive_customer(self):
        self._become_test('/persons/%s/become_inactive_customer', REL_SUB_INACTIVE)

    def test_become_supplier(self):
        self._become_test('/persons/%s/become_supplier', REL_OBJ_CUSTOMER_SUPPLIER)

    def test_leads_customers01(self):
        self.login()

        self._build_managed_orga()
        Organisation.objects.create(user=self.user, name='Nerv')

        response = self.assertGET200('/persons/leads_customers')

        with self.assertNoException():
            orgas_page = response.context['entities']

        self.assertEqual(0, orgas_page.paginator.count)

    def test_leads_customers02(self):
        self.login()

        mng_orga = self._build_managed_orga()

        create_orga = partial(Organisation.objects.create, user=self.user)
        nerv = create_orga(name='Nerv')
        acme = create_orga(name='Acme')
        fsf  = create_orga(name='FSF')

        post = partial(self.client.post, data={'id': mng_orga.id})
        post('/persons/%s/become_customer' % nerv.id)
        post('/persons/%s/become_prospect' % acme.id)
        post('/persons/%s/become_suspect'  % fsf.id)

        response = self.client.get('/persons/leads_customers')
        orgas_page = response.context['entities']

        self.assertEqual(3, orgas_page.paginator.count)

        orgas_set = set(orgas_page.object_list)
        self.assertIn(nerv, orgas_set)
        self.assertIn(acme, orgas_set)
        self.assertIn(fsf,  orgas_set)

    def test_leads_customers03(self):
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        nerv = create_orga(name='Nerv')
        acme = create_orga(name='Acme')
        self.client.post('/persons/%s/become_customer' % nerv.id, data={'id': acme.id})

        response = self.client.get('/persons/leads_customers')
        self.assertEqual(0, response.context['entities'].paginator.count)

    def test_merge01(self):
        "Merging addresses"
        self.login()
        user = self.user

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='NERV')
        orga02 = create_orga(name='Nerv')

        create_address = Address.objects.create
        bill_addr01 = create_address(name="Billing address 01",
                                     address="BA1 - Address", po_box="BA1 - PO box",
                                     zipcode="BA1 - Zip code", city="BA1 - City",
                                     department="BA1 - Department",
                                     state="BA1 - State", country="BA1 - Country",
                                     owner=orga01,
                                    )
        ship_addr01 = create_address(name="Shipping address 01",
                                     address="SA1 - Address", po_box="SA1 - PO box",
                                     zipcode="SA1 - Zip code", city="SA1 - City",
                                     department="SA1 - Department",
                                     state="SA1 - State", country="SA1 - Country",
                                     owner=orga01,
                                    )
        other_addr01 = create_address(name="Other address 01", owner=orga01)
        orga01.billing_address = bill_addr01
        orga01.shipping_address = ship_addr01
        orga01.save()

        bill_addr02 = create_address(name="Billing address 02",
                                     address="BA2 - Address", po_box="BA2 - PO box",
                                     zipcode="BA2 - Zip code", city="BA2 - City",
                                     department="BA2 - Department",
                                     state="BA2 - State", country="BA2 - Country",
                                     owner=orga02,
                                    )
        ship_addr02 = create_address(name="Shipping address 02",
                                     address="SA2 - Address", po_box="SA2 - PO box",
                                     zipcode="SA2 - Zip code", city="SA2 - City",
                                     department="SA2 - Department",
                                     state="SA2 - State", country="SA2 - Country",
                                     owner=orga02,
                                    )
        other_addr02 = create_address(name="Other address 02", owner=orga02)

        orga02.billing_address = bill_addr02
        orga02.shipping_address = ship_addr02
        orga02.save()

        url = self.build_merge_url(orga01, orga02)
        response = self.assertGET200(url)

        with self.assertNoException():
            f_baddr = response.context['form'].fields['billaddr_name']

        self.assertFalse(f_baddr.required)
        self.assertEqual([bill_addr01.name,  bill_addr02.name,  bill_addr01.name], f_baddr.initial)

        response = self.client.post(url, follow=True,
                                    data={'user_1':      user.id,
                                          'user_2':      user.id,
                                          'user_merged': user.id,

                                          'name_1':      orga01.name,
                                          'name_2':      orga02.name,
                                          'name_merged': orga01.name,

                                           #Billing address
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

                                          #Shipping address
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

    def test_merge02(self):
        "Merging addresses"
        self.login()
        user = self.user

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

                                           #Billing address
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
        self.assertEqual('Merged name',          address.name)
        self.assertEqual('Merged address',       address.address)
        self.assertEqual('Merged PO box',        address.po_box)
        self.assertEqual('Merged city',          address.city)
        self.assertEqual('Merged state',         address.state)
        self.assertEqual('Merged zipcode',       address.zipcode)
        self.assertEqual('Merged country',       address.country)
        self.assertEqual('Merged department',    address.department)

        self.assertIsNone(orga01.shipping_address)

    def test_merge03(self):
        "Merging addresses"
        self.login()
        user = self.user

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='NERV')
        orga02 = create_orga(name='Nerv')

        bill_addr01 = Address.objects.create(name="Billing address 01",
                                             address="BA1 - Address", po_box="BA1 - PO box",
                                             zipcode="BA1 - Zip code", city="BA1 - City",
                                             department="BA1 - Department",
                                             state="BA1 - State", country="BA1 - Country",
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

                                           #Billing address
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

        self.assertFalse(Address.objects.filter(object_id=orga01.id))
        self.assertIsNone(orga01.billing_address)
        self.assertIsNone(orga01.shipping_address)

    def test_delete_sector(self):
        "Set to null"
        self.login()
        hunting = Sector.objects.create(title='Bounty hunting')
        bebop = Organisation.objects.create(user=self.user, name='Bebop', sector=hunting)

        self.assertPOST200('/creme_config/persons/sector/delete', data={'id': hunting.pk})
        self.assertDoesNotExist(hunting)

        bebop = self.get_object_or_fail(Organisation, pk=bebop.pk)
        self.assertIsNone(bebop.sector)

    def test_delete_legal_form(self):
        "Set to null"
        self.login()
        band = LegalForm.objects.create(title='Bounty hunting band')
        bebop = Organisation.objects.create(user=self.user, name='Bebop', legal_form=band)

        self.assertPOST200('/creme_config/persons/legal_form/delete', data={'id': band.pk})
        self.assertDoesNotExist(band)

        bebop = self.get_object_or_fail(Organisation, pk=bebop.pk)
        self.assertIsNone(bebop.legal_form)

    def test_delete_staff_size(self):
        "Set to null"
        self.login()
        size = StaffSize.objects.create(size='4 and a dog')
        bebop = Organisation.objects.create(user=self.user, name='Bebop', staff_size=size)

        self.assertPOST200('/creme_config/persons/staff_size/delete', data={'id': size.pk})
        self.assertDoesNotExist(size)

        bebop = self.get_object_or_fail(Organisation, pk=bebop.pk)
        self.assertIsNone(bebop.staff_size)

    def test_csv_import01(self):
        self.login()

        name1 = 'Nerv'
        city1 = 'Tokyo'
        name2 = 'Gunsmith Cats'
        city2 = 'Chicago'
        lines = [(name1, city1, ''), (name2, '', city2)]

        doc = self._build_csv_doc(lines)
        response = self.client.post(self._build_import_url(Organisation),
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=self.user.id,
                                              billaddr_city_colselect=2,
                                              shipaddr_city_colselect=3,
                                             )
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(len(lines), form.imported_objects_count)

        billing_address = self.get_object_or_fail(Organisation, name=name1).billing_address
        self.assertIsNotNone(billing_address)
        self.assertEqual(city1, billing_address.city)

        shipping_address = self.get_object_or_fail(Organisation, name=name2).shipping_address
        self.assertIsNotNone(shipping_address)
        self.assertEqual(city2, shipping_address.city)

    def test_csv_import02(self):
        "Update (with address)"
        self.login()

        user = self.user

        name = 'Bebop'
        city1 = 'Red city'
        city2 = 'Crater city'

        bebop = Organisation.objects.create(user=user, name=name)
        create_address = partial(Address.objects.create, object_id=bebop.id,
                                 address='XXX', country='Mars',
                                 content_type=ContentType.objects.get_for_model(Organisation),
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
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=self.user.id,
                                              key_fields=['name'],
                                              email_colselect=4,
                                              billaddr_address_colselect=2,
                                              shipaddr_address_colselect=3,
                                             )
                                   )
        self.assertNoFormError(response)

        bebop = self.refresh(bebop)
        self.assertEqual(email, bebop.email)

        self.assertEqual(addr_count, Address.objects.count())

        addr1 = self.refresh(addr1)
        self.assertEqual(city1, addr1.city)
        self.assertEqual(address_val1, addr1.address)

        addr2 = self.refresh(addr2)
        self.assertEqual(city2, addr2.city)
