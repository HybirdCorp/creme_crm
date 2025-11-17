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

import logging

from django.contrib.contenttypes.models import ContentType
from django.http import QueryDict
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from creme.documents import get_document_model

from ..constants import UUID_CHANNEL_JOBS
from ..forms.mass_import import form_factory, get_header
from ..gui.job import JobErrorsBrick
from ..models import MassImportJobResult, Notification
from ..models.utils import model_verbose_name
from ..notification import MassImportDoneContent
from ..utils.translation import smart_model_verbose_name
from .base import JobProgress, JobType

logger = logging.getLogger(__name__)


class MassImportJobErrorsBrick(JobErrorsBrick):
    id = JobErrorsBrick.generate_id('creme_core', 'mass_import_job_errors')
    # verbose_name  = 'Mass import job errors'
    dependencies = (MassImportJobResult,)
    template_name = 'creme_core/bricks/massimport-errors.html'

    def _build_queryset(self, job):
        return super()._build_queryset(job).prefetch_related('real_entity')


class _MassImportType(JobType):
    id           = JobType.generate_id('creme_core', 'mass_import')
    verbose_name = _('Mass import')

    def _build_POST(self, job_data):
        return QueryDict(job_data['POST'].encode('utf8'))

    def _get_document(self, POST):
        return get_document_model().objects.get(id=POST['document'])

    def _get_ctype(self, job_data):
        return ContentType.objects.get_for_id(job_data['ctype'])

    def _execute(self, job):
        job_data = job.data
        POST = self._build_POST(job_data)
        doc = self._get_document(POST)
        header = get_header(doc.filedata, has_header='has_header' in POST)
        form_class = form_factory(self._get_ctype(job_data), header)
        form = form_class(user=job.user, data=POST)

        if not form.is_valid():
            # TODO: unit test
            raise self.Error(
                gettext('Invalid data [{}]').format(form.errors.as_text())
            )

        form.process(job)

        Notification.objects.send(
            channel=UUID_CHANNEL_JOBS,
            users=[job.user],
            content=MassImportDoneContent(instance=doc),
        )

    def progress(self, job):
        count = MassImportJobResult.objects.filter(job=job).count()
        return JobProgress(
            percentage=None,
            label=ngettext(
                '{count} line has been processed.',
                '{count} lines have been processed.',
                count
            ).format(count=count)
        )

    @property
    def results_bricks(self):
        # from ..bricks import MassImportJobErrorsBrick
        return [MassImportJobErrorsBrick()]

    def get_description(self, job):
        try:
            job_data = job.data
            desc = [
                gettext('Import «{model}» from {doc}').format(
                    model=model_verbose_name(self._get_ctype(job_data).model_class()),
                    doc=self._get_document(self._build_POST(job_data)),
                ),
            ]
        except Exception:  # TODO: unit test
            logger.exception('Error in _MassImportType.get_description')
            desc = ['?']

        return desc

    def get_stats(self, job):
        stats = []

        result_qs = MassImportJobResult.objects.filter(job=job)
        lines_count = result_qs.count()

        entity_result_qs = result_qs.filter(entity__isnull=False)
        created_count = entity_result_qs.filter(updated=False).count()
        updated_count = entity_result_qs.filter(updated=True).count()

        model = self._get_ctype(job.data).model_class()

        if created_count:
            stats.append(
                ngettext(
                    '{count} «{model}» has been created.',
                    '{count} «{model}» have been created.',
                    created_count
                ).format(
                    count=created_count,
                    model=smart_model_verbose_name(model, created_count),
                )
            )
        elif updated_count != lines_count:
            stats.append(
                gettext('No «{model}» has been created.').format(
                    model=model_verbose_name(model),
                )
            )

        if updated_count:
            stats.append(
                ngettext(
                    '{count} «{model}» has been updated.',
                    '{count} «{model}» have been updated.',
                    updated_count
                ).format(
                    count=updated_count,
                    model=smart_model_verbose_name(model, updated_count),
                )
            )
        elif created_count != lines_count:
            stats.append(
                gettext('No «{model}» has been updated.').format(
                    model=model_verbose_name(model),
                )
            )

        stats.append(
            ngettext(
                '{count} line in the file.',
                '{count} lines in the file.',
                lines_count,
            ).format(count=lines_count)
        )

        return stats


mass_import_type = _MassImportType()
