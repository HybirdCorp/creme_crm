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

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from django.apps import apps
from django.template.loader import get_template
from django.utils.timezone import now

from ..apps import CremeAppConfig
from ..models import Job, JobResult

if TYPE_CHECKING:
    from ..bricks import JobErrorsBrick
    from ..forms.job import JobForm

logger = logging.getLogger(__name__)


class JobProgress:
    template_name: str = 'creme_core/job/progress.html'

    def __init__(self, percentage: Optional[int], label: str = ''):
        """Constructor.

        @param percentage: percentage of the progress (eg: 53 for '53%').
               None means that we cannot precise a percentage
               (so an 'infinite' loop should be displayed).
        @param label: string corresponding to the progress
               (eg: "53 entities have been processed").
               If the label is empty, the percentage will be used.
        """
        self.percentage = percentage
        self.label = label

    @property
    def data(self) -> Dict[str, Any]:
        """Data stored a 'JSONifiable' dictionary."""
        return {
            'percentage': self.percentage,
            'label':      self.label,
        }

    def render(self) -> str:
        """HTML rendering."""
        template = self.template_name
        return get_template(template).render({'progress': self}) if template else ''


class JobType:
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

    id: str = ''   # Overload with a string ; use generate_id()
    verbose_name: str = 'JOB'  # Overload with a gettext_lazy object
    periodic: int = NOT_PERIODIC

    class Error(Exception):
        pass

    def __str__(self):
        return str(self.verbose_name)

    def _execute(self, job: Job):
        "TO BE OVERLOADED BY CHILD CLASSES"
        raise NotImplementedError

    @property
    def app_config(self) -> CremeAppConfig:
        return apps.get_app_config(self.id[:self.id.find('-')])

    @property
    def results_bricks(self) -> List['JobErrorsBrick']:
        from ..bricks import JobErrorsBrick
        return [JobErrorsBrick()]

    # NB: we do not use __call__ because we want to use instances of JobType in template
    def execute(self, job: Job) -> None:
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
            job.error = str(e)
        else:
            job.status = Job.STATUS_OK
            job.error = None

        # job.last_run = now()
        job.save()

        # from ..core.job import JobSchedulerQueue
        # JobSchedulerQueue.get_main_queue().end_job(job)
        from ..core.job import get_queue
        get_queue().end_job(job)

    @staticmethod
    def generate_id(app_label: str, name: str) -> str:
        return f'{app_label}-{name}'

    def get_description(self, job: Job) -> List[str]:
        """Get a humanized description, as a list of strings.
        To be overloaded by child classes.
        """
        return []

    def get_config_form_class(self, job: Job) -> Optional[Type['JobForm']]:
        """Get the configuration form for this job.

        Overload this method if you want a custom form.
        If your job is PERIODIC, your form should inherit creme_core.forms.job.JobForm

        @return A class of form, or None if the job is not configurable.
        """
        if self.periodic == JobType.PERIODIC:
            from ..forms.job import JobForm

            return JobForm

        return None

    def get_stats(self, job: Job) -> List[str]:
        "Get stats as a list of strings. To be overloaded by child classes."
        return []

    def next_wakeup(self, job: Job, now_value: datetime) -> Optional[datetime]:
        """Returns the next time when the job manager should wake up the related
        job. It is only meaningful for PSEUDO_PERIODIC type.
        @param job: <creme_core.models.Job> instance (related to this type).
        @param now_value: <datetime> object representing 'now'.
        @return <None> -> the job has not to be woke up.
                A <datetime> instance -> the job should be woke up at this time.
                If it's in the past, it means the job should be run immediately
                (tip: you can simply return 'now_value').
        """
        if self.periodic != self.PSEUDO_PERIODIC:
            raise ValueError(
                'JobType.next_wakeup() should only be called with PSEUDO_PERIODIC jobs.'
            )

        raise NotImplementedError
        # return None  Pycharm's type checker does not like this either

    def progress(self, job: Job) -> JobProgress:
        return JobProgress(percentage=None)

    def refresh_job(self, force: bool = True) -> None:
        from ..models import Job

        try:
            job = Job.objects.get(type_id=self.id)
        except Job.DoesNotExist:
            logger.critical(
                'Job id="%s" does not exist ! Populate script has not been run correctly.',
                self.id,
            )
        else:
            job.refresh(force=force)
