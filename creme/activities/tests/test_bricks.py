from datetime import timedelta
from functools import partial
from json import loads as json_loads
from unittest.mock import patch

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory
from django.urls import reverse
from django.utils.timezone import now
from django.utils.timezone import override as override_tz

from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    Relation,
    SettingValue,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.media import get_creme_media_url
from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from ..bricks import (
    ActivityBarHatBrick,
    FutureActivitiesBrick,
    MyActivitiesCalendarBrick,
    ParticipantsBrick,
    PastActivitiesBrick,
    SubjectsBrick,
    UserCalendarsBrick,
)
from ..constants import (
    REL_SUB_ACTIVITY_SUBJECT,
    REL_SUB_LINKED_2_ACTIVITY,
    REL_SUB_PART_2_ACTIVITY,
    UUID_SUBTYPE_MEETING_NETWORK,
    UUID_SUBTYPE_PHONECALL_OUTGOING,
)
from ..models import Calendar
from ..setting_keys import review_key
from .base import (
    Activity,
    Contact,
    Organisation,
    _ActivitiesTestCase,
    skipIfCustomActivity,
)


@skipIfCustomActivity
class ActivityBricksTestCase(BrickTestCaseMixin, _ActivitiesTestCase):
    def test_bar__meeting(self):
        user = self.get_root_user()

        sub_type = self._get_sub_type(UUID_SUBTYPE_MEETING_NETWORK)
        activity = Activity.objects.create(
            user=user, title='Meeting #1',
            type_id=sub_type.type_id, sub_type=sub_type,
        )

        request = RequestFactory().get(activity.get_absolute_url())
        request.user = user

        brick = ActivityBarHatBrick()
        render = brick.detailview_display(
            context=self.build_context(user=user, instance=activity),
        )
        brick_node = self.get_brick_node(self.get_html_tree(render), brick=brick)

        icon_node = self.get_html_node_or_fail(brick_node, './/div[@class="bar-icon"]/img')
        self.assertEqual(
            get_creme_media_url(theme='icecream', url='images/meeting_48.png'),
            icon_node.attrib.get('src'),
        )

    def test_bar__phone_call(self):
        user = self.get_root_user()

        sub_type = self._get_sub_type(UUID_SUBTYPE_PHONECALL_OUTGOING)
        activity = Activity.objects.create(
            user=user, title='Call #1',
            type_id=sub_type.type_id, sub_type=sub_type,
        )

        request = RequestFactory().get(activity.get_absolute_url())
        request.user = user

        brick = ActivityBarHatBrick()
        render = brick.detailview_display(
            context=self.build_context(user=user, instance=activity),
        )
        brick_node = self.get_brick_node(self.get_html_tree(render), brick=brick)

        icon_node = self.get_html_node_or_fail(brick_node, './/div[@class="bar-icon"]/img')
        self.assertEqual(
            get_creme_media_url(theme='icecream', url='images/phone_48.png'),
            icon_node.attrib.get('src'),
        )

    @skipIfCustomContact
    def test_participants(self):
        ParticipantsBrick.page_size = max(4, settings.BLOCK_SIZE)

        user = self.login_as_root_and_get()
        activity = self._create_meeting(user=user)

        create_contact = partial(Contact.objects.create, user=user)
        c1 = user.linked_contact
        c2 = create_contact(first_name='Musashi', last_name='Miyamoto')
        c3 = create_contact(first_name='Kojiro',  last_name='Sasaki')

        create_rel = partial(
            Relation.objects.create,
            user=user, object_entity=activity,
        )
        create_rel(subject_entity=c1, type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=c2, type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=c3, type_id=REL_SUB_ACTIVITY_SUBJECT)

        ContentType.objects.get_for_model(Relation)  # Fill cache

        context = self.build_context(user=user, instance=activity)
        # Queries:
        #   - COUNT Relations
        #   - BrickStates
        #   - SettingValues "is open"/"how empty fields"
        #   - Relations
        #   - Contacts (with user/is_user/civility)
        #   - Calendars
        with self.assertNumQueries(6):
            render = ParticipantsBrick().detailview_display(context)

        brick_node = self.get_brick_node(self.get_html_tree(render), ParticipantsBrick)
        self.assertInstanceLink(brick_node, c1)
        self.assertInstanceLink(brick_node, c2)
        self.assertNoInstanceLink(brick_node, c3)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_subjects(self):
        SubjectsBrick.page_size = max(4, settings.BLOCK_SIZE)

        user = self.login_as_root_and_get()
        activity = self._create_meeting(user=user)

        create_contact = partial(Contact.objects.create, user=user)
        c1 = user.linked_contact
        c2 = create_contact(first_name='Musashi', last_name='Miyamoto')
        c3 = create_contact(first_name='Kojiro',  last_name='Sasaki')

        orga = Organisation.objects.create(user=user, name='Yoshioka')

        create_rel = partial(
            Relation.objects.create,
            user=user, object_entity=activity,
        )
        create_rel(subject_entity=c1,   type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=c2,   type_id=REL_SUB_ACTIVITY_SUBJECT)
        create_rel(subject_entity=c3,   type_id=REL_SUB_ACTIVITY_SUBJECT)
        create_rel(subject_entity=orga, type_id=REL_SUB_ACTIVITY_SUBJECT)

        ContentType.objects.get_for_model(Relation)  # Fill cache

        context = self.build_context(user=user, instance=activity)
        # Queries:
        #   - COUNT Relations
        #   - BrickStates
        #   - SettingValues "is open"/"how empty fields"
        #   - Relations
        #   - Contacts
        #   - Organisations
        with self.assertNumQueries(6):
            render = SubjectsBrick().detailview_display(context)

        brick_node = self.get_brick_node(self.get_html_tree(render), SubjectsBrick)
        self.assertInstanceLink(brick_node, c2)
        self.assertInstanceLink(brick_node, c3)
        self.assertInstanceLink(brick_node, orga)
        self.assertNoInstanceLink(brick_node, c1)

    # TODO: assertNumQueries on other type of Bricks

    @skipIfCustomContact
    def test_bricks_future_n_past__contacts(self):
        "Contacts + display minutes."
        FutureActivitiesBrick.page_size = max(10, settings.BLOCK_SIZE)
        PastActivitiesBrick.page_size = max(10, settings.BLOCK_SIZE)

        user = self.login_as_root_and_get()

        now_value = now()
        today8 = self.create_datetime(
            year=now_value.year, month=now_value.month, day=now_value.day,
            hour=8,
        )
        one_day = timedelta(days=1)
        tomorrow = today8 + one_day
        yesterday = today8 - one_day

        sub_type = self._get_sub_type(UUID_SUBTYPE_MEETING_NETWORK)
        create_activity = partial(
            Activity.objects.create,
            user=user,
            type_id=sub_type.type_id,
            sub_type=sub_type,
        )

        future = [
            create_activity(
                title=f'Future #{i}',
                minutes=f'Very interesting info about Future #{i}',
                start=tomorrow + timedelta(hours=i),
                end=tomorrow + timedelta(hours=i, minutes=30),
            ) for i in range(1, 5)
        ]
        past = [
            create_activity(
                title=f'Past #{i}',
                # TODO: test linebreaks + \n
                minutes=f'Very interesting info about Past #{i}',
                start=yesterday + timedelta(hours=i),
                end=yesterday + timedelta(hours=i, minutes=30),
            ) for i in range(1, 5)
        ]

        contact = Contact.objects.create(
            user=user, first_name='Musashi', last_name='Miyamoto',
        )
        create_rel = partial(Relation.objects.create, user=user, subject_entity=contact)
        create_rel(object_entity=future[0], type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(object_entity=future[1], type_id=REL_SUB_ACTIVITY_SUBJECT)
        create_rel(object_entity=future[2], type_id=REL_SUB_LINKED_2_ACTIVITY)

        create_rel(object_entity=past[0], type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(object_entity=past[1], type_id=REL_SUB_ACTIVITY_SUBJECT)
        create_rel(object_entity=past[2], type_id=REL_SUB_LINKED_2_ACTIVITY)

        sv = SettingValue.objects.get_4_key(review_key)
        sv.value = True
        sv.save()

        context = self.build_context(user=user, instance=contact)
        # Queries:
        #   - COUNT Activities
        #   - BrickStates
        #   - SettingValues "is open"/"how empty fields"
        #   - Activities
        #   - Relations ("participates", "subject of activity", "linked to activity")
        #   - Contacts
        with self.assertNumQueries(6):
            render = FutureActivitiesBrick().detailview_display(context)

        future_brick_node1 = self.get_brick_node(
            self.get_html_tree(render), brick=FutureActivitiesBrick,
        )
        self.assertInstanceLink(future_brick_node1, future[0])
        self.assertInstanceLink(future_brick_node1, future[1])
        self.assertInstanceLink(future_brick_node1, future[2])
        self.assertNoInstanceLink(future_brick_node1, future[3])
        self.assertNoInstanceLink(future_brick_node1, past[0])

        # From view ---
        create_brick_detail = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            model=Contact, zone=BrickDetailviewLocation.RIGHT,
        )
        create_brick_detail(brick=FutureActivitiesBrick, order=50)
        create_brick_detail(brick=PastActivitiesBrick,   order=51)

        response = self.assertGET200(contact.get_absolute_url())
        tree = self.get_html_tree(response.content)

        future_brick_node2 = self.get_brick_node(tree, FutureActivitiesBrick)
        self.assertInstanceLink(future_brick_node2, future[0])
        self.assertInstanceLink(future_brick_node2, future[1])
        self.assertInstanceLink(future_brick_node2, future[2])
        self.assertNoInstanceLink(future_brick_node2, future[3])
        self.assertNoInstanceLink(future_brick_node2, past[0])

        future_minutes = {
            n.text
            for n in future_brick_node2.findall('.//div[@class="activity-group-value"]/p')
        }
        self.assertIn(future[0].minutes, future_minutes)
        self.assertIn(future[1].minutes, future_minutes)
        self.assertIn(future[2].minutes, future_minutes)
        self.assertNotIn(future[3].minutes, future_minutes)

        past_brick_node = self.get_brick_node(tree, PastActivitiesBrick)
        self.assertInstanceLink(past_brick_node, past[0])
        self.assertInstanceLink(past_brick_node, past[1])
        self.assertInstanceLink(past_brick_node, past[2])
        self.assertNoInstanceLink(past_brick_node, past[3])
        self.assertNoInstanceLink(past_brick_node, future[0])

        past_minutes = {
            n.text
            for n in past_brick_node.findall('.//div[@class="activity-group-value"]/p')
        }
        self.assertIn(past[0].minutes, past_minutes)
        self.assertIn(past[1].minutes, past_minutes)
        self.assertIn(past[2].minutes, past_minutes)
        self.assertNotIn(past[3].minutes, past_minutes)

    @skipIfCustomContact
    def test_bricks_future_n_past__home(self):
        FutureActivitiesBrick.page_size = max(10, settings.BLOCK_SIZE)
        PastActivitiesBrick.page_size = max(10, settings.BLOCK_SIZE)

        user = self.login_as_root_and_get()

        now_value = now()
        today8 = self.create_datetime(
            year=now_value.year, month=now_value.month, day=now_value.day,
            hour=8,
        )
        one_day = timedelta(days=1)
        tomorrow = today8 + one_day
        yesterday = today8 - one_day

        sub_type = self._get_sub_type(UUID_SUBTYPE_MEETING_NETWORK)
        create_activity = partial(
            Activity.objects.create,
            user=user, type_id=sub_type.type_id, sub_type=sub_type,
        )

        future = [
            create_activity(
                title=f'Future #{i}',
                start=tomorrow + timedelta(hours=i),
                end=tomorrow + timedelta(hours=i, minutes=30),
            ) for i in range(1, 5)
        ]
        past = [
            create_activity(
                title=f'Past #{i}',
                start=yesterday + timedelta(hours=i),
                end=yesterday + timedelta(hours=i, minutes=30),
            ) for i in range(1, 5)
        ]

        contact = user.linked_contact
        create_rel = partial(Relation.objects.create, user=user, subject_entity=contact)
        create_rel(object_entity=future[0], type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(object_entity=future[1], type_id=REL_SUB_ACTIVITY_SUBJECT)
        create_rel(object_entity=future[2], type_id=REL_SUB_LINKED_2_ACTIVITY)

        create_rel(object_entity=past[0], type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(object_entity=past[1], type_id=REL_SUB_ACTIVITY_SUBJECT)
        create_rel(object_entity=past[2], type_id=REL_SUB_LINKED_2_ACTIVITY)

        context = self.build_context(user=user)
        # Queries:
        #   - COUNT Activities
        #   - BrickStates
        #   - SettingValues "is open"/"how empty fields"
        #   - Activities
        #   - Relations ("participates", "subject of activity", "linked to activity")
        #   - Contacts
        #   - SettingValues "activities-display_review_activities_blocks"
        with self.assertNumQueries(7):
            render = FutureActivitiesBrick().home_display(context)

        future_brick_node1 = self.get_brick_node(
            self.get_html_tree(render), brick=FutureActivitiesBrick,
        )
        self.assertInstanceLink(future_brick_node1, future[0])
        self.assertInstanceLink(future_brick_node1, future[1])
        self.assertInstanceLink(future_brick_node1, future[2])
        self.assertNoInstanceLink(future_brick_node1, future[3])
        self.assertNoInstanceLink(future_brick_node1, past[0])

        # From view ---
        BrickHomeLocation.objects.get_or_create(
            brick_id=FutureActivitiesBrick.id, defaults={'order': 10},
        )
        BrickHomeLocation.objects.get_or_create(
            brick_id=PastActivitiesBrick.id, defaults={'order': 11},
        )

        response1 = self.assertGET200(reverse('creme_core__home'))
        tree = self.get_html_tree(response1.content)

        future_brick_node = self.get_brick_node(tree, FutureActivitiesBrick)
        self.assertInstanceLink(future_brick_node, future[0])
        self.assertInstanceLink(future_brick_node, future[1])
        self.assertInstanceLink(future_brick_node, future[2])
        self.assertNoInstanceLink(future_brick_node, future[3])
        self.assertNoInstanceLink(future_brick_node, past[0])

        past_brick_node = self.get_brick_node(tree, PastActivitiesBrick)
        self.assertInstanceLink(past_brick_node, past[0])
        self.assertInstanceLink(past_brick_node, past[1])
        self.assertInstanceLink(past_brick_node, past[2])
        self.assertNoInstanceLink(past_brick_node, past[3])
        self.assertNoInstanceLink(past_brick_node, future[0])

    @skipIfCustomOrganisation
    @skipIfCustomContact
    def test_bricks_future_n_past__organisations_n_contacts(self):
        "Organisations & Contacts + do not display minutes."
        FutureActivitiesBrick.page_size = max(10, settings.BLOCK_SIZE)
        PastActivitiesBrick.page_size = max(10, settings.BLOCK_SIZE)

        create_brick_detail = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            model=Organisation, zone=BrickDetailviewLocation.RIGHT,
        )
        create_brick_detail(brick=FutureActivitiesBrick, order=50)
        create_brick_detail(brick=PastActivitiesBrick,   order=51)

        sv = SettingValue.objects.get_4_key(review_key)
        sv.value = False
        sv.save()

        user = self.login_as_root_and_get()

        now_value = now()
        today8 = self.create_datetime(
            year=now_value.year, month=now_value.month, day=now_value.day,
            hour=8,
        )
        one_day = timedelta(days=1)
        tomorrow = today8 + one_day
        yesterday = today8 - one_day

        sub_type = self._get_sub_type(UUID_SUBTYPE_MEETING_NETWORK)
        create_activity = partial(
            Activity.objects.create,
            user=user, type_id=sub_type.type_id, sub_type=sub_type,
        )

        future = [
            create_activity(
                title=f'Future #{i}',
                minutes=f'Very interesting info about Future #{i}',
                start=tomorrow + timedelta(hours=i),
                end=tomorrow + timedelta(hours=i, minutes=30),
            ) for i in range(1, 5)
        ]
        past = [
            create_activity(
                title=f'Past #{i}',
                minutes=f'Very interesting info about Past #{i}',
                start=yesterday + timedelta(hours=i),
                end=yesterday + timedelta(hours=i, minutes=30),
            ) for i in range(1, 5)
        ]

        orga = Organisation.objects.create(user=user, name='Yoshioka')

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Seijuro',     last_name='Yoshioka')
        c2 = create_contact(first_name='Denshichiro', last_name='Yoshioka')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=c1, object_entity=orga, type_id=REL_SUB_MANAGES)
        create_rel(subject_entity=c2, object_entity=orga, type_id=REL_SUB_EMPLOYED_BY)

        create_rel(subject_entity=c1,   object_entity=future[0], type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=orga, object_entity=future[1], type_id=REL_SUB_ACTIVITY_SUBJECT)
        create_rel(subject_entity=c2, object_entity=future[2], type_id=REL_SUB_LINKED_2_ACTIVITY)

        create_rel(subject_entity=c1,   object_entity=past[0], type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=orga, object_entity=past[1], type_id=REL_SUB_ACTIVITY_SUBJECT)
        create_rel(subject_entity=c2,   object_entity=past[2], type_id=REL_SUB_LINKED_2_ACTIVITY)

        response = self.assertGET200(orga.get_absolute_url())
        tree = self.get_html_tree(response.content)

        future_brick_node = self.get_brick_node(tree, FutureActivitiesBrick)
        self.assertInstanceLink(future_brick_node, future[0])
        self.assertInstanceLink(future_brick_node, future[1])
        self.assertInstanceLink(future_brick_node, future[2])
        self.assertNoInstanceLink(future_brick_node, future[3])
        self.assertNoInstanceLink(future_brick_node, past[0])
        self.assertNotIn(
            future[0].minutes,
            {
                n.text
                for n in future_brick_node.findall('.//div[@class="activity-group-value"]')
            },
        )

        past_brick_node = self.get_brick_node(tree, PastActivitiesBrick)
        self.assertInstanceLink(past_brick_node, past[0])
        self.assertInstanceLink(past_brick_node, past[1])
        self.assertInstanceLink(past_brick_node, past[2])
        self.assertNoInstanceLink(past_brick_node, past[3])
        self.assertNoInstanceLink(past_brick_node, future[0])
        self.assertNotIn(
            past[0].minutes,
            {
                n.text
                for n in past_brick_node.findall('.//div[@class="activity-group-value"]')
            },
        )

    @skipIfCustomContact
    def test_bricks_future_n_past__staff(self):
        "Home + staff root."
        FutureActivitiesBrick.page_size = max(10, settings.BLOCK_SIZE)
        PastActivitiesBrick.page_size = max(10, settings.BLOCK_SIZE)

        user = self.login_as_super(is_staff=True)
        root = self.get_root_user()

        now_value = now()
        today8 = self.create_datetime(
            year=now_value.year, month=now_value.month, day=now_value.day,
            hour=8,
        )
        one_day = timedelta(days=1)
        tomorrow = today8 + one_day
        yesterday = today8 - one_day

        sub_type = self._get_sub_type(UUID_SUBTYPE_MEETING_NETWORK)
        create_activity = partial(
            Activity.objects.create,
            user=root, type_id=sub_type.type_id, sub_type=sub_type,
        )

        future = [
            create_activity(
                title=f'Future #{i}',
                start=tomorrow + timedelta(hours=i),
                end=tomorrow + timedelta(hours=i, minutes=30),
            ) for i in range(1, 5)
        ]
        past = [
            create_activity(
                title=f'Past #{i}',
                start=yesterday + timedelta(hours=i),
                end=yesterday + timedelta(hours=i, minutes=30),
            ) for i in range(1, 5)
        ]

        contact = root.linked_contact
        create_rel = partial(Relation.objects.create, user=root, subject_entity=contact)
        create_rel(object_entity=future[0], type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(object_entity=future[1], type_id=REL_SUB_ACTIVITY_SUBJECT)
        create_rel(object_entity=future[2], type_id=REL_SUB_LINKED_2_ACTIVITY)

        create_rel(object_entity=past[0], type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(object_entity=past[1], type_id=REL_SUB_ACTIVITY_SUBJECT)
        create_rel(object_entity=past[2], type_id=REL_SUB_LINKED_2_ACTIVITY)

        context = self.build_context(user=user)
        future_render = FutureActivitiesBrick().home_display(context)

        future_brick_node = self.get_brick_node(
            self.get_html_tree(future_render), brick=FutureActivitiesBrick,
        )
        self.assertInstanceLink(future_brick_node, future[0])
        self.assertInstanceLink(future_brick_node, future[1])
        self.assertInstanceLink(future_brick_node, future[2])
        self.assertInstanceLink(future_brick_node, future[3])
        self.assertNoInstanceLink(future_brick_node, past[0])

        past_render = PastActivitiesBrick().home_display(context)
        past_brick_node = self.get_brick_node(
            self.get_html_tree(past_render), brick=PastActivitiesBrick,
        )
        self.assertInstanceLink(past_brick_node, past[0])
        self.assertInstanceLink(past_brick_node, past[1])
        self.assertInstanceLink(past_brick_node, past[2])
        self.assertInstanceLink(past_brick_node, past[3])
        self.assertNoInstanceLink(past_brick_node, future[0])

    def test_user_calendars(self):
        user = self.login_as_activities_user()
        UserCalendarsBrick.page_size = max(3, settings.BLOCK_SIZE)

        cal1 = Calendar.objects.get_default_calendar(user)
        cal2 = Calendar.objects.create(user=user, name='Other calendar')

        response = self.assertGET200(reverse('creme_config__user_settings'))
        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, UserCalendarsBrick)

        self.assertCountEqual(
            [f'background-color:#{cal.color};' for cal in [cal1, cal2]],
            [
                n.attrib.get('style')
                # TODO: make uniform?
                for n in brick_node.findall('.//div[@class="colored-square"]')
            ],
        )

    def test_user_calendars__no_app_perm(self):
        self.login_as_standard(allowed_apps=['persons'])  # Not 'activities'

        response = self.assertGET200(reverse('creme_config__user_settings'))
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=UserCalendarsBrick,
        )
        self.assertIn('brick-void', brick_node.attrib.get('class', ''))

    def test_fullcalendar(self):
        user = self.login_as_activities_user()

        contact = Contact.objects.create(user=user, first_name='Ranma', last_name='Saotome')

        default_cal = Calendar.objects.get_default_calendar(user)
        Calendar.objects.create(user=user, name='Other calendar')

        brick = MyActivitiesCalendarBrick()

        with override_tz('Europe/London'):
            dst_date = self.create_datetime(2023, 8, 1)

            with patch('creme.activities.utils.now', return_value=dst_date):
                render = brick.home_display(
                    context=self.build_context(user=user, instance=contact),
                )

        brick_node = self.get_brick_node(self.get_html_tree(render), brick=brick)

        settings = json_loads(
            brick_node.find('.//script[@class="brick-calendar-settings"]').text[4:-4]
        )
        sources = json_loads(
            brick_node.find('.//script[@class="brick-calendar-sources"]').text[4:-4]
        )

        self.assertDictEqual(settings, {
            'allow_event_move': False,
            'allow_event_create': False,
            'allow_keep_state': False,
            'headless_mode': False,
            'show_timezone_info': False,
            'show_week_number': True,
            'day_end': '18:00',
            'day_start': '08:00',
            'extra_data': {},
            'slot_duration': '00:15:00',
            'utc_offset': 60,
            'view': 'month',
            'week_days': [1, 2, 3, 4, 5, 6],
            'week_start': 1,
            'view_day_start': '00:00',
            'view_day_end': '24:00',
        })

        self.assertListEqual(sources, [default_cal.pk])

# TODO: test RelatedCalendarBrick
# TODO: test CalendarConfigItemsBrick
# TODO: test UnsuccessfulButtonConfigBrick
