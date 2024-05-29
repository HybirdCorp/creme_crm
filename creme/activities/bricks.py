################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from creme import persons
from creme.creme_config.bricks import GenericModelBrick
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui.bricks import Brick, QuerysetBrick, SimpleBrick
from creme.creme_core.models import CremeEntity, Relation, SettingValue

from . import constants, get_activity_model, setting_keys
from .models import (
    ActivitySubType,
    ActivityType,
    Calendar,
    CalendarConfigItem,
    Status,
)
from .setting_keys import review_key

Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()

Activity = get_activity_model()


class ActivityTypeBrick(GenericModelBrick):
    id = GenericModelBrick.generate_id('activities', 'type_config')
    template_name = 'activities/bricks/activity-types.html'
    dependencies = (ActivityType,)


class ActivityBarHatBrick(SimpleBrick):
    # NB: we do not set an ID because it's the main Header Brick.
    template_name = 'activities/bricks/activity-hat-bar.html'


class ParticipantsBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('activities', 'participants')
    verbose_name = _('Participants')

    # NB: Organisation is a hack in order to reload the SubjectsBlock when
    #     auto-subjects (see SETTING_AUTO_ORGA_SUBJECTS) is enabled.
    dependencies = (Relation, Contact, Calendar, Organisation)
    relation_type_deps = (constants.REL_OBJ_PART_2_ACTIVITY,)

    template_name = 'activities/bricks/participants.html'
    order_by = 'id'  # For consistent ordering between 2 queries (for pages)

    target_ctypes = (Activity, )
    permissions = 'activities'

    def detailview_display(self, context):
        activity = context['object']
        btc = self.get_template_context(
            context,
            activity.relations.filter(type=constants.REL_OBJ_PART_2_ACTIVITY)
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
    id = QuerysetBrick.generate_id('activities', 'subjects')
    verbose_name = _('Subjects')

    dependencies = (Relation, Organisation)  # See ParticipantsBlock.dependencies
    relation_type_deps = (constants.REL_OBJ_ACTIVITY_SUBJECT,)

    template_name = 'activities/bricks/subjects.html'
    order_by = 'id'  # For consistent ordering between 2 queries (for pages)

    target_ctypes = (Activity, )
    permissions = 'activities'

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            context['object'].relations
                             .filter(type=constants.REL_OBJ_ACTIVITY_SUBJECT)
                             .prefetch_related('real_object'),
        ))


class _RelatedActivitiesBrick(QuerysetBrick):
    dependencies = (Relation, Activity)
    relation_type_deps = (
        constants.REL_SUB_LINKED_2_ACTIVITY,
        constants.REL_SUB_ACTIVITY_SUBJECT,
        constants.REL_SUB_PART_2_ACTIVITY,
    )
    permissions = 'activities'

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
            self._get_queryset_for_entity(context['object'], context)
                .select_related('status', 'type'),
            rtype_id=constants.REL_SUB_LINKED_2_ACTIVITY,
        ))

    def home_display(self, context):
        return self._render(self.get_template_context(
            context,
            self._get_queryset_for_entity(context['user'].linked_contact, context)
                .select_related('status', 'type'),
            is_home=True,
        ))


class FutureActivitiesBrick(_RelatedActivitiesBrick):
    id = QuerysetBrick.generate_id('activities', 'future_activities')
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
        now_value = context['today']

        if entity is None:  # NB: staff user
            # TODO: factorise <order_by('start')> when removed in <future_linked*()>
            # TODO: method in manager?
            return Activity.objects.filter(end__gt=now_value).order_by('start')
        elif isinstance(entity, Organisation):
            return Activity.objects.future_linked_to_organisation(orga=entity, today=now_value)
        else:
            return Activity.objects.future_linked(entity=entity, today=now_value)


class PastActivitiesBrick(_RelatedActivitiesBrick):
    id = QuerysetBrick.generate_id('activities', 'past_activities')
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
        now_value = context['today']

        if entity is None:  # NB: staff user
            # TODO: method in manager?
            return Activity.objects.filter(end__lte=now_value)
        elif isinstance(entity, Organisation):
            return Activity.objects.past_linked_to_organisation(orga=entity, today=now_value)
        else:
            return Activity.objects.past_linked(entity=entity, today=now_value)


