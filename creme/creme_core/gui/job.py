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

from django.utils.translation import gettext_lazy as _

from ..models import EntityJobResult, Job, JobResult
from .bricks import QuerysetBrick


class JobResultsBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('creme_core', 'job_results')
    verbose_name = _('Results')
    dependencies = (JobResult,)
    order_by = 'id'
    template_name = 'creme_core/bricks/job-results.html'
    configurable = False
    page_size = 50

    def _build_queryset(self, job):
        return self.dependencies[0].objects.filter(job=job)

    def _extra_context(self, job):
        return {}

    def detailview_display(self, context):
        job = context['job']

        return self._render(self.get_template_context(
            context, self._build_queryset(job),
            **self._extra_context(job)
        ))


class JobErrorsBrick(JobResultsBrick):
    id = QuerysetBrick.generate_id('creme_core', 'job_errors')
    verbose_name = _('Errors')
    template_name = 'creme_core/bricks/job-errors.html'

    def _build_queryset(self, job):
        return super()._build_queryset(job).filter(messages__isnull=False)

    def _extra_context(self, job):
        return {'JOB_ERROR': Job.STATUS_ERROR}


class EntityJobErrorsBrick(JobErrorsBrick):
    id = QuerysetBrick.generate_id('creme_core', 'entity_job_errors')
    # verbose_name = 'Entity job errors'
    dependencies = (EntityJobResult,)
    template_name = 'creme_core/bricks/entity-job-errors.html'

    def _build_queryset(self, job):
        return super()._build_queryset(job).prefetch_related('real_entity')
