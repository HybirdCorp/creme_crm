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

# import warnings

# from django.conf import settings
from django.shortcuts import render
from django.urls import reverse

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.utils import jsonify
from creme.creme_core.views.bricks import bricks_render_info

from .. import bricks
from ..errors import CremeActiveSyncError
from ..messages import MessageError, _ERROR
from ..sync import Synchronization


# @login_required
# @permission_required('activesync')
# def main_sync(request):
#     warnings.warn('activesync.views.sync.main_sync() is deprecated ; use sync_portal() instead.',
#                   DeprecationWarning
#                  )
#
#     try:
#         sync = Synchronization(request.user)
#     except CremeActiveSyncError as e:
#         tpl_dict = {'all_messages': [(_ERROR, [MessageError(message=e)])],
#                     'fatal_error':  True,
#                    }
#     else:
#         try:
#             sync.synchronize()
#         except CremeActiveSyncError as e:
#             sync.add_error_message(e)
#
#         tpl_dict = {
#             'bricks_reload_url': reverse('activesync__sync_n_reload_bricks'),
#
#             'server_url': sync.server_url,
#             'login':      sync.login,
#             'domain':     sync.domain,
#             'server_ssl': sync.server_ssl,
#             'last_sync':  sync.last_sync,
#
#             'all_messages':   sync.messages(),
#             'sync_calendars': sync.is_user_sync_calendars,
#             'sync_contacts':  sync.is_user_sync_contacts,
#
#             # DEBUG
#             'xml':          sync._data['debug']['xml'],
#             'debug_info':   sync._data['debug']['info'],
#             'debug_errors': sync._data['debug']['errors'],
#             'ACTIVE_SYNC_DEBUG': settings.ACTIVE_SYNC_DEBUG,
#         }
#
#     if request.is_ajax():
#         # TODO: template in a var
#         return render(request, 'activesync/frags/ajax/main_sync.html', tpl_dict)
#
#     return render(request, 'activesync/main_sync.html', tpl_dict)


def _sync_n_bricks(request):
    fatal_messages = None

    try:
        sync = Synchronization(request.user)
    except CremeActiveSyncError as e:
        sync = None
        fatal_messages = [(_ERROR, [MessageError(message=e)])]
    else:
        try:
            sync.synchronize()
        except CremeActiveSyncError as e:
            sync.add_error_message(e)

    return [
        bricks.UserSynchronizationParametersBrick(sync),
        bricks.UserSynchronizationDebugBrick(sync),
        bricks.UserSynchronizationResultsBrick(sync=sync, messages=fatal_messages),
        bricks.UserSynchronizationHistoryBrick(),
    ]


@login_required
@permission_required('activesync')
def sync_portal(request):
    return render(request, 'activesync/sync-portal.html',
                  context={'bricks':            _sync_n_bricks(request),
                           'bricks_reload_url': reverse('activesync__sync_n_reload_bricks'),
                          },
                 )


@login_required
@permission_required('activesync')
@jsonify
def sync_n_reload_bricks(request):
    return bricks_render_info(request, bricks=_sync_n_bricks(request))
