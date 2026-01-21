import uuid
from datetime import date, time
from functools import partial

from django.apps import apps
from django.forms import ModelMultipleChoiceField
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.activities import constants, setting_keys
from creme.activities.custom_forms import ACTIVITY_CREATION_CFORM
from creme.activities.forms.activity import (
    ActivitySubTypeSubCell,
    MyParticipationSubCell,
    UnavailabilityTypeSubCell,
    UserMessagesSubCell,
)
from creme.activities.forms.fields import ActivitySubTypeField
from creme.activities.models import (
    ActivitySubType,
    ActivityType,
    Calendar,
    Status,
)
from creme.activities.tests.base import (
    Activity,
    Contact,
    Organisation,
    _ActivitiesTestCase,
    skipIfCustomActivity,
)
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.forms import LAYOUT_REGULAR, ReadonlyMessageField
from creme.creme_core.forms.widgets import Label
from creme.creme_core.gui.custom_form import FieldGroup, FieldGroupList
from creme.creme_core.models import (
    CustomFormConfigItem,
    Relation,
    RelationType,
    SettingValue,
)
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.creme_core.utils.date_period import DaysPeriod
from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

if apps.is_installed('creme.assistants'):
    from creme.assistants.constants import UUID_PRIORITY_NOT_IMPORTANT
    from creme.assistants.models import Alert, UserMessage


