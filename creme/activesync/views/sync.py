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
from django.http import HttpResponse
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required, permission_required
from django.template.loader import render_to_string
from django.shortcuts import render_to_response

from activesync.sync import Synchronization
from activesync.config import ACTIVE_SYNC_DEBUG
from activesync.errors import CremeActiveSyncError

@login_required
@permission_required('activesync')
def main_sync(request):

    try:
        sync = Synchronization(request.user)
        
    except CremeActiveSyncError, err:
        tpl_dict = {'error_messages'   :  [err]}
    else:

        try:
            sync.synchronize()
        except CremeActiveSyncError, err:
            sync.add_error_message(err)

        tpl_dict = {
            'server_url': sync.server_url,
            'login':      sync.login,
            'domain':     sync.domain,
            'server_ssl': sync.server_ssl,
            'last_sync':  sync.last_sync,

            'all_messages'    :  sync.messages(),


            #DEBUG
            'xml':        sync._data['debug']['xml'],
            'debug_info': sync._data['debug']['info'],
            'ACTIVE_SYNC_DEBUG': ACTIVE_SYNC_DEBUG,
        }

    context = RequestContext(request)


    if request.is_ajax():
        return HttpResponse(render_to_string('activesync/frags/ajax/main_sync.html', tpl_dict, context_instance=context))

    return render_to_response('activesync/main_sync.html',
                       tpl_dict,
                       context_instance=context)