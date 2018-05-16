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

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views.generic import inner_popup, add_to_entity as generic_add_to_entity

from creme.assistants.forms.user_message import UserMessageForm
from creme.assistants.models import UserMessage


@login_required
def add(request):
    if request.method == 'POST':
        message_form = UserMessageForm(entity=None, user=request.user, data=request.POST)

        if message_form.is_valid():
            message_form.save()
    else:
        message_form = UserMessageForm(entity=None, user=request.user)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup.html',
                       {'form':   message_form,
                        'title':  _(u'New message'),
                        'submit_label': _('Save the message'),
                       },
                       is_valid=message_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )


@login_required
def add_to_entity(request, entity_id):
    return generic_add_to_entity(request, entity_id, UserMessageForm,
                                 _(u'New message about «%s»'),
                                 submit_label=_('Save the message'),
                                )


@login_required
def delete(request):
    msg = get_object_or_404(UserMessage, pk=get_from_POST_or_404(request.POST, 'id'))

    if request.user.id != msg.recipient_id:
        raise PermissionDenied(ugettext('You are not allowed to delete this message: %s') % msg)

    msg.delete()

    if request.is_ajax():
        # return HttpResponse("", content_type="text/javascript")
        return HttpResponse()

    entity = msg.creme_entity

    return HttpResponseRedirect(entity.get_absolute_url() if entity else '/')