@skipIfCustomActivity
class ActivityCreationTestCase(_ActivitiesTestCase):
    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_narrow(self):
        user = self.login_as_root_and_get()
        other_user = self.create_user()

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
        response1 = self.assertGET200(url, headers={'referer': f'http://testserver{lv_url}'})

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
        sub_type = ActivitySubType.objects.get(uuid=constants.UUID_SUBTYPE_MEETING_MEETING)
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'user':  user.pk,
                'title': title,

                self.EXTRA_SUBTYPE_KEY: sub_type.id,
                'status':               status.pk,

                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2010, 1, 10),
                f'{self.EXTRA_START_KEY}_1': '17:30:00',
                f'{self.EXTRA_END_KEY}_0':   self.formfield_value_date(2010, 1, 10),
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

        act = self.get_object_or_fail(Activity, title=title)
        self.assertEqual(sub_type, act.sub_type)
        self.assertEqual(sub_type.type_id, act.type_id)
        self.assertEqual(status, act.status)
        # self.assertEqual(constants.NARROW, act.floating_type)  # DEPRECATED
        self.assertEqual(Activity.FloatingType.NARROW, act.floating_type)
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
        self.assertHaveRelation(user.linked_contact,       REL_SUB_PART_2_ACTIVITY, act)
        self.assertHaveRelation(genma,                     REL_SUB_PART_2_ACTIVITY, act)
        self.assertHaveRelation(other_user.linked_contact, REL_SUB_PART_2_ACTIVITY, act)
        self.assertHaveRelation(ranma, constants.REL_SUB_ACTIVITY_SUBJECT,  act)
        self.assertHaveRelation(dojo,  constants.REL_SUB_LINKED_2_ACTIVITY, act)

        # * 2: relations have their symmetric ones
        self.assertEqual(5 * 2, Relation.objects.count())

        self.assertRedirects(response2, act.get_absolute_url())
        self.assertTemplateUsed(response2, 'activities/view_activity.html')

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_permissions(self):
        "Credentials errors."
        user = self.login_as_activities_user(creatable_models=[Activity])
        self.add_credentials(user.role, own=['LINK'], all='!LINK')

        other_user = self.get_root_user()

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

                self.EXTRA_SUBTYPE_KEY: self._get_sub_type(
                    constants.UUID_SUBTYPE_MEETING_QUALIFICATION
                ).id,

                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2011, 2, 22),

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,

                self.EXTRA_PARTUSERS_KEY: [other_user.pk],
                self.EXTRA_OTHERPART_KEY: self.formfield_value_multi_creator_entity(genma),
                self.EXTRA_SUBJECTS_KEY:  self.formfield_value_multi_generic_entity(akane),
                self.EXTRA_LINKED_KEY:    self.formfield_value_multi_generic_entity(dojo),
            },
        )

        form = self.get_form_or_fail(response)
        self.assertFormError(
            form,
            field=self.EXTRA_MYPART_KEY,
            errors=_('You are not allowed to link this entity: {}').format(mireille),
        )

        fmt = _('Some entities are not linkable: {}').format
        self.assertFormError(
            form, field=self.EXTRA_PARTUSERS_KEY, errors=fmt(other_user.linked_contact),
        )
        self.assertFormError(form, field=self.EXTRA_OTHERPART_KEY, errors=fmt(genma))
        self.assertFormError(form, field=self.EXTRA_SUBJECTS_KEY,  errors=fmt(akane))
        self.assertFormError(form, field=self.EXTRA_LINKED_KEY,    errors=fmt(dojo))

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_no_end(self):
        "No end given; auto subjects."
        user = self.login_as_root_and_get()
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
        dojo_t  = create_orga(name='Tendo Dojo')
        dojo_s  = create_orga(name='Saotome Dojo')
        school  = create_orga(name='Furinkan High')
        rest    = create_orga(name='Okonomiyaki tenshi')
        deleted = create_orga(name='Deleted', is_deleted=True)

        mngd = Organisation.objects.filter_managed_by_creme()[0]

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=me,    type_id=REL_SUB_EMPLOYED_BY, object_entity=mngd)
        create_rel(subject_entity=ranma, type_id=REL_SUB_EMPLOYED_BY, object_entity=dojo_s)
        create_rel(subject_entity=akane, type_id=REL_SUB_EMPLOYED_BY, object_entity=school)
        create_rel(subject_entity=akane, type_id=REL_SUB_EMPLOYED_BY, object_entity=dojo_t)
        create_rel(subject_entity=akane, type_id=REL_SUB_EMPLOYED_BY, object_entity=deleted)
        # 2 employees for the same organisations:
        create_rel(subject_entity=genma, type_id=REL_SUB_MANAGES,     object_entity=school)
        create_rel(subject_entity=genma, type_id=REL_SUB_EMPLOYED_BY, object_entity=rest)

        title = 'My training'
        status = Status.objects.all()[0]
        my_calendar = Calendar.objects.get_default_calendar(user)
        a_type = ActivityType.objects.create(
            name='Karate session',
            default_day_duration=1,
            default_hour_duration='00:15:00',
            is_custom=True,
        )
        sub_type = ActivitySubType.objects.create(
            type=a_type,
            name='Kick session',
            is_custom=True,
        )
        response2 = self.client.post(
            self.ACTIVITY_CREATION_URL,
            follow=True,
            data={
                'user':   user.id,
                'title':  title,
                'status': status.pk,

                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2013, 3, 26),
                f'{self.EXTRA_START_KEY}_1': '12:10:00',

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,

                self.EXTRA_OTHERPART_KEY: self.formfield_value_multi_creator_entity(genma, akane),
                self.EXTRA_SUBJECTS_KEY:  self.formfield_value_multi_generic_entity(ranma, rest),
                self.EXTRA_LINKED_KEY:    self.formfield_value_multi_generic_entity(dojo_s),

                self.EXTRA_SUBTYPE_KEY: sub_type.id,
            },
        )
        self.assertNoFormError(response2)

        act = self.get_object_or_fail(Activity, type=a_type, title=title)
        self.assertEqual(status, act.status)

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2013, month=3, day=26, hour=12, minute=10), act.start)
        self.assertEqual(create_dt(year=2013, month=3, day=27, hour=12, minute=25), act.end)

        PARTICIPATES = constants.REL_SUB_PART_2_ACTIVITY
        SUBJECT = constants.REL_SUB_ACTIVITY_SUBJECT
        LINKED = constants.REL_SUB_LINKED_2_ACTIVITY
        self.assertHaveRelation(subject=me,     type=PARTICIPATES,   object=act)
        self.assertHaveRelation(subject=genma,  type=PARTICIPATES,   object=act)
        self.assertHaveRelation(subject=akane,  type=PARTICIPATES,   object=act)
        self.assertHaveRelation(subject=ranma,  type=SUBJECT,        object=act)
        self.assertHaveRelation(subject=dojo_s, type=LINKED,         object=act)
        self.assertHaveNoRelation(subject=dojo_s, type=SUBJECT, object=act)
        # Auto subject #1 & #2
        self.assertHaveRelation(subject=dojo_t, type=SUBJECT, object=act)
        self.assertHaveRelation(subject=school, type=SUBJECT, object=act)
        # No auto subject with managed organisations
        self.assertHaveNoRelation(subject=mngd, type=SUBJECT, object=act)
        # Auto subject #3 (no duplicate error)
        self.assertHaveRelation(subject=rest, type=SUBJECT, object=act)
        # No auto subject with deleted organisations
        self.assertHaveNoRelation(subject=deleted, type=SUBJECT, object=act)

        self.assertEqual(8, Relation.objects.filter(subject_entity=act.id).count())

    def test_no_end__end_time(self):
        "No end but end time."
        user = self.login_as_root_and_get()
        act = self._create_activity_by_view(
            user=user,
            **{
                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2013, 3, 29),
                f'{self.EXTRA_START_KEY}_1': '14:30:00',
                f'{self.EXTRA_END_KEY}_1': '15:45:00',
            }
        )
        create_dt = partial(self.create_datetime, year=2013, month=3, day=29)
        self.assertEqual(create_dt(hour=14, minute=30), act.start)
        self.assertEqual(create_dt(hour=15, minute=45), act.end)

    def test_floating(self):
        "FLOATING type."
        user = self.login_as_root_and_get()
        act = self._create_activity_by_view(user=user)
        self.assertIsNone(act.start)
        self.assertIsNone(act.end)
        # self.assertEqual(constants.FLOATING, act.floating_type)  # DEPRECATED
        self.assertEqual(Activity.FloatingType.FLOATING, act.floating_type)

    def test_floating_time(self):
        "FLOATING_TIME type."
        user = self.login_as_root_and_get()
        act = self._create_activity_by_view(
            user=user,
            **{
                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2013, 3, 30),
                f'{self.EXTRA_END_KEY}_0':   self.formfield_value_date(2013, 3, 30),
            }
        )
        create_dt = partial(self.create_datetime, year=2013, month=3, day=30)
        self.assertEqual(create_dt(hour=0,  minute=0),  act.start)
        self.assertEqual(create_dt(hour=23, minute=59), act.end)
        # self.assertEqual(constants.FLOATING_TIME, act.floating_type)  # DEPRECATED
        self.assertEqual(Activity.FloatingType.FLOATING_TIME, act.floating_type)

    def test_default_duration__day1_floating_time(self):
        "default_day_duration=1 + FLOATING_TIME."
        user = self.login_as_root_and_get()

        atype = self._get_type(constants.UUID_TYPE_SHOW)
        self.assertEqual(1,          atype.default_day_duration)
        self.assertEqual('00:00:00', atype.default_hour_duration)

        act = self._create_activity_by_view(
            user=user,
            title='TGS',
            sub_type=ActivitySubType.objects.filter(type=atype).first(),
            **{f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2013, 7, 3)}
        )

        create_dt = partial(self.create_datetime, year=2013, month=7, day=3)
        self.assertEqual(create_dt(hour=0,  minute=0),  act.start)
        self.assertEqual(create_dt(hour=23, minute=59), act.end)

    def test_default_duration__day1_all_day(self):
        "default_day_duration=1 + is_all_day."
        user = self.login_as_root_and_get()

        atype = self._get_type(constants.UUID_TYPE_SHOW)
        self.assertEqual(1, atype.default_day_duration)
        self.assertEqual('00:00:00', atype.default_hour_duration)

        act = self._create_activity_by_view(
            user=user,
            title='TGS',
            subtype=ActivitySubType.objects.filter(type=atype).first(),
            is_all_day=True,
            **{f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2013, 7, 3)}
        )

        create_dt = partial(self.create_datetime, year=2013, month=7, day=3)
        self.assertEqual(create_dt(hour=0,  minute=0),  act.start)
        self.assertEqual(create_dt(hour=23, minute=59), act.end)

    def test_default_duration__day15_floating_time(self):
        "default_duration = 1.5 day + FLOATING_TIME."
        user = self.login_as_root_and_get()

        atype = ActivityType.objects.create(
            name='Big Show',
            default_day_duration=1,
            default_hour_duration='12:00:00',
            is_custom=True,
        )
        sub_type = ActivitySubType.objects.create(
            name='Big Show for Open source',
            type=atype,
            is_custom=True,
        )

        act = self._create_activity_by_view(
            user=user,
            title='TGS',
            subtype=sub_type,
            **{f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2013, 7, 3)}
        )

        create_dt = partial(self.create_datetime, year=2013, month=7)
        self.assertEqual(create_dt(day=3, hour=0,  minute=0),  act.start)
        self.assertEqual(create_dt(day=4, hour=23, minute=59), act.end)

    def test_default_duration__day0_floating_time(self):
        "default_duration = 0 + FLOATING_TIME."
        user = self.login_as_root_and_get()

        atype = ActivityType.objects.create(
            name='Big Show',
            default_day_duration=0,
            default_hour_duration='00:00:00',
            is_custom=True,
        )
        sub_type = ActivitySubType.objects.create(
            name='Big Show for Open source',
            type=atype,
            is_custom=True,
        )

        act = self._create_activity_by_view(
            user=user,
            title='TGS',
            subtype=sub_type,
            **{f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2013, 7, 3)}
        )

        create_dt = partial(self.create_datetime, year=2013, month=7, day=3)
        self.assertEqual(create_dt(hour=0,  minute=0),  act.start)
        self.assertEqual(create_dt(hour=23, minute=59), act.end)

    @skipIfCustomOrganisation
    def test_no_auto_subjects(self):
        user = self.login_as_root_and_get()
        me = user.linked_contact

        sv = self.get_object_or_fail(SettingValue, key_id=setting_keys.auto_subjects_key.id)
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

                self.EXTRA_SUBTYPE_KEY: self._get_sub_type(
                    constants.UUID_SUBTYPE_MEETING_MEETING,
                ).id,

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,
            },
        )
        self.assertNoFormError(response2)

        act = self.get_object_or_fail(Activity, title=title)
        self.assertHaveRelation(subject=me, type=constants.REL_SUB_PART_2_ACTIVITY, object=act)
        self.assertHaveNoRelation(
            subject=dojo, type=constants.REL_SUB_ACTIVITY_SUBJECT, object=act,
        )

        # Better in a teardown method...
        sv.value = True
        sv.save()

    def test_teams(self):
        "Teams as participants are replaced by their teammates."
        user1 = self.login_as_root_and_get()
        user2 = self.create_user(0)
        user3 = self.create_user(1)
        team = self.create_team('Soldats', user2, user3, user1)  # TODO: user + my_participation

        title = 'Fight !!'
        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_QUALIFICATION)
        response = self.client.post(
            self.ACTIVITY_CREATION_URL, follow=True,
            data={
                'user':  user1.pk,
                'title': title,

                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2015, 3, 10),

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': Calendar.objects.get_default_calendar(user1).pk,

                self.EXTRA_PARTUSERS_KEY: [team.id],

                self.EXTRA_SUBTYPE_KEY: sub_type.id,
            },
        )
        self.assertNoFormError(response)

        act = self.get_object_or_fail(Activity, title=title)
        relations = Relation.objects.filter(
            subject_entity=act.id, type=constants.REL_OBJ_PART_2_ACTIVITY,
        )
        self.assertCountEqual(
            [user2.linked_contact, user3.linked_contact, user1.linked_contact],
            [r.real_object for r in relations],
        )

    def test_light_custom_form(self):
        "Start/end fields are missing."
        user = self.login_as_root_and_get()

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

        act = self._create_activity_by_view(user=user, title='TGS')

        self.assertIsNone(act.start)
        self.assertIsNone(act.end)
        # self.assertEqual(constants.FLOATING, act.floating_type)
        self.assertEqual(Activity.FloatingType.FLOATING, act.floating_type)

    @skipIfCustomOrganisation
    def test_disabled_rtype(self):
        user = self.login_as_root_and_get()
        dojo = Organisation.objects.create(user=user, name='Dojo')
        def_calendar = Calendar.objects.get_default_calendar(user)

        rtype = self.get_object_or_fail(RelationType, id=constants.REL_SUB_LINKED_2_ACTIVITY)
        rtype.enabled = False
        rtype.save()

        url = self.ACTIVITY_CREATION_URL

        try:
            # GET ---
            response1 = self.assertGET200(url)

            with self.assertNoException():
                linked_f = response1.context['form'].fields[self.EXTRA_LINKED_KEY]

            self.assertIsInstance(linked_f, ReadonlyMessageField)
            self.assertIsInstance(linked_f.widget, Label)
            self.assertEqual(
                _(
                    "The relationship type «{predicate}» is disabled; "
                    "re-enable it if it's still useful, "
                    "or remove this form-field in the forms configuration."
                ).format(predicate=_('related to the activity')),
                linked_f.initial,
            )

            # POST ---
            title = 'My task'
            sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER)
            other_contact = Contact.objects.create(
                user=user, first_name='Ranma', last_name='Saotome',
            )
            response2 = self.client.post(
                url,
                follow=True,
                data={
                    'user':  user.pk,
                    'title': title,
                    'status': Status.objects.all()[0].pk,

                    self.EXTRA_SUBTYPE_KEY: sub_type.id,

                    f'{self.EXTRA_MYPART_KEY}_0': True,
                    f'{self.EXTRA_MYPART_KEY}_1': def_calendar.pk,

                    self.EXTRA_SUBJECTS_KEY:  self.formfield_value_multi_generic_entity(dojo),

                    # Should not be used
                    self.EXTRA_LINKED_KEY: self.formfield_value_multi_generic_entity(
                        other_contact,
                    ),
                },
            )

            self.assertNoFormError(response2)

            act = self.get_object_or_fail(Activity, sub_type=sub_type, title=title)
            self.assertHaveRelation(
                subject=user.linked_contact, type=constants.REL_SUB_PART_2_ACTIVITY, object=act,
            )
            self.assertHaveRelation(
                subject=dojo, type=constants.REL_SUB_ACTIVITY_SUBJECT, object=act,
            )
            self.assertHaveNoRelation(
                subject=other_contact, type=constants.REL_SUB_LINKED_2_ACTIVITY, object=act,
            )
        finally:
            rtype.enabled = True
            rtype.save()

    @skipIfCustomContact
    def test_is_staff(self):
        user = self.login_as_super(is_staff=True)
        root = self.get_root_user()

        def_calendar = Calendar.objects.get_default_calendar(user)

        # GET ---
        url = self.ACTIVITY_CREATION_URL
        self.assertGET200(url)

        # ---
        title = 'My task'
        sub_type = ActivitySubType.objects.get(uuid=constants.UUID_SUBTYPE_MEETING_MEETING)
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'user':  root.id,
                'title': title,

                self.EXTRA_SUBTYPE_KEY: sub_type.id,
                'status':               Status.objects.all()[0].id,

                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2023, 12, 11),
                f'{self.EXTRA_START_KEY}_1': '17:00:00',

                # Should not be used
                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': def_calendar.pk,

                self.EXTRA_PARTUSERS_KEY: [root.id],
            },
        )
        self.assertNoFormError(response2)

        act = self.get_object_or_fail(Activity, title=title)
        self.assertEqual(sub_type, act.sub_type)
        self.assertEqual(sub_type.type_id, act.type_id)

        self.assertCountEqual(
            [Calendar.objects.get_default_calendar(root)],
            [*act.calendars.all()],
        )

    def test_errors(self):
        user = self.login_as_root_and_get()
        data = {
            'user': user.pk,
            'title': 'My task',

            self.EXTRA_SUBTYPE_KEY: self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER).id,

            f'{self.EXTRA_END_KEY}_0': self.formfield_value_date(2013, 3, 29),

            f'{self.EXTRA_MYPART_KEY}_0': True,
            f'{self.EXTRA_MYPART_KEY}_1': Calendar.objects.get_default_calendar(user).pk,
        }
        url = self.ACTIVITY_CREATION_URL

        response1 = self.assertPOST200(url, follow=True, data=data)
        self.assertFormError(
            response1.context['form'],
            field=None,
            errors=_("You can't set the end of your activity without setting its start"),
        )

        response2 = self.assertPOST200(
            url, follow=True,
            data={**data, f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2013, 3, 30)},
        )
        self.assertFormError(
            response2.context['form'], field=None, errors=_('End is before start'),
        )

        response3 = self.assertPOST200(
            url,
            follow=True,
            data={
                **data,
                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2013, 3, 29),
                'busy': True,
            },
        )
        self.assertFormError(
            response3.context['form'],
            field=None,
            errors=_("A floating on the day activity can't busy its participants"),
        )

    def test_errors__rtype_constraint(self):
        "RelationType constraint error."
        user = self.login_as_root_and_get()

        bad_subject = self._create_meeting(user=user)
        response = self.assertPOST200(
            self.ACTIVITY_CREATION_URL, follow=True,
            data={
                'user': user.pk,
                'title': 'My task',

                self.EXTRA_SUBTYPE_KEY: self._get_sub_type(
                    constants.UUID_SUBTYPE_MEETING_MEETING
                ).id,

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': Calendar.objects.get_default_calendar(user).pk,

                self.EXTRA_SUBJECTS_KEY: self.formfield_value_multi_generic_entity(bad_subject),
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=self.EXTRA_SUBJECTS_KEY,
            errors=_('This content type is not allowed.'),
        )

    @skipIfCustomContact
    def test_errors__user_participants(self):
        "other_participants contains contact related to user."
        user = self.login_as_root_and_get()

        ranma = Contact.objects.create(user=user, first_name='Ranma', last_name='Saotome')
        other = self.create_user().linked_contact
        response = self.assertPOST200(
            self.ACTIVITY_CREATION_URL, follow=True,
            data={
                'user':  user.id,
                'title': 'My task',

                self.EXTRA_SUBTYPE_KEY: self._get_sub_type(
                    constants.UUID_SUBTYPE_MEETING_MEETING
                ).id,

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': Calendar.objects.get_default_calendar(user).pk,

                self.EXTRA_SUBJECTS_KEY:  self.formfield_value_multi_generic_entity(ranma),

                self.EXTRA_OTHERPART_KEY: self.formfield_value_multi_creator_entity(other),
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=self.EXTRA_OTHERPART_KEY,
            errors=_('«%(entity)s» violates the constraints.') % {'entity': other},
        )

    def test_errors__participating_logged_user(self):
        "participating_users contains request.user."
        user = self.login_as_root_and_get()

        response = self.assertPOST200(
            self.ACTIVITY_CREATION_URL,
            follow=True,
            data={
                'user':  user.id,
                'title': 'My task',

                self.EXTRA_SUBTYPE_KEY: self._get_sub_type(
                    constants.UUID_SUBTYPE_MEETING_MEETING
                ).id,

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': Calendar.objects.get_default_calendar(user).pk,

                self.EXTRA_PARTUSERS_KEY: [user.pk],
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=self.EXTRA_PARTUSERS_KEY,
            errors=_(
                'Select a valid choice. %(value)s is not one of the available choices.'
            ) % {'value': user.id},
        )

    @skipIfNotInstalled('creme.assistants')
    def test_alert(self):
        user = self.login_as_root_and_get()

        title = 'Meeting01'
        my_calendar = Calendar.objects.get_default_calendar(user)
        days = 2
        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_QUALIFICATION)
        response = self.client.post(
            self.ACTIVITY_CREATION_URL, follow=True,
            data={
                'user':  user.id,
                'title': title,

                self.EXTRA_SUBTYPE_KEY: sub_type.id,
                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2010, 1, 10),

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,

                self.EXTRA_ALERTDT_KEY: self.formfield_value_datetime(
                    year=2010, month=2, day=10, hour=10, minute=5,
                ),

                f'{self.EXTRA_ALERTPERIOD_KEY}_0': DaysPeriod.name,
                f'{self.EXTRA_ALERTPERIOD_KEY}_1': days,
            },
        )
        self.assertNoFormError(response)

        act = self.get_object_or_fail(Activity, title=title)
        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2010, month=1, day=10), act.start)
        self.assertEqual(sub_type.type_id, act.type_id)
        self.assertEqual(sub_type.id,      act.sub_type_id)

        alerts = Alert.objects.filter(entity_id=act.id).order_by('id')
        self.assertEqual(2, len(alerts))

        alert1 = alerts[0]
        self.assertEqual(act, alert1.real_entity)
        self.assertEqual(_('Alert of activity'), alert1.title)
        self.assertEqual(
            _('Alert related to {activity}').format(activity=act),
            alert1.description,
        )
        self.assertEqual(create_dt(2010, 2, 10, 10, 5), alert1.trigger_date)

        alert2 = alerts[1]
        self.assertEqual(create_dt(2010, 1, 8, 0, 0), alert2.trigger_date)
        self.assertDictEqual(
            {
                'cell': {'type': 'regular_field', 'value': 'start'},
                'sign': -1,
                'period': {'type': DaysPeriod.name, 'value': days},
            },
            alert2.trigger_offset,
        )

        # Relative Alert updating
        act.start = create_dt(year=2010, month=1, day=12)
        act.save()
        self.assertEqual(create_dt(2010, 1, 10, 0, 0), self.refresh(alert2).trigger_date)

    @skipIfNotInstalled('creme.assistants')
    def test_alert__no_period(self):
        "Period value is missing: no alert created."
        user = self.login_as_root_and_get()

        title = 'Meeting01'
        my_calendar = Calendar.objects.get_default_calendar(user)
        response = self.client.post(
            self.ACTIVITY_CREATION_URL,
            follow=True,
            data={
                'user':  user.pk,
                'title': title,

                self.EXTRA_SUBTYPE_KEY: self._get_sub_type(
                    constants.UUID_SUBTYPE_MEETING_QUALIFICATION
                ).id,

                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2013, 3, 28),
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
    def test_alert__floating(self):
        "Cannot create a relative alert on floating activity."
        user = self.login_as_root_and_get()

        title = 'Meeting01'
        my_calendar = Calendar.objects.get_default_calendar(user)
        response = self.assertPOST200(
            self.ACTIVITY_CREATION_URL,
            follow=True,
            data={
                'user':  user.id,
                'title': title,

                self.EXTRA_SUBTYPE_KEY: self._get_sub_type(
                    constants.UUID_SUBTYPE_MEETING_QUALIFICATION
                ).id,

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,

                f'{self.EXTRA_ALERTPERIOD_KEY}_0': 'days',
                f'{self.EXTRA_ALERTPERIOD_KEY}_1': 1,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=self.EXTRA_ALERTPERIOD_KEY,
            errors=_('You cannot set a relative alert on a floating activity'),
        )

    @skipIfNotInstalled('creme.assistants')
    @skipIfCustomContact
    @override_settings(SOFTWARE_LABEL='My CRM')
    def test_user_message(self):
        user = self.login_as_root_and_get()
        other_user = self.create_user()
        self.assertEqual(0, UserMessage.objects.count())

        # TODO: improve FieldGroupList API (eg .extend()) ?
        umsg_cell = UserMessagesSubCell(model=Activity).into_cell()
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
                ),
            ],
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

                self.EXTRA_SUBTYPE_KEY: self._get_sub_type(
                    constants.UUID_SUBTYPE_MEETING_NETWORK,
                ).id,
                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2010, 1, 10),

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.id,

                self.EXTRA_PARTUSERS_KEY: other_user.pk,
                self.EXTRA_OTHERPART_KEY: self.formfield_value_multi_creator_entity(genma),
                self.EXTRA_SUBJECTS_KEY:  self.formfield_value_multi_generic_entity(akane),

                self.EXTRA_MESSAGES_KEY: [user.id, other_user.id],
            },
        )
        self.assertNoFormError(response)

        meeting = self.get_object_or_fail(Activity, title=title)

        self.assertHaveRelation(me,    constants.REL_SUB_PART_2_ACTIVITY,  meeting)
        self.assertHaveRelation(ranma, constants.REL_SUB_PART_2_ACTIVITY,  meeting)
        self.assertHaveRelation(genma, constants.REL_SUB_PART_2_ACTIVITY,  meeting)
        self.assertHaveRelation(akane, constants.REL_SUB_ACTIVITY_SUBJECT, meeting)

        messages = UserMessage.objects.all()
        self.assertEqual(2, len(messages))

        message = messages[0]
        self.assertEqual(user, message.sender)
        self.assertEqual(
            _('[{software}] Activity created: {activity}').format(
                software='My CRM',
                activity=meeting,
            ),
            message.title,
        )
        self.assertDatetimesAlmostEqual(now(), message.creation_date)
        self.assertUUIDEqual(UUID_PRIORITY_NOT_IMPORTANT, message.priority.uuid)
        self.assertEqual(meeting.id,             message.entity_id)
        self.assertEqual(meeting.entity_type_id, message.entity_content_type_id)

        self.assertSetEqual({user, other_user}, {msg.recipient for msg in messages})

        self.assertIn(str(meeting), message.title)

        body = message.body
        self.assertIn(str(akane), body)
        self.assertIn(str(me), body)
        self.assertIn(str(ranma), body)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_meeting(self):
        user = self.login_as_root_and_get()

        atype = self._get_type(constants.UUID_TYPE_MEETING)
        self.assertEqual(0,          atype.default_day_duration)
        self.assertEqual('00:15:00', atype.default_hour_duration)  # TODO: timedelta instead ??

        subtype = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_NETWORK)

        create_contact = partial(Contact.objects.create, user=user)
        ranma = create_contact(first_name='Ranma', last_name='Saotome')
        genma = create_contact(first_name='Genma', last_name='Saotome')

        dojo = Organisation.objects.create(user=user, name='Dojo')

        url = reverse('activities__create_activity', args=('meeting',))
        response1 = self.assertGET200(url)
        self.assertEqual(_('Create a meeting'), response1.context.get('title'))

        with self.assertNoException():
            subtype_f = response1.context['form'].fields[self.EXTRA_SUBTYPE_KEY]

        self.assertEqual(
            ActivitySubType.objects.get(uuid=constants.UUID_SUBTYPE_MEETING_MEETING).id,
            subtype_f.initial,
        )

        # TODO: help text of end (duration)

        # ---
        title = 'My meeting'
        status = Status.objects.all()[0]
        my_calendar = Calendar.objects.get_default_calendar(user)
        response2 = self.client.post(
            url, follow=True,
            data={
                'user':   user.pk,
                'title':  title,
                'status': status.pk,

                self.EXTRA_SUBTYPE_KEY: subtype.id,

                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2013, 4, 12),
                f'{self.EXTRA_START_KEY}_1': '10:00:00',

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,

                self.EXTRA_OTHERPART_KEY: self.formfield_value_multi_creator_entity(genma),
                self.EXTRA_SUBJECTS_KEY:  self.formfield_value_multi_generic_entity(ranma),
                self.EXTRA_LINKED_KEY:    self.formfield_value_multi_generic_entity(dojo),
            },
        )
        self.assertNoFormError(response2)

        meeting = self.get_object_or_fail(Activity, type=atype, title=title)

        self.assertEqual(status, meeting.status)
        # self.assertEqual(constants.NARROW, meeting.floating_type)  # Deprecated
        self.assertEqual(Activity.FloatingType.NARROW, meeting.floating_type)
        self.assertEqual(
            self.create_datetime(year=2013, month=4, day=12, hour=10, minute=00),
            meeting.start,
        )
        self.assertEqual(
            self.create_datetime(year=2013, month=4, day=12, hour=10, minute=15),
            meeting.end,
        )

        self.assertHaveRelation(user.linked_contact, constants.REL_SUB_PART_2_ACTIVITY,   meeting)
        self.assertHaveRelation(genma,               constants.REL_SUB_PART_2_ACTIVITY,   meeting)
        self.assertHaveRelation(ranma,               constants.REL_SUB_ACTIVITY_SUBJECT,  meeting)
        self.assertHaveRelation(dojo,                constants.REL_SUB_LINKED_2_ACTIVITY, meeting)

    def test_phonecall(self):
        user = self.login_as_root_and_get()
        subtype = self._get_sub_type(constants.UUID_SUBTYPE_PHONECALL_OUTGOING)

        url = reverse('activities__create_activity', args=('phonecall',))
        response1 = self.assertGET200(url)
        self.assertEqual(_('Create a phone call'), response1.context.get('title'))

        with self.assertNoException():
            subtype_f = response1.context['form'].fields[self.EXTRA_SUBTYPE_KEY]

        self.assertEqual(
            self._get_sub_type(constants.UUID_SUBTYPE_PHONECALL_OUTGOING).id,
            subtype_f.initial,
        )

        # ---
        title = 'My call'
        my_calendar = Calendar.objects.get_default_calendar(user)
        response2 = self.client.post(
            url, follow=True,
            data={
                'user': user.pk,
                'title': title,

                self.EXTRA_SUBTYPE_KEY: subtype.id,

                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2013, 4, 12),
                f'{self.EXTRA_START_KEY}_1': '10:00:00',

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,
            },
        )
        self.assertNoFormError(response2)
        activity = self.get_object_or_fail(Activity, title=title)
        self.assertUUIDEqual(constants.UUID_TYPE_PHONECALL, activity.type.uuid)

    def test_invalid_type(self):
        self.login_as_root()
        self.assertGET404(reverse('activities__create_activity', args=('invalid',)))

    def test_task(self):
        user = self.login_as_root_and_get()

        url = reverse('activities__create_activity', args=('task',))
        response1 = self.assertGET200(url)
        self.assertEqual(_('Create a task'), response1.context.get('title'))

        with self.assertNoException():
            subtype_f = response1.context['form'].fields[self.EXTRA_SUBTYPE_KEY]

        sub_type = ActivitySubType.objects.filter(type__uuid=constants.UUID_TYPE_TASK)[0]
        self.assertEqual(sub_type.id, subtype_f.initial)

        title = 'My call'
        my_calendar = Calendar.objects.get_default_calendar(user)
        data = {
            'user': user.pk,
            'title': title,

            f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2013, 4, 12),
            f'{self.EXTRA_START_KEY}_1': '10:00:00',

            f'{self.EXTRA_MYPART_KEY}_0': True,
            f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,
        }
        response2 = self.assertPOST200(url, data=data)
        self.assertFormError(
            response2.context['form'],
            field=self.EXTRA_SUBTYPE_KEY, errors=_('This field is required.'),
        )

        # ---
        response3 = self.client.post(
            url,
            follow=True,
            data={
                **data,
                self.EXTRA_SUBTYPE_KEY: sub_type.id,
            },
        )
        self.assertNoFormError(response3)
        activity = self.get_object_or_fail(Activity, title=title)
        self.assertEqual(sub_type.type_id, activity.type_id)
        self.assertEqual(sub_type.id,      activity.sub_type_id)


