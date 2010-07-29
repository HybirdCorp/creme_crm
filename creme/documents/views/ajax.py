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

from django.contrib.auth.decorators import login_required
from django.core.serializers import serialize
from django.http import HttpResponse

from creme_core.models import CremeEntity
from creme_core.entities_access.filter_allowed_objects import filter_can_read_objects

from documents.models import Folder, Document


@login_required
def get_child_folders(request):
    """
        @Permissions : Filter can Read folder
    """
    if request.POST.has_key('id'):
        folders = Folder.objects.filter(parent_folder=request.POST['id']).order_by('-title')
        folders = filter_can_read_objects(request, folders)
        data = serialize('json', folders, fields=('title', 'description', 'parent_folder'))
        return HttpResponse(data, mimetype="text/javascript")
    else:
        return HttpResponse({}, mimetype="text/javascript")

@login_required
def get_child_documents(request):
    """
        @Permissions : Filter can Read documents
    """
    if request.POST.has_key('id'):
        documents = Document.objects.filter(folder=request.POST['id'])
        documents = filter_can_read_objects(request, documents)
        data = serialize('json', documents, fields=('title', 'description', 'folder', 'filedata'))
        return HttpResponse(data, mimetype="text/javascript")
    else:
        return HttpResponse({}, mimetype="text/javascript")
