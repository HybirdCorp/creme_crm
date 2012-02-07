# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required

from creme_core.views.generic import inner_popup, add_to_entity as generic_add_to_entity
from creme_core.utils import get_from_POST_or_404

from assistants.models import UserMessage
from assistants.forms.user_message import UserMessageForm


@login_required
def add(request):
    if request.method == 'POST':
        message_form = UserMessageForm(entity=None, user=request.user, data=request.POST)

        if message_form.is_valid():
            message_form.save()
    else:
        message_form = UserMessageForm(entity=None, user=request.user)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {'form':   message_form,
                        'title':  _(u'New message'),
                       },
                       is_valid=message_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

@login_required
def add_to_entity(request, entity_id):
    return generic_add_to_entity(request, entity_id, UserMessageForm, _(u'New message about <%s>'))

@login_required
def delete(request):
    msg = get_object_or_404(UserMessage, pk=get_from_POST_or_404(request.POST, 'id'))

    if request.user.id != msg.recipient_id:
        raise PermissionDenied(_('You are not allowed to delete this message: %s') % msg)

    msg.delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(msg.creme_entity.get_absolute_url() if msg.creme_entity else '/')
