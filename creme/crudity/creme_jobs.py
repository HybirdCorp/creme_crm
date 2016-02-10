# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _, ungettext

from creme.creme_core.creme_jobs.base import JobType
from creme.creme_core.models import JobResult

from .views.actions import _fetch


logger = logging.getLogger(__name__)
User = get_user_model()


class _CruditySynchronizeType(JobType):
    id           = JobType.generate_id('crudity', 'synchronization')
    verbose_name = _('Synchronize externals data sent to Creme')
    periodic     = JobType.PERIODIC

    def _execute(self, job):
        try:
            # TODO: retrieve user by username ??
            # TODO: configuration GUI for job (stores config in job.raw_data) ?
            user = User.objects.get(pk=settings.CREME_GET_EMAIL_JOB_USER_ID)
        except User.DoesNotExist:
            logger.critical("The setting 'CREME_GET_EMAIL_JOB_USER_ID' is invalid (not an user's ID)")
        else:
            # self.stdout.write("There are %s new item(s)" % _fetch(user))
            count = _fetch(user)
            JobResult.objects.create(job=job,
                                     messages=[ungettext('There is %s change',
                                                         'There are %s changes',
                                                         count
                                                        ) % count,
                                              ]
                                    )

    @property
    def results_blocks(self):
        from creme.creme_core.blocks import job_results_block
        return [job_results_block]


crudity_synchronize_type = _CruditySynchronizeType()
jobs = (crudity_synchronize_type,)
