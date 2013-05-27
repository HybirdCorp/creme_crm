# -*- coding: utf-8 -*-

try:
    from django.db import transaction
    from django.db.utils import IntegrityError
    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.tests.base import CremeTestCase, CremeTransactionTestCase
    from creme.creme_core.tests.views.list_view_import import CSVImportBaseTestCaseMixin
    from creme.creme_core.models import RelationType, HeaderFilter

    from creme.persons.models import Contact

    from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

    from .models import *
    from .models.status import BASE_STATUS, OPEN_PK, CLOSED_PK, INVALID_PK
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class TicketTestCase(CremeTestCase, CSVImportBaseTestCaseMixin):
    @classmethod
    def setUpClass(cls):
        #cls.populate('creme_core', 'creme_config', 'tickets')
        cls.populate('creme_config', 'tickets')

    def _build_edit_url(self, ticket):
        return '/tickets/ticket/edit/%s' % ticket.pk

    def test_populate(self):
        for pk, name in BASE_STATUS:
            try:
                Status.objects.get(pk=pk)
            except Status.DoesNotExist:
                self.fail("Bad populate: status with pk=%s (%s) doesn't exist" % (pk, name))

        self.assertGreaterEqual(Priority.objects.count(),  2)
        self.assertGreaterEqual(Criticity.objects.count(), 2)

        get_ct = ContentType.objects.get_for_model
        hf_filter = HeaderFilter.objects.filter
        ticket_ct = get_ct(Ticket)
        self.assertTrue(hf_filter(entity_type=ticket_ct).exists())
        self.assertTrue(hf_filter(entity_type=get_ct(TicketTemplate)).exists())

        #contribution to activities
        rtype = self.get_object_or_fail(RelationType, pk=REL_SUB_ACTIVITY_SUBJECT)
        self.assertTrue(rtype.subject_ctypes.filter(id=ticket_ct.id).exists())
        self.assertTrue(rtype.subject_ctypes.filter(id=get_ct(Contact).id).exists())
        self.assertTrue(rtype.symmetric_type.object_ctypes.filter(id=ticket_ct.id).exists())

    def test_portal(self):
        self.login()
        self.assertGET200('/tickets/')

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

        response = self.assertGET200('/tickets/ticket/%s' % ticket.pk)

        with self.assertNoException():
            retr_ticket = response.context['object']

        self.assertIsInstance(retr_ticket, Ticket)
        self.assertEqual(priority,     retr_ticket.priority)
        self.assertEqual(criticity,    retr_ticket.criticity)
        self.assertEqual(title,        retr_ticket.title)
        self.assertEqual(description,  retr_ticket.description)

    def test_detailview02(self):
        self.login()
        self.assertGET404('/tickets/ticket/1024')

    def test_createview01(self):
        self.login()

        self.assertEqual(0, Ticket.objects.count())
        url = '/tickets/ticket/add'
        self.assertGET200(url)

        title       = 'Test ticket'
        description = 'Test description'
        priority    = Priority.objects.all()[0]
        criticity   = Criticity.objects.all()[0]
        data = {'user':         self.user.pk,
                'title':        title,
                'description':  description,
                'priority':     priority.id,
                'criticity':    criticity.id,
               }
        response = self.client.post(url, follow=True, data=data)
        self.assertNoFormError(response)
        self.assertTrue(response.redirect_chain)
        self.assertEqual(1, len(response.redirect_chain))

        tickets = Ticket.objects.all()
        self.assertEqual(len(tickets), 1)

        ticket = tickets[0]
        self.assertEqual(title,        ticket.title)
        self.assertEqual(description,  ticket.description)
        self.assertEqual(priority,     ticket.priority)
        self.assertEqual(criticity,    ticket.criticity)
        self.assertEqual(OPEN_PK,      ticket.status_id)

        self.assertFalse(ticket.closing_date)
        self.assertFalse(ticket.get_resolving_duration())

        with self.assertNoException():
            funf = ticket.function_fields.get('get_resolving_duration')

        self.assertEqual('', funf(ticket).for_html())

        response = self.assertPOST200(url, follow=True, data=data)
        self.assertFormError(response, 'form', 'title',
                             [_(u"%(model_name)s with this %(field_label)s already exists.") %  {
                                    'model_name': _(u'Ticket'),
                                    'field_label': _(u'Title'),
                                }
                             ]
                            )

    def test_editview01(self):
        self.login()

        ticket = Ticket.objects.create(user=self.user,
                                       title='title',
                                       description='description',
                                       status=Status.objects.get(pk=OPEN_PK),
                                       priority=Priority.objects.all()[0],
                                       criticity=Criticity.objects.all()[0],
                                      )

        url = self._build_edit_url(ticket)
        self.assertGET200(url)

        title       = 'Test ticket'
        description = 'Test description'
        priority    = Priority.objects.all()[1]
        criticity   = Criticity.objects.all()[1]
        response = self.client.post(url, follow=True,
                                    data={'user':         self.user.pk,
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

        response = self.client.post(self._build_edit_url(ticket), follow=True,
                                    data={'user':         self.user.pk,
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
        self.assertTrue(ticket.function_fields.get('get_resolving_duration')(ticket))

    def test_listview01(self):
        self.login()

        response = self.assertGET200('/tickets/tickets')

        with self.assertNoException():
            tickets_page = response.context['entities']

        self.assertEqual(1, tickets_page.number)
        self.assertFalse(tickets_page.paginator.count)

    def test_listview02(self):
        self.login()

        Ticket.objects.create(user=self.user,
                              title='title',
                              description='description',
                              status=Status.objects.get(pk=OPEN_PK),
                              priority=Priority.objects.all()[0],
                              criticity=Criticity.objects.all()[0],
                             )

        response = self.assertGET200('/tickets/tickets')

        with self.assertNoException():
            tickets_page = response.context['entities']

        self.assertEqual(1, tickets_page.paginator.count)

    def test_deleteview(self):
        self.login()

        ticket = Ticket.objects.create(user=self.user,
                                       title='title',
                                       description='description',
                                       status=Status.objects.get(pk=OPEN_PK),
                                       priority=Priority.objects.all()[0],
                                       criticity=Criticity.objects.all()[0],
                                      )

        url = '/creme_core/entity/delete/%s' % ticket.pk
        response = self.assertPOST200(url, follow=True)

        with self.assertNoException():
            ticket = self.refresh(ticket)

        self.assertTrue(ticket.is_deleted)
        self.assertRedirects(response, Ticket.get_lv_absolute_url())

        response = self.assertPOST200(url, follow=True)
        self.assertFalse(Ticket.objects.filter(pk=ticket.pk).exists())
        self.assertRedirects(response, Ticket.get_lv_absolute_url())

    def test_clone01(self):
        self.login()
        title = 'ticket'
        ticket = Ticket.objects.create(user=self.user, title=title, description="d",
                                       status=Status.objects.get(pk=OPEN_PK),
                                       priority=Priority.objects.all()[0],
                                       criticity=Criticity.objects.all()[0],
                                      )
        stack = [ticket]
        stack_append = stack.append

        for i in xrange(100):
            clone = ticket.clone()
            ticket = stack[-1]
            self.assertNotEqual(ticket.title, clone.title)
            stack_append(clone)

    def test_clone02(self):
        self.login()
        title = 'ticket'
        ticket = Ticket.objects.create(user=self.user, title=title, description="d",
                                       status=Status.objects.get(pk=OPEN_PK),
                                       priority=Priority.objects.all()[0],
                                       criticity=Criticity.objects.all()[0]
                                      )
        stack = [ticket]
        stack_append = stack.append

        for i in xrange(100):
            clone = ticket.clone()
            self.assertNotEqual(stack[-1].title, clone.title)
            stack_append(clone)

    def test_delete_status(self):
        self.login()

        status = Status.objects.create(name='Delete me please')
        ticket = Ticket.objects.create(user=self.user,
                                       title='title',
                                       description='description',
                                       status=status,
                                       priority=Priority.objects.all()[0],
                                       criticity=Criticity.objects.all()[0],
                                      )
        self.assertPOST404('/creme_config/tickets/status/delete', data={'id': status.pk})
        self.assertTrue(Status.objects.filter(pk=status.pk).exists())

        ticket = self.get_object_or_fail(Ticket, pk=ticket.pk)
        self.assertEqual(status, ticket.status)

    def test_delete_priority(self):
        self.login()

        priority = Priority.objects.create(name='Not so important')
        ticket = Ticket.objects.create(user=self.user,
                                       title='title',
                                       description='description',
                                       status=Status.objects.all()[0],
                                       priority=priority,
                                       criticity=Criticity.objects.all()[0],
                                      )
        self.assertPOST404('/creme_config/tickets/priority/delete', data={'id': priority.pk})
        self.assertTrue(Priority.objects.filter(pk=priority.pk).exists())

        ticket = self.get_object_or_fail(Ticket, pk=ticket.pk)
        self.assertEqual(priority, ticket.priority)

    def test_delete_criticity(self):
        self.login()

        criticity = Criticity.objects.create(name='Not so important')
        ticket = Ticket.objects.create(user=self.user,
                                       title='title',
                                       description='description',
                                       status=Status.objects.all()[0],
                                       priority=Priority.objects.all()[0],
                                       criticity=criticity,
                                      )
        self.assertPOST404('/creme_config/tickets/criticity/delete', data={'id': criticity.pk})
        self.assertTrue(Criticity.objects.filter(pk=criticity.pk).exists())

        ticket = self.get_object_or_fail(Ticket, pk=ticket.pk)
        self.assertEqual(criticity, ticket.criticity)

    def test_csv_import(self):
        self.login()

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

        response = self.client.post(url, data={'step':     1,
                                               'document': doc.id,
                                               #has_header

                                               'user': self.user.id,

                                               'title_colselect': 1,

                                               'status_colselect': 2,
                                               'status_subfield':  'name',
                                               #'status_create':    True,
                                               #'status_defval':    def_status.pk,

                                               'priority_colselect': 3,
                                               'priority_subfield':  'name',
                                               #'priority_create':    True,
                                               #'priority_defval':    def_priority.pk,

                                               'criticity_colselect': 4,
                                               'criticity_subfield':  'name',
                                               #'criticity_create':    True,
                                               #'criticity_defval':    def_criticity.pk,

                                               'description_colselect': 5,
                                               #'description_defval':    def_description,

                                               'solution_colselect': 0,
                                               #'solution_defval':  def_solution,

                                               #'property_types',
                                               #'fixed_relations',
                                               #'dyn_relations',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(count + len(lines), Ticket.objects.count())

        for i, l in enumerate(lines):
            ticket = self.get_object_or_fail(Ticket, title=titles[i])
            self.assertEqual(self.user,       ticket.user)
            self.assertEqual(status_l[i],     ticket.status)
            self.assertEqual(priorities[i],   ticket.priority)
            self.assertEqual(criticities[i],  ticket.criticity)
            self.assertEqual(descriptions[i], ticket.description)
            self.assertEqual('',              ticket.solution)


class TicketTestUniqueCase(CremeTransactionTestCase):
    def test_unique_title(self):
        self.populate('tickets')
        self.login()

        title       = 'Test ticket'
        description = 'Test description %s'

        with self.assertNoException():
            Ticket.objects.create(user=self.user,
                                  title=title,
                                  description=description % 1,
                                  priority=Priority.objects.all()[0],
                                  criticity=Criticity.objects.all()[0],
                                 )

        try:
            Ticket.objects.create(user=self.user,
                                  title=title, # <====
                                  description=description % 2,
                                  priority=Priority.objects.all()[1],
                                  criticity=Criticity.objects.all()[1],
                                 )
            transaction.commit()
        except IntegrityError:
            transaction.rollback()
        else:
            self.fail('IntegrityError not raised')

        self.assertEqual(1, Ticket.objects.count())


class TicketTemplateTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'tickets') #TODO: factorise

    def create_template(self, title, description='description', status=None):
        status = status or Status.objects.get(pk=OPEN_PK)

        return TicketTemplate.objects.create(user=self.user,
                                             title=title,
                                             description='description',
                                             status=status,
                                             priority=Priority.objects.all()[0],
                                             criticity=Criticity.objects.all()[0],
                                            )

    def test_detailview(self):
        self.login()

        template = self.create_template('Title')
        self.assertGET200('/tickets/template/%s' % template.id)

    def test_edit(self):
        self.login()

        title = 'Title'
        description='Description ...'
        template = self.create_template(title, description)
        url = '/tickets/template/edit/%s' % template.id

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
        self.assertGET200('/tickets/templates')

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

    def test_create_entity03(self): #several generations -> 'title' column must be unique
        self.login()

        self.assertEqual(0, Ticket.objects.count())

        template = self.create_template('Title')

        with self.assertNoException():
            template.create_entity()
            template.create_entity()

        self.assertEqual(2, Ticket.objects.count())

    def test_multi_delete(self): #should not delete
        self.login()

        template01 = self.create_template('Title01')
        template02 = self.create_template('Title02')
        self.assertPOST404('/creme_core/entity/delete/multi',
                           data={'ids': '%s,%s,' % (template01.id, template02.id)}
                          )
        self.assertEqual(2, TicketTemplate.objects.filter(pk__in=[template01.id, template02.id]).count())
