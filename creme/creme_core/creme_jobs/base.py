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

import logging

from django.utils.timezone import now

from ..models import Job, JobResult
from ..registry import creme_registry


logger = logging.getLogger(__name__)


class JobType(object):
    """Each Job (see creme_core.models.Job) has a type, which contains the real
    code to execute, & some meta-data :
        - verbose_name: is used in the Job views, in order to have a user-friendly display.
        - periodic: must be in {NOT_PERIODIC, PSEUDO_PERIODIC, PERIODIC}

    NOT_PERIODIC: one shot Job (eg: CSV import). Must be a User Job.
    PERIODIC: these system Jobs are run every Job.periodicity.as_timedelta().
    PSEUDO_PERIODIC: these Jobs have a dynamic 'period' (so it is not really a period).
                     They can compute the next time they should be run.
    """
    # JobType 'periodic' constants
    NOT_PERIODIC    = 0
    PSEUDO_PERIODIC = 1
    PERIODIC        = 2

    id           = None   # Overload with an unicode object ; use generate_id()
    verbose_name = 'JOB'  # Overload with a ugettext_lazy object
    periodic     = NOT_PERIODIC

    class Error(Exception):
        pass

    def __unicode__(self):
        return unicode(self.verbose_name)

    def _execute(self, job):
        "TO BE OVERLOADED BY CHILD CLASSES"
        raise NotImplementedError

    @property
    def app(self):
        return creme_registry.get_app(self.id[:self.id.find('-')])

    @property
    def results_blocks(self):
        from ..blocks import job_errors_block
        return [job_errors_block]

    def execute(self, job):  # NB: we do not use __call__ because we want to use instances of JobType in template
        if self.periodic != self.NOT_PERIODIC and job.last_run:
            # TODO: 'self.result_model' instead of 'JobResult' ??
            JobResult.objects.filter(job=job).delete()
            job.status = Job.STATUS_WAIT  # TODO: test

        job.last_run = now()
        job.save()

        try:
            self._execute(job)
        except Exception as e:
            logger.exception(e)

            job.status = Job.STATUS_ERROR
            job.error = unicode(e)
        else:
            job.status = Job.STATUS_OK
            job.error = None

        # job.last_run = now()
        job.save()

        from ..core.job import JobManagerQueue
        JobManagerQueue.get_main_queue().end_job(job)

    @staticmethod
    def generate_id(app_name, name):
        return u'%s-%s' % (app_name, name)

    def get_description(self, job):
        """Get a humanized description, as a list of strings.
        To be overloaded by child classes.
        """
        return []

    def get_config_form_class(self, job):
        """Get the configuration form for this job.

        Overload this method if you want a custom form.
        If your job is PERIODIC, your form should inherit creme_core.forms.job.JobForm

        @return A class of form, or None if the job is not configurable.
        """
        if self.periodic == JobType.PERIODIC:
            from ..forms.job import JobForm

            return JobForm

    def get_stats(self, job):
        "Get stats as a list of strings. To be overloaded by child classes."
        return []

    def next_wakeup(self, job, now_value):
        """Returns the next time when the job manager should wake up the related
        job. It is only meaningful for PSEUDO_PERIODIC type.
        @param job: creme_core.models.Job instance (related to this type).
        @param now_value: datetime object representing 'now'.
        @return None -> the job has not to be woke up.
                A datetime instance -> the job should be woke up at this time.
                    If it's in the past, it means the job should be run immediately
                    (tip: you can simply return now_value).
        """
        if self.periodic != self.PSEUDO_PERIODIC:
            raise ValueError('JobType.next_wakeup() should only be called with PSEUDO_PERIODIC jobs.')

        raise NotImplementedError

    def refresh_job(self):
        from ..models import Job

        try:
            job = Job.objects.get(type_id=self.id)
        except Job.DoesNotExist:
            logger.critical('Job id="%s" does not exist ! Populate script has not ben run correctly.',
                            self.id,
                           )
        else:
            if job.enabled:
                job.refresh()
