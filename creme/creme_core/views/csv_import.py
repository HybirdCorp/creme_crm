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

from django.shortcuts import render, get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required

from creme_core.forms.csv_import import CSVUploadForm, form_factory

#django wizard doesn't manage to inject its input in the 2nd form
# + we can't upload file with wizard (even if it is a documents.Document for now)

@login_required
def csv_import(request, ct_id):
    ct = get_object_or_404(ContentType, pk=ct_id)
    user = request.user

    user.has_perm_to_create_or_die(ct.model_class())

    if request.method == 'POST':
        POST = request.POST
        step = int(POST.get('csv_step', 0))
        form = CSVUploadForm(user=user, data=POST)

        if step == 0:
            if form.is_valid():
                cleaned_data = form.cleaned_data
                CSVImportForm = form_factory(ct, form.csv_header)
                form = CSVImportForm(user=user,
                                     initial={'csv_step':       1,
                                              'csv_document':   cleaned_data['csv_document'].id,
                                              'csv_has_header': cleaned_data['csv_has_header'],
                                             }
                                    )
        else:
            assert step == 1
            form.is_valid() #clean fields

            CSVImportForm = form_factory(ct, form.csv_header)
            form = CSVImportForm(user=user, data=POST)

            if form.is_valid():
                form.save()
                return render(request, 'creme_core/csv_importing_report.html',
                              {'form':     form,
                               'back_url': request.GET['list_url'],
                              }
                             )
    else:
        form = CSVUploadForm(user=user, initial={'csv_step': 0})

    return render(request, 'creme_core/generics/blockform/add.html', {'form': form})
