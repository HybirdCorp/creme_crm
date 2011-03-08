# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, Relation, CremeProperty
from creme_core.management.commands.creme_populate import Command as PopulateCommand
from creme_core.constants import PROP_IS_MANAGED_BY_CREME

from activities.models import Meeting, PhoneCall, PhoneCallType
from activities.constants import REL_SUB_ACTIVITY_SUBJECT, REL_SUB_PART_2_ACTIVITY, REL_SUB_LINKED_2_ACTIVITY

from persons.models import *
from persons.constants import *
from persons.blocks import neglected_orgas_block


class PersonsTestCase(TestCase):
    def login(self):
        if not self.user:
            user = User.objects.create(username='Kaneda')
            user.set_password(self.password)
            user.is_superuser = True
            user.save()
            self.user = user

        logged = self.client.login(username=self.user.username, password=self.password)
        self.assert_(logged, 'Not logged in')

    def setUp(self):
        PopulateCommand().handle(application=['creme_core', 'persons'])
        self.password = 'test'
        self.user = None

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

    def create_contact(self, first_name, last_name): #useful ??
        response = self.client.post('/persons/contact/add', follow=True,
                                    data={
                                            'user':       self.user.pk,
                                            'first_name': first_name,
                                            'last_name':  last_name,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

        return response

    def test_contact_createview01(self):
        self.login()

        response = self.client.get('/persons/contact/add')
        self.assertEqual(response.status_code, 200)

        count = Contact.objects.count()
        first_name = 'Spike'
        last_name  = 'Spiegel'
        response = self.create_contact(first_name, last_name)
        self.assertEqual(count + 1, Contact.objects.count())

        try:
            contact = Contact.objects.get(first_name=first_name)
        except Exception, e:
            self.fail(str(e))
        self.assertEqual(last_name,  contact.last_name)

        self.assert_(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assert_(response.redirect_chain[0][0].endswith('/persons/contact/%s' % contact.id))

    def test_orga_createview01(self):
        self.login()

        response = self.client.get('/persons/organisation/add')
        self.assertEqual(response.status_code, 200)

        count = Organisation.objects.count()
        name  = 'Spectre'
        description = 'DESCRIPTION'
        response = self.client.post('/persons/organisation/add', follow=True,
                                    data={
                                            'user':        self.user.pk,
                                            'name':        name,
                                            'description': description,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(count + 1, Organisation.objects.count())

        try:
            orga = Organisation.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))
        self.assertEqual(description,  orga.description)

        self.assert_(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assert_(response.redirect_chain[0][0].endswith('/persons/organisation/%s' % orga.id))

    def test_orga_editview01(self):
        self.login()

        name = 'Bebop'
        orga = Organisation.objects.create(user=self.user, name=name)

        response = self.client.get('/persons/organisation/edit/%s' % orga.id)
        self.assertEqual(response.status_code, 200)

        name += '_edited'
        response = self.client.post('/persons/organisation/edit/%s' % orga.id, follow=True,
                                    data={
                                            'user': self.user.pk,
                                            'name': name,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)
        self.assert_(response.redirect_chain)

        edited_orga = Organisation.objects.get(pk=orga.id)
        self.assertEqual(name, edited_orga.name)

    def test_become_customer(self):
        self.login()

        try:
            mng_orga = Organisation.objects.create(user=self.user, name='Bebop')
            CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=mng_orga)
        except IndexError, e:
            self.fail(str(e))

        customer = Contact.objects.create(user=self.user, first_name='Jet', last_name='Black')

        response = self.client.get('/persons/%s/become_customer/%s' % (customer.id, mng_orga.id), follow=True)
        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain)

        try:
            Relation.objects.get(subject_entity=customer, object_entity=mng_orga, type=REL_SUB_CUSTOMER_OF)
        except Exception, e:
            self.fail(str(e))

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
        PopulateCommand().handle(application=['activities'])
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
        PopulateCommand().handle(application=['activities'])
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
        PopulateCommand().handle(application=['activities'])
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
        PopulateCommand().handle(application=['activities'])
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
        PopulateCommand().handle(application=['activities'])
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

#TODO: tests for edit/delete/detail/list views ; tests for Address model ; test leads_customers view
