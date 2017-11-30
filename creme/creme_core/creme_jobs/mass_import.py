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

import logging

from django.contrib.contenttypes.models import ContentType
from django.http import QueryDict
from django.utils.translation import ugettext_lazy as _, ugettext, ungettext

from ..forms.mass_import import get_header, form_factory
from ..models import MassImportJobResult
from .base import JobType, JobProgress
from ..utils.translation import get_model_verbose_name

from creme.documents import get_document_model


logger = logging.getLogger(__name__)


class _MassImportType(JobType):
    id           = JobType.generate_id('creme_core', 'mass_import')
    verbose_name = _(u'Mass import')

    def _build_POST(self, job_data):
        return QueryDict(job_data['POST'])

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
            raise self.Error(ugettext('Invalid data [%s]' % form.errors.as_text()))  # TODO: unit test

        form.process(job)

    def progress(self, job):
        count = MassImportJobResult.objects.filter(job=job).count()
        return JobProgress(percentage=None,
                           label=ungettext(u'{count} line has been processed.',
                                           u'{count} lines have been processed.',
                                           count
                                          ).format(count=count)
                          )

    @property
    def results_bricks(self):
        from ..bricks import MassImportJobErrorsBrick
        return [MassImportJobErrorsBrick()]

    def get_description(self, job):
        try:
            job_data = job.data
            desc = [ugettext(u'Import «{type}» from {doc}').format(
                        type=self._get_ctype(job_data).model_class()._meta.verbose_name,
                        doc=self._get_document(self._build_POST(job_data)),
                    )
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
            stats.append(ungettext(u'{counter} «{type}» has been created.',
                                   u'{counter} «{type}» have been created.',
                                   created_count
                                  ).format(counter=created_count,
                                           type=get_model_verbose_name(model, created_count),
                                          )
                        )
        elif updated_count != lines_count:
            stats.append(ugettext(u'No «{type}» has been created.').format(type=model._meta.verbose_name))

        if updated_count:
            stats.append(ungettext(u'{counter} «{type}» has been updated.',
                                   u'{counter} «{type}» have been updated.',
                                   updated_count
                                  ).format(counter=updated_count,
                                           type=get_model_verbose_name(model, updated_count),
                                          )
                        )
        elif created_count != lines_count:
            stats.append(ugettext(u'No «{type}» has been updated.').format(type=model._meta.verbose_name))

        stats.append(ungettext(u'{count} line in the file.',
                               u'{count} lines in the file.',
                               lines_count,
                              ).format(count=lines_count)
                    )

        return stats


mass_import_type = _MassImportType()
