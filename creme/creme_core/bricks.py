# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from .core.entity_cell import EntityCellCustomField
from .creme_jobs.base import JobType
from .gui.bricks import Brick, QuerysetBrick, BricksManager, list4url
from .gui.statistics import statistics_registry
from .models import (CremeEntity, RelationType, Relation, CremeProperty, CustomField,
        Job, JobResult, MassImportJobResult, EntityJobResult)
from .models.history import HistoryLine, TYPE_SYM_RELATION, TYPE_SYM_REL_DEL


logger = logging.getLogger(__name__)


class PropertiesBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('creme_core', 'properties')
    dependencies  = (CremeProperty,)
    verbose_name  = _(u'Properties')
    # template_name = 'creme_core/templatetags/block_properties.html'
    template_name = 'creme_core/bricks/properties.html'

    def detailview_display(self, context):
        entity = context['object']
        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context, entity.properties.select_related('type'),
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, entity.pk)),
                    ct_id=ContentType.objects.get_for_model(CremeProperty).id,  # DEPRECATED (use 'objects_ctype.id' instead)
        ))


class RelationsBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('creme_core', 'relations')
    dependencies  = (Relation,)  # NB: (Relation, CremeEntity) but useless.
                                 # Useless because _iter_dependencies_info() has been overriden.
    relation_type_deps = ()  # Voluntarily void -> see detailview_display()
    order_by      = 'type'
    verbose_name  = _(u'Relationships')
    # template_name = 'creme_core/templatetags/block_relations.html'
    template_name = 'creme_core/bricks/relations.html'

    def __init__(self):
        super(RelationsBrick, self).__init__()
        self._included_rtype_ids = []
        self._excluded_rtype_ids = []

    @QuerysetBrick.reloading_info.setter
    def reloading_info(self, info):
        info_are_ok = False

        if isinstance(info, dict):
            def is_a_list_of_strings(key):
                rtype_ids = info.get(key, ())
                return isinstance(rtype_ids, (list, tuple)) and all(isinstance(x, basestring) for x in rtype_ids)

            info_are_ok = is_a_list_of_strings('include') and is_a_list_of_strings('exclude')

        if info_are_ok:
            self._reloading_info = info
        else:
            self._reloading_info = {}  # We do not let leave 'None' (because it means 'first render').
            logger.warn('Invalid reloading extra_data for RelationsBlock: %s', info)

    def _iter_dependencies_info(self):
        # In order a JS dependencies intelligence want to get the real dependence.
        yield 'creme_core.relation'

        for rtype_id in self._included_rtype_ids:
            yield 'creme_core.relation.' + rtype_id

    def detailview_display(self, context):
        entity = context['object']
        relations = entity.relations.select_related('type', 'type__symmetric_type', 'object_entity')
        included_rtype_ids = self._included_rtype_ids
        excluded_rtype_ids = self._excluded_rtype_ids
        reloading_info = self._reloading_info

        if reloading_info is None:  # NB: it's not a reload, it's the initial render()
            # TODO: when it's the only use of 'used_relationtypes_ids()', inline the call (+ deprecate method) ?
            used_rtype_ids = BricksManager.get(context).used_relationtypes_ids
            excluded_rtype_ids_set = set(RelationType.objects.filter(id__in=used_rtype_ids,
                                                                     minimal_display=True,
                                                                    )
                                                             .values_list('id', flat=True)
                                        )
            included_rtype_ids.extend(rtype_id for rtype_id in used_rtype_ids if rtype_id not in excluded_rtype_ids_set)
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
            # update_url = '/creme_core/blocks/reload/relations_block/%s/%s/' % (entity.pk, ','.join(excluded_types))
            update_url = reverse('creme_core__reload_relations_block', args=(entity.id, ','.join(excluded_rtype_ids)))
            relations  = relations.exclude(type__in=excluded_rtype_ids)
        else:
            # update_url = '/creme_core/blocks/reload/relations_block/%s/' % entity.pk
            update_url = reverse('creme_core__reload_relations_block', args=(entity.id,))

        # btc = self.get_block_template_context(context, relations,
        btc = self.get_template_context(context, relations,
                                        update_url=update_url,
                                        excluded_rtype_ids=excluded_rtype_ids,
                                       )

        # NB: DB optimisation
        Relation.populate_real_object_entities(btc['page'].object_list)

        return self._render(btc)


