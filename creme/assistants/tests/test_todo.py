from datetime import datetime, timedelta
from functools import partial
from unittest import SkipTest

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
# from django.core import mail
# from django.core.mail.backends.locmem import EmailBackend
from django.db.models.query import Q, QuerySet
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.timezone import localtime, now
from django.utils.translation import gettext as _

from creme.creme_core.bricks import JobErrorsBrick
from creme.creme_core.constants import UUID_CHANNEL_REMINDERS
from creme.creme_core.core.entity_cell import EntityCellFunctionField
from creme.creme_core.core.function_field import function_field_registry
# Should be a test queue
from creme.creme_core.core.job import get_queue
from creme.creme_core.forms.listview import TextLVSWidget
from creme.creme_core.gui.view_tag import ViewTag
# from creme.creme_core.models import DateReminder
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
from ..constants import (
    BRICK_STATE_HIDE_VALIDATED_TODOS,
    MIN_HOUR_4_TODO_REMINDER,
)
from ..function_fields import TodosField
from ..models import Alert, ToDo
from ..notification import TodoReminderContent
from .base import AssistantsTestCase


class TodoTestCase(BrickTestCaseMixin, AssistantsTestCase):
    # @classmethod
    # def setUpClass(cls):
    #     super().setUpClass()
    #     cls.original_send_messages = EmailBackend.send_messages
    #
    # def tearDown(self):
    #     super().tearDown()
    #     EmailBackend.send_messages = self.original_send_messages

    @staticmethod
    def _build_add_url(entity):
        return reverse('assistants__create_todo', args=(entity.id,))

    def _create_todo(self, title='TITLE', description='DESCRIPTION', entity=None, user=None):
        entity = entity or self.entity
        user = user or self.user

        response = self.client.post(
            self._build_add_url(entity),
            data={
                'user':        user.pk,
                'title':       title,
                'description': description,
            },
        )
        self.assertNoFormError(response)

        return self.get_object_or_fail(ToDo, title=title, description=description)

    def _create_several_todos(self):
        self._create_todo('Todo01', 'Description01')

        entity2 = FakeContact.objects.create(
            user=self.user, first_name='Akane', last_name='Tendo',
        )
        self._create_todo('Todo02', 'Description02', entity=entity2)

        user2 = self.create_user(
            username='ryoga', first_name='Ryoga', last_name='Hibiki', email='user@creme.org',
        )
        self._create_todo('Todo03', 'Description03', user=user2)

    def test_populate(self):
        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        self.assertEqual('assistants', sv.key.app_label)
        self.assertEqual(9, sv.value)

    def test_create01(self):
        self.assertFalse(ToDo.objects.exists())
        other_user = self.create_user()

        entity = self.entity
        entity.user = other_user
        entity.save()

        queue = get_queue()
        queue.clear()

        entity = self.entity
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
        todo = self._create_todo(title, 'Description')
        self.assertEqual(1, ToDo.objects.count())
        self.assertEqual(self.user,             todo.user)
        self.assertEqual(entity.id,             todo.entity_id)
        self.assertEqual(entity.entity_type_id, todo.entity_content_type_id)
        self.assertDatetimesAlmostEqual(now(), todo.creation_date)
        self.assertIsNone(todo.deadline)
        self.assertIs(todo.reminded, False)

        self.assertFalse(queue.refreshed_jobs)  # Because there is no deadline

        self.assertEqual(title, str(todo))

    def test_create02(self):
        "Deadline + dynamic user."
        queue = get_queue()
        queue.clear()

        url = self._build_add_url(self.entity)
        title = 'my Todo'
        data = {
            # 'user':        self.user.pk,
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

    def test_edit01(self):
        title = 'Title'
        description = 'Description'
        todo = self._create_todo(title, description)

        url = todo.get_edit_absolute_url()
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(
            _('Todo for «{entity}»').format(entity=self.entity),
            context.get('title'),
        )
        self.assertEqual(_('Save the modifications'), context.get('submit_label'))

        # ---
        title       += '_edited'
        description += '_edited'
        response = self.client.post(
            url,
            data={
                'user':        self.user.pk,
                'title':       title,
                'description': description,
            },
        )
        self.assertNoFormError(response)

        todo = self.refresh(todo)
        self.assertEqual(title,       todo.title)
        self.assertEqual(description, todo.description)

    def test_edit02(self):
        "Entity is deleted."
        todo = self._create_todo()

        entity = self.entity
        entity.trash()

        with self.assertNoException():
            todo = self.refresh(todo)
            entity2 = todo.real_entity

        self.assertEqual(entity, entity2)
        self.assertGET403(todo.get_edit_absolute_url())

    def test_delete_related01(self):
        self._create_todo()
        self.assertEqual(1, ToDo.objects.count())

        self.entity.delete()
        self.assertEqual(0, ToDo.objects.count())

    def test_delete02(self):
        todo = self._create_todo()
        self.assertEqual(1, ToDo.objects.count())

        ct = ContentType.objects.get_for_model(ToDo)
        self.assertPOST(
            302,
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': todo.id},
        )
        self.assertFalse(ToDo.objects.all())

    def test_validate(self):
        todo = self._create_todo()
        self.assertFalse(todo.is_ok)

        url = reverse('assistants__validate_todo', args=(todo.id,))
        self.assertGET405(url)

        response = self.assertPOST200(url, follow=True)
        self.assertRedirects(response, self.entity.get_absolute_url())
        self.assertIs(True, self.refresh(todo).is_ok)

    def test_brick(self):
        user = self.user
        entity1 = self.entity

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

        response1 = self.assertGET200(self.entity.get_absolute_url())
        detail_brick_node = self.get_brick_node(
            self.get_html_tree(response1.content), brick=TodosBrick,
        )

        self.assertTrue(todo_found(detail_brick_node,  todo1))
        self.assertTrue(todo_found(detail_brick_node,  todo2))
        self.assertFalse(todo_found(detail_brick_node, todo3))

        # Home + do no hide ---
        BrickHomeLocation.objects.get_or_create(
            # brick_id=TodosBrick.id_, defaults={'order': 50},
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

        response3 = self.assertGET200(self.entity.get_absolute_url())
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

    def test_brick_reload01(self):
        "Detail-view."
        for i in range(1, 4):
            self._create_todo(f'Todo{i}', f'Description {i}')

        todos = ToDo.objects.filter(entity=self.entity.id)
        self.assertEqual(3, len(todos))
        self.assertCountEqual(ToDo.objects.all(), todos)

        self.assertGreaterEqual(TodosBrick.page_size, 2)

        response = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(self.entity.id,)),
            # data={'brick_id': TodosBrick.id_},
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

    def test_brick_reload02(self):
        "Home."
        self._create_several_todos()
        self.assertEqual(3, ToDo.objects.count())

        todos = ToDo.objects.filter_by_user(self.user)
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

    def test_function_field01(self):
        funf = function_field_registry.get(CremeEntity, 'assistants-get_todos')
        self.assertIsInstance(funf, TodosField)
        self.assertEqual(
            # '<ul></ul>', funf(self.entity, self.user).render(ViewTag.HTML_LIST),
            '', funf(self.entity, self.user).render(ViewTag.HTML_LIST),
        )

        # ---
        field_class = funf.search_field_builder
        self.assertIsNotNone(field_class)

        field = field_class(
            cell=EntityCellFunctionField(model=FakeContact, func_field=funf),
            user=self.user,
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

    def test_function_field02(self):
        funf = function_field_registry.get(CremeEntity, 'assistants-get_todos')
        self._oldify_todo(self._create_todo('Todo01', 'Description01'))
        self._create_todo('Todo02', 'Description02')

        todo3 = self._create_todo('Todo03', 'Description03')
        todo3.is_ok = True
        todo3.save()

        with self.assertNumQueries(1):
            result = funf(self.entity, self.user)

        self.assertEqual(
            # '<ul><li>Todo02</li><li>Todo01</li></ul>',
            '<ul class="limited-list"><li>Todo02</li><li>Todo01</li></ul>',
            result.render(ViewTag.HTML_LIST),
        )

        # limit to 3 ToDos
        # self._create_todo('Todo03', 'Description03')
        # self._create_todo('Todo04', 'Description04')
        # self.assertHTMLEqual(
        #     '<ul><li>Todo04</li><li>Todo03</li><li>Todo02</li></ul>',
        #     funf(self.entity)
        # )

    def test_function_field03(self):
        "Prefetch with 'populate_entities()'."
        user = self.user
        self._oldify_todo(self._create_todo('Todo01', 'Description01'))
        self._create_todo('Todo02', 'Description02')

        todo3 = self._create_todo('Todo03', 'Description03')
        todo3.is_ok = True
        todo3.save()

        entity02 = CremeEntity.objects.create(user=user)
        todo4 = self._create_todo('Todo04', 'Description04', entity=entity02)

        funf = function_field_registry.get(CremeEntity, 'assistants-get_todos')

        with self.assertNumQueries(1):
            funf.populate_entities([self.entity, entity02], user)

        with self.assertNumQueries(0):
            result1 = funf(self.entity, user)
            result2 = funf(entity02, user)

        self.assertEqual(
            # '<ul><li>Todo02</li><li>Todo01</li></ul>',
            '<ul class="limited-list"><li>Todo02</li><li>Todo01</li></ul>',
            result1.render(ViewTag.HTML_LIST),
        )
        self.assertEqual(
            # '<ul><li>Todo04</li></ul>', result2.render(ViewTag.HTML_LIST),
            todo4.title, result2.render(ViewTag.HTML_LIST),
        )

    def test_merge(self):
        def creator(contact01, contact02):
            self._create_todo('Todo01', 'Fight against him', contact01)
            self._create_todo('Todo02', 'Train with him',    contact02)
            self.assertEqual(2, ToDo.objects.count())

        def assertor(contact01):
            todos = ToDo.objects.all()
            self.assertEqual(2, len(todos))

            for todo in todos:
                self.assertEqual(contact01, todo.real_entity)

        self.aux_test_merge(creator, assertor)

    def test_todo_reminder_content01(self):
        user = self.get_root_user()
        entity = self.entity
        todo = ToDo.objects.create(
            user=user,
            real_entity=entity,
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
                'entity': f'<a href="{entity.get_absolute_url()}" target="_self">{entity}</a>',
            },
            content2.get_html_body(user=user),
        )

    def test_todo_reminder_content02(self):
        "No description."
        user = self.get_root_user()
        entity = self.entity
        todo = ToDo.objects.create(
            user=user,
            real_entity=entity,
            title='To be done',
            # description='very important!!\nReally.', # <====
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
                'entity': f'<a href="{entity.get_absolute_url()}" target="_self">{entity}</a>',
            },
            content2.get_html_body(user=user),
        )

    def test_todo_reminder_content_error(self):
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

    # @override_settings(SOFTWARE_LABEL='My CRM')
    def test_reminder01(self):
        user = self.user
        now_value = now()

        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        sv.value = localtime(now_value).hour
        sv.save()

        # DateReminder.objects.all().delete()
        notif_qs = Notification.objects.filter(channel__uuid=UUID_CHANNEL_REMINDERS, user=user)
        self.assertFalse(notif_qs.all())

        job = self.get_reminder_job()
        self.assertIsNone(job.type.next_wakeup(job, now_value))

        create_todo = partial(ToDo.objects.create, real_entity=self.entity, user=user)
        todo1 = create_todo(title='Todo#1', deadline=now_value)
        create_todo(title='Todo#2', deadline=now_value + timedelta(days=2))
        create_todo(title='Todo#3')
        todo4 = create_todo(title='Todo#4', deadline=now_value, is_ok=True)

        self.assertLess(job.type.next_wakeup(job, now_value), now())

        self.execute_reminder_job(job)
        self.assertIsNone(job.user)

        # reminder = self.get_alone_element(DateReminder.objects.all())
        # self.assertEqual(todo1, reminder.object_of_reminder)
        # self.assertEqual(1,     reminder.ident)
        # self.assertDatetimesAlmostEqual(now_value, reminder.date_of_remind, seconds=60)
        notif = self.get_alone_element(notif_qs.all())
        self.assertFalse(notif.discarded)
        self.assertEqual(Notification.Level.NORMAL, notif.level)
        self.assertEqual(TodoReminderContent.id, notif.content_id)
        self.assertEqual({'instance': todo1.id}, notif.content_data)
        self.assertIsInstance(notif.content, TodoReminderContent)

        self.assertTrue(self.refresh(todo1).reminded)
        self.assertFalse(self.refresh(todo4).reminded)

        # message = self.get_alone_element(mail.outbox)
        # self.assertEqual([user.email], message.to)
        #
        # software = 'My CRM'
        # self.assertEqual(
        #     _('Reminder concerning a {software} todo related to {entity}').format(
        #         software=software, entity=self.entity,
        #     ),
        #     message.subject,
        # )
        # self.assertIn(todo1.title, message.body)
        # self.assertIn(software,    message.body)

        self.assertFalse(JobResult.objects.filter(job=job))

        response = self.assertGET200(job.get_absolute_url())
        self.get_brick_node(self.get_html_tree(response.content), brick=JobErrorsBrick)

    def test_reminder02(self):
        "Minimum hour (SettingValue) is in the future."
        user = self.user
        now_value = now()

        next_hour = localtime(now_value).hour + 1
        if next_hour > 23:
            raise SkipTest('It is too late.')

        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        sv.value = next_hour
        sv.save()

        # reminder_ids = [*DateReminder.objects.values_list('id', flat=True)]
        notif_qs = Notification.objects.filter(channel__uuid=UUID_CHANNEL_REMINDERS, user=user)
        self.assertFalse(notif_qs.all())

        ToDo.objects.create(
            real_entity=self.entity, user=user, title='Todo #1', deadline=now_value,
        )

        job = self.get_reminder_job()
        wakeup = job.type.next_wakeup(job, now_value)
        self.assertIsInstance(wakeup, datetime)
        self.assertDatetimesAlmostEqual(
            localtime(now()).replace(hour=next_hour), wakeup,
        )

        self.execute_reminder_job(job)
        # self.assertFalse(DateReminder.objects.exclude(id__in=reminder_ids))
        self.assertFalse(notif_qs.all())

    # def test_reminder03(self):
    #     "Mails error."
    #     now_value = now()
    #
    #     sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
    #     sv.value = max(localtime(now_value).hour - 1, 0)
    #     sv.save()
    #
    #     reminder_ids = [*DateReminder.objects.values_list('id', flat=True)]
    #
    #     def create_todo(title):
    #         ToDo.objects.create(
    #             title=title, deadline=now_value,
    #             real_entity=self.entity, user=self.user,
    #         )
    #
    #     create_todo('Todo#1')
    #
    #     send_messages_called = False
    #     err_msg = 'Sent error'
    #
    #     def send_messages(this, messages):
    #         nonlocal send_messages_called
    #         send_messages_called = True
    #         raise Exception(err_msg)
    #
    #     EmailBackend.send_messages = send_messages
    #
    #     job = self.execute_reminder_job()
    #
    #     self.assertTrue(send_messages_called)
    #     self.assertEqual(1, DateReminder.objects.exclude(id__in=reminder_ids).count())
    #
    #     jresult = self.get_alone_element(JobResult.objects.filter(job=job))
    #     self.assertListEqual(
    #         [
    #             _(
    #                 'An error occurred while sending emails related to «{model}»'
    #             ).format(model=ToDo._meta.verbose_name),
    #             _('Original error: {}').format(err_msg),
    #         ],
    #         jresult.messages,
    #     )
    #
    #     EmailBackend.send_messages = self.original_send_messages
    #
    #     create_todo('Todo#2')
    #     job = self.execute_reminder_job()
    #     self.assertEqual(1, len(mail.outbox))
    #     self.assertEqual(2, DateReminder.objects.exclude(id__in=reminder_ids).count())
    #     self.assertFalse(JobResult.objects.filter(job=job))

    # def test_reminder04(self):
    def test_reminder03(self):
        "Teams."
        user = self.user
        now_value = now()

        teammate = self.create_user(0)
        team = self.create_team('Team #1', teammate, user)

        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        sv.value = max(localtime(now_value).hour - 1, 0)
        sv.save()

        ToDo.objects.create(
            title='Todo#1', deadline=now_value, real_entity=self.entity, user=team,
        )

        self.execute_reminder_job()
        # self.assertCountEqual(
        #     [(teammate.email,), (user.email,)],
        #     [tuple(m.to) for m in mail.outbox],
        # )

        uid = UUID_CHANNEL_REMINDERS
        self.get_object_or_fail(Notification, channel__uuid=uid, user=user)
        self.get_object_or_fail(Notification, channel__uuid=uid, user=teammate)
        self.assertFalse(Notification.objects.filter(channel__uuid=uid, user=team).exists())

    # def test_reminder05(self):
    def test_reminder04(self):
        "Dynamic user."
        other_user = self.create_user()

        entity = self.entity
        entity.user = other_user
        entity.save()

        now_value = now()

        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        sv.value = localtime(now_value).hour
        sv.save()

        notif_qs = Notification.objects.filter(
            channel__uuid=UUID_CHANNEL_REMINDERS, user=other_user,
        )
        self.assertFalse(notif_qs.all())

        ToDo.objects.create(real_entity=entity, title='Todo#1', deadline=now_value)

        self.execute_reminder_job(self.get_reminder_job())
        # self.assertEqual(1, DateReminder.objects.count())
        self.get_alone_element(notif_qs.all())

        # message = self.get_alone_element(mail.outbox)
        # self.assertListEqual([other_user.email], message.to)

    def test_next_wakeup01(self):
        "Next wake is one day later + minimum hour."
        now_value = now()

        next_hour = localtime(now_value).hour + 1
        if next_hour > 23:
            raise SkipTest('It is too late.')

        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        sv.value = next_hour
        sv.save()

        def create_todo(title, deadline, **kwargs):
            ToDo.objects.create(
                real_entity=self.entity, user=self.user,
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
        now_value = now()

        previous_hour = localtime(now_value).hour - 1
        if previous_hour < 0:
            raise SkipTest('It is too early.')

        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        sv.value = previous_hour
        sv.save()

        ToDo.objects.create(
            real_entity=self.entity, user=self.user,
            title='Todo#1',
            deadline=now_value + timedelta(days=2),
        )

        job = self.get_reminder_job()
        self.assertEqual(now_value + timedelta(days=1), job.type.next_wakeup(job, now_value))

    @override_settings(DEFAULT_TIME_ALERT_REMIND=30)
    def test_next_wakeup03(self):
        "ToDos + Alerts => minimum wake up."
        now_value = now()

        previous_hour = localtime(now_value).hour - 1
        if previous_hour < 0:
            raise SkipTest('It is too early.')

        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        sv.value = previous_hour
        sv.save()

        ToDo.objects.create(
            real_entity=self.entity, user=self.user, title='Todo#1',
            deadline=now_value + timedelta(days=2),
        )
        alert = Alert.objects.create(
            real_entity=self.entity, user=self.user, title='Alert#1',
            trigger_date=now_value + timedelta(days=3),
        )

        job = self.get_reminder_job()
        self.assertEqual(now_value + timedelta(days=1), job.type.next_wakeup(job, now_value))

        alert.trigger_date = now_value + timedelta(minutes=50)
        alert.save()

        self.assertEqual(now_value + timedelta(minutes=20), job.type.next_wakeup(job, now_value))

    @staticmethod
    def _get_hlines():
        return [*HistoryLine.objects.order_by('id')]

    def test_history01(self):
        "Creation."
        user = self.user
        akane = FakeContact.objects.create(user=user, first_name='Akane', last_name='Tendo')
        old_count = HistoryLine.objects.count()

        self._create_todo(entity=akane)
        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(akane.id,          hline.entity.id)
        self.assertEqual(akane.entity_type, hline.entity_ctype)
        self.assertEqual(user,              hline.entity_owner)
        self.assertEqual(TYPE_AUX_CREATION, hline.type)

    def test_history02(self):
        "Edition."
        user = self.user
        akane = FakeContact.objects.create(user=user, first_name='Akane', last_name='Tendo')
        todo = ToDo.objects.create(user=user, real_entity=akane, title='Todo#1')
        old_count = HistoryLine.objects.count()

        todo = self.refresh(todo)  # reset cache
        todo.description = description = 'Conquer the world'
        todo.save()

        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(akane.id,         hline.entity.id)
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

    def test_history03(self):
        "Deletion."
        user = self.user
        akane = FakeContact.objects.create(user=user, first_name='Akane', last_name='Tendo')
        todo = ToDo.objects.create(user=user, real_entity=akane, title='Todo#1')
        old_count = HistoryLine.objects.count()

        todo.delete()
        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(akane.id,          hline.entity.id)
        self.assertEqual(TYPE_AUX_DELETION, hline.type)

    def test_manager_filter_by_user(self):
        user = self.user

        other_user = self.create_user(0)
        teammate1  = self.create_user(1)
        teammate2  = self.create_user(2)

        team1 = self.create_team('Team #1', teammate1, user)
        team2 = self.create_team('Team #2', other_user, teammate2)

        create_todo = partial(ToDo.objects.create, real_entity=self.entity, user=user)
        todo1 = create_todo(title='Todo#1')
        create_todo(title='Todo#2', user=other_user)  # No (other user)
        todo3 = create_todo(title='Todo#3', user=team1)
        create_todo(title='Todo#4', user=team2)  # No (other team)

        todos = ToDo.objects.filter_by_user(user)
        self.assertIsInstance(todos, QuerySet)
        self.assertEqual(ToDo, todos.model)

        self.assertCountEqual([todo1, todo3], todos)

    def test_brick_hide_validated_todos(self):
        user = self.user

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
