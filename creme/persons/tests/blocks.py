# -*- coding: utf-8 -*-

try:
    from datetime import datetime, timedelta
    from functools import partial

    from creme.creme_core.models import RelationType, Relation, CremeProperty
    from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME
    from creme.creme_core.tests.base import CremeTestCase

    from creme.activities.models import Activity
    from creme.activities.constants import (REL_SUB_ACTIVITY_SUBJECT, REL_SUB_PART_2_ACTIVITY,
                                            REL_SUB_LINKED_2_ACTIVITY,
                                            ACTIVITYTYPE_MEETING, ACTIVITYTYPE_PHONECALL)

    from ..models import *
    from ..constants import *
    from ..blocks import NeglectedOrganisationsBlock
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('BlocksTestCase',)


class BlocksTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'persons', 'activities')

    def setUp(self):
        self.login()

    def _build_customer_orga(self, mng_orga, name, **kwargs):
        customer = Organisation.objects.create(user=self.user, name=name, **kwargs)
        Relation.objects.create(user=self.user, subject_entity=customer,
                                object_entity=mng_orga,
                                type_id=REL_SUB_CUSTOMER_SUPPLIER,
                               )

        return customer

    def _get_neglected_orgas(self):
        neglected_orgas_block = NeglectedOrganisationsBlock()
        return neglected_orgas_block._get_neglected(datetime.now())

    def test_neglected_block01(self):
        #neglected_orgas_block = NeglectedOrganisationsBlock()
        NeglectedOrganisationsBlock()

        orgas = Organisation.objects.all()
        self.assertEqual(1, len(orgas))

        mng_orga = orgas[0]
        self.assertTrue(CremeProperty.objects.filter(type=PROP_IS_MANAGED_BY_CREME, creme_entity=mng_orga).exists())
        self.assertFalse(self._get_neglected_orgas())

        customer01 = Organisation.objects.create(user=self.user, name='orga02')
        self.assertFalse(self._get_neglected_orgas())

        rtype_customer = RelationType.objects.get(pk=REL_SUB_CUSTOMER_SUPPLIER)
        create_rel = partial(Relation.objects.create, user=self.user)
        create_rel(subject_entity=customer01, object_entity=mng_orga, type=rtype_customer)
        self.assertEqual([customer01.id], [orga.id for orga in self._get_neglected_orgas()])

        customer02 = Organisation.objects.create(user=self.user, name='orga03')
        create_rel(subject_entity=customer02, object_entity=mng_orga,
                   type=RelationType.objects.get(pk=REL_SUB_PROSPECT),
                  )
        neglected_orgas =  self._get_neglected_orgas()
        self.assertEqual(2, len(neglected_orgas))
        self.assertEqual(set([customer01.id, customer02.id]), set(orga.id for orga in neglected_orgas))

        create_rel(subject_entity=customer02, object_entity=mng_orga, type=rtype_customer)
        self.assertEqual(2, len(self._get_neglected_orgas()))

    def test_neglected_block02(self):
        user = self.user
        mng_orga = Organisation.objects.all()[0]
        user_contact = Contact.objects.create(user=user, is_user=user, first_name='Naruto', last_name='Uzumaki')

        customer01 = self._build_customer_orga(mng_orga, 'Konoha')
        customer02 = self._build_customer_orga(mng_orga, 'Suna')
        self.assertEqual(2, len(self._get_neglected_orgas()))

        tomorrow = datetime.now() + timedelta(days=1) #so in the future
        meeting  = Activity.objects.create(user=user, type_id=ACTIVITYTYPE_MEETING,
                                           title='meet01', start=tomorrow,
                                           end=tomorrow + timedelta(hours=2),
                                          )

        get_rtype = RelationType.objects.get
        create_rel = partial(Relation.objects.create, user=user, object_entity=meeting)
        create_rel(subject_entity=customer02, type=get_rtype(pk=REL_SUB_ACTIVITY_SUBJECT))
        self.assertEqual(2, len(self._get_neglected_orgas()))

        create_rel(subject_entity=user_contact, type=get_rtype(pk=REL_SUB_PART_2_ACTIVITY))
        self.assertEqual([customer01.id], [orga.id for orga in self._get_neglected_orgas()])

    def test_neglected_block03(self):
        "Past activity => orga is still neglected"
        user = self.user
        mng_orga = Organisation.objects.all()[0]
        user_contact = Contact.objects.create(user=user, is_user=user, first_name='Naruto', last_name='Uzumaki')

        self._build_customer_orga(mng_orga, 'Konoha')
        customer02 = self._build_customer_orga(mng_orga, 'Suna')

        yesterday = datetime.now() - timedelta(days=1) #so in the past
        meeting  = Activity.objects.create(user=user, type_id=ACTIVITYTYPE_MEETING,
                                           title='meet01', start=yesterday,
                                           end=yesterday + timedelta(hours=2),
                                          )

        create_rel = partial(Relation.objects.create, user=user, object_entity=meeting)
        create_rel(subject_entity=customer02,   type_id=REL_SUB_ACTIVITY_SUBJECT)
        create_rel(subject_entity=user_contact, type_id=REL_SUB_PART_2_ACTIVITY)
        self.assertEqual(2, len(self._get_neglected_orgas())) #and not 1

    def test_neglected_block04(self):
        "A people linked to customer is linked to a future activity"
        user = self.user
        mng_orga = Organisation.objects.all()[0]
        user_contact = Contact.objects.create(user=user, is_user=user, first_name='Naruto', last_name='Uzumaki')

        customer = self._build_customer_orga(mng_orga, 'Suna')

        tomorrow = datetime.now() + timedelta(days=1) #so in the future
        meeting = Activity.objects.create(user=user, type_id=ACTIVITYTYPE_MEETING,
                                          title='meet01', start=tomorrow,
                                          end=tomorrow + timedelta(hours=2),
                                         )
        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=user_contact, object_entity=meeting,
                   type_id=REL_SUB_PART_2_ACTIVITY,
                  )

        employee = Contact.objects.create(user=user, first_name='Kankuro', last_name='???')

        get_rtype = RelationType.objects.get
        create_rel(subject_entity=employee, object_entity=customer,
                   type=get_rtype(pk=REL_SUB_EMPLOYED_BY),
                  )
        self.assertEqual(1, len(self._get_neglected_orgas()))

        create_rel(subject_entity=employee, object_entity=meeting,
                   type=get_rtype(pk=REL_SUB_LINKED_2_ACTIVITY),
                  )
        self.assertFalse(self._get_neglected_orgas())

    def test_neglected_block05(self):
        "2 people linked to customer are linked to a future activity"
        user = self.user
        mng_orga = Organisation.objects.all()[0]

        create_contact = partial(Contact.objects.create, user=user)
        user_contact = create_contact(is_user=user, first_name='Naruto', last_name='Uzumaki')

        customer = self._build_customer_orga(mng_orga, 'Suna')

        tomorrow = datetime.now() + timedelta(days=1) #so in the future
        create_activity = partial(Activity.objects.create, user=user, start=tomorrow)
        meeting   = create_activity(title='meet01', type_id=ACTIVITYTYPE_MEETING,
                                    end=tomorrow + timedelta(hours=2)
                                   )
        phonecall = create_activity(title='call01', type_id=ACTIVITYTYPE_PHONECALL,
                                    end=tomorrow + timedelta(minutes=15),
                                   )

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=user_contact, object_entity=phonecall, type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=user_contact, object_entity=meeting,   type_id=REL_SUB_PART_2_ACTIVITY)

        manager  = create_contact(first_name='Gaara', last_name='???')
        employee = create_contact(first_name='Temari', last_name='???')
        create_rel(subject_entity=manager,  object_entity=customer, type_id=REL_SUB_MANAGES)
        create_rel(subject_entity=employee, object_entity=customer, type_id=REL_SUB_EMPLOYED_BY)
        self.assertEqual(1, len(self._get_neglected_orgas()))

        create_rel(subject_entity=manager, object_entity=phonecall, type_id=REL_SUB_PART_2_ACTIVITY)
        self.assertFalse(self._get_neglected_orgas())

        create_rel(subject_entity=employee, object_entity=meeting, type_id=REL_SUB_ACTIVITY_SUBJECT)
        self.assertFalse(self._get_neglected_orgas())

    def test_neglected_block06(self):
        "Future activity, but not with managed organisation !"
        user = self.user
        mng_orga   = Organisation.objects.all()[0]
        customer   = self._build_customer_orga(mng_orga, 'Suna')
        competitor = Organisation.objects.create(user=user, name='Akatsuki')

        tomorrow = datetime.now() + timedelta(days=1) #so in the future
        meeting  = Activity.objects.create(user=user, type_id=ACTIVITYTYPE_MEETING, 
                                           title='meet01', start=tomorrow,
                                           end=tomorrow + timedelta(hours=2),
                                          )

        manager = Contact.objects.create(user=user,  first_name='Gaara', last_name='???')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=manager,  object_entity=customer, type_id=REL_SUB_MANAGES)

        create_rel(subject_entity=manager,    object_entity=meeting, type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=competitor, object_entity=meeting, type_id=REL_SUB_ACTIVITY_SUBJECT)
        self.assertEqual(1, len(self._get_neglected_orgas()))

    def test_neglected_block07(self):
        "Inactive customers are not counted"
        mng_orga   = Organisation.objects.all()[0]
        customer01 = self._build_customer_orga(mng_orga, 'Konoha')
        customer02 = self._build_customer_orga(mng_orga, 'Suna')
        Relation.objects.create(user=self.user, subject_entity=customer02,
                                object_entity=mng_orga, type_id=REL_SUB_INACTIVE
                               )
        self.assertEqual([customer01], list(self._get_neglected_orgas()))

    def test_neglected_block08(self):
        "Deleted customers are not counted"
        mng_orga = Organisation.objects.all()[0]
        customer = self._build_customer_orga(mng_orga, 'Konoha')
        self._build_customer_orga(mng_orga, 'Suna', is_deleted=True)
        self.assertEqual([customer], list(self._get_neglected_orgas()))
