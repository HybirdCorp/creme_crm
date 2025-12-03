################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
import warnings
from collections import defaultdict

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model, Q
from django.utils.translation import gettext_lazy as _

from .core import notification
from .core.entity_cell import EntityCellCustomField
from .creme_jobs.base import JobType
from .gui import button_menu, statistics
from .gui.bricks import Brick, BrickManager, QuerysetBrick, SimpleBrick
from .gui.history import html_history_registry
from .models import (  # CremeUser
    ButtonMenuItem,
    CremeEntity,
    CremeProperty,
    CustomField,
    Imprint,
    Job,
    LastViewedEntity,
    Notification,
    PinnedEntity,
    Relation,
    RelationType,
)
from .models.history import TYPE_SYM_REL_DEL, TYPE_SYM_RELATION, HistoryLine
from .utils.content_type import entity_ctypes

logger = logging.getLogger(__name__)


class ButtonsBrick(SimpleBrick):
    id = SimpleBrick.generate_id('creme_core', 'buttons')
    # dependencies => filled dynamically (see detailview_display()/_set_dependencies())
    verbose_name = 'Button menu'
    template_name = 'creme_core/bricks/buttons.html'
    configurable = False

    button_registry = button_menu.button_registry

    # def _get_buttons(self, entity: CremeEntity, user: CremeUser) -> dict[str, Button]:
    def _get_buttons(self, entity: CremeEntity, request) -> dict[str, button_menu.Button]:
        registry = self.button_registry
        # NB1: remember that dicts keep the order of insertion
        # NB2: we insert mandatory buttons at the beginning
        buttons = {
            # button.id: button for button in registry.mandatory_buttons(entity=entity)
            button.id: button
            for button in registry.mandatory_buttons(entity=entity, request=request)
        }
        user = request.user

        if user.is_superuser:
            role_q = Q(superuser=True)

            def role_predicate(item):
                return item.superuser
        else:
            role_q = Q(role=user.role)

            def role_predicate(item):
                return item.role_id is not None

        # NB: 'order' field is used as natural ordering
        items = ButtonMenuItem.objects.filter(
            Q(content_type=entity.entity_type) | Q(content_type__isnull=True)
        ).filter(role_q | Q(superuser=False, role=None))
        role_items = [*filter(role_predicate, items)]

        for button in registry.get_buttons(
            # id_list=[item.button_id for item in (role_items or items) if item.button_id],
            button_ids=[
                item.button_id for item in (role_items or items) if item.button_id
            ],
            entity=entity,
            request=request,
        ):
            buttons[button.id] = button

        return buttons

    def _set_dependencies(self,
                          buttons: dict[str, button_menu.Button],
                          model: type[CremeEntity],
                          ) -> None:
        deps: set[type[Model]] = set()
        rtype_deps: set[str] = set()
        CURRENT = button_menu.Button.CURRENT
        for button in buttons.values():
            deps.update(
                model if dep == CURRENT else dep
                for dep in button.dependencies
            )
            rtype_deps.update(button.relation_type_deps)

        self.dependencies = [*deps]
        self.relation_type_deps = [*rtype_deps]

    def get_template_context(self, context, **extra_kwargs):
        entity = context['object']
        request = context['request']
        buttons = self._get_buttons(entity=entity, request=request)
        self._set_dependencies(buttons=buttons, model=type(entity))

        return super().get_template_context(
            context,
            buttons=[
                button.get_context(entity=entity, request=request)
                for button in buttons.values()
            ],
            **extra_kwargs
        )

    # def detailview_display(self, context):
    #     entity = context['object']
    #     request = context['request']
    #     buttons = self._get_buttons(entity=entity, user=context['user'])
    #     self._set_dependencies(buttons=buttons, model=type(entity))
    #
    #     return self._render(self.get_template_context(
    #         context,
    #         buttons=[
    #             button.get_context(entity=entity, request=request)
    #             for button in buttons.values()
    #         ],
    #     ))


class PropertiesBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('creme_core', 'properties')
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
    id = QuerysetBrick.generate_id('creme_core', 'relations')
    verbose_name = _('Relationships')
    description = _(
        'Displays the entities which are linked to the current entity with a Relationship. '
        'A Relationship is: \n'
        '- typed (examples of types: «is a customer of», «has been sent by»)\n'
        '- has a symmetric relationship'
        ' (e.g. «is a customer of» & «is a supplier of» are symmetric)\n'
        'App: Core'
    )

    # NB: indeed (Relation, CremeEntity) but useless because
    # _iter_dependencies_info() has been overridden.
    dependencies = (Relation,)

    relation_type_deps = ()  # Voluntarily void -> see detailview_display()
    # order_by = 'type__predicate'
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
                return isinstance(rtype_ids, list | tuple) and all(
                    isinstance(x, str) for x in rtype_ids
                )

            info_are_ok = is_a_list_of_strings('include') and is_a_list_of_strings('exclude')

        if info_are_ok:
            self._reloading_info = info
        else:
            # We do not leave 'None' (because it means 'first render').
            self._reloading_info = {}
            logger.warning('Invalid reloading extra_data for RelationsBrick: %s', info)

    def _iter_dependencies_info(self):
        # In order a JS dependencies intelligence want to get the real dependence.
        yield 'creme_core.relation'

        for rtype_id in self._included_rtype_ids:
            yield 'creme_core.relation.' + rtype_id

    def detailview_display(self, context):
        entity = context['object']
        # relations = entity.relations.select_related(
        #     'type', 'type__symmetric_type',
        # ).prefetch_related('real_object')
        # NB: we order by:
        #   - "type__predicate" + "type_id" to group relationships by their type
        #     (& preventing issues with types with identical predicate-- even if
        #     you should avoid this).
        #   - "object_entity" which will be extended to
        #     <object_entity__header_filter_search_field>, for alphabetical
        #     ordering of object-entities.
        #   - "id" to get a consistent ordering of entities between different queries
        #     (it's important for pagination)
        relations = entity.relations.select_related(
            'type', 'type__symmetric_type',
        ).order_by(
            'type__predicate', 'type_id', 'object_entity', 'id',
        ).prefetch_related('real_object')

        included_rtype_ids = self._included_rtype_ids
        excluded_rtype_ids = self._excluded_rtype_ids
        reloading_info = self._reloading_info

        if reloading_info is None:  # NB: it's not a reloading, it's the initial render()
            used_rtype_ids = {
                rt_id
                for brick in BrickManager.get(context).bricks
                for rt_id in brick.relation_type_deps
            }
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

        return self._render(self.get_template_context(
            context, relations,
            excluded_rtype_ids=excluded_rtype_ids,
        ))


class CustomFieldsBrick(SimpleBrick):
    id = SimpleBrick.generate_id('creme_core', 'customfields')
    verbose_name = _('Custom fields')
    description = _(
        'Displays the values of the Custom Fields for the current entity. '
        'Custom Fields can be created in the general configuration.\n'
        'App: Core'
    )
    dependencies = (CustomField,)
    template_name = 'creme_core/bricks/custom-fields.html'

    def get_template_context(self, context, **extra_kwargs):
        entity = context['object']

        # TODO: factorise with CremeEntity.get_custom_fields_n_values() ?
        cfields = [
            cfield
            for cfield in CustomField.objects.get_for_model(entity.entity_type).values()
            if not cfield.is_deleted
        ]
        CremeEntity.populate_custom_values([entity], cfields)

        return super().get_template_context(
            context,
            cells=[EntityCellCustomField(cfield) for cfield in cfields],
            **extra_kwargs
        )

    # def detailview_display(self, context):
    #     entity = context['object']
    #
    #     # TODO: factorise with CremeEntity.get_custom_fields_n_values() ?
    #     cfields = [
    #         cfield
    #         for cfield in CustomField.objects.get_for_model(entity.entity_type).values()
    #         if not cfield.is_deleted
    #     ]
    #     CremeEntity.populate_custom_values([entity], cfields)
    #
    #     return self._render(self.get_template_context(
    #         context,
    #         cells=[EntityCellCustomField(cfield) for cfield in cfields],
    #     ))


class HistoryBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('creme_core', 'history')
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
        entity = context['object']
        btc = self.get_template_context(context, HistoryLine.objects.filter(entity=entity.pk))
        hlines = btc['page'].object_list
        user = context['user']

        HistoryLine.populate_related_lines(hlines)
        related_hlines = [*filter(None, (hline.related_line for hline in hlines))]
        self._populate_related_real_entities(related_hlines)

        HistoryLine.populate_users(hlines, user)
        self._populate_explainers([*hlines, *related_hlines], user)

        for hline in hlines:
            hline.entity = entity  # Avoids queries

            # All lines are referencing "entity", which can be viewed.
            hline.can_be_viewed = True

        return self._render(btc)

    def home_display(self, context):
        user = context['user']
        qs = HistoryLine.objects.exclude(type__in=(TYPE_SYM_RELATION, TYPE_SYM_REL_DEL))

        if not user.is_superuser:
            qs = qs.filter(entity_ctype__in=[
                *entity_ctypes(app_labels=user.role.extended_allowed_apps),
            ])

        btc = self.get_template_context(context, qs, HIDDEN_VALUE=settings.HIDDEN_VALUE)
        hlines = btc['page'].object_list

        HistoryLine.populate_related_lines(hlines)
        related_hlines = [*filter(None, (hline.related_line for hline in hlines))]
        extended_hlines = [*hlines, *related_hlines]

        self._populate_related_real_entities(extended_hlines)
        HistoryLine.populate_users(hlines, user)
        self._populate_perms(hlines, user)
        self._populate_explainers(extended_hlines, user)

        return self._render(btc)


class ImprintsBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('creme_core', 'imprints')
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
        return self._render(self.get_template_context(
            context,
            # NB: there will still be queries for each different Contacts
            #     corresponding to users...
            Imprint.objects.prefetch_related('real_entity', 'user')
            if context['user'].is_superuser else
            Imprint.objects.none()
        ))


class TrashBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('creme_core', 'trash')
    verbose_name = _('Trash')
    dependencies = (CremeEntity,)
    order_by = '-modified'
    template_name = 'creme_core/bricks/trash.html'
    page_size = 50
    # permissions = None  # NB: the template uses credentials
    configurable = False  # TODO: allows on home page ?

    def detailview_display(self, context):
        btc = self.get_template_context(
            context,
            CremeEntity.objects.filter(is_deleted=True),
            display_header_button=settings.ENTITIES_DELETION_ALLOWED,
        )
        CremeEntity.populate_real_entities(btc['page'].object_list)

        return self._render(btc)


class RecentEntitiesBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('creme_core', 'recent_entities')
    verbose_name = _('Recent entities')
    dependencies = (LastViewedEntity,)
    order_by = '-viewed'
    template_name = 'creme_core/bricks/recent-entities.html'
    page_size = QuerysetBrick.page_size * 2

    def home_display(self, context):
        return self._render(self.get_template_context(
            context,
            # TODO: factorise with <creme_core.menu.RecentEntitiesEntry> ?
            LastViewedEntity.objects.filter(
                user=context['user'],
                entity__is_deleted=False,
            ).prefetch_related('real_entity'),
        ))


class PinnedEntitiesBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('creme_core', 'pinned_entities')
    verbose_name = _('Pinned entities')
    description = _(
        'Even if the pinned entities are the same as the ones in the menu, '
        'this block allows you to unpin entities which you cannot view anymore.\n'
        'App: Core'
    )
    dependencies = (PinnedEntity,)
    order_by = '-created'
    template_name = 'creme_core/bricks/pinned-entities.html'

    def home_display(self, context):
        return self._render(self.get_template_context(
            context,
            PinnedEntity.objects.filter(
                user=context['user'],
            ).prefetch_related('real_entity'),
            # TODO: message if max pins is reached?
        ))


class StatisticsBrick(Brick):
    id = Brick.generate_id('creme_core', 'statistics')
    verbose_name = _('Statistics')
    description = _(
        'Displays many statistics (e.g. the numbers of customers), depending '
        'on installed apps.\n'
        'App: Core'
    )
    template_name = 'creme_core/bricks/statistics.html'

    # statistics_registry = statistics.statistic_registry
    statistic_registry = statistics.statistic_registry

    def _get_items(self, user):
        has_perm = user.has_perm

        return [
            item
            for item in self.statistic_registry
            if not item.perm or has_perm(item.perm)
        ]

    def get_template_context(self, context, **extra_kwargs):
        return super().get_template_context(
            context,
            items=self._get_items(user=context['user']),
            **extra_kwargs
        )

    def home_display(self, context):
        # has_perm = context['user'].has_perm
        #
        # return self._render(self.get_template_context(
        #     context,
        #     items=[
        #         item
        #         for item in self.statistics_registry
        #         if not item.perm or has_perm(item.perm)
        #     ],
        # ))
        return self._render(self.get_template_context(context))


