# -*- coding: utf-8 -*-

try:
    from datetime import timedelta
    from functools import partial

    from django.contrib.auth import get_user_model
    from django.contrib.contenttypes.models import ContentType
    from django.core.urlresolvers import reverse
    from django.db.models.query import QuerySet
    from django.utils.timezone import now

    from creme.creme_core.models import (BlockDetailviewLocation,
             FakeContact, FakeOrganisation, FakeMailingList)

    from ..bricks import ActionsOnTimeBrick, ActionsNotOnTimeBrick
    from ..models import Action
    from .base import AssistantsTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class ActionTestCase(AssistantsTestCase):
    def _build_add_url(self, entity):
        return reverse('assistants__create_action', args=(entity.id,))

    def _create_action(self, deadline, title='TITLE', descr='DESCRIPTION',
                       reaction='REACTION', entity=None, user=None,
                      ):
        entity = entity or self.entity
        user   = user or self.user
        response = self.client.post(self._build_add_url(entity),
                                    data={'user':              user.pk,
                                          'title':             title,
                                          'description':       descr,
                                          'expected_reaction': reaction,
                                          'deadline':          deadline,
                                         }
                                   )
        self.assertNoFormError(response)

        return self.get_object_or_fail(Action, title=title, description=descr)

    def test_create(self):
        self.assertFalse(Action.objects.exists())

        entity = self.entity
        self.assertGET200(self._build_add_url(entity))

        title    = 'TITLE'
        descr    = 'DESCRIPTION'
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
        self.assertEqual(self.create_datetime(year=2010, month=12, day=24),
                         action.deadline
                        )

        self.assertEqual(title, unicode(action))

        create_bdi = partial(BlockDetailviewLocation.create_if_needed, model=FakeContact,
                             zone=BlockDetailviewLocation.RIGHT,
                            )
        create_bdi(brick_id=ActionsOnTimeBrick.id_,    order=500)
        create_bdi(brick_id=ActionsNotOnTimeBrick.id_, order=501)

        response = self.assertGET200(entity.get_absolute_url())
        self.assertTemplateUsed(response, 'assistants/bricks/actions-on-time.html')
        self.assertTemplateUsed(response, 'assistants/bricks/actions-not-on-time.html')

    def test_edit(self):
        title    = 'TITLE'
        descr    = 'DESCRIPTION'
        reaction = 'REACTION'
        action = self._create_action('2010-12-24', title, descr, reaction)

        url = action.get_edit_absolute_url()
        self.assertGET200(url)

        title    += '_edited'
        descr    += '_edited'
        reaction += '_edited'
        deadline = '2011-11-25'
        response = self.client.post(url, data={'user':              self.user.pk,
                                               'title':             title,
                                               'description':       descr,
                                               'expected_reaction': reaction,
                                               'deadline':          deadline,
                                               'deadline_time':     '17:37:00',
                                              }
                                   )
        self.assertNoFormError(response)

        action = self.refresh(action)
        self.assertEqual(title,    action.title)
        self.assertEqual(descr,    action.description)
        self.assertEqual(reaction, action.expected_reaction)
        self.assertEqual(self.create_datetime(year=2011, month=11, day=25, hour=17, minute=37),
                         action.deadline
                        )

    def test_delete_entity01(self):
        action = self._create_action('2010-12-24', 'title', 'descr', 'reaction')
        self.entity.delete()
        self.assertDoesNotExist(action)

    def _aux_test_delete(self, ajax=False):
        action = self._create_action('2010-12-24', 'title', 'descr', 'reaction')
        ct = ContentType.objects.get_for_model(Action)
        kwargs = {} if not ajax else {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.post(reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
                                    data={'id': action.id}, **kwargs
                                   )
        self.assertDoesNotExist(action)

        return response

    def test_delete_action01(self):
        response = self._aux_test_delete()
        self.assertRedirects(response, self.entity.get_absolute_url())

    def test_delete_action02(self):
        "Ajax version"
        response = self._aux_test_delete(ajax=True)
        self.assertEqual(200, response.status_code)

    def test_validate(self):
        action = self._create_action('2010-12-24', 'title', 'descr', 'reaction')
        self.assertFalse(action.is_ok)
        self.assertIsNone(action.validation_date)

        response = self.assertPOST200(reverse('assistants__validate_action', args=(action.id,)), follow=True)
        self.assertRedirects(response, self.entity.get_absolute_url())

        action = self.refresh(action)
        self.assertTrue(action.is_ok)
        self.assertDatetimesAlmostEqual(now(), action.validation_date)

    def test_merge(self):
        def creator(contact01, contact02):
            create = self._create_action
            create('2011-2-9',  'Fight',      'I have trained', 'I expect a fight',    entity=contact01)
            create('2011-2-10', 'Rendezvous', 'I have flower',  'I want a rendezvous', entity=contact02)
            self.assertEqual(2, Action.objects.count())

        def assertor(contact01):
            actions = Action.objects.all()
            self.assertEqual(2, len(actions))

            for action in actions:
                self.assertEqual(contact01, action.creme_entity)

        self.aux_test_merge(creator, assertor)

    def test_get_actions(self):
        user = self.user
        now_value = now()

        entity2 = FakeOrganisation.objects.create(user=user, name='Thousand sunny')

        create_action = partial(Action.objects.create, creme_entity=self.entity,
                                user=user, deadline=now_value + timedelta(days=1),
                               )
        action1 = create_action(title='Action#1')
        create_action(title='Action#2', is_ok=True)  # No (validated)
        action3 = create_action(title='Action#3')
        create_action(title='Action#4', creme_entity=entity2)  # No (other entity)
        action5 = create_action(title='Action#5', deadline=now_value - timedelta(days=1))  # No (deadline)
        create_action(title='Action#5', deadline=now_value - timedelta(days=1), is_ok=True)  # No

        actions = Action.get_actions_it(entity=self.entity, today=now_value)
        self.assertIsInstance(actions, QuerySet)
        self.assertEqual(Action, actions.model)

        self.assertEqual({action1, action3}, set(actions))
        self.assertEqual(2, len(actions))

        # --
        actions = Action.get_actions_nit(entity=self.entity, today=now_value)
        self.assertIsInstance(actions, QuerySet)
        self.assertEqual(Action, actions.model)

        self.assertEqual({action5}, set(actions))
        self.assertEqual(1, len(actions))

    def test_get_actions_for_home01(self):
        user = self.user
        now_value = now()

        create_action = partial(Action.objects.create, creme_entity=self.entity,
                                user=user, deadline=now_value + timedelta(days=1),
                               )
        yesterday = now_value - timedelta(days=1)
        action1 = create_action(title='Action#1')
        create_action(title='Action#2', is_ok=True)  # No (validated)
        action3 = create_action(title='Action#3')
        create_action(title='Action#4', user=self.other_user)  # No (other user)
        action5 = create_action(title='Action#5', deadline=yesterday)  # No (deadline)
        create_action(title='Action#5', deadline=yesterday, is_ok=True)  # No
        create_action(title='Action#5', deadline=yesterday, user=self.other_user)  # No

        actions = Action.get_actions_it_for_home(user=user, today=now_value)
        self.assertIsInstance(actions, QuerySet)
        self.assertEqual(Action, actions.model)

        self.assertEqual({action1, action3}, set(actions))
        self.assertEqual(2, len(actions))

        # --
        actions = Action.get_actions_nit_for_home(user=user, today=now_value)
        self.assertIsInstance(actions, QuerySet)
        self.assertEqual(Action, actions.model)

        self.assertEqual({action5}, set(actions))
        self.assertEqual(1, len(actions))

    def test_get_actions_for_home02(self):
        "Teams"
        user = self.user
        now_value = now()

        create_user = get_user_model().objects.create
        teammate1 = create_user(username='luffy',
                                email='luffy@sunny.org', role=self.role,
                                first_name='Luffy', last_name='Monkey D.',
                               )
        teammate2 = create_user(username='zorro',
                                email='zorro@sunny.org', role=self.role,
                                first_name='Zorro', last_name='Roronoa',
                               )

        team1 = create_user(username='Team #1', is_team=True)
        team1.teammates = [teammate1, user]

        team2 = create_user(username='Team #2', is_team=True)
        team2.teammates = [self.other_user, teammate2]

        create_action = partial(Action.objects.create, creme_entity=self.entity,
                                user=user, deadline=now_value + timedelta(days=1),
                               )
        yesterday = now_value - timedelta(days=1)
        action1 = create_action(title='Action#1')
        create_action(title='Action#2', user=team2)  # No (other team)
        action3 = create_action(title='Action#3', user=team1)
        action4 = create_action(title='Action#4', deadline=yesterday, user=team1)  # No (deadline)
        create_action(title='Action#5', deadline=yesterday, user=team2)  # No

        actions = Action.get_actions_it_for_home(user=user, today=now_value)
        self.assertEqual({action1, action3}, set(actions))
        self.assertEqual(2, len(actions))

        # --
        actions = Action.get_actions_nit_for_home(user=user, today=now_value)
        self.assertEqual({action4}, set(actions))
        self.assertEqual(1, len(actions))

    def test_get_actions_for_ctypes01(self):
        user = self.user
        now_value = now()

        entity2 = FakeOrganisation.objects.create(user=user, name='Thousand sunny')
        entity3 = FakeMailingList.objects.create(user=user, name='Pirates')

        create_action = partial(Action.objects.create, creme_entity=self.entity,
                                user=user, deadline=now_value + timedelta(days=1),
                               )
        yesterday = now_value - timedelta(days=1)
        action1 = create_action(title='Action#1')
        create_action(title='Action#2', is_ok=True)  # No (validated)
        action3 = create_action(title='Action#3')
        create_action(title='Action#4', user=self.other_user)  # No (other user)
        action5 = create_action(title='Action#5', creme_entity=entity2)
        create_action(title='Action#6', creme_entity=entity3)  # No (other ct)
        action7 = create_action(title='Action#7', deadline=yesterday)  # No (deadline)
        create_action(title='Action#5', deadline=yesterday, is_ok=True)  # No
        create_action(title='Action#5', deadline=yesterday, user=self.other_user)  # No
        create_action(title='Action#5', deadline=yesterday, creme_entity=entity3)  # No

        ct_ids = [self.entity.entity_type_id, entity2.entity_type_id]
        actions = Action.get_actions_it_for_ctypes(user=user, today=now_value, ct_ids=ct_ids)
        self.assertIsInstance(actions, QuerySet)
        self.assertEqual(Action, actions.model)

        self.assertEqual({action1, action3, action5}, set(actions))
        self.assertEqual(3, len(actions))

        # --
        actions = Action.get_actions_nit_for_ctypes(user=user, today=now_value, ct_ids=ct_ids)
        self.assertIsInstance(actions, QuerySet)
        self.assertEqual(Action, actions.model)

        self.assertEqual({action7}, set(actions))
        self.assertEqual(1, len(actions))

    def test_get_actions_for_ctypes02(self):
        "Teams"
        user = self.user
        now_value = now()

        entity2 = FakeOrganisation.objects.create(user=user, name='Thousand sunny')

        create_user = get_user_model().objects.create
        teammate1 = create_user(username='luffy',
                                email='luffy@sunny.org', role=self.role,
                                first_name='Luffy', last_name='Monkey D.',
                               )
        teammate2 = create_user(username='zorro',
                                email='zorro@sunny.org', role=self.role,
                                first_name='Zorro', last_name='Roronoa',
                               )

        team1 = create_user(username='Team #1', is_team=True)
        team1.teammates = [teammate1, user]

        team2 = create_user(username='Team #2', is_team=True)
        team2.teammates = [self.other_user, teammate2]

        create_action = partial(Action.objects.create, creme_entity=self.entity,
                                user=user, deadline=now_value + timedelta(days=1),
                               )
        yesterday = now_value - timedelta(days=1)
        action1 = create_action(title='Action#1')
        create_action(title='Action#2', user=team2)  # No (other team)
        action3 = create_action(title='Action#3', user=team1)
        action4 = create_action(title='Action#4', user=team1, creme_entity=entity2)
        action5 = create_action(title='Action#5', deadline=yesterday, user=team1)  # No (deadline)
        create_action(title='Action#5', deadline=yesterday, user=team2)  # No

        ct_ids = [self.entity.entity_type_id, entity2.entity_type_id]
        actions = Action.get_actions_it_for_ctypes(user=user, today=now_value, ct_ids=ct_ids)
        self.assertEqual({action1, action3, action4}, set(actions))
        self.assertEqual(3, len(actions))

        # --
        actions = Action.get_actions_nit_for_ctypes(user=user, today=now_value, ct_ids=ct_ids)
        self.assertEqual({action5}, set(actions))
        self.assertEqual(1, len(actions))
