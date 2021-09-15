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
from typing import Optional

from django.utils.translation import activate

from creme.creme_core.creme_jobs.base import JobType
from creme.creme_core.global_info import set_global_info
from creme.creme_core.models import Job
from creme.creme_core.utils.imports import import_apps_sub_modules

logger = logging.getLogger(__name__)


class _JobTypeRegistry:
    class Error(Exception):
        pass

    def __init__(self):
        self._job_types = {}

    def __call__(self, job_id: int) -> None:
        job = Job.objects.get(id=job_id)
        job_type = self.get(job.type_id)

        if job_type is None:
            raise _JobTypeRegistry.Error(f'Invalid job type ID: {job.type_id}')

        # Configure environment
        activate(job.language)
        set_global_info(user=job.user)

        job_type.execute(job)

    def get(self, job_type_id: str) -> Optional[JobType]:
        try:
            return self._job_types[job_type_id]
        except KeyError:
            logger.critical('Unknown JobType: %s', job_type_id)

        return None

    def register(self, job_type: JobType) -> None:
        jtype_id = job_type.id

        if not jtype_id:
            raise _JobTypeRegistry.Error(f'Empty JobType id: {job_type}')

        if self._job_types.setdefault(jtype_id, job_type) is not job_type:
            raise _JobTypeRegistry.Error(f'Duplicated job type id: {jtype_id}')

    def autodiscover(self) -> None:
        register = self.register

        for jobs_import in import_apps_sub_modules('creme_jobs'):
            for job in getattr(jobs_import, 'jobs', ()):
                register(job)
