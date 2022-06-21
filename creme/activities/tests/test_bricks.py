# -*- coding: utf-8 -*-

from datetime import timedelta
from functools import partial

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.backends.base import SessionBase
from django.test import RequestFactory
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.gui.bricks import BricksManager
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    Relation,
    SetCredentials,
    SettingValue,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from ..bricks import (
    FutureActivitiesBrick,
    ParticipantsBrick,
    PastActivitiesBrick,
    RelatedCalendarBrick,
    SubjectsBrick,
    UserCalendarsBrick,
)
from ..constants import (
    ACTIVITYSUBTYPE_MEETING_NETWORK,
    ACTIVITYTYPE_MEETING,
    ACTIVITYTYPE_PHONECALL,
    FLOATING,
    REL_SUB_ACTIVITY_SUBJECT,
    REL_SUB_LINKED_2_ACTIVITY,
    REL_SUB_PART_2_ACTIVITY,
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

    @staticmethod
    def _build_add_participants_url(activity):
        return reverse('activities__add_participants', args=(activity.id,))

    @staticmethod
    def _build_add_subjects_url(activity):
        return reverse('activities__add_subjects', args=(activity.id,))

    @skipIfCustomContact
    def test_participants_brick(self):
        ParticipantsBrick.page_size = max(4, settings.BLOCK_SIZE)

        user = self.login()
        activity = self._create_meeting()

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

        brick = ParticipantsBrick()

        request = RequestFactory().get(activity.get_absolute_url())
        request.session = SessionBase()
        request.user = user

        ContentType.objects.get_for_model(Relation)  # Fill cache

        # Queries:
        #   - COUNT Relation
        #   - BrickState
        #   - SettingValue "is open"
        #   - Relation
        #   - Contact (with user/is_user/civility)
        #   - Calendar
        with self.assertNumQueries(6):
            render = brick.detailview_display({
                'object': activity,
                'request': request,
                'user': user,
                BricksManager.var_name: BricksManager(),
            })

        tree = self.get_html_tree(render)
        brick_node = self.get_brick_node(tree, ParticipantsBrick.id_)
        self.assertInstanceLink(brick_node, c1)
        self.assertInstanceLink(brick_node, c2)
        self.assertNoInstanceLink(brick_node, c3)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_subjects_brick(self):
        SubjectsBrick.page_size = max(4, settings.BLOCK_SIZE)

        user = self.login()
        activity = self._create_meeting()

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

        brick = SubjectsBrick()

        request = RequestFactory().get(activity.get_absolute_url())
        request.session = SessionBase()
        request.user = user

        ContentType.objects.get_for_model(Relation)  # Fill cache

        # Queries:
        #   - COUNT Relation
        #   - BrickState
        #   - SettingValue "is open"
        #   - Relation
        #   - Contact
        #   - Organisation
        with self.assertNumQueries(6):
            render = brick.detailview_display({
                'object': activity,
                'request': request,
                'user': user,
                BricksManager.var_name: BricksManager(),
            })

        tree = self.get_html_tree(render)
        brick_node = self.get_brick_node(tree, SubjectsBrick.id_)
        self.assertInstanceLink(brick_node, c2)
        self.assertInstanceLink(brick_node, c3)
        self.assertInstanceLink(brick_node, orga)
        self.assertNoInstanceLink(brick_node, c1)

    # TODO: assertNumQueries on other type of Bricks

    @skipIfCustomContact
    def test_bricks_activity(self):
        ParticipantsBrick.page_size = SubjectsBrick.page_size = max(4, settings.BLOCK_SIZE)

        user = self.login()
        activity = self._create_meeting()

        create_contact = partial(Contact.objects.create, user=user)
        c1 = user.linked_contact
        c2 = create_contact(first_name='Musashi', last_name='Miyamoto')
        c3 = create_contact(first_name='Kojiro',  last_name='Sasaki')
        c4 = create_contact(first_name='Seijuro', last_name='Yoshioka')
        c5 = self.other_user.linked_contact

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
        self.assertTemplateUsed(response, 'activities/bricks/activity-hat-bar.html')

        tree = self.get_html_tree(response.content)

        brick_node1 = self.get_brick_node(tree, ParticipantsBrick.id_)
        self.assertInstanceLink(brick_node1, c1)
        self.assertInstanceLink(brick_node1, c2)
        self.assertNoInstanceLink(brick_node1, c3)
        self.assertNoInstanceLink(brick_node1, c4)
        self.assertNoInstanceLink(brick_node1, c5)

        brick_node2 = self.get_brick_node(tree, SubjectsBrick.id_)
        self.assertInstanceLink(brick_node2, c3)
        self.assertInstanceLink(brick_node2, c4)
        self.assertNoInstanceLink(brick_node2, c1)
        self.assertNoInstanceLink(brick_node2, c2)
        self.assertNoInstanceLink(brick_node2, c5)

        brick_node3 = self.get_brick_node(tree, RelatedCalendarBrick.id_)
        self.assertListEqual(
            [f'background-color:#{cal.get_color};'],
            [
                n.attrib.get('style')
                for n in brick_node3.findall('.//div[@class="activity-calendar-color-square"]')
            ]
        )

    @skipIfCustomContact
    def test_bricks_future_n_past01(self):
        "Contacts + display minutes."
        FutureActivitiesBrick.page_size = max(10, settings.BLOCK_SIZE)
        PastActivitiesBrick.page_size = max(10, settings.BLOCK_SIZE)

        user = self.login()

        now_value = now()
        today8 = self.create_datetime(
            year=now_value.year, month=now_value.month, day=now_value.day,
            hour=8,
        )
        one_day = timedelta(days=1)
        tomorrow = today8 + one_day
        yesterday = today8 - one_day

        create_activity = partial(
            Activity.objects.create,
            user=user, type_id=ACTIVITYTYPE_MEETING, sub_type_id=ACTIVITYSUBTYPE_MEETING_NETWORK,
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

        contact = self.other_user.linked_contact
        create_rel = partial(Relation.objects.create, user=user, subject_entity=contact)
        create_rel(object_entity=future[0], type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(object_entity=future[1], type_id=REL_SUB_ACTIVITY_SUBJECT)
        create_rel(object_entity=future[2], type_id=REL_SUB_LINKED_2_ACTIVITY)

        create_rel(object_entity=past[0], type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(object_entity=past[1], type_id=REL_SUB_ACTIVITY_SUBJECT)
        create_rel(object_entity=past[2], type_id=REL_SUB_LINKED_2_ACTIVITY)

        create_brick_detail = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            model=Contact, zone=BrickDetailviewLocation.RIGHT,
        )
        create_brick_detail(brick=FutureActivitiesBrick, order=50)
        create_brick_detail(brick=PastActivitiesBrick,   order=51)

        sv = SettingValue.objects.get_4_key(review_key)
        sv.value = True
        sv.save()

        response = self.assertGET200(contact.get_absolute_url())
        tree = self.get_html_tree(response.content)

        future_brick_node = self.get_brick_node(tree, FutureActivitiesBrick.id_)
        self.assertInstanceLink(future_brick_node, future[0])
        self.assertInstanceLink(future_brick_node, future[1])
        self.assertInstanceLink(future_brick_node, future[2])
        self.assertNoInstanceLink(future_brick_node, future[3])
        self.assertNoInstanceLink(future_brick_node, past[0])

        future_minutes = {
            n.text
            for n in future_brick_node.findall('.//div[@class="activity-group-value"]/p')
        }
        self.assertIn(future[0].minutes, future_minutes)
        self.assertIn(future[1].minutes, future_minutes)
        self.assertIn(future[2].minutes, future_minutes)
        self.assertNotIn(future[3].minutes, future_minutes)

        past_brick_node = self.get_brick_node(tree, PastActivitiesBrick.id_)
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

        user = self.login()

        now_value = now()
        today8 = self.create_datetime(
            year=now_value.year, month=now_value.month, day=now_value.day,
            hour=8,
        )
        one_day = timedelta(days=1)
        tomorrow = today8 + one_day
        yesterday = today8 - one_day

        create_activity = partial(
            Activity.objects.create,
            user=user, type_id=ACTIVITYTYPE_MEETING, sub_type_id=ACTIVITYSUBTYPE_MEETING_NETWORK,
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

        BrickHomeLocation.objects.get_or_create(
            brick_id=FutureActivitiesBrick.id_, defaults={'order': 10},
        )
        BrickHomeLocation.objects.get_or_create(
            brick_id=PastActivitiesBrick.id_, defaults={'order': 11},
        )

        response1 = self.assertGET200(reverse('creme_core__home'))
        tree = self.get_html_tree(response1.content)

        future_brick_node = self.get_brick_node(tree, FutureActivitiesBrick.id_)
        self.assertInstanceLink(future_brick_node, future[0])
        self.assertInstanceLink(future_brick_node, future[1])
        self.assertInstanceLink(future_brick_node, future[2])
        self.assertNoInstanceLink(future_brick_node, future[3])
        self.assertNoInstanceLink(future_brick_node, past[0])

        past_brick_node = self.get_brick_node(tree, PastActivitiesBrick.id_)
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

        user = self.login()

        now_value = now()
        today8 = self.create_datetime(
            year=now_value.year, month=now_value.month, day=now_value.day,
            hour=8,
        )
        one_day = timedelta(days=1)
        tomorrow = today8 + one_day
        yesterday = today8 - one_day

        create_activity = partial(
            Activity.objects.create,
            user=user, type_id=ACTIVITYTYPE_MEETING, sub_type_id=ACTIVITYSUBTYPE_MEETING_NETWORK,
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

        future_brick_node = self.get_brick_node(tree, FutureActivitiesBrick.id_)
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

        past_brick_node = self.get_brick_node(tree, PastActivitiesBrick.id_)
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
    def test_add_participants01(self):
        user = self.login()
        activity = self._create_meeting()

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

        relations = Relation.objects.filter(
            object_entity=activity.id, type=REL_SUB_PART_2_ACTIVITY,
        )
        self.assertEqual(2, len(relations))
        self.assertSetEqual({c1.id, c2.id}, {r.subject_entity_id for r in relations})

    def test_add_participants02(self):
        "Credentials error with the activity."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

        activity = self._create_meeting()
        self.assertTrue(user.has_perm_to_change(activity))
        self.assertFalse(user.has_perm_to_link(activity))
        self.assertGET403(self._build_add_participants_url(activity))

    @skipIfCustomContact
    def test_add_participants03(self):
        "Credentials error with selected subjects."
        user = self.login(is_superuser=False)
        self._build_nolink_setcreds()

        activity = self._create_meeting()
        self.assertTrue(user.has_perm_to_link(activity))

        contact = Contact.objects.create(
            user=self.other_user, first_name='Musashi', last_name='Miyamoto',
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
            response, 'form', 'participants',
            _('Some entities are not linkable: {}').format(contact),
        )
        self.assertFalse(Relation.objects.filter(
            object_entity=activity.id,
            type=REL_SUB_PART_2_ACTIVITY,
        ))

    @skipIfCustomContact
    def test_add_participants04(self):
        "'My participation' field is removed when it is useless."
        activity = self._create_activity_by_view()

        create_contact = partial(Contact.objects.create, user=self.user)
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

        relations = Relation.objects.filter(
            object_entity=activity.id, type=REL_SUB_PART_2_ACTIVITY,
        )
        self.assertEqual(3, len(relations))
        self.assertSetEqual(
            {c1.id, c2.id, self.user.linked_contact.id},
            {r.subject_entity_id for r in relations},
        )

    @skipIfCustomContact
    def test_add_participants05(self):
        "Fix a bug when checking for collision for a floating activities."
        activity = self._create_activity_by_view()
        self.assertIsNone(activity.start)
        self.assertIsNone(activity.end)
        self.assertEqual(FLOATING, activity.floating_type)

        create_contact = partial(Contact.objects.create, user=self.user)
        c1 = create_contact(first_name='Musashi', last_name='Miyamoto')
        c2 = create_contact(first_name='Kojiro',  last_name='Sasaki')

        uri = self._build_add_participants_url(activity)
        self.assertGET200(uri)
        self.assertNoFormError(self.client.post(
            uri,
            data={'participants': self.formfield_value_multi_creator_entity(c1, c2)},
        ))

        relations = Relation.objects.filter(
            object_entity=activity.id, type=REL_SUB_PART_2_ACTIVITY,
        )
        self.assertEqual(3, len(relations))
        self.assertSetEqual(
            {c1.id, c2.id, self.user.linked_contact.id},
            {r.subject_entity_id for r in relations},
        )

    def test_add_participants06(self):
        "When Teams are selected, their teammates are participants."
        user = self.login()
        activity = self._create_meeting()

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
        team.teammates = [musashi, kojiro, user]

        response = self.client.post(
            self._build_add_participants_url(activity),
            data={
                'my_participation_0':  True,
                'my_participation_1':  Calendar.objects.get_default_calendar(user).pk,
                'participating_users': [team.id, kojiro.id],
            },
        )
        self.assertNoFormError(response)

        relations = Relation.objects.filter(
            object_entity=activity.id, type=REL_SUB_PART_2_ACTIVITY,
        )
        self.assertEqual(3, len(relations))
        self.assertSetEqual(
            {musashi.linked_contact, kojiro.linked_contact, user.linked_contact},
            {r.subject_entity.get_real_entity() for r in relations},
        )

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_add_participants07(self):
        "Auto-subject."
        user = self.login()
        activity = self._create_meeting()

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

        self.assertRelationCount(1, dojo, REL_SUB_ACTIVITY_SUBJECT, activity)

    @skipIfCustomContact
    def test_remove_participants01(self):
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        logged = user.linked_contact
        other = self.other_user.linked_contact
        contact3 = Contact.objects.create(user=user, first_name='Roy', last_name='Mustang')

        dt_now = now()
        phone_call = Activity.objects.create(
            title='a random activity',
            start=dt_now, end=dt_now,
            user=user, type_id=ACTIVITYTYPE_PHONECALL,
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
        self.assertRelationCount(1, logged,   REL_SUB_PART_2_ACTIVITY, phone_call)
        # Other contact user, set in his calendar too
        self.assertRelationCount(1, other,    REL_SUB_PART_2_ACTIVITY, phone_call)
        # Regular contact, has no calendar
        self.assertRelationCount(1, contact3, REL_SUB_PART_2_ACTIVITY, phone_call)
        self.assertEqual(2, phone_call.calendars.count())

        sym_rel = Relation.objects.get(
            subject_entity=logged,
            type=REL_SUB_PART_2_ACTIVITY,
            object_entity=phone_call,
        )

        del_url = self.RM_PARTICIPANT_URL
        self.assertGET405(del_url)
        self.assertPOST404(del_url, data={'id': sym_rel.pk})
        self.get_object_or_fail(Relation, pk=sym_rel.pk)

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
        "Cannot unlink the contact"
        user = self.login(is_superuser=False)
        create_creds = partial(SetCredentials.objects.create, role=self.role)
        create_creds(
            value=EntityCredentials.VIEW | EntityCredentials.UNLINK,
            set_type=SetCredentials.ESET_OWN,
        )
        create_creds(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        contact = self.other_user.linked_contact
        self.assertFalse(user.has_perm_to_unlink(contact))

        phone_call = Activity.objects.create(
            title='A random activity',
            user=user, type_id=ACTIVITYTYPE_PHONECALL,
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
        user = self.login(is_superuser=False)
        create_creds = partial(SetCredentials.objects.create, role=self.role)
        create_creds(
            value=EntityCredentials.VIEW | EntityCredentials.UNLINK,
            set_type=SetCredentials.ESET_OWN,
        )
        create_creds(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        contact = user.linked_contact
        self.assertTrue(user.has_perm_to_unlink(contact))

        phone_call = Activity.objects.create(
            title='A random activity',
            user=self.other_user, type_id=ACTIVITYTYPE_PHONECALL,
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
        user = self.login()

        activity = self._create_meeting()
        orga = Organisation.objects.create(user=user, name='Ghibli')

        url = self._build_add_subjects_url(activity)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(
            _('Adding subjects to activity «{entity}»').format(entity=activity),
            context.get('title'),
        )
        self.assertEqual(_('Add the subjects'), context.get('submit_label'))

        # ---
        data = {'subjects': self.formfield_value_multi_generic_entity(orga)}
        self.assertNoFormError(self.client.post(url, data=data))

        relations = Relation.objects.filter(
            object_entity=activity.id, type=REL_SUB_ACTIVITY_SUBJECT,
        )
        self.assertEqual(1, len(relations))
        self.assertEqual(orga.id, relations[0].subject_entity_id)

        # Avoid duplicates
        response = self.assertPOST200(url, data=data)
        self.assertFormError(
            response, 'form', 'subjects',
            ngettext(
                'This entity is already a subject: %(duplicates)s',
                'These entities are already subjects: %(duplicates)s',
                1,
            ) % {'duplicates': orga},
        )

    def test_add_subjects02(self):
        "Credentials error with the activity."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

        activity = self._create_meeting()
        self.assertTrue(user.has_perm_to_change(activity))
        self.assertFalse(user.has_perm_to_link(activity))
        self.assertGET403(self._build_add_subjects_url(activity))

    @skipIfCustomOrganisation
    def test_add_subjects03(self):
        "Credentials error with selected subjects."
        user = self.login(is_superuser=False)
        self._build_nolink_setcreds()

        activity = self._create_meeting()
        self.assertTrue(user.has_perm_to_link(activity))

        orga = Organisation.objects.create(user=self.other_user, name='Ghibli')
        self.assertTrue(user.has_perm_to_change(orga))
        self.assertFalse(user.has_perm_to_link(orga))

        uri = self._build_add_subjects_url(activity)
        self.assertGET200(uri)

        response = self.assertPOST200(
            uri,
            data={'subjects': self.formfield_value_multi_generic_entity(orga)},
        )
        self.assertFormError(
            response, 'form', 'subjects',
            _('Some entities are not linkable: {}').format(orga)
        )
        self.assertFalse(Relation.objects.filter(
            object_entity=activity.id,
            type=REL_SUB_ACTIVITY_SUBJECT,
        ))

    def test_add_subjects04(self):
        "Bad ContentType (relationType constraint error)."
        self.login()

        create_meeting = self._create_meeting
        activity    = create_meeting(title='My meeting')
        bad_subject = create_meeting(title="I'm bad heeheeeee")

        response = self.assertPOST200(
            self._build_add_subjects_url(activity),
            data={'subjects': self.formfield_value_multi_generic_entity(bad_subject)},
        )
        self.assertFormError(
            response, 'form', 'subjects', _('This content type is not allowed.')
        )

    @skipIfCustomContact
    def test_unlink01(self):
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

        activity = self._create_meeting()
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

        url = reverse('activities__unlink_activity')
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
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

        activity = self._create_meeting()
        contact = Contact.objects.create(user=user, first_name='Musashi', last_name='Miyamoto')
        relation = Relation.objects.create(
            subject_entity=contact, type_id=REL_SUB_PART_2_ACTIVITY,
            object_entity=activity, user=user,
        )

        self.assertPOST403(
            reverse('activities__unlink_activity'),
            data={'id': activity.id, 'object_id': contact.id},
        )
        self.assertEqual(1, contact.relations.filter(pk=relation.id).count())

    @skipIfCustomContact
    def test_unlink03(self):
        "Can not unlink the contact."
        user = self.login(is_superuser=False)

        create_creds = partial(SetCredentials.objects.create, role=self.role)
        create_creds(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )
        create_creds(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        activity = self._create_meeting()
        contact = Contact.objects.create(
            user=self.other_user, first_name='Musashi', last_name='Miyamoto',
        )
        relation = Relation.objects.create(
            subject_entity=contact,
            type_id=REL_SUB_PART_2_ACTIVITY,
            object_entity=activity, user=user,
        )

        self.assertPOST403(
            reverse('activities__unlink_activity'),
            data={'id': activity.id, 'object_id': contact.id},
        )
        self.get_object_or_fail(Relation, pk=relation.id)

    def test_user_calendars(self):
        user = self.login()
        UserCalendarsBrick.page_size = max(3, settings.BLOCK_SIZE)

        cal1 = Calendar.objects.get_default_calendar(user)
        cal2 = Calendar.objects.create(user=user, name='Other calendar')

        response = self.assertGET200(reverse('creme_config__user_settings'))
        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, UserCalendarsBrick.id_)

        self.assertCountEqual(
            [f'background-color:#{cal.get_color};' for cal in [cal1, cal2]],
            [
                n.attrib.get('style')
                # TODO: make uniform?
                # for n in brick_node.findall('.//div[@class="activity-calendar-color-square"]')
                for n in brick_node.findall('.//div[@class="colored-square"]')
            ],
        )