class CustomFieldsBrick(Brick):
    id_           = Brick.generate_id('creme_core', 'customfields')
    dependencies  = (CustomField,)
    verbose_name  = _(u'Custom fields')
    template_name = 'creme_core/bricks/custom-fields.html'

    def detailview_display(self, context):
        entity = context['object']

        # TODO: factorise with CremeEntity.get_custom_fields_n_values() ?
        cfields = CustomField.objects.filter(content_type=entity.entity_type)
        CremeEntity.populate_custom_values([entity], cfields)

        return self._render(self.get_template_context(
                    context,
                    cells=[EntityCellCustomField(cfield) for cfield in cfields],
        ))


class HistoryBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('creme_core', 'history')
    dependencies  = '*'
    read_only     = True
    order_by      = '-date'
    verbose_name  = _(u'History')
    # template_name = 'creme_core/templatetags/block_history.html'
    template_name = 'creme_core/bricks/history.html'

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

        for ct_id, entities_ids in entities_ids_by_ct.iteritems():
            entities_map.update(get_ct(ct_id).model_class().objects.in_bulk(entities_ids))

        for hline in hlines:
            # Should not happen (means that entity does not exist anymore) but...
            hline.entity = entities_map.get(hline.entity_id)

    # TODO: move to HistoryLine (used in templatetags/creme_history.py too)
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
            # NB: we cannot know the owner of the entity if it has been deleted.
            #     So its representation (line.entity_repr) & its modifications
            #     will be viewable even if the entity was not viewable before its deletion...
            entity = hline.entity
            hline.can_be_viewed = user.has_perm_to_view(entity) if entity is not None else True

    def detailview_display(self, context):
        pk = context['object'].pk
        # btc = self.get_block_template_context(
        btc = self.get_template_context(
                    context,
                    HistoryLine.objects.filter(entity=pk),
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, pk),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, pk)),
                   )
        hlines = btc['page'].object_list

        self._populate_users(hlines, context['user'])

        for hline in hlines:
            # All lines are referencing context['object'], which can be viewed.
            hline.can_be_viewed = True

        return self._render(btc)

    def portal_display(self, context, ct_ids):
        # btc = self.get_block_template_context(
        btc = self.get_template_context(
                    context,
                    HistoryLine.objects.filter(entity_ctype__in=ct_ids),
                    # update_url='/creme_core/blocks/reload/portal/%s/%s/' % (self.id_, list4url(ct_ids)),
                    update_url=reverse('creme_core__reload_portal_blocks', args=(self.id_, list4url(ct_ids))),
                    HIDDEN_VALUE=settings.HIDDEN_VALUE,
                   )
        hlines = btc['page'].object_list
        user = context['user']

        self._populate_related_real_entities(hlines, user)
        self._populate_users(hlines, user)
        self._populate_perms(hlines, user)

        return self._render(btc)

    def home_display(self, context):
        # btc = self.get_block_template_context(
        btc = self.get_template_context(
                    context,
                    HistoryLine.objects.exclude(type__in=(TYPE_SYM_RELATION, TYPE_SYM_REL_DEL)),
                    # update_url='/creme_core/blocks/reload/home/%s/' % self.id_,
                    update_url=reverse('creme_core__reload_home_blocks', args=(self.id_,)),
                    HIDDEN_VALUE=settings.HIDDEN_VALUE,
                   )
        hlines = btc['page'].object_list
        user = context['user']

        self._populate_related_real_entities(hlines, user)
        self._populate_users(hlines, user)
        self._populate_perms(hlines, user)

        return self._render(btc)


class TrashBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('creme_core', 'trash')
    dependencies  = (CremeEntity,)
    order_by      = '-modified'
    verbose_name  = _(u'Trash')
    # template_name = 'creme_core/templatetags/block_trash.html'
    template_name = 'creme_core/bricks/trash.html'
    page_size     = 50
    permission    = None  # NB: the template uses credentials
    configurable  = False  # TODO: allows on home page ?

    def detailview_display(self, context):
        # btc = self.get_block_template_context(
        btc = self.get_template_context(
                context,
                CremeEntity.objects.filter(is_deleted=True),
                # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
         )
        CremeEntity.populate_real_entities(btc['page'].object_list)

        return self._render(btc)


class StatisticsBrick(Brick):
    id_           = Brick.generate_id('creme_core', 'statistics')
    verbose_name  = _(u'Statistics')
    template_name = 'creme_core/bricks/statistics.html'
    target_apps   = ('creme_core',)

    def home_display(self, context):
        has_perm = context['user'].has_perm

        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context,
                    items=[item
                            for item in statistics_registry
                                if not item.perm or has_perm(item.perm)
                          ],
                    update_url=reverse('creme_core__reload_home_blocks', args=(self.id_,)),
        ))


class JobBrick(Brick):
    id_           = Brick.generate_id('creme_core', 'job')
    dependencies  = (Job,)
    verbose_name  = 'Job'
    template_name = 'creme_core/bricks/job.html'
    configurable  = False

    def detailview_display(self, context):
        job = context['job']

        return self._render(self.get_template_context(
                    context, job=job,
                    JOB_OK=Job.STATUS_OK,
                    JOB_ERROR=Job.STATUS_ERROR,
                    JOB_WAIT=Job.STATUS_WAIT,
                    # PERIODIC=JobType.PERIODIC,
                    NOT_PERIODIC=JobType.NOT_PERIODIC,
        ))


class JobResultsBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('creme_core', 'job_results')
    dependencies  = (JobResult,)
    order_by      = 'id'
    verbose_name  = 'Job results'
    template_name = 'creme_core/bricks/job-results.html'
    configurable  = False
    page_size     = 50

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
    id_           = QuerysetBrick.generate_id('creme_core', 'job_errors')
    verbose_name  = 'Job errors'
    template_name = 'creme_core/bricks/job-errors.html'

    def _build_queryset(self, job):
        return super(JobErrorsBrick, self)._build_queryset(job).filter(raw_messages__isnull=False)

    def _extra_context(self, job):
        return {'JOB_ERROR': Job.STATUS_ERROR}


class EntityJobErrorsBrick(JobErrorsBrick):
    id_           = QuerysetBrick.generate_id('creme_core', 'entity_job_errors')
    dependencies  = (EntityJobResult,)
    verbose_name  = 'Entity job errors'
    template_name = 'creme_core/bricks/entity-job-errors.html'


class MassImportJobErrorsBrick(JobErrorsBrick):
    id_           = QuerysetBrick.generate_id('creme_core', 'mass_import_job_errors')
    dependencies  = (MassImportJobResult,)
    verbose_name  = 'Mass import job errors'
    template_name = 'creme_core/bricks/massimport-errors.html'


class JobsBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('creme_core', 'jobs')
    dependencies  = (Job,)
    # order_by      = '-created'
    verbose_name  = 'Jobs'
    template_name = 'creme_core/bricks/jobs.html'
    configurable  = False
    page_size     = 50
    permission    = None

    def detailview_display(self, context):
        user = context['user']
        jobs = Job.objects.all()

        if not user.is_superuser:
            jobs = jobs.filter(user=user)

        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context, jobs,
                    # TODO: computed twice when user is not superuser...
                    user_jobs_count=Job.objects.filter(user=user).count(),
                    MAX_JOBS_PER_USER=settings.MAX_JOBS_PER_USER,
                    JOB_WAIT=Job.STATUS_WAIT,
                    # PERIODIC=JobType.PERIODIC,
                    NOT_PERIODIC=JobType.NOT_PERIODIC,
        ))
