# -*- coding: utf-8 -*-

from datetime import timedelta
from functools import partial

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.forms import ModelMultipleChoiceField
from django.forms.utils import ValidationError
from django.urls import reverse
from django.utils.encoding import force_str  # force_text
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.creme_jobs import trash_cleaner_type
from creme.creme_core.forms import LAYOUT_REGULAR
from creme.creme_core.gui import actions
from creme.creme_core.gui.custom_form import FieldGroup, FieldGroupList
from creme.creme_core.models import (
    CustomFormConfigItem,
    EntityFilter,
    Job,
    Relation,
    RelationType,
    SetCredentials,
    SettingValue,
)
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from .. import constants
from ..actions import BulkExportICalAction
from ..custom_forms import (
    ACTIVITY_CREATION_CFORM,
    UNAVAILABILITY_CREATION_FROM,
)
from ..forms.activity import (
    ActivitySubTypeSubCell,
    MyParticipationSubCell,
    UnavailabilityEndSubCell,
    UnavailabilityStartSubCell,
    UnavailableUsersSubCell,
    UserMessagesSubCell,
)
from ..models import ActivitySubType, ActivityType, Calendar, Status
from ..utils import check_activity_collisions
from .base import (
    Activity,
    Contact,
    Organisation,
    _ActivitiesTestCase,
    skipIfCustomActivity,
)

if apps.is_installed('creme.assistants'):
    from creme.assistants.constants import PRIO_NOT_IMP_PK
    from creme.assistants.models import Alert, UserMessage


