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

    from creme.creme_core.core.function_field import function_field_registry
    from creme.creme_core.models import CremeEntity, FakeOrganisation, FakeMailingList

    from ..models import Memo
    from .base import AssistantsTestCase
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class MemoTestCase(AssistantsTestCase):
    def _build_add_url(self, entity):
        return reverse('assistants__create_memo', args=(entity.id,))

    def _create_memo(self, content='Content', on_homepage=True, entity=None):
        entity = entity or self.entity
        response = self.client.post(self._build_add_url(entity),
                                    data={'user':        self.user.pk,
                                          'content':     content,
                                          'on_homepage': on_homepage,
                                         }
                                   )
        self.assertNoFormError(response)

        return self.get_object_or_fail(Memo, content=content)

    def test_create(self):
        self.assertFalse(Memo.objects.exists())

        entity = self.entity
        context = self.assertGET200(self._build_add_url(entity)).context
        # self.assertEqual(_('New Memo for «%s»') % entity, context.get('title'))
        self.assertEqual(_('New memo for «{}»').format(entity), context.get('title'))
        self.assertEqual(_('Save the memo'),                    context.get('submit_label'))

        homepage = True
        content = 'Content'
        memo = self._create_memo(content, homepage)
        self.assertEqual(1, Memo.objects.count())

        self.assertEqual(homepage,  memo.on_homepage)
        self.assertEqual(self.user, memo.user)

        self.assertEqual(entity.id,             memo.entity_id)
        self.assertEqual(entity.entity_type_id, memo.entity_content_type_id)

        self.assertDatetimesAlmostEqual(now(), memo.creation_date)

        self.assertEqual(content, str(memo))

    def test_edit(self):
        content  = 'content'
        homepage = True
        memo = self._create_memo(content, homepage)

        url = memo.get_edit_absolute_url()
        self.assertGET200(url)

        content += u""": 
I add a long text in order to obtain a content that 
will be truncate by str() method"""
        homepage = not homepage
        response = self.client.post(url, data={'user':        self.user.pk,
                                               'content':     content,
                                               'on_homepage': homepage,
                                              }
                                   )
        self.assertNoFormError(response)

        memo = self.refresh(memo)
        self.assertEqual(content,  memo.content)
        self.assertEqual(homepage, memo.on_homepage)

        self.assertEqual(u'content: I add a long te…', str(memo))

    def test_delete_related01(self):
        self._create_memo()
        self.assertEqual(1, Memo.objects.count())

        self.entity.delete()
        self.assertEqual(0, Memo.objects.count())

    def test_delete01(self):
        memo = self._create_memo()
        ct = ContentType.objects.get_for_model(Memo)
        self.assertPOST(302, reverse('creme_core__delete_related_to_entity', args=(ct.id,)), data={'id': memo.id})
        self.assertEqual(0, Memo.objects.count())

    def test_function_field01(self):
        # funf = CremeEntity.function_fields.get('assistants-get_memos')
        funf = function_field_registry.get(CremeEntity, 'assistants-get_memos')
        self.assertIsNotNone(funf)
        self.assertEqual('<ul></ul>', funf(self.entity, self.user).for_html())

    def _oldify_memo(self, memo):
        cdate = memo.creation_date
        memo.creation_date = cdate - timedelta(days=1)
        memo.save()

    def test_function_field02(self):
        # funf = CremeEntity.function_fields.get('assistants-get_memos')
        funf = function_field_registry.get(CremeEntity, 'assistants-get_memos')

        self._oldify_memo(self._create_memo('Content01'))
        self._create_memo('Content02')

        with self.assertNumQueries(1):
            result = funf(self.entity, self.user)

        self.assertEqual('<ul><li>Content02</li><li>Content01</li></ul>', result.for_html())

    def test_function_field03(self):
        "Prefetch with 'populate_entities()'"
        user = self.user
        self._oldify_memo(self._create_memo('Content01'))
        self._create_memo('Content02')

        entity02 = CremeEntity.objects.create(user=user)
        self._oldify_memo(self._create_memo('Content03', entity=entity02))
        self._create_memo('Content04', entity=entity02)

        # funf = CremeEntity.function_fields.get('assistants-get_memos')
        funf = function_field_registry.get(CremeEntity, 'assistants-get_memos')

        with self.assertNumQueries(1):
            funf.populate_entities([self.entity, entity02], user)

        with self.assertNumQueries(0):
            result1 = funf(self.entity, user)
            result2 = funf(entity02, user)

        self.assertEqual('<ul><li>Content02</li><li>Content01</li></ul>', result1.for_html())
        self.assertEqual('<ul><li>Content04</li><li>Content03</li></ul>', result2.for_html())

    def test_merge(self):
        def creator(contact01, contact02):
            self._create_memo('This guy is strong',           entity=contact01)
            self._create_memo('This guy lost himself easily', entity=contact02)
            self.assertEqual(2, Memo.objects.count())

        def assertor(contact01):
            memos = Memo.objects.all()
            self.assertEqual(2, len(memos))

            for memo in memos:
                self.assertEqual(contact01, memo.creme_entity)

        self.aux_test_merge(creator, assertor)

    def test_get_memos(self):
        user = self.user

        entity2 = FakeOrganisation.objects.create(user=user, name='Thousand sunny')

        create_memo = partial(Memo.objects.create, creme_entity=self.entity, user=user)
        memo1 = create_memo(content='Memo#1')
        create_memo(content='Memo#2', creme_entity=entity2)  # No (other entity)
        memo3 = create_memo(content='Memo#3')

        memos = Memo.get_memos(entity=self.entity)
        self.assertIsInstance(memos, QuerySet)
        self.assertEqual(Memo, memos.model)

        self.assertCountEqual([memo1, memo3], memos)

    def test_get_memos_for_home01(self):
        user = self.user

        create_memo = partial(Memo.objects.create, creme_entity=self.entity, user=user, on_homepage=True)
        memo1 = create_memo(content='Memo#1')
        create_memo(content='Memo#2', on_homepage=False)  # No
        memo3 = create_memo(content='Memo#3')
        create_memo(content='Memo#4', user=self.other_user)  # No (other user)

        # entity2 = FakeOrganisation.objects.create(user=user, name='Thousand sunny', is_deleted=True)
        # create_memo(content='Memo#4', creme_entity=entity2)  # Not retrieved (deleted entity)

        memos = Memo.get_memos_for_home(user=user)
        self.assertIsInstance(memos, QuerySet)
        self.assertEqual(Memo, memos.model)

        self.assertCountEqual([memo1, memo3], memos)

    def test_get_memos_for_home02(self):
        "Teams"
        user = self.user

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

        create_memo = partial(Memo.objects.create, creme_entity=self.entity, user=user, on_homepage=True)
        memo1 = create_memo(content='Memo#1')
        create_memo(content='Memo#2', on_homepage=False)  # No
        memo3 = create_memo(content='Memo#3', user=team1)
        create_memo(content='Memo#4', user=team2)  # No (other team)

        memos = Memo.get_memos_for_home(user=user)
        self.assertEqual({memo1, memo3}, set(memos))
        self.assertEqual(2, len(memos))

    def test_get_memos_for_ctypes(self):
        user = self.user

        entity2 = FakeOrganisation.objects.create(user=user, name='Thousand sunny')
        entity3 = FakeMailingList.objects.create(user=user, name='Pirates')

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

        create_memo = partial(Memo.objects.create, creme_entity=self.entity, user=user)
        memo1 = create_memo(content='Memo#1')
        create_memo(content='Memo#2', user=self.other_user)  # No (other user)
        memo3 = create_memo(content='Memo#3', user=team1)
        create_memo(content='Memo#4', user=team2)  # No (other team)
        memo5 = create_memo(content='Memo#5', creme_entity=entity2)
        create_memo(content='Memo#6', creme_entity=entity3)

        memos = Memo.get_memos_for_ctypes(user=user, ct_ids=[self.entity.entity_type_id, entity2.entity_type_id])
        self.assertIsInstance(memos, QuerySet)
        self.assertEqual(Memo, memos.model)

        self.assertEqual({memo1, memo3, memo5}, set(memos))
        self.assertEqual(3, len(memos))

    def test_manager_filter_by_user(self):
        "Teams"
        user = self.user

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

        create_memo = partial(Memo.objects.create, creme_entity=self.entity, user=user, on_homepage=True)
        memo1 = create_memo(content='Memo#1')
        memo2 = create_memo(content='Memo#2', user=team1)
        create_memo(content='Memo#3', user=team2)  # No (other team)

        memos = Memo.objects.filter_by_user(user)
        self.assertEqual({memo1, memo2}, set(memos))
        self.assertEqual(2, len(memos))