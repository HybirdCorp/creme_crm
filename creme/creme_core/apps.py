# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015  Hybird
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
from sys import argv

from django.apps import AppConfig, apps
from django.core import checks
from django.utils.translation import ugettext_lazy as _

from .checks import Tags, check_uninstalled_apps # it registers other checkings too
from .core.reminder import reminder_registry
from .core.setting_key import setting_key_registry
from .gui import (creme_menu, block_registry, bulk_update_registry, button_registry,
        field_printers_registry, icon_registry, import_form_registry,
        merge_form_registry, quickforms_registry, smart_columns_registry)
from .registry import creme_registry


logger = logging.getLogger(__name__)


class CremeAppConfig(AppConfig):
    dependencies = () # Overload ; eg: ['creme.persons']

    # Lots of problems with ContentType table which can be not created yet.
    MIGRATION_MODE = ('migrate' in argv)

    def ready(self):
        # NB: it seems we cannot transform this a check_deps(self, **kwargs) method
        # because we get an error from django [AttributeError: 'instancemethod' object has no attribute 'tags']
        def check_deps(**kwargs):
            return [checks.Error("depends on the app '%s' which is not installed." % dep,
                                 hint='Check the INSTALLED_CREME_APPS setting in your'
                                      ' local_settings.py/project_settings.py',
                                 obj=self.name,
                                 id='creme.E001',
                                )
                        for dep in self.dependencies
                            if not apps.is_installed(dep)
                   ]

        checks.register(Tags.settings)(check_deps)

        if not self.MIGRATION_MODE:
            self.register_creme_app(creme_registry)
            self.register_entity_models(creme_registry)

            self.register_blocks(block_registry)
            self.register_bulk_update(bulk_update_registry)
            self.register_buttons(button_registry)
            self.register_field_printers(field_printers_registry)
            self.register_icons(icon_registry)
            self.register_mass_import(import_form_registry)
            self.register_menu(creme_menu)
            self.register_merge_forms(merge_form_registry)
            self.register_quickforms(quickforms_registry)
            self.register_reminders(reminder_registry)
            self.register_setting_key(setting_key_registry)
            self.register_smart_columns(smart_columns_registry)

    def register_creme_app(self, creme_registry):
        pass

    def register_entity_models(self, creme_registry):
        pass

    def register_blocks(self, block_registry):
        pass

    def register_bulk_update(self, bulk_update_registry):
        pass

    def register_buttons(self, button_registry):
        pass

    def register_field_printers(self, field_printers_registry):
        pass

    def register_icons(self, icon_registry):
        pass

    def register_mass_import(self, import_form_registry):
        pass

    def register_menu(self, creme_menu):
        pass

    def register_merge_forms(self, merge_form_registry):
        pass

    def register_quickforms(self, quickforms_registry):
        pass

    def register_reminders(self, reminder_registry):
        pass

    def register_setting_key(self, setting_key_registry):
        pass

    def register_smart_columns(self, smart_columns_registry):
        pass


class CremeCoreConfig(CremeAppConfig):
    name = 'creme.creme_core'
    verbose_name = _(u'Core')

    def ready(self):
        super(CremeCoreConfig, self).ready()

        if self.MIGRATION_MODE:
            return

        checks.register(Tags.settings)(check_uninstalled_apps) # Crashes in migrate mode.
        self.hook_fk_formfield()

    def register_creme_app(self, creme_registry):
        creme_registry.register_app('creme_core', _(u'Core'), '/')

    def register_menu(self, creme_menu):
        reg_app = creme_menu.register_app
        reg_app('creme_core', '/',     _(u'Home'),    force_order=0)
        reg_app('my_page', '/my_page', _(u'My page'), force_order=1) # HACK: see creme_core/auth/backend.py

    def register_blocks(self, block_registry):
        from .blocks import (relations_block, properties_block, customfields_block,
                history_block, trash_block)

        block_registry.register(relations_block, properties_block, customfields_block,
                                history_block, trash_block,
                               )

    def register_buttons(self, button_registry):
        from .buttons import merge_entities_button

        button_registry.register(merge_entities_button)

    def register_bulk_update(self, bulk_update_registry):
        from .models import CremeProperty

        bulk_update_registry.register(CremeProperty, exclude=('type', 'creme_entity')) # TODO: tags modifiable=False ??

    def register_setting_key(self, setting_key_registry):
        from .setting_keys import block_opening_key, block_showempty_key, currency_symbol_key

        setting_key_registry.register(block_opening_key, block_showempty_key,
                                      currency_symbol_key,
                                     )

    def hook_fk_formfield(self): # TODO: move to creme_config ??
        from django.db.models import ForeignKey

        from creme.creme_config.forms.fields import CreatorModelChoiceField

        original_fk_formfield = ForeignKey.formfield

        def new_fk_formfield(self, **kwargs):
            defaults = {'form_class': CreatorModelChoiceField}
            defaults.update(kwargs)

            return original_fk_formfield(self, **defaults)

        ForeignKey.formfield = new_fk_formfield
