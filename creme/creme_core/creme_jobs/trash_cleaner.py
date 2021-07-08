# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020-2021  Hybird
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
from django.db.models import F, ProtectedError
from django.db.transaction import atomic
from django.db.utils import NotSupportedError
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, ngettext

from creme.creme_core.auth.entity_credentials import EntityCredentials

from ..core.paginator import FlowPaginator
from ..models import CremeEntity, EntityJobResult, TrashCleaningCommand
from .base import JobProgress, JobType

logger = logging.getLogger(__name__)


class _TrashCleanerType(JobType):
    id = JobType.generate_id('creme_core', 'trash_cleaner')
    verbose_name = gettext_lazy('Trash cleaner')

    def _execute(self, job):
        # NB 1: we try to delete the remaining entities (which could not be deleted
        #       because of relationships) when there are errors, while the previous
        #       iteration managed to remove some entities.
        #       It will not work with cyclic references (but it is certainly very unusual).
        # NB 2: we do not use delete() method of queryset in order to send signals.
        user = job.user
        cmd_qs = TrashCleaningCommand.objects.filter(job=job)

        ctype_ids_qs = CremeEntity.objects.filter(is_deleted=True) \
                                          .values_list('entity_type', flat=True)

        try:
            # NB: currently only supported by PostGreSQL
            ctype_ids = [*ctype_ids_qs.order_by('entity_type_id').distinct('entity_type_id')]
        except NotSupportedError:
            ctype_ids = {*ctype_ids_qs}

        entity_classes = [
            ct.model_class()
            for ct in map(ContentType.objects.get_for_id, ctype_ids)
        ]

        while True:
            errors = False
            progress = False

            def create_error(entity, msg):
                nonlocal errors
                errors = True
                EntityJobResult.objects.update_or_create(
                    job=job,
                    entity=entity,
                    defaults={'messages': [msg]},
                )

            # NB: 'SELECT FOR UPDATE' in a query using an 'OUTER JOIN'
            #       and nullable ids will fail with postgresql (both 9.6 & 10.x).
            # TODO: This bug may be fixed in django > 2.2
            #  (see https://code.djangoproject.com/ticket/28010)

            # for entity_class in entity_classes:
            #     paginator = FlowPaginator(
            #         queryset=EntityCredentials.filter(
            #             user,
            #             entity_class.objects.filter(is_deleted=True),
            #             EntityCredentials.DELETE,
            #         ).order_by('id').select_for_update(),
            #         key='id',
            #         per_page=256,
            #     )
            #
            #     with atomic():
            #         for entities_page in paginator.pages():
            #             for entity in entities_page.object_list:
            #                 entity = entity.get_real_entity()
            for entity_class in entity_classes:
                paginator = FlowPaginator(
                    queryset=EntityCredentials.filter(
                        user,
                        entity_class.objects.filter(is_deleted=True),
                        EntityCredentials.DELETE,
                    ).order_by('id'),  # .select_for_update()
                    key='id',
                    per_page=256,
                )

                for entities_page in paginator.pages():
                    with atomic():
                        # NB (#60): Move 'SELECT FOR UPDATE' here for now (see above).
                        for entity in entity_class.objects.filter(
                            pk__in=entities_page.object_list
                        ).select_for_update():
                            try:
                                entity.delete()
                            except ProtectedError:
                                create_error(
                                    entity,
                                    _('Can not be deleted because of its dependencies.'),
                                )
                            except Exception as e:
                                logger.exception('Error when trying to empty the trash')
                                create_error(
                                    entity,
                                    _('Deletion caused an unexpected error [{}].').format(e),
                                )
                            else:
                                progress = True
                                cmd_qs.update(deleted_count=F('deleted_count') + 1)

            if not errors or not progress:
                break

    def progress(self, job):
        count = TrashCleaningCommand.objects.get(job=job).deleted_count

        return JobProgress(
            percentage=None,
            label=ngettext(
                '{count} entity deleted.',
                '{count} entities deleted.',
                count
            ).format(count=count),
        )

    # TODO: factorise
    def get_stats(self, job):
        count = TrashCleaningCommand.objects.get(job=job).deleted_count

        return [
            ngettext(
                '{count} entity deleted.',
                '{count} entities deleted.',
                count
            ).format(count=count),
        ] if count else []

    @property
    def results_bricks(self):
        from ..bricks import EntityJobErrorsBrick
        return [EntityJobErrorsBrick()]


trash_cleaner_type = _TrashCleanerType()
