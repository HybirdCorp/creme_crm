# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.utils.translation import ugettext as _

    from creme.creme_core.tests.base import skipIfNotInstalled
    from creme.creme_core.tests.views.list_view_import import CSVImportBaseTestCaseMixin
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import SetCredentials, RelationType, CremePropertyType, CremeProperty

    from creme.documents.models import Document

    from creme.persons.models import Contact, Civility, Organisation

    from .base import _ActivitiesTestCase
    from ..forms.lv_import import (_PATTERNS, _pattern_FL, _pattern_CFL,
            MultiColumnsParticipantsExtractor, SplittedColumnParticipantsExtractor,
            SubjectsExtractor)
    from ..models import Activity, Calendar
    from ..constants import (ACTIVITYTYPE_TASK, NARROW, FLOATING, FLOATING_TIME,
            REL_OBJ_PART_2_ACTIVITY, REL_OBJ_ACTIVITY_SUBJECT,
            ACTIVITYTYPE_MEETING, ACTIVITYSUBTYPE_MEETING_NETWORK)
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('CSVImportActivityTestCase',)


class CSVImportActivityTestCase(_ActivitiesTestCase, CSVImportBaseTestCaseMixin):
    lv_import_data = {
            'step': 1,
            'title_colselect': 1,

            'start_colselect': 0,
            'end_colselect':   0,

            'status_colselect':         0,
            'description_colselect':    0,
            'place_colselect':          0,
            'duration_colselect':       0,
            'is_all_day_colselect':     0,
            'minutes_colselect':        0,
        }

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'activities', 'persons')
        _ActivitiesTestCase.setUpClass()
        #CSVImportBaseTestCaseMixin.setUpClass()

    def test_import01(self):
        self.login()

        url = self._build_import_url(Activity)
        self.assertGET200(url)

        title1 = 'Task#1'; start1 = '';                 end1 = ''
        title2 = 'Task#2'; start2 = '2014-05-28 15:00'; end2 = '2014-05-28 17:00'
        title3 = 'Task#3'; start3 = '2014-05-28 19:00'; end3 = '2014-05-28 18:00' # start > end !!
        title4 = 'Task#4'; start4 = '2014-05-29 12:00'; end4 = '' # no end
        title5 = 'Task#5'; start5 = '2014-05-30';       end5 = '' # FLOATING_TIME
        title6 = 'Task#6'; start6 = '2014-06-01';       end6 = '2014-06-01' # FLOATING_TIME too
        title7 = 'Task#7'; start7 = '2014-06-02';       end7 = '2014-06-02 18:00' #not FLOATING_TIME
        lines = [(title1, start1, end1), (title2, start2, end2), (title3, start3, end3),
                 (title4, start4, end4), (title5, start5, end5), (title6, start6, end6),
                 (title7, start7, end7),
                ]

        doc = self._build_csv_doc(lines)
        response = self.client.post(url, data={'step':     0,
                                               'document': doc.id,
                                              }
                                   )
        self.assertNoFormError(response)

        response = self.client.post(url,
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=self.user.id,
                                              start_colselect=2,
                                              end_colselect=3,
                                              type_selector=self._acttype_field_value(ACTIVITYTYPE_TASK),

                                              #should not be used
                                              busy_colselect=0,
                                              busy_defval=True, 
                                             )
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(len(lines), form.imported_objects_count)

        act1 = self.get_object_or_fail(Activity, title=title1)
        self.assertEqual(ACTIVITYTYPE_TASK, act1.type_id)
        self.assertIsNone(act1.sub_type)
        self.assertIsNone(act1.start)
        self.assertIsNone(act1.end)
        self.assertEqual(FLOATING, act1.floating_type)

        self.assertFalse(act1.relations.all())

        act2 = self.get_object_or_fail(Activity, title=title2)
        self.assertFalse(act2.busy)

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2014, month=5, day=28, hour=15), act2.start)
        self.assertEqual(create_dt(year=2014, month=5, day=28, hour=17), act2.end)
        self.assertEqual(NARROW, act2.floating_type)

        act3 = self.get_object_or_fail(Activity, title=title3)
        self.assertEqual(create_dt(year=2014, month=5, day=28, hour=19, minute=0),
                         act3.start
                        )
        self.assertEqual(create_dt(year=2014, month=5, day=28, hour=19, minute=15),
                         act3.end
                        )
        self.assertEqual(NARROW, act3.floating_type)

        act4 = self.get_object_or_fail(Activity, title=title4)
        self.assertEqual(create_dt(year=2014, month=5, day=29, hour=12, minute=0),
                         act4.start
                        )
        self.assertEqual(create_dt(year=2014, month=5, day=29, hour=12, minute=15),
                         act4.end
                        )
        self.assertEqual(NARROW, act4.floating_type)

        act5 = self.get_object_or_fail(Activity, title=title5)
        self.assertEqual(create_dt(year=2014, month=5, day=30, hour=0, minute=0),
                         act5.start
                        )
        self.assertEqual(create_dt(year=2014, month=5, day=30, hour=23, minute=59),
                         act5.end
                        )
        self.assertEqual(FLOATING_TIME, act5.floating_type)

        act6 = self.get_object_or_fail(Activity, title=title6)
        self.assertEqual(create_dt(year=2014, month=6, day=1, hour=0, minute=0),
                         act6.start
                        )
        self.assertEqual(create_dt(year=2014, month=6, day=1, hour=23, minute=59),
                         act6.end
                        )
        self.assertEqual(FLOATING_TIME, act6.floating_type)

        act7 = self.get_object_or_fail(Activity, title=title7)
        self.assertEqual(create_dt(year=2014, month=6, day=2, hour=0, minute=0),
                         act7.start
                        )
        self.assertEqual(create_dt(year=2014, month=6, day=2, hour=18, minute=00),
                         act7.end
                        )
        self.assertEqual(NARROW, act7.floating_type)

        errors = list(form.import_errors)
        self.assertEqual(1, len(errors), [e for e in errors])

        error = errors[0]
        self.assertEqual(act3, error.instance)
        self.assertEqual(_('End time is before start time'), error.message)

    def test_import02(self):
        """Static user participants (+ calendars), dynamic participants with
        search on first_name/last_name.
        Dynamic subjects without creation.
        """
        self.login()
        user = self.user
        user_contact = user.linked_contact

        other_user = self.other_user
        other_contact = other_user.linked_contact

        create_contact = partial(Contact.objects.create, user=user)
        participant1 = create_contact(first_name='Tatsumi', last_name='Oga')
        participant2 = create_contact(first_name='Aoi',     last_name='Kunieda')

        unfoundable = 'Behemoth'
        self.assertFalse(Contact.objects.filter(last_name=unfoundable).exists())

        subject = Organisation.objects.create(user=user, name='Ishiyama')

        title1 = 'Meeting#1'
        title2 = 'Meeting#2'
        title3 = 'Meeting#3'
        title4 = 'Meeting#4'
        lines = [(title1, participant1.first_name, participant1.last_name, subject.name),
                 (title2, '',                      participant2.last_name, ''),
                 (title3, '',                      unfoundable,            ''), #unfoundable Contact -> error
                 (title4, user_contact.first_name, user_contact.last_name, ''), #no doublon
                ]

        Calendar.get_user_default_calendar(user)
        my_calendar = Calendar.objects.create(user=user, is_default=False,
                                              name='Imported activities',
                                             )

        doc = self._build_csv_doc(lines)
        data = dict(self.lv_import_data,
                    document=doc.id,
                    user=user.id,
                    type_selector=self._acttype_field_value(ACTIVITYTYPE_MEETING,
                                                            ACTIVITYSUBTYPE_MEETING_NETWORK,
                                                           ),

                    my_participation=True,
                    participating_users=other_user.pk,

                    participants_mode=1, #search with 1 or 2 columns
                    participants_first_name_colselect=2,
                    participants_last_name_colselect=3,

                    subjects_colselect=4,
                   )

        #Validation errors ----------
        response = self.client.post(self._build_import_url(Activity), data=data)
        self.assertFormError(response, 'form', 'my_calendar',
                             _(u'If you participate, you have to choose one of your calendars.')
                            )

        response = self.client.post(self._build_import_url(Activity),
                                    data=dict(data,
                                              participants_first_name_colselect=100, #invalid choice
                                             )
                                   )
        self.assertFormError(response, 'form', 'participants', 'Invalid index')

        #---------
        response = self.client.post(self._build_import_url(Activity),
                                    data=dict(data, my_calendar=my_calendar.pk)
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        act1 = self.get_object_or_fail(Activity, title=title1)
        self.assertEqual(ACTIVITYTYPE_MEETING, act1.type_id)
        self.assertEqual(ACTIVITYSUBTYPE_MEETING_NETWORK, act1.sub_type_id)

        self.assertRelationCount(1, act1, REL_OBJ_PART_2_ACTIVITY, user_contact)
        self.assertRelationCount(1, act1, REL_OBJ_PART_2_ACTIVITY, other_contact)
        self.assertEqual({my_calendar, Calendar.get_user_default_calendar(other_user)},
                         set(act1.calendars.all())
                        )

        self.assertRelationCount(1, act1, REL_OBJ_PART_2_ACTIVITY, participant1)
        self.assertRelationCount(0, act1, REL_OBJ_PART_2_ACTIVITY, participant2)

        self.assertRelationCount(1, act1, REL_OBJ_ACTIVITY_SUBJECT, subject)

        #---------
        act2 = self.get_object_or_fail(Activity, title=title2)
        self.assertRelationCount(1, act2, REL_OBJ_PART_2_ACTIVITY, user_contact)
        self.assertRelationCount(1, act2, REL_OBJ_PART_2_ACTIVITY, other_contact)
        self.assertRelationCount(1, act2, REL_OBJ_PART_2_ACTIVITY, participant2)

        #---------
        act3 = self.get_object_or_fail(Activity, title=title3)
        self.assertFalse(Contact.objects.filter(last_name=unfoundable).exists()) #not created

        self.assertEqual(len(lines), form.imported_objects_count)

        errors = list(form.import_errors)
        self.assertEqual(1, len(errors), [e for e in errors])

        error = errors[0]
        self.assertEqual(act3, error.instance)
        self.assertEqual(_(u'The participant «%s» is unfoundable') % unfoundable,
                         error.message
                        )

        #---------
        act4 = self.get_object_or_fail(Activity, title=title4)
        self.assertRelationCount(1, act4, REL_OBJ_PART_2_ACTIVITY, user_contact) #not 2

    def test_import03(self):
        "Dynamic participants with cell splitting & pattern '$last_name $first_name'."
        self.login()
        user = self.user

        other_user = self.other_user
        other_contact = other_user.linked_contact

        create_contact = partial(Contact.objects.create, user=user)
        participant1 = create_contact(first_name='Tatsumi', last_name='Oga')
        participant2 = create_contact(first_name='Aoi',     last_name='Kunieda')
        participant3 = create_contact(first_name='Kaiser',
                                      last_name='de Emperana Beelzebub', #spaces in last name
                                     )

        unfoundable  = 'Behemoth'
        unfoundable2 = u"En'Ô"
        self.assertFalse(Contact.objects.filter(last_name__in=(unfoundable, unfoundable2)).exists())

        title1 = 'Meeting#1'
        title2 = 'Meeting#2'
        title3 = 'Meeting#3'
        title4 = 'Meeting#4'
        title5 = 'Meeting#5'
        lines = [(title1, '%s %s/%s %s' % (participant1.last_name, participant1.first_name,
                                           participant2.last_name, participant2.first_name,
                                          )
                 ),
                 (title2, '%s %s' % (other_contact.last_name,
                                     other_contact.first_name,
                                    )
                 ),
                 (title3, ' %s %s ' % (participant2.last_name, participant2.first_name)), #trailing spaces
                 (title4, '%s %s/%s %s/%s/' % (unfoundable,            unfoundable,
                                                  participant2.last_name, participant2.first_name,
                                                  unfoundable2,
                                                 )
                 ),
                 (title5, '%s %s/%s' % (participant3.last_name, participant3.first_name,
                                        participant2.last_name,
                                       )
                 ),
                ]

        doc = self._build_csv_doc(lines)
        response = self.client.post(self._build_import_url(Activity),
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=user.id,
                                              type_selector=self._acttype_field_value(ACTIVITYTYPE_MEETING,
                                                                                      ACTIVITYSUBTYPE_MEETING_NETWORK,
                                                                                     ),

                                              participants_mode='2', #search with pattern
                                              participants_separator='/',
                                              participants_pattern=4, #'$last_name $first_name'
                                              participants_colselect=2,
                                             )
                                   )
        self.assertNoFormError(response)

        #---------
        act1 = self.get_object_or_fail(Activity, title=title1)
        self.assertRelationCount(1, act1, REL_OBJ_PART_2_ACTIVITY, participant1)
        self.assertRelationCount(1, act1, REL_OBJ_PART_2_ACTIVITY, participant2)

        #---------
        act2 = self.get_object_or_fail(Activity, title=title2)
        self.assertRelationCount(0, act2, REL_OBJ_PART_2_ACTIVITY, participant1)

        self.assertRelationCount(1, act2, REL_OBJ_PART_2_ACTIVITY, other_contact)
        self.assertEqual([Calendar.get_user_default_calendar(other_user)],
                         list(act2.calendars.all())
                        )

        #---------
        act3 = self.get_object_or_fail(Activity, title=title3)
        self.assertRelationCount(0, act3, REL_OBJ_PART_2_ACTIVITY, participant1)
        self.assertRelationCount(1, act3, REL_OBJ_PART_2_ACTIVITY, participant2)

        #---------
        act4 = self.get_object_or_fail(Activity, title=title4)
        self.assertRelationCount(0, act4, REL_OBJ_PART_2_ACTIVITY, participant1)
        self.assertRelationCount(1, act4, REL_OBJ_PART_2_ACTIVITY, participant2)

        self.assertFalse(Contact.objects.filter(last_name=unfoundable).exists())

        with self.assertNoException():
            form = response.context['form']

        errors = list(form.import_errors)
        self.assertEqual(2, len(errors))

        error = errors[0]
        self.assertEqual(act4, error.instance)
        err_fmt = _(u'The participant «%s» is unfoundable')
        self.assertEqual(err_fmt % ('%s %s' % (unfoundable, unfoundable)),
                         error.message
                        )

        error = errors[1]
        self.assertEqual(act4, error.instance)
        self.assertEqual(err_fmt % unfoundable2, error.message)

        #---------
        act5 = self.get_object_or_fail(Activity, title=title5)
        self.assertRelationCount(1, act5, REL_OBJ_PART_2_ACTIVITY, participant3)
        self.assertRelationCount(1, act5, REL_OBJ_PART_2_ACTIVITY, participant2)

    def test_import04(self):
        "Another cell splitting type: pattern '$civility $first_name $last_name'."
        self.login()
        user = self.user

        miss = self.get_object_or_fail(Civility, pk=2)
        aoi = Contact.objects.create(user=user, first_name='Aoi', last_name='Kunieda', civility=miss)

        title1 = 'Meeting#1'
        lines = [(title1, ' %s %s %s ' % (aoi.civility, aoi.first_name, aoi.last_name))] #+trailng spaces

        doc = self._build_csv_doc(lines)
        url = self._build_import_url(Activity)
        data = dict(self.lv_import_data,
                    document=doc.id,
                    user=user.id,
                    type_selector=self._acttype_field_value(ACTIVITYTYPE_MEETING,
                                                            ACTIVITYSUBTYPE_MEETING_NETWORK,
                                                           ),

                    participants_mode=2, #search with pattern
                    participants_separator='/',
                    participants_pattern=1, #$civility $first_name $last_name
                    participants_colselect=2,
                   )

        response = self.client.post(url, data=dict(data, participants_pattern=5)) #invalid pattern
        self.assertFormError(response, 'form', 'participants', 'Invalid pattern')

        #----------
        response = self.client.post(url, data=data)
        self.assertNoFormError(response)

        act1 = self.get_object_or_fail(Activity, title=title1)
        self.assertRelationCount(1, act1, REL_OBJ_PART_2_ACTIVITY, aoi)

    def test_import05(self):
        "Dynamic participants with search on first_name/last_name + creation"
        self.login()

        title = 'Task#1'
        first_name = 'Aoi'
        last_name = 'Kunieda'

        orga = Organisation.objects.create(user=self.user, name=last_name) #should not be used as subject

        doc = self._build_csv_doc([(title, first_name, last_name)])
        response = self.client.post(self._build_import_url(Activity),
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=self.user.id,
                                              type_selector=self._acttype_field_value(ACTIVITYTYPE_TASK),

                                              participants_mode=1, #search with 1 or 2 columns
                                              participants_first_name_colselect=2,
                                              participants_last_name_colselect=3,
                                              participants_create=True,
                                             )
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        self.assertFalse([unicode(e) for e in form.import_errors])

        task = self.get_object_or_fail(Activity, title=title)
        aoi = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertRelationCount(1, task, REL_OBJ_PART_2_ACTIVITY, aoi)
        self.assertRelationCount(0, task, REL_OBJ_ACTIVITY_SUBJECT, orga)

    def test_import06(self):
        "Dynamic participants with cell splitting + creation"
        self.login()

        aoi = Contact.objects.create(user=self.user, first_name='Aoi', last_name='Kunieda')

        title = 'Task#1'
        first_name = 'Tatsumi'
        last_name = 'Oga'
        doc = self._build_csv_doc([(title, '%s %s#%s %s' % (first_name,     last_name,
                                                            aoi.first_name, aoi.last_name,
                                                           )
                                   )
                                  ]
                                 )
        response = self.client.post(self._build_import_url(Activity),
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=self.user.id,
                                              type_selector=self._acttype_field_value(ACTIVITYTYPE_TASK),

                                              participants_mode=2, #search with pattern
                                              participants_separator='#',
                                              participants_pattern=3, #'$first_name $last_name'
                                              participants_colselect=2,
                                              participants_create=True,
                                             )
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        self.assertFalse([unicode(e) for e in form.import_errors])

        task = self.get_object_or_fail(Activity, title=title)
        self.assertRelationCount(1, task, REL_OBJ_PART_2_ACTIVITY, aoi)

        oga = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertRelationCount(1, task, REL_OBJ_PART_2_ACTIVITY, oga)

    def test_import07(self):
        "Search on first_name/last_name + not creation credentials"
        self.login(is_superuser=False, allowed_apps=('activities', 'persons', 'documents'), 
                   creatable_models=[Activity, Document], #not Contact
                  )
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW | EntityCredentials.LINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        title = 'Task#1'
        first_name = 'Aoi'
        last_name = 'Kunieda'
        doc = self._build_csv_doc([(title, first_name, last_name)])
        response = self.client.post(self._build_import_url(Activity),
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=self.user.id,
                                              type_selector=self._acttype_field_value(ACTIVITYTYPE_TASK),

                                              participants_mode=1, #search with 1 or 2 columns
                                              participants_first_name_colselect=2,
                                              participants_last_name_colselect=3,
                                              participants_create=True, #not used
                                             )
                                   )
        self.assertNoFormError(response)

        self.get_object_or_fail(Activity, title=title)
        self.assertFalse(Contact.objects.filter(first_name=first_name, last_name=last_name))

    def test_import08(self):
        "Property creation (regular post creation handler should be called)"
        self.login()

        ptype = CremePropertyType.create(str_pk='test-prop_imported', text='Has been imported')

        title = 'Task#1'
        doc = self._build_csv_doc([(title, 'Aoi', 'Kunieda')])
        response = self.client.post(self._build_import_url(Activity),
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=self.user.id,
                                              type_selector=self._acttype_field_value(ACTIVITYTYPE_TASK),

                                              property_types=[ptype.id],
                                             )
                                   )
        self.assertNoFormError(response)

        act = self.get_object_or_fail(Activity, title=title)
        self.get_object_or_fail(CremeProperty, type=ptype, creme_entity=act.id)

    def test_import_subjects01(self):
        """Subject: Contact is searched if Organisation is not found.
        No creation asked.
        """
        self.login()

        title1 = 'Task#1'; title2 = 'Task#2'; title3 = 'Task#3'
        title4 = 'Task#4'; title5 = 'Task#5'; title6 = 'Task#6'

        create_contact = partial(Contact.objects.create, user=self.user)
        aoi    = create_contact(first_name='Aoi', last_name='Kunieda')
        furyo1 = create_contact(last_name='Furyo')
        furyo2 = create_contact(last_name='Furyo')

        name = 'Ishiyama'

        create_orga = partial(Organisation.objects.create, user=self.user)
        clan1 = create_orga(name='Clan')
        clan2 = create_orga(name='Clan')

        doc = self._build_csv_doc([(title1, unicode(aoi)),
                                   (title2, (u' %s '  % aoi).upper()),
                                   (title3, u' %s '  % name),
                                   (title4, clan1.name),
                                   (title5, furyo1.last_name),
                                   (title6, u'%s/%s' % (aoi, clan1.name)),
                                  ]
                                 )
        response = self.client.post(self._build_import_url(Activity),
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=self.user.id,
                                              type_selector=self._acttype_field_value(ACTIVITYTYPE_TASK),

                                              subjects_colselect=2,
                                              subjects_separator='/',
                                             )
                                   )
        self.assertNoFormError(response)

        task1 = self.get_object_or_fail(Activity, title=title1)
        self.assertRelationCount(1, task1, REL_OBJ_ACTIVITY_SUBJECT, aoi)

        task2 = self.get_object_or_fail(Activity, title=title2)
        self.assertRelationCount(1, task2, REL_OBJ_ACTIVITY_SUBJECT, aoi)

        task3 = self.get_object_or_fail(Activity, title=title3)
        self.assertRelationCount(0, task3, REL_OBJ_ACTIVITY_SUBJECT, aoi)
        self.assertFalse(Organisation.objects.filter(name__icontains=name))

        task4 = self.get_object_or_fail(Activity, title=title4)
        self.assertRelationCount(1, task4, REL_OBJ_ACTIVITY_SUBJECT, clan1)
        self.assertRelationCount(1, task4, REL_OBJ_ACTIVITY_SUBJECT, clan2)

        task5 = self.get_object_or_fail(Activity, title=title5)
        self.assertRelationCount(1, task5, REL_OBJ_ACTIVITY_SUBJECT, furyo1)
        self.assertRelationCount(1, task5, REL_OBJ_ACTIVITY_SUBJECT, furyo2)

        task6 = self.get_object_or_fail(Activity, title=title6)
        self.assertRelationCount(1, task6, REL_OBJ_ACTIVITY_SUBJECT, aoi)
        self.assertRelationCount(1, task6, REL_OBJ_ACTIVITY_SUBJECT, clan1)
        self.assertRelationCount(1, task6, REL_OBJ_ACTIVITY_SUBJECT, clan2)

        with self.assertNoException():
            form = response.context['form']

        errors = list(form.import_errors)
        self.assertEqual(4, len(errors))

        error = errors[0]
        self.assertEqual(task3, error.instance)
        self.assertEqual(_(u'The subject «%s» is unfoundable') % name,
                         error.message
                        )

        error = errors[1]
        self.assertEqual(task4, error.instance)
        err_fmt = _(u'Several «%(type)s» were found for the search «%(search)s»')
        self.assertEqual(err_fmt % {'type':   _('Organisations'),
                                    'search': clan1.name,
                                   },
                         error.message
                        )

        error = errors[2]
        self.assertEqual(task5, error.instance)
        self.assertEqual(err_fmt % {'type':   _('Contacts'),
                                    'search': furyo1.last_name,
                                   },
                         error.message
                        )

        error = errors[3]
        self.assertEqual(task6, error.instance)
        self.assertEqual(err_fmt % {'type':   _('Organisations'),
                                    'search': clan1.name,
                                   },
                         error.message
                        )

    def test_import_subjects02(self):
        "Subject: creation."
        self.login()

        title = 'My task'
        name = 'Ishiyama'

        doc = self._build_csv_doc([(title, u' %s '  % name)])
        response = self.client.post(self._build_import_url(Activity),
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=self.user.id,
                                              type_selector=self._acttype_field_value(ACTIVITYTYPE_TASK),

                                              subjects_colselect=2,
                                              subjects_create=True,
                                             )
                                   )
        self.assertNoFormError(response)

        task = self.get_object_or_fail(Activity, title=title)
        orga = self.get_object_or_fail(Organisation, name=name)
        self.assertRelationCount(1, task, REL_OBJ_ACTIVITY_SUBJECT, orga)

    def test_import_subjects03(self):
        "Subject: creation credentials."
        self.login(is_superuser=False, allowed_apps=('activities', 'persons', 'documents'), 
                   creatable_models=[Activity, Document], #not Organisation
                  )
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW | EntityCredentials.LINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        title = 'Task#1'
        name = 'Ishiyama'
        doc = self._build_csv_doc([(title, u' %s '  % name)])
        response = self.client.post(self._build_import_url(Activity),
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=self.user.id,
                                              type_selector=self._acttype_field_value(ACTIVITYTYPE_TASK),

                                              subjects_colselect=2,
                                              subjects_create=True, #should not be used
                                             )
                                   )
        self.assertNoFormError(response)

        self.get_object_or_fail(Activity, title=title)
        self.assertFalse(Organisation.objects.filter(name__icontains=name))

    def test_import_subjects04(self):
        "Subject: view credentials."
        self.login(is_superuser=False, allowed_apps=('activities', 'persons', 'documents'),
                   creatable_models=[Activity, Document],
                  )
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW | EntityCredentials.LINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        title = 'My Task'
        name = 'Ishiyama'

        create_orga = Organisation.objects.create
        orga1 = create_orga(user=self.user, name=name)
        orga2 = create_orga(user=self.other_user, name=name)

        doc = self._build_csv_doc([(title, name)])
        response = self.client.post(self._build_import_url(Activity),
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=self.user.id,
                                              type_selector=self._acttype_field_value(ACTIVITYTYPE_TASK),

                                              subjects_colselect=2,
                                             )
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(0, len(form.import_errors))

        task = self.get_object_or_fail(Activity, title=title)
        self.assertRelationCount(1, task, REL_OBJ_ACTIVITY_SUBJECT, orga1)
        self.assertRelationCount(0, task, REL_OBJ_ACTIVITY_SUBJECT, orga2)

    def test_pattern1(self):
        "Pattern #1: 'Civility FirstName LastName'"
        with self.assertNoException():
            pattern_func = _PATTERNS['1']
            result = pattern_func('Ms. Aoi Kunieda')

        expected = ('Ms.', 'Aoi', 'Kunieda')
        self.assertEqual(expected, result)
        self.assertEqual((None, 'Aoi', 'Kunieda'), pattern_func('Aoi Kunieda'))
        self.assertEqual((None, None, 'Kunieda'), pattern_func('Kunieda'))
        self.assertEqual(('Mr.', 'Kaiser', 'de Emperana Beelzebub'),
                         pattern_func('Mr. Kaiser de Emperana Beelzebub')
                        )
        self.assertEqual(expected, pattern_func(' Ms. Aoi Kunieda '))

    def test_pattern2(self):
        "Pattern #2: 'Civility LastName FirstName'"
        with self.assertNoException():
            pattern_func = _PATTERNS['2']
            result = pattern_func('Ms. Kunieda Aoi')

        expected = ('Ms.', 'Aoi', 'Kunieda')
        self.assertEqual(expected, result)
        self.assertEqual(expected, pattern_func(' Ms.  Kunieda  Aoi '))
        self.assertEqual((None, 'Aoi', 'Kunieda'), pattern_func(' Kunieda  Aoi '))
        self.assertEqual(('Mr.', 'Kaiser', 'de Emperana Beelzebub'),
                         pattern_func('Mr. de Emperana Beelzebub Kaiser')
                        )
        self.assertEqual((None, None, 'Kunieda'), pattern_func('Kunieda'))

    def test_pattern3(self):
        "Pattern #3: 'FirstName LastName'"
        with self.assertNoException():
            pattern_func = _PATTERNS['3']
            result = pattern_func('Aoi Kunieda')

        expected = (None, 'Aoi', 'Kunieda')
        self.assertEqual(expected, result)
        self.assertEqual(expected, pattern_func('  Aoi  Kunieda '))
        self.assertEqual((None, None, 'Kunieda'), pattern_func('Kunieda'))
        self.assertEqual((None, 'Kaiser', 'de Emperana Beelzebub'),
                         pattern_func('Kaiser de Emperana Beelzebub ')
                        )

    def test_pattern4(self):
        "Pattern #4: 'LastName FirstName'"
        with self.assertNoException():
            pattern_func = _PATTERNS['4']
            result = pattern_func('Kunieda Aoi')

        self.assertEqual((None, 'Aoi', 'Kunieda'), result)
        self.assertEqual((None, 'Kaiser', 'de Emperana Beelzebub'),
                         pattern_func('de Emperana Beelzebub Kaiser ')
                        )

    def test_participants_multicol_extractor01(self):
        self.login()
        user = self.user

        #-----
        ext = MultiColumnsParticipantsExtractor(1, 2)

        first_name = 'Aoi'
        last_name = 'Kunieda'
        contacts, err_msg = ext.extract_value([first_name, last_name], user)
        self.assertEqual((), contacts)
        self.assertEqual((_(u'The participant «%s» is unfoundable') % 
                          _('%(first_name)s %(last_name)s') % {
                                'first_name': first_name,
                                'last_name':  last_name,
                            },
                         ),
                         err_msg
                        )

        create_contact = partial(Contact.objects.create, user=user, last_name=last_name)
        aoi = create_contact(first_name=first_name)
        contacts, err_msg = ext.extract_value([first_name, last_name], user)
        self.assertEqual([aoi], list(contacts))
        self.assertFalse(err_msg)

        #-----
        ext = MultiColumnsParticipantsExtractor(0, 1)
        contacts, err_msg = ext.extract_value([last_name], user)
        self.assertEqual([aoi], list(contacts))
        self.assertEqual((), err_msg)

        ittosai = create_contact(first_name=u'Ittôsai')
        contacts, err_msg = ext.extract_value([last_name], user)
        self.assertEqual({aoi, ittosai}, set(contacts))
        self.assertEqual((_(u'Several contacts were found for the search «%s»') % last_name,),
                         err_msg
                        )

        create_contact(first_name='Shinobu')
        create_contact(first_name=u'Kôta')
        create_contact(first_name='')
        create_contact(first_name='Tatsumi')
        contacts, err_msg = ext.extract_value([last_name], user)
        self.assertFalse(contacts)
        self.assertEqual((_(u'Too many contacts were found for the search «%s»') % last_name,),
                         err_msg
                        )

    def test_participants_multicol_extractor02(self):
        "View credentials"
        self.login(is_superuser=False)
        user = self.user
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW | EntityCredentials.LINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        last_name = 'Kunieda'
        create_contact = partial(Contact.objects.create, last_name=last_name)
        aoi = create_contact(user=user, first_name='Aoi')
        create_contact(user=self.other_user, first_name=u'Ittôsai')

        ext = MultiColumnsParticipantsExtractor(0, 1)
        contacts, err_msg = ext.extract_value([last_name], user)
        self.assertEqual([aoi], list(contacts))
        self.assertFalse(err_msg)

    def test_participants_multicol_extractor03(self):
        "Link credentials"
        self.login(is_superuser=False)
        user = self.user
        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(value=EntityCredentials.VIEW | EntityCredentials.LINK,
                  set_type=SetCredentials.ESET_OWN,
                 )
        create_sc(value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)

        ext = MultiColumnsParticipantsExtractor(0, 1)
        last_name = 'Kunieda'

        def extract():
            return ext.extract_value([last_name], user)

        contacts, err_msg = extract()
        self.assertFalse(contacts)
        self.assertEqual((_(u'The participant «%s» is unfoundable') % last_name,),
                         err_msg
                        )

        create_contact = partial(Contact.objects.create, last_name=last_name)
        create_contact(user=self.other_user, first_name=u'Ittôsai')

        contacts, err_msg = extract()
        self.assertFalse(contacts)
        self.assertEqual((_(u'No linkable contact found for the search «%s»') % last_name,),
                         err_msg
                        )

        aoi = create_contact(user=user, first_name='Aoi')
        contacts, err_msg = extract()
        self.assertEqual([aoi], contacts)
        self.assertFalse(err_msg)

    def test_participants_multicol_extractor04(self):
        "Creation if not found"
        self.login()

        ext = MultiColumnsParticipantsExtractor(1, 2, create_if_unfound=True)
        first_name = 'Aoi'
        last_name = 'Kunieda'

        def extract():
            return ext.extract_value([first_name, last_name], self.user)

        contacts, err_msg = extract()
        self.assertFalse(err_msg)

        aoi = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertEqual([aoi], list(contacts))

        extract()
        self.assertEqual(1, Contact.objects.filter(first_name=first_name, last_name=last_name).count())

    def test_participants_singlecol_extractor01(self):
        "SplittedColumnParticipantsExtractor"
        self.login()
        user = self.user
        ext = SplittedColumnParticipantsExtractor(1, '#', _pattern_FL)

        create_contact = partial(Contact.objects.create, user=user, last_name='Kunieda')
        searched = 'Aoi Kunieda'
        contacts, err_msg = ext.extract_value([searched], user)
        self.assertFalse(contacts)
        self.assertEqual([_(u'The participant «%s» is unfoundable') % searched,],
                         err_msg
                        )

        aoi = create_contact(first_name='Aoi')
        oga = create_contact(first_name='Tatsumi', last_name='Oga')
        contacts, err_msg = ext.extract_value(['Aoi Kunieda#Tatsumi Oga'], user)
        self.assertEqual({aoi, oga}, set(contacts))
        self.assertFalse(err_msg)

        contacts, err_msg = ext.extract_value(['Aoi Kunieda#Tatsumi Oga#'], user)
        self.assertEqual({aoi, oga}, set(contacts))

        #-------
        searched = 'Kunieda'
        ittosai = create_contact(first_name=u'Ittôsai')
        contacts, err_msg = ext.extract_value([searched], user)
        self.assertEqual({aoi, ittosai}, set(contacts))
        self.assertEqual([_(u'Several contacts were found for the search «%s»') % searched],
                         err_msg
                        )

        create_contact(first_name='Shinobu')
        create_contact(first_name=u'Kôta')
        create_contact(first_name='')
        create_contact(first_name='Tatsumi')
        contacts, err_msg = ext.extract_value([searched], user)
        self.assertFalse(contacts)
        self.assertEqual([_(u'Too many contacts were found for the search «%s»') % searched],
                         err_msg
                        )

    def test_participants_singlecol_extractor02(self):
        "SplittedColumnParticipantsExtractor + credentials"
        self.login(is_superuser=False)
        user = self.user
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW | EntityCredentials.LINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        create_contact = partial(Contact.objects.create, last_name='Kunieda')
        aoi = create_contact(user=user, first_name='Aoi')
        create_contact(user=self.other_user, first_name=u'Ittôsai')

        ext = SplittedColumnParticipantsExtractor(1, '#', _pattern_FL)
        contacts, err_msg = ext.extract_value(['Kunieda'], user)
        self.assertEqual([aoi], contacts)
        self.assertFalse(err_msg)

    def test_participants_singlecol_extractor03(self):
        "Creation if not found + civility"
        self.login()
        user = self.user

        ext = SplittedColumnParticipantsExtractor(1, '#', _pattern_CFL, create_if_unfound=True)

        first_name = 'Aoi'
        last_name = 'Kunieda'
        contacts, err_msg = ext.extract_value(['%s %s' % (first_name, last_name)], user)
        self.assertFalse(err_msg)
        aoi = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertIsNone(aoi.civility)

        first_name = u'Ittôsai'
        contacts, err_msg = ext.extract_value(['Sensei %s %s' % (first_name, last_name)], user)
        self.assertFalse(err_msg)
        ittosai = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertIsNone(ittosai.civility)

        #Civility retrieved by title
        mister = self.get_object_or_fail(Civility, pk=3)
        first_name = 'Tatsumi'
        last_name = 'Oga'
        contacts, err_msg = ext.extract_value(['%s %s %s' % (mister.title, first_name, last_name)], user)
        self.assertFalse(err_msg)
        oga = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertEqual(mister, oga.civility)

        #Civility is not used to search
        contacts, err_msg = ext.extract_value(['Sensei %s %s' % (first_name, last_name)], user)
        self.assertEqual([oga], contacts)
        self.assertEqual(mister, self.refresh(oga).civility)

        #Civility retrieved by short name
        first_name = 'Takayuki'
        last_name = 'Furuichi'
        contacts, err_msg = ext.extract_value(['%s %s %s' % (mister.shortcut, first_name, last_name)], user)
        furuichi = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertEqual(mister, furuichi.civility)

    def test_subjects_extractor01(self):
        "Link credentials."
        self.login(is_superuser=False, allowed_apps=('activities', 'persons', 'documents'),
                   creatable_models=[Activity, Document],
                  )
        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(value=EntityCredentials.VIEW | EntityCredentials.LINK,
                  set_type=SetCredentials.ESET_OWN,
                 )
        create_sc(value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)

        user = self.user
        ext = SubjectsExtractor(1, '/')
        last_name = 'Kunieda'

        def extract():
            return ext.extract_value([last_name], user)

        contacts, err_msg = extract()
        self.assertFalse(contacts)
        self.assertEqual([_(u'The subject «%s» is unfoundable') % last_name],
                         err_msg
                        )

        create_contact = partial(Contact.objects.create, last_name=last_name)
        create_contact(user=self.other_user, first_name=u'Ittôsai')

        contacts, err_msg = extract()
        self.assertFalse(contacts)
        self.assertEqual([_(u'No linkable entity found for the search «%s»') % last_name],
                         err_msg
                        )

        aoi = create_contact(user=user, first_name='Aoi')
        contacts, err_msg = extract()
        self.assertEqual([aoi], contacts)
        self.assertFalse(err_msg)

    def test_subjects_extractor02(self):
        "Limit"
        self.login()
        user = self.user
        ext = SubjectsExtractor(1, '#')

        last_name = 'Kunieda'

        create_contact = partial(Contact.objects.create, user=user, last_name=last_name)
        create_contact(first_name='Aoi')
        create_contact(first_name=u'Ittôsai')
        create_contact(first_name='Shinobu')
        create_contact(first_name=u'Kôta')
        create_contact(first_name='')
        create_contact(first_name='Tatsumi')

        contacts, err_msg = ext.extract_value([' %s #' % last_name], user)
        self.assertFalse(contacts)
        self.assertEqual([_(u'Too many «%(type)s» were found for the search «%(search)s»') % {
                                'type':   _('Contacts'),
                                'search': last_name,
                            }
                         ],
                         err_msg
                        )

    @skipIfNotInstalled('creme.tickets')
    def test_subjects_extractor03(self):
        "Other ContentType"
        from creme.tickets.models import Ticket, Priority, Criticity

        self.populate('tickets')

        rtype = self.get_object_or_fail(RelationType, pk=REL_OBJ_ACTIVITY_SUBJECT)
        self.assertIn(Ticket, (ct.model_class() for ct in rtype.object_ctypes.all()))

        self.login()
        user = self.user
        last_name = 'Kunieda'
        ticket = Ticket.objects.create(user=user, title="%s's ticket" % last_name,
                                       priority=Priority.objects.all()[0],
                                       criticity=Criticity.objects.all()[0],
                                      )

        ext = SubjectsExtractor(1, '/')
        extracted, err_msg = ext.extract_value([last_name], user)
        self.assertEqual([ticket], extracted)
        self.assertFalse(err_msg)
