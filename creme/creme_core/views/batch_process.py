################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _

from ..auth.decorators import login_required
from ..core.batch_process import batch_operator_manager
from ..core.exceptions import BadRequestError
from ..forms.batch_process import BatchProcessForm
from ..http import CremeJsonResponse
from ..models import Job
from ..utils import workflow
from ..utils.content_type import get_ctype_or_404
from . import generic
from .utils import build_cancel_path


@login_required
def batch_process(request, ct_id):
    ct = get_ctype_or_404(ct_id)
    user = request.user

    user.has_perm_to_access_or_die(ct.app_label)

    if Job.objects.not_finished(user).count() >= settings.MAX_JOBS_PER_USER:
        return HttpResponseRedirect(reverse('creme_core__my_jobs'))

    if request.method == 'POST':
        POST = request.POST
        # TODO: make 'content_type' a real arg ?
        bp_form = BatchProcessForm(user=user, data=POST, initial={'content_type': ct})

        if bp_form.is_valid():
            return redirect(bp_form.save())

        cancel_url = POST.get('cancel_url')
    else:
        bp_form = BatchProcessForm(
            user=user,
            initial={
                'content_type': ct,
                'filter': request.GET.get('efilter'),
            },
        )
        cancel_url = build_cancel_path(request)

    return render(
        request,
        'creme_core/forms/batch-process.html',
        {
            'form':          bp_form,
            'submit_label':  _('Run'),
            'cancel_url':    cancel_url,
            # TODO: unit test
            'help_message': workflow.form_help_message(model=ct.model_class()),
        },
    )


class OperatorChoices(generic.base.EntityCTypeRelatedMixin, generic.CheckedView):
    response_class = CremeJsonResponse
    field_url_kwarg = 'field'
    operator_manager = batch_operator_manager

    def get_field_name(self):
        return self.kwargs[self.field_url_kwarg]

    def get_field_class(self):
        model = self.get_ctype().model_class()

        try:
            return type(model._meta.get_field(self.get_field_name()))
        except FieldDoesNotExist as e:
            raise BadRequestError(str(e))

    def get(self, *args, **kwargs):
        return self.response_class(
            [
                (op_name, str(op))
                for op_name, op in self.operator_manager.operators(self.get_field_class())
            ],
            safe=False,  # Result is not a dictionary
        )
