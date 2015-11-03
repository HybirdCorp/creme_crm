# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from creme.creme_core.apps import CremeAppConfig


class ActivitiesConfig(CremeAppConfig):
    name = 'creme.activities'
    verbose_name = _(u'Activities')
    dependencies = ['creme.persons', 'creme.assistants']

#    def ready(self):
    def all_apps_ready(self):
        from . import get_activity_model

        self.Activity = get_activity_model()
#        super(ActivitiesConfig, self).ready()
        super(ActivitiesConfig, self).all_apps_ready()

        from . import signals

    def register_creme_app(self, creme_registry):
        creme_registry.register_app('activities', _(u'Activities'), '/activities')

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Activity)

    def register_blocks(self, block_registry):
        from .blocks import block_list

        block_registry.register(*block_list)

    def register_bulk_update(self, bulk_update_registry):
        from .forms.activity_type import BulkEditTypeForm

        bulk_update_registry.register(self.Activity,
                                      exclude=('start', 'end', 'busy', 'is_all_day'),
                                      innerforms={'type':     BulkEditTypeForm,
                                                  'sub_type': BulkEditTypeForm,
                                                 },
                                     )

    def register_buttons(self, button_registry):
        from .buttons import (add_activity_button, add_meeting_button,
                add_phonecall_button, add_task_button)

        button_registry.register(add_activity_button, add_meeting_button,
                                 add_phonecall_button, add_task_button,
                                )

    def register_icons(self, icon_registry):
        icon_registry.register(self.Activity, 'images/calendar_%(size)s.png')

    def register_mass_import(self, import_form_registry):
        from .forms.lv_import import get_csv_form_builder

        import_form_registry.register(self.Activity, get_csv_form_builder)

    def register_menu(self, creme_menu):
        from django.core.urlresolvers import reverse_lazy as reverse

        from creme.creme_core.auth import build_creation_perm

        Activity = self.Activity
        creation_perm = build_creation_perm(Activity)
        reg_item = creme_menu.register_app('activities', '/activities/').register_item
        reg_item('/activities/',                                              _(u"Portal of activities"),   'activities')
        reg_item('/activities/calendar/user',                                 _(u'Calendar'),               'activities')
        reg_item(reverse('activities__create_activity'),                      Activity.creation_label,      creation_perm)
        reg_item(reverse('activities__create_activity', args=('meeting',)),   _(u'Add a meeting'),          creation_perm)
        reg_item(reverse('activities__create_activity', args=('phonecall',)), _(u'Add a phone call'),       creation_perm)
        reg_item(reverse('activities__create_activity', args=('task',)),      _(u'Add a task'),             creation_perm)
        reg_item(reverse('activities__create_indispo'),                       _(u'Add an indisponibility'), creation_perm)
        reg_item(reverse('activities__list_activities'),                      _(u'All activities'),         'activities')
        reg_item(reverse('activities__list_phone_calls'),                     _(u'All phone calls'),        'activities')
        reg_item(reverse('activities__list_meetings'),                        _(u'All meetings'),           'activities')

    def register_smart_columns(self, smart_columns_registry):
        from .constants import REL_OBJ_PART_2_ACTIVITY, REL_OBJ_ACTIVITY_SUBJECT

        smart_columns_registry.register_model(self.Activity) \
                              .register_field('title') \
                              .register_field('start') \
                              .register_relationtype(REL_OBJ_PART_2_ACTIVITY) \
                              .register_relationtype(REL_OBJ_ACTIVITY_SUBJECT)

    def register_setting_key(self, setting_key_registry):
        from .setting_keys import review_key, auto_subjects_key

        setting_key_registry.register(review_key, auto_subjects_key)
