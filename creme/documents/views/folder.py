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

from django.db.models import Q ##
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType

from creme_core.views.generic import add_entity, edit_entity, view_entity
from creme_core.views.generic.list_entities import list_entities ##
from creme_core.gui.last_viewed import change_page_for_last_item_viewed ##

from documents.models import Folder
from documents.forms.folder import FolderForm


@login_required
@permission_required('documents')
@permission_required('documents.add_folder')
def add(request):
    return add_entity(request, FolderForm)

def edit(request, folder_id):
    return edit_entity(request, folder_id, Folder, FolderForm, 'documents')

@login_required
@permission_required('documents')
def detailview(request, object_id):
    """
        @Permissions : Acces or Admin to document app & Read on current Folder object
        TODO : Use generic view_entity_with_template
    """
    folder = view_entity(request, object_id, Folder)

    folder.view_or_die(request.user)

    return render_to_response('creme_core/generics/view_entity.html',
                              {'object': folder, 'path': '/documents/folder'},
                              context_instance=RequestContext(request))

#TODO: use new list view ????
@login_required
@permission_required('documents')
@change_page_for_last_item_viewed
def listview(request):
    list_field = [
                    ('title',         True, 'title'),
                    ('description',   True, 'description'),
                    ('parent_folder', True, 'parent_folder'),
                    ('user',          True, 'user__username'),
            ]
    page_list_folders = list_entities(request, Folder, list_field, Q(parent_folder__isnull=True), sorder='title')

    return render_to_response('documents/list_folders.html',
                              {'list_objects': page_list_folders},
                              context_instance=RequestContext(request))
