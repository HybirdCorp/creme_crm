from django.urls import reverse

from creme.creme_core.tests.base import CremeTestCase

from .. import constants
from ..models import Criticity, Priority, Status
from .base import (
    Ticket,
    TicketTemplate,
    skipIfCustomTicket,
    skipIfCustomTicketTemplate,
)


@skipIfCustomTicketTemplate
class TicketTemplateTestCase(CremeTestCase):
    def create_template(self, *, user, title, description='description', status=None):
        status = status or Status.objects.get(uuid=constants.UUID_STATUS_OPEN)

        return TicketTemplate.objects.create(
            user=user,
            title=title,
            description=description,
            status=status,
            priority=Priority.objects.all()[0],
            criticity=Criticity.objects.all()[0],
        )

    def test_detail_view(self):
        user = self.login_as_root_and_get()
        self.assertGET200(self.create_template(user=user, title='Title').get_absolute_url())

    def test_edition(self):
        user = self.login_as_root_and_get()

        title = 'Title'
        description = 'Description ...'
        template = self.create_template(user=user, title=title, description=description)
        url = template.get_edit_absolute_url()

        self.assertGET200(url)

        title += '_edited'
        description = '_edited'
        status = Status.objects.create(name='My status')
        priority = Priority.objects.create(name='My priority')
        criticity = Criticity.objects.create(name='My criticity')
        response = self.client.post(
            url, follow=True,
            data={
                'user':        user.id,
                'title':       title,
                'description': description,
                'status':      status.id,
                'priority':    priority.id,
                'criticity':   criticity.id,
            },
        )
        self.assertNoFormError(response)

        template = self.refresh(template)
        self.assertEqual(title,       template.title)
        self.assertEqual(description, template.description)
        self.assertEqual(status,      template.status)
        self.assertEqual(priority,    template.priority)
        self.assertEqual(criticity,   template.criticity)

    def test_listview(self):
        user = self.login_as_root_and_get()

        self.create_template(user=user, title='Title01')
        self.create_template(user=user, title='Title02')
        self.assertGET200(TicketTemplate.get_lv_absolute_url())

    @skipIfCustomTicket
    def test_create_entity(self):
        user = self.login_as_root_and_get()
        template = self.create_template(
            user=user, title='Title',
            status=Status.objects.get(uuid=constants.UUID_STATUS_OPEN),
        )

        with self.assertNoException():
            ticket = template.create_entity()

        self.assertIn(template.title, ticket.title)
        self.assertEqual(template.description, ticket.description)
        self.assertEqual(template.status,      ticket.status)
        self.assertEqual(template.priority,    ticket.priority)
        self.assertEqual(template.criticity,   ticket.criticity)
        self.assertFalse(ticket.closing_date)

    @skipIfCustomTicket
    def test_create_entity__closed_status(self):
        user = self.login_as_root_and_get()
        template = self.create_template(
            user=user, title='Title',
            status=Status.objects.get(uuid=constants.UUID_STATUS_CLOSED),
        )

        with self.assertNoException():
            ticket = template.create_entity()

        self.assertIn(template.title, ticket.title)
        self.assertEqual(template.description, ticket.description)
        self.assertEqual(template.status,      ticket.status)
        self.assertEqual(template.priority,    ticket.priority)
        self.assertEqual(template.criticity,   ticket.criticity)
        self.assertTrue(ticket.closing_date)

    @skipIfCustomTicket
    def test_create_entity__closed_status__custom(self):
        "Custom closing status."
        user = self.login_as_root_and_get()

        status = Status.objects.create(
            name='Alternative closed',
            is_closed=True,
        )
        template = self.create_template(user=user, title='Title', status=status)

        with self.assertNoException():
            ticket = template.create_entity()

        self.assertIn(template.title, ticket.title)
        self.assertEqual(template.description, ticket.description)
        self.assertEqual(template.status,      ticket.status)
        self.assertEqual(template.priority,    ticket.priority)
        self.assertEqual(template.criticity,   ticket.criticity)
        self.assertTrue(ticket.closing_date)

    @skipIfCustomTicket
    def test_create_entity__title_uniqueness(self):
        "Several generations -> 'title' column must be unique."
        user = self.login_as_root_and_get()

        self.assertFalse(Ticket.objects.count())

        template = self.create_template(user=user, title='Title')

        with self.assertNoException():
            template.create_entity()
            template.create_entity()

        self.assertEqual(2, Ticket.objects.count())

    def test_multi_delete(self):
        "Should not delete."
        user = self.login_as_root_and_get()

        template01 = self.create_template(user=user, title='Title01')
        template02 = self.create_template(user=user, title='Title02')
        self.assertPOST409(
            reverse('creme_core__delete_entities'),
            data={'ids': f'{template01.id},{template02.id},'},
        )
        self.assertEqual(
            2,
            TicketTemplate.objects.filter(pk__in=[template01.id, template02.id]).count(),
        )
