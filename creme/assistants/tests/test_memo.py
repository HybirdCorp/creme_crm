# -*- coding: utf-8 -*-

from datetime import timedelta
from functools import partial

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models.query_utils import Q
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import EntityCellFunctionField
from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.forms.listview import TextLVSWidget
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    CremeEntity,
    FakeOrganisation,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from ..bricks import MemosBrick
from ..models import Memo
from .base import AssistantsTestCase


class MemoTestCase(BrickTestCaseMixin, AssistantsTestCase):
    @staticmethod
    def _build_add_url(entity):
        return reverse('assistants__create_memo', args=(entity.id,))

    def _create_memo(self, content='Content', on_homepage=True, entity=None):
        entity = entity or self.entity
        response = self.client.post(
            self._build_add_url(entity),
            data={
                'user':        self.user.pk,
                'content':     content,
                'on_homepage': on_homepage,
            },
        )
        self.assertNoFormError(response)

        return self.get_object_or_fail(Memo, content=content)

    def test_create(self):
        self.assertFalse(Memo.objects.exists())

        entity = self.entity
        context = self.assertGET200(self._build_add_url(entity)).context
        self.assertEqual(
            _('New memo for «{entity}»').format(entity=entity),
            context.get('title'),
        )
        self.assertEqual(_('Save the memo'), context.get('submit_label'))

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
        content = 'content'
        homepage = True
        memo = self._create_memo(content, homepage)

        url = memo.get_edit_absolute_url()
        context = self.assertGET200(url).context
        self.assertEqual(
            _('Memo for «{entity}»').format(entity=self.entity),
            context.get('title'),
        )

        # ---
        content += (
            ': \n'
            'I add a long text in order to obtain a content that \n'
            'will be truncate by str() method'
        )
        homepage = not homepage
        response = self.client.post(
            url,
            data={
                'user':        self.user.pk,
                'content':     content,
                'on_homepage': homepage,
            },
        )
        self.assertNoFormError(response)

        memo = self.refresh(memo)
        self.assertEqual(content,  memo.content)
        self.assertEqual(homepage, memo.on_homepage)

        self.assertEqual('content: I add a long te…', str(memo))

    def test_delete_related01(self):
        self._create_memo()
        self.assertEqual(1, Memo.objects.count())

        self.entity.delete()
        self.assertEqual(0, Memo.objects.count())

    def test_delete01(self):
        memo = self._create_memo()
        ct = ContentType.objects.get_for_model(Memo)
        self.assertPOST(
            302,
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': memo.id},
        )
        self.assertEqual(0, Memo.objects.count())

    def test_function_field01(self):
        funf = function_field_registry.get(CremeEntity, 'assistants-get_memos')
        self.assertIsNotNone(funf)
        self.assertEqual('<ul></ul>', funf(self.entity, self.user).for_html())

        # ---
        field_class = funf.search_field_builder
        self.assertIsNotNone(field_class)

        field = field_class(
            cell=EntityCellFunctionField(model=FakeOrganisation, func_field=funf),
            user=self.user,
        )
        self.assertIsInstance(field.widget, TextLVSWidget)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=None))
        self.assertEqual(Q(), to_python(value=''))

        value = 'foobar'
        self.assertEqual(
            Q(assistants_memos__content__icontains=value),
            to_python(value=value),
        )

    @staticmethod
    def _oldify_memo(memo):
        cdate = memo.creation_date
        memo.creation_date = cdate - timedelta(days=1)
        memo.save()

    def test_function_field02(self):
        funf = function_field_registry.get(CremeEntity, 'assistants-get_memos')

        self._oldify_memo(self._create_memo('Content01'))
        self._create_memo('Content02')

        with self.assertNumQueries(1):
            result = funf(self.entity, self.user)

        self.assertHTMLEqual(
            '<ul><li>Content02</li><li>Content01</li></ul>',
            result.for_html(),
        )

    def test_function_field03(self):
        "Prefetch with 'populate_entities()'"
        user = self.user
        self._oldify_memo(self._create_memo('Content01'))
        self._create_memo('Content02')

        entity02 = CremeEntity.objects.create(user=user)
        self._oldify_memo(self._create_memo('Content03', entity=entity02))
        self._create_memo('Content04', entity=entity02)

        funf = function_field_registry.get(CremeEntity, 'assistants-get_memos')

        with self.assertNumQueries(1):
            funf.populate_entities([self.entity, entity02], user)

        with self.assertNumQueries(0):
            result1 = funf(self.entity, user)
            result2 = funf(entity02, user)

        self.assertHTMLEqual(
            '<ul><li>Content02</li><li>Content01</li></ul>',
            result1.for_html(),
        )
        self.assertHTMLEqual(
            '<ul><li>Content04</li><li>Content03</li></ul>',
            result2.for_html(),
        )

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

    def test_brick(self):
        user = self.user

        entity1 = self.entity

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity2 = create_orga(name='Acme')
        entity3 = create_orga(name='Deleted', is_deleted=True)

        def create_memo(content, entity, on_homepage=True):
            return Memo.objects.create(
                user=user, content=content, creme_entity=entity, on_homepage=on_homepage,
            )

        memo1 = create_memo('Recall',         entity1)
        memo2 = create_memo("It's important", entity1, on_homepage=False)
        memo3 = create_memo('Other',          entity2)
        memo4 = create_memo('Ignored',        entity3)

        MemosBrick.page_size = max(4, settings.BLOCK_SIZE)

        def memo_found(brick_node, memo):
            content = memo.content
            return any(n.text == content for n in brick_node.findall('.//p'))

        BrickDetailviewLocation.objects.create_if_needed(
            brick=MemosBrick,
            model=type(entity1),
            order=50,
            zone=BrickDetailviewLocation.RIGHT,
        )

        response1 = self.assertGET200(self.entity.get_absolute_url())
        detail_brick_node = self.get_brick_node(
            self.get_html_tree(response1.content),
            MemosBrick.id_,
        )

        self.assertTrue(memo_found(detail_brick_node, memo1))
        self.assertTrue(memo_found(detail_brick_node, memo2))
        self.assertFalse(memo_found(detail_brick_node, memo3))

        # ---
        BrickHomeLocation.objects.get_or_create(
            brick_id=MemosBrick.id_, defaults={'order': 50},
        )

        response2 = self.assertGET200(reverse('creme_core__home'))
        home_brick_node = self.get_brick_node(
            self.get_html_tree(response2.content),
            MemosBrick.id_,
        )

        self.assertTrue(memo_found(home_brick_node, memo1))
        self.assertFalse(memo_found(home_brick_node, memo2))
        self.assertTrue(memo_found(home_brick_node, memo3))
        self.assertFalse(memo_found(home_brick_node, memo4))
        self.assertInstanceLink(home_brick_node, entity1)
        self.assertInstanceLink(home_brick_node, entity2)

    def test_manager_filter_by_user(self):
        "Teams."
        user = self.user

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

        create_memo = partial(
            Memo.objects.create,
            creme_entity=self.entity, user=user, on_homepage=True,
        )
        memo1 = create_memo(content='Memo#1')
        memo2 = create_memo(content='Memo#2', user=team1)
        create_memo(content='Memo#3', user=team2)  # No (other team)
        self.assertCountEqual([memo1, memo2], Memo.objects.filter_by_user(user))
