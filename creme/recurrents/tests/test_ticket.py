# -*- coding: utf-8 -*-

from datetime import timedelta
from functools import partial

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.timezone import now

# Should be a test queue
# from creme.creme_core.core.job import JobSchedulerQueue
from creme.creme_core.core.job import get_queue
# from creme.creme_core.models import Job
# from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.creme_core.utils.date_period import DatePeriod, date_period_registry

# from ..creme_jobs import recurrents_gendocs_type
from .base import (  # CTYPE_KEY
    RecurrentGenerator,
    RecurrentsTestCase,
    skipIfCustomGenerator,
)

if apps.is_installed('creme.tickets'):
    from creme.tickets import get_ticket_model, get_tickettemplate_model
    from creme.tickets.models import Criticity, Priority, Status
    from creme.tickets.tests import (
        skipIfCustomTicket,
        skipIfCustomTicketTemplate,
    )

    Ticket = get_ticket_model()
    TicketTemplate = get_tickettemplate_model()
else:
    from unittest import skip

    def skipIfCustomTicket(test_func):
        return skip('App "tickets" not installed')(test_func)

    def skipIfCustomTicketTemplate(test_func):
        return skip('App "tickets" not installed')(test_func)


@skipIfNotInstalled('creme.tickets')
@skipIfCustomGenerator
# class RecurrentsTicketsTestCase(CremeTestCase):
class RecurrentsTicketsTestCase(RecurrentsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.ct = ContentType.objects.get_for_model(Ticket)

    def setUp(self):
        super().setUp()
        self.login()

    # def _get_job(self):
    #     return self.get_object_or_fail(Job, type_id=recurrents_gendocs_type.id)
    #
    # def _generate_docs(self, job=None):
    #     recurrents_gendocs_type.execute(job or self._get_job())

    def _create_ticket_template(self, title='Support ticket'):
        return TicketTemplate.objects.create(
            user=self.user,
            title=title,
            status=Status.objects.all()[0],
            priority=Priority.objects.all()[0],
            criticity=Criticity.objects.all()[0],
        )

    @staticmethod
    def _get_weekly():
        return date_period_registry.get_period('weeks', 1)

    @skipIfCustomTicketTemplate
    def test_createview(self):
        user = self.user
        url = reverse('recurrents__create_generator')
        self.assertGET200(url)

        # queue = JobSchedulerQueue.get_main_queue()
        queue = get_queue()
        queue.clear()

        name = 'Recurrent tickets'
        response = self.client.post(
            url,
            data={
                'recurrent_generator_wizard-current_step': 0,

                '0-user':             user.id,
                '0-name':             name,
                '0-first_generation': '11-06-2014 09:00',
                '0-periodicity_0':    'days',
                '0-periodicity_1':    '4',

                # CTYPE_KEY: self.ct.id,
                self.CTYPE_KEY: self.ct.id,
            },
        )
        self.assertNoWizardFormError(response)

        with self.assertNoException():
            wizard = response.context['wizard']
            steps = wizard['steps']
            count = steps.count
            current = steps.current

        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-wizard.html')
        self.assertEqual(2, count)
        self.assertEqual('1', current)

        title = 'Support ticket'
        desc = "blablabla"
        status = Status.objects.all()[0]
        priority = Priority.objects.all()[0]
        criticity = Criticity.objects.all()[0]
        response = self.client.post(
            url,
            follow=True,
            data={
                'recurrent_generator_wizard-current_step': 1,

                '1-user':        user.id,
                '1-title':       title,
                '1-description': desc,
                '1-status':      status.id,
                '1-priority':    priority.id,
                '1-criticity':   criticity.id,
            },
        )
        self.assertNoWizardFormError(response)

        gen = self.get_object_or_fail(RecurrentGenerator, name=name)
        tpl = self.get_object_or_fail(TicketTemplate, title=title)
        self.assertRedirects(response, tpl.get_absolute_url())

        self.assertEqual(user,    gen.user)
        self.assertEqual(self.ct, gen.ct)

        periodicity = gen.periodicity
        self.assertIsInstance(periodicity, DatePeriod)
        self.assertEqual({'type': 'days', 'value': 4}, periodicity.as_dict())

        self.assertEqual(
            self.create_datetime(year=2014, month=6, day=11, hour=9),
            gen.first_generation
        )
        self.assertIsNone(gen.last_generation)
        self.assertEqual(tpl, gen.template.get_real_entity())
        self.assertTrue(gen.is_working)

        self.assertEqual(user,      tpl.user)
        self.assertEqual(desc,      tpl.description)
        self.assertEqual(status,    tpl.status)
        self.assertEqual(priority,  tpl.priority)
        self.assertEqual(criticity, tpl.criticity)
        self.assertFalse(tpl.solution)

        jobs = queue.refreshed_jobs
        self.assertEqual(1, len(jobs))
        self.assertEqual(self._get_job(), jobs[0][0])

    def test_editview01(self):
        user = self.user

        tpl1 = self._create_ticket_template(title='TicketTemplate #1')
        tpl2 = self._create_ticket_template(title='TicketTemplate #2')

        gen = RecurrentGenerator.objects.create(
            name='Gen1',
            user=user,
            first_generation=now(),
            last_generation=None,
            periodicity=date_period_registry.get_period('weeks', 2),
            ct=self.ct, template=tpl1,
        )

        url = gen.get_edit_absolute_url()
        self.assertGET200(url)

        # queue = JobSchedulerQueue.get_main_queue()
        queue = get_queue()
        queue.clear()

        name = gen.name.upper()
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':             user.id,
                'name':             name,
                'first_generation': '12-06-2014 10:00',

                'periodicity_0':      'months',
                'periodicity_1':      '1',

                # should not be used
                'ct': ContentType.objects.get_for_model(Priority).id,
                'template': tpl2.id,
            },
        )
        self.assertNoFormError(response)
        self.assertRedirects(response, gen.get_absolute_url())
        self.assertTemplateUsed(response, 'recurrents/view_generator.html')

        gen = self.refresh(gen)
        self.assertEqual(name, gen.name)
        self.assertEqual(
            self.create_datetime(year=2014, month=6, day=12, hour=10),
            gen.first_generation,
        )
        self.assertEqual(self.ct, gen.ct)
        self.assertEqual(tpl1, gen.template.get_real_entity())
        self.assertEqual({'type': 'months', 'value': 1}, gen.periodicity.as_dict())

        self.assertEqual(1, len(queue.refreshed_jobs))

    def test_editview02(self):
        "last_generation has been filled => cannot edit first_generation"
        user = self.user

        now_value = now().replace(microsecond=0)  # MySQL does not record microseconds...
        gen = RecurrentGenerator.objects.create(
            name='Gen1',
            user=user,
            first_generation=now_value,
            last_generation=now_value,
            periodicity=date_period_registry.get_period('months', 1),
            ct=self.ct,
            template=self._create_ticket_template(title='TicketTemplate #1'),
        )

        name = gen.name.upper()
        response = self.client.post(
            gen.get_edit_absolute_url(), follow=True,
            data={
                'user': user.id,
                'name': name,

                # Should not be used
                'first_generation': '12-06-2014 10:00',

                'periodicity_0': 'months',
                'periodicity_1': '3',
            },
        )
        self.assertNoFormError(response)

        gen = self.refresh(gen)
        self.assertEqual(now_value, gen.first_generation)

    def test_listview(self):
        tpl = self._create_ticket_template()
        now_value = now()
        create_gen = partial(
            RecurrentGenerator.objects.create,
            user=self.user,
            first_generation=now_value,
            last_generation=now_value,
            periodicity=self._get_weekly(),
            ct=self.ct,
            template=tpl,
        )
        gen1 = create_gen(name='Gen1')
        gen2 = create_gen(name='Gen2')

        response = self.assertGET200(RecurrentGenerator.get_lv_absolute_url())

        with self.assertNoException():
            gens_page = response.context['page_obj']

        self.assertEqual(2, gens_page.paginator.count)
        self.assertSetEqual({gen1, gen2}, {*gens_page.object_list})

    @skipIfCustomTicket
    @skipIfCustomTicketTemplate
    def test_job01(self):
        "first_generation in the past + (no generation yet (ie last_generation is None)."
        self.assertFalse(Ticket.objects.all())
        now_value = now()

        job = self._get_job()
        self.assertIsNone(job.user)
        self.assertIsNone(job.type.next_wakeup(job, now_value))

        tpl = self._create_ticket_template()
        start = now_value - timedelta(days=5)
        gen = RecurrentGenerator.objects.create(
            name='Gen1',
            user=self.user,
            periodicity=self._get_weekly(),
            ct=self.ct, template=tpl,
            first_generation=start,
            last_generation=None,
        )
        self.assertDatetimesAlmostEqual(now(), job.type.next_wakeup(job, now_value))

        # queue = JobSchedulerQueue.get_main_queue()
        queue = get_queue()
        queue.clear()

        self._generate_docs(job)

        new_tickets = Ticket.objects.all()
        self.assertEqual(1, len(new_tickets))

        ticket = new_tickets[0]
        self.assertEqual(
            '{} {}'.format(tpl.title, date_format(now_value.date(), 'DATE_FORMAT')),
            ticket.title,
        )

        gen = self.refresh(gen)
        self.assertEqual(gen.first_generation, gen.last_generation)

        # Job which edits generator should not cause REFRESH signal
        self.assertEqual([], queue.refreshed_jobs)

    @skipIfCustomTicket
    @skipIfCustomTicketTemplate
    def test_job02(self):
        "last_generation is not far enough."
        tpl = self._create_ticket_template()
        now_value = now()
        RecurrentGenerator.objects.create(
            name='Gen1',
            user=self.user,
            periodicity=self._get_weekly(),
            ct=self.ct, template=tpl,
            first_generation=now_value - timedelta(days=13),
            last_generation=now_value - timedelta(days=6),
        )

        job = self._get_job()
        wakeup = job.type.next_wakeup(job, now_value)
        self.assertIsNotNone(wakeup)
        self.assertDatetimesAlmostEqual(now_value + timedelta(days=1), wakeup)

        self._generate_docs(job)
        self.assertFalse(Ticket.objects.all())

    @skipIfCustomTicket
    @skipIfCustomTicketTemplate
    def test_job03(self):
        "last_generation is far enough."
        tpl = self._create_ticket_template()
        now_value = now().replace(microsecond=0)  # MySQL does not record microseconds...
        gen = RecurrentGenerator.objects.create(
            name='Gen1',
            user=self.user,
            periodicity=self._get_weekly(),
            ct=self.ct,
            template=tpl,
            first_generation=now_value - timedelta(days=15),
            last_generation=now_value - timedelta(days=7),
        )

        job = self._get_job()
        self.assertDatetimesAlmostEqual(now(), job.type.next_wakeup(job, now()))

        self._generate_docs(job)
        self.assertEqual(1, Ticket.objects.count())

        gen = self.refresh(gen)
        self.assertEqual(now_value, gen.last_generation)

    @skipIfCustomTicketTemplate
    def test_next_wakeup(self):
        "Minimum of the future generations."
        now_value = now()
        create_gen = partial(
            RecurrentGenerator.objects.create,
            user=self.user, ct=self.ct, template=self._create_ticket_template(),
        )
        create_gen(
            name='Gen1', periodicity=self._get_weekly(),
            first_generation=now_value - timedelta(days=8),
            last_generation=now_value - timedelta(days=1),
        )  # In 6 days
        create_gen(
            name='Gen2', periodicity=date_period_registry.get_period('days', 1),
            first_generation=now_value - timedelta(hours=34),
            last_generation=now_value - timedelta(hours=10),
        )  # In 14 hours ==> that's the one !
        create_gen(
            name='Gen3', periodicity=date_period_registry.get_period('months', 1),
            first_generation=now_value - timedelta(weeks=5),
            last_generation=now_value - timedelta(weeks=1),
        )  # In ~3 weeks

        job = self._get_job()
        wakeup = job.type.next_wakeup(job, now_value)
        self.assertIsNotNone(wakeup)
        self.assertDatetimesAlmostEqual(now_value + timedelta(hours=14), wakeup)

    def test_refresh_job(self):
        # queue = JobSchedulerQueue.get_main_queue()
        queue = get_queue()
        job = self._get_job()
        tpl = self._create_ticket_template()
        now_value = now()
        gen = RecurrentGenerator.objects.create(
            name='Generator',
            user=self.user,
            first_generation=now_value + timedelta(days=2),
            last_generation=None,
            periodicity=date_period_registry.get_period('weeks', 2),
            ct=self.ct, template=tpl,
        )

        queue.clear()
        gen.name = 'My Generator'
        gen.save()
        self.assertFalse(queue.refreshed_jobs)

        gen.first_generation = now_value + timedelta(hours=3)
        gen.save()
        refreshed_jobs = queue.refreshed_jobs
        self.assertEqual(1, len(refreshed_jobs))
        self.assertEqual(job, refreshed_jobs[0][0])

        queue.clear()
        gen.name = 'My Generator again'
        gen.save()
        # The new value of 'first_generation' is cached -> no new refreshing
        self.assertFalse(queue.refreshed_jobs)

        gen.periodicity = date_period_registry.get_period('weeks', 1)
        gen.save()
        self.assertEqual(1, len(queue.refreshed_jobs))

        queue.clear()
        gen.name = 'My Generator again & again'
        gen.save()
        # The new value of 'periodicity' is cached -> no new refreshing
        self.assertFalse(queue.refreshed_jobs)
