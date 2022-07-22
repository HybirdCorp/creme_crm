# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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
from collections import defaultdict

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from .core.entity_cell import EntityCellCustomField
from .creme_jobs.base import JobType
from .gui import statistics
from .gui.bricks import Brick, BricksManager, QuerysetBrick
from .gui.history import html_history_registry
from .models import (
    CremeEntity,
    CremeProperty,
    CustomField,
    EntityJobResult,
    Imprint,
    Job,
    JobResult,
    MassImportJobResult,
    Relation,
    RelationType,
)
from .models.history import TYPE_SYM_REL_DEL, TYPE_SYM_RELATION, HistoryLine
from .utils.db import populate_related

logger = logging.getLogger(__name__)


class PropertiesBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('creme_core', 'properties')
    dependencies = (CremeProperty,)
    verbose_name = _('Properties')
    description = _(
        'Displays the Properties attached to the current entity. '
        'Properties are kind of markers, useful to filter entities.\n'
        'App: Core'
    )
    template_name = 'creme_core/bricks/properties.html'
    order_by = 'type__text'  # TODO: in model ??

    def detailview_display(self, context):
        entity = context['object']
        return self._render(self.get_template_context(
            context, entity.properties.select_related('type'),
        ))


class RelationsBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('creme_core', 'relations')
    verbose_name = _('Relationships')
    description = _(
        'Displays the entities which are linked to the current entity with a Relationship. '
        'A Relationship is: \n'
        '- typed (examples of types: «is a customer of», «has been sent by»)\n'
        '- has a symmetric relationship'
        ' (eg: «is a customer of» & «is a supplier of» are symmetric)\n'
        'App: Core'
    )

    # NB: indeed (Relation, CremeEntity) but useless because
    # _iter_dependencies_info() has been overridden.
    dependencies = (Relation,)

    relation_type_deps = ()  # Voluntarily void -> see detailview_display()
    order_by = 'type__predicate'
    template_name = 'creme_core/bricks/relations.html'

    def __init__(self):
        super().__init__()
        self._included_rtype_ids = []
        self._excluded_rtype_ids = []

    @QuerysetBrick.reloading_info.setter
    def reloading_info(self, info):
        info_are_ok = False

        if isinstance(info, dict):
            def is_a_list_of_strings(key):
                rtype_ids = info.get(key, ())
                return isinstance(rtype_ids, (list, tuple)) and all(
                    isinstance(x, str) for x in rtype_ids
                )

            info_are_ok = is_a_list_of_strings('include') and is_a_list_of_strings('exclude')

        if info_are_ok:
            self._reloading_info = info
        else:
            # We do not let leave 'None' (because it means 'first render').
            self._reloading_info = {}
            logger.warning('Invalid reloading extra_data for RelationsBrick: %s', info)

    def _iter_dependencies_info(self):
        # In order a JS dependencies intelligence want to get the real dependence.
        yield 'creme_core.relation'

        for rtype_id in self._included_rtype_ids:
            yield 'creme_core.relation.' + rtype_id

    def detailview_display(self, context):
        entity = context['object']
        relations = entity.relations.select_related(
            'type', 'type__symmetric_type', 'object_entity',
        )
        included_rtype_ids = self._included_rtype_ids
        excluded_rtype_ids = self._excluded_rtype_ids
        reloading_info = self._reloading_info

        if reloading_info is None:  # NB: it's not a reload, it's the initial render()
            # TODO: when it's the only use of 'used_relationtypes_ids()',
            #       inline the call (+ deprecate method) ?
            used_rtype_ids = BricksManager.get(context).used_relationtypes_ids
            excluded_rtype_ids_set = {
                *RelationType.objects.filter(
                    id__in=used_rtype_ids,
                    minimal_display=True,
                ).values_list('id', flat=True),
            }
            included_rtype_ids.extend(
                rtype_id
                for rtype_id in used_rtype_ids
                if rtype_id not in excluded_rtype_ids_set
            )
            excluded_rtype_ids.extend(excluded_rtype_ids_set)

            self._reloading_info = reloading_info = {}
            if included_rtype_ids:
                reloading_info['include'] = included_rtype_ids
            if excluded_rtype_ids:
                reloading_info['exclude'] = excluded_rtype_ids
        else:
            get = reloading_info.get
            included_rtype_ids.extend(get('include', ()))
            excluded_rtype_ids.extend(get('exclude', ()))

        if excluded_rtype_ids:
            relations = relations.exclude(type__in=excluded_rtype_ids)

        btc = self.get_template_context(
            context, relations,
            excluded_rtype_ids=excluded_rtype_ids,
        )

        # NB: DB optimisation
        Relation.populate_real_object_entities(btc['page'].object_list)

        return self._render(btc)