class CalendarsBrick(GenericModelBrick):
    id = QuerysetBrick.generate_id('activities', 'calendars_config')
    dependencies = (Calendar,)
    template_name = 'activities/bricks/calendars.html'
    # permissions = 'activities.can_admin' => useless because views check that.

    def detailview_display(self, context):
        qs = get_user_model().objects.all()

        if not context['user'].is_staff:
            qs = qs.exclude(is_staff=True)

        return self._render(self.get_template_context(
            context,
            qs.prefetch_related('calendar_set'),
            model_config=self.model_config,
            calendars_count=Calendar.objects.count(),
        ))


class UserCalendarsBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('activities', 'user_calendars')
    verbose_name = 'My calendars'
    dependencies = (Calendar, )
    template_name = 'activities/bricks/user-calendars.html'
    configurable = False
    permissions = 'activities'
    order_by = 'name'

    def detailview_display(self, context):
        user = context['user']
        # has_app_perm = user.has_perm_to_access('activities')
        #
        # if not has_app_perm:
        #     return ''

        return self._render(self.get_template_context(
            context,
            Calendar.objects.filter(user=user),
            # has_app_perm=has_app_perm,
        ))


class RelatedCalendarBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('activities', 'related_calendar')
    verbose_name = _('On my calendars')
    dependencies = (Calendar, )
    template_name = 'activities/bricks/related-calendars.html'
    order_by = 'name'

    target_ctypes = (Activity, )
    permissions = 'activities'

    def detailview_display(self, context):
        user = context['user']
        activity = context['object']
        return self._render(self.get_template_context(
            context,
            activity.calendars.filter(user=user),
        ))


class CalendarConfigItemsBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('activities', 'calendar_view_config')
    verbose_name = 'Calendar view configuration'
    dependencies = (CalendarConfigItem,)
    template_name = 'activities/bricks/calendar-config.html'
    configurable = False
    # permissions = 'activities.can_admin' => useless because views check that.

    def detailview_display(self, context):
        user = context['user']
        configs = CalendarConfigItem.objects.filter(
            role__isnull=False, superuser=False,
        ).order_by('role__name')

        brick_context = self.get_template_context(
            context,
            configs,
            has_app_perm=user.has_perm('activities'),  # TODO: remove?
        )

        page = brick_context['page']

        try:
            default = CalendarConfigItem.objects.get_default()
        except ConflictError as e:
            brick_context['error'] = e
            return self._render(brick_context)

        if page.number < 2:
            superuser = CalendarConfigItem.objects.filter(role=None, superuser=True).first()

            brick_context['default'] = default
            brick_context['superuser'] = superuser

            # Little hack to force display of default & superuser even without any role
            # configuration
            paginator = page.paginator
            paginator.count += 2 if superuser else 1

        return self._render(brick_context)


class UnsuccessfulButtonConfigBrick(Brick):
    id = Brick.generate_id('activities', 'unsuccessful_call_config')
    verbose_name = _('Configuration of the button «Create an unsuccessful phone call»')
    template_name = 'activities/bricks/unsuccessful-config.html'
    configurable = False
    # permissions = 'activities.can_admin' => useless because views check that.

    def detailview_display(self, context):
        svalues = SettingValue.objects.get_4_keys(
            {'key': setting_keys.unsuccessful_subtype_key},
            {'key': setting_keys.unsuccessful_title_key},
            {'key': setting_keys.unsuccessful_status_key},
            {'key': setting_keys.unsuccessful_duration_key},
        )

        # TODO: factorise (form, view)
        try:
            sub_type = ActivitySubType.objects.get(
                uuid=svalues[setting_keys.unsuccessful_subtype_key.id].value,
            )
        except (ActivitySubType.DoesNotExist, ValidationError):
            sub_type = None

        try:
            status = Status.objects.get(
                uuid=svalues[setting_keys.unsuccessful_status_key.id].value,
            )
        except (Status.DoesNotExist, ValidationError):
            status = None

        return self._render(self.get_template_context(
            context,
            sub_type=sub_type,
            status=status,
            title=svalues[setting_keys.unsuccessful_title_key.id].value,
            duration=svalues[setting_keys.unsuccessful_duration_key.id].value,
        ))
