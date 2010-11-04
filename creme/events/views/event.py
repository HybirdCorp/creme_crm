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

from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import add_entity, edit_entity, view_entity_with_template, list_view

from events.models import Event
from events.forms.event import EventForm, AddContactsToEventForm


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

@login_required
@permission_required('events')
#@permission_required('persons') ????
def list_contacts(request, event_id):
    from django.db.models import Q
    from django.shortcuts import get_object_or_404
    from django.utils.translation import ugettext as _

    from persons.models import Contact

    from events.constants import *

    event = get_object_or_404(Event, pk=event_id)

    event.can_view_or_die(request.user)

    return list_view(request, Contact,
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
                              )
                    )

@login_required
@permission_required('events')
def link_contacts(request, event_id):
    return edit_entity(request, event_id, Event, AddContactsToEventForm, 'events')
