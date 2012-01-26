# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import HeaderFilter
    from creme_core.tests.base import CremeTestCase

    from tickets.models import *
    from tickets.models.status import BASE_STATUS, OPEN_PK, CLOSED_PK, INVALID_PK
except Exception as e:
    print 'Error:', e


class TicketTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'tickets')
    #def setUp(self):
        #self.populate('creme_core', 'creme_config', 'tickets')

    def test_populate(self):
        for pk, name in BASE_STATUS:
            try:
                Status.objects.get(pk=pk)
            except Status.DoesNotExist:
                self.fail("Bad populate: status with pk=%s (%s) doesn't exist" % (pk, name))

        self.assertGreaterEqual(Priority.objects.count(),  2)
        self.assertGreaterEqual(Criticity.objects.count(), 2)

        get_ct = ContentType.objects.get_for_model
        self.assertTrue(HeaderFilter.objects.filter(entity_type=get_ct(Ticket)).exists())
        self.assertTrue(HeaderFilter.objects.filter(entity_type=get_ct(TicketTemplate)).exists())

    def test_portal(self):
        self.login()
        self.assertEqual(200, self.client.get('/tickets/').status_code)

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

        response = self.client.get('/tickets/ticket/%s' % ticket.pk)
        self.assertEqual(200, response.status_code)

        #try:
            #retr_ticket = response.context['object']
        #except KeyError as e:
            #self.fail(str(e))
        with self.assertNoException():
            retr_ticket = response.context['object']

        self.assertIsInstance(retr_ticket, Ticket)
        self.assertEqual(priority,     retr_ticket.priority)
        self.assertEqual(criticity,    retr_ticket.criticity)
        self.assertEqual(title,        retr_ticket.title)
        self.assertEqual(description,  retr_ticket.description)

    def test_detailview02(self):
        self.login()
        self.assertEqual(404, self.client.get('/tickets/ticket/1024').status_code)

    def test_createview01(self):
        self.login()

        self.assertEqual(0, Ticket.objects.count())
        url = '/tickets/ticket/add'
        self.assertEqual(200, self.client.get(url).status_code)

        title       = 'Test ticket'
        description = 'Test description'
        priority    = Priority.objects.all()[0]
        criticity   = Criticity.objects.all()[0]
        response = self.client.post(url, follow=True,
                                    data={'user':         self.user.pk,
                                          'title':        title,
                                          'description':  description,
                                          'priority':     priority.id,
                                          'criticity':    criticity.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
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

        #try:
            #funf = ticket.function_fields.get('get_resolving_duration')
        #except Exception as e:
            #self.fail(str(e))
        with self.assertNoException():
            funf = ticket.function_fields.get('get_resolving_duration')

        self.assertEqual('', funf(ticket).for_html())

    def test_editview01(self):
        self.login()

        ticket = Ticket.objects.create(user=self.user,
                                       title='title',
                                       description='description',
                                       status=Status.objects.get(pk=OPEN_PK),
                                       priority=Priority.objects.all()[0],
                                       criticity=Criticity.objects.all()[0],
                                      )

        url = '/tickets/ticket/edit/%s' % ticket.pk
        self.assertEqual(200, self.client.get(url).status_code)

        title       = 'Test ticket'
        description = 'Test description'
        priority    = Priority.objects.all()[1]
        criticity   = Criticity.objects.all()[1]
        response = self.client.post(url, data={'user':         self.user.pk,
                                               'title':        title,
                                               'description':  description,
                                               'status':       INVALID_PK,
                                               'priority':     priority.id,
                                               'criticity':    criticity.id,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(302, response.status_code)

        ticket = self.refresh(ticket)
        self.assertEqual(priority,     ticket.priority)
        self.assertEqual(criticity,    ticket.criticity)
        self.assertEqual(title,        ticket.title)
        self.assertEqual(description,  ticket.description)
        self.assertEqual(INVALID_PK,   ticket.status.id)
        self.assertFalse(ticket.get_resolving_duration())

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

        response = self.client.post('/tickets/ticket/edit/%s' % ticket.pk,
                                    data={'user':         self.user.pk,
                                          'title':        title,
                                          'description':  description,
                                          'status':       CLOSED_PK,
                                          'priority':     priority.id,
                                          'criticity':    criticity.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(302, response.status_code)

        ticket = self.refresh(ticket)
        self.assertEqual(CLOSED_PK, ticket.status_id)

        self.assertTrue(ticket.closing_date)
        self.assertTrue(ticket.get_resolving_duration())
        self.assertTrue(ticket.function_fields.get('get_resolving_duration')(ticket))

    def test_listview01(self):
        self.login()

        response = self.client.get('/tickets/tickets')
        self.assertEqual(response.status_code, 200)

        #try:
            #tickets_page = response.context['entities']
        #except Exception as e:
            #self.fail(str(e))
        with self.assertNoException():
            tickets_page = response.context['entities']

        self.assertEqual(1, tickets_page.number)
        self.assertFalse(tickets_page.paginator.count)

    def test_listview02(self):
        self.login()

        ticket = Ticket.objects.create(user=self.user,
                                       title='title',
                                       description='description',
                                       status=Status.objects.get(pk=OPEN_PK),
                                       priority=Priority.objects.all()[0],
                                       criticity=Criticity.objects.all()[0],
                                      )

        response = self.client.get('/tickets/tickets')
        self.assertEqual(200, response.status_code)

        #try:
            #tickets_page = response.context['entities']
        #except KeyError as e:
            #self.fail(str(e))
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

        response = self.client.post('/creme_core/entity/delete/%s' % ticket.pk, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(response.redirect_chain))
        self.assertTrue(response.redirect_chain[0][0].endswith('/tickets/tickets'))

    def test_ticket_clone01(self):
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

    def test_ticket_clone02(self):
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


class TicketTemplateTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'tickets')
    #def setUp(self):
        #self.populate('creme_core', 'creme_config', 'tickets')

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
        self.assertEqual(200, self.client.get('/tickets/template/%s' % template.id).status_code)

    def test_edit(self):
        self.login()

        title = 'Title'
        description='Description ...'
        template = self.create_template(title, description)
        url = '/tickets/template/edit/%s' % template.id

        self.assertEqual(200, self.client.get(url).status_code)

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
        self.assertEqual(200, response.status_code)

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
        self.assertEqual(200, self.client.get('/tickets/templates').status_code)

    def test_create_entity01(self):
        self.login()

        template = self.create_template('Title', status=Status.objects.get(pk=OPEN_PK))
        #try:
            #ticket = template.create_entity()
        #except Exception as e:
            #self.fail(str(e))
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
        #try:
            #ticket = template.create_entity()
        #except Exception as e:
            #self.fail(str(e))
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
        #try:
            #template.create_entity()
            #template.create_entity()
        #except Exception as e:
            #self.fail(str(e))
        with self.assertNoException():
            template.create_entity()
            template.create_entity()

        self.assertEqual(2, Ticket.objects.count())

    def test_multi_delete(self): #should not delete
        self.login()

        template01 = self.create_template('Title01')
        template02 = self.create_template('Title02')
        self.assertEqual(404, self.client.post('/creme_core/delete_js',
                                               data={'ids': '%s,%s,' % (template01.id, template02.id)}
                                              ).status_code
                        )
        self.assertEqual(2, TicketTemplate.objects.filter(pk__in=[template01.id, template02.id]).count())
