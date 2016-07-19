# -*- coding: utf-8 -*-

try:
    from datetime import timedelta
    from functools import partial

    from django.apps import apps
    from django.contrib.contenttypes.models import ContentType
    from django.core.urlresolvers import reverse
    from django.utils.formats import date_format
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _

    from creme.creme_core.core.entity_cell import EntityCellRegularField
    from creme.creme_core.core.job import JobManagerQueue  # Should be a test queue
    from creme.creme_core.models import HeaderFilter, Job
    from creme.creme_core.tests.base import CremeTestCase, skipIfNotInstalled
    from creme.creme_core.utils.date_period import date_period_registry, DatePeriod

    from creme.tickets import get_ticket_model, get_tickettemplate_model
    from creme.tickets.models import Status, Priority, Criticity
    from creme.tickets.tests import skipIfCustomTicket, skipIfCustomTicketTemplate

    from .base import skipIfCustomGenerator, RecurrentGenerator
    # from ..management.commands.recurrents_gendocs import Command as GenDocsCommand
    from ..creme_jobs import recurrents_gendocs_type
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


Ticket = get_ticket_model()
TicketTemplate = get_tickettemplate_model()


@skipIfCustomGenerator
class RecurrentsTicketsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        # apps_2_pop = ['recurrents']

        if apps.is_installed('creme.tickets'):
            # apps_2_pop.append('tickets')
            cls.ct = ContentType.objects.get_for_model(Ticket)

        # cls.populate(*apps_2_pop)

    def setUp(self):
        self.login()

    def _get_job(self):
        return self.get_object_or_fail(Job, type_id=recurrents_gendocs_type.id)

    def _generate_docs(self, job=None):
        recurrents_gendocs_type.execute(job or self._get_job())

    def test_portal(self):
        self.assertGET200('/recurrents/')

    def test_populate(self):
        self.assertTrue(HeaderFilter.objects.filter(entity_type=ContentType.objects.get_for_model(RecurrentGenerator)))

    def test_entity_cell(self):
        e_cell = EntityCellRegularField.build(model=RecurrentGenerator, name='name')
        self.assertIsInstance(e_cell, EntityCellRegularField)
        self.assertEqual(_('Name of the generator'), e_cell.title)
        self.assertTrue(e_cell.sortable)
        self.assertTrue(e_cell.has_a_filter)

        e_cell = EntityCellRegularField.build(model=RecurrentGenerator, name='periodicity')
        self.assertIsInstance(e_cell, EntityCellRegularField)
        self.assertEqual(_('Periodicity of the generation'), e_cell.title)
        self.assertFalse(e_cell.sortable)
        self.assertFalse(e_cell.has_a_filter)

    def _create_ticket_template(self, title='Support ticket'):
        return TicketTemplate.objects.create(user=self.user,
                                             title=title,
                                             status=Status.objects.all()[0],
                                             priority=Priority.objects.all()[0],
                                             criticity=Criticity.objects.all()[0],
                                            )

    def _get_weekly(self):
        return date_period_registry.get_period('weeks', 1)

    @skipIfNotInstalled('creme.tickets')
    @skipIfCustomTicketTemplate
    def test_createview(self):
        user = self.user
        url = reverse('recurrents__create_generator')
        self.assertGET200(url)

        queue = JobManagerQueue.get_main_queue()
        queue.clear()

        name = 'Recurrent tickets'
        response = self.client.post(url,
                                    data={'recurrent_generator_wizard-current_step': 0,

                                          '0-user':             user.id,
                                          '0-name':             name,
                                          '0-ct':               self.ct.id,
                                          '0-first_generation': '11-06-2014 09:00',
                                          '0-periodicity_0':    'days',
                                          '0-periodicity_1':    '4',
                                         }
                                    )
        self.assertNoWizardFormError(response)

        with self.assertNoException():
            wizard = response.context['wizard']
            steps = wizard['steps']
            count = steps.count
            current = steps.current

        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add_wizard.html')
        self.assertEqual(2, count)
        self.assertEqual('1', current)

        title     = 'Support ticket'
        desc      = "blablabla"
        status    = Status.objects.all()[0]
        priority  = Priority.objects.all()[0]
        criticity = Criticity.objects.all()[0]
        response = self.client.post(url, follow=True,
                                    data={'recurrent_generator_wizard-current_step': 1,

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

        self.assertEqual(user,    gen.user)
        self.assertEqual(self.ct, gen.ct)

        periodicity = gen.periodicity
        self.assertIsInstance(periodicity, DatePeriod)
        self.assertEqual({'type': 'days', 'value': 4}, periodicity.as_dict())

        self.assertEqual(self.create_datetime(year=2014, month=6, day=11, hour=9),
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

        self.assertEqual([self._get_job()], queue.refreshed_jobs)

    @skipIfNotInstalled('creme.tickets')
    def test_editview01(self):
        user = self.user

        tpl1 = self._create_ticket_template(title='TicketTemplate #1')
        tpl2 = self._create_ticket_template(title='TicketTemplate #2')

        gen = RecurrentGenerator.objects.create(name='Gen1',
                                                user=user,
                                                first_generation=now(),
                                                last_generation=None,
                                                periodicity=date_period_registry.get_period('weeks', 2),
                                                ct=self.ct, template=tpl1,
                                               )

        url = gen.get_edit_absolute_url()
        self.assertGET200(url)

        queue = JobManagerQueue.get_main_queue()
        queue.clear()

        name = gen.name.upper()
        response = self.client.post(url, follow=True,
                                    data={'user':             user.id,
                                          'name':             name,
                                          'first_generation': '12-06-2014 10:00',

                                          'periodicity_0':      'months',
                                          'periodicity_1':      '1',

                                          # should not be used
                                          'ct': ContentType.objects.get_for_model(Priority).id,
                                          'template': tpl2.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertRedirects(response, gen.get_absolute_url())

        gen = self.refresh(gen)
        self.assertEqual(name, gen.name)
        self.assertEqual(self.create_datetime(year=2014, month=6, day=12, hour=10),
                         gen.first_generation
                        )
        self.assertEqual(self.ct, gen.ct)
        self.assertEqual(tpl1, gen.template.get_real_entity())
        self.assertEqual({'type': 'months', 'value': 1}, gen.periodicity.as_dict())

        self.assertEqual([self._get_job()], queue.refreshed_jobs)

    @skipIfNotInstalled('creme.tickets')
    def test_editview02(self):
        "last_generation has been filled => cannot edit first_generation"
        user = self.user

        now_value = now().replace(microsecond=0)  # MySQL does not record microseconds...
        gen = RecurrentGenerator.objects.create(name='Gen1',
                                                user=user,
                                                first_generation=now_value,
                                                last_generation=now_value,
                                                periodicity=date_period_registry.get_period('months', 1),
                                                ct=self.ct,
                                                template=self._create_ticket_template(title='TicketTemplate #1'),
                                               )

        name = gen.name.upper()
        response = self.client.post(gen.get_edit_absolute_url(), follow=True,
                                    data={'user':             user.id,
                                          'name':             name,
                                          'first_generation': '12-06-2014 10:00',  # Should not be used

                                          'periodicity_0':    'months',
                                          'periodicity_1':    '3',
                                         }
                                   )
        self.assertNoFormError(response)

        gen = self.refresh(gen)
        self.assertEqual(now_value, gen.first_generation)

    @skipIfNotInstalled('creme.tickets')
    def test_listview(self):
        tpl = self._create_ticket_template()
        now_value = now()
        create_gen = partial(RecurrentGenerator.objects.create, user=self.user,
                             first_generation=now_value,
                             last_generation=now_value,
                             periodicity=self._get_weekly(),
                             ct=self.ct, template=tpl,
                            )
        gen1 = create_gen(name='Gen1')
        gen2 = create_gen(name='Gen2') 

        response = self.assertGET200(RecurrentGenerator.get_lv_absolute_url())

        with self.assertNoException():
            gens_page = response.context['entities']

        self.assertEqual(2, gens_page.paginator.count)
        self.assertEqual({gen1, gen2}, set(gens_page.object_list))

    @skipIfNotInstalled('creme.tickets')
    @skipIfCustomTicket
    @skipIfCustomTicketTemplate
    def test_job01(self):
        "first_generation in the past + (no generation yet (ie last_generation is None)"
        self.assertFalse(Ticket.objects.all())
        now_value = now()

        job = self._get_job()
        self.assertIsNone(job.user)
        self.assertIsNone(job.type.next_wakeup(job, now_value))

        tpl = self._create_ticket_template()
        start = now_value - timedelta(days=5)
        gen = RecurrentGenerator.objects.create(name='Gen1', user=self.user,
                                                periodicity=self._get_weekly(),
                                                ct=self.ct, template=tpl,
                                                first_generation=start,
                                                last_generation=None,
                                               )

        # GenDocsCommand().execute(verbosity=0)
        self.assertDatetimesAlmostEqual(now(), job.type.next_wakeup(job, now_value))

        queue = JobManagerQueue.get_main_queue()
        queue.clear()

        self._generate_docs(job)

        new_tickets = Ticket.objects.all()
        self.assertEqual(1, len(new_tickets))

        ticket = new_tickets[0]
#        self.assertEqual(u'%s %s #1' % (tpl.title, date_format(now_value.date(), 'DATE_FORMAT')),
        self.assertEqual(u'%s %s' % (tpl.title, date_format(now_value.date(), 'DATE_FORMAT')),
                         ticket.title
                        )

        gen = self.refresh(gen)
        self.assertEqual(gen.first_generation, gen.last_generation)

        self.assertEqual([], queue.refreshed_jobs)  # Job which edits generator should not cause REFRESH signal

    @skipIfNotInstalled('creme.tickets')
    @skipIfCustomTicket
    @skipIfCustomTicketTemplate
    def test_job02(self):
        "last_generation is not far enough"
        tpl = self._create_ticket_template()
        now_value = now()
        RecurrentGenerator.objects.create(name='Gen1', user=self.user,
                                          periodicity=self._get_weekly(),
                                          ct=self.ct, template=tpl,
                                          first_generation=now_value - timedelta(days=13),
                                          last_generation=now_value - timedelta(days=6),
                                         )

        job = self._get_job()
        wakeup = job.type.next_wakeup(job, now_value)
        self.assertIsNotNone(wakeup)
        self.assertDatetimesAlmostEqual(now_value + timedelta(days=1), wakeup)

        # GenDocsCommand().handle(verbosity=0)
        self._generate_docs(job)
        self.assertFalse(Ticket.objects.all())

    @skipIfNotInstalled('creme.tickets')
    @skipIfCustomTicket
    @skipIfCustomTicketTemplate
    def test_job03(self):
        "last_generation is far enough"
        tpl = self._create_ticket_template()
        now_value = now().replace(microsecond=0)  # MySQL does not record microseconds...
        gen = RecurrentGenerator.objects.create(name='Gen1', user=self.user,
                                                periodicity=self._get_weekly(),
                                                ct=self.ct, template=tpl,
                                                first_generation=now_value - timedelta(days=15),
                                                last_generation=now_value - timedelta(days=7),
                                               )

        # GenDocsCommand().handle(verbosity=0)
        job = self._get_job()
        self.assertDatetimesAlmostEqual(now(), job.type.next_wakeup(job, now()))

        self._generate_docs(job)
        self.assertEqual(1, Ticket.objects.count())

        gen = self.refresh(gen)
        self.assertEqual(now_value, gen.last_generation)

    @skipIfNotInstalled('creme.tickets')
    @skipIfCustomTicketTemplate
    def test_next_wakeup(self):
        "Minimum of the future generations"
        now_value = now()
        create_gen = partial(RecurrentGenerator.objects.create, user=self.user,
                             ct=self.ct, template=self._create_ticket_template(),
                            )
        create_gen(name='Gen1', periodicity=self._get_weekly(),
                   first_generation=now_value - timedelta(days=8),
                   last_generation=now_value - timedelta(days=1),
                  )  # In 6 days
        create_gen(name='Gen2', periodicity=date_period_registry.get_period('days', 1),
                   first_generation=now_value - timedelta(hours=34),
                   last_generation=now_value - timedelta(hours=10),
                  )  # In 14 hours ==> that's the one !
        create_gen(name='Gen3', periodicity=date_period_registry.get_period('months', 1),
                   first_generation=now_value - timedelta(weeks=5),
                   last_generation=now_value - timedelta(weeks=1),
                  )  # In ~3 weeks

        job = self._get_job()
        wakeup = job.type.next_wakeup(job, now_value)
        self.assertIsNotNone(wakeup)
        self.assertDatetimesAlmostEqual(now_value + timedelta(hours=14), wakeup)

    @skipIfNotInstalled('creme.tickets')
    def test_refresh_job(self):
        queue = JobManagerQueue.get_main_queue()
        job = self._get_job()
        tpl = self._create_ticket_template()
        now_value = now()
        gen = RecurrentGenerator.objects.create(name='Generator',
                                                user=self.user,
                                                first_generation=now_value + timedelta(days=2),
                                                last_generation=None,
                                                periodicity=date_period_registry.get_period('weeks', 2),
                                                ct=self.ct, template=tpl,
                                               )

        queue.clear()
        gen.name = 'My Generator'
        gen.save()
        self.assertEqual([], queue.refreshed_jobs)

        gen.first_generation = now_value + timedelta(hours=3)
        gen.save()
        self.assertEqual([job], queue.refreshed_jobs)

        queue.clear()
        gen.name = 'My Generator again'
        gen.save()
        self.assertEqual([], queue.refreshed_jobs)  # The new value of 'first_generation' is cached -> no new refreshing

        gen.periodicity=date_period_registry.get_period('weeks', 1)
        gen.save()
        self.assertEqual([job], queue.refreshed_jobs)

        queue.clear()
        gen.name = 'My Generator again & again'
        gen.save()
        self.assertEqual([], queue.refreshed_jobs)  # The new value of 'periodicity' is cached -> no new refreshing
