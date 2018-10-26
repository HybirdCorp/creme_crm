# -*- coding: utf-8 -*-

try:
    from datetime import timedelta, datetime
    from functools import partial

    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.contrib.contenttypes.models import ContentType
    from django.core import mail
    from django.core.mail.backends.locmem import EmailBackend
    from django.db.models.query import QuerySet
    from django.test.utils import override_settings
    from django.urls import reverse
    from django.utils.timezone import now, localtime
    from django.utils.translation import ugettext as _

    from creme.creme_core.bricks import JobErrorsBrick
    from creme.creme_core.core.function_field import function_field_registry
    from creme.creme_core.core.job import JobManagerQueue  # Should be a test queue
    from creme.creme_core.models import (CremeEntity, DateReminder,
            SettingValue, HistoryLine, JobResult)
    from creme.creme_core.models.history import (TYPE_AUX_CREATION,
            TYPE_AUX_EDITION, TYPE_AUX_DELETION)
    from creme.creme_core.tests.fake_models import FakeContact, FakeOrganisation, FakeMailingList
    from creme.creme_core.tests.views.base import BrickTestCaseMixin

    from ..bricks import TodosBrick
    from ..constants import MIN_HOUR_4_TODO_REMINDER
    from ..models import ToDo, Alert
    from .base import AssistantsTestCase
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class TodoTestCase(AssistantsTestCase, BrickTestCaseMixin):
    @classmethod
    def setUpClass(cls):
        # super(TodoTestCase, cls).setUpClass()
        super().setUpClass()
        cls.original_send_messages = EmailBackend.send_messages

    def tearDown(self):
        # super(TodoTestCase, self).tearDown()
        super().tearDown()
        EmailBackend.send_messages = self.original_send_messages

    def _build_add_url(self, entity):
        return reverse('assistants__create_todo', args=(entity.id,))

    def _create_todo(self, title='TITLE', description='DESCRIPTION', entity=None, user=None):
        entity = entity or self.entity
        user   = user or self.user

        response = self.client.post(self._build_add_url(entity),
                                    data={'user':        user.pk,
                                          'title':       title,
                                          'description': description,
                                         },
                                   )
        self.assertNoFormError(response)

        return self.get_object_or_fail(ToDo, title=title, description=description)

    def _create_several_todos(self):
        self._create_todo('Todo01', 'Description01')

        entity02 = FakeContact.objects.create(user=self.user, first_name='Akane', last_name='Tendo')
        self._create_todo('Todo02', 'Description02', entity=entity02)

        user02 = get_user_model().objects.create_user(username='ryoga',
                                                      first_name='Ryoga',
                                                      last_name='Hibiki',
                                                      email='user@creme.org',
                                                     )
        self._create_todo('Todo03', 'Description03', user=user02)

    def test_populate(self):
        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        self.assertEqual('assistants', sv.key.app_label)
        self.assertEqual(9, sv.value)

    def test_create01(self):
        self.assertFalse(ToDo.objects.exists())

        queue = JobManagerQueue.get_main_queue()
        queue.clear()

        entity = self.entity
        context = self.assertGET200(self._build_add_url(entity)).context
        # self.assertEqual(_('New Todo for «%s»') % entity, context.get('title'))
        self.assertEqual(_('New todo for «{}»').format(entity), context.get('title'))
        self.assertEqual(_('Save the todo'),                    context.get('submit_label'))

        with self.assertNoException():
            hours = context['form'].fields['deadline_hour'].choices

        self.assertIn((0, '0h'), hours)
        self.assertIn((23, '23h'), hours)
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
        "Deadline"
        queue = JobManagerQueue.get_main_queue()
        queue.clear()

        url = self._build_add_url(self.entity)
        title = 'my Todo'
        data = {'user':        self.user.pk,
                'title':       title,
                'description': '',
                'deadline':    '2013-6-7',
               }
        response = self.assertPOST200(url, data=data)
        self.assertFormError(response, 'form', 'deadline_hour',
                             _('The hour is required if you set a date.')
                            )

        self.assertNoFormError(self.client.post(url, data=dict(data, deadline_hour=9)))

        todo = self.get_object_or_fail(ToDo, title=title)
        self.assertEqual(self.create_datetime(year=2013, month=6, day=7, hour=9),
                         todo.deadline
                        )
        self.assertTrue(queue.refreshed_jobs)

    def test_edit01(self):
        title       = 'Title'
        description = 'Description'
        todo = self._create_todo(title, description)

        url = todo.get_edit_absolute_url()
        response = self.assertGET200(url)
        # self.assertTemplateUsed(response,'creme_core/generics/blockform/edit_popup.html')
        self.assertTemplateUsed(response,'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        # self.assertEqual(_('Todo for «%s»') % self.entity, context.get('title'))
        self.assertEqual(_('Todo for «{}»').format(self.entity), context.get('title'))
        self.assertEqual(_('Save the modifications'),            context.get('submit_label'))

        # ---
        title       += '_edited'
        description += '_edited'
        response = self.client.post(url, data={'user':        self.user.pk,
                                               'title':       title,
                                               'description': description,
                                              }
                                   )
        self.assertNoFormError(response)

        todo = self.refresh(todo)
        self.assertEqual(title,       todo.title)
        self.assertEqual(description, todo.description)

    def test_edit02(self):
        "Entity is deleted"
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
        self.assertPOST(302, reverse('creme_core__delete_related_to_entity', args=(ct.id,)), data={'id': todo.id})
        self.assertFalse(ToDo.objects.all())

    def test_validate(self):
        todo = self._create_todo()
        self.assertFalse(todo.is_ok)

        response = self.assertPOST200(reverse('assistants__validate_todo', args=(todo.id,)), follow=True)
        self.assertRedirects(response, self.entity.get_absolute_url())
        self.assertIs(True, self.refresh(todo).is_ok)

    def test_brick_reload01(self):
        "Detailview"
        for i in range(1, 4):
            self._create_todo('Todo{}'.format(i), 'Description {}'.format(i))

        # todos = ToDo.get_todos(self.entity)
        todos = ToDo.objects.filter(entity=self.entity.id)
        self.assertEqual(3, len(todos))
        self.assertEqual(set(ToDo.objects.values_list('id', flat=True)),
                         {t.id for t in todos}
                        )

        self.assertGreaterEqual(TodosBrick.page_size, 2)

        response = self.assertGET200(reverse('creme_core__reload_detailview_bricks', args=(self.entity.id,)),
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
        self.assertEqual(size, len(set(todos) & set(page.object_list)))

    def test_brick_reload02(self):
        "Home"
        self._create_several_todos()
        self.assertEqual(3, ToDo.objects.count())

        # todos = ToDo.get_todos_for_home(self.user)
        todos = ToDo.objects.filter_by_user(self.user)
        self.assertEqual(2, len(todos))

        response = self.assertGET200(reverse('creme_core__reload_home_bricks'), data={'brick_id': TodosBrick.id_})
        self.assertEqual('application/json', response['Content-Type'])

        content = response.json()
        self.assertEqual(1, len(content))
        self.assertEqual(2, len(content[0]))
        self.assertEqual(TodosBrick.id_, content[0][0])

        with self.assertNoException():
            page = response.context['page']

        self.assertEqual(2, len(page.object_list))
        self.assertEqual(set(todos), set(page.object_list))

    def _oldify_todo(self, todo):
        cdate = todo.creation_date
        todo.creation_date = cdate - timedelta(days=1)
        todo.save()

    def test_function_field01(self):
        # funf = CremeEntity.function_fields.get('assistants-get_todos')
        funf = function_field_registry.get(CremeEntity, 'assistants-get_todos')
        self.assertIsNotNone(funf)
        self.assertEqual('<ul></ul>', funf(self.entity, self.user).for_html())

    def test_function_field02(self):
        # funf = CremeEntity.function_fields.get('assistants-get_todos')
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
        # self.assertEqual('<ul><li>Todo04</li><li>Todo03</li><li>Todo02</li></ul>', funf(self.entity))

    def test_function_field03(self):
        "Prefetch with 'populate_entities()'"
        user = self.user
        self._oldify_todo(self._create_todo('Todo01', 'Description01'))
        self._create_todo('Todo02', 'Description02')

        todo3 = self._create_todo('Todo03', 'Description03')
        todo3.is_ok = True
        todo3.save()

        entity02 = CremeEntity.objects.create(user=user)
        self._create_todo('Todo04', 'Description04', entity=entity02)

        # funf = CremeEntity.function_fields.get('assistants-get_todos')
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
        self.assertEqual(_('Reminder concerning a Creme CRM todo related to {entity}').format(entity=self.entity),
                         message.subject
                        )
        self.assertIn(todo1.title, message.body)

        self.assertFalse(JobResult.objects.filter(job=job))

        response = self.assertGET200(job.get_absolute_url())
        self.get_brick_node(self.get_html_tree(response.content), JobErrorsBrick.id_)

    def test_reminder02(self):
        "Minimum hour (SettingValue) is in the future"
        now_value = now()

        next_hour = localtime(now_value).hour + 1
        if next_hour > 23:
            print('Skip the test TodoTestCase.test_reminder02 because it is too late.')
            return

        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        sv.value = next_hour
        sv.save()

        reminder_ids = list(DateReminder.objects.values_list('id', flat=True))

        ToDo.objects.create(creme_entity=self.entity, user=self.user,
                            title='Todo#1', deadline=now_value,
                           )

        job = self.get_reminder_job()
        wakeup = job.type.next_wakeup(job, now_value)
        self.assertIsInstance(wakeup, datetime)
        self.assertDatetimesAlmostEqual(localtime(now()).replace(hour=next_hour),
                                        wakeup
                                       )

        self.execute_reminder_job(job)
        self.assertFalse(DateReminder.objects.exclude(id__in=reminder_ids))

    def test_reminder03(self):
        "Mails error"
        now_value = now()

        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        sv.value = max(localtime(now_value).hour - 1, 0)
        sv.save()

        reminder_ids = list(DateReminder.objects.values_list('id', flat=True))

        def create_todo(title):
            ToDo.objects.create(title=title, deadline=now_value,
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
        self.assertEqual([_('An error occurred while sending emails related to «{model}»').format(
                                    model=ToDo._meta.verbose_name,
                                ),
                          _('Original error: {}').format(err_msg),
                         ],
                         jresult.messages
                        )

        EmailBackend.send_messages = self.original_send_messages

        create_todo('Todo#2')
        job = self.execute_reminder_job()
        self.assertEqual(1, len(mail.outbox))
        self.assertEqual(2, DateReminder.objects.exclude(id__in=reminder_ids).count())
        self.assertFalse(JobResult.objects.filter(job=job))

    def test_reminder04(self):
        "Teams"
        user = self.user
        now_value = now()

        create_user = get_user_model().objects.create
        teammate = create_user(username='luffy',
                               email='luffy@sunny.org', role=self.role,
                               first_name='Luffy', last_name='Monkey D.',
                              )
        team = create_user(username='Team #1', is_team=True)
        team.teammates = [teammate, user]

        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        sv.value = max(localtime(now_value).hour - 1, 0)
        sv.save()

        ToDo.objects.create(title='Todo#1', deadline=now_value, creme_entity=self.entity, user=team)

        self.execute_reminder_job()

        messages = mail.outbox
        self.assertEqual(2, len(messages))
        self.assertEqual({(teammate.email,), (user.email,)},
                         {tuple(m.to) for m in messages}
                        )

    def test_next_wakeup01(self):
        "Next wake is one day later + minimum hour"
        now_value = now()

        next_hour = localtime(now_value).hour + 1
        if next_hour > 23:
            print('Skip the test TodoTestCase.test_next_wakeup01 because it is too late.')
            return

        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        sv.value = next_hour
        sv.save()

        def create_todo(title, deadline, **kwargs):
            ToDo.objects.create(creme_entity=self.entity, user=self.user,
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

        self.assertEqual((localtime(now_value + timedelta(days=1))).replace(hour=next_hour),
                         job.type.next_wakeup(job, now_value)
                        )

    def test_next_wakeup02(self):
        "Next wake is one day later (but minimum hour has passed)"
        now_value = now()

        previous_hour = localtime(now_value).hour - 1
        if previous_hour < 0:
            print('Skip the test TodoTestCase.test_reminder02 because it is too early.')
            return

        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        sv.value = previous_hour
        sv.save()

        ToDo.objects.create(creme_entity=self.entity, user=self.user,
                            title='Todo#1',
                            deadline=now_value + timedelta(days=2),
                           )

        job = self.get_reminder_job()
        self.assertEqual(now_value + timedelta(days=1), job.type.next_wakeup(job, now_value))

    @override_settings(DEFAULT_TIME_ALERT_REMIND=30)
    def test_next_wakeup03(self):
        "ToDos + Alerts => minimum wake up"
        now_value = now()

        # TODO: factorise
        previous_hour = localtime(now_value).hour - 1
        if previous_hour < 0:
            print('Skip the test TodoTestCase.test_reminder02 because it is too early.')
            return

        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        sv.value = previous_hour
        sv.save()

        ToDo.objects.create(creme_entity=self.entity, user=self.user, title='Todo#1',
                            deadline=now_value + timedelta(days=2),
                           )
        alert = Alert.objects.create(creme_entity=self.entity, user=self.user, title='Alert#1',
                                     trigger_date=now_value + timedelta(days=3),
                                    )

        job = self.get_reminder_job()
        self.assertEqual(now_value + timedelta(days=1), job.type.next_wakeup(job, now_value))

        alert.trigger_date = now_value + timedelta(minutes=50)
        alert.save()

        self.assertEqual(now_value + timedelta(minutes=20), job.type.next_wakeup(job, now_value))

    def _get_hlines(self):
        return list(HistoryLine.objects.order_by('id'))

    def test_history01(self):
        "Creation"
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
        "Edition"
        user = self.user
        akane = FakeContact.objects.create(user=user, first_name='Akane', last_name='Tendo')
        todo = ToDo.objects.create(user=user, creme_entity=akane, title='Todo#1')
        old_count = HistoryLine.objects.count()

        todo.description = 'Conquier the world'
        todo.save()

        hlines = self._get_hlines()
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(akane.id,         hline.entity.id)
        self.assertEqual(TYPE_AUX_EDITION, hline.type)

        vmodifs = hline.get_verbose_modifications(user)
        self.assertEqual(2, len(vmodifs))

        self.assertEqual(_('Edit <{type}>: “{value}”').format(
                                type=_('Todo'),
                                value=todo,
                            ),
                         vmodifs[0]
                        )
        self.assertEqual(_('Set field “{field}”').format(field=_('Description')),
                         vmodifs[1]
                        )

    def test_history03(self):
        "Deletion"
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

        self.assertEqual(_('Delete <{type}>: “{value}”').format(
                                type=_('Todo'),
                                value=todo,
                            ),
                         vmodifs[0]
                        )

    def test_get_todos(self):
        user = self.user

        entity2 = FakeOrganisation.objects.create(user=user, name='Thousand sunny')

        create_todo = partial(ToDo.objects.create, creme_entity=self.entity, user=user)
        todo1 = create_todo(title='Todo#1')
        create_todo(title='Todo#2', creme_entity=entity2)  # No (other entity)
        todo3 = create_todo(title='Todo#3')

        todos = ToDo.get_todos(entity=self.entity)
        self.assertIsInstance(todos, QuerySet)
        self.assertEqual(ToDo, todos.model)

        self.assertEqual({todo1, todo3}, set(todos))
        self.assertEqual(2, len(todos))

    def test_get_todos_for_home(self):
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

        create_todo = partial(ToDo.objects.create, creme_entity=self.entity, user=user)
        todo1 = create_todo(title='Todo#1')
        create_todo(title='Todo#2', user=self.other_user)  # No (other user)
        todo3 = create_todo(title='Todo#3', user=team1)
        create_todo(title='Todo#4', user=team2)  # No (other team)

        # entity2 = FakeOrganisation.objects.create(user=user, name='Thousand sunny', is_deleted=True)
        # create_todo(title='Todo#5', creme_entity=entity2)  # No (deleted entity)

        todos = ToDo.get_todos_for_home(user=user)
        self.assertIsInstance(todos, QuerySet)
        self.assertEqual(ToDo, todos.model)

        self.assertEqual({todo1, todo3}, set(todos))
        self.assertEqual(2, len(todos))

    def test_get_todos_for_ctypes(self):
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

        create_todo = partial(ToDo.objects.create, creme_entity=self.entity, user=user)
        todo1 = create_todo(title='Todo#1')
        create_todo(title='Todo#2', user=self.other_user)  # No (other user)
        todo3 = create_todo(title='Todo#3', user=team1)
        create_todo(title='Todo#4', user=team2)  # No (other team)
        todo5 = create_todo(title='Todo#5', creme_entity=entity2)
        create_todo(title='Todo#6', creme_entity=entity3)  # No (bad ctype)

        todos = ToDo.get_todos_for_ctypes(user=user, ct_ids=[self.entity.entity_type_id, entity2.entity_type_id])
        self.assertIsInstance(todos, QuerySet)
        self.assertEqual(ToDo, todos.model)

        self.assertEqual({todo1, todo3, todo5}, set(todos))
        self.assertEqual(3, len(todos))

    def test_manager_filter_by_user(self):
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

        create_todo = partial(ToDo.objects.create, creme_entity=self.entity, user=user)
        todo1 = create_todo(title='Todo#1')
        create_todo(title='Todo#2', user=self.other_user)  # No (other user)
        todo3 = create_todo(title='Todo#3', user=team1)
        create_todo(title='Todo#4', user=team2)  # No (other team)

        todos = ToDo.objects.filter_by_user(user)
        self.assertIsInstance(todos, QuerySet)
        self.assertEqual(ToDo, todos.model)

        self.assertEqual({todo1, todo3}, set(todos))
        self.assertEqual(2, len(todos))
