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
from functools import partial

# TODO: move in function to do lazy loading ?
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db.transaction import atomic
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from ..core.batch_process import BatchAction
from ..core.paginator import FlowPaginator
from ..core.workflow import WorkflowEngine
from ..gui.job import EntityJobErrorsBrick
from ..models import EntityCredentials, EntityFilter, EntityJobResult
from ..models.utils import model_verbose_name
from .base import JobProgress, JobType

logger = logging.getLogger(__name__)


class _BatchProcessType(JobType):
    id = JobType.generate_id('creme_core', 'batch_process')
    verbose_name = _('Batch process')

    def _get_actions(self, model, job_data):
        for kwargs in job_data['actions']:
            yield BatchAction(model, **kwargs)

    def _get_efilter(self, job_data, raise_exception=True):
        efilter = None
        efilter_id = job_data.get('efilter')

        if efilter_id:
            try:
                efilter = EntityFilter.objects.get(id=efilter_id)
            except EntityFilter.DoesNotExist as e:
                if raise_exception:
                    raise self.Error(gettext('The filter does not exist anymore')) from e

        return efilter

    def _get_model(self, job_data):
        return ContentType.objects.get_for_id(job_data['ctype']).model_class()

    def _humanize_validation_error(self, entity, ve):
        get_field = entity._meta.get_field

        try:
            # TODO: NON_FIELD_ERRORS need to be unit tested...
            humanized = [
                str(errors)
                if field == NON_FIELD_ERRORS else
                '{} => {}'.format(get_field(field).verbose_name, ', '.join(errors))
                for field, errors in ve.message_dict.items()
            ]
        except Exception as e:
            logger.debug('BatchProcess._humanize_validation_error: %s', e)
            humanized = [str(ve)]

        return humanized

    def _execute(self, job):
        job_data = job.data
        model = self._get_model(job_data)
        entities = model.objects.filter(is_deleted=False)

        efilter = self._get_efilter(job_data)
        if efilter is not None:
            entities = efilter.filter(entities)

        already_processed = frozenset(
            EntityJobResult.objects
                           .filter(job=job)
                           .values_list('entity_id', flat=True)
        )
        if already_processed:
            logger.info('BatchProcess: resuming job %s', job.id)

        entities = EntityCredentials.filter(job.user, entities, EntityCredentials.CHANGE)
        paginator = FlowPaginator(
            queryset=entities.order_by('id'), key='id', per_page=1024,
        )
        actions = [*self._get_actions(model, job_data)]
        create_result = partial(EntityJobResult.objects.create, job=job)
        wf_engine = WorkflowEngine.get_current()

        for entities_page in paginator.pages():
            for entity in entities_page.object_list:
                if entity.id in already_processed:
                    continue

                changed = False

                with atomic(), wf_engine.run(user=None):
                    try:
                        final_entity = model.objects.select_for_update().get(id=entity.id)
                    except model.DoesNotExist:
                        continue

                    for action in actions:
                        if action(final_entity):
                            changed = True

                    if changed:
                        try:
                            final_entity.full_clean()
                        except ValidationError as e:
                            create_result(
                                real_entity=final_entity,
                                messages=self._humanize_validation_error(final_entity, e)
                            )
                        else:
                            final_entity.save()
                            create_result(real_entity=final_entity)

    def progress(self, job):
        count = EntityJobResult.objects.filter(job=job).count()
        return JobProgress(
            percentage=None,
            label=ngettext(
                '{count} entity has been processed.',
                '{count} entities have been processed.',
                count
            ).format(count=count),
        )

    @property
    def results_bricks(self):
        return [EntityJobErrorsBrick()]

    def get_description(self, job):
        try:
            job_data = job.data
            model = self._get_model(job_data)
            desc = [gettext('Entity type: {}').format(model_verbose_name(model))]

            efilter = self._get_efilter(job_data, raise_exception=False)
            if efilter is not None:
                desc.append(gettext('Filter: {}').format(efilter))

            desc.extend(str(ba) for ba in self._get_actions(model, job_data))
        except Exception:  # TODO: unit test
            logger.exception('Error in _BatchProcessType.get_description')
            desc = ['?']

        return desc

    def get_stats(self, job):
        count = EntityJobResult.objects.filter(job=job, messages__isnull=True).count()

        return [
            ngettext(
                '{count} entity has been successfully modified.',
                '{count} entities have been successfully modified.',
                count
            ).format(count=count),
        ]


batch_process_type = _BatchProcessType()
