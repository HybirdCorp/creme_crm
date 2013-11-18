# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.decorators import login_required, permission_required

from creme.creme_core.core.entity_cell import EntityCellRelation, EntityCellVolatile
from creme.creme_core.models import RelationType
from creme.creme_core.models.entity import EntityAction
from creme.creme_core.views.generic import add_entity, edit_entity, view_entity, list_view
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.utils.queries import get_first_or_None

from creme.persons.models import Contact

from ..models import Event, EventType
from ..forms.event import EventForm, AddContactsToEventForm, RelatedOpportunityCreateForm
from ..constants import *


@login_required
@permission_required('events')
@permission_required('events.add_event')
def add(request):
    return add_entity(request, EventForm,
                      extra_initial={'type':  get_first_or_None(EventType)},
                      extra_template_dict={'submit_label': _('Save the event')},
                     )

@login_required
@permission_required('events')
def edit(request, event_id):
    return edit_entity(request, event_id, Event, EventForm)

@login_required
@permission_required('events')
def detailview(request, event_id):
    return view_entity(request, event_id, Event, '/events/event', 'events/view_event.html')

@login_required
@permission_required('events')
def listview(request):
    return list_view(request, Event, extra_dict={'add_url': '/events/event/add'})


INV_STATUS_MAP = {
        INV_STATUS_NOT_INVITED: _('Not invited'),
        INV_STATUS_NO_ANSWER:   _('Did not answer'),
        INV_STATUS_ACCEPTED:    _('Accepted the invitation'),
        INV_STATUS_REFUSED:     _('Refused the invitation'),
    }

PRES_STATUS_MAP = {
        PRES_STATUS_DONT_KNOW: _('N/A'),
        PRES_STATUS_COME:      _('Come'),
        PRES_STATUS_NOT_COME:  _('Not come'),
    }


def build_get_actions(event, entity):
    """Build bound method to overload 'get_actions()' method of CremeEntities"""
    def _get_actions(user):
        return {'default': EntityAction(entity.get_absolute_url(), ugettext(u"See"),
                                        user.has_perm_to_view(entity),
                                        icon="images/view_16.png",
                                       ),
                'others':  [EntityAction('/events/event/%s/add_opportunity_with/%s' % (event.id, entity.id),
                                         ugettext(u"Create an opportunity"),
                                         user.has_perm('opportunities.add_opportunity') and user.has_perm_to_link(event),
                                         icon="images/opportunity_16.png",
                                        ),
                           ]
               }

    return _get_actions

