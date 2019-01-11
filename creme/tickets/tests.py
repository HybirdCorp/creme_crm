# -*- coding: utf-8 -*-

skip_ticket_tests = False
skip_tickettemplate_tests = False

try:
    from datetime import timedelta
    from functools import partial
    from unittest import skipIf

    from django.contrib.contenttypes.models import ContentType
    from django.test.utils import override_settings
    from django.urls import reverse
    from django.utils.timezone import now

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.views.base import CSVImportBaseTestCaseMixin
    from creme.creme_core.core.function_field import function_field_registry
    from creme.creme_core.models import RelationType, HeaderFilter
    from creme.creme_core.templatetags.creme_date import timedelta_pprint

    from creme.persons import get_contact_model

    from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

    from . import (ticket_model_is_custom, tickettemplate_model_is_custom,
            get_ticket_model, get_tickettemplate_model)
    from .models import Status, Priority, Criticity, TicketNumber
    from .models.status import BASE_STATUS, OPEN_PK, CLOSED_PK, INVALID_PK

    skip_ticket_tests = ticket_model_is_custom()
    skip_tickettemplate_tests = tickettemplate_model_is_custom()

    Ticket = get_ticket_model()
    TicketTemplate = get_tickettemplate_model()
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


def skipIfCustomTicket(test_func):
    return skipIf(skip_ticket_tests, 'Custom Ticket model in use')(test_func)


def skipIfCustomTicketTemplate(test_func):
    return skipIf(skip_tickettemplate_tests, 'Custom TicketTemplate model in use')(test_func)


