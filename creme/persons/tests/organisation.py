# -*- coding: utf-8 -*-

try:
    from creme_core.models import Relation, CremeProperty, SetCredentials
    from creme_core.constants import PROP_IS_MANAGED_BY_CREME
    from creme_core.tests.base import CremeTestCase

    from persons.models import *
    from persons.constants import *
except Exception as e:
    print 'Error:', e


__all__ = ('OrganisationTestCase',)


class OrganisationTestCase(CremeTestCase):
    def login(self, is_superuser=True):
        super(OrganisationTestCase, self).login(is_superuser, allowed_apps=['persons'])

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'persons')

    def test_createview01(self):
        self.login()

        url = '/persons/organisation/add'
        self.assertEqual(200, self.client.get(url).status_code)

        count = Organisation.objects.count()
        name  = 'Spectre'
        description = 'DESCRIPTION'
        response = self.client.post(url, follow=True,
                                    data={'user':        self.user.pk,
                                          'name':        name,
                                          'description': description,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)
        self.assertEqual(count + 1, Organisation.objects.count())

        orga = self.get_object_or_fail(Organisation, name=name)
        self.assertEqual(description,  orga.description)
        self.assertIsNone(orga.billing_address)
        self.assertIsNone(orga.shipping_address)

        self.assertTrue(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertTrue(response.redirect_chain[0][0].endswith('/persons/organisation/%s' % orga.id))

        self.assertEqual(200, self.client.get('/persons/organisation/%s' % orga.id).status_code)

    def test_editview01(self):
        self.login()

        name = 'Bebop'
        orga = Organisation.objects.create(user=self.user, name=name)
        url = '/persons/organisation/edit/%s' % orga.id
        self.assertEqual(200, self.client.get(url).status_code)

        name += '_edited'
        zipcode = '123456'
        response = self.client.post(url, follow=True,
                                    data={'user':                    self.user.pk,
                                          'name':                    name,
                                          'billing_address-zipcode': zipcode,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)
        self.assertTrue(response.redirect_chain)

        edited_orga = self.refresh(orga)
        self.assertEqual(name, edited_orga.name)
        self.assertIsNotNone(edited_orga.billing_address)
        self.assertEqual(zipcode, edited_orga.billing_address.zipcode)

    def test_listview(self):
        self.login()

        nerv = Organisation.objects.create(user=self.user, name='Nerv')
        acme = Organisation.objects.create(user=self.user, name='Acme')

        response = self.client.get('/persons/organisations')
        self.assertEqual(response.status_code, 200)

        with self.assertNoException():
            orgas_page = response.context['entities']

        self.assertEqual(3, orgas_page.paginator.count) #3: our 2 orgas + default orga

        orgas_set = set(orgas_page.object_list)
        self.assertIn(nerv, orgas_set)
        self.assertIn(acme, orgas_set)

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

        response = self.client.post(url % customer.id, data={'id': mng_orga.id}, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.redirect_chain)
        self.get_object_or_fail(Relation, subject_entity=customer, object_entity=mng_orga, type=relation_type)

    def test_become_customer01(self):
        self._become_test('/persons/%s/become_customer', REL_SUB_CUSTOMER_SUPPLIER)

    def test_become_customer02(self): #creds errors
        self.login(is_superuser=False)

        role = self.role
        create_creds = SetCredentials.objects.create
        create_creds(role=role,
                     value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                           SetCredentials.CRED_DELETE | SetCredentials.CRED_UNLINK, #no CRED_LINK
                     set_type=SetCredentials.ESET_ALL
                    )
        create_creds(role=role,
                     value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                           SetCredentials.CRED_DELETE | SetCredentials.CRED_LINK | SetCredentials.CRED_UNLINK,
                     set_type=SetCredentials.ESET_OWN
                    )

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
        self._become_test('/persons/%s/become_supplier', REL_OBJ_CUSTOMER_SUPPLIER)

    def test_leads_customers01(self):
        self.login()

        self._build_managed_orga()
        Organisation.objects.create(user=self.user, name='Nerv')

        response = self.client.get('/persons/leads_customers')
        self.assertEqual(response.status_code, 200)

        with self.assertNoException():
            orgas_page = response.context['entities']

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

        orgas_set = set(orgas_page.object_list)
        self.assertIn(nerv, orgas_set)
        self.assertIn(acme, orgas_set)
        self.assertIn(fsf,  orgas_set)

    def test_leads_customers03(self):
        self.login()

        nerv = Organisation.objects.create(user=self.user, name='Nerv')
        acme = Organisation.objects.create(user=self.user, name='Acme')
        self.client.post('/persons/%s/become_customer' % nerv.id, data={'id': acme.id})

        response = self.client.get('/persons/leads_customers')
        self.assertEqual(0, response.context['entities'].paginator.count)
