# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from typing import Type

from django.db.models import Q
from django.forms.forms import BaseForm
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.actions import ViewAction
# from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.entity_cell import EntityCellRelation
from creme.creme_core.gui.actions import EntityAction
from creme.creme_core.gui import listview as lv_gui
from creme.creme_core.models import RelationType
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic
from creme.creme_core.views.generic.base import EntityRelatedMixin

from creme.persons import get_contact_model
from creme.persons.views.contact import ContactsList

from creme.opportunities import get_opportunity_model

from .. import constants, get_event_model, gui
from ..forms import event as event_forms
from ..models import EventType

Contact = get_contact_model()
Event   = get_event_model()
Opportunity = get_opportunity_model()


class AddRelatedOpportunityAction(EntityAction):
    id = EntityAction.generate_id('events', 'create_related_opportunity')
    model = Contact

    type = 'redirect'
    url_name = 'events__create_related_opportunity'

    label = _('Create an opportunity')
    icon = 'opportunity'

    def __init__(self, event, **kwargs):
        super().__init__(**kwargs)
        self.event = event

    @property
    def url(self):
        return reverse(self.url_name, args=(self.event.id, self.instance.id))

    @property
    def is_enabled(self):
        user = self.user

        return user.has_perm_to_create(Opportunity) and \
               user.has_perm_to_link(self.event)


# def _get_status(request, valid_status):
#     status_str = get_from_POST_or_404(request.POST, 'status')
#
#     try:
#         status = int(status_str)
#     except Exception as e:
#         raise Http404('Status is not an integer: {}'.format(status_str)) from e
#
#     if not status in valid_status:
#         raise Http404('Unknown status: {}'.format(status))
#
#     return status
#
#
# def _get_event_n_contact(event_id, contact_id, user):
#     event   = get_object_or_404(Event, pk=event_id)
#     contact = get_object_or_404(Contact, pk=contact_id)
#
#     has_perm_or_die = user.has_perm_to_link_or_die
#     has_perm_or_die(event)
#     has_perm_or_die(contact)
#
#     return event, contact
#
#
# @login_required
# @permission_required('events')
# def set_invitation_status(request, event_id, contact_id):
#     status = _get_status(request, constants.INV_STATUS_MAP)
#     user = request.user
#     event, contact = _get_event_n_contact(event_id, contact_id, user)
#
#     event.set_invitation_status(contact, status, user)
#
#     return HttpResponse()
#
#
# @login_required
# @permission_required('events')
# def set_presence_status(request, event_id, contact_id):
#     status = _get_status(request, constants.PRES_STATUS_MAP)
#     user = request.user
#     event, contact = _get_event_n_contact(event_id, contact_id, user)
#
#     event.set_presence_status(contact, status, user)
#
#     return HttpResponse()


class EventCreation(generic.EntityCreation):
    model = Event
    form_class = event_forms.EventForm

    def get_initial(self):
        initial = super().get_initial()
        initial['type'] = EventType.objects.first()

        return initial


class EventDetail(generic.EntityDetail):
    model = Event
    template_name = 'events/view_event.html'
    pk_url_kwarg = 'event_id'


class EventEdition(generic.EntityEdition):
    model = Event
    form_class = event_forms.EventForm
    pk_url_kwarg = 'event_id'


class EventsList(generic.EntitiesList):
    model = Event
    default_headerfilter_id = constants.DEFAULT_HFILTER_EVENT