class CustomFieldsBrick(Brick):
    id_ = Brick.generate_id('creme_core', 'customfields')
    verbose_name = _('Custom fields')
    description = _(
        'Displays the values of the Custom Fields for the current entity. '
        'Custom Fields can be created in the general configuration.\n'
        'App: Core'
    )
    dependencies = (CustomField,)
    template_name = 'creme_core/bricks/custom-fields.html'

    def detailview_display(self, context):
        entity = context['object']

        # TODO: factorise with CremeEntity.get_custom_fields_n_values() ?
        # cfields = CustomField.objects.get_for_model(entity.entity_type).values()
        cfields = [
            cfield
            for cfield in CustomField.objects.get_for_model(entity.entity_type).values()
            if not cfield.is_deleted
        ]
        CremeEntity.populate_custom_values([entity], cfields)

        return self._render(self.get_template_context(
            context,
            cells=[EntityCellCustomField(cfield) for cfield in cfields],
        ))


class HistoryBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('creme_core', 'history')
    verbose_name = _('History')
    description = _(
        'Displays the history of modifications on the current entity. '
        'Each line of history contains a date, the user which made the '
        'modifications & the type of modification (creation, edition of fields, '
        'deletion, relationship adding…).\n'
        'App: Core'
    )
    dependencies = '*'
    read_only = True
    order_by = '-id'  # faster than '-date'
    template_name = 'creme_core/bricks/history.html'

    history_registry = html_history_registry

    # TODO: factorise (see assistants.bricks) ??
    @staticmethod
    # def _populate_related_real_entities(hlines, user):
    def _populate_related_real_entities(hlines):
        hlines = [hline for hline in hlines if hline.entity_id]
        entities_ids_by_ct = defaultdict(set)
        get_ct = ContentType.objects.get_for_id

        for hline in hlines:
            ct_id = hline.entity_ctype_id
            hline.entity_ctype = get_ct(ct_id)
            entities_ids_by_ct[ct_id].add(hline.entity_id)

        entities_map = {}

        for ct_id, entities_ids in entities_ids_by_ct.items():
            entities_map.update(get_ct(ct_id).model_class().objects.in_bulk(entities_ids))

        for hline in hlines:
            # Should not happen (means that entity does not exist anymore) but...
            hline.entity = entities_map.get(hline.entity_id)

    def _populate_explainers(self, hlines, user):
        for hline, explainer in zip(hlines, self.history_registry.line_explainers(hlines, user)):
            hline.explainer = explainer

    @staticmethod
    def _populate_perms(hlines, user):
        for hline in hlines:
            # NB: we cannot know the owner of the entity if it has been deleted.
            #     So its representation (line.entity_repr) & its modifications
            #     will be viewable even if the entity was not viewable before its deletion...
            entity = hline.entity
            hline.can_be_viewed = user.has_perm_to_view(entity) if entity is not None else True

    def detailview_display(self, context):
        pk = context['object'].pk
        btc = self.get_template_context(context, HistoryLine.objects.filter(entity=pk))
        hlines = btc['page'].object_list
        user = context['user']

        HistoryLine.populate_related_lines(hlines)
        related_hlines = [*filter(None, (hline.related_line for hline in hlines))]
        self._populate_related_real_entities(related_hlines)

        HistoryLine.populate_users(hlines, user)
        self._populate_explainers([*hlines, *related_hlines], user)

        for hline in hlines:
            # All lines are referencing context['object'], which can be viewed.
            hline.can_be_viewed = True

        return self._render(btc)

    def home_display(self, context):
        btc = self.get_template_context(
            context,
            HistoryLine.objects.exclude(type__in=(TYPE_SYM_RELATION, TYPE_SYM_REL_DEL)),
            HIDDEN_VALUE=settings.HIDDEN_VALUE,
        )
        hlines = btc['page'].object_list
        user = context['user']

        HistoryLine.populate_related_lines(hlines)
        related_hlines = [*filter(None, (hline.related_line for hline in hlines))]
        extended_hlines = [*hlines, *related_hlines]

        self._populate_related_real_entities(extended_hlines)
        HistoryLine.populate_users(hlines, user)
        self._populate_perms(hlines, user)
        self._populate_explainers(extended_hlines, user)

        return self._render(btc)


class ImprintsBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('creme_core', 'imprints')
    verbose_name = _('History of consultation')
    description = _(
        'Displays who has consulted the current entity, and the date of the consultations.\n'
        'Hint: only super-users can view this data.\n'
        'App: Core'
    )
    dependencies = (Imprint,)
    read_only = True
    order_by = '-id'  # faster than '-date'
    template_name = 'creme_core/bricks/imprints.html'

    def detailview_display(self, context):
        can_view = context['user'].is_superuser
        qs = Imprint.objects.filter(
            entity=context['object'].pk,
        ) if can_view else Imprint.objects.none()

        return self._render(self.get_template_context(context, qs))

    def home_display(self, context):
        can_view = context['user'].is_superuser
        # qs = Imprint.objects.all() if can_view else Imprint.objects.none()
        qs = Imprint.objects.select_related('entity') if can_view else Imprint.objects.none()
        btc = self.get_template_context(context, qs)

        # NB: optimisations
        if can_view:
            # CremeEntity.populate_real_entities(
            #     CremeEntity.objects.filter(
            #         id__in=[imprint.entity_id for imprint in btc['page'].object_list],
            #     )
            # )
            imprints = btc['page'].object_list
            CremeEntity.populate_real_entities(
                [imprint.entity for imprint in imprints]
            )
            # NB: there will still be queries for each different Contacts
            #     corresponding to users...
            populate_related(instances=imprints, field_names=['user'])

        return self._render(btc)


class TrashBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('creme_core', 'trash')
    verbose_name = _('Trash')
    dependencies = (CremeEntity,)
    order_by = '-modified'
    template_name = 'creme_core/bricks/trash.html'
    page_size = 50
    # permission = None  # NB: the template uses credentials
    configurable = False  # TODO: allows on home page ?

    def detailview_display(self, context):
        btc = self.get_template_context(
            context,
            CremeEntity.objects.filter(is_deleted=True),
        )
        CremeEntity.populate_real_entities(btc['page'].object_list)

        return self._render(btc)


class StatisticsBrick(Brick):
    id_ = Brick.generate_id('creme_core', 'statistics')
    verbose_name = _('Statistics')
    description = _(
        'Displays many statistics (eg: the numbers of customers), depending '
        'on installed apps.\n'
        'App: Core'
    )
    template_name = 'creme_core/bricks/statistics.html'

    statistics_registry = statistics.statistics_registry

    def home_display(self, context):
        has_perm = context['user'].has_perm

        return self._render(self.get_template_context(
            context,
            items=[
                item
                for item in self.statistics_registry
                if not item.perm or has_perm(item.perm)
            ],
        ))


class JobBrick(Brick):
    id_ = Brick.generate_id('creme_core', 'job')
    dependencies = (Job,)
    verbose_name = _('Job')
    template_name = 'creme_core/bricks/job.html'
    configurable = False

    @Brick.reloading_info.setter
    def reloading_info(self, info):
        info_are_ok = False

        if isinstance(info, dict):
            info_are_ok = isinstance(info.get('list_url', ''), str)

        if info_are_ok:
            self._reloading_info = info
        else:
            # We do not let leave 'None' (because it means 'first render').
            self._reloading_info = {}
            logger.warning('Invalid reloading extra_data for JobBrick: %s', info)

    def detailview_display(self, context):
        job = context['job']

        reloading_info = self._reloading_info

        if reloading_info is None:  # NB: it's not a reload, it's the initial render()
            list_url = context.get('list_url')
            self._reloading_info = {'list_url': list_url}
        else:
            list_url = reloading_info.get('list_url')

        return self._render(self.get_template_context(
            context, job=job,
            JOB_OK=Job.STATUS_OK,
            JOB_ERROR=Job.STATUS_ERROR,
            JOB_WAIT=Job.STATUS_WAIT,
            # PERIODIC=JobType.PERIODIC,
            NOT_PERIODIC=JobType.NOT_PERIODIC,
            list_url=list_url,
        ))


class JobResultsBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('creme_core', 'job_results')
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
    id_ = QuerysetBrick.generate_id('creme_core', 'job_errors')
    verbose_name = _('Errors')
    template_name = 'creme_core/bricks/job-errors.html'

    def _build_queryset(self, job):
        # return super()._build_queryset(job).filter(raw_messages__isnull=False)
        return super()._build_queryset(job).filter(messages__isnull=False)

    def _extra_context(self, job):
        return {'JOB_ERROR': Job.STATUS_ERROR}


class EntityJobErrorsBrick(JobErrorsBrick):
    id_ = QuerysetBrick.generate_id('creme_core', 'entity_job_errors')
    # verbose_name = 'Entity job errors'
    dependencies = (EntityJobResult,)
    template_name = 'creme_core/bricks/entity-job-errors.html'


class MassImportJobErrorsBrick(JobErrorsBrick):
    id_ = QuerysetBrick.generate_id('creme_core', 'mass_import_job_errors')
    # verbose_name  = 'Mass import job errors'
    dependencies = (MassImportJobResult,)
    template_name = 'creme_core/bricks/massimport-errors.html'


class JobsBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('creme_core', 'jobs')
    verbose_name = _('Jobs')
    dependencies = (Job,)
    # order_by = '-created'
    template_name = 'creme_core/bricks/jobs-all.html'
    configurable = False
    page_size = 50
    # permission = None

    def _jobs_qs(self, context):
        return Job.objects.all()

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context, self._jobs_qs(context),
            # not_finished_user_jobs_count=Job.not_finished_jobs(context['user']).count(),
            not_finished_user_jobs_count=Job.objects.not_finished(context['user']).count(),
            MAX_JOBS_PER_USER=settings.MAX_JOBS_PER_USER,
            NOT_PERIODIC=JobType.NOT_PERIODIC,
            PSEUDO_PERIODIC=JobType.PSEUDO_PERIODIC,
        ))


class MyJobsBrick(JobsBrick):
    id_ = QuerysetBrick.generate_id('creme_core', 'my_jobs')
    verbose_name = _('My jobs')
    template_name = 'creme_core/bricks/jobs-mine.html'

    def _jobs_qs(self, context):
        return Job.objects.filter(user=context['user'])
