# -*- coding: utf-8 -*-

try:
    from datetime import timedelta #datetime
    from functools import partial

    from django.utils.timezone import now

    from creme.creme_core.models import CremeEntity, Relation
    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons.models import Organisation, Contact

    from creme.activities.models import Activity, Status, Calendar
    from creme.activities.constants import (ACTIVITYTYPE_MEETING, ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                                           REL_SUB_PART_2_ACTIVITY)

    from ..models import CommercialApproach
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('CommercialApproachTestCase',)


#TODO: test command
class CommercialApproachTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'activities') #'commercial'

    def _build_entity_field(self, entity):
        return '[{"ctype":"%s", "entity":"%s"}]' % (entity.entity_type_id, entity.id)

    def test_createview(self):
        self.login()
        entity = CremeEntity.objects.create(user=self.user)
        url = '/commercial/approach/add/%s/' % entity.id
        self.assertGET200(url)

        title       = 'TITLE'
        description = 'DESCRIPTION'
        response = self.client.post(url, data={'title':       title,
                                               'description': description,
                                              }
                                   )
        self.assertNoFormError(response)

        commapps = CommercialApproach.objects.all()
        self.assertEqual(1, len(commapps))

        commapp = commapps[0]
        self.assertEqual(title,       commapp.title)
        self.assertEqual(description, commapp.description)
        self.assertEqual(entity.id,   commapp.entity_id)

        self.assertLess((now() - commapp.creation_date).seconds, 10)

        self.assertEqual(title, unicode(commapp))

    def test_merge(self):
        self.login()
        user = self.user

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='NERV')
        orga02 = create_orga(name='Nerv')

        create_commapp = partial(CommercialApproach.objects.create, description='...')
        #create_commapp(title='Commapp01', creation_date=datetime.now(), creme_entity=orga01)
        #create_commapp(title='Commapp02', creation_date=datetime.now(), creme_entity=orga02)
        create_commapp(title='Commapp01', creme_entity=orga01)
        create_commapp(title='Commapp02', creme_entity=orga02)
        self.assertEqual(2, CommercialApproach.objects.count())

        response = self.client.post('/creme_core/entity/merge/%s,%s' % (orga01.id, orga02.id),
                                    follow=True,
                                    data={'user_1':      user.id,
                                          'user_2':      user.id,
                                          'user_merged': user.id,

                                          'name_1':      orga01.name,
                                          'name_2':      orga02.name,
                                          'name_merged': orga01.name,
                                         }
                                   )
        self.assertNoFormError(response)

        self.assertFalse(Organisation.objects.filter(pk=orga02).exists())

        with self.assertNoException():
            orga01 = self.refresh(orga01)

        commapps = CommercialApproach.objects.all()
        self.assertEqual(2, len(commapps))

        for commapp in commapps:
            self.assertEqual(orga01, commapp.creme_entity)

    def test_create_from_activity01(self):
        "No subjects"
        self.login()

        user = self.user
        url = '/activities/activity/add'
        self.assertGET200(url)

        Contact.objects.create(user=user, first_name='Ryoga', last_name='Hibiki', is_user=user) #me

        title = 'Meeting #01'
        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.client.post(url, follow=True,
                                    data={'user':             user.pk,
                                          'title':            title,
                                          'type_selector':    '{"type": "%s", "sub_type": "%s"}' % (
                                                                    ACTIVITYTYPE_MEETING,
                                                                    ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                                                                ),
                                          'status':           Status.objects.all()[0].pk,
                                          'start':            '2011-5-18',
                                          'my_participation': True,
                                          'my_calendar':      my_calendar.pk,

                                          'is_comapp': True,
                                         }
                                   )
        self.assertNoFormError(response)
        self.get_object_or_fail(Activity, type=ACTIVITYTYPE_MEETING, title=title)
        self.assertFalse(CommercialApproach.objects.all())

    def test_create_from_activity02(self): #OK
        self.login()
        user = self.user

        create_contact = partial(Contact.objects.create, user=user)
        create_contact(first_name='Ryoga', last_name='Hibiki', is_user=user) #me
        ranma = create_contact(first_name='Ranma', last_name='Saotome')
        genma = create_contact(first_name='Genma', last_name='Saotome')

        dojo = Organisation.objects.create(user=user, name='Dojo')

        title = 'Meeting #01'
        description = 'Stuffs about the fighting'
        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.client.post('/activities/activity/add', follow=True,
                                    data={'user':             user.pk,
                                          'title':            title,
                                          'type_selector':    '{"type": "%s", "sub_type": "%s"}' % (
                                                                    ACTIVITYTYPE_MEETING,
                                                                    ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                                                                ),
                                          'description':      description,
                                          'status':           Status.objects.all()[0].pk,
                                          'start':            '2011-5-18',
                                          'my_participation': True,
                                          'my_calendar':      my_calendar.pk,

                                          'other_participants': '[%d]' % genma.id,
                                          'subjects':           self._build_entity_field(ranma),
                                          'linked_entities':    self._build_entity_field(dojo),

                                          'is_comapp': True,
                                         }
                                   )
        self.assertNoFormError(response)

        meeting = self.get_object_or_fail(Activity, type=ACTIVITYTYPE_MEETING, title=title)

        comapps = CommercialApproach.objects.filter(related_activity=meeting)
        self.assertEqual(3, len(comapps))
        self.assertEqual(set([genma, ranma, dojo]), set(comapp.creme_entity for comapp in comapps))

        now_value = now()

        for comapp in comapps:
            self.assertEqual(title,       comapp.title)
            self.assertEqual(description, comapp.description)
            self.assertAlmostEqual(now_value, comapp.creation_date, delta=timedelta(seconds=10))

    def test_sync_with_activity(self):
        self.login()

        user = self.user
        title = 'meeting #01'
        description = 'Stuffs about the fighting'
        create_dt = self.create_datetime
        meeting = Activity.objects.create(user=user, title=title, description=description,
                                          type_id=ACTIVITYTYPE_MEETING,
                                          #start=datetime(year=2011, month=5, day=18, hour=14, minute=0),
                                          #end=datetime(year=2011,   month=6, day=1,  hour=15, minute=0)
                                          start=create_dt(year=2011, month=5, day=18, hour=14, minute=0),
                                          end=create_dt(year=2011,   month=6, day=1,  hour=15, minute=0)
                                         )
        ryoga = Contact.objects.create(user=user, first_name='Ryoga', last_name='Hibiki', is_user=user)

        Relation.objects.create(subject_entity=ryoga, type_id=REL_SUB_PART_2_ACTIVITY,
                                object_entity=meeting, user=user
                               )

        comapp = CommercialApproach.objects.create(title=title,
                                                   description=description,
                                                   #creation_date=datetime.now(),
                                                   related_activity_id=meeting.id, #TODO: related_activity=instance after activities refactoring ?
                                                   creme_entity=ryoga,
                                                  )

        title = title.upper()
        meeting.title = title
        meeting.save()
        self.assertEqual(title, self.refresh(comapp).title)

    def test_delete(self):
        self.login()

        orga = Organisation.objects.create(user=self.user, name='NERV')
        comapp = CommercialApproach.objects.create(title='Commapp01',
                                                   description='A commercial approach',
                                                   #creation_date=datetime.now(),
                                                   creme_entity=orga
                                                  )

        orga.delete()
        self.assertDoesNotExist(comapp)