class ListViewPostProcessor(object):
    #_HIDDEN_CELL_DESC = (('relations_invited',  u'Invited',  REL_SUB_IS_INVITED_TO),
                         #('relations_accepted', u'Accepted', REL_SUB_ACCEPTED_INVITATION),
                         #('relations_refused',  u'Refused',  REL_SUB_REFUSED_INVITATION),
                         #('relations_came',     u'Came',     REL_SUB_CAME_EVENT),
                         #('relations_notcame',  u'Not come', REL_SUB_NOT_CAME_EVENT),
                        #)
    _RTYPE_IDS = (REL_SUB_IS_INVITED_TO,
                  REL_SUB_ACCEPTED_INVITATION,
                  REL_SUB_REFUSED_INVITATION,
                  REL_SUB_CAME_EVENT,
                  REL_SUB_NOT_CAME_EVENT,
                 )

    def __init__(self, event):
        self.event = event
        self.user = None

    def __call__(self, context, request):
        self.user = request.user
        cells = context['header_filters'].selected.cells
        rtypes = RelationType.objects.filter(pk__in=self._RTYPE_IDS)

        #NB: add relations items to use the pre-cache system of HeaderFilter (TO: problem: retrieve other related events too)
        cells.extend(EntityCellRelation(rtype=rtype, is_hidden=True) for rtype in rtypes)

        cells.append(EntityCellVolatile(value='invitation_management', title=_(u'Invitation'), render_func=self.invitation_render))
        cells.append(EntityCellVolatile(value='presence_management',   title=_(u'Presence'),   render_func=self.presence_render))

        for entity in context['entities'].object_list:
            entity.get_actions = build_get_actions(self.event, entity)

    def has_relation(self, entity, rtype_id):
        id_ = self.event.id
        return any(id_ == relation.object_entity_id for relation in entity.get_relations(rtype_id))

    def invitation_render(self, entity):
        has_relation = self.has_relation
        event = self.event
        user = self.user

        if not has_relation(entity, REL_SUB_IS_INVITED_TO):
            current_status = INV_STATUS_NOT_INVITED
        elif has_relation(entity, REL_SUB_ACCEPTED_INVITATION):
            current_status = INV_STATUS_ACCEPTED
        elif has_relation(entity, REL_SUB_REFUSED_INVITATION):
            current_status = INV_STATUS_REFUSED
        else:
            current_status = INV_STATUS_NO_ANSWER

        has_perm = user.has_perm_to_link
        select = ["""<select onchange="post_contact_status('/events/event/%s/contact/%s/set_invitation_status', this);" %s>""" % (
                        event.id,
                        entity.id,
                        '' if has_perm(event) and has_perm(entity) else 'disabled="True"'
                    )
                 ]
        select.extend(u'<option value="%s" %s>%s</option>' % (
                            status,
                            'selected' if status == current_status else '',
                            status_name
                        ) for status, status_name in INV_STATUS_MAP.iteritems()
                    )
        select.append('</select>')

        return u''.join(select)

    def presence_render(self, entity):
        has_relation = self.has_relation
        event = self.event
        user = self.user

        if has_relation(entity, REL_SUB_CAME_EVENT):
            current_status = PRES_STATUS_COME
        elif has_relation(entity, REL_SUB_NOT_CAME_EVENT):
            current_status = PRES_STATUS_NOT_COME
        else:
            current_status = PRES_STATUS_DONT_KNOW

        has_perm = user.has_perm_to_link
        select = ["""<select onchange="post_contact_status('/events/event/%s/contact/%s/set_presence_status', this);" %s>""" % (
                        event.id,
                        entity.id,
                        '' if has_perm(event) and has_perm(entity) else 'disabled="True"'
                    )
                 ]
        select.extend(u'<option value="%s" %s>%s</option>' % (
                            status,
                            'selected' if status == current_status else '',
                            status_name
                        ) for status, status_name in PRES_STATUS_MAP.iteritems()
                     )
        select.append('</select>')

        return u''.join(select)


_FILTER_RELATIONTYPES = (REL_SUB_IS_INVITED_TO,
                         REL_SUB_ACCEPTED_INVITATION,
                         REL_SUB_REFUSED_INVITATION,
                         REL_SUB_CAME_EVENT,
                         REL_SUB_NOT_CAME_EVENT,
                        )

@login_required
@permission_required('events')
#@permission_required('persons') ????
def list_contacts(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    request.user.has_perm_to_view_or_die(event)

    return list_view(request, Contact, template='events/list_events.html',
                     extra_dict={'list_title': _(u'List of contacts related to <%s>') % event,
                                 'add_url':    '/events/event/%s/link_contacts' % event_id,
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
        raise Http404('Status is not an integer: %s' % status_str)

    if not status in valid_status:
        raise Http404('Unknow status: %s' % status)

    return status

def _get_event_n_contact(event_id, contact_id, user):
    event   = get_object_or_404(Event, pk=event_id)
    contact = get_object_or_404(Contact, pk=contact_id)

    has_perm_or_die = user.has_perm_to_link_or_die
    has_perm_or_die(event)
    has_perm_or_die(contact)

    return event, contact

#TODO: use jsonify ??
@login_required
@permission_required('events')
def set_invitation_status(request, event_id, contact_id):
    status = _get_status(request, INV_STATUS_MAP)
    user = request.user
    event, contact = _get_event_n_contact(event_id, contact_id, user)

    event.set_invitation_status(contact, status, user)

    return HttpResponse('', mimetype='text/javascript')

@login_required
@permission_required('events')
def set_presence_status(request, event_id, contact_id):
    status = _get_status(request, PRES_STATUS_MAP)
    user  = request.user
    event, contact = _get_event_n_contact(event_id, contact_id, user)

    event.set_presence_status(contact, status, user)

    return HttpResponse('', mimetype='text/javascript')

@login_required
@permission_required('events')
@permission_required('opportunities')
@permission_required('opportunities.add_opportunity')
def add_opportunity(request, event_id, contact_id):
    event   = get_object_or_404(Event, pk=event_id)
    contact = get_object_or_404(Contact, pk=contact_id)

    request.user.has_perm_to_link_or_die(event)

    return add_entity(request, RelatedOpportunityCreateForm,
                      extra_initial={'event': event, 'contact': contact},
                     )
