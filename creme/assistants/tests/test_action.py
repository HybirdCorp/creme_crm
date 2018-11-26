# -*- coding: utf-8 -*-

try:
    from datetime import timedelta
    from functools import partial

    from django.contrib.auth import get_user_model
    from django.contrib.contenttypes.models import ContentType
    from django.db.models.query import QuerySet
    from django.urls import reverse
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import (CremeEntity, BrickDetailviewLocation,
            FakeContact, FakeOrganisation, FakeMailingList)

    from ..bricks import ActionsOnTimeBrick, ActionsNotOnTimeBrick
    from ..models import Action
    from .base import AssistantsTestCase
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class ActionTestCase(AssistantsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.get_ct = ContentType.objects.get_for_model

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
        context = self.assertGET200(self._build_add_url(entity)).context
        # self.assertEqual(_('New action for «%s»') % entity, context.get('title'))
        self.assertEqual(_('New action for «{entity}»').format(entity=entity),
                         context.get('title')
                        )
        self.assertEqual(_('Save the action'), context.get('submit_label'))

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

        self.assertEqual(title, str(action))

        create_bdi = partial(BrickDetailviewLocation.create_if_needed, model=FakeContact,
                             zone=BrickDetailviewLocation.RIGHT,
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
        context = self.assertGET200(url).context
        # self.assertEqual(_('Action for «%s»') % self.entity, context.get('title'))
        self.assertEqual(_('Action for «{entity}»').format(entity=self.entity),
                         context.get('title')
                        )

        # ---
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
        ct = self.get_ct(Action)
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

        self.assertCountEqual([action1, action3], actions)

        # --
        actions = Action.get_actions_nit(entity=self.entity, today=now_value)
        self.assertIsInstance(actions, QuerySet)
        self.assertEqual(Action, actions.model)
        self.assertCountEqual([action5], actions)

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
        create_action(title='Action#6', deadline=yesterday, is_ok=True)  # No
        create_action(title='Action#7', deadline=yesterday, user=self.other_user)  # No

        # entity2 = FakeOrganisation.objects.create(user=user, name='Thousand sunny', is_deleted=True)
        # create_action(title='Action#8', creme_entity=entity2)  # No (deleted entity)
        # create_action(title='Action#9', creme_entity=entity2, deadline=yesterday)  # No (deleted entity + deadline)

        actions = Action.get_actions_it_for_home(user=user, today=now_value)
        self.assertIsInstance(actions, QuerySet)
        self.assertEqual(Action, actions.model)

        self.assertCountEqual([action1, action3], actions)

        # --
        actions = Action.get_actions_nit_for_home(user=user, today=now_value)
        self.assertIsInstance(actions, QuerySet)
        self.assertEqual(Action, actions.model)
        self.assertCountEqual([action5], actions)

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

        self.assertCountEqual([action1, action3],
                              Action.get_actions_it_for_home(user=user, today=now_value)
                             )
        self.assertCountEqual([action4],
                              Action.get_actions_nit_for_home(user=user, today=now_value)
                             )

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

        self.assertCountEqual([action1, action3, action5], actions)

        # --
        actions = Action.get_actions_nit_for_ctypes(user=user, today=now_value, ct_ids=ct_ids)
        self.assertIsInstance(actions, QuerySet)
        self.assertEqual(Action, actions.model)
        self.assertCountEqual([action7], actions)

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
        self.assertCountEqual([action1, action3, action4], actions)

        # --
        self.assertCountEqual([action5],
                              Action.get_actions_nit_for_ctypes(user=user, today=now_value, ct_ids=ct_ids)
                             )

    def test_manager_filter_by_user(self):
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

        action1 = create_action(title='Action#1')
        create_action(title='Action#2', user=team2)  # No (other team)
        action3 = create_action(title='Action#3', user=team1)

        self.assertCountEqual([action1, action3],
                              Action.objects.filter_by_user(user)
                             )


# TODO: create a fake model with a RealEntityForeignKey & move these test case to 'creme_core' ??
class RealEntityForeignKeyTestCase(AssistantsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.get_ct = get_ct = ContentType.objects.get_for_model
        get_ct(FakeContact)
        get_ct(CremeEntity)

    def test_basic_get_n_set(self):
        action = Action(title='My action',
                        deadline=now() + timedelta(days=7),
                        user=self.user,
                       )

        with self.assertNumQueries(0):
            action.creme_entity = self.entity

        with self.assertNumQueries(0):
            ct = action.entity_content_type
        self.assertEqual(self.get_ct(FakeContact), ct)

        with self.assertNumQueries(0):
            entity = action.entity
        self.assertEqual(self.entity, entity)

        with self.assertNoException():
            action.save()

        # ----
        action = self.refresh(action)
        self.assertEqual(self.entity.id, action.entity_id)
        self.assertEqual(ct.id,          action.entity_content_type_id)

        with self.assertNumQueries(1):
            creme_entity = action.creme_entity
        self.assertEqual(self.entity, creme_entity)

    def test_get_with_cache(self):
        action = Action.objects.create(title='My action',
                                       deadline=now() + timedelta(days=7),
                                       user=self.user,
                                       creme_entity=self.entity,
                                      )

        action = self.refresh(action)

        with self.assertNumQueries(1):
            __ = action.creme_entity

        with self.assertNumQueries(0):  # <= cache
            creme_entity = action.creme_entity

        self.assertEqual(self.entity, creme_entity)

    def test_fk_cache(self):
        "Do not retrieve real entity if already stored/retrieved in 'entity' attribute."
        entity = self.entity
        action = Action(title='My action',
                        deadline=now() + timedelta(days=7),
                        user=self.user,
                        entity=entity,  # <== real entity
                        entity_content_type=entity.entity_type,  # Must be set (consistency protection)
                       )

        with self.assertNumQueries(0):
            creme_entity = action.creme_entity

        self.assertEqual(entity, creme_entity)

    def test_missing_ctype01(self):
        "CT not set + base entity set => error"
        action = Action(title='My action',
                        deadline=now() + timedelta(days=7),
                        user=self.user,
                        entity=CremeEntity.objects.get(id=self.entity.id),  # Not real entity...
                       )

        with self.assertRaises(ValueError) as error_context:
            __ = action.creme_entity

        self.assertEqual('The content type is not set while the entity is. '
                         'HINT: set both by hand or just use the RealEntityForeignKey setter.',
                         error_context.exception.args[0]
                        )

    def test_missing_ctype02(self):
        "CT not set + entity ID set => error"
        action = Action(title='My action',
                        deadline=now() + timedelta(days=7),
                        user=self.user,
                        entity_id=self.entity.id
                       )

        with self.assertRaises(ValueError) as error_context:
            __ = action.creme_entity

        self.assertEqual('The content type is not set while the entity is. '
                         'HINT: set both by hand or just use the RealEntityForeignKey setter.',
                         error_context.exception.args[0]
                        )

    def test_cache_for_set(self):
        "After a '__set__' with a real entity, '__get__' uses no query."
        entity = self.entity
        action = Action(title='My action',
                        deadline=now() + timedelta(days=7),
                        user=self.user,
                       )

        with self.assertNumQueries(0):
            action.creme_entity = entity

        with self.assertNumQueries(0):
            creme_entity = action.creme_entity

        self.assertEqual(entity, creme_entity)

    def test_get_real_entity(self):
        "Set a base entity, so '__get__' uses a query to retrieve the real entity."
        entity = self.entity
        action = Action(title='My action',
                        deadline=now() + timedelta(days=7),
                        user=self.user,
                       )

        base_entity = CremeEntity.objects.get(id=entity.id)

        with self.assertNumQueries(0):
            action.creme_entity = base_entity

        with self.assertNumQueries(1):
            creme_entity = action.creme_entity
        self.assertEqual(entity, creme_entity)

        with self.assertNumQueries(0):
            creme_entity2 = action.creme_entity
        self.assertEqual(entity, creme_entity2)

    def test_set_none(self):
        "Set None"
        entity = self.entity
        action = Action(title='My action',
                        deadline=now() + timedelta(days=7),
                        user=self.user,
                        entity=entity,
                        entity_content_type=entity.entity_type,
                       )

        action.creme_entity = None
        self.assertIsNone(action.entity_id)
        self.assertIsNone(action.entity_content_type_id)

    def test_get_none01(self):
        "Get initial None"
        action = Action(title='My action',
                        deadline=now() + timedelta(days=7),
                        user=self.user,
                        # entity=entity,  # Not set
                       )

        with self.assertNumQueries(0):
            creme_entity = action.creme_entity

        self.assertIsNone(creme_entity)

        #  --
        action.entity = entity = self.entity

        with self.assertRaises(ValueError):
            __ = action.creme_entity

        # --
        action.entity_content_type_id = entity.entity_type_id

        with self.assertNumQueries(0):
            creme_entity2 = action.creme_entity

        self.assertEqual(entity, creme_entity2)

    def test_get_none02(self):
        "Get initial None (explicitly set)"
        action = Action(title='My action',
                        deadline=now() + timedelta(days=7),
                        user=self.user,
                        entity=None,
                       )

        with self.assertNumQueries(0):
            creme_entity = action.creme_entity

        self.assertIsNone(creme_entity)

    def test_bad_ctype01(self):
        "Bad CT id + base entity id"
        action = Action(title='My action',
                        deadline=now() + timedelta(days=7),
                        user=self.user,
                        entity_id=self.entity.id,
                        entity_content_type=self.get_ct(FakeOrganisation),  # Does not correspond to 'self.entity'
                       )

        with self.assertRaises(FakeOrganisation.DoesNotExist):
            __ = action.creme_entity

    def test_bad_ctype02(self):
        "Bad CT + base entity"
        action = Action(title='My action',
                        deadline=now() + timedelta(days=7),
                        user=self.user,
                        entity=CremeEntity.objects.get(id=self.entity.id),  # Not real entity...
                        entity_content_type=self.get_ct(FakeOrganisation),  # Does not correspond to 'self.entity'
                       )

        with self.assertRaises(ValueError) as error_context:
            __ = action.creme_entity

        self.assertEqual('The content type does not match this entity.',
                         error_context.exception.args[0]
                        )

    def test_change_entity(self):
        "New entity with new CT"
        action = Action.objects.create(
            title='My action',
            deadline=now() + timedelta(days=7),
            user=self.user,
            creme_entity=self.entity,
        )
        orga = FakeOrganisation.objects.create(user=self.user, name='Tendô no dojo')

        action = self.refresh(action)
        action.creme_entity = orga
        action.save()

        action = self.refresh(action)
        self.assertEqual(orga, action.creme_entity)
        self.assertEqual(orga.id, action.entity_id)
        self.assertEqual(FakeOrganisation, action.entity_content_type.model_class())
