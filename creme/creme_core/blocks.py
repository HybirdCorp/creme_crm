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

from collections import defaultdict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from .creme_jobs.base import JobType
from .gui.block import Block, SimpleBlock, QuerysetBlock, BlocksManager, list4url
from .gui.statistics import statistics_registry
from .models import (CremeEntity, Relation, CremeProperty, Job, JobResult,
        MassImportJobResult, EntityJobResult)
from .models.history import HistoryLine, TYPE_SYM_RELATION, TYPE_SYM_REL_DEL


class PropertiesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_core', 'properties')
    dependencies  = (CremeProperty,)
    verbose_name  = _(u'Properties')
    template_name = 'creme_core/templatetags/block_properties.html'

    def detailview_display(self, context):
        entity = context['object']
        return self._render(self.get_block_template_context(
                                context, entity.properties.select_related('type'),
                                update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                                ct_id=ContentType.objects.get_for_model(CremeProperty).id,
                           ))


class RelationsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_core', 'relations')
    dependencies  = (Relation,)  # NB: (Relation, CremeEntity) but useless
    relation_type_deps = ()  # Voluntarily void -> see detailview_display():
                             #  only types not present in another block are displayed.
    order_by      = 'type'
    verbose_name  = _(u'Relationships')
    template_name = 'creme_core/templatetags/block_relations.html'

    def detailview_display(self, context):
        entity = context['object']
        relations = entity.relations.select_related('type', 'type__symmetric_type', 'object_entity')
        excluded_types = BlocksManager.get(context).used_relationtypes_ids

        if excluded_types:
            update_url = '/creme_core/blocks/reload/relations_block/%s/%s/' % (entity.pk, ','.join(excluded_types))
            relations  = relations.exclude(type__in=excluded_types)
        else:
            update_url = '/creme_core/blocks/reload/relations_block/%s/' % entity.pk

        btc = self.get_block_template_context(context, relations, update_url=update_url)

        # NB: DB optimisation
        Relation.populate_real_object_entities(btc['page'].object_list)

        return self._render(btc)


class CustomFieldsBlock(SimpleBlock):
    id_           = SimpleBlock.generate_id('creme_core', 'customfields')
    # dependencies  = ()
    verbose_name  = _(u'Custom fields')
    template_name = 'creme_core/templatetags/block_customfields.html'


class HistoryBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_core', 'history')
    dependencies  = '*'
    read_only     = True
    order_by      = '-date'
    verbose_name  = _(u'History')
    template_name = 'creme_core/templatetags/block_history.html'

    # TODO: factorise (see assistants.block) ??
    @staticmethod
    def _populate_related_real_entities(hlines, user):
        hlines = [hline for hline in hlines if hline.entity_id]
        entities_ids_by_ct = defaultdict(set)
        get_ct = ContentType.objects.get_for_id

        for hline in hlines:
            ct_id = hline.entity_ctype_id
            hline.entity_ctype = get_ct(ct_id)
            entities_ids_by_ct[ct_id].add(hline.entity_id)

        entities_map = {}
        get_ct = ContentType.objects.get_for_id

        for ct_id, entities_ids in entities_ids_by_ct.iteritems():
            entities_map.update(get_ct(ct_id).model_class().objects.in_bulk(entities_ids))

        for hline in hlines:
            # Should not happen (means that entity does not exist anymore) but...
            hline.entity = entities_map.get(hline.entity_id)

    @staticmethod
    def _populate_users(hlines, user):
        # We retrieve the User instances corresponding to the line usernames, in order to have a verbose display.
        # We avoid a useless query to User if the only used User is the current User (which is already retrieved).
        usernames = {hline.username for hline in hlines}
        usernames.discard(user.username)

        users = {user.username: user}

        if usernames:
            users.update((u.username, u) for u in get_user_model().objects.filter(username__in=usernames))

        for hline in hlines:
            hline.user = users.get(hline.username)

    @staticmethod
    def _populate_perms(hlines, user):
        for hline in hlines:
            # NB: we cannot knwo the owner of the entity if it has been deleted.
            #     So its representation (line.entity_repr) & its modifications
            #     will be viewable even if the entity was not viewable before its deletion...
            entity = hline.entity
            hline.can_be_viewed = user.has_perm_to_view(entity) if entity is not None else True

    def detailview_display(self, context):
        pk = context['object'].pk
        btc = self.get_block_template_context(
                    context,
                    HistoryLine.objects.filter(entity=pk),
                    update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, pk),
                   )
        hlines = btc['page'].object_list

        self._populate_users(hlines, context['request'].user)

        for hline in hlines:
            # All lines are referencing context['object'], which can be viewed.
            hline.can_be_viewed = True

        return self._render(btc)

    def portal_display(self, context, ct_ids):
        btc = self.get_block_template_context(
                    context,
                    HistoryLine.objects.filter(entity_ctype__in=ct_ids),
                    update_url='/creme_core/blocks/reload/portal/%s/%s/' % (self.id_, list4url(ct_ids)),
                    HIDDEN_VALUE=settings.HIDDEN_VALUE,
                   )
        hlines = btc['page'].object_list
        user = context['request'].user

        self._populate_related_real_entities(hlines, user)
        self._populate_users(hlines, user)
        self._populate_perms(hlines, user)

        return self._render(btc)

    def home_display(self, context):
        btc = self.get_block_template_context(
                    context,
                    HistoryLine.objects.exclude(type__in=(TYPE_SYM_RELATION, TYPE_SYM_REL_DEL)),
                    update_url='/creme_core/blocks/reload/home/%s/' % self.id_,
                    HIDDEN_VALUE=settings.HIDDEN_VALUE,
                   )
        hlines = btc['page'].object_list
        user = context['request'].user

        self._populate_related_real_entities(hlines, user)
        self._populate_users(hlines, user)
        self._populate_perms(hlines, user)

        return self._render(btc)


class TrashBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_core', 'trash')
    dependencies  = (CremeEntity,)
    order_by      = '-modified'
    verbose_name  = _(u'Trash')
    template_name = 'creme_core/templatetags/block_trash.html'
    page_size     = 50
    permission    = None  # NB: the template uses credentials
    configurable  = False  # TODO: allows on home page ?

    def detailview_display(self, context):
        btc = self.get_block_template_context(context,
                                              CremeEntity.objects.filter(is_deleted=True),
                                              update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                             )
        CremeEntity.populate_real_entities(btc['page'].object_list)

        return self._render(btc)


class StatisticsBlock(Block):
    id_           = Block.generate_id('creme_core', 'statistics')
    verbose_name  = _(u'Statistics')
    template_name = 'creme_core/templatetags/block_statistics.html'
    target_apps   = ('creme_core',)

    def home_display(self, context):
        has_perm = context['user'].has_perm

        return self._render(self.get_block_template_context(
                                context,
                                items=[item
                                        for item in statistics_registry
                                            if not item.perm or has_perm(item.perm)
                                      ],
                                update_url='/creme_core/blocks/reload/home/%s/' % self.id_,
                               )
                           )


class JobBlock(Block):
    id_           = Block.generate_id('creme_core', 'job')
    dependencies  = (Job,)
    verbose_name  = 'Job'
    template_name = 'creme_core/templatetags/block_job.html'
    configurable  = False

    def detailview_display(self, context):
        job = context['job']

        return self._render(self.get_block_template_context(
                    context, job=job,
                    update_url='/creme_core/job/%s/reload/%s' % (job.id, self.id_),
                    JOB_OK=Job.STATUS_OK,
                    JOB_ERROR=Job.STATUS_ERROR,
                    JOB_WAIT=Job.STATUS_WAIT,
                    # PERIODIC=JobType.PERIODIC,
                    NOT_PERIODIC=JobType.NOT_PERIODIC,
                ))


class JobResultsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_core', 'job_results')
    dependencies  = (JobResult,)
    order_by      = 'id'
    verbose_name  = 'Job results'
    template_name = 'creme_core/templatetags/block_job_results.html'
    configurable  = False
    page_size     = 50

    def _build_queryset(self, job):
        return self.dependencies[0].objects.filter(job=job)

    def _extra_context(self, job):
        return {}

    def detailview_display(self, context):
        job = context['job']

        return self._render(self.get_block_template_context(
                    context, self._build_queryset(job),
                    # self.dependencies[0].objects.filter(job=job, raw_messages__isnull=False),
                    update_url='/creme_core/job/%s/reload/%s' % (job.id, self.id_),
                    **self._extra_context(job)
                ))


class JobErrorsBlock(JobResultsBlock):
    id_           = QuerysetBlock.generate_id('creme_core', 'job_errors')
    verbose_name  = 'Job errors'
    template_name = 'creme_core/templatetags/block_job_errors.html'

    def _build_queryset(self, job):
        return super(JobErrorsBlock, self)._build_queryset(job).filter(raw_messages__isnull=False)

    def _extra_context(self, job):
        return {'JOB_ERROR': Job.STATUS_ERROR}


class EntityJobErrorsBlock(JobErrorsBlock):
    id_           = QuerysetBlock.generate_id('creme_core', 'entity_job_errors')
    dependencies  = (EntityJobResult,)
    verbose_name  = 'Entity job errors'
    template_name = 'creme_core/templatetags/block_entity_job_errors.html'


class MassImportJobErrorsBlock(JobErrorsBlock):
    id_           = QuerysetBlock.generate_id('creme_core', 'mass_import_job_errors')
    dependencies  = (MassImportJobResult,)
    verbose_name  = 'Mass import job errors'
    template_name = 'creme_core/templatetags/block_massimport_job_errors.html'


class JobsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_core', 'jobs')
    dependencies  = (Job,)
    # order_by      = '-created'
    verbose_name  = 'Jobs'
    template_name = 'creme_core/templatetags/block_jobs.html'
    configurable  = False
    page_size     = 50
    permission    = None

    def detailview_display(self, context):
        user = context['user']
        jobs = Job.objects.all()

        if not user.is_superuser:
            jobs = jobs.filter(user=user)

        return self._render(self.get_block_template_context(
                    context, jobs,
                    update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    # TODO: computed twice when user is not superuser...
                    user_jobs_count=Job.objects.filter(user=user).count(),
                    MAX_JOBS_PER_USER=settings.MAX_JOBS_PER_USER,
                    JOB_WAIT=Job.STATUS_WAIT,
                    # PERIODIC=JobType.PERIODIC,
                    NOT_PERIODIC=JobType.NOT_PERIODIC,
                ))


properties_block   = PropertiesBlock()
relations_block    = RelationsBlock()
customfields_block = CustomFieldsBlock()
history_block      = HistoryBlock()
trash_block        = TrashBlock()
statistics_block   = StatisticsBlock()
job_block          = JobBlock()

# Not registered (never get by the registry, used in specific views only)
job_results_block           = JobResultsBlock()
job_errors_block            = JobErrorsBlock()
entity_job_errors_block     = EntityJobErrorsBlock()
massimport_job_errors_block = MassImportJobErrorsBlock()

block_list = (
        properties_block,
        relations_block,
        customfields_block,
        history_block,
        trash_block,
        statistics_block,
        job_block,
        JobsBlock(),
    )
