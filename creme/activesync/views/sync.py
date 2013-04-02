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

from django.http import HttpResponse
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required, permission_required
from django.template.loader import render_to_string
from django.shortcuts import render_to_response
from django.conf import settings

from ..messages import MessageError, _ERROR
from ..sync import Synchronization
from ..errors import CremeActiveSyncError


@login_required
@permission_required('activesync')
def main_sync(request):
    try:
        sync = Synchronization(request.user)
    except CremeActiveSyncError as e:
#        raise Exception(e)
        tpl_dict = {'all_messages': {_ERROR: [MessageError(message=e)]}.iteritems()}#TODO:Bof
    else:
        try:
            sync.synchronize()
        except CremeActiveSyncError as e:
            sync.add_error_message(e)

        tpl_dict = {
            'server_url': sync.server_url,
            'login'     : sync.login,
            'domain'    : sync.domain,
            'server_ssl': sync.server_ssl,
            'last_sync' : sync.last_sync,

            'all_messages'  : sync.messages(),
            'sync_calendars': sync.is_user_sync_calendars,
            'sync_contacts' : sync.is_user_sync_contacts,

            #DEBUG
            'xml':        sync._data['debug']['xml'],
            'debug_info': sync._data['debug']['info'],
            'ACTIVE_SYNC_DEBUG': settings.ACTIVE_SYNC_DEBUG,
        }

    context = RequestContext(request)


    if request.is_ajax():
        return HttpResponse(render_to_string('activesync/frags/ajax/main_sync.html', tpl_dict, context_instance=context))

    return render_to_response('activesync/main_sync.html', tpl_dict, context_instance=context)
