# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2018  Hybird
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
from django.urls import reverse
from django.utils.http import is_safe_url
from django.utils.translation import ugettext as _

from ..auth.decorators import login_required, superuser_required
from ..bricks import JobBrick
from ..core.exceptions import ConflictError
from ..core.job import JobManagerQueue
from ..models import Job
from ..utils import jsonify

from . import bricks as bricks_views
from .decorators import POST_only
from .generic import inner_popup


@login_required
@superuser_required
def list_all(request):
    return render(request, 'creme_core/job/list-all.html',
                  context={'bricks_reload_url': reverse('creme_core__reload_bricks')},
                  # {'back_url': request.META.get('HTTP_REFERER')} #problem when we come from a deleted job
                 )


@login_required
def list_mine(request):
    return render(request, 'creme_core/job/list-mine.html',
                  context={'bricks_reload_url': reverse('creme_core__reload_bricks')},
                  # {'back_url': request.META.get('HTTP_REFERER')} #problem when we come from a deleted job
                 )


@login_required
def detailview(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    jtype = job.type
    if jtype is None:
        raise Http404(_(u'Unknown job type ({}). Please contact your administrator.').format(job_id))

    job.check_owner_or_die(request.user)

    list_url = request.GET.get('list_url')
    list_url_is_safe = list_url and is_safe_url(
        url=list_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )

    return render(request, 'creme_core/job/detail.html',
                  {'job': job,
                   'results_bricks': jtype.results_bricks,
                   'bricks_reload_url': reverse('creme_core__reload_job_bricks', args=(job.id,)),
                   # 'back_url': request.META.get('HTTP_REFERER'),
                   # 'back_url': '/', #TODO: improve (page before form, not form itself)
                   'list_url': list_url if list_url_is_safe else reverse('creme_core__my_jobs'),
                  }
                 )


@login_required
@superuser_required
def edit(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    if job.user_id is not None:
        raise ConflictError('A non-system job cannot be edited')

    config_form = job.get_config_form_class()
    if config_form is None:
        raise ConflictError('This job cannot be edited')

    if request.method == 'POST':
        edit_form = config_form(user=request.user, data=request.POST, instance=job)

        if edit_form.is_valid():
            edit_form.save()
    else:  # GET request
        edit_form = config_form(user=request.user, instance=job)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {'form':  edit_form,
                        'title': _(u'Edit the job «{}»').format(job.type),
                       },
                       is_valid=edit_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )


@login_required
@superuser_required
@POST_only
def enable(request, job_id, enabled=True):
    job = get_object_or_404(Job, id=job_id)

    if job.user_id is not None:
        raise ConflictError('A non-system job cannot be disabled')

    job.enabled = enabled
    job.save()

    return HttpResponse()


@login_required
@POST_only
def delete(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    if job.user_id is None:
        raise ConflictError('A system job cannot be cleared')

    job.check_owner_or_die(request.user)

    if not job.is_finished:
        raise ConflictError('A non finished job cannot be cleared')

    job.delete()

    url = request.POST.get('back_url') or reverse('creme_core__my_jobs')

    if request.is_ajax():
        # return HttpResponse(content=url, content_type='text/javascript')
        return HttpResponse(content=url)

    return HttpResponseRedirect(url)


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
                    ack_errors = job.ack_errors

                    # NB: we check 'error' too, to avoid flooding queue/job_manager.
                    if ack_errors and not error:
                        queue_error = queue.start_job(job) if job.user else job.refresh()
                        if not queue_error:
                            job.forget_ack_errors()
                            ack_errors = 0  # TODO: read again from DB ?

                    progress = job.progress

                    info[job_id] = {
                        'status':     job.status,
                        'ack_errors': ack_errors,
                        'progress':   progress.data,
                    }

    return info


@login_required
@jsonify
def reload_bricks(request, job_id):
    brick_ids = bricks_views.get_brick_ids_or_404(request)
    job = get_object_or_404(Job, id=job_id)
    bricks = []
    results_bricks = None

    for brick_id in brick_ids:
        if brick_id == JobBrick.id_:
            bricks.append(JobBrick())
        else:
            if results_bricks is None:
                results_bricks = job.type.results_bricks

            for err_brick in results_bricks:
                if brick_id == err_brick.id_:
                    bricks.append(err_brick)
                    break
            else:
                raise Http404('Invalid brick ID')

    job.check_owner_or_die(request.user)

    return bricks_views.bricks_render_info(request, bricks=bricks,
                                           context=bricks_views.build_context(request, job=job),
                                          )