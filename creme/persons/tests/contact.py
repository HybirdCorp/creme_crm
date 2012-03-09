# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import Relation, SetCredentials
    from creme_core.gui.quick_forms import quickforms_registry

    from persons.models import Contact, Organisation, Address, Position, Civility, Sector
    from persons.constants import REL_OBJ_EMPLOYED_BY, REL_SUB_EMPLOYED_BY
    from persons.tests.base import _BaseTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('ContactTestCase',)


class ContactTestCase(_BaseTestCase):
    def test_createview01(self):
        self.login()

        url = '/persons/contact/add'
        self.assertEqual(200, self.client.get(url).status_code)

        count = Contact.objects.count()
        first_name = 'Spike'
        last_name  = 'Spiegel'
        response = self.client.post(url, follow=True,
                                    data={'user':       self.user.pk,
                                          'first_name': first_name,
                                          'last_name':  last_name,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)
        self.assertEqual(count + 1, Contact.objects.count())

        contact = self.get_object_or_fail(Contact, first_name=first_name)
        self.assertEqual(last_name,  contact.last_name)
        self.assertIsNone(contact.billing_address)
        self.assertIsNone(contact.shipping_address)

        self.assertTrue(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertTrue(response.redirect_chain[0][0].endswith('/persons/contact/%s' % contact.id))

        self.assertEqual(200, self.client.get('/persons/contact/%s' % contact.id).status_code)

    def test_createview02(self): # addresses
        self.login()

        first_name = 'Spike'
        b_address = 'In the Bebop.'
        s_address = 'In the Bebop (bis).'
        response = self.client.post('/persons/contact/add', follow=True,
                                    data={'user':                     self.user.pk,
                                          'first_name':               first_name,
                                          'last_name':                'Spiegel',
                                          'billing_address-address':  b_address,
                                          'shipping_address-address': s_address,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        contact = self.get_object_or_fail(Contact, first_name=first_name)
        self.assertIsNotNone(contact.billing_address)
        self.assertEqual(b_address, contact.billing_address.address)

        self.assertIsNotNone(contact.shipping_address)
        self.assertEqual(s_address, contact.shipping_address.address)

    def test_editview01(self):
        self.login()
        first_name = 'Faye'
        contact = Contact.objects.create(user=self.user, first_name=first_name, last_name='Valentine')

        url = '/persons/contact/edit/%s' % contact.id
        self.assertEqual(200, self.client.get(url).status_code)

        last_name = 'Spiegel'
        response = self.client.post(url, follow=True,
                                    data={'user':       self.user.pk,
                                          'first_name': first_name,
                                          'last_name':  last_name,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain[0][0].endswith('/persons/contact/%s' % contact.id))

        contact = self.refresh(contact)
        self.assertEqual(last_name, contact.last_name)
        self.assertIsNone(contact.billing_address)
        self.assertIsNone(contact.shipping_address)

    def test_editview02(self):
        self.login()
        first_name = 'Faye'
        last_name  = 'Valentine'
        response = self.client.post('/persons/contact/add', follow=True,
                                    data={'user':                     self.user.pk,
                                          'first_name':               first_name,
                                          'last_name':                last_name,
                                          'billing_address-address':  'In the Bebop.',
                                          'shipping_address-address': 'In the Bebop. (bis)',
                                         }
                                   )
        contact = Contact.objects.get(first_name=first_name)
        billing_address_id  = contact.billing_address_id
        shipping_address_id = contact.shipping_address_id

        state   = 'Solar system'
        country = 'Mars'
        response = self.client.post('/persons/contact/edit/%s' % contact.id, follow=True,
                                    data={'user':                     self.user.pk,
                                          'first_name':               first_name,
                                          'last_name':                last_name,
                                          'billing_address-state':    state,
                                          'shipping_address-country': country,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        contact = self.refresh(contact)
        self.assertEqual(billing_address_id,  contact.billing_address_id)
        self.assertEqual(shipping_address_id, contact.shipping_address_id)

        self.assertEqual(state,   contact.billing_address.state)
        self.assertEqual(country, contact.shipping_address.country)

    def test_listview(self):
        self.login()

        faye  = Contact.objects.create(user=self.user, first_name='Faye',  last_name='Valentine')
        spike = Contact.objects.create(user=self.user, first_name='Spike', last_name='Spiegel')

        response = self.client.get('/persons/contacts')
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            contacts_page = response.context['entities']

        self.assertEqual(3, contacts_page.paginator.count) #3: Creme user

        contacts_set = set(contacts_page.object_list)
        self.assertIn(faye,  contacts_set)
        self.assertIn(spike, contacts_set)

    def test_create_linked_contact01(self):
        self.login()

        orga = Organisation.objects.create(user=self.user, name='Acme')
        redir = orga.get_absolute_url()
        uri = "/persons/contact/add_with_relation/%(orga_id)s/%(rtype_id)s?callback_url=%(url)s" % {
                    'orga_id':  orga.id,
                    'rtype_id': REL_OBJ_EMPLOYED_BY,
                    'url':      redir,
                }
        self.assertEqual(200, self.client.get(uri).status_code)

        first_name = 'Bugs'
        last_name = 'Bunny'
        response = self.client.post(uri, follow=True,
                                    data={'orga_overview': 'dontcare',
                                          'relation':      'dontcare',
                                          'user':          self.user.pk,
                                          'first_name':    first_name,
                                          'last_name':     last_name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.redirect_chain)
        self.assertTrue(response.redirect_chain[-1][0].endswith(redir))

        with self.assertNoException():
            contact = Contact.objects.get(first_name=first_name)
            Relation.objects.get(subject_entity=orga.id, type=REL_OBJ_EMPLOYED_BY, object_entity=contact.id)

        self.assertEqual(last_name, contact.last_name)

    def test_create_linked_contact02(self):
        self.login(is_superuser=False, creatable_models=[Contact])

        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | SetCredentials.CRED_UNLINK, #no CRED_LINK
                                      set_type=SetCredentials.ESET_OWN
                                     )

        orga = Organisation.objects.create(user=self.user, name='Acme')
        response = self.client.get("/persons/contact/add_with_relation/%(orga_id)s/%(rtype_id)s?callback_url=%(url)s" % {
                                        'orga_id':  orga.id,
                                        'rtype_id': REL_OBJ_EMPLOYED_BY,
                                        'url':      orga.get_absolute_url(),
                                    })
        self.assertTrue(response.context) #no context if redirect to creme_login...
        self.assertEqual(403, response.status_code)

    def test_create_linked_contact03(self):
        self.login()

        orga = Organisation.objects.create(user=self.user, name='Acme')
        url = "/persons/contact/add_with_relation/%(orga_id)s/%(rtype_id)s?callback_url=%(url)s"

        self.assertGET404(url % {'orga_id':  1024, #doesn't exist
                                 'rtype_id': REL_OBJ_EMPLOYED_BY,
                                 'url':      orga.get_absolute_url(),
                                }
                         )
        self.assertGET404(url % {'orga_id':  orga.id, #doesn't exist
                                 'rtype_id': 'IDONOTEXIST',
                                 'url':      orga.get_absolute_url(),
                                }
                        )

    #TODO: test relation's object creds
    #TODO: test bad rtype (doesn't exist, constraints) => fixed list of types ??

    def test_clone(self): #addresses & is_user are problematic
        self.login()

        user = self.user
        naruto = Contact.objects.create(user=user, is_user=user,
                                        first_name='Naruto', last_name='Uzumaki'
                                       )

        create_address = partial(Address.objects.create,
                                 city='Konoha', state='Konoha', zipcode='111',
                                 country='The land of fire', department="Ninjas' homes",
                                 content_type=ContentType.objects.get_for_model(Contact),
                                 object_id=naruto.id
                                )
        naruto.billing_address  = create_address(name="Naruto's", address='Home', po_box='000')
        naruto.shipping_address = create_address(name="Naruto's", address='Home (second entry)', po_box='001')
        naruto.save()

        for i in xrange(5):
            create_address(name='Secret Cave #%s' % i, address='Cave #%s' % i, po_box='XXX')

        kage_bunshin = naruto.clone()

        self.assertEqual(naruto.first_name, kage_bunshin.first_name)
        self.assertEqual(naruto.last_name, kage_bunshin.last_name)
        self.assertIsNone(kage_bunshin.is_user) #<====

        self.assertEqual(naruto.id, naruto.billing_address.object_id)
        self.assertEqual(naruto.id, naruto.shipping_address.object_id)

        self.assertEqual(kage_bunshin.id, kage_bunshin.billing_address.object_id)
        self.assertEqual(kage_bunshin.id, kage_bunshin.shipping_address.object_id)

        addresses   = list(Address.objects.filter(object_id=naruto.id))
        c_addresses = list(Address.objects.filter(object_id=kage_bunshin.id))
        self.assertEqual(7, len(addresses))
        self.assertEqual(7, len(c_addresses))

        addresses_map   = dict((a.address, a) for a in addresses)
        c_addresses_map = dict((a.address, a) for a in c_addresses)
        self.assertEqual(7, len(addresses_map))
        self.assertEqual(7, len(c_addresses_map))

        for ident, address in addresses_map.iteritems():
            address2 = c_addresses_map.get(ident)
            self.assertIsNotNone(address2, ident)
            self.assertAddressOnlyContentEqual(address, address2)

    def test_quickform01(self):
        self.login()

        models = set(quickforms_registry.iter_models())
        self.assertIn(Contact, models)
        self.assertIn(Organisation, models)

        data = [('Faye', 'Valentine'), ('Spike', 'Spiegel')]

        ct = ContentType.objects.get_for_model(Contact)
        url = '/creme_core/quickforms/%s/%s' % (ct.id, len(data))
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={'form-TOTAL_FORMS':   len(data),
                                               'form-INITIAL_FORMS': 0,
                                               'form-MAX_NUM_FORMS': u'',
                                               'form-0-user':        self.user.id,
                                               'form-0-first_name':  data[0][0],
                                               'form-0-last_name':   data[0][1],
                                               'form-1-user':        self.user.id,
                                               'form-1-first_name':  data[1][0],
                                               'form-1-last_name':   data[1][1],
                                              }
                                   )
        self.assertEqual(200, response.status_code)

        self.assertEqual(3, Contact.objects.count())
        self.assertEqual(1, Organisation.objects.count())

        for first_name, last_name in data:
            self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)

    def test_quickform02(self):
        self.login()

        orga_name = 'Organisation'
        data = [('Faye', 'Valentine', orga_name), ('Spike', 'Spiegel', orga_name)]

        ct = ContentType.objects.get_for_model(Contact)
        url = '/creme_core/quickforms/%s/%s' % (ct.id, len(data))

        response = self.client.post(url, data={'form-TOTAL_FORMS':      len(data),
                                               'form-INITIAL_FORMS':    0,
                                               'form-MAX_NUM_FORMS':    u'',
                                               'form-0-user':           self.user.id,
                                               'form-0-first_name':     data[0][0],
                                               'form-0-last_name':      data[0][1],
                                               'form-0-organisation':   data[0][2],
                                               'form-1-user':           self.user.id,
                                               'form-1-first_name':     data[1][0],
                                               'form-1-last_name':      data[1][1],
                                               'form-1-organisation':   data[1][2],
                                               }
        )
        self.assertEqual(200, response.status_code)

        self.assertEqual(3, Contact.objects.count())
        self.assertEqual(2, Organisation.objects.count())

        for first_name, last_name, orga_name in data:
            contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
            self.assertEqual(1, Organisation.objects.filter(name=orga_name).count())

            created_orga = self.get_object_or_fail(Organisation, name=orga_name)
            self.assertRelationCount(1, contact, REL_SUB_EMPLOYED_BY, created_orga)

    def test_quickform03(self):
        self.login()

        orga_name = 'Organisation'
        orga = Organisation.objects.create(name=orga_name, user=self.user)
        self.assertEqual(2, Organisation.objects.count())

        data = [('Faye', 'Valentine', orga_name), ('Spike', 'Spiegel', orga_name)]

        ct = ContentType.objects.get_for_model(Contact)
        url = '/creme_core/quickforms/%s/%s' % (ct.id, len(data))

        response = self.client.post(url, data={'form-TOTAL_FORMS':      len(data),
                                               'form-INITIAL_FORMS':    0,
                                               'form-MAX_NUM_FORMS':    u'',
                                               'form-0-user':           self.user.id,
                                               'form-0-first_name':     data[0][0],
                                               'form-0-last_name':      data[0][1],
                                               'form-0-organisation':   data[0][2],
                                               'form-1-user':           self.user.id,
                                               'form-1-first_name':     data[1][0],
                                               'form-1-last_name':      data[1][1],
                                               'form-1-organisation':   data[1][2],
                                               }
        )
        self.assertEqual(200, response.status_code)

        self.assertEqual(3, Contact.objects.count())
        self.assertEqual(2, Organisation.objects.count())

        for first_name, last_name, orga_name in data:
            contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
            self.assertEqual(1, Organisation.objects.filter(name=orga_name).count())
            self.assertRelationCount(1, contact, REL_SUB_EMPLOYED_BY, orga)

    def test_merge01(self): #merging addresses
        self.login()
        user = self.user

        create_contact = Contact.objects.create
        contact01 = create_contact(user=user, first_name='Faye', last_name='Valentine')
        contact02 = create_contact(user=user, first_name='FAYE', last_name='VALENTINE')

        create_address = Address.objects.create
        bill_addr01 = create_address(name="Billing address 01",
                                     address="BA1 - Address", po_box="BA1 - PO box",
                                     zipcode="BA1 - Zip code", city="BA1 - City",
                                     department="BA1 - Department",
                                     state="BA1 - State", country="BA1 - Country",
                                     owner=contact01,
                                    )
        #NB: no shipping address for contact01
        contact01.billing_address = bill_addr01
        contact01.save()

        #NB: no billing address for contact02
        ship_addr02 = create_address(name="Shipping address 02",
                                     address="SA2 - Address", po_box="SA2 - PO box",
                                     zipcode="SA2 - Zip code", city="SA2 - City",
                                     department="SA2 - Department",
                                     state="SA2 - State", country="SA2 - Country",
                                     owner=contact02,
                                    )
        other_addr02 = create_address(name="Other address 02", owner=contact02)

        contact02.shipping_address = ship_addr02
        contact02.save()

        url = '/creme_core/entity/merge/%s,%s' % (contact01.id, contact02.id)
        context = self.client.get(url).context

        with self.assertNoException():
            f_baddr = context['form'].fields['billaddr_address']

        self.assertEqual([bill_addr01.address, '', bill_addr01.address], f_baddr.initial)

        response = self.client.post(url, follow=True,
                                    data={'user_1':      user.id,
                                          'user_2':      user.id,
                                          'user_merged': user.id,

                                          'first_name_1':      contact01.first_name,
                                          'first_name_2':      contact02.first_name,
                                          'first_name_merged': contact01.first_name,

                                          'last_name_1':      contact01.last_name,
                                          'last_name_2':      contact02.last_name,
                                          'last_name_merged': contact01.last_name,

                                           #Billing address
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

                                          #Shipping address
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
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        self.assertFalse(Organisation.objects.filter(pk=contact02).exists())

        with self.assertNoException():
            contact01 = self.refresh(contact01)

        addresses = Address.objects.filter(object_id=contact01.id)
        self.assertEqual(3, len(addresses))

        self.assertIn(bill_addr01,  addresses)
        self.assertIn(ship_addr02,  addresses)
        self.assertIn(other_addr02, addresses)

        billing_address = contact01.billing_address
        self.assertEqual(bill_addr01,         billing_address)
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
        self.assertEqual('Merged PO box 2',     shipping_address.po_box)
        self.assertEqual('Merged city 2',       shipping_address.city)
        self.assertEqual('Merged state 2',      shipping_address.state)
        self.assertEqual('Merged zipcode 2',    shipping_address.zipcode)
        self.assertEqual('Merged country 2',    shipping_address.country)
        self.assertEqual('Merged department 2', shipping_address.department)

    def test_merge02(self): #merging addresses -> empty addresses
        self.login()
        user = self.user

        create_contact = Contact.objects.create
        contact01 = create_contact(user=user, first_name='Faye', last_name='Valentine')
        contact02 = create_contact(user=user, first_name='FAYE', last_name='VALENTINE')

        ship_addr02 = Address.objects.create(name="Shipping address 02",
                                             address="SA2 - Address", po_box="SA2 - PO box",
                                             zipcode="SA2 - Zip code", city="SA2 - City",
                                             department="SA2 - Department",
                                             state="SA2 - State", country="SA2 - Country",
                                             owner=contact02,
                                            )
        contact02.shipping_address = ship_addr02
        contact02.save()

        response = self.client.post('/creme_core/entity/merge/%s,%s' % (contact01.id, contact02.id),
                                    follow=True,
                                    data={'user_1':      user.id,
                                          'user_2':      user.id,
                                          'user_merged': user.id,

                                          'first_name_1':      contact01.first_name,
                                          'first_name_2':      contact02.first_name,
                                          'first_name_merged': contact01.first_name,

                                          'last_name_1':      contact01.last_name,
                                          'last_name_2':      contact02.last_name,
                                          'last_name_merged': contact01.last_name,

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

                                          #Shipping address
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
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        self.assertFalse(Organisation.objects.filter(pk=contact02).exists())

        with self.assertNoException():
            contact01 = self.refresh(contact01)

        self.assertFalse(Address.objects.filter(object_id=contact01.id))
        self.assertIsNone(contact01.billing_address)
        self.assertIsNone(contact01.shipping_address)

    def test_merge03(self): #cannot merge Contacts that represent a user
        self.login()
        user = self.user

        create_contact = Contact.objects.create
        contact01 = create_contact(user=user, first_name='Faye', last_name='Valentine', is_user=user)
        contact02 = create_contact(user=user, first_name='FAYE', last_name='VALENTINE')

        url = '/creme_core/entity/merge/%s,%s'
        self.assertGET404(url % (contact01.id, contact02.id))
        self.assertGET404(url % (contact02.id, contact01.id))

    def test_delete_civility(self): #set to null
        self.login()
        captain = Civility.objects.create(title='Captain')
        harlock = Contact.objects.create(user=self.user, first_name='Harlock',
                                         last_name='Matsumoto', civility=captain,
                                        )

        response = self.client.post('/creme_config/persons/civility/delete', data={'id': captain.pk})
        self.assertEqual(200, response.status_code)
        self.assertFalse(Civility.objects.filter(pk=captain.pk).exists())

        harlock = self.get_object_or_fail(Contact, pk=harlock.pk)
        self.assertIsNone(harlock.civility)

    def test_delete_position(self): #set to null
        self.login()
        captain = Position.objects.create(title='Captain')
        harlock = Contact.objects.create(user=self.user, first_name='Harlock',
                                         last_name='Matsumoto', position=captain,
                                        )

        response = self.client.post('/creme_config/persons/position/delete', data={'id': captain.pk})
        self.assertEqual(200, response.status_code)
        self.assertFalse(Position.objects.filter(pk=captain.pk).exists())

        harlock = self.get_object_or_fail(Contact, pk=harlock.pk)
        self.assertIsNone(harlock.position)

    def test_delete_sector(self): #set to null
        self.login()
        piracy = Sector.objects.create(title='Piracy')
        harlock = Contact.objects.create(user=self.user, first_name='Harlock',
                                         last_name='Matsumoto', sector=piracy,
                                        )

        response = self.client.post('/creme_config/persons/sector/delete', data={'id': piracy.pk})
        self.assertEqual(200, response.status_code)
        self.assertFalse(Sector.objects.filter(pk=piracy.pk).exists())

        harlock = self.get_object_or_fail(Contact, pk=harlock.pk)
        self.assertIsNone(harlock.sector)
