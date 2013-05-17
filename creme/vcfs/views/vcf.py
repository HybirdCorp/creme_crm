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

from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils.encoding import smart_str
from django.contrib.auth.decorators import permission_required, login_required

from creme.persons.models import Contact

from ..forms.vcf import VcfForm, VcfImportForm
from ..vcfgenerator import VcfGenerator


@login_required
@permission_required('persons')
@permission_required('persons.add_contact')
def vcf_import(request):
    user = request.user

    if request.method == 'POST':
        POST = request.POST
        step = int(POST.get('vcf_step', 0))
        form = VcfForm(user=user, data=POST, files=request.FILES)

        if step == 0:
            if form.is_valid():
                form = VcfImportForm(user=user,
                                     vcf_data=form.cleaned_data['vcf_file'],
                                     initial={'vcf_step': 1},
                                    )
        else:
            assert step == 1

            form = VcfImportForm(user=user, data=POST)

            if form.is_valid():
                contact = form.save()
                return HttpResponseRedirect(contact.get_absolute_url())

    else:
        form = VcfForm(user=user, initial={'vcf_step': 0})

    return render(request, 'creme_core/generics/blockform/edit.html', {'form': form})

@login_required
@permission_required('persons')
def vcf_export(request, contact_id):
    person = get_object_or_404(Contact, pk=contact_id)
    request.user.has_perm_to_view_or_die(person)

    vc = VcfGenerator(person).serialize()

    response = HttpResponse(vc, mimetype='text/vcard')
    response['Content-Disposition'] = 'attachment; filename="%s.vcf"' % smart_str(person.last_name)

    return response
