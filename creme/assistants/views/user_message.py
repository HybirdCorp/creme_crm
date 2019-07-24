# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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
# from django.http import HttpResponse, HttpResponseRedirect
# from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _, gettext

# from creme.creme_core.auth.decorators import login_required
# from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from creme.assistants.forms.user_message import UserMessageForm
from creme.assistants.models import UserMessage


class UserMessageCreation(generic.CremeModelCreationPopup):
    model = UserMessage
    form_class = UserMessageForm
    title = _('New message')


class RelatedUserMessageCreation(generic.AddingInstanceToEntityPopup):
    model = UserMessage
    form_class = UserMessageForm
    title = _('New message about «{entity}»')


# @login_required
# def delete(request):
#     msg = get_object_or_404(UserMessage, pk=get_from_POST_or_404(request.POST, 'id'))
#
#     if request.user.id != msg.recipient_id:
#         raise PermissionDenied(gettext('You are not allowed to delete this message: {}').format(msg))
#
#     msg.delete()
#
#     if request.is_ajax():
#         return HttpResponse()
#
#     entity = msg.creme_entity
#
#     return HttpResponseRedirect(entity.get_absolute_url() if entity else '/')
class UserMessageDeletion(generic.CremeModelDeletion):
    model = UserMessage

    def check_instance_permissions(self, instance, user):
        if user.id != instance.recipient_id:
            raise PermissionDenied(
                gettext('You are not allowed to delete this message: {}').format(instance)
            )
