################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2025  Hybird
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

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import F, QuerySet
from django.db.transaction import atomic
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ..utils.date_period import HoursPeriod, date_period_registry
from ..utils.dates import dt_from_ISO8601, dt_to_ISO8601, round_hour
from . import fields as core_fields
from .entity import CremeEntity

if TYPE_CHECKING:
    from ..creme_jobs.base import JobType

logger = logging.getLogger(__name__)


class JobManager(models.Manager):
    def not_finished(self, user) -> QuerySet:
        return self.filter(user=user, status=self.model.STATUS_WAIT)


class Job(models.Model):
    """A job represents a work which has to be done in the 'background'
    (i.e. another process than the processes which respond to the clients).
    They are useful for periodic tasks (e.g. polling data, like emails, from
    another server) or long tasks (e.g. generating a lot of data).

    The type of the job (see creme_core.creme_jobs.base.JobType) determines if
    the job is periodic, pseudo-periodic or not periodic.

    Periodic & pseudo-periodic (see JobType for the difference between them) Jobs
    must be 'system' Job:
        - they are created in 'populate' scripts.
        - they have no user.
        - they can not be deleted, but they can be disabled (see 'enabled' field).
        - periodic Jobs must have their 'periodicity' field filled.
        - pseudo-periodic Jobs should not have their 'periodicity' field filled,
          because it is useless ; the value settings.PSEUDO_PERIOD is used as
          security period instead.

    Not periodic Jobs are user Jobs:
        - they are dynamically created by a view.
        - they must have their 'user' filled; it corresponds to the User which
          have created the Job, & who owns it. The Job should act with the
          credentials of this User.
        - A view which creates a Job should check settings.MAX_JOBS_PER_USER
          before creating a Job, and redirect to the jobs list view if the Job
          can not be created (tip: you can use Job.not_finished_jobs()).
        - They have to be deleted once they are finished, in order to create
          other user Jobs.

    The 'reference_run' field is always filled (in an automatic way at least),
    but does not mean anything for not periodic Jobs ; in this case it is only
    the creation date, which is not very useful. The 'reference_run' is used to
    compute the time of each execution, which must be something like:
        reference_run + N * periodicity
    """
    STATUS_WAIT  = 1
    STATUS_ERROR = 10
    STATUS_OK    = 20

    type_id = models.CharField(_('Type of job'), max_length=48, editable=False)
    user = core_fields.CremeUserForeignKey(
        verbose_name=_('User'), null=True, editable=False,
    )
    enabled = models.BooleanField(
        pgettext_lazy('creme_core-job', 'Enabled'), default=True, editable=False,
    )
    language = models.CharField(_('Language'), max_length=10, editable=False)
    # created = CreationDateTimeField(_('Creation date'))

    reference_run = models.DateTimeField(_('Reference run'))
    periodicity = core_fields.DatePeriodField(_('Periodicity'), null=True)
    last_run = models.DateTimeField(_('Last run'), null=True, editable=False)

    # Number of errors of communication with the queue.
    ack_errors = models.PositiveIntegerField(default=0, editable=False)

    status = models.PositiveSmallIntegerField(
        _('Status'), editable=False,
        default=STATUS_WAIT,
        choices=(
            (STATUS_WAIT,  _('Waiting')),
            (STATUS_ERROR, _('Error')),
            (STATUS_OK,    _('Completed successfully')),
        ),
    )
    error = models.TextField(_('Error'), null=True, editable=False)

    # It stores the Job's parameters
    data = models.JSONField(editable=False, null=True)

    objects = JobManager()

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Job')
        verbose_name_plural = _('Jobs')
        ordering = ('id',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.language:
            self.language = get_language()

        self.__init_refreshing_cache()

    def __init_refreshing_cache(self):
        self._old_periodicity = self.periodicity
        self._old_reference_run = self.reference_run
        self._old_enabled = self.enabled

    def __str__(self):
        return str(self.type)

    def __repr__(self):
        return f'<Job type="{self.type_id}" id="{self.id}">'

    def get_absolute_url(self):
        return reverse('creme_core__job', args=(self.id,))

    def get_delete_absolute_url(self):
        return reverse('creme_core__delete_job', args=(self.id,))

    def get_edit_absolute_url(self):
        return reverse('creme_core__edit_job', args=(self.id,))

    @property
    def description(self) -> list[str]:  # TODO: cache ?
        jtype = self.type

        if jtype is None:
            logger.warning(
                'Cannot build the description of job id="%s" (invalid job type)', self.id,
            )
        else:
            try:
                return jtype.get_description(self)
            except Exception:
                logger.exception(
                    'Error when building the description of the job id="%s"', self.id,
                )

        return []

    def check_owner(self, user) -> bool:
        return user.is_superuser or self.user == user

    def check_owner_or_die(self, user) -> None:
        if not self.check_owner(user):
            raise PermissionDenied('You are not the owner of this job')

    @property
    def is_finished(self) -> bool:
        return self.status != self.STATUS_WAIT

    @property
    def progress(self):
        jtype = self.type

        if jtype is not None:
            return jtype.progress(self)

    @property
    def real_periodicity(self):
        periodicity = self.periodicity

        if periodicity is None and self.user_id is None:
            periodicity = HoursPeriod(value=settings.PSEUDO_PERIOD)

        return periodicity

    def _update_ack_errors(self, incr):
        Job.objects.filter(id=self.id).update(ack_errors=F('ack_errors') + incr)

    def forget_ack_errors(self):
        self._update_ack_errors(- self.ack_errors)

    def get_config_form_class(self):
        "@see JobType.get_config_form_class()"
        jtype = self.type
        return jtype.get_config_form_class(self) if jtype is not None else None

    def refresh(self, force: bool = False):
        """Ask the JobScheduler to refresh the job if it's needed, because
        the next runs should be earlier, or disabled.
        @param force: <True> means the message is sent even if no field has changed.
        """
        from ..core.job import get_queue

        queue_error = False
        enabled = self.enabled
        reference_run = self.reference_run
        periodicity = self.periodicity

        if (
            self._old_enabled != enabled
            or self._old_reference_run != reference_run
            or self._old_periodicity != periodicity
            or force
        ):  # NB: we sent all the fields values in order to get a more robust system
            #     (even if a REFRESH-message is lost, the next one is complete).
            data = {
                'enabled':       enabled,
                'reference_run': dt_to_ISO8601(reference_run),
            }

            if periodicity:
                data['periodicity'] = periodicity.as_dict()

            queue_error = get_queue().refresh_job(self, data)
            self.__init_refreshing_cache()

        return queue_error

    def update(self,
               refresh_data,
               date_period_registry=date_period_registry,
               ) -> bool:
        """Update the fields with information generated by refresh().

        Notice that the instance is not saved.

        @param refresh_data: Dictionary. See data sent on queue by refresh().
        @param date_period_registry: Instance of creme_core.utils.date_period.DatePeriodRegistry.
        @return: True if the instance has changed.
        """
        changed = False
        get = refresh_data.get

        enabled = get('enabled')
        if enabled is not None:
            if self.enabled != enabled:
                self.enabled = enabled
                changed = True

        ref_run_str = get('reference_run')
        if ref_run_str is not None:
            ref_run = dt_from_ISO8601(ref_run_str)

            if self.reference_run != ref_run:
                self.reference_run = ref_run
                changed = True

        periodicity_dict = get('periodicity')
        if periodicity_dict is not None:
            periodicity = date_period_registry.deserialize(periodicity_dict)

            if self.periodicity != periodicity:
                self.periodicity = periodicity
                changed = True

        return changed

    @atomic
    def save(self, *args, **kwargs):
        from ..core.job import get_queue

        created = self.pk is None

        if created and self.reference_run is None:
            self.reference_run = now()

            if self.user_id is None:  # System job
                self.reference_run = round_hour(self.reference_run)

        super().save(*args, **kwargs)

        queue_error = False

        if created:
            if self.user_id is not None:
                queue_error = get_queue().start_job(self)
        elif self.user_id is None:  # System job
            queue_error = self.refresh()

        if queue_error:
            self._update_ack_errors(1)

    @property
    def stats(self) -> list[str]:
        jtype = self.type
        return jtype.get_stats(self) if jtype is not None else []

    @property
    def type(self) -> JobType | None:
        from ..core.job import job_type_registry
        return job_type_registry.get(self.type_id)

    @type.setter
    def type(self, value: JobType):
        # TODO: check that it is in job_type_registry ?
        self.type_id = value.id


class BaseJobResult(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    messages = models.JSONField(null=True)

    class Meta:
        app_label = 'creme_core'
        abstract = True

    def __repr__(self):
        return f'JobResult(job={self.job_id}, messages={self.messages})'


class JobResult(BaseJobResult):
    class Meta(BaseJobResult.Meta):
        abstract = False


class EntityJobResult(BaseJobResult):
    entity_ctype = core_fields.EntityCTypeForeignKey(
        related_name='+', editable=False, null=True,
    )
    entity = models.ForeignKey(CremeEntity, null=True, on_delete=models.CASCADE)
    real_entity = core_fields.RealEntityForeignKey(
        ct_field='entity_ctype', fk_field='entity',
    )

    def __repr__(self):
        return (
            f'EntityJobResult('
            f'job={self.job_id}, '
            f'messages={self.messages}, '
            f'entity_ctype={self.entity_ctype}, '
            f'entity={self.entity_id}'
            f')'
        )


class MassImportJobResult(BaseJobResult):
    entity_ctype = core_fields.EntityCTypeForeignKey(
        null=True, related_name='+', editable=False,
    )
    entity = models.ForeignKey(CremeEntity, null=True, on_delete=models.CASCADE)
    real_entity = core_fields.RealEntityForeignKey(
        ct_field='entity_ctype', fk_field='entity',
    )

    line = models.JSONField(default=list)

    # False: entity created / True: entity updated
    updated = models.BooleanField(default=False)

    def __repr__(self):
        return (
            f'MassImportJobResult('
            f'job={self.job_id}, '
            f'messages={self.messages}, '
            f'entity={self.entity_id}, '
            f'line={self.line}, '
            f'updated={self.updated}'
            f')'
        )
