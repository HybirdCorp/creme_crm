# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.utils.translation import ugettext as _

    from creme.creme_core.tests.base import skipIfNotInstalled
    from creme.creme_core.tests.views.base import CSVImportBaseTestCaseMixin
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import (SetCredentials, RelationType, Relation,
            CremePropertyType, CremeProperty)

    from creme.documents import get_document_model
    from creme.documents.tests.base import skipIfCustomDocument

    from creme.persons.models import Civility
    from creme.persons.tests.base import skipIfCustomContact, skipIfCustomOrganisation

    from .base import _ActivitiesTestCase, skipIfCustomActivity, Contact, Organisation, Activity
    from .. import constants
    from ..forms.mass_import import (_PATTERNS, _pattern_FL, _pattern_CFL,
            MultiColumnsParticipantsExtractor, SplitColumnParticipantsExtractor, SubjectsExtractor)
    from ..models import Calendar
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


Document = get_document_model()


@skipIfCustomDocument
@skipIfCustomActivity
class MassImportActivityTestCase(_ActivitiesTestCase, CSVImportBaseTestCaseMixin):
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

    def test_import01(self):
        user = self.login()

        url = self._build_import_url(Activity)
        self.assertGET200(url)

        title1 = 'Task#1'; start1 = '';                 end1 = ''
        title2 = 'Task#2'; start2 = '2014-05-28 15:00'; end2 = '2014-05-28 17:00'
        title3 = 'Task#3'; start3 = '2014-05-28 19:00'; end3 = '2014-05-28 18:00'  # Start > end !!
        title4 = 'Task#4'; start4 = '2014-05-29 12:00'; end4 = ''  # No end
        title5 = 'Task#5'; start5 = '2014-05-30';       end5 = ''  # FLOATING_TIME
        title6 = 'Task#6'; start6 = '2014-06-01';       end6 = '2014-06-01'  # FLOATING_TIME too
        title7 = 'Task#7'; start7 = '2014-06-02';       end7 = '2014-06-02 18:00'  # Not FLOATING_TIME
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

        response = self.client.post(url, follow=True,
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=user.id,
                                              start_colselect=2,
                                              end_colselect=3,
                                              type_selector=self._acttype_field_value(constants.ACTIVITYTYPE_TASK),

                                              # Should not be used
                                              busy_colselect=0,
                                              busy_defval=True, 
                                             )
                                   )
        self.assertNoFormError(response)

        job = self._execute_job(response)

        results = self._get_job_results(job)
        self.assertEqual(len(lines), len(results))

        act1 = self.get_object_or_fail(Activity, title=title1)
        self.assertEqual(constants.ACTIVITYTYPE_TASK, act1.type_id)
        self.assertIsNone(act1.sub_type)
        self.assertIsNone(act1.start)
        self.assertIsNone(act1.end)
        self.assertEqual(constants.FLOATING, act1.floating_type)

        self.assertFalse(act1.relations.all())

        act2 = self.get_object_or_fail(Activity, title=title2)
        self.assertFalse(act2.busy)

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2014, month=5, day=28, hour=15), act2.start)
        self.assertEqual(create_dt(year=2014, month=5, day=28, hour=17), act2.end)
        self.assertEqual(constants.NARROW, act2.floating_type)

        act3 = self.get_object_or_fail(Activity, title=title3)
        self.assertEqual(create_dt(year=2014, month=5, day=28, hour=19, minute=0),
                         act3.start
                        )
        self.assertEqual(create_dt(year=2014, month=5, day=28, hour=19, minute=15),
                         act3.end
                        )
        self.assertEqual(constants.NARROW, act3.floating_type)

        act4 = self.get_object_or_fail(Activity, title=title4)
        self.assertEqual(create_dt(year=2014, month=5, day=29, hour=12, minute=0),
                         act4.start
                        )
        self.assertEqual(create_dt(year=2014, month=5, day=29, hour=12, minute=15),
                         act4.end
                        )
        self.assertEqual(constants.NARROW, act4.floating_type)

        act5 = self.get_object_or_fail(Activity, title=title5)
        self.assertEqual(create_dt(year=2014, month=5, day=30, hour=0, minute=0),
                         act5.start
                        )
        self.assertEqual(create_dt(year=2014, month=5, day=30, hour=23, minute=59),
                         act5.end
                        )
        self.assertEqual(constants.FLOATING_TIME, act5.floating_type)

        act6 = self.get_object_or_fail(Activity, title=title6)
        self.assertEqual(create_dt(year=2014, month=6, day=1, hour=0, minute=0),
                         act6.start
                        )
        self.assertEqual(create_dt(year=2014, month=6, day=1, hour=23, minute=59),
                         act6.end
                        )
        self.assertEqual(constants.FLOATING_TIME, act6.floating_type)

        act7 = self.get_object_or_fail(Activity, title=title7)
        self.assertEqual(create_dt(year=2014, month=6, day=2, hour=0, minute=0),
                         act7.start
                        )
        self.assertEqual(create_dt(year=2014, month=6, day=2, hour=18, minute=00),
                         act7.end
                        )
        self.assertEqual(constants.NARROW, act7.floating_type)

        jr_errors = [r for r in results if r.messages]
        self.assertEqual(1, len(jr_errors))

        jr_error = jr_errors[0]
        self.assertEqual([_('End time is before start time')],
                         jr_error.messages
                        )
        self.assertEqual(act3, jr_error.entity.get_real_entity())

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_import02(self):
        """Static user participants (+ calendars), dynamic participants with
        search on first_name/last_name.
        Dynamic subjects without creation.
        """
        user = self.login()
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
                 (title3, '',                      unfoundable,            ''),  # Unfoundable Contact -> error
                 (title4, user_contact.first_name, user_contact.last_name, ''),  # No duplicate
                ]

        Calendar.get_user_default_calendar(user)
        my_calendar = Calendar.objects.create(user=user, is_default=False,
                                              name='Imported activities',
                                             )

        doc = self._build_csv_doc(lines)
        data = dict(self.lv_import_data,
                    document=doc.id,
                    user=user.id,
                    type_selector=self._acttype_field_value(constants.ACTIVITYTYPE_MEETING,
                                                            constants.ACTIVITYSUBTYPE_MEETING_NETWORK,
                                                           ),

                    my_participation_0=True,
                    participating_users=other_user.pk,

                    participants_mode=1,  # Search with 1 or 2 columns
                    participants_first_name_colselect=2,
                    participants_last_name_colselect=3,

                    subjects_colselect=4,
                   )

        # Validation errors ----------
        response = self.client.post(self._build_import_url(Activity), data=data)
        self.assertFormError(response, 'form', 'my_participation', _(u'Enter a value if you check the box.'))

        response = self.client.post(self._build_import_url(Activity), follow=True,
                                    data=dict(data,
                                              participants_first_name_colselect=100,  # Invalid choice
                                             )
                                   )
        self.assertFormError(response, 'form', 'participants', 'Invalid index')

        # ---------
        response = self.client.post(self._build_import_url(Activity), follow=True,
                                    data=dict(data, my_participation_1=my_calendar.pk)
                                   )
        self.assertNoFormError(response)

        job = self._execute_job(response)

        act1 = self.get_object_or_fail(Activity, title=title1)
        self.assertEqual(constants.ACTIVITYTYPE_MEETING, act1.type_id)
        self.assertEqual(constants.ACTIVITYSUBTYPE_MEETING_NETWORK, act1.sub_type_id)

        self.assertRelationCount(1, act1, constants.REL_OBJ_PART_2_ACTIVITY, user_contact)
        self.assertRelationCount(1, act1, constants.REL_OBJ_PART_2_ACTIVITY, other_contact)
        self.assertEqual({my_calendar, Calendar.get_user_default_calendar(other_user)},
                         set(act1.calendars.all())
                        )

        self.assertRelationCount(1, act1, constants.REL_OBJ_PART_2_ACTIVITY, participant1)
        self.assertRelationCount(0, act1, constants.REL_OBJ_PART_2_ACTIVITY, participant2)

        self.assertRelationCount(1, act1, constants.REL_OBJ_ACTIVITY_SUBJECT, subject)

        # ---------
        act2 = self.get_object_or_fail(Activity, title=title2)
        self.assertRelationCount(1, act2, constants.REL_OBJ_PART_2_ACTIVITY, user_contact)
        self.assertRelationCount(1, act2, constants.REL_OBJ_PART_2_ACTIVITY, other_contact)
        self.assertRelationCount(1, act2, constants.REL_OBJ_PART_2_ACTIVITY, participant2)

        # ---------
        act3 = self.get_object_or_fail(Activity, title=title3)
        self.assertFalse(Contact.objects.filter(last_name=unfoundable).exists())  # Not created

        results = self._get_job_results(job)
        self.assertEqual(len(lines), len(results))

        jr_errors = [r for r in results if r.messages]
        self.assertEqual(1, len(jr_errors))

        jr_error = jr_errors[0]
        self.assertEqual([_(u'The participant «{}» is unfoundable').format(unfoundable)],
                         jr_error.messages
                        )
        self.assertEqual(act3, jr_error.entity.get_real_entity())

        # ---------
        act4 = self.get_object_or_fail(Activity, title=title4)
        self.assertRelationCount(1, act4, constants.REL_OBJ_PART_2_ACTIVITY, user_contact)  # Not 2

    @skipIfCustomContact
    def test_import03(self):
        "Dynamic participants with cell splitting & pattern '$last_name $first_name'."
        user = self.login()

        other_user = self.other_user
        other_contact = other_user.linked_contact

        create_contact = partial(Contact.objects.create, user=user)
        participant1 = create_contact(first_name='Tatsumi', last_name='Oga')
        participant2 = create_contact(first_name='Aoi',     last_name='Kunieda')
        participant3 = create_contact(first_name='Kaiser',
                                      last_name='de Emperana Beelzebub',  # Spaces in last name
                                     )

        unfoundable  = 'Behemoth'
        unfoundable2 = u"En'Ô"
        self.assertFalse(Contact.objects.filter(last_name__in=(unfoundable, unfoundable2)).exists())

        title1 = 'Meeting#1'
        title2 = 'Meeting#2'
        title3 = 'Meeting#3'
        title4 = 'Meeting#4'
        title5 = 'Meeting#5'
        lines = [(title1, u'{} {}/{} {}'.format(participant1.last_name, participant1.first_name,
                                                participant2.last_name, participant2.first_name,
                                               )
                 ),
                 (title2, u'{} {}'.format(other_contact.last_name,
                                          other_contact.first_name,
                                         )
                 ),
                 (title3, u' {} {} '.format(participant2.last_name, participant2.first_name)),  # Trailing spaces
                 (title4, u'{} {}/{} {}/{}/'.format(unfoundable,            unfoundable,
                                                    participant2.last_name, participant2.first_name,
                                                    unfoundable2,
                                                   )
                 ),
                 (title5, u'{} {}/{}'.format(participant3.last_name, participant3.first_name,
                                             participant2.last_name,
                                            )
                 ),
                ]

        doc = self._build_csv_doc(lines)
        response = self.client.post(self._build_import_url(Activity), follow=True,
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=user.id,
                                              type_selector=self._acttype_field_value(constants.ACTIVITYTYPE_MEETING,
                                                                                      constants.ACTIVITYSUBTYPE_MEETING_NETWORK,
                                                                                     ),

                                              participants_mode='2',  # Search with pattern
                                              participants_separator='/',
                                              participants_pattern=4,  # '$last_name $first_name'
                                              # participants_colselect=2,
                                              participants_pattern_colselect=2,
                                             )
                                   )
        self.assertNoFormError(response)

        job = self._execute_job(response)

        # ---------
        act1 = self.get_object_or_fail(Activity, title=title1)
        self.assertRelationCount(1, act1, constants.REL_OBJ_PART_2_ACTIVITY, participant1)
        self.assertRelationCount(1, act1, constants.REL_OBJ_PART_2_ACTIVITY, participant2)

        # ---------
        act2 = self.get_object_or_fail(Activity, title=title2)
        self.assertRelationCount(0, act2, constants.REL_OBJ_PART_2_ACTIVITY, participant1)

        self.assertRelationCount(1, act2, constants.REL_OBJ_PART_2_ACTIVITY, other_contact)
        self.assertEqual([Calendar.get_user_default_calendar(other_user)],
                         list(act2.calendars.all())
                        )

        # ---------
        act3 = self.get_object_or_fail(Activity, title=title3)
        self.assertRelationCount(0, act3, constants.REL_OBJ_PART_2_ACTIVITY, participant1)
        self.assertRelationCount(1, act3, constants.REL_OBJ_PART_2_ACTIVITY, participant2)

        # ---------
        act4 = self.get_object_or_fail(Activity, title=title4)
        self.assertRelationCount(0, act4, constants.REL_OBJ_PART_2_ACTIVITY, participant1)
        self.assertRelationCount(1, act4, constants.REL_OBJ_PART_2_ACTIVITY, participant2)

        self.assertFalse(Contact.objects.filter(last_name=unfoundable).exists())

        results = self._get_job_results(job)
        self.assertEqual(len(lines), len(results))

        jr_errors = [r for r in results if r.messages]
        self.assertEqual(1, len(jr_errors))

        jr_error = jr_errors[0]
        err_fmt = _(u'The participant «{}» is unfoundable').format
        self.assertEqual([err_fmt('{} {}'.format(unfoundable, unfoundable)),
                          err_fmt(unfoundable2),
                         ],
                         jr_error.messages
                        )

        # ---------
        act5 = self.get_object_or_fail(Activity, title=title5)
        self.assertRelationCount(1, act5, constants.REL_OBJ_PART_2_ACTIVITY, participant3)
        self.assertRelationCount(1, act5, constants.REL_OBJ_PART_2_ACTIVITY, participant2)

    @skipIfCustomContact
    def test_import04(self):
        "Another cell splitting type: pattern '$civility $first_name $last_name'."
        user = self.login()

        miss = self.get_object_or_fail(Civility, pk=2)
        aoi = Contact.objects.create(user=user, first_name='Aoi', last_name='Kunieda', civility=miss)

        title1 = 'Meeting#1'
        lines = [(title1, ' {} {} {} '.format(aoi.civility, aoi.first_name, aoi.last_name))]  # +trailing spaces

        doc = self._build_csv_doc(lines)
        url = self._build_import_url(Activity)
        data = dict(self.lv_import_data,
                    document=doc.id,
                    user=user.id,
                    type_selector=self._acttype_field_value(constants.ACTIVITYTYPE_MEETING,
                                                            constants.ACTIVITYSUBTYPE_MEETING_NETWORK,
                                                           ),

                    participants_mode=2,  # Search with pattern
                    participants_separator='/',
                    participants_pattern=1,  # $civility $first_name $last_name
                    # participants_colselect=2,
                    participants_pattern_colselect=2,
                   )

        response = self.client.post(url, data=dict(data, participants_pattern=5))  # Invalid pattern
        self.assertFormError(response, 'form', 'participants', 'Invalid pattern')

        # ----------
        response = self.client.post(url, follow=True, data=data)
        self.assertNoFormError(response)

        self._execute_job(response)

        act1 = self.get_object_or_fail(Activity, title=title1)
        self.assertRelationCount(1, act1, constants.REL_OBJ_PART_2_ACTIVITY, aoi)

    @skipIfCustomOrganisation
    def test_import05(self):
        "Dynamic participants with search on first_name/last_name + creation"
        user = self.login()

        title = 'Task#1'
        first_name = 'Aoi'
        last_name = 'Kunieda'

        orga = Organisation.objects.create(user=self.user, name=last_name)  # Should not be used as subject

        doc = self._build_csv_doc([(title, first_name, last_name)])
        response = self.client.post(self._build_import_url(Activity), follow=True,
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=user.id,
                                              type_selector=self._acttype_field_value(constants.ACTIVITYTYPE_TASK),

                                              participants_mode=1,  # Search with 1 or 2 columns
                                              participants_first_name_colselect=2,
                                              participants_last_name_colselect=3,
                                              participants_create=True,
                                             )
                                   )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self._assertNoResultError(self._get_job_results(job))

        task = self.get_object_or_fail(Activity, title=title)
        aoi = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertRelationCount(1, task, constants.REL_OBJ_PART_2_ACTIVITY, aoi)
        self.assertRelationCount(0, task, constants.REL_OBJ_ACTIVITY_SUBJECT, orga)

    @skipIfCustomContact
    def test_import06(self):
        "Dynamic participants with cell splitting + creation"
        user = self.login()

        aoi = Contact.objects.create(user=user, first_name='Aoi', last_name='Kunieda')

        title = 'Task#1'
        first_name = 'Tatsumi'
        last_name = 'Oga'
        doc = self._build_csv_doc([(title, '{} {}#{} {}'.format(first_name,     last_name,
                                                                aoi.first_name, aoi.last_name,
                                                               )
                                   )
                                  ]
                                 )
        response = self.client.post(self._build_import_url(Activity), follow=True,
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=user.id,
                                              type_selector=self._acttype_field_value(constants.ACTIVITYTYPE_TASK),

                                              participants_mode=2,  # Search with pattern
                                              participants_separator='#',
                                              participants_pattern=3,  # '$first_name $last_name'
                                              # participants_colselect=2,
                                              participants_pattern_colselect=2,
                                              participants_create=True,
                                             )
                                   )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self._assertNoResultError(self._get_job_results(job))

        task = self.get_object_or_fail(Activity, title=title)
        self.assertRelationCount(1, task, constants.REL_OBJ_PART_2_ACTIVITY, aoi)

        oga = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertRelationCount(1, task, constants.REL_OBJ_PART_2_ACTIVITY, oga)

    def test_import07(self):
        "Search on first_name/last_name + not creation credentials"
        self.login(is_superuser=False, allowed_apps=('activities', 'persons', 'documents'), 
                   creatable_models=[Activity, Document],  # Not Contact
                  )
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW | EntityCredentials.LINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        title = 'Task#1'
        first_name = 'Aoi'
        last_name = 'Kunieda'
        doc = self._build_csv_doc([(title, first_name, last_name)])
        response = self.client.post(self._build_import_url(Activity), follow=True,
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=self.user.id,
                                              type_selector=self._acttype_field_value(constants.ACTIVITYTYPE_TASK),

                                              participants_mode=1,  # Search with 1 or 2 columns
                                              participants_first_name_colselect=2,
                                              participants_last_name_colselect=3,
                                              participants_create=True,  # Not used
                                             )
                                   )
        self.assertNoFormError(response)

        self._execute_job(response)
        self.get_object_or_fail(Activity, title=title)
        self.assertFalse(Contact.objects.filter(first_name=first_name, last_name=last_name))

    def test_import08(self):
        "Property creation (regular post creation handler should be called)"
        user = self.login()

        ptype = CremePropertyType.create(str_pk='test-prop_imported', text='Has been imported')

        title = 'Task#1'
        doc = self._build_csv_doc([(title, 'Aoi', 'Kunieda')])
        response = self.client.post(self._build_import_url(Activity), follow=True,
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=user.id,
                                              type_selector=self._acttype_field_value(constants.ACTIVITYTYPE_TASK),

                                              property_types=[ptype.id],
                                             )
                                   )
        self.assertNoFormError(response)

        self._execute_job(response)
        act = self.get_object_or_fail(Activity, title=title)
        self.get_object_or_fail(CremeProperty, type=ptype, creme_entity=act.id)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_import_subjects01(self):
        """Subject: Contact is searched if Organisation is not found.
        No creation asked.
        """
        user = self.login()

        title1 = 'Task#1'; title2 = 'Task#2'; title3 = 'Task#3'
        title4 = 'Task#4'; title5 = 'Task#5'; title6 = 'Task#6'

        create_contact = partial(Contact.objects.create, user=user)
        aoi    = create_contact(first_name='Aoi', last_name='Kunieda')
        furyo1 = create_contact(last_name='Furyo')
        furyo2 = create_contact(last_name='Furyo')

        name = 'Ishiyama'

        create_orga = partial(Organisation.objects.create, user=user)
        clan1 = create_orga(name='Clan')
        clan2 = create_orga(name='Clan')

        doc = self._build_csv_doc([(title1, unicode(aoi)),
                                   (title2, (u' {} '.format(aoi)).upper()),
                                   (title3, u' {} '.format(name)),
                                   (title4, clan1.name),
                                   (title5, furyo1.last_name),
                                   (title6, u'{}/{}'.format(aoi, clan1.name)),
                                  ]
                                 )
        response = self.client.post(self._build_import_url(Activity), follow=True,
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=user.id,
                                              type_selector=self._acttype_field_value(constants.ACTIVITYTYPE_TASK),

                                              subjects_colselect=2,
                                              subjects_separator='/',
                                             )
                                   )
        self.assertNoFormError(response)

        job = self._execute_job(response)

        task1 = self.get_object_or_fail(Activity, title=title1)
        self.assertRelationCount(1, task1, constants.REL_OBJ_ACTIVITY_SUBJECT, aoi)

        task2 = self.get_object_or_fail(Activity, title=title2)
        self.assertRelationCount(1, task2, constants.REL_OBJ_ACTIVITY_SUBJECT, aoi)

        task3 = self.get_object_or_fail(Activity, title=title3)
        self.assertRelationCount(0, task3, constants.REL_OBJ_ACTIVITY_SUBJECT, aoi)
        self.assertFalse(Organisation.objects.filter(name__icontains=name))

        task4 = self.get_object_or_fail(Activity, title=title4)
        self.assertRelationCount(1, task4, constants.REL_OBJ_ACTIVITY_SUBJECT, clan1)
        self.assertRelationCount(1, task4, constants.REL_OBJ_ACTIVITY_SUBJECT, clan2)

        task5 = self.get_object_or_fail(Activity, title=title5)
        self.assertRelationCount(1, task5, constants.REL_OBJ_ACTIVITY_SUBJECT, furyo1)
        self.assertRelationCount(1, task5, constants.REL_OBJ_ACTIVITY_SUBJECT, furyo2)

        task6 = self.get_object_or_fail(Activity, title=title6)
        self.assertRelationCount(1, task6, constants.REL_OBJ_ACTIVITY_SUBJECT, aoi)
        self.assertRelationCount(1, task6, constants.REL_OBJ_ACTIVITY_SUBJECT, clan1)
        self.assertRelationCount(1, task6, constants.REL_OBJ_ACTIVITY_SUBJECT, clan2)

        job = self._execute_job(response)
        results = self._get_job_results(job)
        jr_errors = [r for r in results if r.messages]
        self.assertEqual(4, len(jr_errors))

        jr_error = jr_errors[0]
        self.assertEqual(task3, jr_error.entity.get_real_entity())
        self.assertEqual([_(u'The subject «{}» is unfoundable').format(name)],
                         jr_error.messages
                        )

        err_fmt = _(u'Several «{models}» were found for the search «{search}»').format
        jr_error = jr_errors[1]
        self.assertEqual(task4, jr_error.entity.get_real_entity())
        self.assertEqual([err_fmt(models=_('Organisations'),
                                  search=clan1.name,
                                 ),
                         ],
                         jr_error.messages
                        )

        jr_error = jr_errors[2]
        self.assertEqual(task5, jr_error.entity.get_real_entity())
        self.assertEqual([err_fmt(models=_('Contacts'),
                                  search=furyo1.last_name,
                                 ),
                         ],
                         jr_error.messages
                        )

        jr_error = jr_errors[3]
        self.assertEqual(task6, jr_error.entity.get_real_entity())
        self.assertEqual([err_fmt(models=_('Organisations'),
                                  search=clan1.name,
                                 ),
                         ],
                         jr_error.messages
                        )

    def test_import_subjects02(self):
        "Subject: creation."
        user = self.login()

        title = 'My task'
        name = 'Ishiyama'

        doc = self._build_csv_doc([(title, u' {} '.format(name))])
        response = self.client.post(self._build_import_url(Activity), follow=True,
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=user.id,
                                              type_selector=self._acttype_field_value(constants.ACTIVITYTYPE_TASK),

                                              subjects_colselect=2,
                                              subjects_create=True,
                                             )
                                   )
        self.assertNoFormError(response)

        self._execute_job(response)
        task = self.get_object_or_fail(Activity, title=title)
        orga = self.get_object_or_fail(Organisation, name=name)
        self.assertRelationCount(1, task, constants.REL_OBJ_ACTIVITY_SUBJECT, orga)

    def test_import_subjects03(self):
        "Subject: creation credentials."
        self.login(is_superuser=False, allowed_apps=('activities', 'persons', 'documents'), 
                   creatable_models=[Activity, Document],  # Not Organisation
                  )
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW | EntityCredentials.LINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        title = 'Task#1'
        name = 'Ishiyama'
        doc = self._build_csv_doc([(title, u' {} '.format(name))])
        response = self.client.post(self._build_import_url(Activity), follow=True,
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=self.user.id,
                                              type_selector=self._acttype_field_value(constants.ACTIVITYTYPE_TASK),

                                              subjects_colselect=2,
                                              subjects_create=True,  # Should not be used
                                             )
                                   )
        self.assertNoFormError(response)

        self._execute_job(response)
        self.get_object_or_fail(Activity, title=title)
        self.assertFalse(Organisation.objects.filter(name__icontains=name))

    @skipIfCustomOrganisation
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
        response = self.client.post(self._build_import_url(Activity), follow=True,
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=self.user.id,
                                              type_selector=self._acttype_field_value(constants.ACTIVITYTYPE_TASK),

                                              subjects_colselect=2,
                                             )
                                   )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self._assertNoResultError(self._get_job_results(job))

        task = self.get_object_or_fail(Activity, title=title)
        self.assertRelationCount(1, task, constants.REL_OBJ_ACTIVITY_SUBJECT, orga1)
        self.assertRelationCount(0, task, constants.REL_OBJ_ACTIVITY_SUBJECT, orga2)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_import_with_update(self):
        "No duplicated Subjects/participants"
        user = self.login()

        create_contact = partial(Contact.objects.create, user=user)
        participant1 = create_contact(first_name='Tatsumi', last_name='Oga')
        participant2 = create_contact(first_name='Aoi',     last_name='Kunieda')

        subject = Organisation.objects.create(user=user, name='Ishiyama')

        create_act = partial(Activity.objects.create, user=user,
                             type_id=constants.ACTIVITYTYPE_MEETING,
                             sub_type_id=constants.ACTIVITYSUBTYPE_MEETING_NETWORK,
                            )
        act1 = create_act(title='Fight against demons#1')
        act2 = create_act(title='Fight against demons#2')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=act1, type_id=constants.REL_OBJ_PART_2_ACTIVITY,  object_entity=participant1)
        create_rel(subject_entity=act2, type_id=constants.REL_OBJ_ACTIVITY_SUBJECT, object_entity=subject)

        place = 'Hell'
        lines = [(act1.title, participant1.first_name, participant1.last_name, subject.name, place),
                 (act2.title, '',                      participant2.last_name, subject.name, ''),
                ]

        doc = self._build_csv_doc(lines)
        response = self.client.post(self._build_import_url(Activity), follow=True,
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=user.id,
                                              key_fields=['title'],

                                              type_selector=self._acttype_field_value(constants.ACTIVITYTYPE_MEETING,
                                                                                      constants.ACTIVITYSUBTYPE_MEETING_NETWORK,
                                                                                     ),

                                              participants_mode=1,  # Search with 1 or 2 columns
                                              participants_first_name_colselect=2,
                                              participants_last_name_colselect=3,

                                              subjects_colselect=4,

                                              place_colselect=5,
                                             )
                                   )
        self.assertNoFormError(response)

        self._execute_job(response)
        act1 = self.refresh(act1)
        self.assertEqual(place, act1.place)

        self.assertRelationCount(1, act1, constants.REL_OBJ_PART_2_ACTIVITY, participant1)  # <- not 2
        self.assertRelationCount(0, act1, constants.REL_OBJ_PART_2_ACTIVITY, participant2)
        self.assertRelationCount(1, act1, constants.REL_OBJ_ACTIVITY_SUBJECT, subject)

        act2 = self.refresh(act2)
        self.assertRelationCount(1, act2, constants.REL_OBJ_PART_2_ACTIVITY, participant2)
        self.assertRelationCount(1, act2, constants.REL_OBJ_ACTIVITY_SUBJECT, subject)  # <- not 2

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

    @skipIfCustomContact
    def test_participants_multicol_extractor01(self):
        self.login()
        user = self.user

        # -----
        ext = MultiColumnsParticipantsExtractor(1, 2)

        first_name = 'Aoi'
        last_name = 'Kunieda'
        contacts, err_msg = ext.extract_value([first_name, last_name], user)
        self.assertEqual((), contacts)
        self.assertEqual(tuple([_(u'The participant «{}» is unfoundable').format(
                                        _('{first_name} {last_name}').format(
                                            first_name=first_name,
                                            last_name=last_name,
                                        ),
                                    ),
                         ]),
                         err_msg
                        )

        create_contact = partial(Contact.objects.create, user=user, last_name=last_name)
        aoi = create_contact(first_name=first_name)
        contacts, err_msg = ext.extract_value([first_name, last_name], user)
        self.assertEqual([aoi], list(contacts))
        self.assertFalse(err_msg)

        # -----
        ext = MultiColumnsParticipantsExtractor(0, 1)
        contacts, err_msg = ext.extract_value([last_name], user)
        self.assertEqual([aoi], list(contacts))
        self.assertEqual((), err_msg)

        ittosai = create_contact(first_name=u'Ittôsai')
        contacts, err_msg = ext.extract_value([last_name], user)
        self.assertEqual({aoi, ittosai}, set(contacts))
        self.assertEqual((_(u'Several contacts were found for the search «{}»').format(last_name),),
                         err_msg
                        )

        create_contact(first_name='Shinobu')
        create_contact(first_name=u'Kôta')
        create_contact(first_name='')
        create_contact(first_name='Tatsumi')
        contacts, err_msg = ext.extract_value([last_name], user)
        self.assertFalse(contacts)
        self.assertEqual(tuple([_(u'Too many contacts were found for the search «{}»').format(last_name)]),
                         err_msg
                        )

    @skipIfCustomContact
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

    @skipIfCustomContact
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
        self.assertEqual((_(u'The participant «{}» is unfoundable').format(last_name),),
                         err_msg
                        )

        create_contact = partial(Contact.objects.create, last_name=last_name)
        create_contact(user=self.other_user, first_name=u'Ittôsai')

        contacts, err_msg = extract()
        self.assertFalse(contacts)
        self.assertEqual((_(u'No linkable contact found for the search «{}»').format(last_name),),
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

    @skipIfCustomContact
    def test_participants_singlecol_extractor01(self):
        "SplittedColumnParticipantsExtractor"
        self.login()
        user = self.user
        ext = SplitColumnParticipantsExtractor(1, '#', _pattern_FL)

        create_contact = partial(Contact.objects.create, user=user, last_name='Kunieda')
        searched = 'Aoi Kunieda'
        contacts, err_msg = ext.extract_value([searched], user)
        self.assertFalse(contacts)
        self.assertEqual([_(u'The participant «{}» is unfoundable').format(searched)],
                         err_msg
                        )

        aoi = create_contact(first_name='Aoi')
        oga = create_contact(first_name='Tatsumi', last_name='Oga')
        contacts, err_msg = ext.extract_value(['Aoi Kunieda#Tatsumi Oga'], user)
        self.assertEqual({aoi, oga}, set(contacts))
        self.assertFalse(err_msg)

        contacts, err_msg = ext.extract_value(['Aoi Kunieda#Tatsumi Oga#'], user)
        self.assertEqual({aoi, oga}, set(contacts))

        # -------
        searched = 'Kunieda'
        ittosai = create_contact(first_name=u'Ittôsai')
        contacts, err_msg = ext.extract_value([searched], user)
        self.assertEqual({aoi, ittosai}, set(contacts))
        self.assertEqual([_(u'Several contacts were found for the search «{}»').format(searched)],
                         err_msg
                        )

        create_contact(first_name='Shinobu')
        create_contact(first_name=u'Kôta')
        create_contact(first_name='')
        create_contact(first_name='Tatsumi')
        contacts, err_msg = ext.extract_value([searched], user)
        self.assertFalse(contacts)
        self.assertEqual([_(u'Too many contacts were found for the search «{}»').format(searched)],
                         err_msg
                        )

    @skipIfCustomContact
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

        ext = SplitColumnParticipantsExtractor(1, '#', _pattern_FL)
        contacts, err_msg = ext.extract_value(['Kunieda'], user)
        self.assertEqual([aoi], contacts)
        self.assertFalse(err_msg)

    @skipIfCustomContact
    def test_participants_singlecol_extractor03(self):
        "Creation if not found + civility"
        self.login()
        user = self.user

        ext = SplitColumnParticipantsExtractor(1, '#', _pattern_CFL, create_if_unfound=True)

        first_name = 'Aoi'
        last_name = 'Kunieda'
        contacts, err_msg = ext.extract_value(['{} {}'.format(first_name, last_name)], user)
        self.assertFalse(err_msg)
        aoi = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertIsNone(aoi.civility)

        first_name = u'Ittôsai'
        contacts, err_msg = ext.extract_value([u'Sensei {} {}'.format(first_name, last_name)], user)
        self.assertFalse(err_msg)
        ittosai = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertIsNone(ittosai.civility)

        # Civility retrieved by title
        mister = self.get_object_or_fail(Civility, pk=3)
        first_name = 'Tatsumi'
        last_name = 'Oga'
        contacts, err_msg = ext.extract_value([u'{} {} {}'.format(mister.title, first_name, last_name)], user)
        self.assertFalse(err_msg)
        oga = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertEqual(mister, oga.civility)

        # Civility is not used to search
        contacts, err_msg = ext.extract_value([u'Sensei {} {}'.format(first_name, last_name)], user)
        self.assertEqual([oga], contacts)
        self.assertEqual(mister, self.refresh(oga).civility)

        # Civility retrieved by short name
        first_name = 'Takayuki'
        last_name = 'Furuichi'
        ext.extract_value([u'{} {} {}'.format(mister.shortcut, first_name, last_name)], user)
        furuichi = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertEqual(mister, furuichi.civility)

    @skipIfCustomContact
    def test_subjects_extractor01(self):
        "Link credentials."
        user = self.login(is_superuser=False, allowed_apps=('activities', 'persons', 'documents'),
                          creatable_models=[Activity, Document],
                         )
        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(value=EntityCredentials.VIEW | EntityCredentials.LINK,
                  set_type=SetCredentials.ESET_OWN,
                 )
        create_sc(value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)

        ext = SubjectsExtractor(1, '/')
        last_name = 'Kunieda'

        def extract():
            return ext.extract_value([last_name], user)

        contacts, err_msg = extract()
        self.assertFalse(contacts)
        self.assertEqual([_(u'The subject «{}» is unfoundable').format(last_name)],
                         err_msg
                        )

        create_contact = partial(Contact.objects.create, last_name=last_name)
        create_contact(user=self.other_user, first_name=u'Ittôsai')

        contacts, err_msg = extract()
        self.assertFalse(contacts)
        self.assertEqual([_(u'No linkable entity found for the search «{}»').format(last_name)],
                         err_msg
                        )

        aoi = create_contact(user=user, first_name='Aoi')
        contacts, err_msg = extract()
        self.assertEqual([aoi], contacts)
        self.assertFalse(err_msg)

    @skipIfCustomContact
    def test_subjects_extractor02(self):
        "Limit"
        user = self.login()
        ext = SubjectsExtractor(1, '#')

        last_name = 'Kunieda'

        create_contact = partial(Contact.objects.create, user=user, last_name=last_name)
        create_contact(first_name='Aoi')
        create_contact(first_name=u'Ittôsai')
        create_contact(first_name='Shinobu')
        create_contact(first_name=u'Kôta')
        create_contact(first_name='')
        create_contact(first_name='Tatsumi')

        contacts, err_msg = ext.extract_value([' {} #'.format(last_name)], user)
        self.assertFalse(contacts)
        self.assertEqual([_(u'Too many «{models}» were found for the search «{search}»').format(
                                models=_('Contacts'),
                                search=last_name,
                            )
                         ],
                         err_msg
                        )

    @skipIfNotInstalled('creme.tickets')
    def test_subjects_extractor03(self):
        "Other ContentType"
        from creme.tickets.models import Ticket, Priority, Criticity

        rtype = self.get_object_or_fail(RelationType, pk=constants.REL_OBJ_ACTIVITY_SUBJECT)
        self.assertIn(Ticket, (ct.model_class() for ct in rtype.object_ctypes.all()))

        user = self.login()
        last_name = 'Kunieda'
        ticket = Ticket.objects.create(user=user, title="{}'s ticket".format(last_name),
                                       priority=Priority.objects.all()[0],
                                       criticity=Criticity.objects.all()[0],
                                      )

        ext = SubjectsExtractor(1, '/')
        extracted, err_msg = ext.extract_value([last_name], user)
        self.assertEqual([ticket], extracted)
        self.assertFalse(err_msg)
