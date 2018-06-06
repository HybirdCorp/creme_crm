# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext_lazy

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.entity_cell import EntityCellRelation, EntityCellVolatile
from creme.creme_core.models import RelationType
from creme.creme_core.models.entity import EntityAction
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views.generic import add_entity, edit_entity, view_entity, list_view

from creme.persons import get_contact_model

from creme.opportunities import get_opportunity_model

from .. import get_event_model
from .. import constants
from ..forms.event import EventForm, AddContactsToEventForm, RelatedOpportunityCreateForm
from ..models import EventType


Contact = get_contact_model()
Event   = get_event_model()
Opportunity = get_opportunity_model()


def abstract_add_event(request, form=EventForm,
                       submit_label=Event.save_label,
                      ):
    return add_entity(request, form,
                      extra_initial={'type': EventType.objects.first()},
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_edit_event(request, event_id, form=EventForm):
    return edit_entity(request, event_id, Event, form)


def abstract_view_event(request, event_id,
                        template='events/view_event.html',
                       ):
    return view_entity(request, event_id, Event, template=template)


@login_required
@permission_required(('events', cperm(Event)))
def add(request):
    return abstract_add_event(request)


@login_required
@permission_required('events')
def edit(request, event_id):
    return abstract_edit_event(request, event_id)


@login_required
@permission_required('events')
def detailview(request, event_id):
    return abstract_view_event(request, event_id)


@login_required
@permission_required('events')
def listview(request):
    return list_view(request, Event, hf_pk=constants.DEFAULT_HFILTER_EVENT)


INV_STATUS_MAP = {
        constants.INV_STATUS_NOT_INVITED: _(u'Not invited'),
        constants.INV_STATUS_NO_ANSWER:   _(u'Did not answer'),
        constants.INV_STATUS_ACCEPTED:    _(u'Accepted the invitation'),
        constants.INV_STATUS_REFUSED:     _(u'Refused the invitation'),
    }

PRES_STATUS_MAP = {
        constants.PRES_STATUS_DONT_KNOW: _(u'N/A'),
        constants.PRES_STATUS_COME:      pgettext_lazy('events-presence_status', u'Come'),
        constants.PRES_STATUS_NOT_COME:  pgettext_lazy('events-presence_status', u'Not come'),
    }


def build_get_actions(event, entity):
    """Build bound method to overload 'get_actions()' method of CremeEntities"""
    def _get_actions(user):
        return {'default': EntityAction(entity.get_absolute_url(), ugettext(u'See'),
                                        user.has_perm_to_view(entity),
                                        icon='view',
                                       ),
                'others':  [EntityAction(reverse('events__create_related_opportunity',
                                                 args=(event.id, entity.id),
                                                ),
                                         ugettext(u'Create an opportunity'),
                                         user.has_perm(cperm(Opportunity)) and user.has_perm_to_link(event),
                                         icon='opportunity',
                                        ),
                           ]
               }

    return _get_actions


class ListViewPostProcessor(object):
    _RTYPE_IDS = (constants.REL_SUB_IS_INVITED_TO,
                  constants.REL_SUB_ACCEPTED_INVITATION,
                  constants.REL_SUB_REFUSED_INVITATION,
                  constants.REL_SUB_CAME_EVENT,
                  constants.REL_SUB_NOT_CAME_EVENT,
                 )

    def __init__(self, event):
        self.event = event
        self.user = None

    def __call__(self, context, request):
        self.user = request.user
        cells = context['header_filters'].selected.cells
        rtypes = RelationType.objects.filter(pk__in=self._RTYPE_IDS)

        # NB: add relations items to use the pre-cache system of HeaderFilter
        #     (TODO: problem: retrieve other related events too)
        cells.extend(EntityCellRelation(model=Contact, rtype=rtype, is_hidden=True) for rtype in rtypes)

        cells.append(EntityCellVolatile(model=Contact, value='invitation_management', title=_(u'Invitation'), render_func=self.invitation_render))
        cells.append(EntityCellVolatile(model=Contact, value='presence_management',   title=_(u'Presence'),   render_func=self.presence_render))

        for entity in context['entities'].object_list:
            entity.get_actions = build_get_actions(self.event, entity)

    def has_relation(self, entity, rtype_id):
        id_ = self.event.id
        return any(id_ == relation.object_entity_id for relation in entity.get_relations(rtype_id))

    def invitation_render(self, entity):
        has_relation = self.has_relation
        event = self.event
        user = self.user

        if not has_relation(entity, constants.REL_SUB_IS_INVITED_TO):
            current_status = constants.INV_STATUS_NOT_INVITED
        elif has_relation(entity, constants.REL_SUB_ACCEPTED_INVITATION):
            current_status = constants.INV_STATUS_ACCEPTED
        elif has_relation(entity, constants.REL_SUB_REFUSED_INVITATION):
            current_status = constants.INV_STATUS_REFUSED
        else:
            current_status = constants.INV_STATUS_NO_ANSWER

        has_perm = user.has_perm_to_link
        # select = ["""<select onchange="creme.events.saveContactStatus('%s', this);" %s>""" % (
        #                 reverse('events__set_invitation_status', args=(event.id, entity.id)),
        #                 '' if has_perm(event) and has_perm(entity) else 'disabled="True"',
        #             )
        #          ]
        # select.extend(u'<option value="%s" %s>%s</option>' % (
        #                     status,
        #                     'selected' if status == current_status else '',
        #                     status_name
        #                 ) for status, status_name in INV_STATUS_MAP.iteritems()
        #             )
        # select.append('</select>')
        #
        # return u''.join(select)
        return format_html(
            u"""<select onchange="creme.events.saveContactStatus('{url}', this);"{attrs}>{options}</select>""",
            url=reverse('events__set_invitation_status', args=(event.id, entity.id)),
            attrs='' if has_perm(event) and has_perm(entity) else mark_safe(' disabled="True"'),
            options=format_html_join(
                '', u'<option value="{}"{}>{}</option>',
                ((status, ' selected' if status == current_status else '', status_name)
                     for status, status_name in INV_STATUS_MAP.iteritems()
                )
            ),
        )

    def presence_render(self, entity):
        has_relation = self.has_relation
        event = self.event
        user = self.user

        if has_relation(entity, constants.REL_SUB_CAME_EVENT):
            current_status = constants.PRES_STATUS_COME
        elif has_relation(entity, constants.REL_SUB_NOT_CAME_EVENT):
            current_status = constants.PRES_STATUS_NOT_COME
        else:
            current_status = constants.PRES_STATUS_DONT_KNOW

        has_perm = user.has_perm_to_link
        # select = ["""<select onchange="creme.events.saveContactStatus('%s', this);" %s>""" % (
        #                 reverse('events__set_presence_status', args=(event.id, entity.id)),
        #                 '' if has_perm(event) and has_perm(entity) else 'disabled="True"',
        #             )
        #          ]
        # select.extend(u'<option value="%s" %s>%s</option>' % (
        #                     status,
        #                     'selected' if status == current_status else '',
        #                     status_name
        #                 ) for status, status_name in PRES_STATUS_MAP.iteritems()
        #              )
        # select.append('</select>')
        #
        # return u''.join(select)
        return format_html(
            u"""<select onchange="creme.events.saveContactStatus('{url}', this);"{attrs}>{options}</select>""",
            url=reverse('events__set_presence_status', args=(event.id, entity.id)),
            attrs='' if has_perm(event) and has_perm(entity) else mark_safe(' disabled="True"'),
            options=format_html_join(
                '', u'<option value="{}"{}>{}</option>',
                ((status, ' selected' if status == current_status else '', status_name)
                     for status, status_name in PRES_STATUS_MAP.iteritems()
                )
            ),
        )

_FILTER_RELATIONTYPES = (constants.REL_SUB_IS_INVITED_TO,
                         constants.REL_SUB_ACCEPTED_INVITATION,
                         constants.REL_SUB_REFUSED_INVITATION,
                         constants.REL_SUB_CAME_EVENT,
                         constants.REL_SUB_NOT_CAME_EVENT,
                        )


@login_required
@permission_required('events')
# @permission_required('persons') ????
def list_contacts(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    request.user.has_perm_to_view_or_die(event)

    return list_view(request, Contact,
                     extra_dict={'list_title': _(u'List of contacts related to «{}»').format(event),
                                 'add_url':    '',
                                 'event_entity': event,  # For ID & to check perm (see 'lv_button_link_contacts.html')
                                 'extra_bt_templates': ('events/lv_button_link_contacts.html',),
                                },
                     extra_q=Q(relations__type__in=_FILTER_RELATIONTYPES),
                     post_process=ListViewPostProcessor(event),
                    )


@login_required
@permission_required('events')
def link_contacts(request, event_id):
    return edit_entity(request, event_id, Event, AddContactsToEventForm)


def _get_status(request, valid_status):
    status_str = get_from_POST_or_404(request.POST, 'status')

    try:
        status = int(status_str)
    except Exception:
        raise Http404('Status is not an integer: {}'.format(status_str))

    if not status in valid_status:
        raise Http404('Unknown status: {}'.format(status))

    return status


def _get_event_n_contact(event_id, contact_id, user):
    event   = get_object_or_404(Event, pk=event_id)
    contact = get_object_or_404(Contact, pk=contact_id)

    has_perm_or_die = user.has_perm_to_link_or_die
    has_perm_or_die(event)
    has_perm_or_die(contact)

    return event, contact


# TODO: use jsonify ??
@login_required
@permission_required('events')
def set_invitation_status(request, event_id, contact_id):
    status = _get_status(request, INV_STATUS_MAP)
    user = request.user
    event, contact = _get_event_n_contact(event_id, contact_id, user)

    event.set_invitation_status(contact, status, user)

    # return HttpResponse(content_type='text/javascript')
    return HttpResponse()


@login_required
@permission_required('events')
def set_presence_status(request, event_id, contact_id):
    status = _get_status(request, PRES_STATUS_MAP)
    user = request.user
    event, contact = _get_event_n_contact(event_id, contact_id, user)

    event.set_presence_status(contact, status, user)

    # return HttpResponse(content_type='text/javascript')
    return HttpResponse()


def abstract_add_related_opportunity(request, event_id, contact_id,
                                     form=RelatedOpportunityCreateForm,
                                    ):
    event   = get_object_or_404(Event, pk=event_id)
    contact = get_object_or_404(Contact, pk=contact_id)

    request.user.has_perm_to_link_or_die(event)

    return add_entity(request, form,
                      extra_initial={'event': event, 'contact': contact},
                     )


@login_required
@permission_required(('events', 'opportunities', cperm(Opportunity)))
def add_opportunity(request, event_id, contact_id):
    return abstract_add_related_opportunity(request, event_id, contact_id)
