# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from django.http import Http404
from django.shortcuts import render
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.forms.list_view_import import UploadForm, form_factory
from creme.creme_core.gui.list_view_import import import_form_registry
from creme.creme_core.utils import get_ct_or_404, get_from_POST_or_404

#django wizard doesn't manage to inject its input in the 2nd form
# + we can't upload file with wizard (even if it is a documents.Document for now)

@login_required
def import_listview(request, ct_id):
    ct = get_ct_or_404(ct_id)
    user = request.user
    submit_label = _('Save the entities')

    try:
        import_form_registry.get(ct)
    except import_form_registry.UnregisteredCTypeException as e:
        raise Http404(e)

    user.has_perm_to_create_or_die(ct.model_class())

    if request.method == 'POST':
        POST = request.POST
        step = get_from_POST_or_404(POST, 'step', cast=int, default=0) #TODO: int -> boundedInt
        form = UploadForm(user=user, data=POST)

        if step == 0:
            if form.is_valid():
                cleaned_data = form.cleaned_data
                ImportForm = form_factory(ct, form.header)
                form = ImportForm(user=user,
                                  initial={'step':       1,
                                           'document':   cleaned_data['document'].id,
                                           'has_header': cleaned_data['has_header'],
                                          }
                                 )
            else:
                submit_label = _('Import this file')
        else:
            if step != 1:
                raise Http404('Step should be in (0, 1)')

            form.is_valid() #clean fields

            ImportForm = form_factory(ct, form.header)
            form = ImportForm(user=user, data=POST)

            if form.is_valid():
                form.save()
                return render(request, 'creme_core/importing_report.html',
                              {'form':     form,
                               'back_url': request.GET['list_url'],
                              }
                             )

        cancel_url = POST.get('cancel_url')
    else:
        form = UploadForm(user=user, initial={'step': 0})
        submit_label = _('Import this file')
        cancel_url = request.META.get('HTTP_REFERER')

    return render(request, 'creme_core/generics/blockform/add.html',
                  {'form':         form,
                   'title':        _('Import data file'),
                   'cancel_url':   cancel_url,
                   'submit_label': submit_label,
                  }
                 )
