# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.apps import CremeAppConfig

from . import constants


class ActivitiesConfig(CremeAppConfig):
    default = True
    name = 'creme.activities'
    verbose_name = _('Activities')
    dependencies = ['creme.persons']  # 'creme.assistants' is optional

    def all_apps_ready(self):
        from . import get_activity_model

        self.Activity = get_activity_model()
        super().all_apps_ready()

        from . import signals  # NOQA

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Activity)

    def register_actions(self, actions_registry):
        from creme.activities import actions

        actions_registry.register_bulk_actions(actions.BulkExportICalAction)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            bricks.ParticipantsBrick,
            bricks.SubjectsBrick,
            bricks.FutureActivitiesBrick,
            bricks.PastActivitiesBrick,
            bricks.UserCalendarsBrick,
            bricks.RelatedCalendarBrick,
        ).register_hat(
            self.Activity,
            main_brick_cls=bricks.ActivityBarHatBrick,
        )

    def register_bulk_update(self, bulk_update_registry):
        from .forms.activity_type import BulkEditTypeForm

        bulk_update_registry.register(
            self.Activity,
            exclude=('start', 'end', 'busy', 'is_all_day'),
            innerforms={
                'type':     BulkEditTypeForm,
                'sub_type': BulkEditTypeForm,
            },
        )

    def register_buttons(self, button_registry):
        from . import buttons

        button_registry.register(
            buttons.AddRelatedActivityButton,
            buttons.AddMeetingButton,
            buttons.AddPhoneCallButton,
            buttons.AddTaskButton,
        )

    def register_creme_config(self, config_registry):
        from . import bricks, models
        from .forms import activity_type as type_forms
        from .forms import calendar as cal_forms

        register_model = config_registry.register_model
        register_model(
            models.ActivityType, 'activity_type',
        ).creation(
            form_class=type_forms.ActivityTypeForm,
        ).edition(
            form_class=type_forms.ActivityTypeForm,
        )
        register_model(
            models.ActivitySubType, 'activity_sub_type',
        ).creation(
            form_class=type_forms.ActivitySubTypeForm,
        ).edition(
            form_class=type_forms.ActivitySubTypeForm,
        )
        register_model(models.Status, 'status')
        register_model(
            models.Calendar, 'calendar'
        ).creation(
            form_class=cal_forms.CalendarConfigForm,
        ).edition(
            form_class=cal_forms.CalendarConfigForm,
        ).deletion(
            form_class=cal_forms.CalendarDeletionForm,
        )

        config_registry.register_user_bricks(bricks.UserCalendarsBrick)

    def register_custom_forms(self, cform_registry):
        from . import custom_forms

        cform_registry.register(
            custom_forms.ACTIVITY_CREATION_CFORM,
            custom_forms.ACTIVITY_CREATION_FROM_CALENDAR_CFORM,
            custom_forms.UNAVAILABILITY_CREATION_FROM,
            custom_forms.ACTIVITY_EDITION_CFORM,
        )

    def register_fields_config(self, fields_config_registry):
        fields_config_registry.register_models(self.Activity)

    def register_icons(self, icon_registry):
        Activity = self.Activity
        get_icon = constants.ICONS.get
        icon_registry.register(Activity, 'images/calendar_%(size)s.png') \
                     .register_4_instance(Activity, lambda instance: get_icon(instance.type_id))

    def register_mass_import(self, import_form_registry):
        from .forms import mass_import

        import_form_registry.register(self.Activity, mass_import.get_massimport_form_builder)

    # def register_menu(self, creme_menu):
    #     from django.urls import reverse_lazy as reverse
    #
    #     from creme.creme_core.auth import build_creation_perm
    #
    #     Activity = self.Activity
    #     creation_perm = build_creation_perm(Activity)
    #     URLItem = creme_menu.URLItem
    #     creme_menu.get(
    #         'features',
    #     ).get_or_create(
    #         creme_menu.ContainerItem, 'activities-main',
    #         priority=10,
    #         defaults={'label': _('Activities')},
    #     ).add(
    #         URLItem(
    #             'activities-calendar',
    #             url=reverse('activities__calendar'),
    #             label=_('Calendar'),
    #             perm='activities',
    #         ),
    #         priority=10,
    #     ).add(
    #         URLItem.list_view('activities-activities', model=Activity),
    #         priority=20,
    #     ).add(
    #         URLItem(
    #             'activities-phone_calls',
    #             url=reverse('activities__list_phone_calls'),
    #             label=_('Phone calls'), perm='activities',
    #         ),
    #         priority=30,
    #     ).add(
    #         URLItem(
    #             'activities-meetings',
    #             url=reverse('activities__list_meetings'),
    #             label=_('Meetings'), perm='activities',
    #         ),
    #         priority=40,
    #     )
    #
    #     creme_menu.get(
    #         'creation', 'any_forms'
    #     ).get_or_create_group(
    #         'activities-main', _('Activities'), priority=5,
    #     ).add_link(
    #         'activities-create_phonecall',
    #         label=_('Phone call'),
    #         url=reverse('activities__create_activity', args=('phonecall',)),
    #         perm=creation_perm,
    #         priority=5,
    #     ).add_link(
    #         'activities-create_meeting',
    #         label=_('Meeting'),
    #         url=reverse('activities__create_activity', args=('meeting',)),
    #         perm=creation_perm,
    #         priority=10,
    #     ).add_link(
    #         'activities-create_activity',
    #         label=_('Activity'),
    #         url=reverse('activities__create_activity'),
    #         perm=creation_perm,
    #         priority=15,
    #     ).add_link(
    #         'activities-create_task',
    #         label=_('Task'),
    #         url=reverse('activities__create_activity', args=('task',)),
    #         perm=creation_perm,
    #         priority=20,
    #     ).add_link(
    #         'activities-create_unavailability',
    #         label=_('Unavailability'),
    #         url=reverse('activities__create_indispo'),
    #         perm=creation_perm,
    #         priority=25,
    #     )

    def register_menu_entries(self, menu_registry):
        from . import menu

        menu_registry.register(
            menu.CalendarEntry,

            menu.ActivitiesEntry,
            menu.PhoneCallsEntry,
            menu.MeetingsEntry,

            menu.ActivityCreationEntry,
            menu.PhoneCallCreationEntry,
            menu.MeetingCreationEntry,
        )

    def register_creation_menu(self, creation_menu_registry):
        from django.urls import reverse_lazy as reverse

        from creme.creme_core.auth import build_creation_perm

        creation_perm = build_creation_perm(self.Activity)
        creation_menu_registry.get_or_create_group(
            'activities-main', _('Activities'), priority=5,
        ).add_link(
            'activities-create_phonecall',
            label=_('Phone call'),
            url=reverse('activities__create_activity', args=('phonecall',)),
            perm=creation_perm,
            priority=5,
        ).add_link(
            'activities-create_meeting',
            label=_('Meeting'),
            url=reverse('activities__create_activity', args=('meeting',)),
            perm=creation_perm,
            priority=10,
        ).add_link(
            'activities-create_activity',
            label=_('Activity'),
            url=reverse('activities__create_activity'),
            perm=creation_perm,
            priority=15,
        ).add_link(
            'activities-create_task',
            label=_('Task'),
            url=reverse('activities__create_activity', args=('task',)),
            perm=creation_perm,
            priority=20,
        ).add_link(
            'activities-create_unavailability',
            label=_('Unavailability'),
            url=reverse('activities__create_indispo'),
            perm=creation_perm,
            priority=25,
        )

    def register_smart_columns(self, smart_columns_registry):
        smart_columns_registry.register_model(self.Activity) \
                              .register_field('title') \
                              .register_field('start') \
                              .register_relationtype(constants.REL_OBJ_PART_2_ACTIVITY) \
                              .register_relationtype(constants.REL_OBJ_ACTIVITY_SUBJECT)

    def register_setting_keys(self, setting_key_registry):
        from . import setting_keys

        setting_key_registry.register(
            setting_keys.review_key,
            setting_keys.auto_subjects_key,
            # setting_keys.form_user_messages_key,
        )

    def register_statistics(self, statistics_registry):
        from .statistics import AveragePerMonthStatistics

        statistics_registry.register(
            id='activities',
            label=AveragePerMonthStatistics.label,
            func=AveragePerMonthStatistics(self.Activity),
            perm='activities', priority=30,
        )
