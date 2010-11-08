# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.models.header_filter import HeaderFilterItem, HFI_RELATION, HFI_VOLATILE
from creme_core.views.generic import add_entity, edit_entity, view_entity_with_template, list_view

from persons.models import Contact

from events.models import Event
from events.forms.event import EventForm, AddContactsToEventForm
from events.constants import *


@login_required
@permission_required('events')
@permission_required('events.add_event')
def add(request):
    return add_entity(request, EventForm)

def edit(request, event_id):
    return edit_entity(request, event_id, Event, EventForm, 'events')

@login_required
@permission_required('events')
def detailview(request, event_id):
    return view_entity_with_template(request, event_id, Event, '/events/event',
                                     'events/view_event.html'
                                    )

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


class ListViewPostProcessor(object):
    def __init__(self, event):
        self.event = event

    def __call__(self, context):
        hfitems = context['header_filters'].selected.items

        #NB: add relations items to use the pre-cache system of HeaderFilter (TO: problem: retrieve other related events too)
        hfitems.extend(HeaderFilterItem(name=name, title=title, is_hidden=True,
                                        type=HFI_RELATION, relation_predicat_id=type_id,
                                    )
                        for name, title, type_id in (('relations_invited',  u'Invited',  REL_SUB_IS_INVITED_TO),
                                                     ('relations_accepted', u'Accepted', REL_SUB_ACCEPTED_INVITATION),
                                                     ('relations_refused',  u'Refused',  REL_SUB_REFUSED_INVITATION),
                                                     ('relations_came',     u'Came',     REL_SUB_CAME_EVENT),
                                                     ('relations_notcame',  u'Not come', REL_SUB_NOT_CAME_EVENT),
                                                    )
                    )

        hfi = HeaderFilterItem(name='invitation_management', title=_(u'Invitation'), type=HFI_VOLATILE)
        hfi.volatile_render = self.invitation_render
        hfitems.append(hfi)

        hfi = HeaderFilterItem(name='presence_management', title=_(u'Presence'), type=HFI_VOLATILE)
        hfi.volatile_render = self.presence_render
        hfitems.append(hfi)

    def has_relation(self, entity, rtype_id):
        id_ = self.event.id
        return any(id_ == relation.object_entity_id for relation in entity.get_relations(rtype_id))

    #TODO: credentials ???
    def invitation_render(self, entity):
        has_relation = self.has_relation

        if not has_relation(entity, REL_SUB_IS_INVITED_TO):
            current_status = INV_STATUS_NOT_INVITED
        elif has_relation(entity, REL_SUB_ACCEPTED_INVITATION):
            current_status = INV_STATUS_ACCEPTED
        elif has_relation(entity, REL_SUB_REFUSED_INVITATION):
            current_status = INV_STATUS_REFUSED
        else:
            current_status = INV_STATUS_NO_ANSWER

        select = ["""<select onchange="post_contact_status('/events/event/%s/contact/%s/set_invitation_status', this);">""" % \
                    (self.event.id, entity.id)
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

        if has_relation(entity, REL_SUB_CAME_EVENT):
            current_status = PRES_STATUS_COME
        elif has_relation(entity, REL_SUB_NOT_CAME_EVENT):
            current_status = PRES_STATUS_NOT_COME
        else:
            current_status = PRES_STATUS_DONT_KNOW

        select = ["""<select onchange="post_contact_status('/events/event/%s/contact/%s/set_presence_status', this);">""" % \
                    (self.event.id, entity.id)
                 ]
        select.extend(u'<option value="%s" %s>%s</option>' % (
                            status,
                            'selected' if status == current_status else '',
                            status_name
                        ) for status, status_name in PRES_STATUS_MAP.iteritems()
                    )
        select.append('</select>')

        return u''.join(select)


@login_required
@permission_required('events')
#@permission_required('persons') ????
def list_contacts(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    event.can_view_or_die(request.user)

    return list_view(request, Contact, template='events/list_events.html',
                     extra_dict={
                                    'list_title': _(u'List of contacts related to <%s>') % event,
                                    'add_url':    '/events/event/%s/link_contacts' % event_id,
                                },
                     extra_q=Q(relations__type__in=[REL_SUB_IS_INVITED_TO,
                                                    REL_SUB_ACCEPTED_INVITATION,
                                                    REL_SUB_REFUSED_INVITATION,
                                                    REL_SUB_CAME_EVENT,
                                                    REL_SUB_NOT_CAME_EVENT,
                                                   ]
                              ),
                     post_process=ListViewPostProcessor(event),
                    )

@login_required
@permission_required('events')
def link_contacts(request, event_id):
    return edit_entity(request, event_id, Event, AddContactsToEventForm, 'events')

def _get_status(request, valid_status):
    try:
        status = int(request.POST['status'])
    except Exception, e:
        raise Http404('Problem with status arg: %s' % status)

    if not status in valid_status:
        raise Http404('Unknow status: %s' % status)

    return status

#TODO: credentials ???
@login_required
@permission_required('events')
def set_invitation_status(request, event_id, contact_id):
    status  = _get_status(request, INV_STATUS_MAP)
    event   = get_object_or_404(Event, pk=event_id)
    contact = get_object_or_404(Contact, pk=contact_id)

    event.set_invitation_status(contact, status, request.user)

    return HttpResponse('', mimetype='text/javascript')

#TODO: credentials ???
@login_required
@permission_required('events')
def set_presence_status(request, event_id, contact_id):
    status  = _get_status(request, PRES_STATUS_MAP)
    event   = get_object_or_404(Event, pk=event_id)
    contact = get_object_or_404(Contact, pk=contact_id)

    event.set_presence_status(contact, status, request.user)

    return HttpResponse('', mimetype='text/javascript')
