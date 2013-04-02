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

from django.contrib.auth.decorators import login_required, permission_required
from django.db.models.query_utils import Q
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404

from creme.creme_core.views.generic import add_entity, edit_entity, view_entity
from creme.creme_core.views.generic.listview import list_view

from ..models import Folder
from ..forms.folder import FolderForm


@login_required
@permission_required('documents')
@permission_required('documents.add_folder')
def add(request):
    return add_entity(request, FolderForm)

@login_required
@permission_required('documents')
def edit(request, folder_id):
    return edit_entity(request, folder_id, Folder, FolderForm)

@login_required
@permission_required('documents')
def detailview(request, folder_id):
    return view_entity(request, folder_id, Folder, '/documents/folder', 'documents/view_folder.html')

@login_required
@permission_required('documents')
def listview(request):
    REQUEST_get = request.REQUEST.get

    parent_id   = REQUEST_get('parent_id')
    extra_q     = Q(parent_folder__isnull=True)
    previous_id = None
    folder      = None

    if parent_id is not None:
        try:
            parent_id = int(parent_id)
        except (ValueError, TypeError):
            pass
        else:
            folder = get_object_or_404(Folder, pk=parent_id)
            folder.can_view_or_die(request.user)
            extra_q = Q(parent_folder=folder)
            previous_id = folder.parent_folder_id

    def post_process(template_dict, request):
        if folder is not None:
            parents = folder.get_parents()
            parents.insert(0, folder)
            parents.reverse()
            template_dict['list_title'] = _(u"List sub-folders of %s") % folder
            template_dict['list_sub_title'] = u" > ".join([f.title for f in parents])

    return list_view(request, Folder, extra_q=extra_q,
                     extra_dict={'add_url': '/documents/folder/add', 'parent_id': parent_id or "",
                                 'extra_bt_templates':('documents/frags/previous.html', ),
                                 'previous_id': previous_id},
                     post_process=post_process)


