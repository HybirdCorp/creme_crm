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
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core.constants import REL_SUB_HAS
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
    RelatedCalendarBrick,
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
    RM_PARTICIPANT_URL = reverse('activities__remove_participant')
    RM_SUBJECT_URL = reverse('activities__remove_subject')
    RM_RELATED_URL = reverse('activities__unlink_activity')

    @staticmethod
    def _build_add_participants_url(activity):
        return reverse('activities__add_participants', args=(activity.id,))

    @staticmethod
    def _build_add_subjects_url(activity):
        return reverse('activities__add_subjects', args=(activity.id,))

    def test_bar_brick__meeting(self):
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

    def test_bar_brick__phone_call(self):
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
    def test_participants_brick(self):
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
    def test_subjects_brick(self):
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
    def test_bricks_activity(self):
        ParticipantsBrick.page_size = SubjectsBrick.page_size = max(4, settings.BLOCK_SIZE)

        user = self.login_as_root_and_get()
        activity = self._create_meeting(user=user)

        create_contact = partial(Contact.objects.create, user=user)
        c1 = user.linked_contact
        c2 = create_contact(first_name='Musashi', last_name='Miyamoto')
        c3 = create_contact(first_name='Kojiro',  last_name='Sasaki')
        c4 = create_contact(first_name='Seijuro', last_name='Yoshioka')
        c5 = self.create_user().linked_contact

        create_rel = partial(
            Relation.objects.create,
            user=user, object_entity=activity,
        )
        create_rel(subject_entity=c1, type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=c2, type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=c3, type_id=REL_SUB_ACTIVITY_SUBJECT)
        create_rel(subject_entity=c4, type_id=REL_SUB_ACTIVITY_SUBJECT)

        cal = Calendar.objects.get_default_calendar(user)
        activity.calendars.add(cal)

        response = self.assertGET200(activity.get_absolute_url())
        self.assertTemplateUsed(response, 'activities/bricks/activity-hat-card.html')

        tree = self.get_html_tree(response.content)

        brick_node1 = self.get_brick_node(tree, ParticipantsBrick)
        self.assertInstanceLink(brick_node1, c1)
        self.assertInstanceLink(brick_node1, c2)
        self.assertNoInstanceLink(brick_node1, c3)
        self.assertNoInstanceLink(brick_node1, c4)
        self.assertNoInstanceLink(brick_node1, c5)

        brick_node2 = self.get_brick_node(tree, SubjectsBrick)
        self.assertInstanceLink(brick_node2, c3)
        self.assertInstanceLink(brick_node2, c4)
        self.assertNoInstanceLink(brick_node2, c1)
        self.assertNoInstanceLink(brick_node2, c2)
        self.assertNoInstanceLink(brick_node2, c5)

        brick_node3 = self.get_brick_node(tree, RelatedCalendarBrick)
        self.assertListEqual(
            [f'background-color:#{cal.color};'],
            [
                n.attrib.get('style')
                for n in brick_node3.findall('.//div[@class="activity-calendar-color-square"]')
            ],
        )

    @skipIfCustomContact
    def test_bricks_future_n_past01(self):
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
    def test_bricks_future_n_past02(self):
        "Home."
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
    def test_bricks_future_n_past03(self):
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
    def test_bricks_future_n_past04(self):
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

    @skipIfCustomContact
    def test_add_participants01(self):
        user = self.login_as_root_and_get()
        activity = self._create_meeting(user=user)

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Musashi', last_name='Miyamoto')
        c2 = create_contact(first_name='Kojiro',  last_name='Sasaki')

        url = self._build_add_participants_url(activity)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(
            _('Adding participants to activity «{entity}»').format(entity=activity),
            context.get('title')
        )
        self.assertEqual(_('Add the participants'), context.get('submit_label'))

        # ---
        self.assertNoFormError(self.client.post(
            url,
            data={'participants': self.formfield_value_multi_creator_entity(c1, c2)},
        ))
        self.assertCountEqual(
            [c1, c2],
            [
                r.subject_entity.get_real_entity()
                for r in Relation.objects.filter(
                    object_entity=activity.id, type=REL_SUB_PART_2_ACTIVITY,
                )
            ],
        )

    def test_add_participants02(self):
        "Credentials error with the activity."
        user = self.login_as_activities_user()
        self.add_credentials(user.role, own='!LINK')

        activity = self._create_meeting(user=user)
        self.assertTrue(user.has_perm_to_change(activity))
        self.assertFalse(user.has_perm_to_link(activity))
        self.assertGET403(self._build_add_participants_url(activity))

    @skipIfCustomContact
    def test_add_participants03(self):
        "Credentials error with selected subjects."
        user = self.login_as_activities_user()
        self.add_credentials(user.role, own=['LINK'], all='!LINK')

        activity = self._create_meeting(user=user)
        self.assertTrue(user.has_perm_to_link(activity))

        contact = Contact.objects.create(
            user=self.get_root_user(), first_name='Musashi', last_name='Miyamoto',
        )
        self.assertTrue(user.has_perm_to_change(contact))
        self.assertFalse(user.has_perm_to_link(contact))

        uri = self._build_add_participants_url(activity)
        self.assertGET200(uri)

        response = self.assertPOST200(
            uri,
            data={'participants': self.formfield_value_multi_creator_entity(contact)},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='participants',
            errors=_('Some entities are not linkable: {}').format(contact),
        )
        self.assertFalse(Relation.objects.filter(
            object_entity=activity.id,
            type=REL_SUB_PART_2_ACTIVITY,
        ))

    @skipIfCustomContact
    def test_add_participants04(self):
        "'My participation' field is removed when it is useless."
        user = self.login_as_root_and_get()
        activity = self._create_activity_by_view(user=user)

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Musashi', last_name='Miyamoto')
        c2 = create_contact(first_name='Kojiro',  last_name='Sasaki')

        uri = self._build_add_participants_url(activity)
        response = self.assertGET200(uri)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('my_participation', fields)
        self.assertNotIn('my_calendar',      fields)

        self.assertNoFormError(self.client.post(
            uri,
            data={'participants': self.formfield_value_multi_creator_entity(c1, c2)},
        ))
        self.assertCountEqual(
            [c1.id, c2.id, user.linked_contact.id],
            [
                *Relation.objects
                         .filter(object_entity=activity.id, type=REL_SUB_PART_2_ACTIVITY)
                         .values_list('subject_entity_id', flat=True),
            ],
        )

    @skipIfCustomContact
    def test_add_participants05(self):
        "Fix a bug when checking for collision for a floating activities."
        user = self.login_as_root_and_get()
        activity = self._create_activity_by_view(user=user)
        self.assertIsNone(activity.start)
        self.assertIsNone(activity.end)
        self.assertEqual(Activity.FloatingType.FLOATING, activity.floating_type)

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Musashi', last_name='Miyamoto')
        c2 = create_contact(first_name='Kojiro',  last_name='Sasaki')

        uri = self._build_add_participants_url(activity)
        self.assertGET200(uri)
        self.assertNoFormError(self.client.post(
            uri,
            data={'participants': self.formfield_value_multi_creator_entity(c1, c2)},
        ))
        self.assertCountEqual(
            [c1.id, c2.id, user.linked_contact.id],
            [
                *Relation.objects
                         .filter(object_entity=activity.id, type=REL_SUB_PART_2_ACTIVITY)
                         .values_list('subject_entity_id', flat=True),
            ],
        )

    def test_add_participants06(self):
        "When Teams are selected, their teammates are participants."
        user1 = self.login_as_root_and_get()
        activity = self._create_meeting(user=user1)

        user2 = self.create_user(0)
        user3  = self.create_user(1)
        team = self.create_team('Samurais', user2, user3, user1)

        response = self.client.post(
            self._build_add_participants_url(activity),
            data={
                'my_participation_0':  True,
                'my_participation_1':  Calendar.objects.get_default_calendar(user1).pk,
                'participating_users': [team.id, user3.id],
            },
        )
        self.assertNoFormError(response)
        self.assertCountEqual(
            [user2.linked_contact, user3.linked_contact, user1.linked_contact],
            [
                r.subject_entity.get_real_entity()
                for r in Relation.objects.filter(
                    object_entity=activity.id, type=REL_SUB_PART_2_ACTIVITY,
                )
            ],
        )
        self.assertCountEqual(
            [
                Calendar.objects.get_default_calendar(user)
                for user in (user1, user2, user3, team)
            ],
            activity.calendars.all(),
        )

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_add_participants07(self):
        "Auto-subject."
        user = self.login_as_root_and_get()
        activity = self._create_meeting(user=user)

        akane = Contact.objects.create(user=user, first_name='Akane', last_name='Tendo')
        dojo = Organisation.objects.create(user=user, name='Tendo Dojo')

        Relation.objects.create(
            user=user, subject_entity=akane,
            type_id=REL_SUB_EMPLOYED_BY, object_entity=dojo,
        )

        self.assertNoFormError(self.client.post(
            self._build_add_participants_url(activity),
            data={'participants': self.formfield_value_multi_creator_entity(akane)},
        ))
        self.assertHaveRelation(subject=dojo, type=REL_SUB_ACTIVITY_SUBJECT, object=activity)

    def test_add_participants08(self):
        "I already participate + the selected team includes me."
        user = self.login_as_root_and_get()
        other_user = self.create_user()
        team = self.create_team('A-team', user, other_user)

        activity = self._create_meeting(user=user)
        Relation.objects.create(
            user=user,
            subject_entity=user.linked_contact,
            type_id=REL_SUB_PART_2_ACTIVITY,
            object_entity=activity,
        )
        get_default_calendar = Calendar.objects.get_default_calendar
        cal1 = get_default_calendar(user)
        activity.calendars.add(cal1)

        self.assertNoFormError(self.client.post(
            self._build_add_participants_url(activity),
            data={'participating_users': [team.id]},
        ))
        self.assertHaveRelation(user.linked_contact,       REL_SUB_PART_2_ACTIVITY, activity)
        self.assertHaveRelation(other_user.linked_contact, REL_SUB_PART_2_ACTIVITY, activity)
        self.assertCountEqual(
            [cal1, get_default_calendar(other_user), get_default_calendar(team)],
            activity.calendars.all(),
        )

    @skipIfCustomContact
    def test_remove_participants01(self):
        user = self.login_as_activities_user()
        self.add_credentials(user.role, all='*')

        logged = user.linked_contact
        other = self.get_root_user().linked_contact
        contact3 = Contact.objects.create(user=user, first_name='Roy', last_name='Mustang')

        dt_now = now()
        sub_type = self._get_sub_type(UUID_SUBTYPE_PHONECALL_OUTGOING)
        phone_call = Activity.objects.create(
            title='Phone call to be deleted',
            start=dt_now, end=dt_now,
            user=user,
            type_id=sub_type.type_id, sub_type=sub_type,
        )

        self.assertPOST200(
            self._build_add_participants_url(phone_call), follow=True,
            data={
                'my_participation_0':  True,
                'my_participation_1':  Calendar.objects.get_default_calendar(logged.is_user).pk,
                'participating_users': [other.is_user_id],
                'participants':        self.formfield_value_multi_creator_entity(contact3),
            },
        )

        # Logged user, set in his calendar
        sym_rel = self.get_object_or_fail(
            Relation,
            subject_entity=logged, type=REL_SUB_PART_2_ACTIVITY, object_entity=phone_call,
        )
        # Other contact user, set in his calendar too
        self.assertHaveRelation(subject=other, type=REL_SUB_PART_2_ACTIVITY, object=phone_call)
        # Regular contact, has no calendar
        self.assertHaveRelation(subject=contact3, type=REL_SUB_PART_2_ACTIVITY, object=phone_call)
        self.assertEqual(2, phone_call.calendars.count())

        del_url = self.RM_PARTICIPANT_URL
        self.assertGET405(del_url)
        self.assertPOST404(del_url, data={'id': sym_rel.pk})
        self.assertStillExists(sym_rel)

        qs = Relation.objects.filter(
            type=REL_SUB_PART_2_ACTIVITY, object_entity=phone_call,
        )

        for participant_rel in qs.all():
            self.assertGET405(del_url)

            response = self.client.post(
                del_url, data={'id': participant_rel.symmetric_relation_id},
            )
            self.assertRedirects(response, phone_call.get_absolute_url())

        self.assertFalse(qs.all())
        self.assertFalse(phone_call.calendars.all())

    @skipIfCustomContact
    def test_remove_participants02(self):
        "Cannot unlink the contact."
        user = self.login_as_activities_user()
        self.add_credentials(user.role, all='!UNLINK', own=['VIEW', 'UNLINK'])

        contact = self.get_root_user().linked_contact
        self.assertFalse(user.has_perm_to_unlink(contact))

        sub_type = self._get_sub_type(UUID_SUBTYPE_PHONECALL_OUTGOING)
        phone_call = Activity.objects.create(
            title='A random activity',
            user=user,
            type_id=sub_type.type_id, sub_type=sub_type,
        )
        self.assertTrue(user.has_perm_to_unlink(phone_call))

        rel = Relation.objects.create(
            user=user,
            subject_entity=contact,
            type_id=REL_SUB_PART_2_ACTIVITY,
            object_entity=phone_call,
        )
        self.assertPOST403(self.RM_PARTICIPANT_URL, data={'id': rel.symmetric_relation_id})

    @skipIfCustomContact
    def test_remove_participants03(self):
        "Cannot unlink the activity."
        user = self.login_as_activities_user()
        self.add_credentials(user.role, all='!UNLINK', own=['VIEW', 'UNLINK'])

        contact = user.linked_contact
        self.assertTrue(user.has_perm_to_unlink(contact))

        sub_type = self._get_sub_type(UUID_SUBTYPE_PHONECALL_OUTGOING)
        phone_call = Activity.objects.create(
            title='A random activity',
            user=self.get_root_user(),
            type_id=sub_type.type_id, sub_type=sub_type,
        )
        self.assertFalse(user.has_perm_to_unlink(phone_call))

        rel = Relation.objects.create(
            user=user,
            subject_entity=contact,
            type_id=REL_SUB_PART_2_ACTIVITY,
            object_entity=phone_call,
        )
        self.assertPOST403(self.RM_PARTICIPANT_URL, data={'id': rel.symmetric_relation_id})

    @skipIfCustomOrganisation
    def test_add_subjects01(self):
        user = self.login_as_root_and_get()

        activity = self._create_meeting(user=user)
        orga = Organisation.objects.create(user=user, name='Ghibli')

        url = self._build_add_subjects_url(activity)
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/link-popup.html')

        context = response1.context
        self.assertEqual(
            _('Adding subjects to activity «{entity}»').format(entity=activity),
            context.get('title'),
        )
        self.assertEqual(_('Add the subjects'), context.get('submit_label'))

        # ---
        data = {'subjects': self.formfield_value_multi_generic_entity(orga)}
        self.assertNoFormError(self.client.post(url, data=data))
        self.assertCountEqual(
            [orga.id],
            [
                *Relation.objects
                         .filter(object_entity=activity.id, type=REL_SUB_ACTIVITY_SUBJECT)
                         .values_list('subject_entity_id', flat=True)
            ],
        )

        # Avoid duplicates
        response2 = self.assertPOST200(url, data=data)
        self.assertFormError(
            response2.context['form'],
            field='subjects',
            errors=ngettext(
                'This entity is already a subject: %(duplicates)s',
                'These entities are already subjects: %(duplicates)s',
                1,
            ) % {'duplicates': orga},
        )

    def test_add_subjects02(self):
        "Credentials error with the activity."
        user = self.login_as_activities_user()
        self.add_credentials(user.role, own='!LINK')

        activity = self._create_meeting(user=user)
        self.assertTrue(user.has_perm_to_change(activity))
        self.assertFalse(user.has_perm_to_link(activity))
        self.assertGET403(self._build_add_subjects_url(activity))

    @skipIfCustomOrganisation
    def test_add_subjects03(self):
        "Credentials error with selected subjects."
        user = self.login_as_activities_user()
        self.add_credentials(user.role, own=['LINK'], all='!LINK')

        activity = self._create_meeting(user=user)
        self.assertTrue(user.has_perm_to_link(activity))

        orga = Organisation.objects.create(user=self.get_root_user(), name='Ghibli')
        self.assertTrue(user.has_perm_to_change(orga))
        self.assertFalse(user.has_perm_to_link(orga))

        uri = self._build_add_subjects_url(activity)
        self.assertGET200(uri)

        response = self.assertPOST200(
            uri, data={'subjects': self.formfield_value_multi_generic_entity(orga)},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='subjects',
            errors=_('Some entities are not linkable: {}').format(orga),
        )
        self.assertFalse(Relation.objects.filter(
            object_entity=activity.id,
            type=REL_SUB_ACTIVITY_SUBJECT,
        ))

    def test_add_subjects04(self):
        "Bad ContentType (relationType constraint error)."
        user = self.login_as_root_and_get()

        create_meeting = partial(self._create_meeting, user=user)
        activity    = create_meeting(title='My meeting')
        bad_subject = create_meeting(title="I'm bad heeheeeee")

        response = self.assertPOST200(
            self._build_add_subjects_url(activity),
            data={'subjects': self.formfield_value_multi_generic_entity(bad_subject)},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='subjects', errors=_('This content type is not allowed.'),
        )

    @skipIfCustomContact
    def test_remove_subject01(self):
        user = self.login_as_activities_user()
        self.add_credentials(user.role, own='*')

        activity = self._create_meeting(user=user)
        contact = Contact.objects.create(user=user, first_name='Musashi', last_name='Miyamoto')

        create_rel = partial(
            Relation.objects.create,
            subject_entity=contact, object_entity=activity, user=user,
        )
        r1 = create_rel(type_id=REL_SUB_PART_2_ACTIVITY)
        r2 = create_rel(type_id=REL_SUB_ACTIVITY_SUBJECT)
        r3 = create_rel(type_id=REL_SUB_LINKED_2_ACTIVITY)
        r4 = create_rel(type_id=REL_SUB_HAS)

        url = self.RM_SUBJECT_URL
        self.assertGET405(url)

        response = self.assertPOST200(url, data={'id': r2.symmetric_relation_id}, follow=True)
        self.assertDoesNotExist(r2)
        self.assertRedirects(response, activity.get_absolute_url())

        # Errors
        self.assertPOST404(url, data={'id': r1.symmetric_relation_id})
        self.assertPOST404(url, data={'id': r3.symmetric_relation_id})
        self.assertPOST404(url, data={'id': r4.symmetric_relation_id})
        self.assertPOST404(url)

    @skipIfCustomContact
    def test_remove_subject02(self):
        "Can not unlink the activity."
        user = self.login_as_standard()
        self.add_credentials(user.role, own='!UNLINK')

        activity = self._create_meeting(user=user)
        contact = Contact.objects.create(user=user, first_name='Musashi', last_name='Miyamoto')
        relation = Relation.objects.create(
            subject_entity=contact,
            type_id=REL_SUB_ACTIVITY_SUBJECT,
            object_entity=activity,
            user=user,
        )

        self.assertPOST403(
            self.RM_SUBJECT_URL,
            data={'id': relation.symmetric_relation_id},
        )
        self.assertStillExists(relation)

    @skipIfCustomContact
    def test_remove_subject03(self):
        "Can not unlink the contact."
        user = self.login_as_standard()
        self.add_credentials(user.role, all='!UNLINK', own='*')

        activity = self._create_meeting(user=user)
        contact = Contact.objects.create(
            user=self.get_root_user(), first_name='Musashi', last_name='Miyamoto',
        )
        relation = Relation.objects.create(
            subject_entity=contact,
            type_id=REL_SUB_ACTIVITY_SUBJECT,
            object_entity=activity,
            user=user,
        )
        self.assertPOST403(
            self.RM_SUBJECT_URL,
            data={'id': relation.symmetric_relation_id},
        )
        self.assertStillExists(relation)

    @skipIfCustomContact
    def test_unlink01(self):
        user = self.login_as_activities_user()
        self.add_credentials(user.role, own='*')

        activity = self._create_meeting(user=user)
        contact = Contact.objects.create(user=user, first_name='Musashi', last_name='Miyamoto')

        create_rel = partial(
            Relation.objects.create,
            subject_entity=contact, object_entity=activity, user=user,
        )
        r1 = create_rel(type_id=REL_SUB_PART_2_ACTIVITY)
        r2 = create_rel(type_id=REL_SUB_ACTIVITY_SUBJECT)
        r3 = create_rel(type_id=REL_SUB_LINKED_2_ACTIVITY)
        r4 = create_rel(type_id=REL_SUB_HAS)
        self.assertEqual(3, contact.relations.filter(pk__in=[r1.id, r2.id, r3.id]).count())

        url = self.RM_RELATED_URL
        self.assertPOST200(url, data={'id': activity.id, 'object_id': contact.id}, follow=True)
        self.assertFalse(contact.relations.filter(pk__in=[r1.id, r2.id, r3.id]))
        self.assertEqual(1, contact.relations.filter(pk=r4.id).count())

        # Errors
        self.assertPOST404(url, data={'id': activity.id})
        self.assertPOST404(url, data={'object_id': contact.id})
        self.assertPOST404(url)
        self.assertPOST404(url, data={'id': self.UNUSED_PK, 'object_id': contact.id})
        self.assertPOST404(url, data={'id': activity.id,    'object_id': self.UNUSED_PK})

    @skipIfCustomContact
    def test_unlink02(self):
        "Can not unlink the activity."
        user = self.login_as_standard()
        self.add_credentials(user.role, own='!UNLINK')

        activity = self._create_meeting(user=user)
        contact = Contact.objects.create(user=user, first_name='Musashi', last_name='Miyamoto')
        relation = Relation.objects.create(
            subject_entity=contact, type_id=REL_SUB_PART_2_ACTIVITY,
            object_entity=activity, user=user,
        )
        self.assertPOST403(
            self.RM_RELATED_URL,
            data={'id': activity.id, 'object_id': contact.id},
        )
        self.assertStillExists(relation)

    @skipIfCustomContact
    def test_unlink03(self):
        "Can not unlink the contact."
        user = self.login_as_standard()
        self.add_credentials(user.role, all='!UNLINK', own='*')

        activity = self._create_meeting(user=user)
        contact = Contact.objects.create(
            user=self.get_root_user(), first_name='Musashi', last_name='Miyamoto',
        )
        relation = Relation.objects.create(
            subject_entity=contact,
            type_id=REL_SUB_PART_2_ACTIVITY,
            object_entity=activity, user=user,
        )

        self.assertPOST403(
            self.RM_RELATED_URL,
            data={'id': activity.id, 'object_id': contact.id},
        )
        self.assertStillExists(relation)

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

    def test_activity_fullcalendar(self):
        user = self.login_as_activities_user()

        ranma = Contact.objects.create(user=user, first_name='Ranma', last_name='Saotome')

        default_cal = Calendar.objects.get_default_calendar(user)
        Calendar.objects.create(user=user, name='Other calendar')

        brick = MyActivitiesCalendarBrick()

        with override_tz('Europe/London'):
            dst_date = self.create_datetime(2023, 8, 1)

            with patch('creme.activities.utils.now', return_value=dst_date):
                render = brick.home_display(
                    context=self.build_context(user=user, instance=ranma),
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
