# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from django.contrib.contenttypes.models import ContentType

from creme_core.models import (RelationType, Relation, CremeProperty, SetCredentials,
                               EntityFilter, EntityFilterCondition)
from creme_core.constants import PROP_IS_MANAGED_BY_CREME
from creme_core.gui.quick_forms import quickforms_registry
from creme_core.tests.base import CremeTestCase

from activities.models import Meeting, PhoneCall, PhoneCallType
from activities.constants import REL_SUB_ACTIVITY_SUBJECT, REL_SUB_PART_2_ACTIVITY, REL_SUB_LINKED_2_ACTIVITY

from persons.models import *
from persons.constants import *
from persons.blocks import neglected_orgas_block


class PersonsTestCase(CremeTestCase):
    def login(self, is_superuser=True):
        super(PersonsTestCase, self).login(is_superuser, allowed_apps=['persons'])

    def setUp(self):
        self.populate('creme_core', 'persons')

    def test_populate(self): #test relationtype creation with constraints
        def get_relationtype_or_fail(pk):
            try:
                return RelationType.objects.get(pk=pk)
            except RelationType.DoesNotExist:
                self.fail('Bad populate: unfoundable RelationType with pk=%s' % pk)

        rel_sub_employed = get_relationtype_or_fail(REL_SUB_EMPLOYED_BY)
        rel_obj_employed = get_relationtype_or_fail(REL_OBJ_EMPLOYED_BY)
        rel_sub_customer = get_relationtype_or_fail(REL_SUB_CUSTOMER_OF)
        rel_obj_customer = get_relationtype_or_fail(REL_OBJ_CUSTOMER_OF)

        self.assertEqual(rel_sub_employed.symmetric_type_id, rel_obj_employed.id)
        self.assertEqual(rel_obj_employed.symmetric_type_id, rel_sub_employed.id)

        get_ct = ContentType.objects.get_for_model
        ct_id_contact = get_ct(Contact).id
        ct_id_orga    = get_ct(Organisation).id
        self.assertEqual([ct_id_contact], [ct.id for ct in rel_sub_employed.subject_ctypes.all()])
        self.assertEqual([ct_id_orga],    [ct.id for ct in rel_obj_employed.subject_ctypes.all()])

        ct_id_set = set((ct_id_contact, ct_id_orga))
        self.assertEqual(ct_id_set, set(ct.id for ct in rel_sub_customer.subject_ctypes.all()))
        self.assertEqual(ct_id_set, set(ct.id for ct in rel_obj_customer.subject_ctypes.all()))

        try:
            efilter = EntityFilter.objects.get(pk=FILTER_MANAGED_ORGA)
        except EntityFilter.DoesNotExist:
            self.fail('Managed organisations filter does not exist')

        self.failIf(efilter.is_custom)
        self.assertEqual(ct_id_orga, efilter.entity_type_id)
        self.assertEqual([EntityFilterCondition.EFC_PROPERTY], [c.type for c in efilter.conditions.all()])

    def test_contact_createview01(self):
        self.login()

        response = self.client.get('/persons/contact/add')
        self.assertEqual(response.status_code, 200)

        count = Contact.objects.count()
        first_name = 'Spike'
        last_name  = 'Spiegel'
        response = self.client.post('/persons/contact/add', follow=True,
                            data={
                                    'user':       self.user.pk,
                                    'first_name': first_name,
                                    'last_name':  last_name,
                                 }
                           )
        self.assertEqual(200, response.status_code)
        self.assertEqual(count + 1, Contact.objects.count())

        try:
            contact = Contact.objects.get(first_name=first_name)
        except Exception, e:
            self.fail(str(e))
        self.assertEqual(last_name,  contact.last_name)
        self.assert_(contact.billing_address is None)
        self.assert_(contact.shipping_address is None)

        self.assert_(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assert_(response.redirect_chain[0][0].endswith('/persons/contact/%s' % contact.id))

        response = self.client.get('/persons/contact/%s' % contact.id)
        self.assertEqual(response.status_code, 200)

    def test_contact_createview02(self): # addresses
        self.login()

        first_name = 'Spike'
        b_address = 'In the Bebop.'
        s_address = 'In the Bebop (bis).'
        response = self.client.post('/persons/contact/add', follow=True,
                                    data={
                                            'user':                     self.user.pk,
                                            'first_name':               first_name,
                                            'last_name':                'Spiegel',
                                            'billing_address-address':  b_address,
                                            'shipping_address-address': s_address,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        contact = Contact.objects.get(first_name=first_name)
        self.assert_(contact.billing_address is not None)
        self.assertEqual(b_address, contact.billing_address.address)

        self.assert_(contact.shipping_address is not None)
        self.assertEqual(s_address, contact.shipping_address.address)

    def test_contact_editview01(self):
        self.login()
        first_name = 'Faye'
        contact = Contact.objects.create(user=self.user, first_name=first_name, last_name='Valentine')

        url = '/persons/contact/edit/%s' % contact.id
        self.assertEqual(200, self.client.get(url).status_code)

        last_name = 'Spiegel'
        response = self.client.post(url, follow=True,
                                    data={
                                            'user':       self.user.pk,
                                            'first_name': first_name,
                                            'last_name':  last_name,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain[0][0].endswith('/persons/contact/%s' % contact.id))

        contact = Contact.objects.get(pk=contact.id)
        self.assertEqual(last_name, contact.last_name)
        self.assert_(contact.billing_address is None)
        self.assert_(contact.shipping_address is None)

    def test_contact_editview02(self):
        self.login()
        first_name = 'Faye'
        last_name  = 'Valentine'
        response = self.client.post('/persons/contact/add', follow=True,
                                    data={
                                            'user':                     self.user.pk,
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
                                    data={
                                            'user':                     self.user.pk,
                                            'first_name':               first_name,
                                            'last_name':                last_name,
                                            'billing_address-state':    state,
                                            'shipping_address-country': country,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        contact = Contact.objects.get(pk=contact.id) #refresh object
        self.assertEqual(billing_address_id,  contact.billing_address_id)
        self.assertEqual(shipping_address_id, contact.shipping_address_id)

        self.assertEqual(state,   contact.billing_address.state)
        self.assertEqual(country, contact.shipping_address.country)

    def test_contact_listview(self):
        self.login()

        faye  = Contact.objects.create(user=self.user, first_name='Faye',  last_name='Valentine')
        spike = Contact.objects.create(user=self.user, first_name='Spike', last_name='Spiegel')

        response = self.client.get('/persons/contacts')
        self.assertEqual(200, response.status_code)

        try:
            contacts_page = response.context['entities']
        except KeyError, e:
            self.fail(str(e))

        self.assertEqual(3, contacts_page.paginator.count) #3: Creme user

        contacts_set = set(contact.id for contact in contacts_page.object_list)
        self.assert_(faye.id in contacts_set)
        self.assert_(spike.id in contacts_set)

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
        response = self.client.post(uri, data={
                                        'orga_overview': 'dontcare',
                                        'relation':      'dontcare',
                                        'user':          self.user.pk,
                                        'first_name':    first_name,
                                        'last_name':     last_name,
                                    }, follow=True
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain)
        self.assert_(response.redirect_chain[-1][0].endswith(redir))

        try:
            contact = Contact.objects.get(first_name=first_name)
            Relation.objects.get(subject_entity=orga.id, type=REL_OBJ_EMPLOYED_BY, object_entity=contact.id)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(last_name, contact.last_name)

    def test_create_linked_contact02(self):
        self.login(is_superuser=False)

        role = self.user.role
        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | SetCredentials.CRED_UNLINK, #no CRED_LINK
                                      set_type=SetCredentials.ESET_OWN)
        role.creatable_ctypes = [ContentType.objects.get_for_model(Contact)]

        orga = Organisation.objects.create(user=self.user, name='Acme')
        response = self.client.get("/persons/contact/add_with_relation/%(orga_id)s/%(rtype_id)s?callback_url=%(url)s" % {
                                        'orga_id':  orga.id,
                                        'rtype_id': REL_OBJ_EMPLOYED_BY,
                                        'url':      orga.get_absolute_url(),
                                    })
        self.assert_(response.context) #no context if redirect to creme_login...
        self.assertEqual(403, response.status_code)

    def test_create_linked_contact03(self):
        self.login()

        orga = Organisation.objects.create(user=self.user, name='Acme')
        url = "/persons/contact/add_with_relation/%(orga_id)s/%(rtype_id)s?callback_url=%(url)s"

        self.assertEqual(404, self.client.get(url % {
                                        'orga_id':  1024, #doesn't exist
                                        'rtype_id': REL_OBJ_EMPLOYED_BY,
                                        'url':      orga.get_absolute_url(),
                                    }).status_code)
        self.assertEqual(404, self.client.get(url % {
                                        'orga_id':  orga.id, #doesn't exist
                                        'rtype_id': 'IDONOTEXIST',
                                        'url':      orga.get_absolute_url(),
                                    }).status_code)

    #TODO: test relation's object creds
    #TODO: test bad rtype (doesn't exist, constraints) => fixed list of types ??

    def test_orga_createview01(self):
        self.login()

        url = '/persons/organisation/add'
        self.assertEqual(200, self.client.get(url).status_code)

        count = Organisation.objects.count()
        name  = 'Spectre'
        description = 'DESCRIPTION'
        response = self.client.post(url, follow=True,
                                    data={
                                            'user':        self.user.pk,
                                            'name':        name,
                                            'description': description,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertEqual(count + 1, Organisation.objects.count())

        try:
            orga = Organisation.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))
        self.assertEqual(description,  orga.description)
        self.assert_(orga.billing_address is None)
        self.assert_(orga.shipping_address is None)

        self.assert_(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assert_(response.redirect_chain[0][0].endswith('/persons/organisation/%s' % orga.id))

        self.assertEqual(200, self.client.get('/persons/organisation/%s' % orga.id).status_code)

    def test_orga_editview01(self):
        self.login()

        name = 'Bebop'
        orga = Organisation.objects.create(user=self.user, name=name)
        url = '/persons/organisation/edit/%s' % orga.id
        self.assertEqual(200, self.client.get(url).status_code)

        name += '_edited'
        zipcode = '123456'
        response = self.client.post(url, follow=True,
                                    data={
                                            'user':                    self.user.pk,
                                            'name':                    name,
                                            'billing_address-zipcode': zipcode,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain)

        edited_orga = Organisation.objects.get(pk=orga.id)
        self.assertEqual(name, edited_orga.name)
        self.assert_(edited_orga.billing_address is not None)
        self.assertEqual(zipcode, edited_orga.billing_address.zipcode)

    def test_orga_listview(self):
        self.login()

        nerv = Organisation.objects.create(user=self.user, name='Nerv')
        acme = Organisation.objects.create(user=self.user, name='Acme')

        response = self.client.get('/persons/organisations')
        self.assertEqual(response.status_code, 200)

        try:
            orgas_page = response.context['entities']
        except KeyError, e:
            self.fail(str(e))

        self.assertEqual(3, orgas_page.paginator.count) #3: our 2 orgas + default orga

        orgas_set = set(orga.id for orga in orgas_page.object_list)
        self.assert_(nerv.id in orgas_set)
        self.assert_(acme.id in orgas_set)

    def _build_managed_orga(self, user=None):
        user = user or self.user
        try:
            mng_orga = Organisation.objects.create(user=user, name='Bebop')
            CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=mng_orga)
        except Exception, e:
            self.fail(str(e))

        return mng_orga

    def _become_test(self, url, relation_type):
        self.login()

        mng_orga = self._build_managed_orga()
        customer = Contact.objects.create(user=self.user, first_name='Jet', last_name='Black')

        response = self.client.post(url % customer.id, data={'id': mng_orga.id}, follow=True)
        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain)

        try:
            Relation.objects.get(subject_entity=customer, object_entity=mng_orga, type=relation_type)
        except Exception, e:
            self.fail(str(e))

    def test_become_customer01(self):
        self._become_test('/persons/%s/become_customer', REL_SUB_CUSTOMER_OF)

    def test_become_customer02(self): #creds errors
        self.login(is_superuser=False)

        role = self.user.role
        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | SetCredentials.CRED_UNLINK, #no CRED_LINK
                                      set_type=SetCredentials.ESET_ALL)
        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | SetCredentials.CRED_LINK | SetCredentials.CRED_UNLINK,
                                      set_type=SetCredentials.ESET_OWN)

        mng_orga01 = self._build_managed_orga()
        customer01 = Contact.objects.create(user=self.other_user, first_name='Jet', last_name='Black') #can not link it
        response = self.client.post('/persons/%s/become_customer' % customer01.id, data={'id': mng_orga01.id}, follow=True)
        self.assertEqual(403, response.status_code)
        self.assertEqual(0,   Relation.objects.filter(subject_entity=customer01.id).count())

        mng_orga02 = self._build_managed_orga(user=self.other_user)  #can not link it
        customer02 = Contact.objects.create(user=self.user, first_name='Vicious', last_name='??')
        response = self.client.post('/persons/%s/become_customer' % customer02.id, data={'id': mng_orga02.id}, follow=True)
        self.assertEqual(403, response.status_code)
        self.assertEqual(0,   Relation.objects.filter(subject_entity=customer02.id).count())

    def test_become_prospect(self):
        self._become_test('/persons/%s/become_prospect', REL_SUB_PROSPECT)

    def test_become_suspect(self):
        self._become_test('/persons/%s/become_suspect', REL_SUB_SUSPECT)

    def test_become_inactive_customer(self):
        self._become_test('/persons/%s/become_inactive_customer', REL_SUB_INACTIVE)

    def test_become_supplier(self):
        self._become_test('/persons/%s/become_supplier', REL_SUB_SUPPLIER)

    def test_leads_customers01(self):
        self.login()

        self._build_managed_orga()
        Organisation.objects.create(user=self.user, name='Nerv')

        response = self.client.get('/persons/leads_customers')
        self.assertEqual(response.status_code, 200)

        try:
            orgas_page = response.context['entities']
        except KeyError, e:
            self.fail(str(e))

        self.assertEqual(0, orgas_page.paginator.count)

    def test_leads_customers02(self):
        self.login()

        mng_orga = self._build_managed_orga()
        nerv = Organisation.objects.create(user=self.user, name='Nerv')
        acme = Organisation.objects.create(user=self.user, name='Acme')
        fsf  = Organisation.objects.create(user=self.user, name='FSF')

        data = {'id': mng_orga.id}
        self.client.post('/persons/%s/become_customer' % nerv.id, data=data)
        self.client.post('/persons/%s/become_prospect' % acme.id, data=data)
        self.client.post('/persons/%s/become_suspect'  % fsf.id,  data=data)

        response = self.client.get('/persons/leads_customers')
        orgas_page = response.context['entities']

        self.assertEqual(3, orgas_page.paginator.count)

        orgas_set = set(orga.id for orga in orgas_page.object_list)
        self.assert_(nerv.id in orgas_set)
        self.assert_(acme.id in orgas_set)
        self.assert_(fsf.id in orgas_set)

    def test_leads_customers03(self):
        self.login()

        nerv = Organisation.objects.create(user=self.user, name='Nerv')
        acme = Organisation.objects.create(user=self.user, name='Acme')
        self.client.post('/persons/%s/become_customer' % nerv.id, data={'id': acme.id})

        response = self.client.get('/persons/leads_customers')
        self.assertEqual(0, response.context['entities'].paginator.count)

    def _create_address(self, orga, name, address, po_box, city, state, zipcode, country, department):
        response = self.client.post('/persons/address/add/%s' % orga.id,
                                    data={
                                            'name':       name,
                                            'address':    address,
                                            'po_box':     po_box,
                                            'city':       city,
                                            'state':      state,
                                            'zipcode':    zipcode,
                                            'country':    country,
                                            'department': department,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

    def test_address_createview(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Nerv')

        self.assertEqual(0, Address.objects.filter(object_id=orga.id).count())

        response = self.client.get('/persons/address/add/%s' % orga.id)
        self.assertEqual(response.status_code, 200)

        name = 'Address#1'
        address_value = '21 jump street'
        po_box = 'Popop'
        city = 'Antlantis'
        state = '??'
        zipcode = '424242'
        country = 'wtf'
        department = 'rucrazy'

        self._create_address(orga, name, address_value, po_box, city, state, zipcode, country, department)

        addresses = Address.objects.filter(object_id=orga.id)
        self.assertEqual(1, len(addresses))

        address = addresses[0]
        self.assertEqual(name,       address.name)
        self.assertEqual(address_value, address.address)
        self.assertEqual(po_box,     address.po_box)
        self.assertEqual(city,       address.city)
        self.assertEqual(state,      address.state)
        self.assertEqual(zipcode,    address.zipcode)
        self.assertEqual(country,    address.country)
        self.assertEqual(department, address.department)

    def test_address_editview(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Nerv')

        name = 'Address#1'
        address_value = '21 jump street'
        po_box = 'Popop'
        city = 'Antlantis'
        state = '??'
        zipcode = '424242'
        country = 'wtf'
        department = 'rucrazy'

        self._create_address(orga, name, address_value, po_box, city, state, zipcode, country, department)
        address = Address.objects.filter(object_id=orga.id)[0]

        response = self.client.get('/persons/address/edit/%s' % address.id)
        self.assertEqual(response.status_code, 200)

        city = 'Groville'
        country = 'Groland'
        response = self.client.post('/persons/address/edit/%s' % address.id,
                                    data={
                                            'name':       name,
                                            'address':    address,
                                            'po_box':     po_box,
                                            'city':       city,
                                            'state':      state,
                                            'zipcode':    zipcode,
                                            'country':    country,
                                            'department': department,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

        address = Address.objects.get(pk=address.id)
        self.assertEqual(city,    address.city)
        self.assertEqual(country, address.country)

    def test_address_deleteview(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Nerv')

        self._create_address(orga, 'name', 'address', 'po_box', 'city', 'state', 'zipcode', 'country', 'department')
        address = Address.objects.filter(object_id=orga.id)[0]
        ct = ContentType.objects.get_for_model(Address)

        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': address.id})
        self.assertEqual(0, Address.objects.filter(object_id=orga.id).count())

    def test_portal(self):
        self.login()

        response = self.client.get('/persons/')
        self.assertEqual(response.status_code, 200)

    def test_quickform01(self):
        self.login()

        models = set(quickforms_registry.iter_models())
        self.assert_(Contact in models)
        self.assert_(Organisation in models)

        data = [('Faye', 'Valentine'), ('Spike', 'Spiegel')]

        ct = ContentType.objects.get_for_model(Contact)
        url = '/creme_core/quickforms/%s/%s' % (ct.id, len(data))

        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url,
                                    data={
                                            'form-TOTAL_FORMS':   len(data),
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
            try:
                contact = Contact.objects.get(first_name=first_name)
            except Exception, e:
                self.fail(str(e))

            self.assertEqual(last_name, contact.last_name)

    def _get_neglected_orgas(self):
        return neglected_orgas_block._get_neglected(datetime.now())

    def test_neglected_block01(self):
        self.login()

        orgas = Organisation.objects.all()
        self.assertEqual(1, len(orgas))

        mng_orga = orgas[0]
        self.assert_(CremeProperty.objects.filter(type=PROP_IS_MANAGED_BY_CREME, creme_entity=mng_orga).exists())
        self.failIf(self._get_neglected_orgas())

        customer01 = Organisation.objects.create(user=self.user, name='orga02')
        self.failIf(self._get_neglected_orgas())

        rtype_customer = RelationType.objects.get(pk=REL_SUB_CUSTOMER_OF)
        Relation.objects.create(user=self.user, subject_entity=customer01, object_entity=mng_orga, type=rtype_customer)
        self.assertEqual([customer01.id], [orga.id for orga in self._get_neglected_orgas()])

        customer02 = Organisation.objects.create(user=self.user, name='orga03')
        rtype_prospect = RelationType.objects.get(pk=REL_SUB_PROSPECT)
        Relation.objects.create(user=self.user, subject_entity=customer02, object_entity=mng_orga, type=rtype_prospect)
        neglected_orgas =  self._get_neglected_orgas()
        self.assertEqual(2, len(neglected_orgas))
        self.assertEqual(set([customer01.id, customer02.id]), set(orga.id for orga in neglected_orgas))

        Relation.objects.create(user=self.user, subject_entity=customer02, object_entity=mng_orga, type=rtype_customer)
        self.assertEqual(2, len(self._get_neglected_orgas()))

    def _build_customer_orga(self, mng_orga, name):
        customer = Organisation.objects.create(user=self.user, name=name)
        Relation.objects.create(user=self.user, subject_entity=customer, object_entity=mng_orga, type_id=REL_SUB_CUSTOMER_OF)

        return customer

    def test_neglected_block02(self):
        self.populate('activities')
        self.login()

        user = self.user
        mng_orga = Organisation.objects.all()[0]
        user_contact = Contact.objects.create(user=user, is_user=user, first_name='Naruto', last_name='Uzumaki')

        customer01 = self._build_customer_orga(mng_orga, 'Konoha')
        customer02 = self._build_customer_orga(mng_orga, 'Suna')
        self.assertEqual(2, len(self._get_neglected_orgas()))

        tomorrow = datetime.now() + timedelta(days=1) #so in the future
        meeting  = Meeting.objects.create(user=user, title='meet01', start=tomorrow, end=tomorrow + timedelta(hours=2))

        rtype_actsubject = RelationType.objects.get(pk=REL_SUB_ACTIVITY_SUBJECT)
        Relation.objects.create(user=user, subject_entity=customer02, object_entity=meeting, type=rtype_actsubject)
        self.assertEqual(2, len(self._get_neglected_orgas()))

        rtype_actpart = RelationType.objects.get(pk=REL_SUB_PART_2_ACTIVITY)
        Relation.objects.create(user=user, subject_entity=user_contact, object_entity=meeting, type=rtype_actpart)
        self.assertEqual([customer01.id], [orga.id for orga in self._get_neglected_orgas()])

    def test_neglected_block03(self): #past activity => orga is still neglected
        self.populate('activities')
        self.login()

        user = self.user
        mng_orga = Organisation.objects.all()[0]
        user_contact = Contact.objects.create(user=user, is_user=user, first_name='Naruto', last_name='Uzumaki')

        customer01 = self._build_customer_orga(mng_orga, 'Konoha')
        customer02 = self._build_customer_orga(mng_orga, 'Suna')

        yesteday = datetime.now() - timedelta(days=1) #so in the past
        meeting  = Meeting.objects.create(user=user, title='meet01', start=yesteday, end=yesteday + timedelta(hours=2))

        Relation.objects.create(user=user, subject_entity=customer02,   object_entity=meeting, type_id=REL_SUB_ACTIVITY_SUBJECT)
        Relation.objects.create(user=user, subject_entity=user_contact, object_entity=meeting, type_id=REL_SUB_PART_2_ACTIVITY)
        self.assertEqual(2, len(self._get_neglected_orgas())) #and not 1

    def test_neglected_block04(self): #a people linked to customer is linked to a future activity
        self.populate('activities')
        self.login()

        user = self.user
        mng_orga = Organisation.objects.all()[0]
        user_contact = Contact.objects.create(user=user, is_user=user, first_name='Naruto', last_name='Uzumaki')

        customer = self._build_customer_orga(mng_orga, 'Suna')

        tomorrow = datetime.now() + timedelta(days=1) #so in the future
        meeting = Meeting.objects.create(user=user, title='meet01', start=tomorrow, end=tomorrow + timedelta(hours=2))
        Relation.objects.create(user=user, subject_entity=user_contact, object_entity=meeting, type_id=REL_SUB_PART_2_ACTIVITY)

        employee = Contact.objects.create(user=user, first_name='Kankuro', last_name='???')
        rtype_employed = RelationType.objects.get(pk=REL_SUB_EMPLOYED_BY)
        Relation.objects.create(user=user, subject_entity=employee, object_entity=customer, type=rtype_employed)
        self.assertEqual(1, len(self._get_neglected_orgas()))

        rtype_actlink = RelationType.objects.get(pk=REL_SUB_LINKED_2_ACTIVITY)
        Relation.objects.create(user=user, subject_entity=employee, object_entity=meeting, type=rtype_actlink)
        self.failIf(self._get_neglected_orgas())

    def test_neglected_block05(self): #2 people linked to customer are linked to a future activity
        self.populate('activities')
        self.login()

        user = self.user
        mng_orga = Organisation.objects.all()[0]
        user_contact = Contact.objects.create(user=user, is_user=user, first_name='Naruto', last_name='Uzumaki')

        customer = self._build_customer_orga(mng_orga, 'Suna')

        tomorrow = datetime.now() + timedelta(days=1) #so in the future
        meeting   = Meeting.objects.create(user=user, title='meet01', start=tomorrow, end=tomorrow + timedelta(hours=2))
        phonecall = PhoneCall.objects.create(user=user, title='call01', start=tomorrow, end=tomorrow + timedelta(minutes=15), call_type=PhoneCallType.objects.all()[0])
        Relation.objects.create(user=user, subject_entity=user_contact, object_entity=phonecall, type_id=REL_SUB_PART_2_ACTIVITY)
        Relation.objects.create(user=user, subject_entity=user_contact, object_entity=meeting,   type_id=REL_SUB_PART_2_ACTIVITY)

        manager = Contact.objects.create(user=user,  first_name='Gaara', last_name='???')
        employee = Contact.objects.create(user=user, first_name='Temari', last_name='???')
        Relation.objects.create(user=user, subject_entity=manager,  object_entity=customer, type_id=REL_SUB_MANAGES)
        Relation.objects.create(user=user, subject_entity=employee, object_entity=customer, type_id=REL_SUB_EMPLOYED_BY)
        self.assertEqual(1, len(self._get_neglected_orgas()))

        Relation.objects.create(user=user, subject_entity=manager, object_entity=phonecall, type_id=REL_SUB_PART_2_ACTIVITY)
        self.failIf(self._get_neglected_orgas())

        Relation.objects.create(user=user, subject_entity=employee, object_entity=meeting, type_id=REL_SUB_ACTIVITY_SUBJECT)
        self.failIf(self._get_neglected_orgas())

    def test_neglected_block06(self): #future activity, but not with managed organisation !
        self.populate('activities')
        self.login()

        user = self.user
        mng_orga   = Organisation.objects.all()[0]
        customer   = self._build_customer_orga(mng_orga, 'Suna')
        competitor = Organisation.objects.create(user=user, name='Akatsuki')

        tomorrow = datetime.now() + timedelta(days=1) #so in the future
        meeting  = Meeting.objects.create(user=user, title='meet01', start=tomorrow, end=tomorrow + timedelta(hours=2))

        manager = Contact.objects.create(user=user,  first_name='Gaara', last_name='???')
        Relation.objects.create(user=user, subject_entity=manager,  object_entity=customer, type_id=REL_SUB_MANAGES)

        Relation.objects.create(user=user, subject_entity=manager,    object_entity=meeting, type_id=REL_SUB_PART_2_ACTIVITY)
        Relation.objects.create(user=user, subject_entity=competitor, object_entity=meeting, type_id=REL_SUB_ACTIVITY_SUBJECT)
        self.assertEqual(1, len(self._get_neglected_orgas()))

#TODO: tests for portal stats