@skipIfCustomTicket
class TicketTestCase(CremeTestCase, CSVImportBaseTestCaseMixin):
    def test_populate(self):
        for pk, name in BASE_STATUS:
            try:
                status = Status.objects.get(pk=pk)
            except Status.DoesNotExist:
                self.fail("Bad populate: status with pk={} ({}) doesn't exist".format(pk, name))
            else:
                self.assertEqual(name, status.name)
                self.assertFalse(status.is_custom)
                self.assertIsNotNone(status.order)

        self.assertGreaterEqual(Priority.objects.count(),  2)
        self.assertGreaterEqual(Criticity.objects.count(), 2)

        get_ct = ContentType.objects.get_for_model
        hf_filter = HeaderFilter.objects.filter
        ticket_ct = get_ct(Ticket)
        self.assertTrue(hf_filter(entity_type=ticket_ct).exists())
        self.assertTrue(hf_filter(entity_type=get_ct(TicketTemplate)).exists())

        # Contribution to activities
        rtype = self.get_object_or_fail(RelationType, pk=REL_SUB_ACTIVITY_SUBJECT)
        self.assertTrue(rtype.subject_ctypes.filter(id=ticket_ct.id).exists())
        self.assertTrue(rtype.subject_ctypes.filter(id=get_ct(get_contact_model()).id).exists())
        self.assertTrue(rtype.symmetric_type.object_ctypes.filter(id=ticket_ct.id).exists())

    def test_detailview01(self):
        self.login()

        title       = 'Test ticket'
        description = 'Test description'
        priority    = Priority.objects.all()[0]
        criticity   = Criticity.objects.all()[0]
        ticket = Ticket.objects.create(user=self.user,
                                       title=title,
                                       description=description,
                                       status=Status.objects.get(pk=OPEN_PK),
                                       priority=priority,
                                       criticity=criticity,
                                      )

        response = self.assertGET200(ticket.get_absolute_url())
        self.assertTemplateUsed(response, 'tickets/view_ticket.html')

        with self.assertNoException():
            retr_ticket = response.context['object']

        self.assertIsInstance(retr_ticket, Ticket)
        self.assertEqual(priority,    retr_ticket.priority)
        self.assertEqual(criticity,   retr_ticket.criticity)
        self.assertEqual(title,       retr_ticket.title)
        self.assertEqual(description, retr_ticket.description)

        self.assertEqual(u'#{} - {}'.format(ticket.number, title),
                         str(retr_ticket)
                        )

    def test_detailview02(self):
        self.login()
        self.assertGET404(reverse('tickets__view_ticket', args=(1024,)))

    def test_createview01(self):
        user = self.login()

        self.assertEqual(0, Ticket.objects.count())
        url = reverse('tickets__create_ticket')
        self.assertGET200(url)

        title       = 'Test ticket'
        description = 'Test description'
        priority    = Priority.objects.all()[0]
        criticity   = Criticity.objects.all()[0]
        number = 1024
        data = {'user':         self.user.pk,
                'title':        title,
                'description':  description,
                'priority':     priority.id,
                'criticity':    criticity.id,
                'number':       number,  # Should not be used
               }
        response = self.client.post(url, follow=True, data=data)
        self.assertNoFormError(response)

        tickets = Ticket.objects.all()
        self.assertEqual(len(tickets), 1)

        ticket = tickets[0]
        self.assertEqual(title,        ticket.title)
        self.assertEqual(description,  ticket.description)
        self.assertEqual(priority,     ticket.priority)
        self.assertEqual(criticity,    ticket.criticity)
        self.assertEqual(OPEN_PK,      ticket.status_id)

        self.assertTrue(ticket.number)
        self.assertNotEqual(number, ticket.number)

        self.assertFalse(ticket.closing_date)
        self.assertFalse(ticket.get_resolving_duration())

        funf = function_field_registry.get(Ticket, 'get_resolving_duration')
        self.assertIsNotNone(funf)

        self.assertEqual('', funf(ticket, user).for_html())

        self.assertRedirects(response, ticket.get_absolute_url())

    def test_number(self):
        user = self.login()

        self.assertFalse(TicketNumber.objects.all())

        create_ticket= partial(Ticket.objects.create, user=user,
                               priority= Priority.objects.all()[0],
                               criticity= Criticity.objects.all()[0],
                              )
        ticket1 = create_ticket(title='Test ticket #1')
        numbers1 = TicketNumber.objects.all()
        self.assertEqual(1, len(numbers1))
        self.assertEqual(numbers1[0].id, ticket1.number)

        ticket2 = create_ticket(title='Test ticket #2')
        self.assertNotEqual(ticket1.number, ticket2.number)

        numbers2 = TicketNumber.objects.all()
        self.assertEqual(1, len(numbers2))

    def test_get_resolving_duration01(self):
        "Resolving duration with CLOSED_PK + closing_date=None (eg: CSV import)"
        user = self.login()

        get_status = Status.objects.get
        ticket = Ticket.objects.create(user=user,
                                       title='title',
                                       description='description',
                                       status=get_status(pk=OPEN_PK),
                                       priority=Priority.objects.all()[0],
                                       criticity=Criticity.objects.all()[0],
                                      )
        self.assertIsNone(ticket.closing_date)
        self.assertEqual('', ticket.get_resolving_duration())

        ticket.status = get_status(pk=CLOSED_PK)
        ticket.save()
        self.assertDatetimesAlmostEqual(now(), ticket.closing_date)
        self.assertEqual(timedelta_pprint(ticket.closing_date - ticket.created),
                         ticket.get_resolving_duration()
                        )

    def test_get_resolving_duration02(self):
        "Resolving duration with CLOSED_PK + closing_date=None (eg: CSV import)"
        user = self.login()

        ticket = Ticket.objects.create(user=user,
                                       title='title',
                                       description='description',
                                       status=Status.objects.get(pk=CLOSED_PK),
                                       priority=Priority.objects.all()[0],
                                       criticity=Criticity.objects.all()[0],
                                      )
        self.assertEqual('?', ticket.get_resolving_duration())

    def test_editview01(self):
        user = self.login()

        ticket = Ticket.objects.create(user=user,
                                       title='title',
                                       description='description',
                                       status=Status.objects.get(pk=OPEN_PK),
                                       priority=Priority.objects.all()[0],
                                       criticity=Criticity.objects.all()[0],
                                      )

        url = ticket.get_edit_absolute_url()
        self.assertGET200(url)

        title       = 'Test ticket'
        description = 'Test description'
        priority    = Priority.objects.all()[1]
        criticity   = Criticity.objects.all()[1]
        response = self.client.post(url, follow=True,
                                    data={'user':         user.pk,
                                          'title':        title,
                                          'description':  description,
                                          'status':       INVALID_PK,
                                          'priority':     priority.id,
                                          'criticity':    criticity.id,
                                         }
                                   )
        self.assertNoFormError(response)

        ticket = self.refresh(ticket)
        self.assertEqual(priority,     ticket.priority)
        self.assertEqual(criticity,    ticket.criticity)
        self.assertEqual(title,        ticket.title)
        self.assertEqual(description,  ticket.description)
        self.assertEqual(INVALID_PK,   ticket.status.id)
        self.assertFalse(ticket.get_resolving_duration())

        self.assertRedirects(response, ticket.get_absolute_url())

    def test_editview02(self):
        user = self.login()

        title       = 'Test ticket'
        description = 'Test description'
        priority    = Priority.objects.all()[0]
        criticity   = Criticity.objects.all()[0]
        ticket = Ticket.objects.create(user=user,
                                       title=title,
                                       description=description,
                                       status=Status.objects.get(pk=OPEN_PK),
                                       priority=priority,
                                       criticity=criticity,
                                      )

        response = self.client.post(ticket.get_edit_absolute_url(), follow=True,
                                    data={'user':         user.pk,
                                          'title':        title,
                                          'description':  description,
                                          'status':       CLOSED_PK,
                                          'priority':     priority.id,
                                          'criticity':    criticity.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertRedirects(response, ticket.get_absolute_url())

        ticket = self.refresh(ticket)
        self.assertEqual(CLOSED_PK, ticket.status_id)

        self.assertTrue(ticket.closing_date)
        self.assertTrue(ticket.get_resolving_duration())
        self.assertTrue(function_field_registry.get(Ticket, 'get_resolving_duration')(ticket, user))

    def test_listview01(self):
        self.login()

        response = self.assertGET200(Ticket.get_lv_absolute_url())

        with self.assertNoException():
            tickets_page = response.context['entities']

        self.assertEqual(1, tickets_page.number)
        self.assertFalse(tickets_page.paginator.count)

    def test_listview02(self):
        user = self.login()

        Ticket.objects.create(user=user,
                              title='title',
                              description='description',
                              status=Status.objects.get(pk=OPEN_PK),
                              priority=Priority.objects.all()[0],
                              criticity=Criticity.objects.all()[0],
                             )

        response = self.assertGET200(Ticket.get_lv_absolute_url())

        with self.assertNoException():
            tickets_page = response.context['entities']

        self.assertEqual(1, tickets_page.paginator.count)

    def test_deleteview(self):
        user = self.login()

        ticket = Ticket.objects.create(user=user,
                                       title='title',
                                       description='description',
                                       status=Status.objects.get(pk=OPEN_PK),
                                       priority=Priority.objects.all()[0],
                                       criticity=Criticity.objects.all()[0],
                                      )

        url = ticket.get_delete_absolute_url()
        self.assertTrue(url)
        response = self.assertPOST200(url, follow=True)

        with self.assertNoException():
            ticket = self.refresh(ticket)

        self.assertTrue(ticket.is_deleted)
        self.assertRedirects(response, Ticket.get_lv_absolute_url())

        response = self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(ticket)
        self.assertRedirects(response, Ticket.get_lv_absolute_url())

    def test_clone(self):
        "The cloned ticket is open"
        user = self.login()

        get_status = Status.objects.get
        status_open   = get_status(pk=OPEN_PK)
        status_closed = get_status(pk=CLOSED_PK)

        ticket = Ticket.objects.create(user=user, title='ticket', description="d",
                                       status=status_open,
                                       priority=Priority.objects.all()[0],
                                       criticity=Criticity.objects.all()[0],
                                      )

        ticket.status = status_closed
        ticket.save()
        self.assertIsNotNone(ticket.closing_date)

        clone = ticket.clone()
        self.assertEqual(ticket.title, clone.title)
        self.assertEqual(status_open, clone.status)
        self.assertIsNone(clone.closing_date)

    def test_delete_status(self):
        user = self.login()

        status = Status.objects.create(name='Delete me please')
        ticket = Ticket.objects.create(user=user,
                                       title='title',
                                       description='description',
                                       status=status,
                                       priority=Priority.objects.all()[0],
                                       criticity=Criticity.objects.all()[0],
                                      )
        self.assertPOST404(reverse('creme_config__delete_instance', args=('tickets', 'status')),
                           data={'id': status.pk}
                          )
        self.assertStillExists(status)

        ticket = self.get_object_or_fail(Ticket, pk=ticket.pk)
        self.assertEqual(status, ticket.status)

    def test_delete_priority(self):
        user = self.login()

        priority = Priority.objects.create(name='Not so important')
        self.assertEqual(Priority.objects.count(), priority.order)

        ticket = Ticket.objects.create(user=user,
                                       title='title',
                                       description='description',
                                       status=Status.objects.all()[0],
                                       priority=priority,
                                       criticity=Criticity.objects.all()[0],
                                      )
        self.assertPOST404(reverse('creme_config__delete_instance', args=('tickets', 'priority')),
                           data={'id': priority.pk}
                          )
        self.assertStillExists(priority)

        ticket = self.get_object_or_fail(Ticket, pk=ticket.pk)
        self.assertEqual(priority, ticket.priority)

    def test_delete_criticity(self):
        user = self.login()

        criticity = Criticity.objects.create(name='Not so important')
        self.assertEqual(Criticity.objects.count(), criticity.order)

        ticket = Ticket.objects.create(user=user,
                                       title='title',
                                       description='description',
                                       status=Status.objects.all()[0],
                                       priority=Priority.objects.all()[0],
                                       criticity=criticity,
                                      )
        self.assertPOST404(reverse('creme_config__delete_instance', args=('tickets', 'criticity')),
                           data={'id': criticity.pk}
                          )
        self.assertStillExists(criticity)

        ticket = self.get_object_or_fail(Ticket, pk=ticket.pk)
        self.assertEqual(criticity, ticket.criticity)

    def test_csv_import(self):
        user = self.login()

        count = Ticket.objects.count()

        titles       = 'Ticket 01', 'Ticket 02'
        descriptions = 'Description #1', 'Description #2'
        status_l     = Status.objects.all()[:2]
        priorities   = Priority.objects.all()[:2]
        criticities  = Criticity.objects.all()[:2]

        lines = [(titles[0], status_l[0].name, priorities[0].name, criticities[0].name, descriptions[0]),
                 (titles[1], status_l[1].name, priorities[1].name, criticities[1].name, descriptions[1]),
                ]

        doc = self._build_csv_doc(lines)
        url = self._build_import_url(Ticket)
        self.assertGET200(url)

        response = self.client.post(url, follow=True,
                                    data={'step':     1,
                                          'document': doc.id,
                                          # has_header

                                          'user': user.id,

                                          'title_colselect': 1,

                                          'status_colselect': 2,
                                          'status_subfield':  'name',
                                          # 'status_create':    True,
                                          # 'status_defval':    def_status.pk,

                                          'priority_colselect': 3,
                                          'priority_subfield':  'name',
                                          # 'priority_create':    True,
                                          # 'priority_defval':    def_priority.pk,

                                          'criticity_colselect': 4,
                                          'criticity_subfield':  'name',
                                          # 'criticity_create':    True,
                                          # 'criticity_defval':    def_criticity.pk,

                                          'description_colselect': 5,
                                          # 'description_defval':    def_description,

                                          'solution_colselect': 0,
                                          # 'solution_defval':  def_solution,

                                          # 'property_types',
                                          # 'fixed_relations',
                                          # 'dyn_relations',
                                        }
                                   )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual(count + len(lines), Ticket.objects.count())

        for i, l in enumerate(lines):
            ticket = self.get_object_or_fail(Ticket, title=titles[i])
            self.assertEqual(user,            ticket.user)
            self.assertEqual(status_l[i],     ticket.status)
            self.assertEqual(priorities[i],   ticket.priority)
            self.assertEqual(criticities[i],  ticket.criticity)
            self.assertEqual(descriptions[i], ticket.description)
            self.assertEqual('',              ticket.solution)

        results = self._get_job_results(job)
        self.assertEqual(len(lines), len(results))
        self._assertNoResultError(results)

    @override_settings(TICKETS_COLOR_DELAY=7)
    def test_ticket_color(self):
        user = self.login()
        get_status = Status.objects.get
        create_ticket = partial(Ticket,  # .objects.create,
                                user=user,
                                title='My ticket',
                                description='Test description',
                                status=get_status(pk=OPEN_PK),
                                priority=Priority.objects.all()[0],
                                criticity=Criticity.objects.all()[0],
                               )

        now_value = now()
        self.assertEqual({}, create_ticket().get_html_attrs({'today': now_value}))

        context = {'today': now_value + timedelta(days=8)}
        self.assertEqual({'data-color': 'tickets-important'},
                         create_ticket().get_html_attrs(context)
                        )
        self.assertFalse(create_ticket(status=get_status(pk=CLOSED_PK)).get_html_attrs(context))


@skipIfCustomTicketTemplate
class TicketTemplateTestCase(CremeTestCase):
    def create_template(self, title, description='description', status=None):
        status = status or Status.objects.get(pk=OPEN_PK)

        return TicketTemplate.objects.create(user=self.user,
                                             title=title,
                                             description=description,
                                             status=status,
                                             priority=Priority.objects.all()[0],
                                             criticity=Criticity.objects.all()[0],
                                            )

    def test_detailview(self):
        self.login()
        self.assertGET200(self.create_template('Title').get_absolute_url())

    def test_edit(self):
        self.login()

        title = 'Title'
        description='Description ...'
        template = self.create_template(title, description)
        url = template.get_edit_absolute_url()

        self.assertGET200(url)

        title += '_edited'
        description = '_edited'
        status = Status.objects.create(name='My status')
        priority = Priority.objects.create(name='My priority')
        criticity = Criticity.objects.create(name='My criticity')
        response = self.client.post(url, follow=True,
                                    data={'user':        self.user.id,
                                          'title':       title,
                                          'description': description,
                                          'status':      status.id,
                                          'priority':    priority.id,
                                          'criticity':   criticity.id,
                                         }
                                   )
        self.assertNoFormError(response)

        template = self.refresh(template)
        self.assertEqual(title,       template.title)
        self.assertEqual(description, template.description)
        self.assertEqual(status,      template.status)
        self.assertEqual(priority,    template.priority)
        self.assertEqual(criticity,   template.criticity)

    def test_listview(self):
        self.login()

        self.create_template('Title01')
        self.create_template('Title02')
        self.assertGET200(TicketTemplate.get_lv_absolute_url())

    @skipIfCustomTicket
    def test_create_entity01(self):
        self.login()

        template = self.create_template('Title', status=Status.objects.get(pk=OPEN_PK))

        with self.assertNoException():
            ticket = template.create_entity()

        self.assertIn(template.title, ticket.title)
        self.assertEqual(template.description, ticket.description)
        self.assertEqual(template.status,      ticket.status)
        self.assertEqual(template.priority,    ticket.priority)
        self.assertEqual(template.criticity,   ticket.criticity)
        self.assertFalse(ticket.closing_date)

    @skipIfCustomTicket
    def test_create_entity02(self):
        self.login()

        template = self.create_template('Title', status=Status.objects.get(pk=CLOSED_PK))

        with self.assertNoException():
            ticket = template.create_entity()

        self.assertIn(template.title, ticket.title)
        self.assertEqual(template.description, ticket.description)
        self.assertEqual(template.status,      ticket.status)
        self.assertEqual(template.priority,    ticket.priority)
        self.assertEqual(template.criticity,   ticket.criticity)
        self.assertTrue(ticket.closing_date)

    @skipIfCustomTicket
    def test_create_entity03(self):
        "Several generations -> 'title' column must be unique"
        self.login()

        self.assertEqual(0, Ticket.objects.count())

        template = self.create_template('Title')

        with self.assertNoException():
            template.create_entity()
            template.create_entity()

        self.assertEqual(2, Ticket.objects.count())

    def test_multi_delete(self):
        "Should not delete"
        self.login()

        template01 = self.create_template('Title01')
        template02 = self.create_template('Title02')
        self.assertPOST404(reverse('creme_core__delete_entities'),
                           data={'ids': '{},{},'.format(template01.id, template02.id)}
                          )
        self.assertEqual(2, TicketTemplate.objects.filter(pk__in=[template01.id, template02.id]).count())
