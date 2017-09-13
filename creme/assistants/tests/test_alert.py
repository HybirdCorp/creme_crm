# -*- coding: utf-8 -*-

try:
    from datetime import timedelta, datetime
    from functools import partial

    from django.contrib.auth import get_user_model
    from django.contrib.contenttypes.models import ContentType
    from django.core import mail
    from django.core.urlresolvers import reverse
    from django.db.models.query import QuerySet
    from django.test.utils import override_settings
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _

    from creme.creme_core.core.job import JobManagerQueue  # Should be a test queue
    # from creme.creme_core.management.commands.reminder import Command as ReminderCommand
    from creme.creme_core.models import CremeEntity, DateReminder, FakeOrganisation, FakeMailingList

    from ..models import Alert
    from .base import AssistantsTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class AlertTestCase(AssistantsTestCase):
    def _build_add_url(self, entity):
        # return '/assistants/alert/add/%s/' % entity.id
        return reverse('assistants__create_alert', args=(entity.id,))

    def _create_alert(self, title='TITLE', description='DESCRIPTION', trigger_date='2010-9-29', entity=None):
        entity = entity or self.entity
        response = self.client.post(self._build_add_url(entity),
                                    data={'user':         self.user.pk,
                                          'title':        title,
                                          'description':  description,
                                          'trigger_date': trigger_date,
                                         }
                                   )
        self.assertNoFormError(response)

        return self.get_object_or_fail(Alert, title=title, description=description)

    def test_create01(self):
        self.assertFalse(Alert.objects.exists())

        queue = JobManagerQueue.get_main_queue()
        queue.clear()

        entity = self.entity
        self.assertGET200(self._build_add_url(entity))

        title = 'Title'
        alert = self._create_alert(title, 'Description', '2010-9-29')
        self.assertEqual(1, Alert.objects.count())

        self.assertIs(False,        alert.is_validated)
        self.assertEqual(self.user, alert.user)
        self.assertIs(False,        alert.reminded)

        self.assertEqual(entity.id,             alert.entity_id)
        self.assertEqual(entity.entity_type_id, alert.entity_content_type_id)
        self.assertEqual(self.create_datetime(year=2010, month=9, day=29),
                         alert.trigger_date
                        )

        self.assertEqual(title, unicode(alert))

        self.assertEqual([self.get_reminder_job()], queue.refreshed_jobs)

    def test_create02(self):
        "Errors"
        def _fail_creation(**post_data):
            response = self.assertPOST200(self._build_add_url(self.entity), data=post_data)

            with self.assertNoException():
                form = response.context['form']

            self.assertFalse(form.is_valid(), 'Creation should fail with data=%s' % post_data)

        user_pk = self.user.pk
        _fail_creation(user=user_pk, title='',      description='description', trigger_date='2010-9-29')
        _fail_creation(user=user_pk, title='title', description='description', trigger_date='')

    def test_edit(self):
        title       = 'Title'
        description = 'Description'
        alert = self._create_alert(title, description, '2010-9-29')

        url = alert.get_edit_absolute_url()
        self.assertGET200(url)

        title       += '_edited'
        description += '_edited'
        response = self.client.post(url, data={'user':         self.user.pk,
                                               'title':        title,
                                               'description':  description,
                                               'trigger_date': '2011-10-30',
                                               'trigger_time': '15:12:00',
                                              }
                                   )
        self.assertNoFormError(response)

        alert = self.refresh(alert)
        self.assertEqual(title,       alert.title)
        self.assertEqual(description, alert.description)

        # Don't care about seconds
        #self.assertEqual(datetime(year=2011, month=10, day=30, hour=15, minute=12), alert.trigger_date)
        self.assertEqual(self.create_datetime(year=2011, month=10, day=30, hour=15, minute=12),
                         alert.trigger_date
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
        # self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': alert.id})
        self.client.post(reverse('creme_core__delete_related_to_entity', args=(ct.id,)), data={'id': alert.id})
        self.assertEqual(0, Alert.objects.count())

    def test_validate(self):
        alert = self._create_alert()
        self.assertFalse(alert.is_validated)

        # response = self.assertPOST200('/assistants/alert/validate/%s/' % alert.id, follow=True)
        response = self.assertPOST200(reverse('assistants__validate_alert', args=(alert.id,)), follow=True)
        self.assertRedirects(response, self.entity.get_absolute_url())

        self.assertTrue(self.refresh(alert).is_validated)

    def test_function_field01(self):
        funf = CremeEntity.function_fields.get('assistants-get_alerts')
        self.assertIsNotNone(funf)
        self.assertEqual(u'<ul></ul>', funf(self.entity, self.user).for_html())

    def test_function_field02(self):
        funf = CremeEntity.function_fields.get('assistants-get_alerts')

        self._create_alert('Alert01', 'Description01', trigger_date='2011-10-21')
        self._create_alert('Alert02', 'Description02', trigger_date='2010-10-20')

        alert3 = self._create_alert('Alert03', 'Description03', trigger_date='2010-10-3')
        alert3.is_validated = True
        alert3.save()

        with self.assertNumQueries(1):
            result = funf(self.entity, self.user)

        self.assertEqual(u'<ul><li>Alert02</li><li>Alert01</li></ul>', result.for_html())

    def test_function_field03(self):
        "Prefetch with 'populate_entities()'"
        user = self.user
        self._create_alert('Alert01', 'Description01', trigger_date='2011-10-21')
        self._create_alert('Alert02', 'Description02', trigger_date='2010-10-20')

        entity02 = CremeEntity.objects.create(user=user)

        alert3 = self._create_alert('Alert03', 'Description03', trigger_date='2010-10-3', entity=entity02)
        alert3.is_validated = True
        alert3.save()

        self._create_alert('Alert04', 'Description04', trigger_date='2010-10-3', entity=entity02)

        funf = CremeEntity.function_fields.get('assistants-get_alerts')

        with self.assertNumQueries(1):
            funf.populate_entities([self.entity, entity02], user)

        with self.assertNumQueries(0):
            result1 = funf(self.entity, user)
            result2 = funf(entity02, user)

        self.assertEqual(u'<ul><li>Alert02</li><li>Alert01</li></ul>', result1.for_html())
        self.assertEqual(u'<ul><li>Alert04</li></ul>',                 result2.for_html())

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

        reminder_ids = list(DateReminder.objects.values_list('id', flat=True))

        create_alert = partial(Alert.objects.create, creme_entity=self.entity,
                               user=user, trigger_date=now_value,
                              )
        alert1 = create_alert(title='Alert#1', trigger_date=now_value + timedelta(minutes=50))
        alert2 = create_alert(title='Alert#2', trigger_date=now_value + timedelta(minutes=70))
        create_alert(title='Alert#3', is_validated=True)

        self.assertLess(job.type.next_wakeup(job, now_value), now())

        # def remind():
        #     ReminderCommand().execute(verbosity=0)
        #
        # remind()
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
        self.assertEqual(_(u'Reminder concerning a Creme CRM alert related to %s') % self.entity,
                         message.subject
                        )
        self.assertIn(alert1.title, message.body)

        # Reminders are not recreated if they already exist
        # remind()
        self.execute_reminder_job(job)
        self.assertFalse(DateReminder.objects.exclude(id__in=reminder_ids + [reminder.id]))
        self.assertEqual(1, len(mail.outbox))

    @override_settings(DEFAULT_TIME_ALERT_REMIND=30)
    def test_next_wakeup(self):
        now_value = now()

        create_alert = partial(Alert.objects.create, creme_entity=self.entity,
                               user=self.user, trigger_date=now_value,
                              )
        create_alert(title='Alert#2', is_validated=True)
        create_alert(title='Alert#4', reminded=True)
        create_alert(title='Alert#6', trigger_date=now_value + timedelta(minutes=60))
        create_alert(title='Alert#1', trigger_date=now_value + timedelta(minutes=50))  # <== only this one should be used
        create_alert(title='Alert#7', trigger_date=now_value + timedelta(minutes=70))
        create_alert(title='Alert#3', is_validated=True)
        create_alert(title='Alert#5', reminded=True)

        job = self.get_reminder_job()
        wakeup = job.type.next_wakeup(job, now_value)
        self.assertIsInstance(wakeup, datetime)
        self.assertDatetimesAlmostEqual(now_value + timedelta(minutes=20),
                                        wakeup
                                       )

    def test_get_alerts(self):
        user = self.user
        now_value = now()

        entity2 = FakeOrganisation.objects.create(user=user, name='Thousand sunny')

        create_alert = partial(Alert.objects.create, creme_entity=self.entity,
                               user=user, trigger_date=now_value,
                              )
        alert1 = create_alert(title='Alert#1')
        create_alert(title='Alert#2', is_validated=True)  # No (validated)
        alert3 = create_alert(title='Alert#3')
        create_alert(title='Alert#4', creme_entity=entity2)  # No (other entity)

        alerts = Alert.get_alerts(entity=self.entity)
        self.assertIsInstance(alerts, QuerySet)
        self.assertEqual(Alert, alerts.model)

        self.assertEqual({alert1, alert3}, set(alerts))
        self.assertEqual(2, len(alerts))

    def test_get_alerts_for_home01(self):
        user = self.user
        now_value = now()

        create_alert = partial(Alert.objects.create, creme_entity=self.entity,
                               user=user, trigger_date=now_value,
                              )
        alert1 = create_alert(title='Alert#1')
        create_alert(title='Alert#2', is_validated=True)  # No (validated)
        alert3 = create_alert(title='Alert#3')
        create_alert(title='Alert#4', user=self.other_user)  # No (other user)

        alerts = Alert.get_alerts_for_home(user=user)
        self.assertIsInstance(alerts, QuerySet)
        self.assertEqual(Alert, alerts.model)

        self.assertEqual({alert1, alert3}, set(alerts))
        self.assertEqual(2, len(alerts))

    def test_get_alerts_for_home02(self):
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

        create_alert = partial(Alert.objects.create, creme_entity=self.entity,
                               user=user, trigger_date=now_value,
                              )
        alert1 = create_alert(title='Alert#1')
        create_alert(title='Alert#2', user=team2)  # No (other team)
        alert3 = create_alert(title='Alert#3', user=team1)

        alerts = Alert.get_alerts_for_home(user=user)
        self.assertEqual({alert1, alert3}, set(alerts))
        self.assertEqual(2, len(alerts))

    def test_get_alerts_for_ctypes01(self):
        user = self.user
        now_value = now()

        entity2 = FakeOrganisation.objects.create(user=user, name='Thousand sunny')
        entity3 = FakeMailingList.objects.create(user=user, name='Pirates')

        create_alert = partial(Alert.objects.create, creme_entity=self.entity,
                               user=user, trigger_date=now_value,
                              )
        alert1 = create_alert(title='Alert#1')
        create_alert(title='Alert#2', is_validated=True)  # No (validated)
        alert3 = create_alert(title='Alert#3')
        create_alert(title='Alert#4', user=self.other_user)  # No (other user)
        alert5 = create_alert(title='Alert#5', creme_entity=entity2)
        create_alert(title='Alert#6', creme_entity=entity3)  # No (bad ctype)

        alerts = Alert.get_alerts_for_ctypes(user=user, ct_ids=[self.entity.entity_type_id, entity2.entity_type_id])
        self.assertIsInstance(alerts, QuerySet)
        self.assertEqual(Alert, alerts.model)

        self.assertEqual({alert1, alert3, alert5}, set(alerts))
        self.assertEqual(3, len(alerts))

    def test_get_alerts_for_ctypes02(self):
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

        create_alert = partial(Alert.objects.create, creme_entity=self.entity,
                               user=user, trigger_date=now_value,
                              )
        alert1 = create_alert(title='Alert#1')
        create_alert(title='Alert#2', user=team2)  # No (other team)
        alert3 = create_alert(title='Alert#3', user=team1)
        alert4 = create_alert(title='Alert#4', creme_entity=entity2)

        alerts = Alert.get_alerts_for_ctypes(user=user, ct_ids=[self.entity.entity_type_id, entity2.entity_type_id])
        self.assertEqual({alert1, alert3, alert4}, set(alerts))
        self.assertEqual(3, len(alerts))
