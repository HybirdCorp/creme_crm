from datetime import datetime, timedelta
from functools import partial
from unittest import SkipTest

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models.query import Q, QuerySet
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.timezone import localtime, now
from django.utils.translation import gettext as _

from creme.creme_core.constants import UUID_CHANNEL_REMINDERS
from creme.creme_core.core.entity_cell import EntityCellFunctionField
from creme.creme_core.core.function_field import function_field_registry
# Should be a test queue
from creme.creme_core.core.job import get_queue
from creme.creme_core.forms.listview import TextLVSWidget
from creme.creme_core.gui.job import JobErrorsBrick
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    BrickState,
    CremeEntity,
    FakeContact,
    FakeOrganisation,
    HistoryLine,
    JobResult,
    Notification,
    SettingValue,
)
from creme.creme_core.models.history import (
    TYPE_AUX_CREATION,
    TYPE_AUX_DELETION,
    TYPE_AUX_EDITION,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from ..bricks import TodosBrick
from ..constants import BRICK_STATE_HIDE_VALIDATED_TODOS
from ..function_fields import TodosField
from ..models import Alert, ToDo
from ..notification import TodoReminderContent
from ..setting_keys import todo_reminder_key
from .base import AssistantsTestCase


class TodoTestCase(BrickTestCaseMixin, AssistantsTestCase):
    @staticmethod
    def _build_add_url(entity):
        return reverse('assistants__create_todo', args=(entity.id,))

    def _create_todo(self, *, entity, user, title='TITLE', description='DESCRIPTION', **kwargs):
        return ToDo.objects.create(
            real_entity=entity, user=user, title=title, description=description,
            **kwargs
        )

    def test_populate(self):
        sv = self.get_object_or_fail(SettingValue, key_id=todo_reminder_key.id)
        self.assertEqual('assistants', sv.key.app_label)
        self.assertEqual(9, sv.value)

    def test_create(self):
        user = self.login_as_assistants_user()
        self.add_credentials(role=user.role, all=['VIEW', 'CHANGE'])
        self.assertFalse(ToDo.objects.exists())

        other_user = self.create_user(index=1)

        entity = self.create_entity(user=other_user)

        queue = get_queue()
        queue.clear()

        context = self.assertGET200(self._build_add_url(entity)).context
        self.assertEqual(
            _('New todo for «{entity}»').format(entity=entity),
            context.get('title'),
        )
        self.assertEqual(_('Save the todo'), context.get('submit_label'))

        with self.assertNoException():
            fields = context['form'].fields
            user_f = fields['user']
            hours = fields['deadline_hour'].choices

        self.assertFalse(user_f.required)
        self.assertEqual(
            _('Same owner than the entity (currently «{user}»)').format(user=other_user),
            user_f.empty_label,
        )

        self.assertInChoices(value=0, label='0h', choices=hours)
        self.assertInChoices(value=23, label='23h', choices=hours)
        self.assertEqual(24, len(hours))

        # ---
        title = 'Title'
        description = 'Description'
        self.assertNoFormError(self.client.post(
            self._build_add_url(entity),
            data={
                'user':        user.pk,
                'title':       title,
                'description': description,
            },
        ))

        todo = self.get_object_or_fail(ToDo, title=title, description=description)
        self.assertEqual(user, todo.user)
        self.assertEqual(entity.id,          todo.entity_id)
        self.assertEqual(entity.entity_type, todo.entity_content_type)
        self.assertIsNone(todo.deadline)
        self.assertIs(todo.reminded, False)

        now_value = now()
        self.assertDatetimesAlmostEqual(now_value, todo.creation_date)
        self.assertDatetimesAlmostEqual(now_value, todo.modification_date)

        self.assertEqual(1, ToDo.objects.count())

        self.assertFalse(queue.refreshed_jobs)  # Because there is no deadline

        self.assertEqual(title, str(todo))

    def test_create__no_app_perm(self):
        user = self.login_as_standard()
        self.add_credentials(role=user.role, all=['VIEW', 'CHANGE'])
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

    def test_create__dynamic_user(self):
        "Deadline + dynamic user."
        user = self.login_as_root_and_get()
        entity = self.create_entity(user=user)

        queue = get_queue()
        queue.clear()

        url = self._build_add_url(entity)
        title = 'my Todo'
        data = {
            # 'user':      ...,
            'title':       title,
            'description': '',
            'deadline':    self.formfield_value_date(2013, 6, 7),
        }
        response1 = self.assertPOST200(url, data=data)
        self.assertFormError(
            response1.context['form'],
            field='deadline_hour',
            errors=_('The hour is required if you set a date.'),
        )

        # ---
        self.assertNoFormError(self.client.post(url, data={**data, 'deadline_hour': 9}))

        todo = self.get_object_or_fail(ToDo, title=title)
        self.assertIsNone(todo.user)
        self.assertEqual(
            self.create_datetime(year=2013, month=6, day=7, hour=9),
            todo.deadline,
        )
        self.assertTrue(queue.refreshed_jobs)

    def test_edit(self):
        user = self.login_as_assistants_user()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])

        title = 'Title'
        description = 'Description'
        entity = self.create_entity(user=user)
        todo = ToDo.objects.create(
            user=user, real_entity=entity, title=title, description=description,
        )

        url = todo.get_edit_absolute_url()
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')

        context = response1.context
        self.assertEqual(
            _('Todo for «{entity}»').format(entity=entity),
            context.get('title'),
        )
        self.assertEqual(_('Save the modifications'), context.get('submit_label'))

        # ---
        title       += '_edited'
        description += '_edited'
        response1 = self.client.post(
            url,
            data={
                'user':        user.pk,
                'title':       title,
                'description': description,
            },
        )
        self.assertNoFormError(response1)

        todo = self.refresh(todo)
        self.assertEqual(title,       todo.title)
        self.assertEqual(description, todo.description)

    def test_edit__deleted_entity(self):
        user = self.login_as_root_and_get()
        entity = self.create_entity(user=user, is_deleted=True)
        todo = self._create_todo(user=user, entity=entity)

        with self.assertNoException():
            todo = self.refresh(todo)
            entity2 = todo.real_entity

        self.assertEqual(entity, entity2)
        self.assertGET403(todo.get_edit_absolute_url())

    def test_edit__no_app_perm(self):
        user = self.login_as_standard()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])

        title = 'Title'
        description = 'Description'
        entity = self.create_entity(user=user)
        todo = ToDo.objects.create(
            user=user, real_entity=entity, title=title, description=description,
        )
        response = self.assertGET403(
            todo.get_edit_absolute_url(), HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(
            _('You are not allowed to access to the app: {}').format(
                _('Assistants (Todos, Memos, …)')
            ),
            response.text,
        )

    def test_delete_related(self):
        user = self.login_as_root_and_get()
        entity = self.create_entity(user=user)
        self._create_todo(user=user, entity=entity)
        self.assertEqual(1, ToDo.objects.count())

        entity.delete()
        self.assertEqual(0, ToDo.objects.count())

    def test_delete(self):
        user = self.login_as_assistants_user()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])

        todo = self._create_todo(user=user, entity=self.create_entity(user=user))
        ct = ContentType.objects.get_for_model(ToDo)
        self.assertPOST200(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': todo.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertDoesNotExist(todo)

    def test_validate(self):
        user = self.login_as_assistants_user()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])

        entity = self.create_entity(user=user)
        todo = self._create_todo(user=user, entity=entity)
        self.assertFalse(todo.is_ok)

        url = reverse('assistants__validate_todo', args=(todo.id,))
        self.assertGET405(url)

        response = self.assertPOST200(url, follow=True)
        self.assertRedirects(response, entity.get_absolute_url())
        self.assertIs(True, self.refresh(todo).is_ok)

    def test_validate__no_app_perm(self):
        user = self.login_as_standard()
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])

        entity = self.create_entity(user=user)
        todo = self._create_todo(user=user, entity=entity)
        response = self.assertPOST403(
            reverse('assistants__validate_todo', args=(todo.id,)),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
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
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity2 = create_orga(name='Acme')
        entity3 = create_orga(name='Deleted', is_deleted=True)

        def create_todo(title, entity, is_ok=False):
            return ToDo.objects.create(
                user=user, title=title, real_entity=entity, is_ok=is_ok,
            )

        todo1 = create_todo('Recall',         entity1)
        todo2 = create_todo("It's important", entity1, is_ok=True)
        todo3 = create_todo('Other',          entity2)
        todo4 = create_todo('Ignore me',      entity3)

        TodosBrick.page_size = max(4, settings.BLOCK_SIZE)

        def todo_found(brick_node, todo):
            title = todo.title
            return any(n.text == title for n in brick_node.findall('.//td'))

        # Detail + do not hide ---
        BrickDetailviewLocation.objects.create_if_needed(
            brick=TodosBrick,
            model=type(entity1),
            order=50,
            zone=BrickDetailviewLocation.RIGHT,
        )

        response1 = self.assertGET200(entity1.get_absolute_url())
        detail_brick_node = self.get_brick_node(
            self.get_html_tree(response1.content), brick=TodosBrick,
        )

        self.assertTrue(todo_found(detail_brick_node,  todo1))
        self.assertTrue(todo_found(detail_brick_node,  todo2))
        self.assertFalse(todo_found(detail_brick_node, todo3))

        # Home + do no hide ---
        BrickHomeLocation.objects.get_or_create(
            brick_id=TodosBrick.id, defaults={'order': 50},
        )

        response2 = self.assertGET200(reverse('creme_core__home'))
        home_brick_node = self.get_brick_node(
            self.get_html_tree(response2.content), brick=TodosBrick,
        )

        self.assertTrue(todo_found(home_brick_node, todo1))
        self.assertTrue(todo_found(home_brick_node, todo2))
        self.assertTrue(todo_found(home_brick_node, todo3))
        self.assertFalse(todo_found(home_brick_node, todo4))
        self.assertInstanceLink(home_brick_node, entity1)
        self.assertInstanceLink(home_brick_node, entity2)

        # Detail + hide validated ---
        state = BrickState.objects.get_for_brick_id(user=user, brick_id=TodosBrick.id)
        state.set_extra_data(key=BRICK_STATE_HIDE_VALIDATED_TODOS, value=True)
        state.save()

        response3 = self.assertGET200(entity1.get_absolute_url())
        detail_brick_node_hidden = self.get_brick_node(
            self.get_html_tree(response3.content), brick=TodosBrick,
        )

        self.assertTrue(todo_found(detail_brick_node_hidden, todo1))
        self.assertFalse(todo_found(detail_brick_node_hidden, todo2))
        self.assertFalse(todo_found(detail_brick_node_hidden, todo3))

        # Home + hide validated ---
        response4 = self.assertGET200(reverse('creme_core__home'))
        home_brick_node_hidden = self.get_brick_node(
            self.get_html_tree(response4.content), brick=TodosBrick,
        )

        self.assertTrue(todo_found(home_brick_node_hidden, todo1))
        self.assertFalse(todo_found(home_brick_node_hidden, todo2))
        self.assertTrue(todo_found(home_brick_node_hidden, todo3))
        self.assertFalse(todo_found(home_brick_node_hidden, todo4))

    def test_brick__no_app_perm(self):
        user = self.login_as_standard()
        self.add_credentials(role=user.role, own=['VIEW'])

        entity = self.create_entity(user=user)
        BrickDetailviewLocation.objects.create_if_needed(
            brick=TodosBrick,
            model=type(entity),
            order=50,
            zone=BrickDetailviewLocation.RIGHT,
        )

        response = self.assertGET200(entity.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=TodosBrick,
        )
        # TODO: method?
        self.assertIn('brick-forbidden', brick_node.attrib.get('class'))

    def test_brick_reload__detailview(self):
        user = self.login_as_root_and_get()
        entity = self.create_entity(user=user)

        for i in range(1, 4):
            self._create_todo(
                user=user, entity=entity,
                title=f'Todo{i}', description=f'Description {i}',
            )

        todos = ToDo.objects.filter(entity=entity.id)
        self.assertEqual(3, len(todos))
        self.assertCountEqual(ToDo.objects.all(), todos)

        self.assertGreaterEqual(TodosBrick.page_size, 2)

        response = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(entity.id,)),
            data={'brick_id': TodosBrick.id},
        )
        self.assertEqual('application/json', response['Content-Type'])

        content = response.json()
        self.assertEqual(1, len(content))
        self.assertEqual(2, len(content[0]))
        self.assertEqual(TodosBrick.id, content[0][0])

        with self.assertNoException():
            page = response.context['page']

        size = min(3, settings.BLOCK_SIZE)
        self.assertEqual(size, len(page.object_list))
        self.assertEqual(size, len({*todos} & {*page.object_list}))

    def test_brick_reload__home(self):
        user1 = self.login_as_root_and_get()
        user2 = self.create_user()

        entity1 = self.create_entity(user=user1)
        entity2 = FakeContact.objects.create(
            user=user1, first_name='Akane', last_name='Tendo',
        )

        self._create_todo(user=user1, entity=entity1, title='Todo01')
        self._create_todo(user=user1, entity=entity2, title='Todo02')
        self._create_todo(user=user2, entity=entity1, title='Todo03')

        todos = ToDo.objects.filter_by_user(user1)
        self.assertEqual(2, len(todos))

        response = self.assertGET200(
            reverse('creme_core__reload_home_bricks'),
            data={'brick_id': TodosBrick.id},
        )
        self.assertEqual('application/json', response['Content-Type'])

        content = response.json()
        self.assertEqual(1, len(content))
        self.assertEqual(2, len(content[0]))
        self.assertEqual(TodosBrick.id, content[0][0])

        with self.assertNoException():
            page = response.context['page']

        self.assertCountEqual(todos, page.object_list)

    @staticmethod
    def _oldify_todo(todo):
        cdate = todo.creation_date
        todo.creation_date = cdate - timedelta(days=1)
        todo.save()

        return todo

    def test_function_field__empty(self):
        user = self.get_root_user()
        entity = self.create_entity(user=user)

        funf = function_field_registry.get(CremeEntity, 'assistants-get_todos')
        self.assertIsInstance(funf, TodosField)
        self.assertEqual(
            '', funf(entity, user).render(ViewTag.HTML_LIST),
        )

        # ---
        field_class = funf.search_field_builder
        self.assertIsNotNone(field_class)

        field = field_class(
            cell=EntityCellFunctionField(model=FakeContact, func_field=funf),
            user=user,
        )
        self.assertIsInstance(field.widget, TextLVSWidget)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=None))
        self.assertEqual(Q(), to_python(value=''))

        value = 'foobar'
        self.assertQEqual(
            Q(
                assistants_todos__title__icontains=value,
                assistants_todos__is_ok=False,
            ),
            to_python(value=value),
        )

    def test_function_field(self):
        user = self.create_user(
            role=self.create_role(allowed_apps=['creme_core', 'assistants']),
        )
        entity = self.create_entity(user=user)

        funf = function_field_registry.get(CremeEntity, 'assistants-get_todos')

        todo1 = self._oldify_todo(self._create_todo(user=user, entity=entity, title='Todo01'))
        todo2 = self._create_todo(user=user, entity=entity, title='Todo02')
        self._create_todo(user=user, entity=entity, title='Todo03', is_ok=True)

        with self.assertNumQueries(1):
            result = funf(entity, user)

        self.assertEqual(
            f'<ul class="limited-list"><li>{todo2.title}</li><li>{todo1.title}</li></ul>',
            result.render(ViewTag.HTML_LIST),
        )

        # limit to 3 ToDos
        # self._create_todo('Todo03', 'Description03')
        # self._create_todo('Todo04', 'Description04')
        # self.assertHTMLEqual(
        #     '<ul><li>Todo04</li><li>Todo03</li><li>Todo02</li></ul>',
        #     funf(self.entity)
        # )

    def test_function_field__prefetch(self):
        "Prefetch with 'populate_entities()'."
        user = self.create_user(
            role=self.create_role(allowed_apps=['creme_core', 'assistants']),
        )

        entity1 = self.create_entity(user=user)
        entity2 = CremeEntity.objects.create(user=user)

        todo1 = self._oldify_todo(self._create_todo(user=user, entity=entity1, title='Todo01'))
        todo2 = self._create_todo(user=user, entity=entity1, title='Todo02')
        self._create_todo(user=user, entity=entity1, title='Todo03', is_ok=True)

        todo4 = self._create_todo(user=user, entity=entity2, title='Todo04')

        funf = function_field_registry.get(CremeEntity, 'assistants-get_todos')

        with self.assertNumQueries(1):
            funf.populate_entities([entity1, entity2], user)

        with self.assertNumQueries(0):
            result1 = funf(entity1, user)
            result2 = funf(entity2, user)

        self.assertEqual(
            f'<ul class="limited-list"><li>{todo2.title}</li><li>{todo1.title}</li></ul>',
            result1.render(ViewTag.HTML_LIST),
        )
        self.assertEqual(todo4.title, result2.render(ViewTag.HTML_LIST))

    def test_function_field__no_app_perm(self):
        user = self.create_user(
            role=self.create_role(allowed_apps=['creme_core']),  # Not 'assistants'
        )
        entity = self.create_entity(user=user)
        funf = function_field_registry.get(CremeEntity, 'assistants-get_todos')

        with self.assertNumQueries(0):
            result = funf(entity, user)

        self.assertEqual(_('Forbidden app'), result.render(ViewTag.HTML_LIST))

    def test_function_field__no_app_perm__prefetch(self):
        user = self.create_user(
            role=self.create_role(allowed_apps=['creme_core']),  # Not 'assistants'
        )
        funf = function_field_registry.get(CremeEntity, 'assistants-get_todos')
        entity = self.create_entity(user=user)

        with self.assertNumQueries(0):
            funf.populate_entities([entity], user)

        with self.assertNumQueries(0):
            result = funf(entity, user)
        self.assertEqual(_('Forbidden app'), result.render(ViewTag.HTML_LIST))

    def test_merge(self):
        def creator(user, contact01, contact02):
            self._create_todo(
                user=user, entity=contact01, title='Todo01', description='Fight against him',
            )
            self._create_todo(
                user=user, entity=contact02, title='Todo02', description='Train with him',
            )
            self.assertEqual(2, ToDo.objects.count())

        def assertor(contact01):
            todos = ToDo.objects.all()
            self.assertEqual(2, len(todos))

            for todo in todos:
                self.assertEqual(contact01, todo.real_entity)

        self.aux_test_merge(creator, assertor)

    @override_settings(SITE_DOMAIN='https://crm.domain')
    def test_reminder_content(self):
        user = self.get_root_user()
        entity = self.create_entity(user=user)
        todo = self._create_todo(
            user=user, entity=entity,
            title='You must do something',
            description='very important!!\nReally.',
            deadline=self.create_datetime(year=2023, month=10, day=23, hour=16, utc=True),
        )
        content1 = TodoReminderContent(instance=todo)
        content2 = TodoReminderContent.from_dict(content1.as_dict())
        self.assertEqual(
            _('A todo related to «%(entity)s» will soon reach its deadline') % {'entity': entity},
            content2.get_subject(user=user),
        )
        self.assertEqual(
            '{}\n{}'.format(
                _('The todo «%(title)s» will expire on %(expiration)s.') % {
                    'title': todo.title,
                    'expiration': date_format(
                        value=localtime(todo.deadline),
                        format='DATETIME_FORMAT',
                    ),
                },
                _('Description: %(description)s') % {'description': todo.description},
            ),
            content2.get_body(user=user),
        )
        self.assertHTMLEqual(
            '<h1>{title}</h1><p>{body}</p>'.format(
                title=todo.title,
                body=todo.description.replace('\n', '<br>'),
            ) + _('Related to %(entity)s') % {
                'entity': (
                    f'<a href="https://crm.domain{entity.get_absolute_url()}" target="_self">'
                    f'{entity}'
                    f'</a>'
                ),
            },
            content2.get_html_body(user=user),
        )

    @override_settings(SITE_DOMAIN='https://creme.domain')
    def test_reminder_content__no_description(self):
        user = self.get_root_user()
        entity = self.create_entity(user=user)
        todo = self._create_todo(
            user=user, entity=entity, title='To be done',
            description='',  # <====
            deadline=now() + timedelta(days=7),
        )
        content1 = TodoReminderContent(instance=todo)
        content2 = TodoReminderContent.from_dict(content1.as_dict())
        self.assertEqual(
            _('The todo «%(title)s» will expire on %(expiration)s.') % {
                'title': todo.title,
                'expiration': date_format(
                    value=localtime(todo.deadline),
                    format='DATETIME_FORMAT',
                ),
            },
            content2.get_body(user=user).strip(),
        )
        self.assertHTMLEqual(
            '<h1>{title}</h1>'.format(
                title=todo.title,
            ) + _('Related to %(entity)s') % {
                'entity': (
                    f'<a href="https://creme.domain{entity.get_absolute_url()}" target="_self">'
                    f'{entity}'
                    f'</a>'
                ),
            },
            content2.get_html_body(user=user),
        )

    def test_reminder_content__error(self):
        "Todo does not exist anymore."
        user = self.get_root_user()
        content = TodoReminderContent.from_dict({'instance': self.UNUSED_PK})
        self.assertEqual(
            _('A todo will soon reach its deadline'),
            content.get_subject(user=user),
        )
        body = _('The todo has been deleted')
        self.assertEqual(body, content.get_body(user=user))
        self.assertEqual(body, content.get_html_body(user=user))

    def test_reminder(self):
        user = self.login_as_root_and_get()
        entity = self.create_entity(user=user)
        now_value = now()

        sv = self.get_object_or_fail(SettingValue, key_id=todo_reminder_key.id)
        sv.value = localtime(now_value).hour
        sv.save()

        notif_qs = Notification.objects.filter(channel__uuid=UUID_CHANNEL_REMINDERS, user=user)
        self.assertFalse(notif_qs.all())

        job = self.get_reminder_job()
        self.assertIsNone(job.type.next_wakeup(job, now_value))

        create_todo = partial(ToDo.objects.create, real_entity=entity, user=user)
        todo1 = create_todo(title='Todo#1', deadline=now_value)
        create_todo(title='Todo#2', deadline=now_value + timedelta(days=2))
        create_todo(title='Todo#3')
        todo4 = create_todo(title='Todo#4', deadline=now_value, is_ok=True)

        self.assertLess(job.type.next_wakeup(job, now_value), now())

        self.execute_reminder_job(job)
        self.assertIsNone(job.user)

        notif = self.get_alone_element(notif_qs.all())
        self.assertFalse(notif.discarded)
        self.assertEqual(Notification.Level.NORMAL, notif.level)
        self.assertEqual(TodoReminderContent.id, notif.content_id)
        self.assertEqual({'instance': todo1.id}, notif.content_data)
        self.assertIsInstance(notif.content, TodoReminderContent)

        self.assertTrue(self.refresh(todo1).reminded)
        self.assertFalse(self.refresh(todo4).reminded)

        self.assertFalse(JobResult.objects.filter(job=job))

        response = self.assertGET200(job.get_absolute_url())
        self.get_brick_node(self.get_html_tree(response.content), brick=JobErrorsBrick)

    def test_reminder__minimum_hour(self):
        "Minimum hour (SettingValue) is in the future."
        user = self.get_root_user()
        entity = self.create_entity(user=user)
        now_value = now()

        next_hour = localtime(now_value).hour + 1
        if next_hour > 23:
            raise SkipTest('It is too late.')

        sv = self.get_object_or_fail(SettingValue, key_id=todo_reminder_key.id)
        sv.value = next_hour
        sv.save()

        notif_qs = Notification.objects.filter(channel__uuid=UUID_CHANNEL_REMINDERS, user=user)
        self.assertFalse(notif_qs.all())

        self._create_todo(entity=entity, user=user, title='Todo #1', deadline=now_value)

        job = self.get_reminder_job()
        wakeup = job.type.next_wakeup(job, now_value)
        self.assertIsInstance(wakeup, datetime)
        self.assertDatetimesAlmostEqual(
            localtime(now()).replace(hour=next_hour), wakeup,
        )

        self.execute_reminder_job(job)
        self.assertFalse(notif_qs.all())

    def test_reminder__teams(self):
        user = self.get_root_user()
        entity = self.create_entity(user=user)
        now_value = now()

        teammate = self.create_user(0)
        team = self.create_team('Team #1', teammate, user)

        sv = self.get_object_or_fail(SettingValue, key_id=todo_reminder_key.id)
        sv.value = max(localtime(now_value).hour - 1, 0)
        sv.save()

        self._create_todo(title='Todo#1', deadline=now_value, entity=entity, user=team)

        self.execute_reminder_job()

        uid = UUID_CHANNEL_REMINDERS
        self.get_object_or_fail(Notification, channel__uuid=uid, user=user)
        self.get_object_or_fail(Notification, channel__uuid=uid, user=teammate)
        self.assertFalse(Notification.objects.filter(channel__uuid=uid, user=team).exists())

    def test_reminder__dynamic_user(self):
        other_user = self.create_user()
        entity = self.create_entity(user=other_user)
        now_value = now()

        sv = self.get_object_or_fail(SettingValue, key_id=todo_reminder_key.id)
        sv.value = localtime(now_value).hour
        sv.save()

        notif_qs = Notification.objects.filter(
            channel__uuid=UUID_CHANNEL_REMINDERS, user=other_user,
        )
        self.assertFalse(notif_qs.all())

        ToDo.objects.create(real_entity=entity, title='Todo#1', deadline=now_value)

        self.execute_reminder_job(self.get_reminder_job())
        self.get_alone_element(notif_qs.all())

    def test_next_wakeup01(self):
        "Next wake is one day later + minimum hour."
        user = self.get_root_user()
        entity = self.create_entity(user=user)
        now_value = now()

        next_hour = localtime(now_value).hour + 1
        if next_hour > 23:
            raise SkipTest('It is too late.')

        sv = self.get_object_or_fail(SettingValue, key_id=todo_reminder_key.id)
        sv.value = next_hour
        sv.save()

        def create_todo(title, deadline, **kwargs):
            ToDo.objects.create(
                real_entity=entity, user=user,
                title=title, deadline=deadline, **kwargs
            )

        create_todo('Todo#2', now_value, is_ok=True)
        create_todo('Todo#4', now_value, reminded=True)
        create_todo('Todo#6', now_value + timedelta(days=3))
        create_todo('Todo#1', now_value + timedelta(days=2))  # <==== this one should be used
        create_todo('Todo#3', now_value, is_ok=True)
        create_todo('Todo#5', now_value, reminded=True)
        create_todo('Todo#7', now_value + timedelta(days=4))

        job = self.get_reminder_job()

        self.assertEqual(
            (localtime(now_value + timedelta(days=1))).replace(hour=next_hour),
            job.type.next_wakeup(job, now_value),
        )

    def test_next_wakeup02(self):
        "Next wake is one day later (but minimum hour has passed)."
        user = self.get_root_user()
        entity = self.create_entity(user=user)
        now_value = now()

        previous_hour = localtime(now_value).hour - 1
        if previous_hour < 0:
            raise SkipTest('It is too early.')

        sv = self.get_object_or_fail(SettingValue, key_id=todo_reminder_key.id)
        sv.value = previous_hour
        sv.save()

        self._create_todo(
            entity=entity, user=user, title='Todo#1',
            deadline=now_value + timedelta(days=2),
        )

        job = self.get_reminder_job()
        self.assertEqual(now_value + timedelta(days=1), job.type.next_wakeup(job, now_value))

    @override_settings(DEFAULT_TIME_ALERT_REMIND=30)
    def test_next_wakeup03(self):
        "ToDos + Alerts => minimum wake up."
        user = self.get_root_user()
        entity = self.create_entity(user=user)
        now_value = now()

        previous_hour = localtime(now_value).hour - 1
        if previous_hour < 0:
            raise SkipTest('It is too early.')

        sv = self.get_object_or_fail(SettingValue, key_id=todo_reminder_key.id)
        sv.value = previous_hour
        sv.save()

        self._create_todo(
            entity=entity, user=user, title='Todo#1',
            deadline=now_value + timedelta(days=2),
        )
        alert = Alert.objects.create(
            real_entity=entity, user=user, title='Alert#1',
            trigger_date=now_value + timedelta(days=3),
        )

        job = self.get_reminder_job()
        self.assertEqual(
            now_value + timedelta(days=1),
            job.type.next_wakeup(job, now_value),
        )

        alert.trigger_date = now_value + timedelta(minutes=50)
        alert.save()
        self.assertEqual(
            now_value + timedelta(minutes=20),
            job.type.next_wakeup(job, now_value),
        )

    @staticmethod
    def _get_hlines():
        return [*HistoryLine.objects.order_by('id')]

    def test_history__creation(self):
        user = self.get_root_user()
        entity = self.create_entity(user=user)
        old_count = HistoryLine.objects.count()

        self._create_todo(user=user, entity=entity)
        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(entity.id,          hline.entity.id)
        self.assertEqual(entity.entity_type, hline.entity_ctype)
        self.assertEqual(user,              hline.entity_owner)
        self.assertEqual(TYPE_AUX_CREATION, hline.type)

    def test_history__edition(self):
        user = self.get_root_user()
        entity = self.create_entity(user=user)
        todo = ToDo.objects.create(user=user, real_entity=entity, title='Todo#1')
        old_count = HistoryLine.objects.count()

        todo = self.refresh(todo)  # reset cache
        todo.description = description = 'Conquer the world'
        todo.save()

        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(entity.id,         hline.entity.id)
        self.assertEqual(TYPE_AUX_EDITION, hline.type)
        self.assertListEqual(
            [
                [
                    ContentType.objects.get_for_model(ToDo).id,
                    todo.id,
                    str(todo),
                ],
                ['description', description],
            ],
            hline.modifications,
        )

    def test_history__deletion(self):
        user = self.get_root_user()
        entity = self.create_entity(user=user)
        todo = self._create_todo(user=user, entity=entity, title='Todo#1')
        old_count = HistoryLine.objects.count()

        todo.delete()
        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(entity.id,          hline.entity.id)
        self.assertEqual(TYPE_AUX_DELETION, hline.type)

    def test_manager_filter_by_user(self):
        user = self.get_root_user()
        entity = self.create_entity(user=user)

        other_user = self.create_user(0)
        teammate1  = self.create_user(1)
        teammate2  = self.create_user(2)

        team1 = self.create_team('Team #1', teammate1, user)
        team2 = self.create_team('Team #2', other_user, teammate2)

        create_todo = partial(ToDo.objects.create, real_entity=entity, user=user)
        todo1 = create_todo(title='Todo#1')
        create_todo(title='Todo#2', user=other_user)  # No (other user)
        todo3 = create_todo(title='Todo#3', user=team1)
        create_todo(title='Todo#4', user=team2)  # No (other team)

        todos = ToDo.objects.filter_by_user(user)
        self.assertIsInstance(todos, QuerySet)
        self.assertEqual(ToDo, todos.model)

        self.assertCountEqual([todo1, todo3], todos)

    def test_brick_hide_validated_todos(self):
        user = self.login_as_root_and_get()

        def get_state():
            return BrickState.objects.get_for_brick_id(user=user, brick_id=TodosBrick.id)

        self.assertIsNone(get_state().pk)

        url = reverse('assistants__hide_validated_todos')
        self.assertGET405(url)

        # ---
        self.assertPOST200(url, data={'value': 'true'})
        state1 = get_state()
        self.assertIsNotNone(state1.pk)
        self.assertIs(
            state1.get_extra_data(BRICK_STATE_HIDE_VALIDATED_TODOS),
            True,
        )

        # ---
        self.assertPOST200(url, data={'value': '0'})
        self.assertIs(
            get_state().get_extra_data(BRICK_STATE_HIDE_VALIDATED_TODOS),
            False,
        )
