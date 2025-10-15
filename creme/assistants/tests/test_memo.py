from datetime import timedelta
from functools import partial

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models.query_utils import Q
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import EntityCellFunctionField
from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.forms.listview import TextLVSWidget
from creme.creme_core.gui.view_tag import ViewTag
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

    def _create_memo(self, *, entity, user, content='Content', on_homepage=True):
        return Memo.objects.create(
            user=user, real_entity=entity, content=content, on_homepage=on_homepage,
        )

    def test_create(self):
        user = self.login_as_assistants_user()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])
        self.assertFalse(Memo.objects.exists())

        entity = self.create_entity(user=user)
        context = self.assertGET200(self._build_add_url(entity)).context
        self.assertEqual(
            _('New memo for «{entity}»').format(entity=entity),
            context.get('title'),
        )
        self.assertEqual(_('Save the memo'), context.get('submit_label'))

        homepage = True
        content = 'Content'
        self.assertNoFormError(self.client.post(
            self._build_add_url(entity),
            data={
                'user':        user.id,
                'content':     content,
                'on_homepage': 'on',
            },
        ))

        memo = self.get_object_or_fail(Memo, content=content)
        self.assertEqual(homepage, memo.on_homepage)
        self.assertEqual(user,     memo.user)
        self.assertEqual(entity.id,             memo.entity_id)
        self.assertEqual(entity.entity_type_id, memo.entity_content_type_id)
        self.assertEqual(content, str(memo))

        now_value = now()
        self.assertDatetimesAlmostEqual(now_value, memo.creation_date)
        self.assertDatetimesAlmostEqual(now_value, memo.modification_date)

        self.assertEqual(1, Memo.objects.count())

    def test_create__no_app_perm(self):
        user = self.login_as_standard()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])
        self.assertFalse(Memo.objects.exists())

        response = self.assertGET403(
            self._build_add_url(self.create_entity(user=user)),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
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

        content = 'content'
        homepage = True
        memo = Memo.objects.create(
            user=user, real_entity=entity, content=content, on_homepage=homepage,
        )

        url = memo.get_edit_absolute_url()
        context = self.assertGET200(url).context
        self.assertEqual(
            _('Memo for «{entity}»').format(entity=entity),
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
                'user':        user.id,
                'content':     content,
                'on_homepage': homepage,
            },
        )
        self.assertNoFormError(response)

        memo = self.refresh(memo)
        self.assertEqual(content,  memo.content)
        self.assertEqual(homepage, memo.on_homepage)

        self.assertEqual('content: I add a long te…', str(memo))

    def test_edit__no_app_perm(self):
        user = self.login_as_standard()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])

        memo = Memo.objects.create(
            user=user, real_entity=self.create_entity(user=user), content='Le content',
        )
        response = self.assertGET403(
            memo.get_edit_absolute_url(),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(
            _('You are not allowed to access to the app: {}').format(
                _('Assistants (Todos, Memos, …)')
            ),
            response.text,
        )

    def test_delete_entity(self):
        user = self.login_as_root_and_get()
        entity = self.create_entity(user=user)
        memo = self._create_memo(user=user, entity=entity)

        entity.delete()
        self.assertDoesNotExist(memo)

    def test_delete(self):
        user = self.login_as_assistants_user()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])

        memo = self._create_memo(user=user, entity=self.create_entity(user=user))
        ct = ContentType.objects.get_for_model(Memo)
        self.assertPOST200(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': memo.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertDoesNotExist(memo)

    def test_function_field__empty(self):
        user = self.login_as_root_and_get()
        entity = self.create_entity(user=user)

        funf = function_field_registry.get(CremeEntity, 'assistants-get_memos')
        self.assertIsNotNone(funf)
        self.assertEqual('', funf(entity, user).render(ViewTag.HTML_LIST))

        # ---
        field_class = funf.search_field_builder
        self.assertIsNotNone(field_class)

        field = field_class(
            cell=EntityCellFunctionField(model=FakeOrganisation, func_field=funf),
            user=user,
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

    def test_function_field(self):
        user = self.create_user(
            role=self.create_role(allowed_apps=['creme_core', 'assistants']),
        )
        entity = self.create_entity(user=user)

        funf = function_field_registry.get(CremeEntity, 'assistants-get_memos')

        self._oldify_memo(self._create_memo(user=user, entity=entity, content='Content01'))
        self._create_memo(user=user, entity=entity, content='Content02')

        with self.assertNumQueries(1):
            result = funf(entity, user)

        self.assertHTMLEqual(
            '<ul class="limited-list"><li>Content02</li><li>Content01</li></ul>',
            result.render(ViewTag.HTML_LIST),
        )

    def test_function_field__prefetch(self):
        "Prefetch with 'populate_entities()'"
        user = self.create_user(
            role=self.create_role(allowed_apps=['creme_core', 'assistants']),
        )
        entity1 = self.create_entity(user=user)

        self._oldify_memo(self._create_memo(user=user, entity=entity1, content='Content01'))
        self._create_memo(user=user, entity=entity1, content='Content02')

        entity2 = CremeEntity.objects.create(user=user)
        self._oldify_memo(self._create_memo(user=user, entity=entity2, content='Content03'))
        self._create_memo(user=user, entity=entity2, content='Content04')

        funf = function_field_registry.get(CremeEntity, 'assistants-get_memos')

        with self.assertNumQueries(1):
            funf.populate_entities([entity1, entity2], user)

        with self.assertNumQueries(0):
            result1 = funf(entity1, user)
            result2 = funf(entity2, user)

        self.assertHTMLEqual(
            '<ul class="limited-list"><li>Content02</li><li>Content01</li></ul>',
            result1.render(ViewTag.HTML_LIST),
        )
        self.assertHTMLEqual(
            '<ul class="limited-list"><li>Content04</li><li>Content03</li></ul>',
            result2.render(ViewTag.HTML_LIST),
        )

    def test_function_field__no_app_perm(self):
        user = self.create_user(
            role=self.create_role(allowed_apps=['creme_core']),  # Not 'assistants'
        )
        entity = self.create_entity(user=user)
        funf = function_field_registry.get(CremeEntity, 'assistants-get_memos')

        with self.assertNumQueries(0):
            result = funf(entity, user)

        self.assertEqual(_('Forbidden app'), result.render(ViewTag.HTML_LIST))

    def test_function_field__no_app_perm__prefetch(self):
        user = self.create_user(
            role=self.create_role(allowed_apps=['creme_core']),  # Not 'assistants'
        )
        funf = function_field_registry.get(CremeEntity, 'assistants-get_memos')
        entity = self.create_entity(user=user)

        with self.assertNumQueries(0):
            funf.populate_entities([entity], user)

        with self.assertNumQueries(0):
            result = funf(entity, user)
        self.assertEqual(_('Forbidden app'), result.render(ViewTag.HTML_LIST))

    def test_merge(self):
        def creator(user, contact01, contact02):
            create = partial(Memo.objects.create, user=user)
            create(content='This guy is strong',           real_entity=contact01)
            create(content='This guy lost himself easily', real_entity=contact02)
            self.assertEqual(2, Memo.objects.count())

        def assertor(contact01):
            memos = Memo.objects.all()
            self.assertEqual(2, len(memos))

            for memo in memos:
                self.assertEqual(contact01, memo.real_entity)

        self.aux_test_merge(creator, assertor)

    def test_brick(self):
        user = self.login_as_assistants_user()
        self.add_credentials(role=user.role, own=['VIEW'])

        entity1 = self.create_entity(user=user)

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity2 = create_orga(name='Acme')
        entity3 = create_orga(name='Deleted', is_deleted=True)

        def create_memo(content, entity, on_homepage=True):
            return Memo.objects.create(
                user=user, content=content, real_entity=entity, on_homepage=on_homepage,
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

        response1 = self.assertGET200(entity1.get_absolute_url())
        detail_brick_node = self.get_brick_node(
            self.get_html_tree(response1.content), brick=MemosBrick,
        )

        self.assertTrue(memo_found(detail_brick_node, memo1))
        self.assertTrue(memo_found(detail_brick_node, memo2))
        self.assertFalse(memo_found(detail_brick_node, memo3))

        # ---
        BrickHomeLocation.objects.get_or_create(
            brick_id=MemosBrick.id, defaults={'order': 50},
        )

        response2 = self.assertGET200(reverse('creme_core__home'))
        home_brick_node = self.get_brick_node(
            self.get_html_tree(response2.content), brick=MemosBrick,
        )

        self.assertTrue(memo_found(home_brick_node, memo1))
        self.assertFalse(memo_found(home_brick_node, memo2))
        self.assertTrue(memo_found(home_brick_node, memo3))
        self.assertFalse(memo_found(home_brick_node, memo4))
        self.assertInstanceLink(home_brick_node, entity1)
        self.assertInstanceLink(home_brick_node, entity2)

    def test_manager_filter_by_user(self):
        "Teams."
        user = self.get_root_user()
        other_user = self.create_user(0)
        teammate1  = self.create_user(1)
        teammate2  = self.create_user(2)

        team1 = self.create_team('Team #1', teammate1, user)
        team2 = self.create_team('Team #2', other_user, teammate2)

        create_memo = partial(
            Memo.objects.create,
            real_entity=self.create_entity(user=user), user=user, on_homepage=True,
        )
        memo1 = create_memo(content='Memo#1')
        memo2 = create_memo(content='Memo#2', user=team1)
        create_memo(content='Memo#3', user=team2)  # No (other team)
        self.assertCountEqual([memo1, memo2], Memo.objects.filter_by_user(user))
