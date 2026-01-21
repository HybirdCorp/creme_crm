from functools import partial

from django.conf import settings
from django.urls import reverse
from django.utils.encoding import force_str

from creme.activities import bricks, constants
from creme.activities.models import Calendar
from creme.activities.tests.base import (
    Activity,
    Contact,
    _ActivitiesTestCase,
    skipIfCustomActivity,
)
from creme.creme_core.models import Relation
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.media import get_creme_media_url
from creme.persons.tests.base import skipIfCustomContact


@skipIfCustomActivity
class ActivityMiscViewsTestCase(BrickTestCaseMixin, _ActivitiesTestCase):
    def test_detail_view__meeting(self):
        user = self.login_as_root_and_get()
        self.assertEqual('icecream', user.theme)

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_MEETING)
        activity = Activity.objects.create(
            user=user, title='Meeting #1',
            type_id=sub_type.type_id, sub_type=sub_type,
        )

        response = self.assertGET200(activity.get_absolute_url())
        brick_node = self.get_brick_node(
            tree=self.get_html_tree(response.content),
            brick=bricks.ActivityCardHatBrick,
        )
        icon_node = self.get_html_node_or_fail(brick_node, './/div[@class="card-icon"]/div/img')
        self.assertEqual(
            get_creme_media_url(theme='icecream', url='images/meeting_22.png'),
            icon_node.attrib.get('src'),
        )

    def test_detail_view__phone_call(self):
        user = self.login_as_root_and_get()
        self.assertEqual('icecream', user.theme)

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_PHONECALL_OUTGOING)
        activity = Activity.objects.create(
            user=user, title='Phone call #1',
            type_id=sub_type.type_id, sub_type=sub_type,
        )

        response = self.assertGET200(activity.get_absolute_url())
        brick_node = self.get_brick_node(
            tree=self.get_html_tree(response.content),
            brick=bricks.ActivityCardHatBrick,
        )
        icon_node = self.get_html_node_or_fail(brick_node, './/div[@class="card-icon"]/div/img')
        self.assertEqual(
            get_creme_media_url(theme='icecream', url='images/phone_22.png'),
            icon_node.attrib.get('src'),
        )

    @skipIfCustomContact
    def test_detail_view__bricks(self):
        bricks.ParticipantsBrick.page_size = bricks.SubjectsBrick.page_size =\
            max(4, settings.BLOCK_SIZE)

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
        create_rel(subject_entity=c1, type_id=constants.REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=c2, type_id=constants.REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=c3, type_id=constants.REL_SUB_ACTIVITY_SUBJECT)
        create_rel(subject_entity=c4, type_id=constants.REL_SUB_ACTIVITY_SUBJECT)

        cal = Calendar.objects.get_default_calendar(user)
        activity.calendars.add(cal)

        response = self.assertGET200(activity.get_absolute_url())
        self.assertTemplateUsed(response, 'activities/bricks/activity-hat-card.html')

        tree = self.get_html_tree(response.content)

        brick_node1 = self.get_brick_node(tree, bricks.ParticipantsBrick)
        self.assertInstanceLink(brick_node1, c1)
        self.assertInstanceLink(brick_node1, c2)
        self.assertNoInstanceLink(brick_node1, c3)
        self.assertNoInstanceLink(brick_node1, c4)
        self.assertNoInstanceLink(brick_node1, c5)

        brick_node2 = self.get_brick_node(tree, bricks.SubjectsBrick)
        self.assertInstanceLink(brick_node2, c3)
        self.assertInstanceLink(brick_node2, c4)
        self.assertNoInstanceLink(brick_node2, c1)
        self.assertNoInstanceLink(brick_node2, c2)
        self.assertNoInstanceLink(brick_node2, c5)

        brick_node3 = self.get_brick_node(tree, bricks.RelatedCalendarBrick)
        self.assertListEqual(
            [f'background-color:#{cal.color};'],
            [
                n.attrib.get('style')
                for n in brick_node3.findall('.//div[@class="activity-calendar-color-square"]')
            ],
        )

    def test_popup_view(self):
        user = self.login_as_root_and_get()

        create_dt = partial(self.create_datetime, year=2010, month=10, day=1)
        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_MEETING)
        activity = Activity.objects.create(
            user=user, title='Meet01',
            type_id=sub_type.type_id, sub_type=sub_type,
            start=create_dt(hour=14, minute=0),
            end=create_dt(hour=15, minute=0),
        )
        response = self.client.get(
            reverse('activities__view_activity_popup', args=(activity.id,))
        )
        self.assertContains(response, activity.type)

    def test_list_views(self):
        user = self.login_as_root_and_get()
        self.assertFalse(Activity.objects.all())

        create_act = partial(Activity.objects.create, user=user)
        create_dt = self.create_datetime
        sub_type1 = self._get_sub_type(constants.UUID_SUBTYPE_PHONECALL_INCOMING)
        sub_type2 = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_REVIVAL)
        acts = [
            create_act(
                title='call01',
                type_id=sub_type1.type_id, sub_type=sub_type1,
                start=create_dt(year=2010, month=10, day=1, hour=12, minute=0),
                end=create_dt(year=2010, month=10, day=1, hour=13, minute=0),
            ),
            create_act(
                title='meet01',
                type_id=sub_type2.type_id, sub_type=sub_type2,
                start=create_dt(year=2010, month=10, day=1, hour=14, minute=0),
                end=create_dt(year=2010, month=10, day=1, hour=15, minute=0),
            ),
        ]

        response = self.assertGET200(Activity.get_lv_absolute_url())

        with self.assertNoException():
            activities_page = response.context['page_obj']

        self.assertEqual(1, activities_page.number)
        self.assertEqual(2, activities_page.paginator.count)
        self.assertCountEqual(acts, activities_page.object_list)

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

    def test_dl_ical(self):
        user = self.login_as_root_and_get()

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_MEETING)
        create_act = partial(
            Activity.objects.create,
            user=user, busy=True,
            type_id=sub_type.type_id, sub_type=sub_type,
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
        create_act(  # Not used
            title='Act#3',
            start=create_dt(year=2013, month=4, day=3, hour=9),
            end=create_dt(year=2013,   month=4, day=3, hour=10),
        )

        response = self.assertGET200(
            reverse('activities__dl_ical'), data={'id': [act1.id, act2.id]},
        )
        self.assertEqual('text/calendar', response['Content-Type'])
        self.assertEqual('attachment; filename="Calendar.ics"', response['Content-Disposition'])

        content = force_str(response.content)
        self.assertStartsWith(
            content,
            'BEGIN:VCALENDAR\n'
            'VERSION:2.0\n'
        )
        self.assertIn(f'UID:{act2.uuid}\n', content)
        self.assertIn(f'UID:{act1.uuid}\n', content)
        self.assertCountOccurrences('UID:', content, 2)
        self.assertEndsWith(content, 'END:VEVENT\nEND:VCALENDAR')

        # TODO: test view permission
