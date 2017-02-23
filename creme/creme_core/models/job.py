# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2017  Hybird
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

from json import dumps as jsondumps, loads as jsonloads
import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import (Model, CharField, TextField, DateTimeField,
        PositiveIntegerField, PositiveSmallIntegerField, BooleanField,
        ForeignKey, F)
from django.db.transaction import atomic
from django.utils.timezone import now
from django.utils.translation import get_language, ugettext_lazy as _

from ..utils.dates import round_hour
from ..utils.date_period import HoursPeriod
from .entity import CremeEntity
from .fields import CremeUserForeignKey, DatePeriodField  # CreationDateTimeField

logger = logging.getLogger(__name__)


class Job(Model):
    """A job represents a work which has to be done in the 'background' (ie:
    another process than the processes which respond to the clients). They are
    useful for periodic tasks (eg: polling data, like emails, from another server)
    or long tasks (eg: generating a lot of data).

    The type of the job (see creme_core.creme_jobs.base.JobType) determines if
    the job is periodic, pseudo-periodic or not periodic.

    Periodic & pseudo-periodic (see JobType for the difference between them)
    Jobs must be 'system' Job:
        - they are created in 'populate' scripts.
        - they have no user.
        - they can not be deleted, but they can be disabled (see 'enabled' field).
        - periodic Jobs must have their 'periodicity' field filled.
        - pseudo-periodic Jobs should not have their 'periodicity' field filled,
          because it is useless ; the value settings.PSEUDO_PERIOD is used as
          security period instead.

    Not periodic Jobs are user Jobs:
        - they are dynamically created by a view.
        - they must have their 'user' filled; it correspond to the User which
          have created the Job, & who owns it. The Job should act with the
          credentials of this User.
        - A view which creates a Job should check settings.MAX_JOBS_PER_USER
          before creating a Job, and redirect to the jobs list view if the Job
          can not be created.
        - They have to be deleted once they are finished, in order to create
          other user Jobs.

    The 'reference_run' field is always filled (in an automatic way at least),
    but does not means anything for not periodic Jobs ; in this case it is only
    the creation date, which is not very useful. The 'reference_run' is used to
    compute the time of each execution, which must be something like:
        reference_run + N * periodicity
    """
    STATUS_WAIT  = 1
    STATUS_ERROR = 10
    STATUS_OK    = 20

    type_id       = CharField(_('Type of job'), max_length=48, editable=False)
    user          = CremeUserForeignKey(verbose_name=_('User'), null=True, editable=False)
    enabled       = BooleanField(_('Enabled'), default=True, editable=False)
    language      = CharField(_('Language'), max_length=10, editable=False)
    # created      = CreationDateTimeField(_('Creation date'))
    reference_run = DateTimeField(_('Reference run'))
    periodicity   = DatePeriodField(_('Periodicity'), null=True)
    last_run      = DateTimeField(_('Last run'), null=True, editable=False)
    ack_errors    = PositiveIntegerField(default=0, editable=False)
    status        = PositiveSmallIntegerField(_('Status'), editable=False,
                                              default=STATUS_WAIT,
                                              choices=((STATUS_WAIT,  _(u'Waiting')),
                                                       (STATUS_ERROR, _(u'Error')),
                                                       (STATUS_OK,    _(u'Completed successfully')),
                                                      ),
                                             )
    error         = TextField(_('Error'), null=True, editable=False)
    raw_data      = TextField(editable=False)  # It stores the Job's parameters  # TODO: use a JSONField ?

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Job')
        verbose_name_plural = _(u'Jobs')
        # ordering = ('created',)
        ordering = ('id',)

    def __init__(self, *args, **kwargs):
        super(Job, self).__init__(*args, **kwargs)
        if not self.language:
            self.language = get_language()

        self.__init_refreshing_cache()

    def __init_refreshing_cache(self):
        self._old_periodicity = self.periodicity
        self._old_reference_run = self.reference_run
        self._old_enabled = self.enabled

    def __unicode__(self):
        return unicode(self.type)

    def __repr__(self):
        return u'<Job type="%s" id="%s">' % (self.type.id, self.id)

    def get_absolute_url(self):
        # return '/creme_core/job/%s' % self.id
        return reverse('creme_core__job', args=(self.id,))

    def get_delete_absolute_url(self):
        return reverse('creme_core__delete_job', args=(self.id,))

    def get_edit_absolute_url(self):
        # return '/creme_core/job/%s/edit' % self.id
        return reverse('creme_core__edit_job', args=(self.id,))

    @property
    def data(self):
        return jsonloads(self.raw_data)  # TODO: cache

    @data.setter
    def data(self, value):
        self.raw_data = jsondumps(value)

    @property
    def description(self):  # TODO: cache ?
        try:
            return self.type.get_description(self)
        except Exception:
            logger.exception('Error when building the description of the job id="%s"', self.id)

        return ()

    def check_owner(self, user):
        return user.is_superuser or self.user == user

    def check_owner_or_die(self, user):
        if not self.check_owner(user):
            raise PermissionDenied('You are not the owner of this job')

    @property
    def is_finished(self):
        return self.status != self.STATUS_WAIT

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

    def refresh(self):
        """Ask to the JobManager to refresh the job, because the next runs should
        be earlier, or disabled.
        """
        from ..core.job import JobManagerQueue

        queue_error = JobManagerQueue.get_main_queue().refresh_job(self)
        self.__init_refreshing_cache()

        return queue_error

    @atomic
    def save(self, *args, **kwargs):
        from ..core.job import JobManagerQueue

        created = self.pk is None

        if created and self.reference_run is None:
            self.reference_run = now()

            if self.user_id is None:  # System job
                self.reference_run = round_hour(self.reference_run)

        super(Job, self).save(*args, **kwargs)

        queue_error = False

        if created:
            if self.user_id is not None:
                queue_error = JobManagerQueue.get_main_queue().start_job(self)
        elif self.user_id is None:  # System job
            if self._old_periodicity != self.periodicity or \
               self._old_reference_run != self.reference_run or \
               self._old_enabled != self.enabled:
                queue_error = self.refresh()

        if queue_error:
            self._update_ack_errors(1)

    @property
    def stats(self):
        return self.type.get_stats(self)

    @property
    def type(self):
        from ..core.job import job_type_registry
        return job_type_registry.get(self.type_id)

    @type.setter
    def type(self, value):
        # TODO: check that it is in job_type_registry ?
        self.type_id = value.id


