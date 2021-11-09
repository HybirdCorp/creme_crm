# -*- coding: utf-8 -*-

from datetime import timedelta
from functools import partial

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    FakeContact,
    FakeOrganisation,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from ..bricks import ActionsNotOnTimeBrick, ActionsOnTimeBrick
from ..models import Action
from .base import AssistantsTestCase


class ActionTestCase(BrickTestCaseMixin, AssistantsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.get_ct = ContentType.objects.get_for_model

    @staticmethod
    def _build_add_url(entity):
        return reverse('assistants__create_action', args=(entity.id,))

    def _create_action(self, deadline, title='TITLE', descr='DESCRIPTION',
                       reaction='REACTION', entity=None, user=None,
                       ):
        entity = entity or self.entity
        user = user or self.user
        response = self.client.post(
            self._build_add_url(entity),
            data={
                'user':              user.pk,
                'title':             title,
                'description':       descr,
                'expected_reaction': reaction,
                'deadline':          deadline,
            },
        )
        self.assertNoFormError(response)

        return self.get_object_or_fail(Action, title=title, description=descr)

    def test_create(self):
        self.assertFalse(Action.objects.exists())

        entity = self.entity
        context = self.assertGET200(self._build_add_url(entity)).context
        self.assertEqual(
            _('New action for «{entity}»').format(entity=entity),
            context.get('title'),
        )
        self.assertEqual(
            pgettext('assistants', 'Save the action'),
            context.get('submit_label'),
        )

        title = 'TITLE'
        descr = 'DESCRIPTION'
        reaction = 'REACTION'
        deadline = '2010-12-24'
        action = self._create_action(deadline, title, descr, reaction)

        self.assertEqual(title,     action.title)
        self.assertEqual(descr,     action.description)
        self.assertEqual(reaction,  action.expected_reaction)
        self.assertEqual(self.user, action.user)

        self.assertEqual(entity.entity_type_id, action.entity_content_type_id)
        self.assertEqual(entity.id,             action.entity_id)
        self.assertEqual(entity.id,             action.creme_entity.id)

        self.assertDatetimesAlmostEqual(now(), action.creation_date)
        self.assertEqual(
            self.create_datetime(year=2010, month=12, day=24),
            action.deadline,
        )

        self.assertEqual(title, str(action))

        create_bdl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            model=FakeContact, zone=BrickDetailviewLocation.RIGHT,
        )
        create_bdl(brick=ActionsOnTimeBrick,    order=500)
        create_bdl(brick=ActionsNotOnTimeBrick, order=501)

        response = self.assertGET200(entity.get_absolute_url())
        self.assertTemplateUsed(response, 'assistants/bricks/actions-on-time.html')
        self.assertTemplateUsed(response, 'assistants/bricks/actions-not-on-time.html')

    def test_edit(self):
        title = 'TITLE'
        descr = 'DESCRIPTION'
        reaction = 'REACTION'
        action = self._create_action('2010-12-24', title, descr, reaction)

        url = action.get_edit_absolute_url()
        context = self.assertGET200(url).context
        self.assertEqual(
            _('Action for «{entity}»').format(entity=self.entity),
            context.get('title'),
        )

        # ---
        title    += '_edited'
        descr    += '_edited'
        reaction += '_edited'
        deadline = '2011-11-25'
        response = self.client.post(
            url,
            data={
                'user':              self.user.pk,
                'title':             title,
                'description':       descr,
                'expected_reaction': reaction,
                'deadline':          deadline,
                'deadline_time':     '17:37:00',
            },
        )
        self.assertNoFormError(response)

        action = self.refresh(action)
        self.assertEqual(title,    action.title)
        self.assertEqual(descr,    action.description)
        self.assertEqual(reaction, action.expected_reaction)
        self.assertEqual(
            self.create_datetime(year=2011, month=11, day=25, hour=17, minute=37),
            action.deadline,
        )

    def test_delete_entity01(self):
        action = self._create_action('2010-12-24', 'title', 'descr', 'reaction')
        self.entity.delete()
        self.assertDoesNotExist(action)

    def _aux_test_delete(self, ajax=False):
        action = self._create_action('2010-12-24', 'title', 'descr', 'reaction')
        ct = self.get_ct(Action)
        kwargs = {} if not ajax else {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.post(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': action.id},
            **kwargs
        )
        self.assertDoesNotExist(action)

        return response

    def test_delete_action01(self):
        response = self._aux_test_delete()
        self.assertRedirects(response, self.entity.get_absolute_url())

    def test_delete_action02(self):
        "Ajax version."
        response = self._aux_test_delete(ajax=True)
        self.assertEqual(200, response.status_code)

    def test_brick(self):
        entity1 = self.entity
        entity2 = FakeOrganisation.objects.create(user=self.user, name='Acme')

        now_value = now()

        create_action = self._create_action
        action_ok1 = create_action(
            entity=entity1, deadline=now_value + timedelta(days=1), title='Recall',
        )
        action_ok2 = create_action(
            entity=entity1, deadline=now_value + timedelta(days=2), title="It's important",
        )
        action_ok3 = create_action(
            entity=entity2, deadline=now_value + timedelta(days=2), title='Other',
        )

        action_ko1 = create_action(
            entity=entity1, deadline=now_value - timedelta(days=1), title='Too late',
        )
        action_ko2 = create_action(
            entity=entity1, deadline=now_value - timedelta(days=2), title='Damned',
        )
        action_ko3 = create_action(
            entity=entity2, deadline=now_value - timedelta(days=2), title='Other old',
        )

        ActionsOnTimeBrick.page_size = ActionsNotOnTimeBrick.page_size = max(
            4, settings.BLOCK_SIZE
        )

        def action_found(brick_node, action):
            title = action.title
            return any(n.text == title for n in brick_node.findall('.//td'))

        create_detail = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            model=type(entity1), zone=BrickDetailviewLocation.RIGHT,
        )
        create_detail(brick=ActionsOnTimeBrick,    order=50)
        create_detail(brick=ActionsNotOnTimeBrick, order=51)

        response1 = self.assertGET200(self.entity.get_absolute_url())

        detail_brick_node_ok = self.get_brick_node(
            self.get_html_tree(response1.content),
            ActionsOnTimeBrick.id_,
        )
        self.assertTrue(action_found(detail_brick_node_ok, action_ok1))
        self.assertTrue(action_found(detail_brick_node_ok, action_ok2))
        self.assertFalse(action_found(detail_brick_node_ok, action_ok3))

        detail_brick_node_ko = self.get_brick_node(
            self.get_html_tree(response1.content),
            ActionsNotOnTimeBrick.id_,
        )
        self.assertTrue(action_found(detail_brick_node_ko, action_ko1))
        self.assertTrue(action_found(detail_brick_node_ko, action_ko2))
        self.assertFalse(action_found(detail_brick_node_ko, action_ko3))

        # ---
        create_home = BrickHomeLocation.objects.get_or_create
        create_home(brick_id=ActionsOnTimeBrick.id_,    defaults={'order': 50})
        create_home(brick_id=ActionsNotOnTimeBrick.id_, defaults={'order': 51})

        response2 = self.assertGET200(reverse('creme_core__home'))

        home_brick_node_ok = self.get_brick_node(
            self.get_html_tree(response2.content),
            ActionsOnTimeBrick.id_,
        )
        self.assertTrue(action_found(home_brick_node_ok, action_ok1))
        self.assertTrue(action_found(home_brick_node_ok, action_ok2))
        self.assertTrue(action_found(home_brick_node_ok, action_ok3))
        self.assertInstanceLink(home_brick_node_ok, entity1)
        self.assertInstanceLink(home_brick_node_ok, entity2)

        home_brick_node_ko = self.get_brick_node(
            self.get_html_tree(response2.content),
            ActionsNotOnTimeBrick.id_,
        )
        self.assertTrue(action_found(home_brick_node_ko, action_ko1))
        self.assertTrue(action_found(home_brick_node_ko, action_ko2))
        self.assertTrue(action_found(home_brick_node_ko, action_ko3))
        self.assertInstanceLink(home_brick_node_ko, entity1)
        self.assertInstanceLink(home_brick_node_ko, entity2)

    def test_validate(self):
        action = self._create_action('2010-12-24', 'title', 'descr', 'reaction')
        self.assertFalse(action.is_ok)
        self.assertIsNone(action.validation_date)

        url = reverse('assistants__validate_action', args=(action.id,))
        self.assertGET405(url)

        response = self.assertPOST200(url, follow=True)
        self.assertRedirects(response, self.entity.get_absolute_url())

        action = self.refresh(action)
        self.assertTrue(action.is_ok)
        self.assertDatetimesAlmostEqual(now(), action.validation_date)

    def test_merge(self):
        def creator(contact01, contact02):
            create = self._create_action
            create(
                deadline='2011-2-9',
                title='Fight', descr='I have trained',
                reaction='I expect a fight',
                entity=contact01,
            )
            create(
                deadline='2011-2-10',
                title='Rendezvous', descr='I have flower',
                reaction='I want a rendezvous',
                entity=contact02,
            )
            self.assertEqual(2, Action.objects.count())

        def assertor(contact01):
            actions = Action.objects.all()
            self.assertEqual(2, len(actions))

            for action in actions:
                self.assertEqual(contact01, action.creme_entity)

        self.aux_test_merge(creator, assertor)

    def test_manager_filter_by_user(self):
        user = self.user
        now_value = now()

        create_user = get_user_model().objects.create
        teammate1 = create_user(
            username='luffy',
            email='luffy@sunny.org', role=self.role,
            first_name='Luffy', last_name='Monkey D.',
        )
        teammate2 = create_user(
            username='zorro',
            email='zorro@sunny.org', role=self.role,
            first_name='Zorro', last_name='Roronoa',
        )

        team1 = create_user(username='Team #1', is_team=True)
        team1.teammates = [teammate1, user]

        team2 = create_user(username='Team #2', is_team=True)
        team2.teammates = [self.other_user, teammate2]

        create_action = partial(
            Action.objects.create,
            creme_entity=self.entity, user=user,
            deadline=now_value + timedelta(days=1),
        )

        action1 = create_action(title='Action#1')
        create_action(title='Action#2', user=team2)  # No (other team)
        action3 = create_action(title='Action#3', user=team1)

        self.assertCountEqual(
            [action1, action3],
            Action.objects.filter_by_user(user),
        )
