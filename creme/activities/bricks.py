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

from itertools import chain

from django.utils.translation import gettext_lazy as _

from creme import persons
from creme.creme_core.gui.bricks import QuerysetBrick, SimpleBrick
from creme.creme_core.models import CremeEntity, Relation, SettingValue

from . import constants, get_activity_model
from .models import Calendar
from .setting_keys import review_key

Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()

Activity = get_activity_model()


class ActivityBarHatBrick(SimpleBrick):
    # NB: we do not set an ID because it's the main Header Brick.
    template_name = 'activities/bricks/activity-hat-bar.html'


class ParticipantsBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('activities', 'participants')
    verbose_name = _('Participants')

    # NB: Organisation is a hack in order to reload the SubjectsBlock when
    #     auto-subjects (see SETTING_AUTO_ORGA_SUBJECTS) is enabled.
    dependencies = (Relation, Contact, Calendar, Organisation)
    relation_type_deps = (constants.REL_OBJ_PART_2_ACTIVITY,)

    template_name = 'activities//bricks/participants.html'
    order_by = 'id'  # For consistent ordering between 2 queries (for pages)

    target_ctypes = (Activity, )

    def detailview_display(self, context):
        activity = context['object']
        btc = self.get_template_context(
            context,
            activity.relations.filter(type=constants.REL_OBJ_PART_2_ACTIVITY)
            #                  .select_related('type', 'object_entity'),
        )
        relations = btc['page'].object_list
        # TODO: remove civility with better entity repr system ??
        # TODO: move in Relation.populate_real_objects() (with new arg for fixed model) ???
        contacts = Contact.objects.filter(
            pk__in=[r.object_entity_id for r in relations],
        ).select_related('user', 'is_user', 'civility').in_bulk()

        for relation in relations:
            relation.object_entity = contacts[relation.object_entity_id]

        users_contacts = {
            contact.is_user_id: contact
            for contact in contacts.values()
            if contact.is_user_id
        }

        for calendar in Calendar.objects.filter(
            user__in=users_contacts.keys(), activity=activity.id,
        ):
            users_contacts[calendar.user_id].calendar_cache = calendar

        return self._render(btc)


class SubjectsBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('activities', 'subjects')
    verbose_name = _('Subjects')

    dependencies = (Relation, Organisation)  # See ParticipantsBlock.dependencies
    relation_type_deps = (constants.REL_OBJ_ACTIVITY_SUBJECT,)

    template_name = 'activities/bricks/subjects.html'
    order_by = 'id'  # For consistent ordering between 2 queries (for pages)

    target_ctypes = (Activity, )

    def detailview_display(self, context):
        activity = context['object']
        btc = self.get_template_context(
            context,
            activity.relations.filter(type=constants.REL_OBJ_ACTIVITY_SUBJECT)
                    .select_related('object_entity'),
            #        .select_related('type', 'object_entity'),
        )

        Relation.populate_real_object_entities(btc['page'].object_list)

        return self._render(btc)


class _RelatedActivitiesBrick(QuerysetBrick):
    dependencies = (Relation, Activity)
    relation_type_deps = (
        constants.REL_SUB_LINKED_2_ACTIVITY,
        constants.REL_SUB_ACTIVITY_SUBJECT,
        constants.REL_SUB_PART_2_ACTIVITY,
    )

    _RTYPES_2_POP = (
        constants.REL_OBJ_PART_2_ACTIVITY,
        constants.REL_OBJ_ACTIVITY_SUBJECT,
        constants.REL_OBJ_LINKED_2_ACTIVITY,
    )

    def _get_queryset_for_entity(self, entity, context):
        raise NotImplementedError

    def get_template_context(self, *args, **kwargs):
        ctxt = super().get_template_context(*args, **kwargs)

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
                    activity.enable_unlink_button = any(
                        entity.id == rel.object_entity_id
                        for rel in chain(
                            activity.get_subject_relations(),
                            activity.get_linkedto_relations(),
                        )
                    )

        ctxt['display_review'] = SettingValue.objects.get_4_key(review_key).value

        return ctxt

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            self._get_queryset_for_entity(context['object'], context).select_related('status'),
            rtype_id=constants.REL_SUB_LINKED_2_ACTIVITY,
        ))

    def home_display(self, context):
        return self._render(self.get_template_context(
            context,
            self._get_queryset_for_entity(context['user'].linked_contact, context)
                .select_related('status'),
            is_home=True,
        ))


# class FutureActivitiesBrick(QuerysetBrick):
class FutureActivitiesBrick(_RelatedActivitiesBrick):
    id_ = QuerysetBrick.generate_id('activities', 'future_activities')
    verbose_name = _('Future activities')
    description = _(
        'Displays activities which:\n'
        '- are linked to the current entity with a relationship «participates»,'
        ' «is subject» or «related to the activity» (if the current entity is an'
        ' Organisation, activities linked to managers & employees are displayed too)\n'
        '- are ending in the future\n'
        'Hint: the block uses the setting value «Display minutes information in activities '
        'blocks» which is configurable in the configuration of the app «Activities».\n'
        'App: Activities'
    )
    template_name = 'activities/bricks/future-activities.html'

    def _get_queryset_for_entity(self, entity, context):
        if isinstance(entity, Organisation):
            return Activity.objects.future_linked_to_organisation(entity, context['today'])
        else:
            return Activity.objects.future_linked(entity=entity, today=context['today'])


# class PastActivitiesBrick(FutureActivitiesBrick):
class PastActivitiesBrick(_RelatedActivitiesBrick):
    id_ = QuerysetBrick.generate_id('activities', 'past_activities')
    verbose_name = _('Past activities')
    description = _(
        'Displays activities which:\n'
        '- are linked to the current entity with a relationship «participates»,'
        ' «is subject» or «related to the activity» (if the current entity is an'
        ' Organisation, activities linked to managers & employees are displayed too)\n'
        '- are ended\n'
        'Hint: it is a block complementary with the block «Future activities».\n'
        'App: Activities'
    )
    template_name = 'activities/bricks/past-activities.html'

    def _get_queryset_for_entity(self, entity, context):
        if isinstance(entity, Organisation):
            return Activity.objects.past_linked_to_organisation(entity, context['today'])
        else:
            return Activity.objects.past_linked(entity, context['today'])


class UserCalendarsBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('activities', 'user_calendars')
    verbose_name = 'My calendars'
    dependencies = (Calendar, )
    template_name = 'activities/bricks/user-calendars.html'
    configurable = False
    order_by = 'name'

    def detailview_display(self, context):
        # NB: credentials are OK, because we retrieve only Calendars related of the user.
        user = context['user']

        return self._render(self.get_template_context(
            context,
            Calendar.objects.filter(user=user),
            has_app_perm=user.has_perm('activities'),
        ))


class RelatedCalendarBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('activities', 'related_calendar')
    verbose_name = _('On my calendars')
    dependencies = (Calendar, )
    template_name = 'activities/bricks/related-calendars.html'
    order_by = 'name'

    target_ctypes = (Activity, )

    def detailview_display(self, context):
        user = context['user']
        activity = context['object']
        return self._render(self.get_template_context(
            context,
            activity.calendars.filter(user=user),
        ))
