# -*- coding: utf-8 -*-

from django.contrib.contenttypes.models import ContentType

from creme_core.models import HeaderFilter
from creme_core.tests.base import CremeTestCase

from tickets.models import *
from tickets.models.status import BASE_STATUS, OPEN_PK, CLOSED_PK, INVALID_PK


class TicketTestCase(CremeTestCase):
    def setUp(self):
        self.populate('tickets')

    def test_populate(self):
        for pk, name in BASE_STATUS:
            try:
                Status.objects.get(pk=pk)
            except Status.DoesNotExist:
                self.fail("Bad populate: status with pk=%s (%s) doesn't exist" % (pk, name))

        self.assert_(Priority.objects.all().count() >= 2)
        self.assert_(Criticity.objects.all().count() >= 2)

        get_ct = ContentType.objects.get_for_model
        self.assert_(HeaderFilter.objects.filter(entity_type=get_ct(Ticket)).exists())
        self.assert_(HeaderFilter.objects.filter(entity_type=get_ct(TicketTemplate)).exists())

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

        try:
            retr_ticket = response.context['object']
        except KeyError, e:
            self.fail(str(e))

        self.assert_(isinstance(retr_ticket, Ticket), 'Not a Ticket')
        self.assertEqual(priority.id,  retr_ticket.priority.id)
        self.assertEqual(criticity.id, retr_ticket.criticity.id)
        self.assertEqual(title,        retr_ticket.title)
        self.assertEqual(description,  retr_ticket.description)

    def test_detailview02(self):
        self.login()

        self.assertEqual(404, self.client.get('/tickets/ticket/1024').status_code)

    def test_createview01(self):
        self.login()

        self.failIf(Ticket.objects.all())
        self.assertEqual(200, self.client.get('/tickets/ticket/add').status_code)

        title       = 'Test ticket'
        description = 'Test description'
        priority    = Priority.objects.all()[0]
        criticity   = Criticity.objects.all()[0]
        response = self.client.post('/tickets/ticket/add', follow=True,
                                    data={
                                            'user':         self.user.pk,
                                            'title':        title,
                                            'description':  description,
                                            'priority':     priority.id,
                                            'criticity':    criticity.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain)
        self.assertEqual(1, len(response.redirect_chain))

        tickets = Ticket.objects.all()
        self.assertEqual(len(tickets), 1)

        ticket = tickets[0]
        self.assertEqual(title,        ticket.title)
        self.assertEqual(description,  ticket.description)
        self.assertEqual(priority.id,  ticket.priority.id)
        self.assertEqual(criticity.id, ticket.criticity.id)
        self.assertEqual(OPEN_PK,      ticket.status_id)

        self.failIf(ticket.closing_date)
        self.failIf(ticket.get_resolving_duration())

        try: #test FunctionField
            funf = ticket.function_fields.get('get_resolving_duration')
        except Exception, e:
            self.fail(str(e))

    def test_editview01(self):
        self.login()

        ticket = Ticket.objects.create(user=self.user,
                                       title='title',
                                       description='description',
                                       status=Status.objects.get(pk=OPEN_PK),
                                       priority=Priority.objects.all()[0],
                                       criticity=Criticity.objects.all()[0],
                                      )

        response = self.client.get('/tickets/ticket/edit/%s' % ticket.pk)
        self.assertEqual(response.status_code, 200)

        title       = 'Test ticket'
        description = 'Test description'
        priority    = Priority.objects.all()[1]
        criticity   = Criticity.objects.all()[1]

        response = self.client.post('/tickets/ticket/edit/%s' % ticket.pk,
                                    data={
                                            'user':         self.user.pk,
                                            'title':        title,
                                            'description':  description,
                                            'status':       INVALID_PK,
                                            'priority':     priority.id,
                                            'criticity':    criticity.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(response.status_code, 302)

        edited_ticket = Ticket.objects.get(pk=ticket)
        self.assertEqual(priority.id,  edited_ticket.priority.id)
        self.assertEqual(criticity.id, edited_ticket.criticity.id)
        self.assertEqual(title,        edited_ticket.title)
        self.assertEqual(description,  edited_ticket.description)
        self.assertEqual(INVALID_PK,   edited_ticket.status_id)
        self.failIf(ticket.get_resolving_duration())

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
                                    data={
                                            'user':         self.user.pk,
                                            'title':        title,
                                            'description':  description,
                                            'status':       CLOSED_PK,
                                            'priority':     priority.id,
                                            'criticity':    criticity.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(response.status_code, 302)

        edited_ticket = Ticket.objects.get(pk=ticket)
        self.assertEqual(CLOSED_PK, edited_ticket.status_id)

        self.assert_(edited_ticket.closing_date)
        self.assert_(edited_ticket.get_resolving_duration())

    def test_listview01(self):
        self.login()

        response = self.client.get('/tickets/tickets')
        self.assertEqual(response.status_code, 200)

        try:
            tickets_page = response.context['entities']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(1, tickets_page.number)
        self.failIf(tickets_page.paginator.count)

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
        self.assertEqual(response.status_code, 200)

        try:
            tickets_page = response.context['entities']
        except KeyError, e:
            self.fail(str(e))

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
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assert_(response.redirect_chain[0][0].endswith('/tickets/tickets'))

    def test_ticket_clone01(self):
        self.login()
        title = 'ticket'
        ticket = Ticket.objects.create(user=self.user, title=title, description="d",
                                       status=Status.objects.get(pk=OPEN_PK),
                                       priority=Priority.objects.all()[0],
                                       criticity=Criticity.objects.all()[0])

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
                                       criticity=Criticity.objects.all()[0])

        stack = [ticket]
        stack_append = stack.append

        for i in xrange(100):
            clone = ticket.clone()
            self.assertNotEqual(stack[-1].title, clone.title)
            stack_append(clone)

class TicketTemplateTestCase(CremeTestCase):
    def setUp(self):
        self.populate('tickets')

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
                                    data={
                                            'user':        self.user.id,
                                            'title':       title,
                                            'description': description,
                                            'status':      status.id,
                                            'priority':    priority.id,
                                            'criticity':   criticity.id,
                                    }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        template = TicketTemplate.objects.get(pk=template.id) #refresh
        self.assertEqual(title,        template.title)
        self.assertEqual(description,  template.description)
        self.assertEqual(status.id,    template.status_id)
        self.assertEqual(priority.id,  template.priority_id)
        self.assertEqual(criticity.id, template.criticity_id)

    def test_listview(self):
        self.login()

        self.create_template('Title01')
        self.create_template('Title02')
        self.assertEqual(200, self.client.get('/tickets/templates').status_code)

    def test_create_entity01(self):
        self.login()

        template = self.create_template('Title', status=Status.objects.get(pk=OPEN_PK))
        try:
            ticket = template.create_entity()
        except Exception, e:
            self.fail(str(e))

        self.assert_(template.title in ticket.title)
        self.assertEqual(template.description,  ticket.description)
        self.assertEqual(template.status_id,    ticket.status_id)
        self.assertEqual(template.priority_id,  ticket.priority_id)
        self.assertEqual(template.criticity_id, ticket.criticity_id)
        self.failIf(ticket.closing_date)

    def test_create_entity02(self):
        self.login()

        template = self.create_template('Title', status=Status.objects.get(pk=CLOSED_PK))
        try:
            ticket = template.create_entity()
        except Exception, e:
            self.fail(str(e))

        self.assert_(template.title in ticket.title)
        self.assertEqual(template.description,  ticket.description)
        self.assertEqual(template.status_id,    ticket.status_id)
        self.assertEqual(template.priority_id,  ticket.priority_id)
        self.assertEqual(template.criticity_id, ticket.criticity_id)
        self.assert_(ticket.closing_date)

    def test_create_entity03(self): #several generations -> 'title' column must be unique
        self.login()

        self.assertEqual(0, Ticket.objects.count())

        template = self.create_template('Title')
        try:
            template.create_entity()
            template.create_entity()
        except Exception, e:
            self.fail(str(e))

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
