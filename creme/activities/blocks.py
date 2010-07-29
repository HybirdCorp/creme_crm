# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import Relation
from creme_core.gui.block import QuerysetBlock

from models import Activity
from constants import REL_SUB_PART_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT, REL_SUB_LINKED_2_ACTIVITY


class ParticipantsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('activities', 'participants')
    dependencies  = (Relation,)
    verbose_name  = _(u'Participants')
    template_name = 'activities/templatetags/block_participants.html'

    def detailview_display(self, context):
        activity = context['object']
        return self._render(self.get_block_template_context(context, activity.get_participant_relations(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, activity.pk),
                                                            ))


class SubjectsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('activities', 'subjects')
    dependencies  = (Relation,)
    verbose_name  = _(u'Sujets')
    template_name = 'activities/templatetags/block_subjects.html'

    def detailview_display(self, context):
        activity = context['object']
        return self._render(self.get_block_template_context(context, activity.get_subject_relations(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, activity.pk),
                                                            ))


class FutureActivitiesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('activities', 'future_activities')
    dependencies  = (Relation,) #Activity
    verbose_name  = _(u'Activités futures')
    template_name = 'activities/templatetags/block_future_activities.html'

    def __init__(self, *args, **kwargs):
        super(FutureActivitiesBlock, self).__init__(*args, **kwargs)

        self._activity_ct_id = None

    def detailview_display(self, context):
        entity = context['object']
        activities = Activity.get_future_linked(entity, context['today'])

        if not self._activity_ct_id:
            self._activity_ct_id = ContentType.objects.get_for_model(Activity).id

        return self._render(self.get_block_template_context(context, activities,
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.id),
                                                            predicate_id=REL_SUB_LINKED_2_ACTIVITY,
                                                            ct_id=self._activity_ct_id,
                                                            ))


class PastActivitiesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('activities', 'past_activities')
    dependencies  = (Relation,) #Activity
    verbose_name  = _(u'Activités passées')
    template_name = 'activities/templatetags/block_past_activities.html'

    def detailview_display(self, context):
        entity = context['object']
        activities = Activity.get_past_linked(entity, context['today'])

        return self._render(self.get_block_template_context(context, activities,
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.id),
                                                            ))


participants_block      = ParticipantsBlock()
subjects_block          = SubjectsBlock()
future_activities_block = FutureActivitiesBlock()
past_activities_block   = PastActivitiesBlock()
