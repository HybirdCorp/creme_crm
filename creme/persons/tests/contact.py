# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import Relation, SetCredentials
    from creme_core.gui.quick_forms import quickforms_registry
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact, Organisation
    from persons.constants import REL_OBJ_EMPLOYED_BY
except Exception as e:
    print 'Error:', e


__all__ = ('ContactTestCase',)


class ContactTestCase(CremeTestCase):
    def login(self, is_superuser=True, **kwargs):
        super(ContactTestCase, self).login(is_superuser, allowed_apps=['persons'], **kwargs)

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'persons')

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

        self.assertEqual(404, self.client.get(url % {'orga_id':  1024, #doesn't exist
                                                     'rtype_id': REL_OBJ_EMPLOYED_BY,
                                                     'url':      orga.get_absolute_url(),
                                                }).status_code
                        )
        self.assertEqual(404, self.client.get(url % {'orga_id':  orga.id, #doesn't exist
                                                     'rtype_id': 'IDONOTEXIST',
                                                     'url':      orga.get_absolute_url(),
                                                    }).status_code
                        )

    #TODO: test relation's object creds
    #TODO: test bad rtype (doesn't exist, constraints) => fixed list of types ??

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

        contacts = Contact.objects.all()
        self.assertEqual(3, len(contacts))

        for first_name, last_name in data:
            self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
