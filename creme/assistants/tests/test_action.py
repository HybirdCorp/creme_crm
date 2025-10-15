from datetime import date, timedelta
from functools import partial

from django.conf import settings
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
    @staticmethod
    def _build_add_url(entity):
        return reverse('assistants__create_action', args=(entity.id,))

    def _create_action(self, *, entity, user, deadline=None,
                       title='TITLE', description='DESCRIPTION', reaction='REACTION',
                       ):
        return Action.objects.create(
            user=user, real_entity=entity,
            title=title, description=description, expected_reaction=reaction,
            deadline=deadline or now(),
        )

    def test_create(self):
        user = self.login_as_assistants_user()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])
        self.assertFalse(Action.objects.exists())

        entity = self.create_entity(user=user)
        context = self.assertGET200(self._build_add_url(entity)).context
        self.assertEqual(
            _('New action for «{entity}»').format(entity=entity),
            context.get('title'),
        )
        self.assertEqual(
            pgettext('assistants', 'Save the action'),
            context.get('submit_label'),
        )

        # POST ---
        title = 'TITLE'
        description = 'DESCRIPTION'
        reaction = 'REACTION'
        deadline = date(2010, 12, 24)
        self.assertNoFormError(self.client.post(
            self._build_add_url(entity),
            data={
                'user':              user.pk,
                'title':             title,
                'description':       description,
                'expected_reaction': reaction,
                'deadline':          self.formfield_value_date(deadline),
            },
        ))

        action = self.get_object_or_fail(Action, title=title, description=description)
        self.assertEqual(title,       action.title)
        self.assertEqual(description, action.description)
        self.assertEqual(reaction,    action.expected_reaction)
        self.assertEqual(user,        action.user)

        self.assertEqual(entity.entity_type_id, action.entity_content_type_id)
        self.assertEqual(entity.id,             action.entity_id)
        self.assertEqual(entity,                action.real_entity)

        now_value = now()
        self.assertDatetimesAlmostEqual(now_value, action.creation_date)
        self.assertDatetimesAlmostEqual(now_value, action.modification_date)

        self.assertEqual(
            self.create_datetime(year=2010, month=12, day=24),
            action.deadline,
        )
        self.assertEqual(title, str(action))

        # ---
        create_bdl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            model=FakeContact, zone=BrickDetailviewLocation.RIGHT,
        )
        create_bdl(brick=ActionsOnTimeBrick,    order=500)
        create_bdl(brick=ActionsNotOnTimeBrick, order=501)

        response = self.assertGET200(entity.get_absolute_url())
        self.assertTemplateUsed(response, 'assistants/bricks/actions-on-time.html')
        self.assertTemplateUsed(response, 'assistants/bricks/actions-not-on-time.html')

    def test_create__no_app_perm(self):
        user = self.login_as_standard()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])

        entity = self.create_entity(user=user)
        response = self.assertGET403(
            self._build_add_url(entity), HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(
            _('You are not allowed to access to the app: {}').format(
                _('Assistants (Todos, Memos, …)')
            ),
            response.text,
        )

    def test_edit(self):
        user = self.login_as_assistants_user()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])

        entity = self.create_entity(user=user)
        title = 'TITLE'
        descr = 'DESCRIPTION'
        reaction = 'REACTION'
        action = self._create_action(
            entity=entity, user=user,
            deadline=self.create_datetime(2010, 12, 24),
            title=title, description=descr, reaction=reaction,
        )

        url = action.get_edit_absolute_url()
        context = self.assertGET200(url).context
        self.assertEqual(
            _('Action for «{entity}»').format(entity=entity),
            context.get('title'),
        )

        # ---
        title    += '_edited'
        descr    += '_edited'
        reaction += '_edited'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'user':              user.pk,
                'title':             title,
                'description':       descr,
                'expected_reaction': reaction,
                'deadline':          self.formfield_value_date(2011, 11, 25),
                'deadline_time':     '17:37:00',
            },
        ))

        action = self.refresh(action)
        self.assertEqual(title,    action.title)
        self.assertEqual(descr,    action.description)
        self.assertEqual(reaction, action.expected_reaction)
        self.assertEqual(
            self.create_datetime(year=2011, month=11, day=25, hour=17, minute=37),
            action.deadline,
        )

    def test_edit__no_app_perm(self):
        user = self.login_as_standard()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])

        entity = self.create_entity(user=user)
        action = self._create_action(
            user=user, entity=entity, deadline=self.create_datetime(2025, 7, 15),
        )
        response = self.assertGET403(
            action.get_edit_absolute_url(), HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(
            _('You are not allowed to access to the app: {}').format(
                _('Assistants (Todos, Memos, …)')
            ),
            response.text,
        )

    def test_delete_entity(self):
        user = self.login_as_assistants_user()
        entity = self.create_entity(user=user)
        action = self._create_action(
            entity=entity, user=user, title='title',
            deadline=self.create_datetime(2010, 12, 24),
        )

        entity.delete()
        self.assertDoesNotExist(action)

    def _aux_test_delete(self, action, ajax=False):
        ct = ContentType.objects.get_for_model(Action)
        kwargs = {} if not ajax else {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        return self.client.post(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': action.id},
            **kwargs
        )

    def test_delete(self):
        user = self.login_as_assistants_user()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])

        entity = self.create_entity(user=user)
        action = self._create_action(user=user, entity=entity)
        response = self._aux_test_delete(action=action)
        self.assertDoesNotExist(action)
        self.assertRedirects(response, entity.get_absolute_url())

    def test_delete__ajax(self):
        user = self.login_as_root_and_get()
        action = self._create_action(user=user, entity=self.create_entity(user=user))
        response = self._aux_test_delete(action=action, ajax=True)
        self.assertDoesNotExist(action)
        self.assertEqual(200, response.status_code)

    def test_delete__no_app_perm(self):
        user = self.login_as_standard()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])

        action = self._create_action(user=user, entity=self.create_entity(user=user))
        response = self._aux_test_delete(action=action, ajax=True)
        self.assertEqual(403, response.status_code)
        self.assertStillExists(action)
        self.assertEqual(
            _('You are not allowed to access to the app: {}').format(
                _('Assistants (Todos, Memos, …)')
            ),
            response.text,
        )

    def test_brick(self):
        user = self.login_as_assistants_user()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])

        entity1 = self.create_entity(user=user)
        entity2 = FakeOrganisation.objects.create(user=user, name='Acme')

        now_value = now()

        create_action = partial(Action.objects.create, user=user)
        action_ok1 = create_action(
            real_entity=entity1, deadline=now_value + timedelta(days=1), title='Recall',
        )
        action_ok2 = create_action(
            real_entity=entity1, deadline=now_value + timedelta(days=2), title="It's important",
        )
        action_ok3 = create_action(
            real_entity=entity2, deadline=now_value + timedelta(days=2), title='Other',
        )

        action_ko1 = create_action(
            real_entity=entity1, deadline=now_value - timedelta(days=1), title='Too late',
        )
        action_ko2 = create_action(
            real_entity=entity1, deadline=now_value - timedelta(days=2), title='Damned',
        )
        action_ko3 = create_action(
            real_entity=entity2, deadline=now_value - timedelta(days=2), title='Other old',
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

        response1 = self.assertGET200(entity1.get_absolute_url())

        detail_brick_node_ok = self.get_brick_node(
            self.get_html_tree(response1.content), brick=ActionsOnTimeBrick,
        )
        self.assertTrue(action_found(detail_brick_node_ok, action_ok1))
        self.assertTrue(action_found(detail_brick_node_ok, action_ok2))
        self.assertFalse(action_found(detail_brick_node_ok, action_ok3))

        detail_brick_node_ko = self.get_brick_node(
            self.get_html_tree(response1.content), brick=ActionsNotOnTimeBrick,
        )
        self.assertTrue(action_found(detail_brick_node_ko, action_ko1))
        self.assertTrue(action_found(detail_brick_node_ko, action_ko2))
        self.assertFalse(action_found(detail_brick_node_ko, action_ko3))

        # ---
        create_home = BrickHomeLocation.objects.get_or_create
        create_home(brick_id=ActionsOnTimeBrick.id,    defaults={'order': 50})
        create_home(brick_id=ActionsNotOnTimeBrick.id, defaults={'order': 51})

        response2 = self.assertGET200(reverse('creme_core__home'))

        home_brick_node_ok = self.get_brick_node(
            self.get_html_tree(response2.content), brick=ActionsOnTimeBrick,
        )
        self.assertTrue(action_found(home_brick_node_ok, action_ok1))
        self.assertTrue(action_found(home_brick_node_ok, action_ok2))
        self.assertTrue(action_found(home_brick_node_ok, action_ok3))
        self.assertInstanceLink(home_brick_node_ok, entity1)
        self.assertInstanceLink(home_brick_node_ok, entity2)

        home_brick_node_ko = self.get_brick_node(
            self.get_html_tree(response2.content), brick=ActionsNotOnTimeBrick,
        )
        self.assertTrue(action_found(home_brick_node_ko, action_ko1))
        self.assertTrue(action_found(home_brick_node_ko, action_ko2))
        self.assertTrue(action_found(home_brick_node_ko, action_ko3))
        self.assertInstanceLink(home_brick_node_ko, entity1)
        self.assertInstanceLink(home_brick_node_ko, entity2)

    def test_validate(self):
        user = self.login_as_assistants_user()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])

        entity = self.create_entity(user=user)
        action = self._create_action(
            user=user, entity=entity, deadline=self.create_datetime(2010, 12, 24),
        )
        self.assertFalse(action.is_ok)
        self.assertIsNone(action.validation_date)

        url = reverse('assistants__validate_action', args=(action.id,))
        self.assertGET405(url)

        response = self.assertPOST200(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest', follow=True)
        self.assertRedirects(response, entity.get_absolute_url())

        action = self.refresh(action)
        self.assertTrue(action.is_ok)
        self.assertDatetimesAlmostEqual(now(), action.validation_date)

    def test_validate__no_app_perm(self):
        user = self.login_as_standard()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])

        entity = self.create_entity(user=user)
        action = self._create_action(
            user=user, entity=entity, deadline=self.create_datetime(2010, 12, 24),
        )
        response = self.assertPOST403(
            reverse('assistants__validate_action', args=(action.id,)),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest', follow=True,
        )
        self.assertEqual(
            _('You are not allowed to access to the app: {}').format(
                _('Assistants (Todos, Memos, …)')
            ),
            response.text,
        )

    def test_merge(self):
        def creator(user, contact01, contact02):
            create = partial(Action.objects.create, user=user)
            create(
                deadline=self.create_datetime(2011, 2, 9),
                title='Fight',
                description='I have trained',
                expected_reaction='I expect a fight',
                real_entity=contact01,
            )
            create(
                deadline=self.create_datetime(2011, 2, 10),
                title='Rendezvous',
                description='I have flower',
                expected_reaction='I want a rendezvous',
                real_entity=contact02,
            )
            self.assertEqual(2, Action.objects.count())

        def assertor(contact01):
            actions = Action.objects.all()
            self.assertEqual(2, len(actions))

            for action in actions:
                self.assertEqual(contact01, action.real_entity)

        self.aux_test_merge(creator, assertor)

    def test_manager_filter_by_user(self):
        user = self.login_as_root_and_get()
        now_value = now()
        entity = self.create_entity(user=user)

        other_user = self.create_user(0)
        teammate1 = self.create_user(1)
        teammate2 = self.create_user(2)

        team1 = self.create_team('Team #1', teammate1, user)
        team2 = self.create_team('Team #2', other_user, teammate2)

        create_action = partial(
            Action.objects.create,
            real_entity=entity, user=user,
            deadline=now_value + timedelta(days=1),
        )

        action1 = create_action(title='Action#1')
        create_action(title='Action#2', user=team2)  # No (other team)
        action3 = create_action(title='Action#3', user=team1)

        self.assertCountEqual(
            [action1, action3],
            Action.objects.filter_by_user(user),
        )