@skipIfCustomActivity
class ActivityRelatedCreationTestCase(_ActivitiesTestCase):
    @staticmethod
    def _build_add_related_uri(related, type_uuid=None):
        url = reverse('activities__create_related_activity', args=(related.id,))

        return url if not type_uuid else f'{url}?activity_type={type_uuid}'

    @skipIfCustomContact
    def test_to_simple_contact(self):
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        contact1 = Contact.objects.create(user=user, first_name='Ranma', last_name='Saotome')
        contact2 = other_user.linked_contact

        uri = self._build_add_related_uri(contact1)
        response1 = self.assertGET200(uri)

        with self.assertNoException():
            form = response1.context['form']

        self.assertListEqual([contact1], form.initial.get(self.EXTRA_OTHERPART_KEY))

        title = 'My meeting'
        callback_url = contact1.get_absolute_url()
        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_REVIVAL)
        response2 = self.client.post(
            uri,
            follow=True,
            data={
                'user':  user.id,
                'title': title,

                self.EXTRA_SUBTYPE_KEY: sub_type.id,

                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2010, 1, 10),
                f'{self.EXTRA_START_KEY}_1': '17:30:00',

                self.EXTRA_PARTUSERS_KEY: [other_user.pk],

                'callback_url': callback_url,
            },
        )
        self.assertNoFormError(response2)
        self.assertRedirects(response2, callback_url)

        meeting = self.get_object_or_fail(Activity, title=title)
        self.assertEqual(
            self.create_datetime(year=2010, month=1, day=10, hour=17, minute=30),
            meeting.start,
        )
        self.assertEqual(sub_type.type_id, meeting.type_id)
        self.assertEqual(sub_type.id,      meeting.sub_type_id)

        self.assertEqual(2, Relation.objects.count())

        relation = self.get_alone_element(
            Relation.objects.filter(type=constants.REL_SUB_PART_2_ACTIVITY)
        )
        self.assertEqual(contact2.id, relation.subject_entity_id)
        self.assertEqual(meeting.id,   relation.object_entity_id)

    def test_to_user_contact(self):
        "Link to a user-Contact => selected a participating user."
        self.login_as_root()
        other_user = self.create_user()

        response = self.assertGET200(self._build_add_related_uri(
            related=other_user.linked_contact,
            type_uuid=constants.UUID_TYPE_MEETING,
        ))

        form = self.get_form_or_fail(response)
        self.assertListEqual([other_user], form.initial.get(self.EXTRA_PARTUSERS_KEY))

    @skipIfCustomOrganisation
    def test_subject(self):
        "Link to an Entity which can be a subject."
        user = self.login_as_root_and_get()

        dojo = Organisation.objects.create(user=user, name='Tendo no dojo')
        response = self.assertGET200(
            self._build_add_related_uri(dojo, type_uuid=constants.UUID_TYPE_MEETING),
        )
        form = self.get_form_or_fail(response)
        self.assertListEqual(
            [dojo.id],
            [e.id for e in form.initial.get(self.EXTRA_SUBJECTS_KEY, ())],
        )

    def test_disabled_rtype(self):
        "Link to an Entity which cannot be a participant/subject."
        user = self.login_as_root_and_get()

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER)
        linked = Activity.objects.create(
            user=user, title='Meet01',
            type_id=sub_type.type_id, sub_type=sub_type,
        )
        url = self._build_add_related_uri(linked, type_uuid=constants.UUID_TYPE_PHONECALL)
        response1 = self.assertGET200(url)

        self.assertListEqual(
            [linked.id],
            [e.id for e in response1.context['form'].initial.get(self.EXTRA_LINKED_KEY, ())],
        )

        rtype = self.get_object_or_fail(
            RelationType, id=constants.REL_SUB_LINKED_2_ACTIVITY,
        )
        rtype.enabled = False
        rtype.save()

        try:
            response2 = self.assertGET200(url)
            self.assertNotIn(self.EXTRA_LINKED_KEY, response2.context['form'].initial)
        finally:
            rtype.enabled = True
            rtype.save()

    def test_link_forbidden(self):
        "Not allowed LINKing."
        user = self.login_as_activities_user(creatable_models=[Activity])
        self.add_credentials(user.role, own='!LINK')

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER)
        linked = Activity.objects.create(
            user=user, title='Meet01', type_id=sub_type.type_id, sub_type=sub_type,
        )
        self.assertGET403(self._build_add_related_uri(linked, constants.UUID_TYPE_PHONECALL))

    @skipIfCustomContact
    def test_meeting(self):
        "Meeting forced."
        user = self.login_as_root_and_get()

        ryoga = Contact.objects.create(user=user, first_name='Ryoga', last_name='Hibiki')

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_REVIVAL)
        uri = self._build_add_related_uri(ryoga, type_uuid=constants.UUID_TYPE_MEETING)
        title = 'My meeting'
        my_calendar = Calendar.objects.get_default_calendar(user)
        response1 = self.client.post(
            uri,
            follow=True,
            data={
                'user': user.pk,
                'title': title,

                self.EXTRA_SUBTYPE_KEY: sub_type.id,

                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2013, 5, 21),
                f'{self.EXTRA_START_KEY}_1': '9:30:00',

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,
            },
        )
        self.assertNoFormError(response1)

        meeting = self.get_object_or_fail(Activity, title=title)
        self.assertEqual(
            self.create_datetime(year=2013, month=5, day=21, hour=9, minute=30),
            meeting.start,
        )
        self.assertEqual(sub_type.type_id, meeting.type_id)
        self.assertEqual(sub_type.id,      meeting.sub_type_id)

        self.assertRedirects(response1, meeting.get_absolute_url())

    @skipIfCustomContact
    def test_other_types(self):
        user = self.login_as_root_and_get()

        ryoga = Contact.objects.create(user=user, first_name='Ryoga', last_name='Hibiki')
        build_url = partial(self._build_add_related_uri, ryoga)
        self.assertGET200(build_url(type_uuid=constants.UUID_TYPE_PHONECALL))
        self.assertGET200(build_url(type_uuid=constants.UUID_TYPE_TASK))
        self.assertGET404(build_url(type_uuid=str(uuid.uuid4())))


