# -*- coding: utf-8 -*-

from django.test import TestCase
from django.contrib.auth.models import User

from creme_core.management.commands.creme_populate import Command as PopulateCommand

from tickets.models import *
from tickets.models.status import BASE_STATUS, OPEN_PK, CLOSED_PK, INVALID_PK


class TicketTestCase(TestCase):
    def login(self):
        if not self.user:
            user = User.objects.all()[0]
            user.set_password(self.password)
            user.is_superuser = True
            user.save()
            self.user = user

        logged = self.client.login(username=self.user.username, password=self.password)
        self.assert_(logged, 'Not logged in')

    def setUp(self):
        PopulateCommand().handle('-a tickets -v')
        self.password = 'test'
        self.user = None

    def test_status_n_friends(self):
        for pk, name in BASE_STATUS:
            try:
                Status.objects.get(pk=pk)
            except Status.DoesNotExist:
                self.fail("Bad populate: status with pk=%s (%s) doesn't exist" % (pk, name))

        self.assert_(Priority.objects.all().count() >= 2)
        self.assert_(Criticity.objects.all().count() >= 2)

    def test_ticket_detailview01(self):
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
        self.assertEqual(response.status_code, 200)

        try:
            retr_ticket = response.context['object']
        except KeyError, e:
            self.fail(str(e))

        self.assert_(isinstance(retr_ticket, Ticket), 'Not a Ticket')
        self.assertEqual(priority.id,  retr_ticket.priority.id)
        self.assertEqual(criticity.id, retr_ticket.criticity.id)
        self.assertEqual(title,        retr_ticket.title)
        self.assertEqual(description,  retr_ticket.description)

    def test_ticket_detailview02(self):
        self.login()

        response = self.client.get('/tickets/ticket/1024')
        self.assertEqual(response.status_code, 404)

    def test_ticket_createview01(self):
        self.login()

        self.failIf(Ticket.objects.all())

        response = self.client.get('/tickets/ticket/add')
        self.assertEqual(response.status_code, 200)

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
        self.assertEqual(response.status_code, 200)
        self.assert_(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)

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

    def test_ticket_editview01(self):
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
        self.assertEqual(response.status_code, 302)

        edited_ticket = Ticket.objects.get(pk=ticket)
        self.assertEqual(priority.id,  edited_ticket.priority.id)
        self.assertEqual(criticity.id, edited_ticket.criticity.id)
        self.assertEqual(title,        edited_ticket.title)
        self.assertEqual(description,  edited_ticket.description)
        self.assertEqual(INVALID_PK,   edited_ticket.status_id)
        self.failIf(ticket.get_resolving_duration())

    def test_ticket_editview02(self):
        self.login()

        title        = 'Test ticket'
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
        self.assertEqual(response.status_code, 302)

        edited_ticket = Ticket.objects.get(pk=ticket)
        self.assertEqual(CLOSED_PK, edited_ticket.status_id)

        self.assert_(edited_ticket.closing_date)
        self.assert_(edited_ticket.get_resolving_duration())

    def test_ticket_listview01(self):
        self.login()

        response = self.client.get('/tickets/tickets')
        self.assertEqual(response.status_code, 200)

        try:
            tickets_page = response.context['entities']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(1, tickets_page.number)
        self.failIf(tickets_page.paginator.count)

    def test_ticket_listview02(self):
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
