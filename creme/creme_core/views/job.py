# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2021  Hybird
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

from django.db.transaction import atomic
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme  # is_safe_url
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from ..auth import SUPERUSER_PERM
from ..bricks import JobBrick
from ..core.exceptions import ConflictError
# from ..core.job import JobSchedulerQueue
from ..core.job import get_queue
from ..http import CremeJsonResponse
from ..models import Job
from . import bricks as bricks_views
from . import generic


class Jobs(generic.BricksView):
    template_name = 'creme_core/job/list-all.html'
    permissions = SUPERUSER_PERM


class MyJobs(generic.BricksView):
    template_name = 'creme_core/job/list-mine.html'


class JobDetail(generic.CremeModelDetail):
    model = Job
    template_name = 'creme_core/job/detail.html'
    pk_url_kwarg = 'job_id'

    def check_instance_permissions(self, instance, user):
        jtype = instance.type

        if jtype is None:
            raise Http404(
                gettext(
                    'Unknown job type ({}). Please contact your administrator.'
                ).format(instance.id)
            )

        instance.check_owner_or_die(user)

    def get_list_url(self):
        request = self.request
        list_url = request.GET.get('list_url')
        # list_url_is_safe = list_url and is_safe_url(
        list_url_is_safe = list_url and url_has_allowed_host_and_scheme(
            url=list_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )

        return list_url if list_url_is_safe else reverse('creme_core__my_jobs')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job = self.object
        context['results_bricks'] = job.type.results_bricks
        context['bricks_reload_url'] = reverse('creme_core__reload_job_bricks', args=(job.id,))
        context['list_url'] = self.get_list_url()

        return context


class JobEdition(generic.CremeModelEditionPopup):
    model = Job
    # form_class = ...
    pk_url_kwarg = 'job_id'
    permissions = SUPERUSER_PERM
    title = _('Edit the job «{object}»')

    def check_instance_permissions(self, instance, user):
        super().check_instance_permissions(instance=instance, user=user)

        if instance.user_id is not None:
            raise ConflictError('A non-system job cannot be edited')

    def get_form_class(self):
        config_form = self.object.get_config_form_class()
        if config_form is None:
            raise ConflictError('This job cannot be edited')

        return config_form


class JobEnabling(generic.CheckedView):
    permissions = SUPERUSER_PERM
    job_id_url_kwargs = 'job_id'
    enabled_arg = 'enabled'
    enabled_default = True

    @atomic
    def post(self, *args, **kwargs):
        job = get_object_or_404(
            Job.objects.select_for_update(),
            id=kwargs[self.job_id_url_kwargs],
        )

        if job.user_id is not None:
            raise ConflictError('A non-system job cannot be disabled')

        job.enabled = kwargs.get(self.enabled_arg, self.enabled_default)
        job.save()

        return HttpResponse()


class JobDeletion(generic.CremeModelDeletion):
    model = Job
    job_id_url_kwarg = 'job_id'

    def check_instance_permissions(self, instance, user):
        if instance.user_id is None:
            raise ConflictError('A system job cannot be cleared')

        instance.check_owner_or_die(user)

        if not instance.is_finished:
            raise ConflictError('A non finished job cannot be cleared')

    def get_query_kwargs(self):
        return {'id': self.kwargs[self.job_id_url_kwarg]}

    def get_ajax_success_url(self):
        return self.get_success_url()

    def get_success_url(self):
        # TODO: callback_url?
        return self.request.POST.get('back_url') or reverse('creme_core__my_jobs')


class JobsInformation(generic.CheckedView):
    response_class = CremeJsonResponse
    job_ids_arg = 'id'

    def get_job_ids(self):
        return [
            int(ji)
            for ji in self.request.GET.getlist(self.job_ids_arg)
            if ji.isdigit()
        ]

    def get_job_info(self, *, job, queue, queue_error):
        if not job.check_owner(self.request.user):
            info = 'Job is not allowed'
        else:
            ack_errors = job.ack_errors

            # NB: we check 'error' too, to avoid flooding queue/job_manager.
            if ack_errors and not queue_error:
                queue_error = queue.start_job(job) if job.user else job.refresh()
                if not queue_error:
                    job.forget_ack_errors()
                    ack_errors = 0  # TODO: read again from DB ?

            progress = job.progress

            info = {
                'status': job.status,
                'ack_errors': ack_errors,
                'progress': progress.data,
            }

        return info

    def get_jobs_info(self):
        info = {}
        # queue = JobSchedulerQueue.get_main_queue()
        queue = get_queue()

        error = queue.ping()
        if error is not None:
            info['error'] = error

        job_ids = self.get_job_ids()

        if job_ids:
            jobs = Job.objects.in_bulk(job_ids)

            for job_id in job_ids:
                job = jobs.get(job_id)
                info[job_id] = 'Invalid job ID' if job is None else self.get_job_info(
                    job=job, queue=queue, queue_error=error,
                )

        return info

    def get(self, *args, **kwargs):
        return self.response_class(self.get_jobs_info())


class JobBricksReloading(bricks_views.BricksReloading):
    check_bricks_permission = False
    job_id_url_kwarg = 'job_id'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.job = None

    def get_bricks(self):
        job = self.get_job()
        bricks = []
        results_bricks = None

        for brick_id in self.get_brick_ids():
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

        return bricks

    def get_bricks_context(self):
        context = super().get_bricks_context()
        context['job'] = self.get_job()

        return context

    def get_job(self):
        job = self.job

        if job is None:
            self.job = job = get_object_or_404(
                Job,
                id=self.kwargs[self.job_id_url_kwarg],
            )
            job.check_owner_or_die(self.request.user)

        return job
