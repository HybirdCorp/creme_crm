# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from functools import partial

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.db.models.query_utils import Q
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

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
    FakeOrganisation,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from ..bricks import AlertsBrick
from ..constants import BRICK_STATE_HIDE_VALIDATED_ALERTS
from ..models import Alert
from .base import AssistantsTestCase


class AlertTestCase(BrickTestCaseMixin, AssistantsTestCase):
    @staticmethod
    def _build_add_url(entity):
        return reverse('assistants__create_alert', args=(entity.id,))

    def _create_alert(self,
                      title='TITLE',
                      description='DESCRIPTION',
                      trigger_date='2010-9-29',
                      entity=None,
                      ):
        entity = entity or self.entity
        response = self.client.post(
            self._build_add_url(entity),
            data={
                'user':         self.user.pk,
                'title':        title,
                'description':  description,
                'trigger_date': trigger_date,
            },
        )
        self.assertNoFormError(response)

        return self.get_object_or_fail(Alert, title=title, description=description)

    def test_create01(self):
        self.assertFalse(Alert.objects.exists())

        # queue = JobSchedulerQueue.get_main_queue()
        queue = get_queue()
        queue.clear()

        entity = self.entity
        context = self.assertGET200(self._build_add_url(entity)).context
        self.assertEqual(
            _('New alert for «{entity}»').format(entity=entity),
            context.get('title'),
        )
        self.assertEqual(_('Save the alert'), context.get('submit_label'))

        title = 'Title'
        alert = self._create_alert(title, 'Description', '2010-9-29')
        self.assertEqual(1, Alert.objects.count())

        self.assertIs(False,        alert.is_validated)
        self.assertEqual(self.user, alert.user)
        self.assertIs(False,        alert.reminded)

        self.assertEqual(entity.id,             alert.entity_id)
        self.assertEqual(entity.entity_type_id, alert.entity_content_type_id)
        self.assertEqual(
            self.create_datetime(year=2010, month=9, day=29),
            alert.trigger_date,
        )

        self.assertEqual(title, str(alert))

        jobs = queue.refreshed_jobs
        self.assertEqual(1, len(jobs))
        self.assertEqual(self.get_reminder_job(), jobs[0][0])

    def test_create02(self):
        "Errors."
        def _fail_creation(**post_data):
            response = self.assertPOST200(self._build_add_url(self.entity), data=post_data)

            with self.assertNoException():
                form = response.context['form']

            self.assertFalse(form.is_valid(), f'Creation should fail with data={post_data}')

        user_pk = self.user.pk
        _fail_creation(
            user=user_pk, title='',      description='description', trigger_date='2010-9-29',
        )
        _fail_creation(
            user=user_pk, title='title', description='description', trigger_date='',
        )

    def test_edit(self):
        title = 'Title'
        description = 'Description'
        alert = self._create_alert(title, description, '2010-9-29')

        url = alert.get_edit_absolute_url()
        context = self.assertGET200(url).context
        self.assertEqual(
            _('Alert for «{entity}»').format(entity=self.entity),
            context.get('title'),
        )

        # ---
        title += '_edited'
        description += '_edited'
        response = self.client.post(
            url,
            data={
                'user':         self.user.pk,
                'title':        title,
                'description':  description,
                'trigger_date': '2011-10-30',
                'trigger_time': '15:12:00',
            },
        )
        self.assertNoFormError(response)

        alert = self.refresh(alert)
        self.assertEqual(title,       alert.title)
        self.assertEqual(description, alert.description)

        # Don't care about seconds
        self.assertEqual(
            self.create_datetime(year=2011, month=10, day=30, hour=15, minute=12),
            alert.trigger_date,
        )

    def test_delete_related01(self):
        self._create_alert()
        self.assertEqual(1, Alert.objects.count())

        self.entity.delete()
        self.assertEqual(0, Alert.objects.count())

    def test_delete01(self):
        alert = self._create_alert()
        self.assertEqual(1, Alert.objects.count())

        ct = ContentType.objects.get_for_model(Alert)
        self.client.post(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': alert.id},
        )
        self.assertFalse(Alert.objects.all())

    def test_validate(self):
        alert = self._create_alert()
        self.assertFalse(alert.is_validated)

        url = reverse('assistants__validate_alert', args=(alert.id,))
        self.assertGET405(url)

        response = self.assertPOST200(url, follow=True)
        self.assertRedirects(response, self.entity.get_absolute_url())

        self.assertTrue(self.refresh(alert).is_validated)

    def test_function_field01(self):
        funf = function_field_registry.get(CremeEntity, 'assistants-get_alerts')
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
        self.assertQEqual(
            Q(
                assistants_alerts__title__icontains=value,
                assistants_alerts__is_validated=False,
            ),
            to_python(value=value),
        )

    def test_function_field02(self):
        funf = function_field_registry.get(CremeEntity, 'assistants-get_alerts')

        self._create_alert('Alert01', 'Description01', trigger_date='2011-10-21')
        self._create_alert('Alert02', 'Description02', trigger_date='2010-10-20')

        alert3 = self._create_alert('Alert03', 'Description03', trigger_date='2010-10-3')
        alert3.is_validated = True
        alert3.save()

        with self.assertNumQueries(1):
            result = funf(self.entity, self.user)

        self.assertEqual('<ul><li>Alert02</li><li>Alert01</li></ul>', result.for_html())

    def test_function_field03(self):
        "Prefetch with 'populate_entities()'."
        user = self.user
        self._create_alert('Alert01', 'Description01', trigger_date='2011-10-21')
        self._create_alert('Alert02', 'Description02', trigger_date='2010-10-20')

        entity02 = CremeEntity.objects.create(user=user)

        alert3 = self._create_alert(
            'Alert03', 'Description03', trigger_date='2010-10-3', entity=entity02,
        )
        alert3.is_validated = True
        alert3.save()

        self._create_alert('Alert04', 'Description04', trigger_date='2010-10-3', entity=entity02)

        funf = function_field_registry.get(CremeEntity, 'assistants-get_alerts')

        with self.assertNumQueries(1):
            funf.populate_entities([self.entity, entity02], user)

        with self.assertNumQueries(0):
            result1 = funf(self.entity, user)
            result2 = funf(entity02, user)

        self.assertEqual('<ul><li>Alert02</li><li>Alert01</li></ul>', result1.for_html())
        self.assertEqual('<ul><li>Alert04</li></ul>',                 result2.for_html())

    def test_merge(self):
        def creator(contact01, contact02):
            self._create_alert('Alert01', 'Fight against him', '2011-1-9',  contact01)
            self._create_alert('Alert02', 'Train with him',    '2011-1-10', contact02)
            self.assertEqual(2, Alert.objects.count())

        def assertor(contact01):
            alerts = Alert.objects.all()
            self.assertEqual(2, len(alerts))

            for alert in alerts:
                self.assertEqual(contact01, alert.creme_entity)

        self.aux_test_merge(creator, assertor)

    @override_settings(DEFAULT_TIME_ALERT_REMIND=60)
    def test_reminder(self):
        user = self.user
        now_value = now()

        job = self.get_reminder_job()
        self.assertIsNone(job.user)
        self.assertIsNone(job.type.next_wakeup(job, now_value))

        reminder_ids = [*DateReminder.objects.values_list('id', flat=True)]

        create_alert = partial(
            Alert.objects.create,
            creme_entity=self.entity, user=user, trigger_date=now_value,
        )
        alert1 = create_alert(title='Alert#1', trigger_date=now_value + timedelta(minutes=50))
        alert2 = create_alert(title='Alert#2', trigger_date=now_value + timedelta(minutes=70))
        create_alert(title='Alert#3', is_validated=True)

        self.assertLess(job.type.next_wakeup(job, now_value), now())

        self.execute_reminder_job(job)
        reminders = DateReminder.objects.exclude(id__in=reminder_ids)
        self.assertEqual(1, len(reminders))

        reminder = reminders[0]
        self.assertEqual(alert1, reminder.object_of_reminder)
        self.assertEqual(1,      reminder.ident)
        self.assertDatetimesAlmostEqual(now_value, reminder.date_of_remind, seconds=60)
        self.assertTrue(self.refresh(alert1).reminded)
        self.assertFalse(self.refresh(alert2).reminded)

        messages = mail.outbox
        self.assertEqual(1, len(messages))

        message = messages[0]
        self.assertEqual([user.email], message.to)
        self.assertEqual(
            _('Reminder concerning a Creme CRM alert related to {entity}').format(
                entity=self.entity,
            ),
            message.subject,
        )
        self.assertIn(alert1.title, message.body)

        # Reminders are not recreated if they already exist
        self.execute_reminder_job(job)
        self.assertFalse(DateReminder.objects.exclude(id__in=[*reminder_ids, reminder.id]))
        self.assertEqual(1, len(mail.outbox))

    @override_settings(DEFAULT_TIME_ALERT_REMIND=30)
    def test_next_wakeup(self):
        now_value = now()

        create_alert = partial(
            Alert.objects.create,
            creme_entity=self.entity, user=self.user, trigger_date=now_value,
        )
        create_alert(title='Alert#2', is_validated=True)
        create_alert(title='Alert#4', reminded=True)
        create_alert(title='Alert#6', trigger_date=now_value + timedelta(minutes=60))
        # Only this one should be used:
        create_alert(title='Alert#1', trigger_date=now_value + timedelta(minutes=50))
        create_alert(title='Alert#7', trigger_date=now_value + timedelta(minutes=70))
        create_alert(title='Alert#3', is_validated=True)
        create_alert(title='Alert#5', reminded=True)

        job = self.get_reminder_job()
        wakeup = job.type.next_wakeup(job, now_value)
        self.assertIsInstance(wakeup, datetime)
        self.assertDatetimesAlmostEqual(
            now_value + timedelta(minutes=20),
            wakeup,
        )

    def test_manager_filter_by_user(self):
        "Teams."
        user = self.user
        now_value = now()

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

        create_alert = partial(
            Alert.objects.create,
            creme_entity=self.entity, user=user, trigger_date=now_value,
        )
        alert1 = create_alert(title='Alert#1')
        create_alert(title='Alert#2', user=team2)  # No (other team)
        alert3 = create_alert(title='Alert#3', user=team1)

        alerts = Alert.objects.filter_by_user(user=user)
        self.assertSetEqual({alert1, alert3}, {*alerts})
        self.assertEqual(2, len(alerts))

    def test_brick(self):
        user = self.user
        entity1 = self.entity

        state = BrickState.objects.get_for_brick_id(user=user, brick_id=AlertsBrick.id_)
        state.set_extra_data(key=BRICK_STATE_HIDE_VALIDATED_ALERTS, value=False)
        state.save()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity2 = create_orga(name='Acme')
        entity3 = create_orga(name='Deleted', is_deleted=True)

        def create_alert(title, entity, is_validated=False):
            return Alert.objects.create(
                user=user,
                title=title,
                creme_entity=entity,
                trigger_date=now() + timedelta(days=5),
                is_validated=is_validated,
            )

        alert1 = create_alert('Recall',         entity1)
        alert2 = create_alert("It's important", entity1, is_validated=True)
        alert3 = create_alert('Other',          entity2)
        alert4 = create_alert('Ignored',        entity3)

        AlertsBrick.page_size = max(4, settings.BLOCK_SIZE)

        def alert_found(brick_node, alert):
            title = alert.title
            return any(n.text == title for n in brick_node.findall('.//td'))

        # Detail + do not hide ---
        BrickDetailviewLocation.objects.create_if_needed(
            brick=AlertsBrick,
            model=type(entity1),
            order=50,
            zone=BrickDetailviewLocation.RIGHT,
        )

        response1 = self.assertGET200(self.entity.get_absolute_url())
        detail_brick_node = self.get_brick_node(
            self.get_html_tree(response1.content),
            AlertsBrick.id_,
        )

        self.assertTrue(alert_found(detail_brick_node, alert1))
        self.assertTrue(alert_found(detail_brick_node, alert2))
        self.assertFalse(alert_found(detail_brick_node, alert3))

        # Home + do not hide ---
        BrickHomeLocation.objects.get_or_create(
            brick_id=AlertsBrick.id_, defaults={'order': 50},
        )

        response2 = self.assertGET200(reverse('creme_core__home'))
        home_brick_node = self.get_brick_node(
            self.get_html_tree(response2.content),
            AlertsBrick.id_,
        )

        self.assertTrue(alert_found(home_brick_node, alert1))
        self.assertTrue(alert_found(home_brick_node, alert2))
        self.assertTrue(alert_found(home_brick_node, alert3))
        self.assertFalse(alert_found(home_brick_node, alert4))
        self.assertInstanceLink(home_brick_node, entity1)
        self.assertInstanceLink(home_brick_node, entity2)

        # Detail + hide validated ---
        state.set_extra_data(key=BRICK_STATE_HIDE_VALIDATED_ALERTS, value=True)
        state.save()

        response3 = self.assertGET200(self.entity.get_absolute_url())
        detail_brick_node_hidden = self.get_brick_node(
            self.get_html_tree(response3.content),
            AlertsBrick.id_,
        )

        self.assertTrue(alert_found(detail_brick_node_hidden, alert1))
        self.assertFalse(alert_found(detail_brick_node_hidden, alert2))
        self.assertFalse(alert_found(detail_brick_node_hidden, alert3))

        # Home + hide validated ---
        response4 = self.assertGET200(reverse('creme_core__home'))
        home_brick_node_hidden = self.get_brick_node(
            self.get_html_tree(response4.content),
            AlertsBrick.id_,
        )

        self.assertTrue(alert_found(home_brick_node_hidden, alert1))
        self.assertFalse(alert_found(home_brick_node_hidden, alert2))
        self.assertTrue(alert_found(home_brick_node_hidden, alert3))
        self.assertFalse(alert_found(home_brick_node_hidden, alert4))

    def test_brick_hide_validated_alerts(self):
        user = self.user

        def get_state():
            return BrickState.objects.get_for_brick_id(user=user, brick_id=AlertsBrick.id_)

        self.assertIsNone(get_state().pk)

        url = reverse('assistants__hide_validated_alerts')
        self.assertGET405(url)

        # ---
        self.assertPOST200(url, data={'value': 'true'})
        state1 = get_state()
        self.assertIsNotNone(state1.pk)
        self.assertIs(
            state1.get_extra_data(BRICK_STATE_HIDE_VALIDATED_ALERTS),
            True,
        )

        # ---
        self.assertPOST200(url, data={'value': '0'})
        self.assertIs(
            get_state().get_extra_data(BRICK_STATE_HIDE_VALIDATED_ALERTS),
            False,
        )
