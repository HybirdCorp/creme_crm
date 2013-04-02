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
from django.core.serializers import serialize
from django.http import HttpResponse

from creme.creme_core.models import EntityCredentials

from creme.documents.models import Folder, Document


@login_required
@permission_required('documents')
def get_child_folders(request):
    """
        @Permissions : Filter can Read folder
    """
    if request.POST.has_key('id'):
        folders = Folder.objects.filter(parent_folder=request.POST['id']).order_by('-title')
        folders = EntityCredentials.filter(request.user, folders)
        data = serialize('json', folders, fields=('title', 'description', 'parent_folder'))
    else:
        data = {}

    return HttpResponse(data, mimetype="text/javascript")

@login_required
@permission_required('documents')
def get_child_documents(request):
    """
        @Permissions : Filter can Read documents
    """
    if request.POST.has_key('id'):
        documents = Document.objects.filter(folder=request.POST['id'])
        documents = EntityCredentials.filter(request.user, documents)
        data = serialize('json', documents, fields=('title', 'description', 'folder', 'filedata'))
    else:
        data = {}

    return HttpResponse(data, mimetype="text/javascript")
