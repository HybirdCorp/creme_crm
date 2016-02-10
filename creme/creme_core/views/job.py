# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016  Hybird
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

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext as _

from ..auth.decorators import login_required, superuser_required
from ..blocks import job_block
from ..creme_jobs.base import JobType
from ..core.exceptions import ConflictError
from ..core.job import JobManagerQueue
from ..forms.job import JobForm
from ..models import Job
from ..utils import jsonify
from .blocks import build_context
from .decorators import POST_only
from .generic import inner_popup


@login_required
def listview(request):
    return render(request, 'creme_core/jobs.html',
                  # {'back_url': request.META.get('HTTP_REFERER')} #problem when we went from a deleted job
                 )


@login_required
def detailview(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    job.check_owner_or_die(request.user)

    return render(request, 'creme_core/job.html',
                  {'job': job,
                   'results_blocks': job.type.results_blocks,
                   # 'back_url': request.META.get('HTTP_REFERER'),
                   # 'back_url': '/', #TODO: improve (page before form, not form itself)
                  }
                 )


@login_required
@superuser_required
def edit(request, job_id):
    job = get_object_or_404(Job, pk=job_id)

    if job.user_id is not None:
        raise ConflictError('A non-system job cannot be edited')

    if job.type.periodic != JobType.PERIODIC:
        raise ConflictError('A non-periodic job cannot be edited')

    if request.method == 'POST':
        edit_form = JobForm(user=request.user, data=request.POST, instance=job)

        if edit_form.is_valid():
            edit_form.save()
    else:  # GET request
        edit_form = JobForm(user=request.user, instance=job)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {'form':  edit_form,
                        'title': _(u'Edit the job «%s»') % job.type,
                       },
                       is_valid=edit_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )


@login_required
@superuser_required
@POST_only
def enable(request, job_id, enabled=True):
    job = get_object_or_404(Job, pk=job_id)

    if job.user_id is not None:
        raise ConflictError('A non-system job cannot be disabled')

    job.enabled = enabled
    job.save()

    return HttpResponse()


@login_required
@POST_only
def delete(request, job_id):
    job = get_object_or_404(Job, pk=job_id)

    if job.user_id is None:
        raise ConflictError('A system job cannot be cleared')

    job.check_owner_or_die(request.user)

    if not job.is_finished:
        raise ConflictError('A non finished job cannot be cleared')

    job.delete()

    if request.is_ajax():
        return HttpResponse()

    return HttpResponseRedirect('/creme_core/job/all')


@login_required
@jsonify
def get_info(request):
    info = {}
    queue = JobManagerQueue.get_main_queue()

    error = queue.ping()
    if error is not None:
        info['error'] = error

    job_ids = [int(ji) for ji in request.GET.getlist('id') if ji.isdigit()]

    if job_ids:
        user = request.user
        jobs = Job.objects.in_bulk(job_ids)

        for job_id in job_ids:
            job = jobs.get(job_id)
            if job is None:
                info[job_id] = 'Invalid job ID'
            else:
                if not job.check_owner(user):
                    info[job_id] = 'Job is not allowed'
                else:
                    # TODO: other info -> progress, progress label, is finished
                    ack_errors = job.ack_errors

                    if ack_errors and not error:  # NB: we check 'error' too, to avoid flooding queue/job_manager.
                        queue_error = queue.start_job(job) if job.user else job.refresh()
                        if not queue_error:
                            job.forget_ack_errors()
                            ack_errors = 0  # TODO: read again from DB ?

                    info[job_id] = {'status': job.status, 'ack_errors': ack_errors}

    return info


@login_required
@jsonify
def reload_block(request, job_id, block_id):
    job = get_object_or_404(Job, pk=job_id)

    if block_id == job_block.id_:
        block = job_block
    else:
        for err_block in job.type.results_blocks:
            if block_id == err_block.id_:
                block = err_block
                break
        else:
            raise Http404('Invalid block ID')

    job.check_owner_or_die(request.user)

    context = build_context(request)
    context['job'] = job

    return [(block.id_, block.detailview_display(context))]