@skipIfCustomActivity
class ActivityCreationPopupTestCase(_ActivitiesTestCase):
    ACTIVITY_POPUP_CREATION_URL = reverse('activities__create_activity_popup')
    TITLE = 'Meeting activity'

    def _build_submit_data(self, user, **kwargs):
        return {
            'user': user.pk,
            'title': self.TITLE,
            self.EXTRA_SUBTYPE_KEY: self._get_sub_type(
                constants.UUID_SUBTYPE_MEETING_NETWORK,
            ).id,
            **kwargs
        }

    @parameterized.expand([
        ({}, 404),
        ({'start': 'invalid'}, 404),
        ({'end': 'invalid'}, 404),
        ({'start': 'invalid', 'end': 'invalid'}, 404),
        ({'start': '2010-01-01T16:35:00', 'end': 'invalid'}, 404),
    ])
    def test_invalid_parameter(self, data, status_code):
        self.login_as_root()

        response = self.client.get(self.ACTIVITY_POPUP_CREATION_URL, data=data)
        self.assertEqual(response.status_code, status_code)

    def test_regular_user(self):
        self.login_as_activities_user(creatable_models=[Activity])
        self.assertGET200(
            self.ACTIVITY_POPUP_CREATION_URL,
            data={'start': '2010-01-01T16:35:00'},
        )

    def test_creation_perm(self):
        "Creation perm is needed."
        self.login_as_activities_user()
        self.assertGET403(
            self.ACTIVITY_POPUP_CREATION_URL,
            data={'start': '2010-01-01T16:35:00'},
        )

    def test_render(self):
        self.login_as_root()

        response = self.assertGET200(
            self.ACTIVITY_POPUP_CREATION_URL,
            data={'start': '2010-01-01T16:35:00'},
        )

        context = response.context
        self.assertEqual(Activity.creation_label, context.get('title'))
        self.assertEqual(Activity.save_label,     context.get('submit_label'))

        # It seems TemplateDoesNotExists is not raised in unit tests
        self.assertContains(response, 'name="title"')

        get_initial = context['form'].initial.get
        self.assertTupleEqual(
            (date(2010, 1, 1), time(16, 35)),
            get_initial(self.EXTRA_START_KEY),
        )
        self.assertIsNone(get_initial(self.EXTRA_END_KEY))
        self.assertFalse(get_initial('is_all_day'))

    @parameterized.expand([
        ('2010-01-01T16:35:12', date(2010, 1, 1), time(16, 35)),
        # Beware when it's 23 o clock (bugfix)
        ('2010-01-01T23:16:00', date(2010, 1, 1), time(23, 16)),
        ('2010-01-01T00:00:00', date(2010, 1, 1), None),
    ])
    def test_start_only(self, start_iso, start_date, start_time):
        self.login_as_root()

        response = self.assertGET200(
            self.ACTIVITY_POPUP_CREATION_URL,
            data={'start': start_iso},
        )

        get_initial = self.get_form_or_fail(response).initial.get
        self.assertTupleEqual(
            (start_date, start_time),
            get_initial(self.EXTRA_START_KEY),
        )
        self.assertIsNone(get_initial(self.EXTRA_END_KEY))
        self.assertFalse(get_initial('is_all_day'))

    def test_start_n_end(self):
        self.login_as_root()

        response = self.assertGET200(
            self.ACTIVITY_POPUP_CREATION_URL,
            data={
                'start': '2010-01-01T16:35:00',
                'end': '2010-01-01T18:35:00',
            },
        )

        get_initial = self.get_form_or_fail(response).initial.get
        self.assertTupleEqual(
            (date(2010, 1, 1), time(16, 35)),
            get_initial(self.EXTRA_START_KEY),
        )
        self.assertEqual(
            (date(2010, 1, 1), time(18, 35)),
            get_initial(self.EXTRA_END_KEY),
        )
        self.assertFalse(get_initial('is_all_day'))

    def test_start_all_day(self):
        self.login_as_root()

        response = self.assertGET200(
            self.ACTIVITY_POPUP_CREATION_URL,
            data={
                'start': '2010-01-01T16:35:00',
                'allDay': 'true',
            },
        )

        get_initial = self.get_form_or_fail(response).initial.get
        self.assertEqual(
            (date(2010, 1, 1), time(16, 35)),
            get_initial(self.EXTRA_START_KEY),
        )
        self.assertIsNone(get_initial(self.EXTRA_END_KEY))
        self.assertTrue(get_initial('is_all_day'))

    def test_error__no_participant(self):
        "No participant given."
        user = self.login_as_root_and_get()

        response = self.assertPOST200(
            self.ACTIVITY_POPUP_CREATION_URL,
            data=self._build_submit_data(
                user,
                **{
                    f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2010, 1, 10),
                    f'{self.EXTRA_START_KEY}_1': '09:30:00',

                    f'{self.EXTRA_END_KEY}_0': self.formfield_value_date(2010, 1, 10),
                    f'{self.EXTRA_END_KEY}_1': '15:00:00',
                }
            ),
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=None, errors=_('No participant'),
        )

    def test_error__my_participation_no_calendar(self):
        "Selected myself as participant without calendar."
        user = self.login_as_root_and_get()
        response = self.assertPOST200(
            self.ACTIVITY_POPUP_CREATION_URL,
            data=self._build_submit_data(
                user,
                **{
                    f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2010, 1, 10),
                    f'{self.EXTRA_START_KEY}_1': '09:30:00',

                    f'{self.EXTRA_END_KEY}_0': self.formfield_value_date(2010, 1, 10),
                    f'{self.EXTRA_END_KEY}_1': '15:00:00',

                    f'{self.EXTRA_MYPART_KEY}_0': True,
                }
            ),
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=self.EXTRA_MYPART_KEY,
            errors=_('Enter a value if you check the box.'),
        )

    def test_my_participation(self):
        user = self.login_as_root_and_get()
        self.assertNoFormError(self.client.post(
            self.ACTIVITY_POPUP_CREATION_URL,
            data=self._build_submit_data(
                user,
                **{
                    f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2010, 1, 10),
                    f'{self.EXTRA_START_KEY}_1': '09:30:00',

                    f'{self.EXTRA_END_KEY}_0': self.formfield_value_date(2010, 1, 10),
                    f'{self.EXTRA_END_KEY}_1': '15:00:00',

                    f'{self.EXTRA_MYPART_KEY}_0': True,
                    f'{self.EXTRA_MYPART_KEY}_1': Calendar.objects.get_default_calendar(user).pk
                }
            ),
        ))

        self.assertEqual(1, Activity.objects.count())
        activity = self.get_object_or_fail(Activity, title=self.TITLE)

        create_dt = partial(self.create_datetime, year=2010, month=1, day=10)
        self.assertEqual(create_dt(hour=9, minute=30), activity.start)
        self.assertEqual(create_dt(hour=15), activity.end)
        self.assertUUIDEqual(constants.UUID_TYPE_MEETING,            activity.type.uuid)
        self.assertUUIDEqual(constants.UUID_SUBTYPE_MEETING_NETWORK, activity.sub_type.uuid)

    def test_custom_activity_type(self):
        user = self.login_as_root_and_get()
        custom_type = ActivityType.objects.create(
            name='Karate session',
            default_day_duration=0,
            default_hour_duration='00:15:00',
            is_custom=True,
        )
        custom_sub_type = ActivitySubType.objects.create(
            name='Kick session',
            type=custom_type,
            is_custom=True,
        )

        self.assertNoFormError(self.client.post(
            self.ACTIVITY_POPUP_CREATION_URL,
            data=self._build_submit_data(
                user,
                **{
                    f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2010, 1, 10),
                    f'{self.EXTRA_START_KEY}_1': '09:30:00',

                    self.EXTRA_SUBTYPE_KEY: custom_sub_type.id,

                    f'{self.EXTRA_MYPART_KEY}_0': True,
                    f'{self.EXTRA_MYPART_KEY}_1': Calendar.objects.get_default_calendar(user).pk,
                }
            ),
        ))

        self.assertEqual(1, Activity.objects.count())
        activity = self.get_object_or_fail(Activity, title=self.TITLE)

        create_dt = partial(self.create_datetime, year=2010, month=1, day=10)
        self.assertEqual(create_dt(hour=9, minute=30), activity.start)
        self.assertEqual(create_dt(hour=9, minute=45), activity.end)
        self.assertEqual(custom_type.id, activity.type_id)
        self.assertEqual(custom_sub_type.id, activity.sub_type_id)

    @parameterized.expand([
        # Timezone DST change for Europe/Paris
        (_ActivitiesTestCase.create_datetime(2013, 10, 27),),

        # No DST change for Europe/Paris
        (_ActivitiesTestCase.create_datetime(2013, 10, 28),),
    ])
    def test_DST_transition_all_day(self, today):
        "Check that the DST transition works for all-day meetings."
        user = self.login_as_root_and_get()

        self.assertNoFormError(self.client.post(
            self.ACTIVITY_POPUP_CREATION_URL,
            data=self._build_submit_data(
                user,
                **{
                    f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(today),

                    f'{self.EXTRA_MYPART_KEY}_0': True,
                    f'{self.EXTRA_MYPART_KEY}_1': Calendar.objects.get_default_calendar(user).pk,
                }
            ),
        ))

        activity = self.get_object_or_fail(Activity, title=self.TITLE)
        create_today_dt = partial(
            self.create_datetime,
            year=today.year, month=today.month, day=today.day,
        )
        self.assertEqual(create_today_dt(hour=0,  minute=0), activity.start)
        self.assertEqual(create_today_dt(hour=23, minute=59), activity.end)