@skipIfCustomActivity
class ActivityTestCase(_ActivitiesTestCase):
    ADD_INDISPO_URL = reverse('activities__create_indispo')

    @staticmethod
    def _build_add_related_uri(related, act_type_id=None):
        url = reverse('activities__create_related_activity', args=(related.id,))

        return url if not act_type_id else f'{url}?activity_type={act_type_id}'

    @staticmethod
    def _build_get_types_url(type_id):
        return reverse('activities__get_types', args=(type_id,))

    def _create_phonecall(
            self,
            title='Call01',
            subtype_id=constants.ACTIVITYSUBTYPE_PHONECALL_OUTGOING,
            hour=14):
        create_dt = self.create_datetime
        return Activity.objects.create(
            user=self.user, title=title,
            type_id=constants.ACTIVITYTYPE_PHONECALL, sub_type_id=subtype_id,
            start=create_dt(year=2013, month=4, day=1, hour=hour, minute=0),
            end=create_dt(year=2013,   month=4, day=1, hour=hour, minute=15),
        )

    def _create_task(self, title='Task01', day=1):
        create_dt = self.create_datetime
        return Activity.objects.create(
            user=self.user, title=title,
            type_id=constants.ACTIVITYTYPE_TASK,
            start=create_dt(year=2013, month=4, day=day, hour=8,  minute=0),
            end=create_dt(year=2013,   month=4, day=day, hour=18, minute=0),
        )

    def test_populate(self):
        rtypes_pks = [
            constants.REL_SUB_LINKED_2_ACTIVITY,
            constants.REL_SUB_ACTIVITY_SUBJECT,
            constants.REL_SUB_PART_2_ACTIVITY,
        ]
        self.assertEqual(len(rtypes_pks), RelationType.objects.filter(pk__in=rtypes_pks).count())

        acttypes_pks = [
            constants.ACTIVITYTYPE_TASK,
            constants.ACTIVITYTYPE_MEETING,
            constants.ACTIVITYTYPE_PHONECALL,
            constants.ACTIVITYTYPE_GATHERING,
            constants.ACTIVITYTYPE_SHOW,
            constants.ACTIVITYTYPE_DEMO,
            constants.ACTIVITYTYPE_INDISPO,
        ]
        self.assertEqual(
            len(acttypes_pks),
            ActivityType.objects.filter(pk__in=acttypes_pks).count()
        )

        subtype_ids = [
            constants.ACTIVITYSUBTYPE_PHONECALL_INCOMING,
            constants.ACTIVITYSUBTYPE_PHONECALL_OUTGOING,
            constants.ACTIVITYSUBTYPE_PHONECALL_CONFERENCE,
            constants.ACTIVITYSUBTYPE_MEETING_NETWORK,
            constants.ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
        ]
        self.assertEqual(
            len(subtype_ids),
            ActivitySubType.objects.filter(pk__in=subtype_ids).count()
        )

        # Filters
        self.login()
        acts = [
            self._create_meeting(
                'Meeting01', subtype_id=constants.ACTIVITYSUBTYPE_MEETING_NETWORK, hour=14,
            ),
            self._create_meeting(
                'Meeting02', subtype_id=constants.ACTIVITYSUBTYPE_MEETING_REVIVAL, hour=15,
            ),
            self._create_phonecall(
                'Call01', subtype_id=constants.ACTIVITYSUBTYPE_PHONECALL_OUTGOING, hour=14,
            ),
            self._create_phonecall(
                'Call02', subtype_id=constants.ACTIVITYSUBTYPE_PHONECALL_OUTGOING, hour=15,
            ),
            self._create_task('Task01', day=1),
            self._create_task('Task02', day=2),
        ]

        def check_content(efilter, *expected_titles):
            titles = {*efilter.filter(Activity.objects.all()).values_list('title', flat=True)}

            for activity in acts:
                title = activity.title
                if title in expected_titles:
                    self.assertIn(title, titles)
                else:
                    self.assertNotIn(title, titles)

        efilter = self.get_object_or_fail(EntityFilter, pk=constants.EFILTER_MEETINGS)
        self.assertFalse(efilter.is_custom)
        check_content(efilter, 'Meeting01', 'Meeting02')

        efilter = self.get_object_or_fail(EntityFilter, pk=constants.EFILTER_PHONECALLS)
        check_content(efilter, 'Call01', 'Call02')

        efilter = self.get_object_or_fail(EntityFilter, pk=constants.EFILTER_TASKS)
        check_content(efilter, 'Task01', 'Task02')

        sv = self.get_object_or_fail(SettingValue, key_id=constants.SETTING_DISPLAY_REVIEW)
        self.assertIs(sv.value, True)

        sv = self.get_object_or_fail(SettingValue, key_id=constants.SETTING_AUTO_ORGA_SUBJECTS)
        self.assertIs(sv.value, True)

    def test_get_subtypes(self):
        self.login()
        build_url = self._build_get_types_url
        self.assertGET404(build_url('unknown'))

        # Empty
        response = self.assertGET200(build_url(''))
        self.assertListEqual([], response.json())

        # Valid type
        response = self.assertGET200(build_url(constants.ACTIVITYTYPE_TASK))
        self.assertListEqual(
            [
                *ActivitySubType.objects
                                .filter(type=constants.ACTIVITYTYPE_TASK)
                                .values_list('id', 'name'),
            ],
            response.json(),
        )

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_createview01(self):
        user = self.login()
        other_user = self.other_user

        create_contact = partial(Contact.objects.create, user=user)
        ranma = create_contact(first_name='Ranma', last_name='Saotome')
        genma = create_contact(first_name='Genma', last_name='Saotome')

        dojo = Organisation.objects.create(user=user, name='Dojo')

        def_calendar = Calendar.objects.get_default_calendar(user)
        my_calendar = Calendar.objects.create(
            user=user, name='My main Calendar', is_public=True,
        )

        # GET ---
        url = self.ACTIVITY_CREATION_URL
        lv_url = Activity.get_lv_absolute_url()
        response1 = self.assertGET200(url, HTTP_REFERER='http://testserver' + lv_url)

        context = response1.context
        self.assertEqual(_('Create an activity'), context.get('title'))
        self.assertEqual(_('Save the activity'),  context.get('submit_label'))
        self.assertEqual(lv_url,                  context.get('cancel_url'))

        with self.assertNoException():
            fields = context['form'].fields
            end_f = fields[self.EXTRA_END_KEY]
            my_part_f = fields[self.EXTRA_MYPART_KEY]
            allday_f = fields['is_all_day']

        self.assertEqual(
            _('Default duration of the type will be used if you leave blank.'),
            end_f.help_text,
        )
        self.assertTupleEqual((True, def_calendar.id), my_part_f.initial)
        self.assertFalse(allday_f.help_text)

        # POST ---
        title = 'My task'
        status = Status.objects.all()[0]
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'user':  user.pk,
                'title': title,

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(constants.ACTIVITYTYPE_TASK),
                'status':               status.pk,

                f'{self.EXTRA_START_KEY}_0': '2010-1-10',
                f'{self.EXTRA_START_KEY}_1': '17:30:00',
                f'{self.EXTRA_END_KEY}_0':   '2010-1-10',
                f'{self.EXTRA_END_KEY}_1':   '18:45:00',

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,

                self.EXTRA_OTHERPART_KEY: self.formfield_value_multi_creator_entity(genma),
                self.EXTRA_PARTUSERS_KEY: [other_user.id],
                self.EXTRA_SUBJECTS_KEY:  self.formfield_value_multi_generic_entity(ranma),
                self.EXTRA_LINKED_KEY:    self.formfield_value_multi_generic_entity(dojo),
            },
        )
        self.assertNoFormError(response2)

        act = self.get_object_or_fail(Activity, type=constants.ACTIVITYTYPE_TASK, title=title)
        self.assertIsNone(act.sub_type)
        self.assertEqual(status, act.status)
        self.assertEqual(constants.NARROW, act.floating_type)
        self.assertEqual(
            self.create_datetime(year=2010, month=1, day=10, hour=17, minute=30),
            act.start,
        )
        self.assertEqual(
            self.create_datetime(year=2010, month=1, day=10, hour=18, minute=45),
            act.end,
        )
        self.assertCountEqual(
            [my_calendar, Calendar.objects.get_default_calendar(other_user)],
            [*act.calendars.all()],
        )

        REL_SUB_PART_2_ACTIVITY = constants.REL_SUB_PART_2_ACTIVITY
        self.assertRelationCount(1, user.linked_contact,       REL_SUB_PART_2_ACTIVITY, act)
        self.assertRelationCount(1, genma,                     REL_SUB_PART_2_ACTIVITY, act)
        self.assertRelationCount(1, other_user.linked_contact, REL_SUB_PART_2_ACTIVITY, act)
        self.assertRelationCount(1, ranma, constants.REL_SUB_ACTIVITY_SUBJECT,  act)
        self.assertRelationCount(1, dojo,  constants.REL_SUB_LINKED_2_ACTIVITY, act)

        # * 2: relations have their symmetric ones
        self.assertEqual(5 * 2, Relation.objects.count())

        self.assertRedirects(response2, act.get_absolute_url())
        self.assertTemplateUsed(response2, 'activities/view_activity.html')

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_createview02(self):
        "Credentials errors."
        user = self.login(is_superuser=False)
        self._build_nolink_setcreds()
        self.role.creatable_ctypes.set([ContentType.objects.get_for_model(Activity)])

        other_user = self.other_user

        mireille = user.linked_contact
        mireille.user = other_user
        mireille.save()

        self.assertFalse(user.has_perm_to_link(mireille))

        create_contact = partial(Contact.objects.create, user=other_user)
        genma = create_contact(first_name='Genma', last_name='Saotome')
        akane = create_contact(first_name='Akane', last_name='Tendo')

        dojo = Organisation.objects.create(user=other_user, name='Dojo')

        my_calendar = Calendar.objects.get_default_calendar(user)
        response = self.assertPOST200(
            self.ACTIVITY_CREATION_URL, follow=True,
            data={
                'user':  user.pk,
                'title': 'Fight !!',

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(
                    constants.ACTIVITYTYPE_MEETING,
                    constants.ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                ),

                f'{self.EXTRA_START_KEY}_0': '2011-2-22',

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,

                self.EXTRA_PARTUSERS_KEY: [other_user.pk],
                self.EXTRA_OTHERPART_KEY: self.formfield_value_multi_creator_entity(genma),
                self.EXTRA_SUBJECTS_KEY:  self.formfield_value_multi_generic_entity(akane),
                self.EXTRA_LINKED_KEY:    self.formfield_value_multi_generic_entity(dojo),
            },
        )
        self.assertFormError(
            response, 'form', self.EXTRA_MYPART_KEY,
            _('You are not allowed to link this entity: {}').format(mireille),
        )

        fmt = _('Some entities are not linkable: {}').format
        self.assertFormError(
            response, 'form', self.EXTRA_PARTUSERS_KEY, fmt(other_user.linked_contact),
        )
        self.assertFormError(response, 'form', self.EXTRA_OTHERPART_KEY, fmt(genma))
        self.assertFormError(response, 'form', self.EXTRA_SUBJECTS_KEY,  fmt(akane))
        self.assertFormError(response, 'form', self.EXTRA_LINKED_KEY,    fmt(dojo))

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_createview03(self):
        "No end given ; auto subjects."
        user = self.login()
        me = user.linked_contact

        response1 = self.assertGET200(self.ACTIVITY_CREATION_URL)

        with self.assertNoException():
            subjects_f = response1.context['form'].fields[self.EXTRA_SUBJECTS_KEY]

        self.assertEqual(
            _('The organisations of the participants will be automatically added as subjects'),
            subjects_f.help_text,
        )

        # ---
        create_contact = partial(Contact.objects.create, user=user)
        ranma = create_contact(first_name='Ranma', last_name='Saotome')
        genma = create_contact(first_name='Genma', last_name='Saotome')
        akane = create_contact(first_name='Akane', last_name='Tendo')

        create_orga = partial(Organisation.objects.create, user=user)
        dojo_t = create_orga(name='Tendo Dojo')
        dojo_s = create_orga(name='Saotome Dojo')
        school = create_orga(name='Furinkan High')
        rest   = create_orga(name='Okonomiyaki tenshi')

        mngd = Organisation.objects.filter_managed_by_creme()[0]

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=me,    type_id=REL_SUB_EMPLOYED_BY, object_entity=mngd)
        create_rel(subject_entity=ranma, type_id=REL_SUB_EMPLOYED_BY, object_entity=dojo_s)
        create_rel(subject_entity=akane, type_id=REL_SUB_EMPLOYED_BY, object_entity=school)
        create_rel(subject_entity=akane, type_id=REL_SUB_EMPLOYED_BY, object_entity=dojo_t)
        # 2 employees for the same organisations:
        create_rel(subject_entity=genma, type_id=REL_SUB_MANAGES,     object_entity=school)
        create_rel(subject_entity=genma, type_id=REL_SUB_EMPLOYED_BY, object_entity=rest)

        title = 'My training'
        status = Status.objects.all()[0]
        my_calendar = Calendar.objects.get_default_calendar(user)
        type_id = 'activities-activity_custom_1'
        ActivityType.objects.create(
            pk=type_id, name='Karate session',
            default_day_duration=1,
            default_hour_duration='00:15:00',
            is_custom=True,
        )
        response2 = self.client.post(
            self.ACTIVITY_CREATION_URL,
            follow=True,
            data={
                'user':               user.id,
                'title':              title,
                'status':             status.pk,

                f'{self.EXTRA_START_KEY}_0': '2013-3-26',
                f'{self.EXTRA_START_KEY}_1': '12:10:00',

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,

                self.EXTRA_OTHERPART_KEY: self.formfield_value_multi_creator_entity(genma, akane),
                self.EXTRA_SUBJECTS_KEY:  self.formfield_value_multi_generic_entity(ranma, rest),
                self.EXTRA_LINKED_KEY:    self.formfield_value_multi_generic_entity(dojo_s),

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(type_id),
            },
        )
        self.assertNoFormError(response2)

        act = self.get_object_or_fail(Activity, type=type_id, title=title)
        self.assertEqual(status, act.status)

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2013, month=3, day=26, hour=12, minute=10), act.start)
        self.assertEqual(create_dt(year=2013, month=3, day=27, hour=12, minute=25), act.end)

        self.assertRelationCount(1, me,     constants.REL_SUB_PART_2_ACTIVITY,   act)
        self.assertRelationCount(1, genma,  constants.REL_SUB_PART_2_ACTIVITY,   act)
        self.assertRelationCount(1, akane,  constants.REL_SUB_PART_2_ACTIVITY,   act)
        self.assertRelationCount(1, ranma,  constants.REL_SUB_ACTIVITY_SUBJECT,  act)
        self.assertRelationCount(1, dojo_s, constants.REL_SUB_LINKED_2_ACTIVITY, act)
        self.assertRelationCount(0, dojo_s, constants.REL_SUB_ACTIVITY_SUBJECT,  act)
        # Auto subject #1
        self.assertRelationCount(1, dojo_t, constants.REL_SUB_ACTIVITY_SUBJECT,  act)
        # Auto subject #2
        self.assertRelationCount(1, school, constants.REL_SUB_ACTIVITY_SUBJECT,  act)
        # No auto subject with managed organisations
        self.assertRelationCount(0, mngd,   constants.REL_SUB_ACTIVITY_SUBJECT,  act)
        # Auto subject #3 -> no duplicate
        self.assertRelationCount(1, rest,   constants.REL_SUB_ACTIVITY_SUBJECT,  act)

        self.assertEqual(8, Relation.objects.filter(subject_entity=act.id).count())

    def test_createview04(self):
        "No end but end time."
        act = self._create_activity_by_view(
            **{
                f'{self.EXTRA_START_KEY}_0': '2013-3-29',
                f'{self.EXTRA_START_KEY}_1': '14:30:00',
                f'{self.EXTRA_END_KEY}_1': '15:45:00',
            }
        )
        create_dt = partial(self.create_datetime, year=2013, month=3, day=29)
        self.assertEqual(create_dt(hour=14, minute=30), act.start)
        self.assertEqual(create_dt(hour=15, minute=45), act.end)

    def test_createview05(self):
        "FLOATING type."
        act = self._create_activity_by_view()
        self.assertIsNone(act.start)
        self.assertIsNone(act.end)
        self.assertEqual(constants.FLOATING, act.floating_type)

    def test_createview06(self):
        "FLOATING_TIME type."
        act = self._create_activity_by_view(
            **{
                f'{self.EXTRA_START_KEY}_0': '2013-3-30',
                f'{self.EXTRA_END_KEY}_0':   '2013-3-30',
            }
        )
        create_dt = partial(self.create_datetime, year=2013, month=3, day=30)
        self.assertEqual(create_dt(hour=0,  minute=0),  act.start)
        self.assertEqual(create_dt(hour=23, minute=59), act.end)
        self.assertEqual(constants.FLOATING_TIME, act.floating_type)

    def test_createview_default_duration01(self):
        "default_day_duration=1 + FLOATING_TIME."
        atype = self.get_object_or_fail(ActivityType, id=constants.ACTIVITYTYPE_SHOW)
        self.assertEqual(1,          atype.default_day_duration)
        self.assertEqual('00:00:00', atype.default_hour_duration)

        act = self._create_activity_by_view(
            'TGS', atype.id, **{f'{self.EXTRA_START_KEY}_0': '2013-7-3'}
        )

        create_dt = partial(self.create_datetime, year=2013, month=7, day=3)
        self.assertEqual(create_dt(hour=0,  minute=0),  act.start)
        self.assertEqual(create_dt(hour=23, minute=59), act.end)

    def test_createview_default_duration02(self):
        "default_day_duration=1 + is_all_day."
        act = self._create_activity_by_view(
            'TGS', constants.ACTIVITYTYPE_SHOW, is_all_day=True,
            **{f'{self.EXTRA_START_KEY}_0': '2013-7-3'}
        )

        create_dt = partial(self.create_datetime, year=2013, month=7, day=3)
        self.assertEqual(create_dt(hour=0,  minute=0),  act.start)
        self.assertEqual(create_dt(hour=23, minute=59), act.end)

    def test_createview_default_duration03(self):
        "default_duration = 1.5 day + FLOATING_TIME."
        atype = ActivityType.objects.create(
            pk='activities-activity_custom_1',
            name='Big Show',
            default_day_duration=1,
            default_hour_duration='12:00:00',
            is_custom=True,
        )

        act = self._create_activity_by_view(
            'TGS', atype.id, **{f'{self.EXTRA_START_KEY}_0': '2013-7-3'}
        )

        create_dt = partial(self.create_datetime, year=2013, month=7)
        self.assertEqual(create_dt(day=3, hour=0,  minute=0),  act.start)
        self.assertEqual(create_dt(day=4, hour=23, minute=59), act.end)

    def test_createview_default_duration04(self):
        "default_duration = 0 + FLOATING_TIME."
        atype = ActivityType.objects.create(
            pk='activities-activity_custom_1',
            name='Big Show',
            default_day_duration=0,
            default_hour_duration='00:00:00',
            is_custom=True,
        )

        act = self._create_activity_by_view(
            'TGS', atype.id, **{f'{self.EXTRA_START_KEY}_0': '2013-7-3'}
        )

        create_dt = partial(self.create_datetime, year=2013, month=7, day=3)
        self.assertEqual(create_dt(hour=0,  minute=0),  act.start)
        self.assertEqual(create_dt(hour=23, minute=59), act.end)

    @skipIfCustomOrganisation
    def test_createview_no_auto_subjects(self):
        user = self.login()
        me = user.linked_contact

        sv = self.get_object_or_fail(SettingValue, key_id=constants.SETTING_AUTO_ORGA_SUBJECTS)
        sv.value = False  # We disable the auto subjects feature
        sv.save()

        response1 = self.assertGET200(self.ACTIVITY_CREATION_URL)

        with self.assertNoException():
            subjects_f = response1.context['form'].fields[self.EXTRA_SUBJECTS_KEY]

        self.assertFalse(subjects_f.help_text)

        # ---
        dojo = Organisation.objects.create(user=user, name='Tendo Dojo')
        Relation.objects.create(
            subject_entity=me, type_id=REL_SUB_EMPLOYED_BY, object_entity=dojo, user=user,
        )

        title = 'My task'
        my_calendar = Calendar.objects.get_default_calendar(user)
        response2 = self.client.post(
            self.ACTIVITY_CREATION_URL,
            follow=True,
            data={
                'user': user.pk,
                'title': title,
                'status': Status.objects.all()[0].pk,

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(constants.ACTIVITYTYPE_TASK),

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,
            },
        )
        self.assertNoFormError(response2)

        act = self.get_object_or_fail(Activity, title=title)
        self.assertRelationCount(1, me,   constants.REL_SUB_PART_2_ACTIVITY,  act)
        self.assertRelationCount(0, dojo, constants.REL_SUB_ACTIVITY_SUBJECT, act)

        # Better in a teardown method...
        sv.value = True
        sv.save()

    def test_createview_teams(self):
        "Teams as participants are replaced by their teammates."
        user = self.login()

        create_user = get_user_model().objects.create
        musashi = create_user(
            username='musashi', first_name='Musashi',
            last_name='Miyamoto', email='musashi@miyamoto.jp',
        )
        kojiro  = create_user(
            username='kojiro', first_name='Kojiro',
            last_name='Sasaki', email='kojiro@sasaki.jp',
        )

        team = create_user(username='Samurais', is_team=True, role=None)
        team.teammates = [musashi, kojiro, user]  # TODO: user + my_participation !!!!!!

        title = 'Fight !!'
        response = self.client.post(
            self.ACTIVITY_CREATION_URL, follow=True,
            data={
                'user':  user.pk,
                'title': title,

                f'{self.EXTRA_START_KEY}_0': '2015-03-10',

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': Calendar.objects.get_default_calendar(user).pk,

                self.EXTRA_PARTUSERS_KEY: [team.id],

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(
                    constants.ACTIVITYTYPE_MEETING,
                    constants.ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                ),
            },
        )
        self.assertNoFormError(response)

        act = self.get_object_or_fail(Activity, title=title)
        relations = Relation.objects.filter(
            subject_entity=act.id, type=constants.REL_OBJ_PART_2_ACTIVITY,
        )
        self.assertEqual(3, len(relations))
        self.assertSetEqual(
            {musashi.linked_contact, kojiro.linked_contact, user.linked_contact},
            {r.object_entity.get_real_entity() for r in relations},
        )

    def test_createview_light_customform(self):
        "Start/end fields are missing."
        # cfci = CustomFormConfigItem.objects.get(cform_id=ACTIVITY_CREATION_CFORM.id)
        cfci = CustomFormConfigItem.objects.get(descriptor_id=ACTIVITY_CREATION_CFORM.id)
        new_groups = FieldGroupList.from_cells(
            model=Activity,
            cell_registry=ACTIVITY_CREATION_CFORM.build_cell_registry(),
            data=[
                {
                    'name': 'Main',
                    'layout': LAYOUT_REGULAR,
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'title'}),
                        (EntityCellRegularField, {'name': 'busy'}),
                        ActivitySubTypeSubCell(model=Activity).into_cell(),
                        MyParticipationSubCell(model=Activity).into_cell(),
                    ],
                },
            ],
        )
        cfci.store_groups(new_groups)
        cfci.save()

        act = self._create_activity_by_view('TGS')

        self.assertIsNone(act.start)
        self.assertIsNone(act.end)
        self.assertEqual(constants.FLOATING, act.floating_type)

    def test_createview_errors01(self):
        user = self.login()

        data = {
            'user': user.pk,
            'title': 'My task',

            self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(constants.ACTIVITYTYPE_TASK),

            f'{self.EXTRA_END_KEY}_0': '2013-3-29',

            f'{self.EXTRA_MYPART_KEY}_0': True,
            f'{self.EXTRA_MYPART_KEY}_1': Calendar.objects.get_default_calendar(user).pk,
        }
        url = self.ACTIVITY_CREATION_URL

        response1 = self.assertPOST200(url, follow=True, data=data)
        self.assertFormError(
            response1, 'form', None,
            _("You can't set the end of your activity without setting its start"),
        )

        response2 = self.assertPOST200(
            url, follow=True, data={**data, f'{self.EXTRA_START_KEY}_0': '2013-3-30'},
        )
        self.assertFormError(response2, 'form', None, _('End is before start'))

        response3 = self.assertPOST200(
            url,
            follow=True,
            data={**data, f'{self.EXTRA_START_KEY}_0': '2013-3-29', 'busy': True},
        )
        self.assertFormError(
            response3, 'form', None,
            _("A floating on the day activity can't busy its participants"),
        )

    def test_createview_errors02(self):
        "RelationType constraint error."
        user = self.login()

        bad_subject = self._create_meeting()
        response = self.assertPOST200(
            self.ACTIVITY_CREATION_URL, follow=True,
            data={
                'user': user.pk,
                'title': 'My task',

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(constants.ACTIVITYTYPE_TASK),

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': Calendar.objects.get_default_calendar(user).pk,

                self.EXTRA_SUBJECTS_KEY: self.formfield_value_multi_generic_entity(bad_subject),
            },
        )
        self.assertFormError(
            response, 'form', self.EXTRA_SUBJECTS_KEY,
            _('This content type is not allowed.'),
        )

    @skipIfCustomContact
    def test_createview_errors03(self):
        "other_participants contains contact of user."
        user = self.login()

        ranma = Contact.objects.create(user=user, first_name='Ranma', last_name='Saotome')
        other = self.other_user.linked_contact
        response = self.assertPOST200(
            self.ACTIVITY_CREATION_URL, follow=True,
            data={
                'user':               user.id,
                'title':              'My task',

                self.EXTRA_SUBTYPE_KEY:  self._acttype_field_value(constants.ACTIVITYTYPE_TASK),

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': Calendar.objects.get_default_calendar(user).pk,

                self.EXTRA_SUBJECTS_KEY:  self.formfield_value_multi_generic_entity(ranma),

                self.EXTRA_OTHERPART_KEY: self.formfield_value_multi_creator_entity(other),
            },
        )
        self.assertFormError(
            response, 'form', self.EXTRA_OTHERPART_KEY,
            # _('This entity does not exist.'),
            _('«%(entity)s» violates the constraints.') % {'entity': other},
        )

    def test_createview_errors04(self):
        "participating_users contains request.user."
        user = self.login()

        response = self.assertPOST200(
            self.ACTIVITY_CREATION_URL,
            follow=True,
            data={
                'user':               user.id,
                'title':              'My task',

                self.EXTRA_SUBTYPE_KEY:  self._acttype_field_value(constants.ACTIVITYTYPE_TASK),

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': Calendar.objects.get_default_calendar(user).pk,

                self.EXTRA_PARTUSERS_KEY: [user.pk],
            },
        )
        self.assertFormError(
            response, 'form', self.EXTRA_PARTUSERS_KEY,
            _('Select a valid choice. %(value)s is not one of the available choices.') % {
                'value': user.id,
            },
        )

    @skipIfNotInstalled('creme.assistants')
    def test_createview_alert01(self):
        user = self.login()

        title = 'Meeting01'
        my_calendar = Calendar.objects.get_default_calendar(user)
        response = self.client.post(
            self.ACTIVITY_CREATION_URL, follow=True,
            data={
                'user':  user.id,
                'title': title,

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(
                    constants.ACTIVITYTYPE_MEETING,
                    constants.ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                ),
                f'{self.EXTRA_START_KEY}_0': '2010-1-10',

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,

                self.EXTRA_ALERTDT_KEY: '2010-2-10 10:05',

                f'{self.EXTRA_ALERTPERIOD_KEY}_0': 'days',
                f'{self.EXTRA_ALERTPERIOD_KEY}_1': 2,
            },
        )
        self.assertNoFormError(response)

        act = self.get_object_or_fail(Activity, title=title)
        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2010, month=1, day=10), act.start)
        self.assertEqual(constants.ACTIVITYTYPE_MEETING, act.type.id)
        self.assertEqual(constants.ACTIVITYSUBTYPE_MEETING_QUALIFICATION, act.sub_type.id)

        alerts = Alert.objects.filter(entity_id=act.id).order_by('id')
        self.assertEqual(2, len(alerts))

        alert1 = alerts[0]
        self.assertEqual(_('Alert of activity'), alert1.title)
        self.assertEqual(
            _('Alert related to {activity}').format(activity=act),
            alert1.description,
        )
        self.assertEqual(create_dt(2010, 2, 10, 10, 5), alert1.trigger_date)

        self.assertEqual(create_dt(2010, 1, 8, 0, 0), alerts[1].trigger_date)

    @skipIfNotInstalled('creme.assistants')
    def test_createview_alert02(self):
        "Period value is missing: no alert created."
        user = self.login()

        title = 'Meeting01'
        my_calendar = Calendar.objects.get_default_calendar(user)
        response = self.client.post(
            self.ACTIVITY_CREATION_URL,
            follow=True,
            data={
                'user':  user.pk,
                'title': title,

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(
                    constants.ACTIVITYTYPE_MEETING,
                    constants.ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                ),

                f'{self.EXTRA_START_KEY}_0': '2013-3-28',
                f'{self.EXTRA_START_KEY}_1': '17:30:00',

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,

                f'{self.EXTRA_ALERTPERIOD_KEY}_0': 'days',
            },
        )
        self.assertNoFormError(response)

        act = self.get_object_or_fail(Activity, title=title)
        self.assertFalse(Alert.objects.filter(entity_id=act.id))

    @skipIfNotInstalled('creme.assistants')
    def test_createview_alert03(self):
        "Cannot create a relative alert on floating activity."
        user = self.login()

        title = 'Meeting01'
        my_calendar = Calendar.objects.get_default_calendar(user)
        response = self.assertPOST200(
            self.ACTIVITY_CREATION_URL,
            follow=True,
            data={
                'user':  user.id,
                'title': title,

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(
                    constants.ACTIVITYTYPE_MEETING,
                    constants.ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                ),

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,

                f'{self.EXTRA_ALERTPERIOD_KEY}_0': 'days',
                f'{self.EXTRA_ALERTPERIOD_KEY}_1': 1,
            },
        )
        self.assertFormError(
            response, 'form', self.EXTRA_ALERTPERIOD_KEY,
            _('You cannot set a relative alert on a floating activity'),
        )

    @skipIfNotInstalled('creme.assistants')
    @skipIfCustomContact
    def test_createview_usermsg(self):
        "UserMessage creation."
        user = self.login()
        other_user = self.other_user
        self.assertEqual(0, UserMessage.objects.count())

        # TODO: improve FieldGroupList API (eg .extend()) ?
        umsg_cell = UserMessagesSubCell(model=Activity).into_cell()
        # cfci = CustomFormConfigItem.objects.get(cform_id=ACTIVITY_CREATION_CFORM.id)
        cfci = CustomFormConfigItem.objects.get(descriptor_id=ACTIVITY_CREATION_CFORM.id)
        old_groups = ACTIVITY_CREATION_CFORM.groups(item=cfci)
        new_groups = FieldGroupList(
            model=old_groups.model,
            cell_registry=old_groups.cell_registry,
            groups=[
                *old_groups,
                FieldGroup(
                    name='user_messages',
                    cells=[umsg_cell],
                    layout=LAYOUT_REGULAR,
                )
            ]
        )
        cfci.store_groups(new_groups)
        cfci.save()

        me    = user.linked_contact
        ranma = other_user.linked_contact

        create_contact = partial(Contact.objects.create, user=user)
        genma = create_contact(first_name='Genma', last_name='Saotome')
        akane = create_contact(first_name='Akane', last_name='Tendo')

        url = self.ACTIVITY_CREATION_URL
        response = self.assertGET200(url)

        with self.assertNoException():
            msg_f = response.context['form'].fields[umsg_cell.key]

        self.assertIsInstance(msg_f, ModelMultipleChoiceField)

        title = 'Meeting dojo'
        my_calendar = Calendar.objects.get_default_calendar(user)
        response = self.client.post(
            url, follow=True,
            data={
                'user':  user.id,
                'title': title,

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(
                    constants.ACTIVITYTYPE_MEETING,
                    constants.ACTIVITYSUBTYPE_MEETING_NETWORK,
                ),
                f'{self.EXTRA_START_KEY}_0': '2010-1-10',

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.id,

                self.EXTRA_PARTUSERS_KEY: other_user.pk,
                self.EXTRA_OTHERPART_KEY: self.formfield_value_multi_creator_entity(genma),
                self.EXTRA_SUBJECTS_KEY:  self.formfield_value_multi_generic_entity(akane),

                self.EXTRA_MESSAGES_KEY: [user.id, other_user.id],
            },
        )
        self.assertNoFormError(response)

        meeting = self.get_object_or_fail(
            Activity, title=title, type=constants.ACTIVITYTYPE_MEETING,
        )

        self.assertRelationCount(1, me,    constants.REL_SUB_PART_2_ACTIVITY,  meeting)
        self.assertRelationCount(1, ranma, constants.REL_SUB_PART_2_ACTIVITY,  meeting)
        self.assertRelationCount(1, genma, constants.REL_SUB_PART_2_ACTIVITY,  meeting)
        self.assertRelationCount(1, akane, constants.REL_SUB_ACTIVITY_SUBJECT, meeting)

        messages = UserMessage.objects.all()
        self.assertEqual(2, len(messages))

        message = messages[0]
        self.assertEqual(user, message.sender)
        self.assertDatetimesAlmostEqual(now(), message.creation_date)
        self.assertEqual(PRIO_NOT_IMP_PK,  message.priority_id)
        self.assertFalse(message.email_sent)
        self.assertEqual(meeting.id,             message.entity_id)
        self.assertEqual(meeting.entity_type_id, message.entity_content_type_id)

        self.assertEqual({user, other_user}, {msg.recipient for msg in messages})

        self.assertIn(str(meeting), message.title)

        body = message.body
        self.assertIn(str(akane), body)
        self.assertIn(str(me), body)
        self.assertIn(str(ranma), body)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_create_view_meeting(self):
        user = self.login()

        atype = self.get_object_or_fail(ActivityType, pk=constants.ACTIVITYTYPE_MEETING)
        self.assertEqual(0,          atype.default_day_duration)
        self.assertEqual('00:15:00', atype.default_hour_duration)  # TODO: timedelta instead ??

        subtype = self.get_object_or_fail(
            ActivitySubType, pk=constants.ACTIVITYSUBTYPE_MEETING_NETWORK,
        )

        create_contact = partial(Contact.objects.create, user=user)
        ranma = create_contact(first_name='Ranma', last_name='Saotome')
        genma = create_contact(first_name='Genma', last_name='Saotome')

        dojo = Organisation.objects.create(user=user, name='Dojo')

        url = reverse('activities__create_activity', args=('meeting',))
        response = self.assertGET200(url)
        self.assertEqual(_('Create a meeting'), response.context.get('title'))

        # TODO: help text of end (duration)

        title = 'My meeting'
        status = Status.objects.all()[0]
        my_calendar = Calendar.objects.get_default_calendar(user)
        response = self.client.post(
            url, follow=True,
            data={
                'user':   user.pk,
                'title':  title,
                'status': status.pk,

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(atype.id, subtype.id),

                f'{self.EXTRA_START_KEY}_0': '2013-4-12',
                f'{self.EXTRA_START_KEY}_1': '10:00:00',

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,

                self.EXTRA_OTHERPART_KEY: self.formfield_value_multi_creator_entity(genma),
                self.EXTRA_SUBJECTS_KEY:  self.formfield_value_multi_generic_entity(ranma),
                self.EXTRA_LINKED_KEY:    self.formfield_value_multi_generic_entity(dojo),
            },
        )
        self.assertNoFormError(response)

        meeting = self.get_object_or_fail(Activity, type=atype, title=title)

        self.assertEqual(status, meeting.status)
        self.assertEqual(constants.NARROW, meeting.floating_type)
        self.assertEqual(
            self.create_datetime(year=2013, month=4, day=12, hour=10, minute=00),
            meeting.start,
        )
        self.assertEqual(
            self.create_datetime(year=2013, month=4, day=12, hour=10, minute=15),
            meeting.end,
        )

        self.assertRelationCount(
            1, user.linked_contact, constants.REL_SUB_PART_2_ACTIVITY, meeting,
        )
        self.assertRelationCount(1, genma, constants.REL_SUB_PART_2_ACTIVITY, meeting)
        self.assertRelationCount(1, ranma, constants.REL_SUB_ACTIVITY_SUBJECT, meeting)
        self.assertRelationCount(1, dojo, constants.REL_SUB_LINKED_2_ACTIVITY, meeting)

    def test_create_view_phonecall(self):
        user = self.login()

        type_id = constants.ACTIVITYTYPE_PHONECALL
        subtype = self.get_object_or_fail(
            ActivitySubType,
            pk=constants.ACTIVITYSUBTYPE_PHONECALL_OUTGOING,
        )

        url = reverse('activities__create_activity', args=('phonecall',))
        response = self.assertGET200(url)
        self.assertEqual(_('Create a phone call'), response.context.get('title'))

        title = 'My call'
        my_calendar = Calendar.objects.get_default_calendar(user)
        response = self.client.post(
            url, follow=True,
            data={
                'user': user.pk,
                'title': title,

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(type_id, subtype.id),

                f'{self.EXTRA_START_KEY}_0': '2013-4-12',
                f'{self.EXTRA_START_KEY}_1': '10:00:00',

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,
            },
        )
        self.assertNoFormError(response)
        self.get_object_or_fail(Activity, type=type_id, title=title)

    def test_create_view_invalidtype(self):
        self.login()
        self.assertGET404(reverse('activities__create_activity', args=('invalid',)))

    def test_create_view_unallowedtype(self):
        user = self.login()

        response = self.assertPOST200(
            reverse('activities__create_activity', args=('phonecall',)),
            follow=True,
            data={
                'user': user.pk,
                'title': 'My meeting',

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(
                    constants.ACTIVITYTYPE_MEETING,
                    constants.ACTIVITYSUBTYPE_MEETING_NETWORK,
                ),

                f'{self.EXTRA_START_KEY}_0': '2013-4-12',
                f'{self.EXTRA_START_KEY}_1': '10:00:00',
            },
        )
        self.assertFormError(
            response, 'form', self.EXTRA_SUBTYPE_KEY, _('This type causes constraint error.'),
        )

    def test_create_view_task(self):
        user = self.login()
        type_id = constants.ACTIVITYTYPE_TASK

        url = reverse('activities__create_activity', args=('task',))
        self.assertGET200(url)

        title = 'My call'
        my_calendar = Calendar.objects.get_default_calendar(user)
        response = self.client.post(
            url,
            follow=True,
            data={
                'user': user.pk,
                'title': title,

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(type_id),

                f'{self.EXTRA_START_KEY}_0': '2013-4-12',
                f'{self.EXTRA_START_KEY}_1': '10:00:00',

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,
            },
        )
        self.assertNoFormError(response)
        self.get_object_or_fail(Activity, type=type_id, title=title)

    @skipIfCustomContact
    def test_createview_related01(self):
        user = self.login()
        other_user = self.other_user

        contact01 = Contact.objects.create(user=user, first_name='Ranma', last_name='Saotome')
        contact02 = other_user.linked_contact

        uri = self._build_add_related_uri(contact01)
        response1 = self.assertGET200(uri)

        with self.assertNoException():
            form = response1.context['form']

        self.assertListEqual([contact01], form.initial.get(self.EXTRA_OTHERPART_KEY))

        title = 'My meeting'
        callback_url = contact01.get_absolute_url()
        response2 = self.client.post(
            uri,
            follow=True,
            data={
                'user':  user.id,
                'title': title,

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(
                    constants.ACTIVITYTYPE_MEETING,
                    constants.ACTIVITYSUBTYPE_MEETING_REVIVAL,
                ),

                f'{self.EXTRA_START_KEY}_0': '2010-1-10',
                f'{self.EXTRA_START_KEY}_1': '17:30:00',

                self.EXTRA_PARTUSERS_KEY: [other_user.pk],

                'callback_url': callback_url,
            },
        )
        self.assertNoFormError(response2)
        # self.assertRedirects(response2, contact01.get_absolute_url())
        self.assertRedirects(response2, callback_url)

        meeting = self.get_object_or_fail(Activity, title=title)
        self.assertEqual(
            self.create_datetime(year=2010, month=1, day=10, hour=17, minute=30),
            meeting.start
        )
        self.assertEqual(constants.ACTIVITYTYPE_MEETING,            meeting.type.pk)
        self.assertEqual(constants.ACTIVITYSUBTYPE_MEETING_REVIVAL, meeting.sub_type_id)

        self.assertEqual(2, Relation.objects.count())

        relations = Relation.objects.filter(type=constants.REL_SUB_PART_2_ACTIVITY)
        self.assertEqual(1, len(relations))

        relation = relations[0]
        self.assertEqual(contact02.id, relation.subject_entity_id)
        self.assertEqual(meeting.id,   relation.object_entity_id)

    def test_createview_related02(self):
        "Link to a user-Contact => selected a participating user."
        self.login()

        response = self.assertGET200(self._build_add_related_uri(
            self.other_user.linked_contact, constants.ACTIVITYTYPE_MEETING,
        ))

        with self.assertNoException():
            form = response.context['form']

        self.assertListEqual([self.other_user], form.initial.get(self.EXTRA_PARTUSERS_KEY))

    @skipIfCustomOrganisation
    def test_createview_related03(self):
        "Link to an Entity which can be a subject."
        user = self.login()

        dojo = Organisation.objects.create(user=user, name='Tendo no dojo')
        response = self.assertGET200(
            self._build_add_related_uri(dojo, constants.ACTIVITYTYPE_MEETING),
        )

        self.assertListEqual(
            [dojo.id],
            [e.id for e in response.context['form'].initial.get(self.EXTRA_SUBJECTS_KEY, ())],
        )

    def test_createview_related04(self):
        "Link to an Entity which cannot be a participant/subject."
        user = self.login()

        linked = Activity.objects.create(
            user=user, title='Meet01', type_id=constants.ACTIVITYTYPE_MEETING,
        )
        response = self.assertGET200(
            self._build_add_related_uri(linked, constants.ACTIVITYTYPE_PHONECALL)
        )

        self.assertListEqual(
            [linked.id],
            [e.id for e in response.context['form'].initial.get(self.EXTRA_LINKED_KEY, ())],
        )

    def test_createview_related05(self):
        "Not allowed to LINK."
        user = self.login(is_superuser=False, creatable_models=[Activity])
        SetCredentials.objects.create(
            role=self.role,
            # Not LINK
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.DELETE,
            set_type=SetCredentials.ESET_OWN,
        )

        linked = Activity.objects.create(
            user=user, title='Meet01', type_id=constants.ACTIVITYTYPE_MEETING,
        )
        self.assertGET403(self._build_add_related_uri(linked, constants.ACTIVITYTYPE_PHONECALL))

    @skipIfCustomContact
    def test_createview_related_meeting(self):
        "Meeting forced."
        user = self.login()

        ryoga = Contact.objects.create(user=user, first_name='Ryoga', last_name='Hibiki')

        uri = self._build_add_related_uri(ryoga, constants.ACTIVITYTYPE_MEETING)
        title = 'My meeting'
        my_calendar = Calendar.objects.get_default_calendar(user)
        response1 = self.client.post(
            uri,
            follow=True,
            data={
                'user': user.pk,
                'title': title,

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(
                    constants.ACTIVITYTYPE_MEETING,
                    constants.ACTIVITYSUBTYPE_MEETING_REVIVAL,
                ),

                f'{self.EXTRA_START_KEY}_0': '2013-5-21',
                f'{self.EXTRA_START_KEY}_1': '9:30:00',

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,
            },
        )
        self.assertNoFormError(response1)
        # self.assertRedirects(response, ryoga.get_absolute_url())

        meeting = self.get_object_or_fail(Activity, title=title)
        self.assertEqual(
            self.create_datetime(year=2013, month=5, day=21, hour=9, minute=30),
            meeting.start
        )
        self.assertEqual(constants.ACTIVITYTYPE_MEETING,            meeting.type.pk)
        self.assertEqual(constants.ACTIVITYSUBTYPE_MEETING_REVIVAL, meeting.sub_type_id)

        self.assertRedirects(response1, meeting.get_absolute_url())

        # ---
        response2 = self.assertPOST200(
            uri, follow=True,
            data={
                'user':  user.pk,
                'title': 'Other meeting',

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(constants.ACTIVITYTYPE_TASK),

                f'{self.EXTRA_START_KEY}_0': '2013-5-21',
                f'{self.EXTRA_START_KEY}_1': '9:30:00',

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,
            },
        )
        self.assertFormError(
            response2, 'form', self.EXTRA_SUBTYPE_KEY, _('This type causes constraint error.'),
        )

    @skipIfCustomContact
    def test_createview_related_other(self):
        user = self.login()

        ryoga = Contact.objects.create(user=user, first_name='Ryoga', last_name='Hibiki')
        build_url = partial(self._build_add_related_uri, ryoga)
        self.assertGET200(build_url(constants.ACTIVITYTYPE_PHONECALL))
        self.assertGET200(build_url(constants.ACTIVITYTYPE_TASK))
        self.assertGET404(build_url('foobar'))

    def test_popup_view01(self):
        user = self.login()

        create_dt = partial(self.create_datetime, year=2010, month=10, day=1)
        activity = Activity.objects.create(
            user=user, title='Meet01',
            type_id=constants.ACTIVITYTYPE_MEETING,
            start=create_dt(hour=14, minute=0),
            end=create_dt(hour=15, minute=0),
        )
        response = self.assertGET200(
            reverse('activities__view_activity_popup', args=(activity.id,))
        )
        self.assertContains(response, activity.type)

    def test_editview01(self):
        user = self.login()

        title = 'meet01'
        create_dt = partial(self.create_datetime, year=2013, month=10, day=1)
        start = create_dt(hour=22, minute=0)
        end = create_dt(hour=23, minute=0)
        type_id = constants.ACTIVITYTYPE_MEETING
        sub_type_id = constants.ACTIVITYSUBTYPE_MEETING_MEETING
        activity = Activity.objects.create(
            user=user, title=title,
            type_id=type_id, sub_type_id=sub_type_id,
            start=start, end=end,
        )
        rel = Relation.objects.create(
            subject_entity=user.linked_contact, user=user,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
            object_entity=activity,
        )

        url = activity.get_edit_absolute_url()
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            start_f = fields[self.EXTRA_START_KEY]
            end_f = fields[self.EXTRA_END_KEY]
            subtype_f = fields[self.EXTRA_SUBTYPE_KEY]

        self.assertEqual(1,  start_f.initial[0].day)
        self.assertEqual(22, start_f.initial[1].hour)
        self.assertEqual(1,  end_f.initial[0].day)
        self.assertEqual(23, end_f.initial[1].hour)

        self.assertTupleEqual((type_id, sub_type_id), subtype_f.initial)

        # ---
        title += '_edited'
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user': self.user.pk,
                'title': title,
                f'{self.EXTRA_START_KEY}_0': '2011-2-22',
                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(type_id, sub_type_id),
            },
        ))

        activity = self.refresh(activity)
        self.assertEqual(title, activity.title)
        self.assertEqual(create_dt(year=2011, month=2, day=22), activity.start)
        self.assertEqual(type_id,     activity.type.id)
        self.assertEqual(sub_type_id, activity.sub_type.id)

        relations = Relation.objects.filter(type=constants.REL_SUB_PART_2_ACTIVITY)
        self.assertEqual(1, len(relations))
        self.assertEqual(rel, relations[0])

    def test_editview02(self):
        "Change type."
        user = self.login()

        title = 'act01'
        create_dt = self.create_datetime
        activity = Activity.objects.create(
            user=user, title=title,
            start=create_dt(year=2010, month=10, day=1, hour=14, minute=0),
            end=create_dt(year=2010, month=10, day=1, hour=15, minute=0),
            type_id=constants.ACTIVITYTYPE_PHONECALL,
            sub_type_id=constants.ACTIVITYSUBTYPE_PHONECALL_INCOMING,
        )

        title += '_edited'
        self.assertNoFormError(self.client.post(
            activity.get_edit_absolute_url(),
            follow=True,
            data={
                'user':  user.pk,
                'title': title,
                f'{self.EXTRA_START_KEY}_0': '2011-2-22',
                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(
                    constants.ACTIVITYTYPE_MEETING,
                    constants.ACTIVITYSUBTYPE_MEETING_NETWORK,
                ),
            },
        ))

        activity = self.refresh(activity)
        self.assertEqual(title, activity.title)
        self.assertEqual(create_dt(year=2011, month=2, day=22), activity.start)
        self.assertEqual(constants.ACTIVITYTYPE_MEETING,            activity.type_id)
        self.assertEqual(constants.ACTIVITYSUBTYPE_MEETING_NETWORK, activity.sub_type_id)

    def test_editview03(self):
        "Collision."
        user = self.login()
        contact = user.linked_contact

        def create_task(**kwargs):
            task = Activity.objects.create(
                user=user, type_id=constants.ACTIVITYTYPE_TASK, **kwargs
            )
            Relation.objects.create(
                subject_entity=contact, user=user,
                type_id=constants.REL_SUB_PART_2_ACTIVITY,
                object_entity=task,
            )

            return task

        create_dt = self.create_datetime
        task01 = create_task(
            title='Task#1',
            start=create_dt(year=2013, month=4, day=17, hour=11, minute=0),
            end=create_dt(year=2013,   month=4, day=17, hour=12, minute=0),
        )
        task02 = create_task(
            title='Task#2', busy=True,
            start=create_dt(year=2013, month=4, day=17, hour=14, minute=0),
            end=create_dt(year=2013,   month=4, day=17, hour=15, minute=0),
        )

        response = self.assertPOST200(
            task01.get_edit_absolute_url(),
            follow=True,
            data={
                'user':  user.pk,
                'title': task01.title,
                'busy':  True,

                f'{self.EXTRA_START_KEY}_0': '2013-4-17',
                f'{self.EXTRA_START_KEY}_1': '14:30:00',

                f'{self.EXTRA_END_KEY}_0': '2013-4-17',
                f'{self.EXTRA_END_KEY}_1': '16:00:00',

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(
                    task01.type_id,
                    task01.sub_type_id,
                ),
            }
        )
        self.assertFormError(
            response, 'form', None,
            _(
                '{participant} already participates to the activity '
                '«{activity}» between {start} and {end}.'
            ).format(
                participant=contact,
                activity=task02,
                start='14:30:00',
                end='15:00:00',
            )
        )

    def test_editview04(self):
        "Edit FLOATING_TIME activity."
        task = self._create_activity_by_view(
            **{f'{self.EXTRA_START_KEY}_0': '2013-7-25'}
        )
        self.assertEqual(constants.FLOATING_TIME, task.floating_type)

        response = self.assertGET200(task.get_edit_absolute_url())

        with self.assertNoException():
            fields = response.context['form'].fields
            start_f = fields[self.EXTRA_START_KEY]
            end_f = fields[self.EXTRA_END_KEY]

        self.assertEqual(25, start_f.initial[0].day)
        self.assertIsNone(start_f.initial[1])
        self.assertEqual(25, end_f.initial[0].day)
        self.assertIsNone(end_f.initial[1])

    def test_editview05(self):
        "Edit an Unavailability: type cannot be changed, sub_type can."
        user = self.login()

        create_dt = self.create_datetime
        activity = Activity.objects.create(
            user=user, title='act01',
            start=create_dt(year=2015, month=1, day=1, hour=14, minute=0),
            end=create_dt(year=2015, month=1, day=1, hour=15, minute=0),
            type_id=constants.ACTIVITYTYPE_INDISPO,
        )

        url = activity.get_edit_absolute_url()
        fvalue = self._acttype_field_value
        data = {
            'user':       user.pk,
            'title':      activity.title,

            f'{self.EXTRA_START_KEY}_0':      '2015-1-1',
            f'{self.EXTRA_START_KEY}_1': '14:30:00',

            f'{self.EXTRA_END_KEY}_0': '2015-1-1',
            f'{self.EXTRA_END_KEY}_1': '16:00:00',
        }

        response = self.assertPOST200(
            url,
            follow=True,
            data={
                **data,
                self.EXTRA_SUBTYPE_KEY: fvalue(
                    constants.ACTIVITYTYPE_PHONECALL,
                    constants.ACTIVITYSUBTYPE_PHONECALL_INCOMING,
                ),
            },
        )
        self.assertFormError(
            response, 'form', self.EXTRA_SUBTYPE_KEY, _('This type causes constraint error.')
        )

        subtype = ActivitySubType.objects.create(
            id='hollydays', name='Hollydays', type_id=constants.ACTIVITYTYPE_INDISPO,
        )
        response = self.client.post(
            url, follow=True,
            data={
                **data,
                self.EXTRA_SUBTYPE_KEY: fvalue(constants.ACTIVITYTYPE_INDISPO, subtype.id),
            },
        )
        self.assertNoFormError(response)

        activity = self.refresh(activity)
        self.assertEqual(
            create_dt(year=2015, month=1, day=1, hour=14, minute=30),
            activity.start,
        )
        self.assertEqual(constants.ACTIVITYTYPE_INDISPO, activity.type_id)
        self.assertEqual(subtype, activity.sub_type)

    @skipIfCustomContact
    def test_delete01(self):
        "Cannot delete a participant."
        user = self.login()

        activity = self._create_meeting()
        musashi = Contact.objects.create(
            user=user, first_name='Musashi', last_name='Miyamoto', is_deleted=True,
        )
        rel = Relation.objects.create(
            user=user, subject_entity=musashi,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
            object_entity=activity,
        )

        self.assertPOST409(musashi.get_delete_absolute_url(), follow=True)
        self.assertStillExists(musashi)
        self.assertStillExists(activity)
        self.assertStillExists(rel)

    @skipIfCustomContact
    def test_delete02(self):
        "Relations constants.REL_SUB_PART_2_ACTIVITY are removed when the Activity is deleted."
        user = self.login()

        activity = self._create_meeting()
        activity.trash()

        musashi = Contact.objects.create(user=user, first_name='Musashi', last_name='Miyamoto')
        rel = Relation.objects.create(
            user=user, subject_entity=musashi,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
            object_entity=activity,
        )

        self.assertPOST200(activity.get_delete_absolute_url(), follow=True)
        self.assertDoesNotExist(activity)
        self.assertDoesNotExist(rel)
        self.assertStillExists(musashi)

    @skipIfCustomContact
    def test_delete_all01(self):
        """Relations constants.REL_SUB_PART_2_ACTIVITY are removed when the
        Activity is deleted (empty_trash).
        """
        user = self.login()

        activity = self._create_meeting()
        activity.trash()

        musashi = Contact.objects.create(user=user, first_name='Musashi', last_name='Miyamoto')
        rel = Relation.objects.create(
            user=user, subject_entity=musashi,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
            object_entity=activity,
        )

        self.assertPOST200(reverse('creme_core__empty_trash'))

        job = self.get_object_or_fail(Job, type_id=trash_cleaner_type.id)
        trash_cleaner_type.execute(job)
        self.assertDoesNotExist(activity)
        self.assertDoesNotExist(rel)
        self.assertStillExists(musashi)

    @skipIfCustomContact
    def test_delete_all02(self):
        """If an Activity & its participants are in the trash, the relationships
        cannot avoid the trash emptying.
        """
        user = self.login()

        create_contact = partial(Contact.objects.create, user=user)
        musashi = create_contact(first_name='Musashi', last_name='Miyamoto')

        activity = self._create_meeting()

        kojiro = create_contact(first_name='Kojiro',  last_name='Sasaki')
        # we want that at least one contact tries to delete() before the activity
        self.assertLess(musashi.id, activity.id)
        self.assertLess(activity.id, kojiro.id)

        create_rel = partial(
            Relation.objects.create,
            user=user, type_id=constants.REL_SUB_PART_2_ACTIVITY, object_entity=activity,
        )
        create_rel(subject_entity=musashi)
        create_rel(subject_entity=kojiro)

        activity.trash()
        musashi.trash()
        kojiro.trash()

        self.assertPOST200(reverse('creme_core__empty_trash'))

        job = self.get_object_or_fail(Job, type_id=trash_cleaner_type.id)
        trash_cleaner_type.execute(job)
        self.assertDoesNotExist(activity)
        self.assertDoesNotExist(musashi)
        self.assertDoesNotExist(kojiro)

    def _aux_inner_edit_type(self, field_name):
        "Type (& subtype)."
        user = self.login()

        create_dt = self.create_datetime
        activity = Activity.objects.create(
            user=user, title='act01',
            start=create_dt(year=2015, month=1, day=1, hour=14, minute=0),
            end=create_dt(year=2015, month=1, day=1, hour=15, minute=0),
            type_id=constants.ACTIVITYTYPE_PHONECALL,
            sub_type_id=constants.ACTIVITYSUBTYPE_PHONECALL_INCOMING,
        )

        url = self.build_inneredit_url(activity, field_name)
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(
            url,
            data={
                'field_value': self._acttype_field_value(
                    constants.ACTIVITYTYPE_MEETING,
                    constants.ACTIVITYSUBTYPE_MEETING_NETWORK,
                ),
            },
        ))

        activity = self.refresh(activity)
        self.assertEqual(constants.ACTIVITYTYPE_MEETING,            activity.type_id)
        self.assertEqual(constants.ACTIVITYSUBTYPE_MEETING_NETWORK, activity.sub_type_id)

    def test_inner_edit_type01(self):
        "Type (& subtype)"
        self._aux_inner_edit_type('type')

    def test_inner_edit_type02(self):
        "SubType (& type)"
        self._aux_inner_edit_type('sub_type')

    def test_inner_edit_type03(self):
        "Exclude constants.ACTIVITYTYPE_INDISPO from valid choices"
        user = self.login()

        create_dt = self.create_datetime
        activity = Activity.objects.create(
            user=user, title='act01',
            start=create_dt(year=2015, month=1, day=1, hour=14, minute=0),
            end=create_dt(year=2015, month=1, day=1, hour=15, minute=0),
            type_id=constants.ACTIVITYTYPE_PHONECALL,
            sub_type_id=constants.ACTIVITYSUBTYPE_PHONECALL_INCOMING,
        )

        response = self.assertPOST200(
            self.build_inneredit_url(activity, 'type'),
            data={
                'field_value': self._acttype_field_value(constants.ACTIVITYTYPE_INDISPO, ''),
            },
        )
        self.assertFormError(
            response, 'form', 'field_value', _('This type causes constraint error.')
        )

    def test_inner_edit_type04(self):
        "Indisponibilities type cannot be changed, the sub_type can."
        user = self.login()

        subtype = ActivitySubType.objects.create(
            id='hollydays', name='Hollydays',
            type_id=constants.ACTIVITYTYPE_INDISPO,
        )

        create_dt = self.create_datetime
        activity = Activity.objects.create(
            user=user, title='act01',
            start=create_dt(year=2015, month=1, day=1, hour=14, minute=0),
            end=create_dt(year=2015, month=1, day=1, hour=15, minute=0),
            type_id=constants.ACTIVITYTYPE_INDISPO,
        )

        fvalue = self._acttype_field_value
        url = self.build_inneredit_url(activity, 'type')
        response = self.assertPOST200(
            url,
            data={
                'field_value': fvalue(
                    constants.ACTIVITYTYPE_PHONECALL,
                    constants.ACTIVITYSUBTYPE_PHONECALL_INCOMING,
                ),
            },
        )
        self.assertFormError(
            response, 'form', 'field_value', _('This type causes constraint error.')
        )

        self.assertNoFormError(self.client.post(
            url,
            data={'field_value': fvalue(constants.ACTIVITYTYPE_INDISPO, subtype.id)},
        ))
        activity = self.refresh(activity)
        self.assertEqual(constants.ACTIVITYTYPE_INDISPO, activity.type_id)
        self.assertEqual(subtype,              activity.sub_type)

    def test_bulk_edit_type01(self):
        "Unavailabilities cannot be changed when they are mixed with other types."
        user = self.login()

        create_dt = self.create_datetime
        create_activity = partial(Activity.objects.create, user=user)
        activity1 = create_activity(
            title='act01',
            start=create_dt(year=2015, month=1, day=1, hour=14, minute=0),
            end=create_dt(year=2015, month=1, day=1, hour=15, minute=0),
            type_id=constants.ACTIVITYTYPE_INDISPO,
        )
        activity2 = create_activity(
            title='act02',
            start=create_dt(year=2015, month=1, day=2, hour=14, minute=0),
            end=create_dt(year=2015, month=1, day=2, hour=15, minute=0),
            type_id=constants.ACTIVITYTYPE_PHONECALL,
            sub_type_id=constants.ACTIVITYSUBTYPE_PHONECALL_INCOMING,
        )

        url = self.build_bulkupdate_url(Activity, 'type')
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(
            url,
            data={
                '_bulk_fieldname': url,
                'field_value': self._acttype_field_value(
                    constants.ACTIVITYTYPE_MEETING,
                    constants.ACTIVITYSUBTYPE_MEETING_NETWORK,
                ),
                'entities': [activity1.pk, activity2.pk],
            },
        ))
        self.assertEqual(constants.ACTIVITYTYPE_MEETING, self.refresh(activity2).type_id)
        # No change
        self.assertEqual(constants.ACTIVITYTYPE_INDISPO, self.refresh(activity1).type_id)

    def test_bulk_edit_type02(self):
        "Unavailabilities type can be changed when they are not mixed with other types."
        user = self.login()

        ACTIVITYTYPE_INDISPO = constants.ACTIVITYTYPE_INDISPO
        subtype = ActivitySubType.objects.create(
            id='holidays', name='Holidays', type_id=ACTIVITYTYPE_INDISPO,
        )

        create_dt = self.create_datetime
        create_indispo = partial(Activity.objects.create, user=user, type_id=ACTIVITYTYPE_INDISPO)
        activity1 = create_indispo(
            title='Indispo01',
            start=create_dt(year=2015, month=1, day=1, hour=14, minute=0),
            end=create_dt(year=2015, month=1, day=1, hour=15, minute=0),
        )
        activity2 = create_indispo(
            title='Indispo02',
            start=create_dt(year=2015, month=1, day=2, hour=14, minute=0),
            end=create_dt(year=2015, month=1, day=2, hour=15, minute=0),
        )

        url = self.build_bulkupdate_url(Activity, 'type')
        self.assertNoFormError(self.client.post(
            url,
            data={
                '_bulk_fieldname': url,
                'field_value': self._acttype_field_value(
                    ACTIVITYTYPE_INDISPO, subtype.id,
                ),
                'entities': [activity1.pk, activity2.pk],
            },
        ))
        activity1 = self.refresh(activity1)
        self.assertEqual(ACTIVITYTYPE_INDISPO, activity1.type_id)
        self.assertEqual(subtype,              activity1.sub_type)

        activity2 = self.refresh(activity2)
        self.assertEqual(ACTIVITYTYPE_INDISPO, activity2.type_id)
        self.assertEqual(subtype,              activity2.sub_type)

    def _check_activity_collisions(self, activity_start, activity_end, participants,
                                   busy=True, exclude_activity_id=None):
        collisions = check_activity_collisions(
            activity_start, activity_end, participants,
            busy=busy, exclude_activity_id=exclude_activity_id,
        )
        if collisions:
            raise ValidationError(collisions)

    @skipIfCustomContact
    def test_collision01(self):
        user = self.login()

        create_activity = partial(Activity.objects.create, user=user)
        create_dt = self.create_datetime

        with self.assertNoException():
            act01 = create_activity(
                title='call01', type_id=constants.ACTIVITYTYPE_PHONECALL,
                sub_type_id=constants.ACTIVITYSUBTYPE_PHONECALL_INCOMING,
                start=create_dt(year=2010, month=10, day=1, hour=12, minute=0),
                end=create_dt(year=2010, month=10, day=1, hour=13, minute=0),
            )
            act02 = create_activity(
                title='meet01', type_id=constants.ACTIVITYTYPE_MEETING,
                start=create_dt(year=2010, month=10, day=1, hour=14, minute=0),
                end=create_dt(year=2010, month=10, day=1, hour=15, minute=0),
            )
            act03 = create_activity(
                title='meet02',  type_id=constants.ACTIVITYTYPE_MEETING, busy=True,
                start=create_dt(year=2010, month=10, day=1, hour=18, minute=0),
                end=create_dt(year=2010, month=10, day=1, hour=19, minute=0),
            )

            create_contact = partial(Contact.objects.create, user=user)
            c1 = create_contact(first_name='first_name1', last_name='last_name1')
            c2 = create_contact(first_name='first_name2', last_name='last_name2')

            create_rel = partial(
                Relation.objects.create,
                subject_entity=c1, type_id=constants.REL_SUB_PART_2_ACTIVITY, user=user,
            )
            create_rel(object_entity=act01)
            create_rel(object_entity=act02)
            create_rel(object_entity=act03)

        check_coll = partial(self._check_activity_collisions, participants=[c1, c2])

        try:
            # No collision
            # Next day
            check_coll(
                activity_start=create_dt(year=2010, month=10, day=2, hour=12, minute=0),
                activity_end=create_dt(year=2010,   month=10, day=2, hour=13, minute=0),
            )

            # One minute before
            check_coll(
                activity_start=create_dt(year=2010, month=10, day=1, hour=11, minute=0),
                activity_end=create_dt(year=2010,   month=10, day=1, hour=11, minute=59),
            )

            # One minute after
            check_coll(
                activity_start=create_dt(year=2010, month=10, day=1, hour=13, minute=1),
                activity_end=create_dt(year=2010,   month=10, day=1, hour=13, minute=10),
            )
            # Not busy
            check_coll(
                activity_start=create_dt(year=2010, month=10, day=1, hour=14, minute=0),
                activity_end=create_dt(year=2010,   month=10, day=1, hour=15, minute=0),
                busy=False
            )
        except ValidationError as e:
            self.fail(str(e))

        # Collision with act01
        # Before
        self.assertRaises(
            ValidationError, self._check_activity_collisions,
            activity_start=create_dt(year=2010, month=10, day=1, hour=11, minute=30),
            activity_end=create_dt(year=2010, month=10, day=1, hour=12, minute=30),
            participants=[c1, c2],
        )

        # After
        self.assertRaises(
            ValidationError, self._check_activity_collisions,
            activity_start=create_dt(year=2010, month=10, day=1, hour=12, minute=30),
            activity_end=create_dt(year=2010, month=10, day=1, hour=13, minute=30),
            participants=[c1, c2],
        )

        # Shorter
        self.assertRaises(
            ValidationError, self._check_activity_collisions,
            activity_start=create_dt(year=2010, month=10, day=1, hour=12, minute=10),
            activity_end=create_dt(year=2010, month=10, day=1, hour=12, minute=30),
            participants=[c1, c2],
        )

        # Longer
        self.assertRaises(
            ValidationError, self._check_activity_collisions,
            activity_start=create_dt(year=2010, month=10, day=1, hour=11, minute=0),
            activity_end=create_dt(year=2010, month=10, day=1, hour=13, minute=30),
            participants=[c1, c2],
        )

        # Busy1
        self.assertRaises(
            ValidationError, self._check_activity_collisions,
            activity_start=create_dt(year=2010, month=10, day=1, hour=17, minute=30),
            activity_end=create_dt(year=2010, month=10, day=1, hour=18, minute=30),
            participants=[c1, c2],
        )

        # Busy2
        self.assertRaises(
            ValidationError, self._check_activity_collisions,
            activity_start=create_dt(year=2010, month=10, day=1, hour=18, minute=0),
            activity_end=create_dt(year=2010, month=10, day=1, hour=18, minute=30),
            busy=False, participants=[c1, c2],
        )

    def test_listviews(self):
        user = self.login()
        self.assertFalse(Activity.objects.all())

        create_act = partial(Activity.objects.create, user=user)
        create_dt = self.create_datetime
        acts = [
            create_act(
                title='call01', type_id=constants.ACTIVITYTYPE_PHONECALL,
                sub_type_id=constants.ACTIVITYSUBTYPE_PHONECALL_INCOMING,
                start=create_dt(year=2010, month=10, day=1, hour=12, minute=0),
                end=create_dt(year=2010, month=10, day=1, hour=13, minute=0)
            ),
            create_act(
                title='meet01', type_id=constants.ACTIVITYTYPE_MEETING,
                sub_type_id=constants.ACTIVITYSUBTYPE_MEETING_REVIVAL,
                start=create_dt(year=2010, month=10, day=1, hour=14, minute=0),
                end=create_dt(year=2010, month=10, day=1, hour=15, minute=0)
            ),
        ]

        response = self.assertGET200(Activity.get_lv_absolute_url())

        with self.assertNoException():
            activities_page = response.context['page_obj']

        self.assertEqual(1, activities_page.number)
        self.assertEqual(2, activities_page.paginator.count)
        self.assertSetEqual({*acts}, {*activities_page.object_list})

        # Phone calls
        response = self.assertGET200(reverse('activities__list_phone_calls'))

        with self.assertNoException():
            pcalls_page = response.context['page_obj']

        self.assertListEqual([acts[0]], [*pcalls_page.object_list])

        # Meetings
        response = self.assertGET200(reverse('activities__list_meetings'))

        with self.assertNoException():
            meetings_page = response.context['page_obj']

        self.assertListEqual([acts[1]], [*meetings_page.object_list])

    def test_listview_bulk_actions(self):
        user = self.login()
        export_actions = [
            action
            for action in actions.actions_registry.bulk_actions(user=user, model=Activity)
            if isinstance(action, BulkExportICalAction)
        ]
        self.assertEqual(1, len(export_actions))

        export_action = export_actions[0]
        self.assertEqual('activities-export-ical', export_action.type)
        self.assertEqual(reverse('activities__dl_ical'), export_action.url)
        self.assertIsNone(export_action.action_data)
        self.assertTrue(export_action.is_enabled)
        self.assertTrue(export_action.is_visible)

    def test_unavailability_createview01(self):
        "Can not create an unavailability with the generic view."
        user = self.login()

        url = self.ACTIVITY_CREATION_URL
        self.assertGET200(url)

        status = Status.objects.all()[0]
        my_calendar = Calendar.objects.get_default_calendar(user)
        response = self.assertPOST200(
            url, follow=True,
            data={
                'user':  user.id,
                'title': 'Away',
                'status': status.pk,

                self.EXTRA_SUBTYPE_KEY: self._acttype_field_value(constants.ACTIVITYTYPE_INDISPO),

                f'{self.EXTRA_START_KEY}_0': '2013-3-27',
                f'{self.EXTRA_START_KEY}_1': '09:00:00',

                f'{self.EXTRA_END_KEY}_0': '2010-3-27',
                f'{self.EXTRA_END_KEY}_1': '11:00:00',

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,
            },
        )
        self.assertFormError(
            response, 'form', self.EXTRA_SUBTYPE_KEY,
            _('This type causes constraint error.'),
        )

    def test_unavailability_createview02(self):
        user = self.login()
        other_user = self.other_user

        url = self.ADD_INDISPO_URL
        response1 = self.assertGET200(url)
        self.assertEqual(_('Create an unavailability'), response1.context.get('title'))

        with self.assertNoException():
            fields = response1.context['form'].fields
            end_f = fields[self.EXTRA_END_KEY]
            p_user_f = fields[self.EXTRA_PARTUSERS_KEY]
            allday_f = fields['is_all_day']

        self.assertFalse(end_f.help_text)
        self.assertEqual(_('Unavailable users'), p_user_f.label)
        self.assertTrue(p_user_f.required)
        self.assertEqual(
            _(
                'An unavailability always busies its participants ; mark it as '
                '«all day» if you do not set the start/end times.'
            ),
            allday_f.help_text,
        )

        # ---
        title = 'Away'
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'user':  user.pk,
                'title': title,

                f'{self.EXTRA_START_KEY}_0': '2010-1-10',
                f'{self.EXTRA_START_KEY}_1': '09:08:07',

                f'{self.EXTRA_END_KEY}_0':  '2010-1-12',
                f'{self.EXTRA_END_KEY}_1': '06:05:04',

                self.EXTRA_PARTUSERS_KEY: [user.id, other_user.id],
            },
        )
        self.assertNoFormError(response2)

        act = self.get_object_or_fail(Activity, type=constants.ACTIVITYTYPE_INDISPO, title=title)
        self.assertIsNone(act.sub_type)
        self.assertIsNone(act.status)
        self.assertFalse(act.is_all_day)
        self.assertFalse(act.busy)

        get_cal = Calendar.objects.get_default_calendar
        self.assertCountEqual([get_cal(user), get_cal(other_user)], [*act.calendars.all()])

        create_dt = self.create_datetime
        self.assertEqual(
            create_dt(year=2010, month=1, day=10, hour=9, minute=8, second=7), act.start,
        )
        self.assertEqual(
            create_dt(year=2010, month=1, day=12, hour=6, minute=5, second=4), act.end,
        )

        self.assertRelationCount(
            1, user.linked_contact, constants.REL_SUB_PART_2_ACTIVITY, act,
        )
        self.assertRelationCount(
            1, other_user.linked_contact, constants.REL_SUB_PART_2_ACTIVITY, act,
        )

    def test_unavailability_createview03(self):
        "Is all day."
        user = self.login()

        title = 'AFK'
        subtype = ActivitySubType.objects.create(
            id='holidays', name='Holidays', type_id=constants.ACTIVITYTYPE_INDISPO,
        )
        response = self.client.post(
            self.ADD_INDISPO_URL,
            follow=True,
            data={
                'user':  user.pk,
                'title': title,
                'is_all_day': True,

                'cform_extra-activities_unavailability_subtype': subtype.id,

                f'{self.EXTRA_START_KEY}_0': '2010-1-10',
                f'{self.EXTRA_END_KEY}_0':   '2010-1-12',

                self.EXTRA_PARTUSERS_KEY: [user.id],
            },
        )
        self.assertNoFormError(response)

        act = self.get_object_or_fail(Activity, type=constants.ACTIVITYTYPE_INDISPO, title=title)
        self.assertEqual(subtype, act.sub_type)
        self.assertTrue(act.is_all_day)

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2010, month=1, day=10, hour=0,  minute=0),  act.start)
        self.assertEqual(create_dt(year=2010, month=1, day=12, hour=23, minute=59), act.end)

    def test_unavailability_createview04(self):
        "Start & end are required."
        user = self.login()

        response = self.assertPOST200(
            self.ADD_INDISPO_URL,
            follow=True,
            data={
                'user': user.pk,
                'title': 'AFK',
                self.EXTRA_PARTUSERS_KEY: [user.id],
            },
        )
        msg = _('This field is required.')
        self.assertFormError(response, 'form', self.EXTRA_START_KEY, msg)
        self.assertFormError(response, 'form', self.EXTRA_END_KEY,   msg)

    def test_unavailability_createview05(self):
        "Sub-type field is missing."
        user = self.login()

        # cfci = CustomFormConfigItem.objects.get(cform_id=UNAVAILABILITY_CREATION_FROM.id)
        cfci = CustomFormConfigItem.objects.get(descriptor_id=UNAVAILABILITY_CREATION_FROM.id)
        new_groups = FieldGroupList.from_cells(
            model=Activity,
            cell_registry=UNAVAILABILITY_CREATION_FROM.build_cell_registry(),
            data=[
                {
                    'name': 'Main',
                    'layout': LAYOUT_REGULAR,
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'title'}),

                        UnavailabilityStartSubCell(model=Activity).into_cell(),
                        UnavailabilityEndSubCell(model=Activity).into_cell(),
                        UnavailableUsersSubCell(model=Activity).into_cell(),
                    ],
                },
            ],
        )
        cfci.store_groups(new_groups)
        cfci.save()

        title = 'AFK'
        response = self.assertPOST200(
            self.ADD_INDISPO_URL,
            follow=True,
            data={
                'user': user.id,
                'title': title,

                f'{self.EXTRA_START_KEY}_0': '2020-11-17',
                f'{self.EXTRA_START_KEY}_1': '14:00:00',

                f'{self.EXTRA_END_KEY}_0': '2020-11-17',
                f'{self.EXTRA_END_KEY}_1': '17:30:00',

                self.EXTRA_PARTUSERS_KEY: [user.id],
            },
        )
        self.assertNoFormError(response)

        act = self.get_object_or_fail(Activity, type=constants.ACTIVITYTYPE_INDISPO, title=title)
        self.assertIsNone(act.sub_type)

    def test_detete_activity_type01(self):
        self.login()

        atype = ActivityType.objects.update_or_create(
            id='activities-activity_custom_1',
            defaults={
                'name':                 'Karate session',
                'default_day_duration':  0,
                'default_hour_duration': '00:15:00',
                'is_custom':             True,
            },
        )[0]
        response = self.client.post(reverse(
            'creme_config__delete_instance',
            args=('activities', 'activity_type', atype.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(ActivityType).job
        job.type.execute(job)
        self.assertDoesNotExist(atype)

    def test_detete_activity_type02(self):
        user = self.login()

        atype = ActivityType.objects.update_or_create(
            id='activities-activity_custom_1',
            defaults={
                'name':                 'Karate session',
                'default_day_duration':  0,
                'default_hour_duration': '00:15:00',
                'is_custom':             True,
            },
        )[0]

        Activity.objects.create(user=user, type=atype)

        response = self.assertPOST200(reverse(
            'creme_config__delete_instance',
            args=('activities', 'activity_type', atype.id),
        ))
        self.assertFormError(
            response, 'form',
            'replace_activities__activity_type',
            _('Deletion is not possible.'),
        )

    def test_dl_ical(self):
        user = self.login()

        create_act = partial(
            Activity.objects.create, user=user, type_id=constants.ACTIVITYTYPE_TASK, busy=True,
        )
        create_dt = self.create_datetime
        act1 = create_act(
            title='Act#1',
            start=create_dt(year=2013, month=4, day=1, hour=9),
            end=create_dt(year=2013,   month=4, day=1, hour=10),
        )
        act2 = create_act(
            title='Act#2',
            start=create_dt(year=2013, month=4, day=2, hour=9),
            end=create_dt(year=2013,   month=4, day=2, hour=10),
        )

        response = self.assertGET200(
            reverse('activities__dl_ical'), data={'id': [act1.id, act2.id]},
        )
        self.assertEqual('text/calendar', response['Content-Type'])
        # self.assertEqual('attachment; filename=Calendar.ics', response['Content-Disposition'])
        self.assertEqual('attachment; filename="Calendar.ics"', response['Content-Disposition'])

        # content = force_text(response.content)
        content = force_str(response.content)
        self.assertStartsWith(
            content,
            'BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//CremeCRM//CremeCRM//EN\n'
            'BEGIN:VEVENT\n'
            'UID:http://cremecrm.com\n'
        )
        self.assertIn(
            f'SUMMARY:Act#2\n'
            f'DTSTART:20130402T090000Z\n'
            f'DTEND:20130402T100000Z\n'
            f'LOCATION:\n'
            f'CATEGORIES:{act2.type.name}\n'
            f'STATUS:\n'
            f'END:VEVENT\n',
            content,
        )
        self.assertIn('SUMMARY:Act#1\n', content)
        self.assertEndsWith(content, 'END:VCALENDAR')

    def test_clone01(self):
        self.login()

        activity1 = self._create_meeting()
        activity2 = activity1.clone()
        self.assertNotEqual(activity1.pk, activity2.pk)

        for attr in (
            'user', 'title', 'start', 'end', 'description', 'minutes',
            'type', 'sub_type', 'is_all_day', 'status', 'busy',
        ):
            self.assertEqual(getattr(activity1, attr), getattr(activity2, attr))

    @skipIfCustomContact
    def test_clone02(self):
        user = self.login()

        rtype_participant = RelationType.objects.get(pk=constants.REL_SUB_PART_2_ACTIVITY)

        create_dt = self.create_datetime
        activity1 = Activity.objects.create(
            user=user, type_id=constants.ACTIVITYTYPE_MEETING,
            title='Meeting', description='Desc',
            start=create_dt(year=2015, month=3, day=20, hour=9),
            end=create_dt(year=2015, month=3, day=20, hour=11),
            is_all_day=False, busy=True,
            place='Here', minutes='123',
            status=Status.objects.all()[0],
        )

        create_contact = partial(Contact.objects.create, user=user, last_name='Saotome')
        create_rel = partial(
            Relation.objects.create, user=user, type=rtype_participant, object_entity=activity1,
        )
        create_rel(subject_entity=create_contact(first_name='Ranma'))
        create_rel(subject_entity=create_contact(first_name='Genma'))

        activity2 = activity1.clone().clone().clone().clone().clone().clone().clone()
        self.assertNotEqual(activity1.pk, activity2.pk)

        for attr in (
            'user', 'title', 'start', 'end', 'description', 'minutes',
            'type', 'sub_type', 'is_all_day', 'status', 'place'
        ):
            self.assertEqual(getattr(activity1, attr), getattr(activity2, attr))

        self.assertNotEqual(activity1.busy, activity2.busy)
        self.assertSameRelationsNProperties(activity1, activity2, exclude_internal=False)

    def test_manager_future_linked(self):
        user = self.login()
        create_dt = self.create_datetime
        today = create_dt(year=2019, month=8, day=26, hour=8)

        rtype1 = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
        )[0]

        create_activity = partial(
            Activity.objects.create, user=user,
            type_id=constants.ACTIVITYTYPE_MEETING,
            start=today + timedelta(hours=3),
            end=today + timedelta(hours=4),
        )
        activity1 = create_activity(title='Meeting#1')
        create_activity(title='Meeting#2')  # No relation
        activity3 = create_activity(title='Meeting#3')  # Ignored type of relation
        activity4 = create_activity(title='Meeting#4', is_deleted=True)
        activity5 = create_activity(
            title='Meeting#5',
            start=today - timedelta(hours=15),
            end=today   - timedelta(hours=14),
        )  # In the past
        activity6 = create_activity(
            title='Meeting#6',
            start=today + timedelta(hours=1),
            end=today + timedelta(hours=2),
        )

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Ranma', last_name='Saotome')
        c2 = create_contact(first_name='Genma', last_name='Saotome')

        create_orga = partial(Organisation.objects.create, user=user)
        o1 = create_orga(name='Saotome dojo')
        o2 = create_orga(name='Tendou dojo')

        create_rel = partial(
            Relation.objects.create,
            user=user, object_entity=activity1, type_id=constants.REL_SUB_PART_2_ACTIVITY,
        )

        create_rel(subject_entity=c1)
        # Second relation on the same activity => return once
        create_rel(subject_entity=c1, type_id=constants.REL_SUB_ACTIVITY_SUBJECT)
        create_rel(subject_entity=o1, type_id=constants.REL_SUB_ACTIVITY_SUBJECT)
        create_rel(subject_entity=o2, type_id=constants.REL_SUB_LINKED_2_ACTIVITY)
        create_rel(subject_entity=c2, type_id=rtype1.id, object_entity=activity3)
        create_rel(subject_entity=c1, object_entity=activity4)
        create_rel(subject_entity=c1, object_entity=activity5)
        create_rel(subject_entity=c1, object_entity=activity6)

        self.assertListEqual(
            [activity6, activity1],
            [*Activity.objects.future_linked(entity=c1, today=today)]
        )
        self.assertListEqual(
            [activity1],
            [*Activity.objects.future_linked(entity=o1, today=today)]
        )
        self.assertListEqual(
            [activity1],
            [*Activity.objects.future_linked(entity=o2, today=today)]
        )
        self.assertFalse(Activity.objects.future_linked(entity=c2, today=today))

    def test_manager_past_linked(self):
        user = self.login()
        create_dt = self.create_datetime
        today = create_dt(year=2019, month=8, day=26, hour=8)

        rtype1 = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
        )[0]

        create_activity = partial(
            Activity.objects.create, user=user,
            type_id=constants.ACTIVITYTYPE_MEETING,
            start=today - timedelta(hours=24),
            end=today - timedelta(hours=23),
        )
        activity1 = create_activity(title='Meeting#1')
        create_activity(title='Meeting#2')  # No relation
        activity3 = create_activity(title='Meeting#3')  # Ignored type of relation
        activity4 = create_activity(title='Meeting#4', is_deleted=True)
        activity5 = create_activity(
            title='Meeting#5',
            start=today + timedelta(hours=4),
            end=today + timedelta(hours=5),
        )  # In the future
        activity6 = create_activity(
            title='Meeting#6',
            start=today - timedelta(hours=15),
            end=today   - timedelta(hours=14),
        )

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Ranma', last_name='Saotome')
        c2 = create_contact(first_name='Genma', last_name='Saotome')

        create_orga = partial(Organisation.objects.create, user=user)
        o1 = create_orga(name='Saotome dojo')
        o2 = create_orga(name='Tendou dojo')

        create_rel = partial(
            Relation.objects.create,
            user=user, object_entity=activity1, type_id=constants.REL_SUB_PART_2_ACTIVITY,
        )

        create_rel(subject_entity=c1)
        # Second relation on the same activity => return once
        create_rel(subject_entity=c1, type_id=constants.REL_SUB_ACTIVITY_SUBJECT)
        create_rel(subject_entity=o1, type_id=constants.REL_SUB_ACTIVITY_SUBJECT)
        create_rel(subject_entity=o2, type_id=constants.REL_SUB_LINKED_2_ACTIVITY)
        create_rel(subject_entity=c2, type_id=rtype1.id, object_entity=activity3)
        create_rel(subject_entity=c1, object_entity=activity4)
        create_rel(subject_entity=c1, object_entity=activity5)
        create_rel(subject_entity=c1, object_entity=activity6)

        self.assertListEqual(
            [activity6, activity1],
            [*Activity.objects.past_linked(entity=c1, today=today)],
        )
        self.assertListEqual(
            [activity1],
            [*Activity.objects.past_linked(entity=o1, today=today)],
        )
        self.assertListEqual(
            [activity1],
            [*Activity.objects.past_linked(entity=o2, today=today)],
        )
        self.assertFalse(Activity.objects.past_linked(entity=c2, today=today))

    def test_manager_future_linked_to_organisation(self):
        user = self.login()

        sv = self.get_object_or_fail(SettingValue, key_id=constants.SETTING_AUTO_ORGA_SUBJECTS)
        sv.value = False  # We disable the auto subjects feature
        sv.save()

        create_dt = self.create_datetime
        today = create_dt(year=2019, month=8, day=26, hour=8)

        rtype1 = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
        )[0]

        create_activity = partial(
            Activity.objects.create,
            user=user,
            type_id=constants.ACTIVITYTYPE_MEETING,
            start=today + timedelta(hours=3),
            end=today   + timedelta(hours=4),
        )
        activity1 = create_activity(title='Meeting#1')
        activity2 = create_activity(title='Meeting#2')
        activity3 = create_activity(title='Meeting#3')
        activity4 = create_activity(title='Meeting#4', is_deleted=True)
        activity5 = create_activity(
            title='Meeting#5',
            start=today - timedelta(hours=15),
            end=today   - timedelta(hours=14),
        )  # In the past => ignored
        activity6 = create_activity(
            title='Meeting#6',
            start=today + timedelta(hours=1),
            end=today   + timedelta(hours=2),
        )  # Before <activity1> when ordering by 'start'
        activity7 = create_activity(title='Meeting#2')

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Saotome dojo')
        orga2 = create_orga(name='Tendou dojo')
        orga3 = create_orga(name='Hibiki dojo')
        orga4 = create_orga(name='Happosai dojo')

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Ranma', last_name='Saotome')
        c2 = create_contact(first_name='Ryoga', last_name='Hibiki')
        c3 = create_contact(first_name='Akane', last_name='Tendou')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=c1, type_id=REL_SUB_EMPLOYED_BY, object_entity=orga2)
        create_rel(subject_entity=c2, type_id=REL_SUB_MANAGES,     object_entity=orga3)
        create_rel(subject_entity=c3, type_id=REL_SUB_EMPLOYED_BY, object_entity=orga4)

        SUBJECT = constants.REL_SUB_ACTIVITY_SUBJECT

        # About <orga1> ---
        create_rel(
            subject_entity=orga1, type_id=SUBJECT,  object_entity=activity1,
        )
        # Ignored type of relation
        create_rel(subject_entity=orga1, type_id=rtype1.id, object_entity=activity3)
        create_rel(subject_entity=orga1, type_id=SUBJECT, object_entity=activity4)
        create_rel(subject_entity=orga1, type_id=SUBJECT, object_entity=activity5)
        create_rel(subject_entity=orga1, type_id=SUBJECT, object_entity=activity6)

        # About <orga2> ---
        create_rel(
            subject_entity=c1,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
            object_entity=activity2,
        )

        # About <orga3> ---
        create_rel(
            subject_entity=c2,
            type_id=constants.REL_SUB_LINKED_2_ACTIVITY,
            object_entity=activity3,
        )

        # About <orga4> (2 relationships on the same activity => return only one)
        create_rel(subject_entity=orga4, type_id=SUBJECT, object_entity=activity7)
        create_rel(
            subject_entity=c3,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
            object_entity=activity7,
        )

        self.assertListEqual(
            [activity6, activity1],
            [*Activity.objects.future_linked_to_organisation(orga1, today=today)]
        )

        self.assertFalse(Relation.objects.filter(subject_entity=activity2, object_entity=orga2))
        self.assertListEqual(
            [activity2],
            [*Activity.objects.future_linked_to_organisation(orga=orga2, today=today)],
        )

        self.assertListEqual(
            [activity3],
            [*Activity.objects.future_linked_to_organisation(orga=orga3, today=today)],
        )

        self.assertListEqual(
            [activity7],
            [*Activity.objects.future_linked_to_organisation(orga=orga4, today=today)],
        )

    def test_manager_past_linked_to_organisation(self):
        user = self.login()

        sv = self.get_object_or_fail(SettingValue, key_id=constants.SETTING_AUTO_ORGA_SUBJECTS)
        sv.value = False  # We disable the auto subjects feature
        sv.save()

        create_dt = self.create_datetime
        today = create_dt(year=2019, month=8, day=26, hour=8)

        rtype1 = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by')
        )[0]

        create_activity = partial(
            Activity.objects.create,
            user=user,
            type_id=constants.ACTIVITYTYPE_MEETING,
            start=today - timedelta(hours=16),
            end=today   - timedelta(hours=15),
        )
        activity1 = create_activity(title='Meeting#1')
        activity2 = create_activity(title='Meeting#2')
        activity3 = create_activity(title='Meeting#3')
        activity4 = create_activity(title='Meeting#4', is_deleted=True)
        activity5 = create_activity(
            title='Meeting#5',
            start=today + timedelta(hours=1),
            end=today   + timedelta(hours=2),
        )  # In the Future => ignored
        activity6 = create_activity(
            title='Meeting#6',
            start=today - timedelta(hours=15),
            end=today   - timedelta(hours=14),
        )  # Before <activity1> when ordering by '-start'
        activity7 = create_activity(title='Meeting#2')

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Saotome dojo')
        orga2 = create_orga(name='Tendou dojo')
        orga3 = create_orga(name='Hibiki dojo')
        orga4 = create_orga(name='Happosai dojo')

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Ranma', last_name='Saotome')
        c2 = create_contact(first_name='Ryoga', last_name='Hibiki')
        c3 = create_contact(first_name='Akane', last_name='Tendou')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=c1, type_id=REL_SUB_EMPLOYED_BY, object_entity=orga2)
        create_rel(subject_entity=c2, type_id=REL_SUB_MANAGES,     object_entity=orga3)
        create_rel(subject_entity=c3, type_id=REL_SUB_EMPLOYED_BY, object_entity=orga4)

        SUBJECT = constants.REL_SUB_ACTIVITY_SUBJECT

        # About <orga1> ---
        create_rel(subject_entity=orga1, type_id=SUBJECT,  object_entity=activity1)
        create_rel(subject_entity=orga1, type_id=rtype1.id, object_entity=activity3)
        # Ignored type of relation
        create_rel(subject_entity=orga1, type_id=SUBJECT,  object_entity=activity4)
        create_rel(subject_entity=orga1, type_id=SUBJECT,  object_entity=activity5)
        create_rel(subject_entity=orga1, type_id=SUBJECT,  object_entity=activity6)

        # About <orga2> ---
        create_rel(
            subject_entity=c1,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
            object_entity=activity2,
        )

        # About <orga3> ---
        create_rel(
            subject_entity=c2,
            type_id=constants.REL_SUB_LINKED_2_ACTIVITY,
            object_entity=activity3,
        )

        # About <orga4> (2 relationships on the same activity => return only one)
        create_rel(
            subject_entity=orga4,
            type_id=SUBJECT,
            object_entity=activity7,
        )
        create_rel(
            subject_entity=c3,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
            object_entity=activity7,
        )

        self.assertListEqual(
            [activity6, activity1],
            [*Activity.objects.past_linked_to_organisation(orga1, today=today)]
        )

        self.assertFalse(Relation.objects.filter(subject_entity=activity2, object_entity=orga2))
        self.assertListEqual(
            [activity2],
            [*Activity.objects.past_linked_to_organisation(orga=orga2, today=today)],
        )

        self.assertListEqual(
            [activity3],
            [*Activity.objects.past_linked_to_organisation(orga=orga3, today=today)],
        )

        self.assertListEqual(
            [activity7],
            [*Activity.objects.past_linked_to_organisation(orga=orga4, today=today)],
        )
