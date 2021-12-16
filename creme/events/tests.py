# -*- coding: utf-8 -*-

from functools import partial
from unittest import skipIf

from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme import persons
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.constants import DEFAULT_CURRENCY_PK
from creme.creme_core.models import (
    FieldsConfig,
    Relation,
    RelationType,
    SetCredentials,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.profiling import CaptureQueriesContext
from creme.opportunities import get_opportunity_model
from creme.opportunities.models import SalesPhase
from creme.opportunities.tests.base import skipIfCustomOpportunity
from creme.persons.constants import REL_SUB_EMPLOYED_BY
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from . import constants, event_model_is_custom, get_event_model
from .bricks import ResultsBrick
from .models import EventType
from .views.event import AddRelatedOpportunityAction

skip_event_tests = event_model_is_custom()
Event = get_event_model()

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()

Opportunity = get_opportunity_model()


def skipIfCustomEvent(test_func):
    return skipIf(skip_event_tests, 'Custom Event model in use')(test_func)


@skipIfCustomEvent
class EventsTestCase(BrickTestCaseMixin, CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.ADD_URL = reverse('events__create_event')

    @staticmethod
    def _build_invitation_url(event, contact):
        return reverse('events__set_invitation_status', args=(event.id, contact.id))

    @staticmethod
    def _build_link_contacts_url(event):
        return reverse('events__link_contacts', args=(event.id,))

    @staticmethod
    def _build_presence_url(event, contact):
        return reverse('events__set_presence_status', args=(event.id, contact.id))

    @staticmethod
    def _build_related_opp_url(event, contact):
        return reverse('events__create_related_opportunity', args=(event.id, contact.id))

    def test_populate(self):
        rtypes_pks = [
            constants.REL_SUB_IS_INVITED_TO,

            constants.REL_SUB_ACCEPTED_INVITATION,
            constants.REL_SUB_REFUSED_INVITATION,

            constants.REL_SUB_CAME_EVENT,
            constants.REL_SUB_NOT_CAME_EVENT
        ]
        rtypes = RelationType.objects.filter(pk__in=rtypes_pks)
        self.assertEqual(len(rtypes_pks), len(rtypes))

        self.assertTrue(EventType.objects.exists())

    def _create_event(self, name, etype=None, start_date='2010-11-3', **extra_data):
        etype = etype or EventType.objects.all()[0]

        self.assertNoFormError(self.client.post(
            self.ADD_URL,
            follow=True,
            data={
                'user':       self.user.id,
                'name':       name,
                'type':       etype.pk,
                'start_date': start_date,
                **extra_data
            },
        ))

        return self.get_object_or_fail(Event, name=name)

    def test_detailview(self):
        user = self.login()
        event = Event.objects.create(
            user=user, name='Eclipse',
            type=EventType.objects.all()[0],
            start_date=self.create_datetime(year=2021, month=11, day=15),
        )

        response = self.assertGET200(event.get_absolute_url())
        self.assertTemplateUsed(response, 'events/view_event.html')
        self.assertTemplateUsed(response, 'events/bricks/event-hat-bar.html')

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            ResultsBrick.id_,
        )
        self.assertEqual(_('Results'), self.get_brick_title(brick_node))

    def test_createview01(self):
        self.login()
        self.assertGET200(self.ADD_URL)

        etype = EventType.objects.all()[0]
        event = self._create_event('Eclipse', etype)

        self.assertEqual(1, Event.objects.count())
        self.assertEqual(etype, event.type)
        self.assertEqual(self.create_datetime(2010, 11, 3), event.start_date)
        self.assertIsNone(event.end_date)

    def test_createview02(self):
        "End data, hours."
        self.login()

        etype = EventType.objects.all()[1]
        event = self._create_event(
            'Comiket', etype,
            start_date='2016-7-25 8:00', end_date='2016-7-29 18:30',
        )
        self.assertEqual(etype, event.type)

        create_dt = self.create_datetime
        self.assertEqual(
            create_dt(year=2016, month=7, day=25, hour=8),
            event.start_date,
        )
        self.assertEqual(
            create_dt(year=2016, month=7, day=29, hour=18, minute=30),
            event.end_date,
        )

    def test_createview03(self):
        "start > end."
        user = self.login()
        etype = EventType.objects.all()[1]
        response = self.assertPOST200(
            self.ADD_URL, follow=True,
            data={
                'user':       user.pk,
                'name':       'Comicon',
                'type':       etype.pk,
                'start_date': '2016-7-29 8:00',
                'end_date':   '2016-7-28 18:30',
            },
        )
        self.assertFormError(
            response, 'form', 'end_date',
            _('The end date must be after the start date.'),
        )

    def test_createview04(self):
        "FieldsConfig: end is hidden."
        self.login()

        FieldsConfig.objects.create(
            content_type=Event,
            descriptions=[('end_date', {FieldsConfig.HIDDEN: True})],
        )

        event = self._create_event(
            'Comiket', start_date='2016-7-25 8:00', end_date='2016-7-29 18:30',
        )
        self.assertEqual(
            self.create_datetime(year=2016, month=7, day=25, hour=8),
            event.start_date,
        )
        self.assertIsNone(event.end_date)

    def test_editview(self):
        user = self.login()

        name = 'Eclipse'
        etype = EventType.objects.all()[0]
        event = self._create_event(name, etype)

        url = event.get_edit_absolute_url()
        self.assertGET200(url)

        name += '_edited'
        self.assertNoFormError(self.client.post(
            url, follow=True,
            data={
                'user':       user.pk,
                'name':       name,
                'type':       etype.pk,
                'start_date': '2010-11-4',
            },
        ))

        event = self.refresh(event)
        self.assertEqual(name, event.name)
        self.assertEqual(self.create_datetime(2010, 11, 4), event.start_date)

    def test_listview(self):
        self.login()

        etype = EventType.objects.all()[0]
        event1 = self._create_event('Eclipse', etype)
        event2 = self._create_event('Show', etype)

        response = self.assertGET200(Event.get_lv_absolute_url())

        with self.assertNoException():
            events_page = response.context['page_obj']

        self.assertEqual(2, events_page.paginator.count)
        self.assertSetEqual({event1, event2}, {*events_page.object_list})

    def test_listview_add_related_opport_action(self):
        user = self.login()
        event = self._create_event('Eclipse')
        casca = Contact.objects.create(first_name='Casca', last_name='Miura', user=user)

        action = AddRelatedOpportunityAction(
            user=user, model=Contact, instance=casca, event=event,
        )
        self.assertEqual('redirect', action.type)
        self.assertEqual(event, action.event)
        self.assertEqual(
            reverse('events__create_related_opportunity', args=(event.id, casca.id)),
            action.url,
        )
        self.assertTrue(action.is_visible)
        self.assertTrue(action.is_enabled)

    def test_stats01(self):
        self.login()

        event = self._create_event('Eclipse')
        stats = event.get_stats()

        self.assertEqual(4, len(stats))

        with self.assertNoException():
            stats_list = [
                stats['invitations_count'],
                stats['accepted_count'],
                stats['refused_count'],
                stats['visitors_count'],
            ]

        self.assertEqual([0] * 4, stats_list)

    @skipIfCustomContact
    def test_stats02(self):
        user = self.login()
        event = self._create_event('Eclipse')

        create_contact = partial(Contact.objects.create, user=user)
        casca    = create_contact(first_name='Casca',    last_name='Miura')
        judo     = create_contact(first_name='Judo',     last_name='Miura')
        griffith = create_contact(first_name='Griffith', last_name='Miura')
        rickert  = create_contact(first_name='Rickert',  last_name='Miura')
        # TODO ??
        #   carcus   = create_contact(first_name='Carcus',   last_name='Miura', is_deleted=True)

        def create_relation(subject, type_id):
            Relation.objects.create(
                subject_entity=subject,
                type_id=type_id,
                object_entity=event,
                user=user,
            )

        create_relation(casca,    constants.REL_SUB_IS_INVITED_TO)
        create_relation(judo,     constants.REL_SUB_IS_INVITED_TO)
        create_relation(griffith, constants.REL_SUB_IS_INVITED_TO)
        create_relation(rickert,  constants.REL_SUB_IS_INVITED_TO)

        create_relation(griffith, constants.REL_SUB_ACCEPTED_INVITATION)

        create_relation(casca,    constants.REL_SUB_REFUSED_INVITATION)
        create_relation(judo,     constants.REL_SUB_REFUSED_INVITATION)

        create_relation(casca,    constants.REL_SUB_CAME_EVENT)
        create_relation(judo,     constants.REL_SUB_CAME_EVENT)
        create_relation(griffith, constants.REL_SUB_CAME_EVENT)
        # create_relation(carcus,   constants.REL_SUB_CAME_EVENT)

        stats = event.get_stats()
        self.assertEqual(4, stats['invitations_count'])
        self.assertEqual(1, stats['accepted_count'])
        self.assertEqual(2, stats['refused_count'])
        self.assertEqual(3, stats['visitors_count'])

    def _set_invitation_status(self, event, contact, status_id):
        self.client.post(
            self._build_invitation_url(event, contact),
            data={'status': status_id},
        )

    @skipIfCustomContact
    def test_set_invitation_status01(self):
        user = self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=user, first_name='Casca', last_name='Miura')

        stats = event.get_stats()
        self.assertEqual(0, stats['invitations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])
        self.assertEqual(0, stats['visitors_count'])

        url = self._build_invitation_url(event, casca)
        self.assertPOST404(url, data={'status': 'not_an_int'})
        self.assertGET405(url, data={'status': constants.INV_STATUS_NO_ANSWER})
        self.assertPOST200(url, data={'status': constants.INV_STATUS_NO_ANSWER})

        stats = event.get_stats()
        self.assertEqual(1, stats['invitations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])
        self.assertEqual(0, stats['visitors_count'])

        self.assertPOST200(url, data={'status': constants.INV_STATUS_NOT_INVITED})

        stats = event.get_stats()
        self.assertEqual(0, stats['invitations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])
        self.assertEqual(0, stats['visitors_count'])

    @skipIfCustomContact
    def test_set_invitation_status02(self):
        user = self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=user, first_name='Casca', last_name='Miura')

        url = self._build_invitation_url(event, casca)
        self.assertPOST200(url, data={'status': constants.INV_STATUS_ACCEPTED})

        stats = event.get_stats()
        self.assertEqual(1, stats['invitations_count'])
        self.assertEqual(1, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])

        self.client.post(url, data={'status': constants.INV_STATUS_NOT_INVITED})
        stats = event.get_stats()
        self.assertEqual(0, stats['invitations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])

    @skipIfCustomContact
    def test_set_invitation_status03(self):
        user = self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=user, first_name='Casca', last_name='Miura')

        self._set_invitation_status(event, casca, constants.INV_STATUS_REFUSED)
        stats = event.get_stats()
        self.assertEqual(1, stats['invitations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(1, stats['refused_count'])

        self._set_invitation_status(event, casca, constants.INV_STATUS_NOT_INVITED)
        stats = event.get_stats()
        self.assertEqual(0, stats['invitations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])

    @skipIfCustomContact
    def test_set_invitation_status04(self):
        user = self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=user, first_name='Casca', last_name='Miura')

        self._set_invitation_status(event, casca, constants.INV_STATUS_ACCEPTED)
        self._set_invitation_status(event, casca, constants.INV_STATUS_REFUSED)
        stats = event.get_stats()
        self.assertEqual(1, stats['invitations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(1, stats['refused_count'])

        self._set_invitation_status(event, casca, constants.INV_STATUS_NO_ANSWER)
        stats = event.get_stats()
        self.assertEqual(1, stats['invitations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])

    @skipIfCustomContact
    def test_set_invitation_status05(self):
        user = self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=user, first_name='Casca', last_name='Miura')

        self._set_invitation_status(event, casca, constants.INV_STATUS_REFUSED)
        self._set_invitation_status(event, casca, constants.INV_STATUS_ACCEPTED)
        stats = event.get_stats()
        self.assertEqual(1, stats['invitations_count'])
        self.assertEqual(1, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])

    @skipIfCustomContact
    def test_set_invitation_status06(self):
        "Credentials errors"
        user = self.login(is_superuser=False, allowed_apps=['persons', 'events'])
        other_user = self.other_user

        create_creds = partial(SetCredentials.objects.create, role=user.role)
        create_creds(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )
        create_creds(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
            ),  # No LINK
            set_type=SetCredentials.ESET_ALL,
        )

        create_contact = Contact.objects.create

        def _create_event(user, name):
            return Event.objects.create(
                user=user, name=name, start_date=now(),
                type=EventType.objects.all()[0],
            )

        event = _create_event(user=user, name='Eclipse 01')
        casca = create_contact(user=other_user, first_name='Casca', last_name='Miura')
        self.assertTrue(user.has_perm_to_link(event))
        self.assertFalse(user.has_perm_to_link(casca))
        self.assertPOST403(
            self._build_invitation_url(event, casca),
            data={'status': constants.INV_STATUS_REFUSED},
        )

        event = _create_event(user=other_user, name='Eclipse 02')
        guts = create_contact(user=user, first_name='Guts', last_name='Miura')
        self.assertFalse(user.has_perm_to_link(event))
        self.assertTrue(user.has_perm_to_link(guts))
        self.assertPOST403(
            self._build_invitation_url(event, guts),
            data={'status': constants.INV_STATUS_REFUSED},
        )

    def _set_presence_status(self, event, contact, status_id):
        return self.client.post(
            self._build_presence_url(event, contact),
            data={'status': status_id},
        )

    @skipIfCustomContact
    def test_set_presence_status01(self):
        user = self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=user, first_name='Casca', last_name='Miura')

        self.assertEqual(
            200,
            self._set_presence_status(
                event, casca, constants.PRES_STATUS_COME,
            ).status_code,
        )

        with CaptureQueriesContext() as ctxt:
            stats = event.get_stats()

        self.assertEqual(1, len(ctxt.captured_sql))
        self.assertNotIn(' ORDER BY ', ctxt.captured_sql[0])

        self.assertEqual(0, stats['invitations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])
        self.assertEqual(1, stats['visitors_count'])

        self._set_presence_status(event, casca, constants.PRES_STATUS_DONT_KNOW)
        self.assertEqual(0, event.get_stats()['visitors_count'])
        self.assertRelationCount(0, casca, constants.REL_SUB_NOT_CAME_EVENT, event)

    @skipIfCustomContact
    def test_set_presence_status02(self):
        user = self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=user, first_name='Casca', last_name='Miura')

        self._set_presence_status(event, casca, constants.PRES_STATUS_COME)
        self.assertEqual(1, event.get_stats()['visitors_count'])

        self._set_presence_status(event, casca, constants.PRES_STATUS_NOT_COME)
        self.assertEqual(0, event.get_stats()['visitors_count'])
        self.assertRelationCount(1, casca, constants.REL_SUB_NOT_CAME_EVENT, event)

        self._set_presence_status(event, casca, constants.PRES_STATUS_DONT_KNOW)
        self.assertEqual(0, event.get_stats()['visitors_count'])
        self.assertRelationCount(0, casca, constants.REL_SUB_NOT_CAME_EVENT, event)

    @skipIfCustomContact
    def test_set_presence_status03(self):
        user = self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=user, first_name='Casca', last_name='Miura')

        self._set_presence_status(event, casca, constants.PRES_STATUS_NOT_COME)
        self.assertEqual(0, event.get_stats()['visitors_count'])
        self.assertRelationCount(1, casca, constants.REL_SUB_NOT_CAME_EVENT, event)

        self._set_presence_status(event, casca, constants.PRES_STATUS_COME)
        self.assertEqual(1, event.get_stats()['visitors_count'])
        self.assertRelationCount(0, casca, constants.REL_SUB_NOT_CAME_EVENT, event)

    @skipIfCustomContact
    def test_set_presence_status04(self):
        "Credentials errors"
        user = self.login(is_superuser=False, allowed_apps=['persons', 'events'])
        other_user = self.other_user

        create_creds = partial(SetCredentials.objects.create, role=user.role)
        create_creds(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )
        create_creds(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
            ),  # No LINK
            set_type=SetCredentials.ESET_ALL,
        )

        etype = EventType.objects.all()[0]
        _create_event = Event.objects.create
        create_contact = Contact.objects.create

        event = _create_event(user=user, name='Eclipse 01', type=etype, start_date=now())
        casca = create_contact(user=other_user, first_name='Casca', last_name='Miura')
        self.assertTrue(user.has_perm_to_link(event))
        self.assertFalse(user.has_perm_to_link(casca))
        self.assertPOST403(
            self._build_presence_url(event, casca),
            data={'status': constants.PRES_STATUS_COME},
        )

        event = _create_event(user=other_user, name='Eclipse 02', type=etype, start_date=now())
        guts = create_contact(user=user, first_name='Guts', last_name='Miura')
        self.assertFalse(user.has_perm_to_link(event))
        self.assertTrue(user.has_perm_to_link(guts))
        self.assertPOST403(
            self._build_presence_url(event, guts),
            data={'status': constants.PRES_STATUS_COME},
        )

    @skipIfCustomContact
    def test_list_contacts(self):
        user = self.login()

        event1 = self._create_event('Eclipse')
        event2 = self._create_event('Coronation')

        create_contact = partial(Contact.objects.create, user=user)
        casca     = create_contact(first_name='Casca',     last_name='Miura')
        judo      = create_contact(first_name='Judo',      last_name='Miura')
        griffith  = create_contact(first_name='Griffith',  last_name='Miura')
        charlotte = create_contact(first_name='Charlotte', last_name='Miura')

        self._set_presence_status(event1, casca, constants.PRES_STATUS_COME)
        self._set_invitation_status(event1, judo, constants.INV_STATUS_NO_ANSWER)
        self._set_invitation_status(event1, griffith, constants.INV_STATUS_ACCEPTED)

        self._set_presence_status(event2, griffith,  constants.PRES_STATUS_COME)
        self._set_presence_status(event2, charlotte, constants.PRES_STATUS_COME)

        response = self.assertGET200(reverse('events__list_related_contacts', args=(event1.id,)))

        with self.assertNoException():
            contacts_page = response.context['page_obj']

        self.assertEqual(3, contacts_page.paginator.count)
        self.assertSetEqual({casca, judo, griffith}, {*contacts_page.object_list})

    @staticmethod
    def relations_types(contact, event):
        return [
            *Relation.objects
                     .filter(subject_entity=contact, object_entity=event)
                     .values_list('type_id', flat=True),
        ]

    @skipIfCustomContact
    def test_link_contacts01(self):
        user = self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=user, first_name='Casca', last_name='Miura')

        url = self._build_link_contacts_url(event)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link.html')
        self.assertEqual(
            _('Link some contacts to «{object}»').format(object=event),
            response.context.get('title'),
        )
        self.assertEqual(_('Link these contacts'), response.context.get('submit_label'))

        cb_url = reverse('events__list_related_contacts', args=(event.id,))
        response = self.client.post(
            url, follow=True,
            data={
                'related_contacts': self.formfield_value_multi_relation_entity(
                    (constants.REL_OBJ_CAME_EVENT, casca),
                ),
                'callback_url': cb_url,
            },
        )
        self.assertNoFormError(response)
        self.assertListEqual(
            [constants.REL_SUB_CAME_EVENT], self.relations_types(casca, event),
        )
        # self.assertRedirects(
        #     response, reverse('events__list_related_contacts', args=(event.id,)),
        # )
        self.assertRedirects(response, cb_url)

    @skipIfCustomContact
    def test_link_contacts02(self):
        user = self.login()
        event = self._create_event('Eclipse')

        create_contact = partial(Contact.objects.create, user=user)
        casca    = create_contact(first_name='Casca',    last_name='Miura')
        judo     = create_contact(first_name='Judo',     last_name='Miura')
        griffith = create_contact(first_name='Griffith', last_name='Miura')
        rickert  = create_contact(first_name='Rickert',  last_name='Miura')
        carcus   = create_contact(first_name='Carcus',   last_name='Miura')

        response = self.client.post(
            self._build_link_contacts_url(event), follow=True,
            data={
                'related_contacts': self.formfield_value_multi_relation_entity(
                    (constants.REL_OBJ_IS_INVITED_TO,  casca),
                    (constants.REL_OBJ_CAME_EVENT,     judo),
                    (constants.REL_OBJ_NOT_CAME_EVENT, griffith),
                    (constants.REL_OBJ_IS_INVITED_TO,  rickert),
                    (constants.REL_OBJ_CAME_EVENT,     carcus),
                ),
            },
        )
        self.assertNoFormError(response)

        self.assertListEqual(
            [constants.REL_SUB_IS_INVITED_TO],
            self.relations_types(casca, event),
        )
        self.assertListEqual(
            [constants.REL_SUB_CAME_EVENT],
            self.relations_types(judo, event),
        )
        self.assertListEqual(
            [constants.REL_SUB_NOT_CAME_EVENT],
            self.relations_types(griffith, event),
        )
        self.assertListEqual(
            [constants.REL_SUB_IS_INVITED_TO],
            self.relations_types(rickert, event),
        )
        self.assertListEqual(
            [constants.REL_SUB_CAME_EVENT],
            self.relations_types(carcus, event),
        )

        response = self.client.post(
            self._build_link_contacts_url(event),
            follow=True,
            data={
                'related_contacts': self.formfield_value_multi_relation_entity(
                    (constants.REL_OBJ_IS_INVITED_TO,  casca),
                    (constants.REL_OBJ_NOT_CAME_EVENT, judo),
                    (constants.REL_OBJ_CAME_EVENT,     griffith),
                    (constants.REL_OBJ_CAME_EVENT,     rickert),
                    (constants.REL_OBJ_CAME_EVENT,     carcus),
                ),
            },
        )
        self.assertNoFormError(response)

        self.assertListEqual(
            [constants.REL_SUB_IS_INVITED_TO],
            self.relations_types(casca, event),
        )
        self.assertListEqual(
            [constants.REL_SUB_NOT_CAME_EVENT],
            self.relations_types(judo, event),
        )
        self.assertListEqual(
            [constants.REL_SUB_CAME_EVENT],
            self.relations_types(griffith, event),
        )
        self.assertSetEqual(
            {constants.REL_SUB_IS_INVITED_TO, constants.REL_SUB_CAME_EVENT},
            {*self.relations_types(rickert, event)},
        )
        self.assertListEqual(
            [constants.REL_SUB_CAME_EVENT],
            self.relations_types(carcus, event),
        )

    @skipIfCustomContact
    def test_link_contacts03(self):
        user = self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=user, first_name='Casca', last_name='Miura')

        response = self.assertPOST200(
            self._build_link_contacts_url(event),
            follow=True,
            data={
                'related_contacts': self.formfield_value_multi_relation_entity(
                    (constants.REL_OBJ_IS_INVITED_TO, casca),
                    (constants.REL_OBJ_CAME_EVENT,    casca),
                ),
            },
        )
        self.assertFormError(
            response, 'form', 'related_contacts',
            _('Contact %(contact)s is present twice.') % {'contact': casca},
        )

    @skipIfCustomContact
    def test_link_contacts04(self):
        "Link credentials error."
        user = self.login(is_superuser=False, allowed_apps=['persons', 'events'])

        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
                # | EntityCredentials.LINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

        event = Event.objects.create(
            user=user, name='Eclipse',
            type=EventType.objects.all()[0],
            start_date=now(),
        )
        casca = Contact.objects.create(user=user, first_name='Casca', last_name='Miura')
        url = self._build_link_contacts_url(event)
        self.assertGET200(url)

        response = self.assertPOST200(
            url,
            follow=True,
            data={
                'related_contacts': self.formfield_value_multi_relation_entity(
                    (constants.REL_OBJ_IS_INVITED_TO, casca),
                ),
            },
        )
        self.assertFormError(
            response, 'form', 'related_contacts',
            _('Some entities are not linkable: {}').format(casca),
        )

    def test_delete_type(self):
        self.login()
        etype = EventType.objects.create(name='Natural')
        etype2 = EventType.objects.exclude(id=etype.id)[0]

        event = self._create_event('Eclipse', etype)

        self.assertNoFormError(self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('events', 'event_type', etype.id),
            ),
            data={'replace_events__event_type': etype2.id},
        ))

        job = self.get_deletion_command_or_fail(EventType).job
        job.type.execute(job)
        self.assertDoesNotExist(etype)

        event = self.assertStillExists(event)
        self.assertEqual(etype2, event.type)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    @skipIfCustomOpportunity
    def test_related_opportunity01(self):
        "Contact is not related to an Organisation."
        user = self.login()

        name = 'Opp01'
        self.assertFalse(Opportunity.objects.filter(name=name))

        casca = Contact.objects.create(user=user, first_name='Casca', last_name='Miura')
        event = Event.objects.create(
            user=user, name='Eclipse', type=EventType.objects.all()[0], start_date=now(),
        )

        url = self._build_related_opp_url(event, casca)
        response = self.assertGET200(url)
        context = response.context
        self.assertEqual(
            _('Create an opportunity related to «{contact}»').format(contact=casca),
            context.get('title'),
        )
        self.assertEqual(Opportunity.save_label, context.get('submit_label'))

        with self.assertNoException():
            # target_f = context['form'].fields['target']
            target_f = context['form'].fields['cform_extra-opportunities_target']

        self.assertTrue(target_f.help_text)

        emitter = Organisation.objects.create(user=user, name='My society', is_managed=True)

        phase = SalesPhase.objects.all()[0]
        response = self.client.post(
            url, follow=True,
            data={
                'user':        user.id,
                'name':        name,
                'sales_phase': phase.id,
                'currency':    DEFAULT_CURRENCY_PK,

                'cform_extra-opportunities_target': self.formfield_value_generic_entity(casca),
                'cform_extra-opportunities_emitter': emitter.id,
            },
        )
        self.assertNoFormError(response)

        opp = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(phase, opp.sales_phase)
        self.assertRelationCount(1, opp, constants.REL_SUB_GEN_BY_EVENT, event)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    @skipIfCustomOpportunity
    def test_related_opportunity02(self):
        "Contact is related to an Organisation."
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        emitter = create_orga(name='My society', is_managed=True)
        hawks   = create_orga(name='Hawks')
        rhino   = create_orga(name='Rhino')  # No related to the contact

        casca = Contact.objects.create(user=user, first_name='Casca', last_name='Miura')
        Relation.objects.create(
            user=user,
            subject_entity=casca,
            type_id=REL_SUB_EMPLOYED_BY,
            object_entity=hawks,
        )

        event = Event.objects.create(
            user=user, name='Eclipse', type=EventType.objects.all()[0], start_date=now(),
        )

        url = self._build_related_opp_url(event, casca)
        response = self.assertGET200(url)

        with self.assertNoException():
            target_f = response.context['form'].fields['cform_extra-opportunities_target']

        self.assertFalse(target_f.help_text)

        name = 'Opp01'
        data = {
            'user':        user.pk,
            'name':        name,
            'sales_phase': SalesPhase.objects.all()[0].id,
            'currency':    DEFAULT_CURRENCY_PK,

            'cform_extra-opportunities_target': rhino.id,
            'cform_extra-opportunities_emitter': emitter.id,
        }

        response = self.assertPOST200(url, follow=True, data=data)
        self.assertFormError(
            response, 'form', 'cform_extra-opportunities_target',
            _('Select a valid choice. That choice is not one of the available choices.'),
        )

        data['cform_extra-opportunities_target'] = hawks.id
        response = self.client.post(url, follow=True, data=data)
        self.assertNoFormError(response)

        opp = self.get_object_or_fail(Opportunity, name=name)
        self.assertRelationCount(1, opp, constants.REL_SUB_GEN_BY_EVENT, event)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    @skipIfCustomOpportunity
    def test_related_opportunity03(self):
        """Opportunity.description is hidden."""
        user = self.login()

        FieldsConfig.objects.create(
            content_type=Opportunity,
            descriptions=[('description', {FieldsConfig.HIDDEN: True})],
        )

        casca = Contact.objects.create(user=user, first_name='Casca', last_name='Miura')
        event = Event.objects.create(
            user=user, name='Eclipse', type=EventType.objects.first(), start_date=now(),
        )

        emitter = Organisation.objects.create(user=user, name='My society', is_managed=True)

        name = 'Opp01'
        response = self.client.post(
            self._build_related_opp_url(event, casca), follow=True,
            data={
                'user':        user.id,
                'name':        name,
                'sales_phase': SalesPhase.objects.first().id,
                'currency':    DEFAULT_CURRENCY_PK,

                'cform_extra-opportunities_target': self.formfield_value_generic_entity(casca),
                'cform_extra-opportunities_emitter': emitter.id,
            },
        )
        self.assertNoFormError(response)

        opp = self.get_object_or_fail(Opportunity, name=name)
        self.assertFalse(opp.description)

    @skipIfCustomContact
    @skipIfCustomOpportunity
    def test_related_opportunity04(self):
        "Not super-user."
        user = self.login(
            is_superuser=False,
            allowed_apps=['persons', 'opportunities', 'events'],
            creatable_models=[Opportunity],
        )
        SetCredentials.objects.create(
            role=user.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL,
        )

        casca = Contact.objects.create(user=user, first_name='Casca', last_name='Miura')
        event = Event.objects.create(
            user=user, name='Eclipse', type=EventType.objects.all()[0], start_date=now(),
        )
        self.assertGET200(self._build_related_opp_url(event, casca))

    @skipIfCustomContact
    @skipIfCustomOpportunity
    def test_related_opportunity05(self):
        "Creation permission needed."
        user = self.login(
            is_superuser=False,
            allowed_apps=['persons', 'opportunities', 'events'],
            # creatable_models=[Opportunity],
        )
        SetCredentials.objects.create(
            role=user.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.LINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        casca = Contact.objects.create(user=user, first_name='Casca', last_name='Miura')
        event = Event.objects.create(
            user=user, name='Eclipse', type=EventType.objects.all()[0], start_date=now(),
        )
        self.assertGET403(self._build_related_opp_url(event, casca))

    @skipIfCustomContact
    @skipIfCustomOpportunity
    def test_related_opportunity06(self):
        "LINK permission is needed."
        user = self.login(
            is_superuser=False,
            allowed_apps=['persons', 'opportunities', 'events'],
            creatable_models=[Opportunity],
        )
        SetCredentials.objects.create(
            role=user.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE,  # EntityCredentials.LINK
            set_type=SetCredentials.ESET_ALL,
        )

        casca = Contact.objects.create(user=user, first_name='Casca', last_name='Miura')
        event = Event.objects.create(
            user=user, name='Eclipse', type=EventType.objects.all()[0], start_date=now(),
        )
        self.assertGET403(self._build_related_opp_url(event, casca))

    @skipIfCustomContact
    @skipIfCustomOpportunity
    def test_related_opportunity07(self):
        "Contact must be viewable."
        user = self.login(
            is_superuser=False,
            allowed_apps=['persons', 'opportunities', 'events'],
            creatable_models=[Opportunity],
        )
        SetCredentials.objects.create(
            role=user.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.LINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

        casca = Contact.objects.create(
            user=self.other_user, first_name='Casca', last_name='Miura',
        )
        event = Event.objects.create(
            user=user, name='Eclipse', type=EventType.objects.all()[0], start_date=now(),
        )
        url = self._build_related_opp_url(event, casca)
        self.assertGET403(url)

        casca.user = user
        casca.save()
        self.assertGET200(url)