@skipIfCustomActivity
class UnavailabilityCreationTestCase(_ActivitiesTestCase):
    ADD_UNAVAILABILITY_URL = reverse('activities__create_unavailability')

    def test_not_generic(self):
        "Can not create an unavailability with the generic view."
        user = self.login_as_root_and_get()

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

                self.EXTRA_SUBTYPE_KEY: self._get_type(
                    constants.UUID_TYPE_UNAVAILABILITY
                ).activitysubtype_set.first().id,

                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2013, 3, 27),
                f'{self.EXTRA_START_KEY}_1': '09:00:00',

                f'{self.EXTRA_END_KEY}_0': self.formfield_value_date(2010, 3, 27),
                f'{self.EXTRA_END_KEY}_1': '11:00:00',

                f'{self.EXTRA_MYPART_KEY}_0': True,
                f'{self.EXTRA_MYPART_KEY}_1': my_calendar.pk,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=self.EXTRA_SUBTYPE_KEY,
            errors=ActivitySubTypeField.default_error_messages['invalid_choice'],
        )

    def test_ok(self):
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        url = self.ADD_UNAVAILABILITY_URL
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
                'An unavailability always busies its participants; mark it as '
                '«all day» if you do not set the start/end times.'
            ),
            allday_f.help_text,
        )

        # ---
        title = 'Away'
        data = {
            'user': user.pk,
            'title': title,

            f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2010, 1, 10),
            f'{self.EXTRA_START_KEY}_1': '09:08:07',

            f'{self.EXTRA_END_KEY}_0': self.formfield_value_date(2010, 1, 12),
            f'{self.EXTRA_END_KEY}_1': '06:05:04',

            self.EXTRA_PARTUSERS_KEY: [user.id, other_user.id],
        }
        response2 = self.assertPOST200(
            url,
            follow=True,
            data=data,
        )
        key = f'cform_extra-{UnavailabilityTypeSubCell.sub_type_id}'
        self.assertFormError(
            response2.context['form'],
            field=key, errors=_('This field is required.'),
        )

        # ---
        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_UNAVAILABILITY)
        response3 = self.client.post(
            url, follow=True, data={**data, key: sub_type.id},
        )
        self.assertNoFormError(response3)

        act = self.get_object_or_fail(Activity, title=title)
        self.assertEqual(sub_type.type_id, act.type_id)
        self.assertEqual(sub_type.id, act.sub_type_id)
        self.assertIsNone(act.status)
        self.assertFalse(act.is_all_day)
        self.assertFalse(act.busy)

        get_cal = Calendar.objects.get_default_calendar
        self.assertCountEqual([get_cal(user), get_cal(other_user)], [*act.calendars.all()])

        create_dt = partial(self.create_datetime, year=2010, month=1)
        self.assertEqual(
            create_dt(day=10, hour=9, minute=8, second=7), act.start,
        )
        self.assertEqual(
            create_dt(day=12, hour=6, minute=5, second=4), act.end,
        )

        self.assertHaveRelation(user.linked_contact,       constants.REL_SUB_PART_2_ACTIVITY, act)
        self.assertHaveRelation(other_user.linked_contact, constants.REL_SUB_PART_2_ACTIVITY, act)

    def test_is_all_day(self):
        user = self.login_as_root_and_get()

        title = 'AFK'
        unav_type = self._get_type(constants.UUID_TYPE_UNAVAILABILITY)
        subtype = ActivitySubType.objects.create(name='Holidays', type=unav_type)
        response = self.client.post(
            self.ADD_UNAVAILABILITY_URL,
            follow=True,
            data={
                'user':  user.pk,
                'title': title,
                'is_all_day': True,

                'cform_extra-activities_unavailability_subtype': subtype.id,

                f'{self.EXTRA_START_KEY}_0': self.formfield_value_date(2010, 1, 10),
                f'{self.EXTRA_END_KEY}_0':   self.formfield_value_date(2010, 1, 12),

                self.EXTRA_PARTUSERS_KEY: [user.id],
            },
        )
        self.assertNoFormError(response)

        act = self.get_object_or_fail(Activity, title=title)
        self.assertEqual(unav_type, act.type)
        self.assertEqual(subtype, act.sub_type)
        self.assertTrue(act.is_all_day)

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2010, month=1, day=10, hour=0,  minute=0),  act.start)
        self.assertEqual(create_dt(year=2010, month=1, day=12, hour=23, minute=59), act.end)

    def test_required_start_n_end(self):
        "Start & end are required."
        user = self.login_as_root_and_get()

        response = self.assertPOST200(
            self.ADD_UNAVAILABILITY_URL,
            follow=True,
            data={
                'user': user.pk,
                'title': 'AFK',
                self.EXTRA_PARTUSERS_KEY: [user.id],
            },
        )
        form = self.get_form_or_fail(response)
        msg = _('This field is required.')
        self.assertFormError(form, field=self.EXTRA_START_KEY, errors=msg)
        self.assertFormError(form, field=self.EXTRA_END_KEY,   errors=msg)
