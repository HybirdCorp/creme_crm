# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2020  Hybird
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
from os import remove as delete_file
from os.path import exists

from django.db.models import ProtectedError
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from ..models import FileRef, JobResult
from ..utils.date_period import date_period_registry
from .base import JobType

logger = logging.getLogger(__name__)


class _TempFilesCleanerType(JobType):
    id           = JobType.generate_id('creme_core', 'temp_files_cleaner')
    verbose_name = gettext_lazy('Temporary files cleaner')
    periodic     = JobType.PERIODIC

    def _execute(self, job):
        delay = self.get_delay(job)

        if delay is None:
            JobResult.objects.create(
                job=job,
                messages=[
                    _("The configured delay is invalid. Edit the job's configuration to fix it."),
                ],
            )
        else:
            for temp_file in FileRef.objects.filter(
                    temporary=True,
                    created__lt=now() - delay.as_timedelta(),
            ):
                full_path = temp_file.filedata.path

                if exists(full_path):
                    try:
                        delete_file(full_path)
                    except Exception as e:
                        JobResult.objects.create(
                            job=job,
                            messages=[
                                _(
                                    'An error occurred while deleting the temporary file «{}»'
                                ).format(full_path),
                                _('Original error: {}').format(e),
                            ],
                        )
                        continue
                else:
                    logger.warning(
                        '_TempFilesCleanerType: the file %s has already been deleted.',
                        full_path,
                    )

                try:
                    temp_file.delete()
                except ProtectedError as e:
                    logger.warning(
                        'The FileRef(id=%s) cannot be deleted because of its dependencies: %s',
                        temp_file.id, e.args[1],
                    )
                    JobResult.objects.create(
                        job=job,
                        messages=[
                            _(
                                'The temporary file with id={} cannot be '
                                'deleted because of its dependencies.'
                            ).format(temp_file.id),
                        ],
                    )
                except Exception as e:
                    logger.exception(
                        'Error when trying to delete the FileRef(id=%s)', temp_file.id,
                    )
                    JobResult.objects.create(
                        job=job,
                        messages=[
                            _(
                                'The temporary file with id={} cannot be '
                                'deleted because of an unexpected error.'
                            ).format(temp_file.id),
                            _('Original error: {}').format(e),
                        ],
                    )

    @staticmethod
    def get_delay(job):
        """Returns the delay (TempFile older than it will be removed).
        @param job: Job instance. Its type must be _TempFilesCleanerType.
        @return: A creme_core.utils.date_period.DatePeriod instance, or None in an error occurred.
        """
        try:
            return date_period_registry.deserialize(job.data['delay'])
        except Exception:  # TODO: better exception
            logger.exception('Error in _TempFilesCleanerType.get_delay()')

    def get_description(self, job):
        return [_('Remove old temporary files')]  # TODO: + delay ?

    def get_config_form_class(self, job):
        from ..forms.temp_files_cleaner import TempFilesCleanerJobForm

        return TempFilesCleanerJobForm


temp_files_cleaner_type = _TempFilesCleanerType()
