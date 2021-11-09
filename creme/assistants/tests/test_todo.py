# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from functools import partial
from unittest import SkipTest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.core.mail.backends.locmem import EmailBackend
from django.db.models.query import Q, QuerySet
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.timezone import localtime, now
from django.utils.translation import gettext as _

from creme.creme_core.bricks import JobErrorsBrick
from creme.creme_core.core.entity_cell import EntityCellFunctionField
from creme.creme_core.core.function_field import function_field_registry
# Should be a test queue
# from creme.creme_core.core.job import JobSchedulerQueue
from creme.creme_core.core.job import get_queue
from creme.creme_core.forms.listview import TextLVSWidget
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    BrickState,
    CremeEntity,
    DateReminder,
    FakeContact,
    FakeOrganisation,
    HistoryLine,
    JobResult,
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
from .base import AssistantsTestCase


class TodoTestCase(BrickTestCaseMixin, AssistantsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.original_send_messages = EmailBackend.send_messages

    def tearDown(self):
        super().tearDown()
        EmailBackend.send_messages = self.original_send_messages

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

        entity02 = FakeContact.objects.create(
            user=self.user, first_name='Akane', last_name='Tendo',
        )
        self._create_todo('Todo02', 'Description02', entity=entity02)

        user02 = get_user_model().objects.create_user(
            username='ryoga', first_name='Ryoga', last_name='Hibiki', email='user@creme.org',
        )
        self._create_todo('Todo03', 'Description03', user=user02)

    def test_populate(self):
        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        self.assertEqual('assistants', sv.key.app_label)
        self.assertEqual(9, sv.value)

    def test_create01(self):
        self.assertFalse(ToDo.objects.exists())

        # queue = JobSchedulerQueue.get_main_queue()
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
            hours = context['form'].fields['deadline_hour'].choices

        self.assertInChoices(value=0, label='0h', choices=hours)
        self.assertInChoices(value=23, label='23h', choices=hours)
        self.assertEqual(24, len(hours))

        # ---
        title = 'Title'
        todo = self._create_todo(title, 'Description')
        self.assertEqual(1, ToDo.objects.count())
        self.assertEqual(entity.id,             todo.entity_id)
        self.assertEqual(entity.entity_type_id, todo.entity_content_type_id)
        self.assertDatetimesAlmostEqual(now(), todo.creation_date)
        self.assertIsNone(todo.deadline)
        self.assertIs(todo.reminded, False)

        self.assertFalse(queue.refreshed_jobs)  # Because there is no deadline

        self.assertEqual(title, str(todo))

    def test_create02(self):
        "Deadline."
        # queue = JobSchedulerQueue.get_main_queue()
        queue = get_queue()
        queue.clear()

        url = self._build_add_url(self.entity)
        title = 'my Todo'
        data = {
            'user':        self.user.pk,
            'title':       title,
            'description': '',
            'deadline':    '2013-6-7',
        }
        response = self.assertPOST200(url, data=data)
        self.assertFormError(
            response, 'form', 'deadline_hour',
            _('The hour is required if you set a date.'),
        )

        self.assertNoFormError(self.client.post(url, data={**data, 'deadline_hour': 9}))

        todo = self.get_object_or_fail(ToDo, title=title)
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
            entity2 = todo.creme_entity

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
                user=user, title=title, creme_entity=entity, is_ok=is_ok,
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
            self.get_html_tree(response1.content),
            TodosBrick.id_,
        )

        self.assertTrue(todo_found(detail_brick_node,  todo1))
        self.assertTrue(todo_found(detail_brick_node,  todo2))
        self.assertFalse(todo_found(detail_brick_node, todo3))

        # Home + do no hide ---
        BrickHomeLocation.objects.get_or_create(
            brick_id=TodosBrick.id_, defaults={'order': 50},
        )

        response2 = self.assertGET200(reverse('creme_core__home'))
        home_brick_node = self.get_brick_node(
            self.get_html_tree(response2.content),
            TodosBrick.id_,
        )

        self.assertTrue(todo_found(home_brick_node, todo1))
        self.assertTrue(todo_found(home_brick_node, todo2))
        self.assertTrue(todo_found(home_brick_node, todo3))
        self.assertFalse(todo_found(home_brick_node, todo4))
        self.assertInstanceLink(home_brick_node, entity1)
        self.assertInstanceLink(home_brick_node, entity2)

        # Detail + hide validated ---
        state = BrickState.objects.get_for_brick_id(user=user, brick_id=TodosBrick.id_)
        state.set_extra_data(key=BRICK_STATE_HIDE_VALIDATED_TODOS, value=True)
        state.save()

        response3 = self.assertGET200(self.entity.get_absolute_url())
        detail_brick_node_hidden = self.get_brick_node(
            self.get_html_tree(response3.content),
            TodosBrick.id_,
        )

        self.assertTrue(todo_found(detail_brick_node_hidden, todo1))
        self.assertFalse(todo_found(detail_brick_node_hidden, todo2))
        self.assertFalse(todo_found(detail_brick_node_hidden, todo3))

        # Home + hide validated ---
        response4 = self.assertGET200(reverse('creme_core__home'))
        home_brick_node_hidden = self.get_brick_node(
            self.get_html_tree(response4.content),
            TodosBrick.id_,
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
        self.assertSetEqual(
            {*ToDo.objects.values_list('id', flat=True)},
            {t.id for t in todos},
        )

        self.assertGreaterEqual(TodosBrick.page_size, 2)

        response = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(self.entity.id,)),
            data={'brick_id': TodosBrick.id_},
        )
        self.assertEqual('application/json', response['Content-Type'])

        content = response.json()
        self.assertEqual(1, len(content))
        self.assertEqual(2, len(content[0]))
        self.assertEqual(TodosBrick.id_, content[0][0])

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
            data={'brick_id': TodosBrick.id_},
        )
        self.assertEqual('application/json', response['Content-Type'])

        content = response.json()
        self.assertEqual(1, len(content))
        self.assertEqual(2, len(content[0]))
        self.assertEqual(TodosBrick.id_, content[0][0])

        with self.assertNoException():
            page = response.context['page']

        self.assertEqual(2, len(page.object_list))
        self.assertSetEqual({*todos}, {*page.object_list})

    @staticmethod
    def _oldify_todo(todo):
        cdate = todo.creation_date
        todo.creation_date = cdate - timedelta(days=1)
        todo.save()

    def test_function_field01(self):
        funf = function_field_registry.get(CremeEntity, 'assistants-get_todos')
        self.assertIsInstance(funf, TodosField)
        self.assertEqual('<ul></ul>', funf(self.entity, self.user).for_html())

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

        self.assertEqual('<ul><li>Todo02</li><li>Todo01</li></ul>', result.for_html())

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
        self._create_todo('Todo04', 'Description04', entity=entity02)

        funf = function_field_registry.get(CremeEntity, 'assistants-get_todos')

        with self.assertNumQueries(1):
            funf.populate_entities([self.entity, entity02], user)

        with self.assertNumQueries(0):
            result1 = funf(self.entity, user)
            result2 = funf(entity02, user)

        self.assertEqual('<ul><li>Todo02</li><li>Todo01</li></ul>', result1.for_html())
        self.assertEqual('<ul><li>Todo04</li></ul>',                result2.for_html())

    def test_merge(self):
        def creator(contact01, contact02):
            self._create_todo('Todo01', 'Fight against him', contact01)
            self._create_todo('Todo02', 'Train with him',    contact02)
            self.assertEqual(2, ToDo.objects.count())

        def assertor(contact01):
            todos = ToDo.objects.all()
            self.assertEqual(2, len(todos))

            for todo in todos:
                self.assertEqual(contact01, todo.creme_entity)

        self.aux_test_merge(creator, assertor)

    def test_reminder01(self):
        user = self.user
        now_value = now()

        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        sv.value = localtime(now_value).hour
        sv.save()

        DateReminder.objects.all().delete()

        job = self.get_reminder_job()
        self.assertIsNone(job.type.next_wakeup(job, now_value))

        create_todo = partial(ToDo.objects.create, creme_entity=self.entity, user=user)
        todo1 = create_todo(title='Todo#1', deadline=now_value)
        create_todo(title='Todo#2', deadline=now_value + timedelta(days=2))
        create_todo(title='Todo#3')
        todo4 = create_todo(title='Todo#4', deadline=now_value, is_ok=True)

        self.assertLess(job.type.next_wakeup(job, now_value), now())

        self.execute_reminder_job(job)
        self.assertIsNone(job.user)

        reminders = DateReminder.objects.all()
        self.assertEqual(1, len(reminders))

        reminder = reminders[0]
        self.assertEqual(todo1, reminder.object_of_reminder)
        self.assertEqual(1,     reminder.ident)
        self.assertDatetimesAlmostEqual(now_value, reminder.date_of_remind, seconds=60)
        self.assertTrue(self.refresh(todo1).reminded)
        self.assertFalse(self.refresh(todo4).reminded)

        messages = mail.outbox
        self.assertEqual(1, len(messages))

        message = messages[0]
        self.assertEqual([user.email], message.to)
        self.assertEqual(
            _('Reminder concerning a Creme CRM todo related to {entity}').format(
                entity=self.entity,
            ),
            message.subject,
        )
        self.assertIn(todo1.title, message.body)

        self.assertFalse(JobResult.objects.filter(job=job))

        response = self.assertGET200(job.get_absolute_url())
        self.get_brick_node(self.get_html_tree(response.content), JobErrorsBrick.id_)

    def test_reminder02(self):
        "Minimum hour (SettingValue) is in the future."
        now_value = now()

        next_hour = localtime(now_value).hour + 1
        if next_hour > 23:
            raise SkipTest('It is too late.')

        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        sv.value = next_hour
        sv.save()

        reminder_ids = [*DateReminder.objects.values_list('id', flat=True)]

        ToDo.objects.create(
            creme_entity=self.entity, user=self.user,
            title='Todo#1', deadline=now_value,
        )

        job = self.get_reminder_job()
        wakeup = job.type.next_wakeup(job, now_value)
        self.assertIsInstance(wakeup, datetime)
        self.assertDatetimesAlmostEqual(
            localtime(now()).replace(hour=next_hour), wakeup,
        )

        self.execute_reminder_job(job)
        self.assertFalse(DateReminder.objects.exclude(id__in=reminder_ids))

    def test_reminder03(self):
        "Mails error."
        now_value = now()

        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        sv.value = max(localtime(now_value).hour - 1, 0)
        sv.save()

        reminder_ids = [*DateReminder.objects.values_list('id', flat=True)]

        def create_todo(title):
            ToDo.objects.create(
                title=title, deadline=now_value,
                creme_entity=self.entity, user=self.user,
            )

        create_todo('Todo#1')

        send_messages_called = False
        err_msg = 'Sent error'

        def send_messages(this, messages):
            nonlocal send_messages_called
            send_messages_called = True
            raise Exception(err_msg)

        EmailBackend.send_messages = send_messages

        job = self.execute_reminder_job()

        self.assertTrue(send_messages_called)
        self.assertEqual(1, DateReminder.objects.exclude(id__in=reminder_ids).count())

        jresults = JobResult.objects.filter(job=job)
        self.assertEqual(1, len(jresults))

        jresult = jresults[0]
        self.assertListEqual(
            [
                _(
                    'An error occurred while sending emails related to «{model}»'
                ).format(model=ToDo._meta.verbose_name),
                _('Original error: {}').format(err_msg),
            ],
            jresult.messages,
        )

        EmailBackend.send_messages = self.original_send_messages

        create_todo('Todo#2')
        job = self.execute_reminder_job()
        self.assertEqual(1, len(mail.outbox))
        self.assertEqual(2, DateReminder.objects.exclude(id__in=reminder_ids).count())
        self.assertFalse(JobResult.objects.filter(job=job))

    def test_reminder04(self):
        "Teams."
        user = self.user
        now_value = now()

        create_user = get_user_model().objects.create
        teammate = create_user(
            username='luffy',
            email='luffy@sunny.org', role=self.role,
            first_name='Luffy', last_name='Monkey D.',
        )
        team = create_user(username='Team #1', is_team=True)
        team.teammates = [teammate, user]

        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        sv.value = max(localtime(now_value).hour - 1, 0)
        sv.save()

        ToDo.objects.create(
            title='Todo#1', deadline=now_value, creme_entity=self.entity, user=team,
        )

        self.execute_reminder_job()

        messages = mail.outbox
        self.assertEqual(2, len(messages))
        self.assertSetEqual(
            {(teammate.email,), (user.email,)}, {tuple(m.to) for m in messages}
        )

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
                creme_entity=self.entity, user=self.user,
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
            creme_entity=self.entity, user=self.user,
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
            creme_entity=self.entity, user=self.user, title='Todo#1',
            deadline=now_value + timedelta(days=2),
        )
        alert = Alert.objects.create(
            creme_entity=self.entity, user=self.user, title='Alert#1',
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
        todo = ToDo.objects.create(user=user, creme_entity=akane, title='Todo#1')
        old_count = HistoryLine.objects.count()

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

        vmodifs = hline.get_verbose_modifications(user)
        self.assertEqual(2, len(vmodifs))

        self.assertEqual(
            _('Edit <{type}>: “{value}”').format(type=_('Todo'), value=todo),
            vmodifs[0],
        )
        self.assertEqual(
            # _('Set field “{field}”').format(field=_('Description')),
            _('Set field “{field}” to “{value}”').format(
                field=_('Description'),
                value=description,
            ),
            vmodifs[1],
        )

    def test_history03(self):
        "Deletion."
        user = self.user
        akane = FakeContact.objects.create(user=user, first_name='Akane', last_name='Tendo')
        todo = ToDo.objects.create(user=user, creme_entity=akane, title='Todo#1')
        old_count = HistoryLine.objects.count()

        todo.delete()
        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(akane.id,          hline.entity.id)
        self.assertEqual(TYPE_AUX_DELETION, hline.type)

        vmodifs = hline.get_verbose_modifications(user)
        self.assertEqual(1, len(vmodifs))

        self.assertEqual(
            _('Delete <{type}>: “{value}”').format(type=_('Todo'), value=todo),
            vmodifs[0],
        )

    def test_manager_filter_by_user(self):
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

        create_todo = partial(ToDo.objects.create, creme_entity=self.entity, user=user)
        todo1 = create_todo(title='Todo#1')
        create_todo(title='Todo#2', user=self.other_user)  # No (other user)
        todo3 = create_todo(title='Todo#3', user=team1)
        create_todo(title='Todo#4', user=team2)  # No (other team)

        todos = ToDo.objects.filter_by_user(user)
        self.assertIsInstance(todos, QuerySet)
        self.assertEqual(ToDo, todos.model)

        self.assertSetEqual({todo1, todo3}, {*todos})
        self.assertEqual(2, len(todos))

    def test_brick_hide_validated_todos(self):
        user = self.user

        def get_state():
            return BrickState.objects.get_for_brick_id(user=user, brick_id=TodosBrick.id_)

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
