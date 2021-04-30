# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.encoding import smart_str
from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import (
    login_required,
    permission_required,
)
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views.utils import build_cancel_path
from creme.persons import get_contact_model

from ..forms.vcf import VcfForm, VcfImportForm
from ..vcfgenerator import VcfGenerator

Contact = get_contact_model()


def abstract_vcf_import(request, file_form=VcfForm, import_form=VcfImportForm,
                        template='creme_core/generics/blockform/add.html',
                        title=_('Import contact from VCF file'),
                        ):
    user = request.user
    submit_label = Contact.save_label

    if request.method == 'POST':
        POST = request.POST
        step = get_from_POST_or_404(POST, 'vcf_step', cast=int, default=0)
        form_instance = file_form(user=user, data=POST, files=request.FILES)

        if step == 0:
            if form_instance.is_valid():
                form_instance = import_form(
                    user=user,
                    vcf_data=form_instance.cleaned_data['vcf_file'],
                    initial={'vcf_step': 1},
                )
            else:
                submit_label = _('Import this VCF file')
        else:
            if step != 1:
                raise Http404('"vcf_step" must be in {0, 1}')

            form_instance = import_form(user=user, data=POST)

            if form_instance.is_valid():
                contact = form_instance.save()
                return redirect(contact)

        cancel_url = POST.get('cancel_url')
    else:
        form_instance = file_form(user=user, initial={'vcf_step': 0})
        submit_label = _('Import this VCF file')
        cancel_url = build_cancel_path(request)

    return render(
        request, template,
        {
            'form':         form_instance,
            'title':        title,
            'submit_label': submit_label,
            'cancel_url':   cancel_url,
        },
    )


@login_required
@permission_required(('persons', cperm(Contact)))
def vcf_import(request):
    return abstract_vcf_import(request)


@login_required
@permission_required('persons')
def vcf_export(request, contact_id):
    person = get_object_or_404(Contact, pk=contact_id)
    request.user.has_perm_to_view_or_die(person)

    # vc = VcfGenerator(person).serialize()
    #
    # response = HttpResponse(vc, content_type='text/vcard')
    # response['Content-Disposition'] = 'attachment; filename="{}.vcf"'.format(
    #     smart_str(person.last_name),
    # )
    #
    # return response
    return HttpResponse(
        VcfGenerator(person).serialize(),
        headers={
            'Content-Type': 'text/vcard',
            'Content-Disposition': f'attachment; filename="{smart_str(person.last_name)}.vcf"',
        },
    )
