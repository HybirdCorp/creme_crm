from functools import partial

from django.utils.translation import gettext as _

from creme.activities import constants
from creme.activities.models import Calendar
from creme.creme_core.models import CremePropertyType, Relation
from creme.creme_core.tests.views.base import MassImportBaseTestCaseMixin
from creme.documents import get_document_model
from creme.documents.tests.base import skipIfCustomDocument
from creme.persons.models import Civility
from creme.persons.populate import UUID_CIVILITY_MISS
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from ..base import (
    Activity,
    Contact,
    Organisation,
    _ActivitiesTestCase,
    skipIfCustomActivity,
)

Document = get_document_model()


@skipIfCustomDocument
@skipIfCustomActivity
class MassImportActivityTestCase(MassImportBaseTestCaseMixin, _ActivitiesTestCase):
    lv_import_data = {
        'step': 1,
        'title_colselect': 1,

        'start_colselect': 0,
        'end_colselect':   0,

        'status_colselect':      0,
        'description_colselect': 0,
        'place_colselect':       0,
        'duration_colselect':    0,
        'is_all_day_colselect':  0,
        'minutes_colselect':     0,
    }

    def test_basic(self):
        user = self.login_as_root_and_get()

        url = self._build_import_url(Activity)
        self.assertGET200(url)

        title1 = 'Task#1'
        title2 = 'Task#2'
        title3 = 'Task#3'
        title4 = 'Task#4'
        title5 = 'Task#5'
        title6 = 'Task#6'
        title7 = 'Task#7'

        date_value = self.formfield_value_date
        dt_value = self.formfield_value_datetime
        lines = [
            (title1, '', ''),
            (
                title2,
                dt_value(year=2014, month=5, day=28, hour=15),
                dt_value(year=2014, month=5, day=28, hour=17),
            ),

            # Start > end !!
            (
                title3,
                dt_value(year=2014, month=5, day=28, hour=19),
                dt_value(year=2014, month=5, day=28, hour=18),
            ),

            # No end
            (title4, dt_value(year=2014, month=5, day=29, hour=12), ''),

            # FLOATING_TIME
            (title5, date_value(2014, 5, 30), ''),

            # FLOATING_TIME too
            (title6, date_value(2014, 6, 1), date_value(2014, 6, 1)),

            # Not FLOATING_TIME
            (title7, date_value(2014, 6, 2), dt_value(year=2014, month=6, day=2, hour=18)),
        ]

        doc = self._build_csv_doc(lines, user=user)
        response = self.client.post(
            url,
            data={
                'step':     0,
                'document': doc.id,
            },
        )
        self.assertNoFormError(response)

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER)
        response = self.client.post(
            url, follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'start_colselect': 2,
                'end_colselect': 3,
                'type_selector': sub_type.id,

                # Should not be used
                'busy_colselect': 0,
                'busy_defval': True,
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)

        results = self._get_job_results(job)
        self.assertEqual(len(lines), len(results))

        act1 = self.get_object_or_fail(Activity, title=title1)
        self.assertEqual(sub_type.type_id, act1.type_id)
        self.assertEqual(sub_type.id,      act1.sub_type_id)
        self.assertIsNone(act1.start)
        self.assertIsNone(act1.end)
        self.assertEqual(Activity.FloatingType.FLOATING, act1.floating_type)

        self.assertFalse(act1.relations.all())

        act2 = self.get_object_or_fail(Activity, title=title2)
        self.assertFalse(act2.busy)

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2014, month=5, day=28, hour=15), act2.start)
        self.assertEqual(create_dt(year=2014, month=5, day=28, hour=17), act2.end)
        self.assertEqual(Activity.FloatingType.NARROW, act2.floating_type)

        act3 = self.get_object_or_fail(Activity, title=title3)
        self.assertEqual(
            create_dt(year=2014, month=5, day=28, hour=19, minute=0),
            act3.start,
        )
        self.assertEqual(
            create_dt(year=2014, month=5, day=28, hour=19, minute=15),
            act3.end,
        )
        self.assertEqual(Activity.FloatingType.NARROW, act3.floating_type)

        act4 = self.get_object_or_fail(Activity, title=title4)
        self.assertEqual(
            create_dt(year=2014, month=5, day=29, hour=12, minute=0),
            act4.start,
        )
        self.assertEqual(
            create_dt(year=2014, month=5, day=29, hour=12, minute=15),
            act4.end,
        )
        self.assertEqual(Activity.FloatingType.NARROW, act4.floating_type)

        act5 = self.get_object_or_fail(Activity, title=title5)
        self.assertEqual(
            create_dt(year=2014, month=5, day=30, hour=0, minute=0),
            act5.start,
        )
        self.assertEqual(
            create_dt(year=2014, month=5, day=30, hour=23, minute=59),
            act5.end,
        )
        self.assertEqual(Activity.FloatingType.FLOATING_TIME, act5.floating_type)

        act6 = self.get_object_or_fail(Activity, title=title6)
        self.assertEqual(
            create_dt(year=2014, month=6, day=1, hour=0, minute=0),
            act6.start,
        )
        self.assertEqual(
            create_dt(year=2014, month=6, day=1, hour=23, minute=59),
            act6.end,
        )
        self.assertEqual(Activity.FloatingType.FLOATING_TIME, act6.floating_type)

        act7 = self.get_object_or_fail(Activity, title=title7)
        self.assertEqual(
            create_dt(year=2014, month=6, day=2, hour=0, minute=0),
            act7.start,
        )
        self.assertEqual(
            create_dt(year=2014, month=6, day=2, hour=18, minute=00),
            act7.end,
        )
        self.assertEqual(Activity.FloatingType.NARROW, act7.floating_type)

        jr_error = self.get_alone_element(r for r in results if r.messages)
        self.assertListEqual(
            [_('End time is before start time')],
            jr_error.messages,
        )
        self.assertEqual(act3, jr_error.entity.get_real_entity())

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_participants_n_subjects(self):
        """Static user participants (+ calendars), dynamic participants with
        search on first_name/last_name.
        Dynamic subjects without creation.
        """
        user = self.login_as_root_and_get()
        user_contact = user.linked_contact

        other_user = self.create_user()
        other_contact = other_user.linked_contact

        create_contact = partial(Contact.objects.create, user=user)
        participant1 = create_contact(first_name='Tatsumi', last_name='Oga')
        participant2 = create_contact(first_name='Aoi',     last_name='Kunieda')

        furuichi = self.create_user(
            username='furuichi', first_name='Furuichi',
            last_name='Takayuki', email='furuichi@ishiyama.jp',
        )
        chiaki = self.create_user(
            username='chiaki', first_name='Chiaki',
            last_name='Tanimura', email='chiaki@ishiyama.jp',
        )

        team = self.create_team('Samurais', furuichi, chiaki)

        unfoundable = 'Behemoth'
        self.assertFalse(Contact.objects.filter(last_name=unfoundable).exists())

        subject = Organisation.objects.create(user=user, name='Ishiyama')

        title1 = 'Meeting#1'
        title2 = 'Meeting#2'
        title3 = 'Meeting#3'
        title4 = 'Meeting#4'
        lines = [
            (title1, participant1.first_name, participant1.last_name, subject.name),
            (title2, '',                      participant2.last_name, ''),
            # Unfoundable Contact -> error
            (title3, '',                      unfoundable,            ''),
            # No duplicate
            (title4, user_contact.first_name, user_contact.last_name, ''),
        ]

        Calendar.objects.get_default_calendar(user)
        my_calendar = Calendar.objects.create(
            user=user, is_default=False, name='Imported activities',
        )

        doc = self._build_csv_doc(lines, user=user)
        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_NETWORK)
        data = {
            **self.lv_import_data,
            'document': doc.id,
            'user': other_user.id,
            'type_selector': sub_type.id,

            'my_participation_0': True,
            'participating_users': [other_user.id, team.id],

            'participants_mode': 1,  # Search with 1 or 2 columns
            'participants_first_name_colselect': 2,
            'participants_last_name_colselect': 3,

            'subjects_colselect': 4,
        }

        # Validation errors ----------
        response = self.assertPOST200(self._build_import_url(Activity), data=data, follow=True)
        self.assertFormError(
            self.get_form_or_fail(response),
            field='my_participation',
            errors=_('Enter a value if you check the box.'),
        )

        response = self.assertPOST200(
            self._build_import_url(Activity), follow=True,
            data={
                **data,
                'participants_first_name_colselect': 100,  # Invalid choice
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='participants', errors='Invalid index',
        )

        # ---------
        response = self.client.post(
            self._build_import_url(Activity), follow=True,
            data={**data, 'my_participation_1': my_calendar.pk},
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)

        act1 = self.get_object_or_fail(Activity, title=title1)
        self.assertEqual(other_user, act1.user)
        self.assertEqual(sub_type.type_id, act1.type_id)
        self.assertEqual(sub_type.id,      act1.sub_type_id)

        PARTICIPATES = constants.REL_SUB_PART_2_ACTIVITY
        self.assertHaveRelation(subject=user_contact,            type=PARTICIPATES, object=act1)
        self.assertHaveRelation(subject=other_contact,           type=PARTICIPATES, object=act1)
        self.assertHaveRelation(subject=furuichi.linked_contact, type=PARTICIPATES, object=act1)
        self.assertHaveRelation(subject=chiaki.linked_contact,   type=PARTICIPATES, object=act1)

        get_def_calendar = Calendar.objects.get_default_calendar
        self.assertCountEqual(
            [
                my_calendar,
                get_def_calendar(other_user),
                get_def_calendar(furuichi),
                get_def_calendar(chiaki),
                get_def_calendar(team),
            ],
            act1.calendars.all(),
        )

        self.assertHaveRelation(subject=participant1,   type=PARTICIPATES, object=act1)
        self.assertHaveNoRelation(subject=participant2, type=PARTICIPATES, object=act1)

        self.assertHaveRelation(
            subject=subject, type=constants.REL_SUB_ACTIVITY_SUBJECT, object=act1,
        )

        # ---------
        act2 = self.get_object_or_fail(Activity, title=title2)
        self.assertHaveRelation(user_contact,  PARTICIPATES, act2)
        self.assertHaveRelation(other_contact, PARTICIPATES, act2)
        self.assertHaveRelation(participant2,  PARTICIPATES, act2)

        # ---------
        act3 = self.get_object_or_fail(Activity, title=title3)
        self.assertFalse(Contact.objects.filter(last_name=unfoundable).exists())  # Not created

        results = self._get_job_results(job)
        self.assertEqual(len(lines), len(results))

        jr_error = self.get_alone_element(r for r in results if r.messages)
        self.assertEqual(
            [_('The participant «{}» cannot be found').format(unfoundable)],
            jr_error.messages,
        )
        self.assertEqual(act3, jr_error.entity.get_real_entity())

        # ---------
        act4 = self.get_object_or_fail(Activity, title=title4)
        # Not duplicate error
        self.assertHaveRelation(subject=user_contact, type=PARTICIPATES, object=act4)

    @skipIfCustomContact
    def test_participants__last_name_first_name(self):
        "Dynamic participants with cell splitting & pattern '$last_name $first_name'."
        user = self.login_as_root_and_get()

        other_user = self.create_user()
        other_contact = other_user.linked_contact

        create_contact = partial(Contact.objects.create, user=user)
        participant1 = create_contact(first_name='Tatsumi', last_name='Oga')
        participant2 = create_contact(first_name='Aoi',     last_name='Kunieda')
        participant3 = create_contact(
            first_name='Kaiser',
            last_name='de Emperana Beelzebub',  # Spaces in last name
        )

        unfoundable1 = 'Behemoth'
        unfoundable2 = "En'Ô"
        self.assertFalse(
            Contact.objects.filter(last_name__in=(unfoundable1, unfoundable2)).exists()
        )

        title1 = 'Meeting#1'
        title2 = 'Meeting#2'
        title3 = 'Meeting#3'
        title4 = 'Meeting#4'
        title5 = 'Meeting#5'
        lines = [
            (
                title1,
                f'{participant1.last_name} {participant1.first_name}/'
                f'{participant2.last_name} {participant2.first_name}',
            ),
            (title2, f'{other_contact.last_name} {other_contact.first_name}'),
            (title3, f' {participant2.last_name} {participant2.first_name} '),  # Trailing spaces
            (
                title4,
                f'{unfoundable1} {unfoundable1}/'
                f'{participant2.last_name} {participant2.first_name}/'
                f'{unfoundable2}/',
            ),
            (
                title5,
                f'{participant3.last_name} {participant3.first_name}/'
                f'{participant2.last_name}',
            ),
        ]

        doc = self._build_csv_doc(lines, user=user)
        response = self.client.post(
            self._build_import_url(Activity), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'type_selector': self._get_sub_type(constants.UUID_SUBTYPE_MEETING_NETWORK).id,

                'participants_mode': '2',  # Search with pattern
                'participants_separator': '/',
                'participants_pattern': 4,  # '$last_name $first_name'
                'participants_pattern_colselect': 2,
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)

        # ---------
        act1 = self.get_object_or_fail(Activity, title=title1)
        self.assertHaveRelation(act1, constants.REL_OBJ_PART_2_ACTIVITY, participant1)
        self.assertHaveRelation(act1, constants.REL_OBJ_PART_2_ACTIVITY, participant2)

        # ---------
        act2 = self.get_object_or_fail(Activity, title=title2)
        self.assertHaveNoRelation(act2, constants.REL_OBJ_PART_2_ACTIVITY, participant1)

        self.assertHaveRelation(act2, constants.REL_OBJ_PART_2_ACTIVITY, other_contact)
        self.assertListEqual(
            [Calendar.objects.get_default_calendar(other_user)],
            [*act2.calendars.all()],
        )

        # ---------
        act3 = self.get_object_or_fail(Activity, title=title3)
        self.assertHaveNoRelation(act3, constants.REL_OBJ_PART_2_ACTIVITY, participant1)
        self.assertHaveRelation(act3, constants.REL_OBJ_PART_2_ACTIVITY, participant2)

        # ---------
        act4 = self.get_object_or_fail(Activity, title=title4)
        self.assertHaveNoRelation(act4, constants.REL_OBJ_PART_2_ACTIVITY, participant1)
        self.assertHaveRelation(act4, constants.REL_OBJ_PART_2_ACTIVITY, participant2)

        self.assertFalse(Contact.objects.filter(last_name=unfoundable1).exists())

        results = self._get_job_results(job)
        self.assertEqual(len(lines), len(results))

        jr_error = self.get_alone_element(r for r in results if r.messages)
        err_fmt = _('The participant «{}» cannot be found').format
        self.assertListEqual(
            [
                err_fmt(f'{unfoundable1} {unfoundable1}'),
                err_fmt(unfoundable2),
            ],
            jr_error.messages,
        )

        # ---------
        act5 = self.get_object_or_fail(Activity, title=title5)
        self.assertHaveRelation(act5, constants.REL_OBJ_PART_2_ACTIVITY, participant3)
        self.assertHaveRelation(act5, constants.REL_OBJ_PART_2_ACTIVITY, participant2)

    @skipIfCustomContact
    def test_participants__civility(self):
        "Another cell splitting type: pattern '$civility $first_name $last_name'."
        user = self.login_as_root_and_get()

        miss = self.get_object_or_fail(Civility, uuid=UUID_CIVILITY_MISS)
        aoi = Contact.objects.create(
            user=user, first_name='Aoi', last_name='Kunieda', civility=miss,
        )

        title1 = 'Meeting#1'
        # Notice trailing spaces
        lines = [(title1, f' {aoi.civility} {aoi.first_name} {aoi.last_name} ')]

        doc = self._build_csv_doc(lines, user=user)
        url = self._build_import_url(Activity)
        data = {
            **self.lv_import_data,
            'document': doc.id,
            'user': user.id,
            'type_selector': self._get_sub_type(constants.UUID_SUBTYPE_MEETING_NETWORK).id,

            'participants_mode': 2,  # Search with pattern
            'participants_separator': '/',
            'participants_pattern': 1,  # $civility $first_name $last_name
            'participants_pattern_colselect': 2,
        }

        response1 = self.client.post(url, data={**data, 'participants_pattern': 5})
        self.assertFormError(
            response1.context['form'], field='participants', errors='Invalid pattern',
        )

        # ----------
        response2 = self.client.post(url, follow=True, data=data)
        self.assertNoFormError(response2)

        self._execute_job(response2)

        act1 = self.get_object_or_fail(Activity, title=title1)
        self.assertHaveRelation(subject=act1, type=constants.REL_OBJ_PART_2_ACTIVITY, object=aoi)

    @skipIfCustomOrganisation
    def test_participants__search_n_create(self):
        "Dynamic participants with search on first_name/last_name + creation."
        user = self.login_as_root_and_get()

        title = 'Task#1'
        first_name = 'Aoi'
        last_name = 'Kunieda'

        # Should not be used as subject
        orga = Organisation.objects.create(user=user, name=last_name)

        doc = self._build_csv_doc([(title, first_name, last_name)], user=user)
        response = self.client.post(
            self._build_import_url(Activity), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'type_selector': self._get_sub_type(constants.UUID_SUBTYPE_PHONECALL_OUTGOING).id,

                'participants_mode': 1,  # Search with 1 or 2 columns
                'participants_first_name_colselect': 2,
                'participants_last_name_colselect': 3,
                'participants_create': True,
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self._assertNoResultError(self._get_job_results(job))

        task = self.get_object_or_fail(Activity, title=title)
        aoi = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertHaveRelation(
            subject=task, type=constants.REL_OBJ_PART_2_ACTIVITY, object=aoi,
        )
        self.assertHaveNoRelation(
            subject=task, type=constants.REL_OBJ_ACTIVITY_SUBJECT, object=orga,
        )

    @skipIfCustomContact
    def test_participants__split_n_create(self):
        "Dynamic participants with cell splitting + creation."
        user = self.login_as_root_and_get()

        aoi = Contact.objects.create(user=user, first_name='Aoi', last_name='Kunieda')

        title = 'Task#1'
        first_name = 'Tatsumi'
        last_name = 'Oga'
        doc = self._build_csv_doc(
            [(title, f'{first_name} {last_name}#{aoi.first_name} {aoi.last_name}')],
            user=user,
        )
        response = self.client.post(
            self._build_import_url(Activity), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'type_selector': self._get_sub_type(constants.UUID_SUBTYPE_MEETING_MEETING).id,

                'participants_mode': 2,  # Search with pattern
                'participants_separator': '#',
                'participants_pattern': 3,  # '$first_name $last_name'
                'participants_pattern_colselect': 2,
                'participants_create': True,
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self._assertNoResultError(self._get_job_results(job))

        task = self.get_object_or_fail(Activity, title=title)
        self.assertHaveRelation(subject=task, type=constants.REL_OBJ_PART_2_ACTIVITY, object=aoi)

        oga = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertHaveRelation(subject=task, type=constants.REL_OBJ_PART_2_ACTIVITY, object=oga)

    def test_participants__creation_perms(self):
        "Search on first_name/last_name + not creation credentials."
        user = self.login_as_activities_user(
            allowed_apps=('documents',),
            creatable_models=[Activity, Document],  # Not Contact
        )
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        title = 'Task#1'
        first_name = 'Aoi'
        last_name = 'Kunieda'
        doc = self._build_csv_doc([(title, first_name, last_name)], user=user)
        response = self.client.post(
            self._build_import_url(Activity), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'type_selector': self._get_sub_type(
                    constants.UUID_SUBTYPE_PHONECALL_CONFERENCE,
                ).id,

                'participants_mode': 1,  # Search with 1 or 2 columns
                'participants_first_name_colselect': 2,
                'participants_last_name_colselect': 3,
                'participants_create': True,  # Not used
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)
        self.get_object_or_fail(Activity, title=title)
        self.assertFalse(Contact.objects.filter(first_name=first_name, last_name=last_name))

    def test_property(self):
        "Property creation (regular post creation handler should be called)."
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Has been imported')

        title = 'Task#1'
        doc = self._build_csv_doc([(title, 'Aoi', 'Kunieda')], user=user)
        response = self.client.post(
            self._build_import_url(Activity), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'type_selector': self._get_sub_type(
                    constants.UUID_SUBTYPE_MEETING_QUALIFICATION
                ).id,

                'property_types': [ptype.id],
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)
        act = self.get_object_or_fail(Activity, title=title)
        self.assertHasProperty(entity=act, ptype=ptype)

    @skipIfCustomContact
    def test_errors__link_perms(self):
        "Link credentials for user's Contact."
        user = self.login_as_activities_user(
            allowed_apps=('documents',),
            creatable_models=[Activity, Document],
        )
        self.add_credentials(user.role, all=['VIEW', 'LINK'])
        self.add_credentials(user.role, forbidden_all=['LINK'], model=Contact)

        other_user = self.get_root_user()
        my_calendar = Calendar.objects.get_default_calendar(user)
        doc = self._build_csv_doc([('Meeting#1',)], user=user)
        response = self.assertPOST200(
            self._build_import_url(Activity),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'type_selector': self._get_sub_type(constants.UUID_SUBTYPE_MEETING_NETWORK).id,

                'my_participation_0': True,
                'my_participation_1': my_calendar.pk,

                'participating_users': other_user.pk,
            },
        )
        form = self.get_form_or_fail(response)
        self.assertFormError(
            form,
            field='my_participation',
            errors=_('You are not allowed to link this entity: {}').format(user.linked_contact),
        )
        self.assertFormError(
            form,
            field='participating_users',
            errors=_('Some entities are not linkable: {}').format(other_user.linked_contact),
        )

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_subjects__contact_fallback(self):
        """Subject: Contact is searched if Organisation is not found.
        No creation asked.
        """
        user = self.login_as_root_and_get()

        title1 = 'Task#1'
        title2 = 'Task#2'
        title3 = 'Task#3'
        title4 = 'Task#4'
        title5 = 'Task#5'
        title6 = 'Task#6'

        create_contact = partial(Contact.objects.create, user=user)
        aoi    = create_contact(first_name='Aoi', last_name='Kunieda')
        furyo1 = create_contact(last_name='Furyo')
        furyo2 = create_contact(last_name='Furyo')

        name = 'Ishiyama'

        create_orga = partial(Organisation.objects.create, user=user)
        clan1 = create_orga(name='Clan')
        clan2 = create_orga(name='Clan')

        doc = self._build_csv_doc(
            [
                (title1, str(aoi)),
                (title2, f' {aoi} '.upper()),
                (title3, f' {name} '),
                (title4, clan1.name),
                (title5, furyo1.last_name),
                (title6, f'{aoi}/{clan1.name}'),
            ],
            user=user,
        )
        response = self.client.post(
            self._build_import_url(Activity), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'type_selector': self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER).id,

                'subjects_colselect': 2,
                'subjects_separator': '/',
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)

        SUBJECT = constants.REL_SUB_ACTIVITY_SUBJECT
        task1 = self.get_object_or_fail(Activity, title=title1)
        self.assertHaveRelation(subject=aoi, type=SUBJECT, object=task1)

        task2 = self.get_object_or_fail(Activity, title=title2)
        self.assertHaveRelation(subject=aoi, type=SUBJECT, object=task2)

        task3 = self.get_object_or_fail(Activity, title=title3)
        self.assertHaveNoRelation(subject=aoi, type=SUBJECT, object=task3)
        self.assertFalse(Organisation.objects.filter(name__icontains=name))

        task4 = self.get_object_or_fail(Activity, title=title4)
        self.assertHaveRelation(subject=clan1, type=SUBJECT, object=task4)
        self.assertHaveRelation(subject=clan2, type=SUBJECT, object=task4)

        task5 = self.get_object_or_fail(Activity, title=title5)
        self.assertHaveRelation(subject=furyo1, type=SUBJECT, object=task5)
        self.assertHaveRelation(subject=furyo2, type=SUBJECT, object=task5)

        task6 = self.get_object_or_fail(Activity, title=title6)
        self.assertHaveRelation(subject=aoi,   type=SUBJECT, object=task6)
        self.assertHaveRelation(subject=clan1, type=SUBJECT, object=task6)
        self.assertHaveRelation(subject=clan2, type=SUBJECT, object=task6)

        results = self._get_job_results(job)
        jr_errors = [r for r in results if r.messages]
        self.assertEqual(4, len(jr_errors))

        jr_error = jr_errors[0]
        self.assertEqual(task3, jr_error.entity.get_real_entity())
        self.assertListEqual(
            [_('The subject «{}» cannot be found').format(name)],
            jr_error.messages,
        )

        err_fmt = _('Several «{models}» were found for the search «{search}»').format
        jr_error = jr_errors[1]
        self.assertEqual(task4, jr_error.entity.get_real_entity())
        self.assertListEqual(
            [err_fmt(models=_('Organisations'), search=clan1.name)],
            jr_error.messages,
        )

        jr_error = jr_errors[2]
        self.assertEqual(task5, jr_error.entity.get_real_entity())
        self.assertListEqual(
            [err_fmt(models=_('Contacts'), search=furyo1.last_name)],
            jr_error.messages
        )

        jr_error = jr_errors[3]
        self.assertEqual(task6, jr_error.entity.get_real_entity())
        self.assertListEqual(
            [err_fmt(models=_('Organisations'), search=clan1.name)],
            jr_error.messages,
        )

    def test_subjects__creation(self):
        "Subject: creation."
        user = self.login_as_root_and_get()

        title = 'My task'
        name = 'Ishiyama'

        doc = self._build_csv_doc([(title, f' {name} ')], user=user)
        response = self.client.post(
            self._build_import_url(Activity), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'type_selector': self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER).id,

                'subjects_colselect': 2,
                'subjects_create': True,
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)
        task = self.get_object_or_fail(Activity, title=title)
        orga = self.get_object_or_fail(Organisation, name=name)
        self.assertHaveRelation(
            subject=orga, type=constants.REL_SUB_ACTIVITY_SUBJECT, object=task,
        )

    def test_subjects__creation_perms(self):
        "Subject: creation credentials."
        user = self.login_as_activities_user(
            allowed_apps=('documents',),
            creatable_models=[Activity, Document],  # Not Organisation
        )
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        title = 'Task#1'
        name = 'Ishiyama'
        doc = self._build_csv_doc([(title, f' {name} ')], user=user)
        response = self.client.post(
            self._build_import_url(Activity), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'type_selector': self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER).id,

                'subjects_colselect': 2,
                'subjects_create': True,  # Should not be used
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)
        self.get_object_or_fail(Activity, title=title)
        self.assertFalse(Organisation.objects.filter(name__icontains=name))

    @skipIfCustomOrganisation
    def test_subjects__view_perms(self):
        "Subject: view credentials."
        user = self.login_as_activities_user(
            allowed_apps=('documents',), creatable_models=[Activity, Document],
        )
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        title = 'My Task'
        name = 'Ishiyama'

        create_orga = Organisation.objects.create
        orga1 = create_orga(user=user, name=name)
        orga2 = create_orga(user=self.get_root_user(), name=name)

        doc = self._build_csv_doc([(title, name)], user=user)
        response = self.client.post(
            self._build_import_url(Activity), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'type_selector': self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER).id,

                'subjects_colselect': 2,
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self._assertNoResultError(self._get_job_results(job))

        task = self.get_object_or_fail(Activity, title=title)
        SUBJECT = constants.REL_SUB_ACTIVITY_SUBJECT
        self.assertHaveRelation(subject=orga1, type=SUBJECT, object=task)
        self.assertHaveNoRelation(subject=orga2, type=SUBJECT, object=task)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_update_mode(self):
        "No duplicated Subjects/participants."
        user = self.login_as_root_and_get()

        create_contact = partial(Contact.objects.create, user=user)
        participant1 = create_contact(first_name='Tatsumi', last_name='Oga')
        participant2 = create_contact(first_name='Aoi',     last_name='Kunieda')

        subject = Organisation.objects.create(user=user, name='Ishiyama')

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_NETWORK)
        create_act = partial(
            Activity.objects.create,
            user=user,
            type_id=sub_type.type_id, sub_type=sub_type,
        )
        act1 = create_act(title='Fight against demons#1')
        act2 = create_act(title='Fight against demons#2')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(
            subject_entity=act1,
            type_id=constants.REL_OBJ_PART_2_ACTIVITY,
            object_entity=participant1,
        )
        create_rel(
            subject_entity=act2,
            type_id=constants.REL_OBJ_ACTIVITY_SUBJECT,
            object_entity=subject,
        )

        place = 'Hell'
        lines = [
            (act1.title, participant1.first_name, participant1.last_name, subject.name, place),
            (act2.title, '',                      participant2.last_name, subject.name, ''),
        ]

        doc = self._build_csv_doc(lines, user=user)
        response = self.client.post(
            self._build_import_url(Activity), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'key_fields': ['title'],

                'type_selector': self._get_sub_type(constants.UUID_SUBTYPE_MEETING_NETWORK).id,

                'participants_mode': 1,  # Search with 1 or 2 columns
                'participants_first_name_colselect': 2,
                'participants_last_name_colselect': 3,

                'subjects_colselect': 4,

                'place_colselect': 5,
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)
        act1 = self.refresh(act1)
        self.assertEqual(place, act1.place)

        PARTICIPATES = constants.REL_SUB_PART_2_ACTIVITY
        SUBJECT = constants.REL_SUB_ACTIVITY_SUBJECT
        self.assertHaveRelation(subject=participant1, type=PARTICIPATES, object=act1)
        self.assertHaveNoRelation(subject=participant2, type=PARTICIPATES, object=act1)
        self.assertHaveRelation(subject=subject, type=SUBJECT, object=act1)

        act2 = self.refresh(act2)
        self.assertHaveRelation(subject=participant2, type=PARTICIPATES, object=act2)
        self.assertHaveRelation(subject=subject,      type=SUBJECT, object=act2)
