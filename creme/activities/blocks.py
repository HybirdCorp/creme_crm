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
from creme_core.gui.block import QuerysetBlock, list4url

from persons.models import Contact

from models import Activity, Calendar
from constants import *


class ParticipantsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('activities', 'participants')
    dependencies  = (Relation,)
    relation_type_deps = (REL_OBJ_PART_2_ACTIVITY,)
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
    relation_type_deps = (REL_OBJ_ACTIVITY_SUBJECT,)
    verbose_name  = _(u'Subjects')
    template_name = 'activities/templatetags/block_subjects.html'

    def detailview_display(self, context):
        activity = context['object']
        return self._render(self.get_block_template_context(context, activity.get_subject_relations(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, activity.pk),
                                                            ))


#TODO: need query optimisations (retrieve all relations in one query,
#      retrieve subjects (real entities) of relations by grouping them)
class FutureActivitiesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('activities', 'future_activities')
    dependencies  = (Relation,) #Activity
    relation_type_deps = (REL_SUB_LINKED_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT, REL_SUB_PART_2_ACTIVITY)
    verbose_name  = _(u'Future activities')
    template_name = 'activities/templatetags/block_future_activities.html'
    configurable  = True

    def _get_queryset_for_entity(self, entity, context):
        return Activity.get_future_linked(entity, context['today'])

    def _get_queryset_for_ctypes(self, ct_ids, context):
        return Activity.get_future_linked_for_ctypes(ct_ids, context['today'])


    def detailview_display(self, context):
        entity = context['object']

        return self._render(self.get_block_template_context(context,
                                                            self._get_queryset_for_entity(entity, context),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.id),
                                                            predicate_id=REL_SUB_LINKED_2_ACTIVITY,
                                                            ct_id=ContentType.objects.get_for_model(Activity).id,
                                                           ))

    def portal_display(self, context, ct_ids):
        return self._render(self.get_block_template_context(context,
                                                            self._get_queryset_for_ctypes(ct_ids, context),
                                                            update_url='/creme_core/blocks/reload/portal/%s/%s/' % (self.id_, list4url(ct_ids)),
                                                           ))

    def home_display(self, context):
        user = context['request'].user

        #cache the Contact related to the current user (used by PastActivitiesBlock too)
        entity = context.get('user_contact')
        if entity is None:
            context['user_contact'] = entity = Contact.objects.get(is_user=user)

        return self._render(self.get_block_template_context(context,
                                                            self._get_queryset_for_entity(entity, context),
                                                            update_url='/creme_core/blocks/reload/home/%s/' % self.id_,
                                                            is_home=True
                                                           ))


class PastActivitiesBlock(FutureActivitiesBlock):
    id_           = QuerysetBlock.generate_id('activities', 'past_activities')
    verbose_name  = _(u'Past activities')
    template_name = 'activities/templatetags/block_past_activities.html'

    def _get_queryset_for_entity(self, entity, context):
        return Activity.get_past_linked(entity, context['today'])

    def _get_queryset_for_ctypes(self, ct_ids, context):
        return Activity.get_past_linked_for_ctypes(ct_ids, context['today'])


class UserCalendars(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('activities', 'user_calendars')
    dependencies  = (Calendar, )
    verbose_name  = _(u'My calendars')
    template_name = 'activities/templatetags/block_user_calendars.html'
    order_by      = 'name'

    def detailview_display(self, context):
        model = Calendar
        user = context['request'].user
        return self._render(self.get_block_template_context(context,
                                                            Calendar.objects.filter(user=user),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           ))


participants_block      = ParticipantsBlock()
subjects_block          = SubjectsBlock()
future_activities_block = FutureActivitiesBlock()
past_activities_block   = PastActivitiesBlock()
user_calendars_block    = UserCalendars()
