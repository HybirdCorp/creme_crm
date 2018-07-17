# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.translation import ugettext as _

from ..auth.decorators import login_required
from ..core.batch_process import batch_operator_manager
from ..forms.batch_process import BatchProcessForm
from ..models import Job
from ..utils import get_ct_or_404, jsonify
from .utils import build_cancel_path


@login_required
def batch_process(request, ct_id):
    ct = get_ct_or_404(ct_id)
    user = request.user

    if not user.has_perm(ct.app_label):  # TODO: factorise
        raise PermissionDenied(_(u"You are not allowed to access to this app"))

    if Job.not_finished_jobs(user).count() >= settings.MAX_JOBS_PER_USER:
        return HttpResponseRedirect(reverse('creme_core__my_jobs'))

    if request.method == 'POST':
        POST = request.POST
        # TODO: make 'content_type' a real arg ?
        bp_form = BatchProcessForm(user=user, data=POST, initial={'content_type': ct})

        if bp_form.is_valid():
            return redirect(bp_form.save())

        cancel_url = POST.get('cancel_url')
    else:
        bp_form = BatchProcessForm(user=user,
                                   initial={'content_type': ct,
                                            'filter': request.GET.get('efilter'),
                                           },
                                  )
        cancel_url = build_cancel_path(request)

    return render(request,
                  'creme_core/forms/batch-process.html',
                  {'form':          bp_form,
                   'submit_label':  _(u'Run'),
                   'cancel_url':    cancel_url,
                  }
                 )


@login_required
@jsonify
def get_ops(request, ct_id, field):
    ct = get_ct_or_404(ct_id)

    if not request.user.has_perm(ct.app_label):
        raise PermissionDenied(_(u'You are not allowed to access to this app'))

    field_class = ct.model_class()._meta.get_field(field).__class__

    return [(op_name, str(op))
                for op_name, op in batch_operator_manager.operators(field_class)
           ]