class RelatedContactsList(EntityRelatedMixin, ContactsList):
    entity_id_url_kwarg = 'event_id'
    entity_classes = Event

    title = _('List of contacts related to «{event}»')

    RTYPE_IDS = (
        constants.REL_SUB_IS_INVITED_TO,
        constants.REL_SUB_ACCEPTED_INVITATION,
        constants.REL_SUB_REFUSED_INVITATION,
        constants.REL_SUB_CAME_EVENT,
        constants.REL_SUB_NOT_CAME_EVENT,
    )

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_view_or_die(entity)  # NB: entity == event

    def get_actions_registry(self):
        view_action_class = next(
            (c for c in self.actions_registry.instance_action_classes(model=Contact)
                if (issubclass(c, ViewAction))
            ),
            None
        )

        registry = gui.RelatedContactsActionsRegistry(event=self.get_related_entity())
        registry.register_instance_actions(AddRelatedOpportunityAction)

        if view_action_class is not None:
            registry.register_instance_actions(view_action_class)

        return registry

    def get_buttons(self):
        # TODO: let BatchProcessButton when it manages the internal Q
        # TODO: let MassImportButton when we can set a fixed relation to the event
        # TODO: let MassExportHeaderButton when MassImportButton is here
        return super().get_buttons()\
                      .update_context(event_entity=self.get_related_entity()) \
                      .insert(0, gui.EventDetailButton) \
                      .replace(old=lv_gui.CreationButton, new=gui.AddContactsButton) \
                      .remove(lv_gui.BatchProcessButton) \
                      .remove(lv_gui.MassImportButton) \
                      .remove(lv_gui.MassExportHeaderButton)

    def get_cells(self, hfilter):
        cells = super().get_cells(hfilter=hfilter)

        rtypes = RelationType.objects.filter(pk__in=self.RTYPE_IDS)

        # NB: add relations items to use the pre-cache system of HeaderFilter
        #     (TODO: problem: retrieve other related events too)
        cells.extend(EntityCellRelation(model=Contact, rtype=rtype, is_hidden=True) for rtype in rtypes)

        event = self.get_related_entity()
        cells.append(gui.EntityCellVolatileInvitation(event=event))
        cells.append(gui.EntityCellVolatilePresence(event=event))

        return cells

    def get_internal_q(self):
        return Q(relations__type__in=self.RTYPE_IDS,
                 relations__object_entity=self.get_related_entity().id,
                )

    def get_title_format_data(self):
        return {
            'event': self.get_related_entity(),
        }


class AddContactsToEvent(generic.EntityEdition):
    model = Event
    form_class: Type[BaseForm] = event_forms.AddContactsToEventForm
    template_name = 'creme_core/generics/blockform/link.html'
    pk_url_kwarg = 'event_id'
    title = _('Link some contacts to «{object}»')
    submit_label = _('Link these contacts')

    # TODO: use a "?next=" GET argument ?
    def get_success_url(self):
        return reverse('events__list_related_contacts', args=(self.object.id,))


class RelatedOpportunityCreation(generic.EntityCreation):
    model = Opportunity
    form_class = event_forms.RelatedOpportunityCreateForm
    permissions = 'events'
    title = _('Create an opportunity related to «{contact}»')
    event_id_url_kwarg = 'event_id'
    contact_id_url_kwarg = 'contact_id'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = None
        self.contact = None

    def get_contact(self):
        contact = self.contact
        if contact is None:
            self.contact = contact = \
                get_object_or_404(Contact, pk=self.kwargs[self.contact_id_url_kwarg])
            self.request.user.has_perm_to_view_or_die(contact)

        return contact

    def get_event(self):
        event = self.event
        if event is None:
            self.event = event = \
                get_object_or_404(Event, pk=self.kwargs[self.event_id_url_kwarg])
            self.request.user.has_perm_to_link_or_die(event)

        return event

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['event']   = self.get_event()
        kwargs['contact'] = self.get_contact()

        return kwargs

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['contact'] = self.get_contact()
        # data['event'] = self.get_event()  TODO ?

        return data


class BaseStatusSetting(generic.CheckedView):
    permissions = 'events'
    status_map = constants.INV_STATUS_MAP
    status_arg = 'status'
    event_id_url_kwarg = 'event_id'
    contact_id_url_kwarg = 'contact_id'

    def check_contact_permissions(self, contact, user):
        user.has_perm_to_link_or_die(contact)

    def check_event_permissions(self, event, user):
        user.has_perm_to_link_or_die(event)

    def get_contact(self):
        contact = get_object_or_404(Contact, pk=self.kwargs[self.contact_id_url_kwarg])
        self.check_contact_permissions(contact, self.request.user)

        return contact

    def get_event(self):
        event = get_object_or_404(Event, pk=self.kwargs[self.event_id_url_kwarg])
        self.check_event_permissions(event, self.request.user)

        return event

    def get_status(self):
        status = get_from_POST_or_404(self.request.POST, self.status_arg, cast=int)

        if status not in self.status_map:
            raise Http404(f'Unknown status: {status}')

        return status

    def post(self, *args, **kwargs):
        self.update(
            status=self.get_status(),
            event=self.get_event(),
            contact=self.get_contact(),
        )

        return HttpResponse()

    def update(self, *, event, contact, status):
        raise NotImplementedError()


class InvitationStatusSetting(BaseStatusSetting):
    def update(self, *, event, contact, status):
        event.set_invitation_status(contact=contact, status=status, user=self.request.user)


class PresenceStatusSetting(BaseStatusSetting):
    def update(self, *, event, contact, status):
        event.set_presence_status(contact=contact, status=status, user=self.request.user)