class BaseJobResult(Model):
    job          = ForeignKey(Job)
    raw_messages = TextField(null=True)  # TODO: use a JSONField ?

    class Meta:
        app_label = 'creme_core'
        abstract = True

    def __repr__(self):
        return 'JobResult(job=%s, raw_messages="%s")' % (
                    self.job_id, self.raw_messages,
                )

    @property
    def messages(self):  # TODO: cache ?
        raw_messages = self.raw_messages
        return None if raw_messages is None else jsonloads(raw_messages)

    @messages.setter
    def messages(self, value):
        # TODO: None if not value
        self.raw_messages = jsondumps(value)


class JobResult(BaseJobResult):
    class Meta(BaseJobResult.Meta):
        abstract = False


class EntityJobResult(BaseJobResult):
    entity = ForeignKey(CremeEntity, null=True)

    # class Meta(BaseJobResult.Meta):
    #     abstract = False

    def __repr__(self):
        return 'EntityJobResult(job=%s, raw_messages="%s", entity=%s)' % (
                    self.job_id, self.raw_messages, self.entity_id,
                )


class MassImportJobResult(BaseJobResult):
    entity   = ForeignKey(CremeEntity, null=True)
    raw_line = TextField()  # TODO: use a JSONField ?
    updated  = BooleanField(default=False)  # False: entity created
                                            # True: entity updated

    # class Meta(BaseJobResult.Meta):
    #     abstract = False

    def __repr__(self):
        return 'MassImportJobResult(job=%s, raw_messages="%s", entity=%s, raw_line="%s", updated=%s)' % (
                    self.job_id, self.raw_messages, self.entity_id, self.raw_line, self.updated,
                )

    @property
    def line(self):  # TODO: cache ?
        return jsonloads(self.raw_line)

    @line.setter
    def line(self, value):
        "@param value: List of strings"
        self.raw_line = jsondumps(value)
