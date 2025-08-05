from datetime import timedelta
from functools import partial
from unittest import skipIf

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

import creme.creme_core.tests.views.base as views_base
from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import HeaderFilter, RelationType
from creme.creme_core.templatetags.creme_date import timedelta_pprint
from creme.creme_core.tests.base import CremeTestCase
from creme.persons import get_contact_model

from . import (
    constants,
    get_ticket_model,
    get_tickettemplate_model,
    ticket_model_is_custom,
    tickettemplate_model_is_custom,
)
from .bricks import TicketBrick
from .models import Criticity, Priority, Status, TicketNumber

skip_ticket_tests = ticket_model_is_custom()
skip_tickettemplate_tests = tickettemplate_model_is_custom()

Ticket = get_ticket_model()
TicketTemplate = get_tickettemplate_model()


def skipIfCustomTicket(test_func):
    return skipIf(skip_ticket_tests, 'Custom Ticket model in use')(test_func)


def skipIfCustomTicketTemplate(test_func):
    return skipIf(skip_tickettemplate_tests, 'Custom TicketTemplate model in use')(test_func)


@skipIfCustomTicket
class TicketTestCase(views_base.MassImportBaseTestCaseMixin,
                     views_base.BrickTestCaseMixin,
                     CremeTestCase):
    def test_populate(self):
        open_status = self.get_object_or_fail(Status, uuid=constants.UUID_STATUS_OPEN)
        self.assertEqual(pgettext('tickets-status', 'Open'), open_status.name)
        self.assertEqual('f8f223',                           open_status.color)
        self.assertEqual(1,                                  open_status.order)
        self.assertFalse(open_status.is_closed)

        closed_status = self.get_object_or_fail(Status, uuid=constants.UUID_STATUS_CLOSED)
        self.assertEqual(pgettext('tickets-status', 'Closed'), closed_status.name)
        self.assertEqual('1dd420',                             closed_status.color)
        self.assertEqual(2,                                    closed_status.order)
        self.assertTrue(closed_status.is_closed)

        self.assertGreaterEqual(Priority.objects.count(),  2)
        self.assertGreaterEqual(Criticity.objects.count(), 2)

        get_ct = ContentType.objects.get_for_model
        hf_filter = HeaderFilter.objects.filter
        ticket_ct = get_ct(Ticket)
        self.assertTrue(hf_filter(entity_type=ticket_ct).exists())
        self.assertTrue(hf_filter(entity_type=get_ct(TicketTemplate)).exists())

        # Contribution to activities
        if apps.is_installed('creme.activities'):
            from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

            rtype = self.get_object_or_fail(RelationType, pk=REL_SUB_ACTIVITY_SUBJECT)
            self.assertTrue(
                rtype.subject_ctypes.filter(id=ticket_ct.id).exists()
            )
            self.assertTrue(
                rtype.subject_ctypes.filter(id=get_ct(get_contact_model()).id).exists()
            )
            self.assertTrue(
                rtype.symmetric_type.object_ctypes.filter(id=ticket_ct.id).exists()
            )

    def test_status(self):
        user = self.get_root_user()
        status = Status.objects.create(name='OK', color='00FF00')
        ctxt = {
            'user': user,
            'ticket': Ticket(user=user, title='OK Ticket', status=status),
        }
        template = Template(
            r'{% load creme_core_tags %}'
            r'{% print_field object=ticket field="status" tag=tag %}'
        )
        self.assertEqual(
            status.name,
            template.render(Context({**ctxt, 'tag': ViewTag.TEXT_PLAIN})).strip(),
        )
        self.assertHTMLEqual(
            f'<div class="ui-creme-colored_status">'
            f' <div class="ui-creme-color_indicator" style="background-color:#{status.color};" />'
            f' <span>{status.name}</span>'
            f'</div>',
            template.render(Context({**ctxt, 'tag': ViewTag.HTML_DETAIL})),
        )

    def test_save(self):
        user = self.get_root_user()
        title = 'Test ticket'
        description = 'Test description'
        status1 = Status.objects.get(uuid=constants.UUID_STATUS_OPEN)
        priority = Priority.objects.all()[0]
        criticity = Criticity.objects.all()[0]
        ticket = Ticket.objects.create(
            user=user,
            title=title,
            description=description,
            status=status1,
            priority=priority,
            criticity=criticity,
        )
        self.assertIsInstance(ticket, Ticket)
        self.assertEqual(status1,     ticket.status)
        self.assertEqual(priority,    ticket.priority)
        self.assertEqual(criticity,   ticket.criticity)
        self.assertEqual(title,       ticket.title)
        self.assertEqual(description, ticket.description)
        self.assertIsNone(ticket.closing_date)

        # ---
        status2 = Status.objects.get(uuid=constants.UUID_STATUS_INVALID)
        ticket.status = status2
        ticket.save()
        ticket.refresh_from_db()
        self.assertEqual(status2, ticket.status)
        self.assertIsNone(ticket.closing_date)

        # ---
        status3 = Status.objects.create(name='Very closed', is_closed=True)
        ticket.status = status3
        ticket.save()
        ticket.refresh_from_db()
        self.assertEqual(status3, ticket.status)
        self.assertDatetimesAlmostEqual(now(), ticket.closing_date)

    def test_save_update_fields(self):
        user = self.get_root_user()
        ticket = Ticket.objects.create(
            user=user,
            title='Test ticket',
            status=Status.objects.get(uuid=constants.UUID_STATUS_OPEN),
            priority=Priority.objects.all()[0],
            criticity=Criticity.objects.all()[0],
        )

        status2 = Status.objects.create(name='Very closed', is_closed=True)
        ticket.status = status2
        ticket.save(update_fields=['status'])
        ticket.refresh_from_db()
        self.assertEqual(status2, ticket.status)

        closing_date = ticket.closing_date
        self.assertIsNotNone(closing_date)
        self.assertDatetimesAlmostEqual(now(), ticket.closing_date)

    def test_detailview01(self):
        user = self.login_as_root_and_get()

        title = 'Test ticket'
        description = 'Test description'
        priority = Priority.objects.all()[0]
        criticity = Criticity.objects.all()[0]
        ticket = Ticket.objects.create(
            user=user,
            title=title,
            description=description,
            status=Status.objects.get(uuid=constants.UUID_STATUS_OPEN),
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

        self.assertEqual(
            f'#{ticket.number} - {title}', str(retr_ticket),
        )

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=TicketBrick,
        )
        self.assertEqual(
            _('Information on the ticket'),
            self.get_brick_title(brick_node),
        )
        self.assertEqual(
            priority.name,
            self.get_brick_tile(brick_node, 'regular_field-priority').text,
        )
        self.assertIsNone(
            self.get_brick_tile(brick_node, 'function_field-get_resolving_duration').text,
        )

    def test_detailview02(self):
        self.login_as_root()
        self.assertGET404(reverse('tickets__view_ticket', args=(self.UNUSED_PK,)))

    def test_createview01(self):
        user = self.login_as_root_and_get()

        self.assertEqual(0, Ticket.objects.count())
        url = reverse('tickets__create_ticket')
        self.assertGET200(url)

        title = 'Test ticket'
        description = 'Test description'
        priority = Priority.objects.all()[0]
        criticity = Criticity.objects.all()[0]
        number = 1024
        data = {
            'user':         user.pk,
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
        self.assertUUIDEqual(constants.UUID_STATUS_OPEN, ticket.status.uuid)

        self.assertTrue(ticket.number)
        self.assertNotEqual(number, ticket.number)

        self.assertFalse(ticket.closing_date)

        funf = function_field_registry.get(Ticket, 'get_resolving_duration')
        self.assertIsNotNone(funf)
        self.assertEqual('', funf(ticket, user).render(ViewTag.HTML_LIST))

        self.assertRedirects(response, ticket.get_absolute_url())

    def test_number(self):
        user = self.login_as_root_and_get()

        self.assertFalse(TicketNumber.objects.all())

        create_ticket = partial(
            Ticket.objects.create,
            user=user,
            priority=Priority.objects.all()[0],
            criticity=Criticity.objects.all()[0],
        )
        ticket1 = create_ticket(title='Test ticket #1')
        number1 = self.get_alone_element(TicketNumber.objects.all())
        self.assertEqual(number1.id, ticket1.number)

        ticket2 = create_ticket(title='Test ticket #2')
        self.assertNotEqual(ticket1.number, ticket2.number)

        self.get_alone_element(TicketNumber.objects.all())

    def test_get_resolving_duration01(self):
        "Resolving duration with CLOSED_PK + closing_date=None (e.g. CSV import)."
        user = self.login_as_root_and_get()

        get_status = Status.objects.get
        ticket = Ticket.objects.create(
            user=user,
            title='title',
            description='description',
            status=get_status(uuid=constants.UUID_STATUS_OPEN),
            priority=Priority.objects.all()[0],
            criticity=Criticity.objects.all()[0],
        )
        self.assertIsNone(ticket.closing_date)

        funf = function_field_registry.get(Ticket, 'get_resolving_duration')
        self.assertEqual('', funf(ticket, user).render(ViewTag.HTML_LIST))

        ticket.status = get_status(uuid=constants.UUID_STATUS_CLOSED)
        ticket.save()
        self.assertDatetimesAlmostEqual(now(), ticket.closing_date)
        self.assertEqual(
            timedelta_pprint(ticket.closing_date - ticket.created),
            funf(ticket, user).render(ViewTag.HTML_LIST),
        )

    def test_get_resolving_duration02(self):
        "Resolving duration with CLOSED_PK + closing_date=None (e.g. CSV import)."
        user = self.login_as_root_and_get()

        ticket = Ticket.objects.create(
            user=user,
            title='title',
            description='description',
            status=Status.objects.get(uuid=constants.UUID_STATUS_CLOSED),
            priority=Priority.objects.all()[0],
            criticity=Criticity.objects.all()[0],
        )

        funf = function_field_registry.get(Ticket, 'get_resolving_duration')
        self.assertEqual('?', funf(ticket, user).render(ViewTag.HTML_LIST))

    def test_editview01(self):
        user = self.login_as_root_and_get()

        ticket = Ticket.objects.create(
            user=user,
            title='title',
            description='description',
            status=Status.objects.get(uuid=constants.UUID_STATUS_OPEN),
            priority=Priority.objects.all()[0],
            criticity=Criticity.objects.all()[0],
        )

        url = ticket.get_edit_absolute_url()
        self.assertGET200(url)

        title = 'Test ticket'
        description = 'Test description'
        status = self.get_object_or_fail(Status, uuid=constants.UUID_STATUS_INVALID)
        priority = Priority.objects.all()[1]
        criticity = Criticity.objects.all()[1]
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':         user.pk,
                'title':        title,
                'description':  description,
                'status':       status.id,
                'priority':     priority.id,
                'criticity':    criticity.id,
            },
        )
        self.assertNoFormError(response)

        ticket = self.refresh(ticket)
        self.assertEqual(priority,     ticket.priority)
        self.assertEqual(criticity,    ticket.criticity)
        self.assertEqual(title,        ticket.title)
        self.assertEqual(description,  ticket.description)
        self.assertUUIDEqual(constants.UUID_STATUS_INVALID, ticket.status.uuid)
        self.assertFalse(ticket.closing_date)

        self.assertRedirects(response, ticket.get_absolute_url())

    def test_editview02(self):
        user = self.login_as_root_and_get()

        title = 'Test ticket'
        description = 'Test description'
        priority = Priority.objects.all()[0]
        criticity = Criticity.objects.all()[0]
        ticket = Ticket.objects.create(
            user=user,
            title=title,
            description=description,
            status=Status.objects.get(uuid=constants.UUID_STATUS_OPEN),
            priority=priority,
            criticity=criticity,
        )

        status = Status.objects.get(uuid=constants.UUID_STATUS_CLOSED)
        response = self.client.post(
            ticket.get_edit_absolute_url(),
            follow=True,
            data={
                'user':         user.pk,
                'title':        title,
                'description':  description,
                'status':       status.id,
                'priority':     priority.id,
                'criticity':    criticity.id,
            },
        )
        self.assertNoFormError(response)
        self.assertRedirects(response, ticket.get_absolute_url())

        ticket = self.refresh(ticket)
        self.assertUUIDEqual(constants.UUID_STATUS_CLOSED, ticket.status.uuid)

        self.assertTrue(ticket.closing_date)

        ffield = function_field_registry.get(Ticket, 'get_resolving_duration')(ticket, user)
        self.assertTrue(ffield.render(ViewTag.HTML_LIST))

    def test_editview03(self):
        "Custom closing status."
        user = self.login_as_root_and_get()

        status = Status.objects.create(
            name='Alternative closed',
            is_closed=True,
        )

        ticket = Ticket.objects.create(
            user=user,
            title='Test ticket',
            description='Test description',
            status=Status.objects.get(uuid=constants.UUID_STATUS_OPEN),
            priority=Priority.objects.all()[0],
            criticity=Criticity.objects.all()[0],
        )

        response = self.client.post(
            ticket.get_edit_absolute_url(),
            follow=True,
            data={
                'user':         user.pk,
                'title':        ticket.title,
                'description':  ticket.description,
                'status':       status.id,
                'priority':     ticket.priority_id,
                'criticity':    ticket.criticity_id,
            },
        )
        self.assertNoFormError(response)

        ticket = self.refresh(ticket)
        self.assertEqual(status, ticket.status)
        self.assertTrue(ticket.closing_date)

        ffield = function_field_registry.get(Ticket, 'get_resolving_duration')(ticket, user)
        self.assertTrue(ffield.render(ViewTag.HTML_LIST))

    def test_listview01(self):
        self.login_as_root()

        response = self.assertGET200(Ticket.get_lv_absolute_url())

        with self.assertNoException():
            tickets_page = response.context['page_obj']

        self.assertEqual(1, tickets_page.number)
        self.assertFalse(tickets_page.paginator.count)

    def test_listview02(self):
        user = self.login_as_root_and_get()

        Ticket.objects.create(
            user=user,
            title='title',
            description='description',
            status=Status.objects.get(uuid=constants.UUID_STATUS_OPEN),
            priority=Priority.objects.all()[0],
            criticity=Criticity.objects.all()[0],
        )

        response = self.assertGET200(Ticket.get_lv_absolute_url())

        with self.assertNoException():
            tickets_page = response.context['page_obj']

        self.assertEqual(1, tickets_page.paginator.count)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_deleteview(self):
        user = self.login_as_root_and_get()

        ticket = Ticket.objects.create(
            user=user,
            title='title',
            description='description',
            status=Status.objects.get(uuid=constants.UUID_STATUS_OPEN),
            priority=Priority.objects.all()[0],
            criticity=Criticity.objects.all()[0],
        )

        url = ticket.get_delete_absolute_url()
        self.assertTrue(url)
        response1 = self.assertPOST200(url, follow=True)

        with self.assertNoException():
            ticket = self.refresh(ticket)

        self.assertTrue(ticket.is_deleted)
        self.assertRedirects(response1, Ticket.get_lv_absolute_url())

        response2 = self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(ticket)
        self.assertRedirects(response2, Ticket.get_lv_absolute_url())

    def test_clone(self):
        "The cloned ticket is open."
        user = self.login_as_root_and_get()

        get_status = Status.objects.get
        status_open   = get_status(uuid=constants.UUID_STATUS_OPEN)
        status_closed = get_status(uuid=constants.UUID_STATUS_CLOSED)

        ticket = Ticket.objects.create(
            user=user,
            title='ticket',
            description='blablablabla',
            status=status_open,
            priority=Priority.objects.all()[0],
            criticity=Criticity.objects.all()[0],
        )

        ticket.status = status_closed
        ticket.save()
        self.assertIsNotNone(ticket.closing_date)

        cloned_ticket = self.clone(ticket)
        self.assertEqual(ticket.title, cloned_ticket.title)
        self.assertEqual(status_open, cloned_ticket.status)
        self.assertIsNone(cloned_ticket.closing_date)

    # def test_clone__method(self):  # DEPRECATED
    #     "The cloned ticket is open."
    #     user = self.login_as_root_and_get()
    #
    #     get_status = Status.objects.get
    #     status_open   = get_status(uuid=constants.UUID_STATUS_OPEN)
    #     status_closed = get_status(uuid=constants.UUID_STATUS_CLOSED)
    #
    #     ticket = Ticket.objects.create(
    #         user=user,
    #         title='ticket',
    #         description='blablablabla',
    #         status=status_open,
    #         priority=Priority.objects.all()[0],
    #         criticity=Criticity.objects.all()[0],
    #     )
    #
    #     ticket.status = status_closed
    #     ticket.save()
    #     self.assertIsNotNone(ticket.closing_date)
    #
    #     clone = ticket.clone()
    #     self.assertEqual(ticket.title, clone.title)
    #     self.assertEqual(status_open, clone.status)
    #     self.assertIsNone(clone.closing_date)

    def test_delete_status(self):
        user = self.login_as_root_and_get()

        status2 = Status.objects.first()
        status = Status.objects.create(name='Delete me please')
        ticket = Ticket.objects.create(
            user=user,
            title='title',
            description='description',
            status=status,
            priority=Priority.objects.all()[0],
            criticity=Criticity.objects.all()[0],
        )

        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('tickets', 'status', status.id),
            ),
            data={
                'replace_tickets__ticket_status':         status2.id,
                'replace_tickets__tickettemplate_status': status2.id,
            },
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Status).job
        job.type.execute(job)
        self.assertDoesNotExist(status)

        ticket = self.assertStillExists(ticket)
        self.assertEqual(status2, ticket.status)

    def test_delete_priority(self):
        user = self.login_as_root_and_get()

        priority2 = Priority.objects.first()
        priority = Priority.objects.create(name='Not so important')
        self.assertEqual(Priority.objects.count(), priority.order)

        ticket = Ticket.objects.create(
            user=user,
            title='title',
            description='description',
            status=Status.objects.all()[0],
            priority=priority,
            criticity=Criticity.objects.all()[0],
        )
        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('tickets', 'priority', priority.id)
            ),
            data={
                'replace_tickets__ticket_priority':         priority2.id,
                'replace_tickets__tickettemplate_priority': priority2.id,
            },
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Priority).job
        job.type.execute(job)
        self.assertDoesNotExist(priority)

        ticket = self.assertStillExists(ticket)
        self.assertEqual(priority2, ticket.priority)

    def test_delete_criticity(self):
        user = self.login_as_root_and_get()

        criticity2 = Criticity.objects.first()
        criticity = Criticity.objects.create(name='Not so important')
        self.assertEqual(Criticity.objects.count(), criticity.order)

        ticket = Ticket.objects.create(
            user=user,
            title='title',
            description='description',
            status=Status.objects.all()[0],
            priority=Priority.objects.all()[0],
            criticity=criticity,
        )
        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('tickets', 'criticity', criticity.id)
            ),
            data={
                'replace_tickets__ticket_criticity':         criticity2.id,
                'replace_tickets__tickettemplate_criticity': criticity2.id,
            },
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Criticity).job
        job.type.execute(job)
        self.assertDoesNotExist(criticity)

        ticket = self.assertStillExists(ticket)
        self.assertEqual(criticity2, ticket.criticity)

    def test_mass_import(self):
        user = self.login_as_root_and_get()

        count = Ticket.objects.count()

        titles = 'Ticket 01', 'Ticket 02'
        descriptions = 'Description #1', 'Description #2'
        status_l = Status.objects.all()[:2]
        priorities = Priority.objects.all()[:2]
        crits = Criticity.objects.all()[:2]

        lines = [
            (titles[0], status_l[0].name, priorities[0].name, crits[0].name, descriptions[0]),
            (titles[1], status_l[1].name, priorities[1].name, crits[1].name, descriptions[1]),
        ]

        doc = self._build_csv_doc(lines, user=user)
        url = self._build_import_url(Ticket)
        self.assertGET200(url)

        response = self.client.post(
            url, follow=True,
            data={
                'step':     1,
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
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual(count + len(lines), Ticket.objects.count())

        for i, l in enumerate(lines):
            ticket = self.get_object_or_fail(Ticket, title=titles[i])
            self.assertEqual(user,            ticket.user)
            self.assertEqual(status_l[i],     ticket.status)
            self.assertEqual(priorities[i],   ticket.priority)
            self.assertEqual(crits[i],  ticket.criticity)
            self.assertEqual(descriptions[i], ticket.description)
            self.assertEqual('',              ticket.solution)

        results = self._get_job_results(job)
        self.assertEqual(len(lines), len(results))
        self._assertNoResultError(results)

    @override_settings(TICKETS_COLOR_DELAY=7)
    def test_ticket_color(self):
        user = self.login_as_root_and_get()
        get_status = Status.objects.get
        create_ticket = partial(
            Ticket,
            user=user,
            title='My ticket',
            description='Test description',
            status=get_status(uuid=constants.UUID_STATUS_OPEN),
            priority=Priority.objects.all()[0],
            criticity=Criticity.objects.all()[0],
        )

        now_value = now()
        self.assertDictEqual(
            {}, create_ticket().get_html_attrs({'today': now_value}),
        )

        context = {'today': now_value + timedelta(days=8)}
        self.assertDictEqual(
            {'data-color': 'tickets-important'},
            create_ticket().get_html_attrs(context),
        )
        self.assertFalse(
            create_ticket(
                status=get_status(uuid=constants.UUID_STATUS_CLOSED),
            ).get_html_attrs(context),
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

    def test_detailview(self):
        user = self.login_as_root_and_get()
        self.assertGET200(self.create_template(user=user, title='Title').get_absolute_url())

    def test_edit(self):
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
    def test_create_entity01(self):
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
    def test_create_entity02(self):
        "status=CLOSED_PK."
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
    def test_create_entity03(self):
        "Several generations -> 'title' column must be unique."
        user = self.login_as_root_and_get()

        self.assertFalse(Ticket.objects.count())

        template = self.create_template(user=user, title='Title')

        with self.assertNoException():
            template.create_entity()
            template.create_entity()

        self.assertEqual(2, Ticket.objects.count())

    @skipIfCustomTicket
    def test_create_entity04(self):
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
