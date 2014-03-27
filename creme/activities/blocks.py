# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from creme.creme_core.models import CremeEntity, Relation
from creme.creme_core.gui.block import QuerysetBlock, list4url

from creme.persons.models import Contact, Organisation

from .models import Activity, Calendar
from .constants import *


class ParticipantsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('activities', 'participants')
    dependencies  = (Relation, Contact, Calendar)
    relation_type_deps = (REL_OBJ_PART_2_ACTIVITY,)
    verbose_name  = _(u'Participants')
    template_name = 'activities/templatetags/block_participants.html'
    target_ctypes = (Activity, )

    def detailview_display(self, context):
        activity = context['object']
        btc = self.get_block_template_context(
                        context,
                        activity.relations.filter(type=REL_OBJ_PART_2_ACTIVITY)
                                          .select_related('type', 'object_entity'),
                        update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, activity.pk),
                    )
        relations = btc['page'].object_list
        #TODO: select_related(depth=1) ?? remove civility with better entity repr system ??
        #TODO: move in Relation.populate_real_objects() (with new arg for fixed model) ???
        contacts = dict((c.id, c)
                            for c in Contact.objects.filter(pk__in=[r.object_entity_id for r in relations])
                                                    .select_related('user', 'is_user', 'civility')
                       )

        for relation in relations:
            relation.object_entity = contacts[relation.object_entity_id]

        users_contacts = dict((contact.is_user_id, contact)
                                for contact in contacts.itervalues()
                                    if contact.is_user_id
                             )

        for calendar in Calendar.objects.filter(user__in=users_contacts.keys(), activity=activity.id):
            users_contacts[calendar.user_id].calendar_cache = calendar

        return self._render(btc)


class SubjectsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('activities', 'subjects')
    dependencies  = (Relation,)
    relation_type_deps = (REL_OBJ_ACTIVITY_SUBJECT,)
    verbose_name  = _(u'Subjects')
    template_name = 'activities/templatetags/block_subjects.html'
    target_ctypes = (Activity, )

    def detailview_display(self, context):
        activity = context['object']
        btc = self.get_block_template_context(context,
                                              activity.relations.filter(type=REL_OBJ_ACTIVITY_SUBJECT).select_related('type', 'object_entity'),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, activity.pk),
                                             )

        Relation.populate_real_object_entities(btc['page'].object_list)

        return self._render(btc)


class FutureActivitiesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('activities', 'future_activities')
    dependencies  = (Relation, Activity)
    relation_type_deps = (REL_SUB_LINKED_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT, REL_SUB_PART_2_ACTIVITY)
    verbose_name  = _(u'Future activities')
    template_name = 'activities/templatetags/block_future_activities.html'
    #configurable  = True

    _RTYPES_2_POP = (REL_OBJ_PART_2_ACTIVITY, REL_OBJ_ACTIVITY_SUBJECT, REL_OBJ_LINKED_2_ACTIVITY)

    def _get_queryset_for_entity(self, entity, context):
        if isinstance(entity, Organisation):
            return Activity.get_future_linked_for_orga(entity, context['today'])
        else:
            return Activity.get_future_linked(entity, context['today'])

    def _get_queryset_for_ctypes(self, ct_ids, context):
        return Activity.get_future_linked_for_ctypes(ct_ids, context['today'])

    def _render(self, template_context):
        #optimisation
        CremeEntity.populate_relations(template_context['page'].object_list,
                                       self._RTYPES_2_POP, #template_context['user'],
                                      )

        return super(FutureActivitiesBlock, self)._render(template_context)

    def detailview_display(self, context):
        entity = context['object']
        return self._render(self.get_block_template_context(
                    context,
                    self._get_queryset_for_entity(entity, context).select_related('status'),
                    update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.id),
                    predicate_id=REL_SUB_LINKED_2_ACTIVITY,
                    ct_id=ContentType.objects.get_for_model(Activity).id,
                    display_review=Activity.display_review(),
                ))

    def portal_display(self, context, ct_ids):
        return self._render(self.get_block_template_context(
                    context,
                    self._get_queryset_for_ctypes(ct_ids, context).select_related('status'),
                    update_url='/creme_core/blocks/reload/portal/%s/%s/' % (self.id_, list4url(ct_ids)),
                    display_review=Activity.display_review(),
                ))

    def home_display(self, context):
        user = context['request'].user
        #cache the Contact related to the current user (used by PastActivitiesBlock too)
        entity = context.get('user_contact')
        if entity is None:
            #context['user_contact'] = entity = Contact.get_user_contact_or_mock(user)
            context['user_contact'] = entity = user.linked_contact

        return self._render(self.get_block_template_context(
                    context,
                    self._get_queryset_for_entity(entity, context).select_related('status'),
                    update_url='/creme_core/blocks/reload/home/%s/' % self.id_,
                    is_home=True,
                    display_review=Activity.display_review(),
                ))


class PastActivitiesBlock(FutureActivitiesBlock):
    id_           = QuerysetBlock.generate_id('activities', 'past_activities')
    verbose_name  = _(u'Past activities')
    template_name = 'activities/templatetags/block_past_activities.html'

    def _get_queryset_for_entity(self, entity, context):
        if isinstance(entity, Organisation):
            return Activity.get_past_linked_for_orga(entity, context['today'])
        else:
            return Activity.get_past_linked(entity, context['today'])

    def _get_queryset_for_ctypes(self, ct_ids, context):
        return Activity.get_past_linked_for_ctypes(ct_ids, context['today'])


class UserCalendars(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('activities', 'user_calendars')
    dependencies  = (Calendar, )
    verbose_name  = u'My calendars'
    template_name = 'activities/templatetags/block_user_calendars.html'
    configurable  = False
    order_by      = 'name'
    permission    = None #NB: used by the view creme_core.views.blocks.reload_basic ; None means 'No special permission required'

    def detailview_display(self, context):
        #NB: credentials are OK : we retrieve only Calendars related of the user
        user = context['user']
        #in case the user has just been created, creates his default calendar
        Calendar.get_user_default_calendar(user)
        return self._render(self.get_block_template_context(
                    context,
                    Calendar.objects.filter(user=user),
                    update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    has_app_perm=user.has_perm('activities'),
                ))


class RelatedCalendar(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('activities', 'related_calendar')
    dependencies  = (Calendar, )
    verbose_name  = u'On my calendars'
    template_name = 'activities/templatetags/block_related_calendar.html'
    order_by      = 'name'
    target_ctypes = (Activity, )

    def detailview_display(self, context):
        user = context['user']
        activity = context['object']
        return self._render(self.get_block_template_context(
                    context,
                    activity.calendars.filter(user=user),
                    update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, activity.pk),
                    has_app_perm=user.has_perm('activities'),
                ))


participants_block           = ParticipantsBlock()
subjects_block               = SubjectsBlock()
future_activities_block      = FutureActivitiesBlock()
past_activities_block        = PastActivitiesBlock()
user_calendars_block         = UserCalendars()
related_calendar_block       = RelatedCalendar()

block_list = (
        participants_block,
        subjects_block,
        future_activities_block,
        past_activities_block,
        user_calendars_block,
        related_calendar_block,
    )