# class JobBrick(Brick):
#     id = Brick.generate_id('creme_core', 'job')
#     dependencies = (Job,)
#     verbose_name = _('Job')
#     template_name = 'creme_core/bricks/job.html'
#     configurable = False
#
#     @Brick.reloading_info.setter
#     def reloading_info(self, info):
#         info_are_ok = False
#
#         if isinstance(info, dict):
#             info_are_ok = isinstance(info.get('list_url', ''), str)
#
#         if info_are_ok:
#             self._reloading_info = info
#         else:
#             # We do not leave 'None' (because it means 'first render').
#             self._reloading_info = {}
#             logger.warning('Invalid reloading extra_data for JobBrick: %s', info)
#
#     def detailview_display(self, context):
#         job = context['job']
#
#         reloading_info = self._reloading_info
#
#         if reloading_info is None:  # NB: it's not a reloading, it's the initial render()
#             list_url = context.get('list_url')
#             self._reloading_info = {'list_url': list_url}
#         else:
#             list_url = reloading_info.get('list_url')
#
#         return self._render(self.get_template_context(
#             context, job=job,
#             JOB_OK=Job.STATUS_OK,
#             JOB_ERROR=Job.STATUS_ERROR,
#             JOB_WAIT=Job.STATUS_WAIT,
#             # PERIODIC=JobType.PERIODIC,
#             NOT_PERIODIC=JobType.NOT_PERIODIC,
#             list_url=list_url,
#         ))


class JobsBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('creme_core', 'jobs')
    verbose_name = _('Jobs')
    dependencies = (Job,)
    template_name = 'creme_core/bricks/jobs-all.html'
    configurable = False
    page_size = 50
    # permission = None

    def _jobs_qs(self, context):
        # NB: would be cool to order by app's verbose name + job type's verbose name.
        #     This ordering regroups jobs per app, it's not bad.
        return Job.objects.order_by('type_id', 'id')

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context, self._jobs_qs(context),
            not_finished_user_jobs_count=Job.objects.not_finished(context['user']).count(),
            MAX_JOBS_PER_USER=settings.MAX_JOBS_PER_USER,
            NOT_PERIODIC=JobType.NOT_PERIODIC,
            PSEUDO_PERIODIC=JobType.PSEUDO_PERIODIC,
        ))


class MyJobsBrick(JobsBrick):
    id = QuerysetBrick.generate_id('creme_core', 'my_jobs')
    verbose_name = _('My jobs')
    template_name = 'creme_core/bricks/jobs-mine.html'

    def _jobs_qs(self, context):
        return super()._jobs_qs(context=context).filter(user=context['user'])


class NotificationsBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('creme_core', 'notifications')
    verbose_name = _('Notifications')
    dependencies = (Notification,)
    template_name = 'creme_core/bricks/notifications.html'
    configurable = False
    page_size = 50

    def detailview_display(self, context):
        user = context['user']
        btc = self.get_template_context(
            context,
            Notification.objects.filter(
                user=user, discarded=None, output=notification.OUTPUT_WEB,
            ).order_by('-id').select_related('channel'),
        )

        for notif in btc['page'].object_list:
            content = notif.content
            notif.content_subject = content.get_subject(user=user)
            notif.content_body = (
                content.get_html_body(user=user) or content.get_body(user=user)
            )

        return self._render(btc)


def __getattr__(name):
    if name == 'JobResultsBrick':
        warnings.warn(
            '"JobResultsBrick" has moved to <creme_core.gui.job>; '
            'fix your import statement.',
            DeprecationWarning,
        )
        from .gui.job import JobResultsBrick

        return JobResultsBrick

    if name == 'JobErrorsBrick':
        warnings.warn(
            '"JobErrorsBrick" has moved to <creme_core.gui.job>; '
            'fix your import statement.',
            DeprecationWarning,
        )
        from .gui.job import JobErrorsBrick

        return JobErrorsBrick

    if name == 'EntityJobErrorsBrick':
        warnings.warn(
            '"EntityJobErrorsBrick" has moved to <creme_core.gui.job>; '
            'fix your import statement.',
            DeprecationWarning,
        )
        from .gui.job import EntityJobErrorsBrick

        return EntityJobErrorsBrick

    if name == 'MassImportJobErrorsBrick':
        warnings.warn(
            '"MassImportJobErrorsBrick" has moved to <creme_core.creme_jobs.mass_import>; '
            'fix your import statement.',
            DeprecationWarning,
        )
        from .creme_jobs.mass_import import MassImportJobErrorsBrick

        return MassImportJobErrorsBrick

    if name == 'TrashCleanerJobErrorsBrick':
        warnings.warn(
            '"TrashCleanerJobErrorsBrick" has moved to <creme_core.creme_jobs.trash_cleaner>; '
            'fix your import statement.',
            DeprecationWarning,
        )
        from .creme_jobs.trash_cleaner import TrashCleanerJobErrorsBrick

        return TrashCleanerJobErrorsBrick

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
