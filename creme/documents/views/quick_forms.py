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
from django.http import Http404, HttpResponse
from django.forms.formsets import formset_factory
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from django.core.serializers.json import DjangoJSONEncoder as JSONEncoder

from creme_core.views.generic import inner_popup
from creme_core.views.quick_forms import json_quickform_response
from creme_core.utils import get_ct_or_404

from documents.forms.quick import CSVDocumentWidgetQuickForm
from documents.models import Document, Folder
from documents.utils import get_csv_folder_or_create

@login_required
def add_csv_from_widget(request, count):
    user = request.user

    if not user.has_perm_to_create(Document):
        raise PermissionDenied('You are not allowed to create a document')

    #TODO : see for permission issues
    #folder.can_change_or_die(user)

    if request.method == 'POST':
        form = CSVDocumentWidgetQuickForm(user=user, data=request.POST, files=request.FILES or None, initial=None)
    else:
        form = CSVDocumentWidgetQuickForm(user=user, initial=None)

    if request.method == 'GET' or not form.is_valid():
        return inner_popup(request, 'creme_core/generics/form/add_innerpopup.html',
                           {'form':   form,
                            'title':  _('New value'),
                           },
                           is_valid=form.is_valid(),
                           reload=False,
                           delegate_reload=True,
                          )

    form.save()

    return json_quickform_response(form.instance)
