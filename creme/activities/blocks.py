# -*- coding: utf-8 -*-

from itertools import chain
import warnings

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.gui.block import QuerysetBlock, list4url
from creme.creme_core.models import CremeEntity, Relation

from .bricks import (
    Activity, Organisation,
    ParticipantsBrick as ParticipantsBlock,
    SubjectsBrick as SubjectsBlock,
    UserCalendarsBrick as UserCalendars,
    RelatedCalendarBrick as RelatedCalendar,
)
from .constants import (REL_SUB_PART_2_ACTIVITY, REL_OBJ_PART_2_ACTIVITY,
        REL_SUB_ACTIVITY_SUBJECT, REL_OBJ_ACTIVITY_SUBJECT,
        REL_SUB_LINKED_2_ACTIVITY, REL_OBJ_LINKED_2_ACTIVITY)


warnings.warn('activities.blocks is deprecated ; use activities.bricks instead.', DeprecationWarning)


class FutureActivitiesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('activities', 'future_activities')
    dependencies  = (Relation, Activity)
    relation_type_deps = (REL_SUB_LINKED_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT, REL_SUB_PART_2_ACTIVITY)
    verbose_name  = _(u'Future activities')
    template_name = 'activities/templatetags/block_future_activities.html'

    _RTYPES_2_POP = (REL_OBJ_PART_2_ACTIVITY, REL_OBJ_ACTIVITY_SUBJECT, REL_OBJ_LINKED_2_ACTIVITY)

    def _get_queryset_for_entity(self, entity, context):
        if isinstance(entity, Organisation):
            return Activity.get_future_linked_for_orga(entity, context['today'])
        else:
            return Activity.get_future_linked(entity, context['today'])

    def _get_queryset_for_ctypes(self, ct_ids, context):
        return Activity.get_future_linked_for_ctypes(ct_ids, context['today'])

    def get_block_template_context(self, *args, **kwargs):
        # ctxt = super(FutureActivitiesBlock, self).get_block_template_context(*args, **kwargs)
        ctxt = super(FutureActivitiesBlock, self).get_template_context(*args, **kwargs)

        activities = ctxt['page'].object_list
        CremeEntity.populate_relations(activities, self._RTYPES_2_POP)  # Optimisation

        entity = ctxt.get('object')
        if entity is not None:
            for activity in activities:
                activity.enable_unlink_button = True

            if isinstance(entity, Organisation):
                # We display the 'unlink' button only for Activities that have
                # at least a Relation with the Organisation (if a direct Relation
                # does not exist the button is useless).
                for activity in activities:
                    activity.enable_unlink_button = \
                        any(entity.id == rel.object_entity_id
                                for rel in chain(activity.get_subject_relations(),
                                                 activity.get_linkedto_relations(),
                                                )
                           )

        return ctxt

    def detailview_display(self, context):
        entity = context['object']
        return self._render(self.get_block_template_context(
                    context,
                    self._get_queryset_for_entity(entity, context).select_related('status'),
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.id),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, entity.id)),
                    predicate_id=REL_SUB_LINKED_2_ACTIVITY,
                    ct_id=ContentType.objects.get_for_model(Activity).id,
                    display_review=Activity.display_review(),
                ))

    def portal_display(self, context, ct_ids):
        return self._render(self.get_block_template_context(
                    context,
                    self._get_queryset_for_ctypes(ct_ids, context).select_related('status'),
                    # update_url='/creme_core/blocks/reload/portal/%s/%s/' % (self.id_, list4url(ct_ids)),
                    update_url=reverse('creme_core__reload_portal_blocks', args=(self.id_, list4url(ct_ids))),
                    display_review=Activity.display_review(),
                ))

    def home_display(self, context):
        return self._render(self.get_block_template_context(
                    context,
                    self._get_queryset_for_entity(context['user'].linked_contact, context)
                        .select_related('status'),
                    # update_url='/creme_core/blocks/reload/home/%s/' % self.id_,
                    update_url=reverse('creme_core__reload_home_blocks', args=(self.id_,)),
                    is_home=True,
                    display_review=Activity.display_review(),
                ))


class PastActivitiesBlock(FutureActivitiesBlock):
    id_           = FutureActivitiesBlock.generate_id('activities', 'past_activities')
    verbose_name  = _(u'Past activities')
    template_name = 'activities/templatetags/block_past_activities.html'

    def _get_queryset_for_entity(self, entity, context):
        if isinstance(entity, Organisation):
            return Activity.get_past_linked_for_orga(entity, context['today'])
        else:
            return Activity.get_past_linked(entity, context['today'])

    def _get_queryset_for_ctypes(self, ct_ids, context):
        return Activity.get_past_linked_for_ctypes(ct_ids, context['today'])


participants_block      = ParticipantsBlock()
subjects_block          = SubjectsBlock()
future_activities_block = FutureActivitiesBlock()
past_activities_block   = PastActivitiesBlock()
user_calendars_block    = UserCalendars()
related_calendar_block  = RelatedCalendar()

block_list = (
    participants_block,
    subjects_block,
    future_activities_block,
    past_activities_block,
    user_calendars_block,
    related_calendar_block,
)
