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

from os.path import splitext

from django.conf import settings
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.encoding import smart_str
from django.utils.translation import gettext as _

from ..auth.decorators import login_required
from ..backends import export_backend_registry
from ..core.exceptions import ConflictError
from ..creme_jobs import mass_import_type
from ..forms.mass_import import (
    UploadForm,
    form_factory,
    get_header,
    get_import_backend_class,
)
from ..gui.mass_import import import_form_registry
from ..models import Job, MassImportJobResult
from ..utils import get_from_POST_or_404
from ..utils.content_type import get_ctype_or_404
from .utils import build_cancel_path

# django wizard doesn't manage to inject its input in the 2nd form
# + we can't upload file with wizard (even if it is a documents.Document for now)


@login_required
def mass_import(request, ct_id):
    ct = get_ctype_or_404(ct_id)

    try:
        import_form_registry.get(ct)
    except import_form_registry.UnregisteredCTypeException as e:
        raise Http404(e) from e

    user = request.user

    # if Job.not_finished_jobs(user).count() >= settings.MAX_JOBS_PER_USER:
    if Job.objects.not_finished(user).count() >= settings.MAX_JOBS_PER_USER:
        return HttpResponseRedirect(reverse('creme_core__my_jobs'))

    model = ct.model_class()
    user.has_perm_to_create_or_die(model)

    submit_label = _('Save the entities')

    if request.method == 'POST':
        POST = request.POST
        step = get_from_POST_or_404(POST, 'step', cast=int, default=0)  # TODO: int -> boundedInt
        form = UploadForm(user=user, data=POST)

        if step == 0:
            if form.is_valid():
                cleaned_data = form.cleaned_data
                # TODO: import_form_registry as attribute is the future CBV
                #       + pass it as argument here
                ImportForm = form_factory(ct, form.header)
                form = ImportForm(
                    user=user,
                    initial={
                        'step':       1,
                        'document':   cleaned_data['document'].id,
                        'has_header': cleaned_data['has_header'],
                    },
                )
            else:
                submit_label = _('Import this file')
        else:
            if step != 1:
                raise Http404('Step should be in (0, 1)')

            form.is_valid()  # Clean fields

            ImportForm = form_factory(ct, form.header)
            form = ImportForm(user=user, data=POST)

            if form.is_valid():
                job = Job.objects.create(
                    user=user,
                    type=mass_import_type,
                    data={
                        'ctype': ct.id,
                        'POST':  POST.urlencode(),
                    },
                )
                return redirect(job)

        cancel_url = POST.get('cancel_url')
    else:
        form = UploadForm(user=user, initial={'step': 0})
        submit_label = _('Import this file')
        cancel_url = build_cancel_path(request)

    return render(
        request,
        'creme_core/generics/blockform/add.html',
        {
            'form': form,
            'title': _('Import «{model}» from data file').format(
                model=model._meta.verbose_name_plural,
            ),
            'cancel_url': cancel_url,
            'submit_label': submit_label,
        },
    )


@login_required
def download_errors(request, job_id):
    job = get_object_or_404(Job, id=job_id, type_id=mass_import_type.id)
    job.check_owner_or_die(request.user)

    # TODO: real API for that...
    POST = mass_import_type._build_POST(job.data)
    doc = mass_import_type._get_document(POST)

    # TODO: improve get_header() & factorise to return the backend too (we retrieve it twice...)
    header = get_header(doc.filedata, has_header='has_header' in POST)
    import_backend_cls, error_msg = get_import_backend_class(doc.filedata)

    if error_msg:
        return ConflictError(error_msg)

    get_export_backend_class = export_backend_registry.get_backend_class
    export_backend_class = (
        get_export_backend_class(import_backend_cls.id)
        or get_export_backend_class(next(export_backend_registry.backend_classes).id)
    )

    if not export_backend_class:
        return ConflictError(_('Unknown file type ; please contact your administrator.'))

    writer = export_backend_class()
    writerow = writer.writerow

    if header:
        writerow([
            *(smart_str(h) for h in header),
            smart_str(_('Errors')),
        ])

    # for job_result in MassImportJobResult.objects.filter(job=job).exclude(raw_messages=None):
    for job_result in MassImportJobResult.objects.filter(
        job=job, messages__isnull=False,
    ):
        writerow([
            *(smart_str(i) for i in job_result.line),
            smart_str('/'.join(job_result.messages)),
        ])

    writer.save(f'{splitext(doc.title)[0]}-errors', request.user)

    return writer.response
