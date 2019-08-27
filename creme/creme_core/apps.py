# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2019  Hybird
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
from django.contrib.contenttypes.apps import ContentTypesConfig as VanillaContentTypesConfig
from django.conf import settings
from django.core import checks
from django.utils.translation import gettext_lazy as _

from .checks import Tags, check_uninstalled_apps  # NB: it registers other checks too
from .registry import creme_registry

logger = logging.getLogger(__name__)


# Hooking of AppConfig ------------------

AppConfig.creme_app = False
AppConfig.extended_app = None  # If you extend an app by swapping its models. Eg: 'persons'
AppConfig._extending_app_configs = None


def __get_extending_app_configs(self):
    ext_app_configs = self._extending_app_configs

    if ext_app_configs is None:
        name = self.name
        ext_app_configs = self._extending_app_configs = [
            app_config
                for app_config in apps.get_app_configs()
                    if app_config.extended_app == name
            ]

    return ext_app_configs

AppConfig.get_extending_app_configs = __get_extending_app_configs


# Hooking of AppConfig [end] ------------

# TODO: remove when MediaGenerator is not used
class MediaGeneratorConfig(AppConfig):
    name = 'mediagenerator'
    verbose_name = 'Media generator'  # _('Media generator')

    def ready(self):
        self._build_MEDIA_BUNDLES()
        # self._fix_i18n_filter()

    def _build_MEDIA_BUNDLES(self):
        is_installed = apps.is_installed

        MEDIA_BUNDLES = [
            settings.CREME_I18N_JS,
            [*settings.CREME_LIB_JS,
             *(js for app, js in settings.CREME_OPTLIB_JS if is_installed(app)),
            ],
            [*settings.CREME_CORE_JS,
             *(js for app, js in settings.CREME_OPT_JS if is_installed(app)),
            ],
        ]

        if settings.FORCE_JS_TESTVIEW:
            MEDIA_BUNDLES.append(settings.TEST_CREME_LIB_JS)
            MEDIA_BUNDLES.append(
                [*settings.TEST_CREME_CORE_JS,
                 *(js for app, js in settings.TEST_CREME_OPT_JS if is_installed(app)),
                ]
            )

        MEDIA_BUNDLES += settings.CREME_OPT_MEDIA_BUNDLES

        CREME_CSS = [
            *settings.CREME_CORE_CSS,
            *(css for app, css in settings.CREME_OPT_CSS if is_installed(app)),
        ]
        MEDIA_BUNDLES.extend(
            [theme_dir + CREME_CSS[0],
             *(css_file if isinstance(css_file, dict) else '{}/{}'.format(theme_dir, css_file)
                  for css_file in CREME_CSS[1:]
              ),
            ] for theme_dir, theme_vb_name in settings.THEMES
        )

        settings.CREME_CSS = CREME_CSS  # For compatibility (should not be useful)
        settings.MEDIA_BUNDLES = MEDIA_BUNDLES


class ContentTypesConfig(VanillaContentTypesConfig):
    def ready(self):
        super().ready()

        from django.contrib.contenttypes.models import ContentType
        assert not ContentType._meta.ordering, 'It seems ContentType has an ordering policy now ?!'
        ContentType._meta.ordering = ('id', )


class CremeAppConfig(AppConfig):
    creme_app = True   # True => App can be used by some services
                       #        (urls.py automatically used, 'creme_populate command' etc...)
    dependencies = ()  # Names of the apps on which this app depends ;
                       # an error is raised if the dependencies are not installed.
                       # Eg: ['creme.persons']

    CRED_NONE    = 0b00
    CRED_REGULAR = 0b01
    CRED_ADMIN   = 0b10
    credentials = CRED_REGULAR|CRED_ADMIN

    # Lots of problems with ContentType table which can be not created yet.
    MIGRATION_MODE = any(cmd in argv for cmd in settings.NO_SQL_COMMANDS)  # TODO: rename

    @property
    def url_root(self):
        return self.label + '/'

    def ready(self):
        # NB: it seems we cannot transform this a check_deps(self, **kwargs) method
        # because we get an error from django [AttributeError: 'instancemethod' object has no attribute 'tags']
        @checks.register(Tags.settings)
        def check_deps(**kwargs):
            return [checks.Error("depends on the app '{}' which is not installed.".format(dep),
                                 hint='Check the INSTALLED_CREME_APPS setting in your'
                                      ' local_settings.py/project_settings.py',
                                 obj=self.name,
                                 id='creme.E001',
                                )
                        for dep in self.dependencies
                            if not apps.is_installed(dep)
                   ]

        @checks.register(Tags.settings)
        def check_extended_app(**kwargs):
            errors = []
            app_name = self.extended_app

            if app_name is not None:
                if not apps.is_installed(app_name):
                    errors.append(checks.Error("extends the app '{}' which is not installed.".format(app_name),
                                               hint='Check the INSTALLED_CREME_APPS setting in your'
                                                    ' local_settings.py/project_settings.py',
                                               obj=self.name,
                                               id='creme.E006',
                                              )
                                 )

                if self.credentials != self.CRED_NONE:
                    errors.append(checks.Error("The app '{}' is an extending app & "
                                               "so it cannot have its own credentials.".format(self.name),
                                               hint='Set "credentials = CremeAppConfig.CRED_NONE" in the AppConfig.',
                                               obj=self.name,
                                               id='creme.E007',
                                              )
                                 )

            return errors

    def all_apps_ready(self):
        if not self.MIGRATION_MODE:
            # if hasattr(self, 'register_creme_app'):
            #     logger.critical('The AppConfig for "%s" has a method register_creme_app() which is now useless.', self.name)

            from .core import (entity_filter, enumerable, function_field, imprint,
                    reminder, sandbox, setting_key, sorter)
            from .gui import (actions, bricks, bulk_update, button_menu, fields_config,
                    field_printers, icons, listview, mass_import, menu, merge, quick_forms, statistics)

            self.register_entity_models(creme_registry)

            self.register_actions(actions.actions_registry)
            self.register_bricks(bricks.brick_registry)
            self.register_bulk_update(bulk_update.bulk_update_registry)
            self.register_buttons(button_menu.button_registry)
            self.register_cell_sorters(sorter.cell_sorter_registry)
            self.register_entity_filter(entity_filter.entity_filter_registry)
            self.register_enumerable(enumerable.enumerable_registry)
            self.register_fields_config(fields_config.fields_config_registry)
            self.register_field_printers(field_printers.field_printers_registry)
            self.register_function_fields(function_field.function_field_registry)
            self.register_icons(icons.icon_registry)
            self.register_imprints(imprint.imprint_manager)
            self.register_mass_import(mass_import.import_form_registry)
            self.register_menu(menu.creme_menu)
            self.register_merge_forms(merge.merge_form_registry)
            self.register_quickforms(quick_forms.quickforms_registry)
            self.register_reminders(reminder.reminder_registry)
            self.register_sanboxes(sandbox.sandbox_type_registry)
            self.register_search_fields(listview.search_field_registry)
            self.register_setting_keys(setting_key.setting_key_registry)
            self.register_statistics(statistics.statistics_registry)
            self.register_smart_columns(listview.smart_columns_registry)
            self.register_user_setting_keys(setting_key.user_setting_key_registry)

    def register_entity_models(self, creme_registry):
        pass

    def register_actions(self, actions_registry):
        pass

    def register_bricks(self, brick_registry):
        pass

    def register_bulk_update(self, bulk_update_registry):
        pass

    def register_buttons(self, button_registry):
        pass

    def register_cell_sorters(self, cell_sorter_registry):
        pass

    def register_entity_filter(self, entity_filter_registry):
        pass

    def register_enumerable(self, enumerable_registry):
        pass

    def register_fields_config(self, fields_config_registry):
        pass

    def register_field_printers(self, field_printers_registry):
        pass

    def register_function_fields(self, function_field_registry):
        pass

    def register_icons(self, icon_registry):
        pass

    def register_imprints(self, imprint_manager):
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

    def register_sanboxes(self, sandbox_type_registry):
        pass

    def register_search_fields(self, search_field_registry):
        pass

    def register_setting_keys(self, setting_key_registry):
        pass

    def register_smart_columns(self, smart_columns_registry):
        pass

    def register_statistics(self, statistics_registry):
        pass

    def register_user_setting_keys(self, user_setting_key_registry):
        pass


class CremeCoreConfig(CremeAppConfig):
    name = 'creme.creme_core'
    verbose_name = _('Core')

    @property
    def url_root(self):
        return ''  # We want to catch some URLs which do not start by 'creme_core/'

    def ready(self):
        super().ready()

        if self.MIGRATION_MODE:
            return

        checks.register(Tags.settings)(check_uninstalled_apps)  # Crashes in migrate mode.

    def all_apps_ready(self):
        if self.MIGRATION_MODE:
            return

        self.tag_ctype()

        self.hook_fk_formfield()
        self.hook_fk_check()
        self.hook_m2m_formfield()
        self.hook_datetime_widgets()
        self.hook_multiselection_widgets()

        if settings.TESTS_ON:
            from .tests.fake_apps import ready
            ready()

        super().all_apps_ready()

    def register_menu(self, creme_menu):
        from django.urls import reverse_lazy as reverse

        from .gui.menu import (ItemGroup, ContainerItem, URLItem, TrashItem, LastViewedEntitiesItem,
                QuickCreationItemGroup, CreationFormsItem)
        from .gui.quick_forms import quickforms_registry

        creme_menu.add(ContainerItem('creme', label='Creme')
                          .add(URLItem('home', url=reverse('creme_core__home'), label=_('Home')), priority=10)
                          .add(TrashItem('trash'), priority=20)  # TODO: icon ?
                          .add(ItemGroup('user', label=_('User'))
                                  .add(URLItem('my_page', url=reverse('creme_core__my_page'), label=_('My page')),
                                       priority=10,
                                      )
                                  .add(URLItem('my_jobs', url=reverse('creme_core__my_jobs'), label=_('My jobs')),
                                       priority=20,
                                      ),
                               priority=30,
                              )
                          .add(URLItem('logout', url=reverse('creme_logout'), label=_('Log out')), priority=40),
                       priority=10,
                      ) \
                  .add(ItemGroup('features')
                            .add(ContainerItem('tools', label=_('Tools'))
                                    .add(URLItem('creme_core-jobs', url=reverse('creme_core__jobs'),
                                                 label=_('Jobs'), perm=lambda user: user.is_superuser  # TODO: '*superuser*'' ?
                                                ),
                                         priority=5,
                                        ),
                                 priority=100,
                                ),
                       priority=20,
                      ) \
                  .add(ContainerItem('creation', label=_('+ Creation'))
                           .add(ItemGroup('main_entities', label=_('Main entities')), priority=10)
                           .add(QuickCreationItemGroup('quick_forms', registry=quickforms_registry), priority=20)
                           .add(CreationFormsItem('any_forms', label=_('Other type of entity')), priority=30),
                       priority=30,
                      ) \
                  .add(LastViewedEntitiesItem('recent_entities', label=_('Recent entities')), priority=40)

    def register_actions(self, actions_registry):
        from . import actions

        actions_registry.register_instance_actions(
            actions.EditAction,
            actions.CloneAction,
            actions.DeleteAction,
            actions.ViewAction,
        )
        actions_registry.register_bulk_actions(
            actions.BulkEditAction,
            actions.BulkDeleteAction,
            actions.BulkAddPropertyAction,
            actions.BulkAddRelationAction,
            actions.MergeAction,
       )

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            bricks.PropertiesBrick,
            bricks.RelationsBrick,
            bricks.CustomFieldsBrick,
            bricks.HistoryBrick,
            bricks.ImprintsBrick,
            bricks.TrashBrick,
            bricks.StatisticsBrick,
            bricks.JobBrick,
            bricks.JobsBrick,
            bricks.MyJobsBrick,
        )

    def register_bulk_update(self, bulk_update_registry):
        from .models import CremeProperty

        bulk_update_registry.register(CremeProperty, exclude=('type', 'creme_entity'))  # TODO: tags modifiable=False ??

    def register_buttons(self, button_registry):
        from . import buttons

        button_registry.register(buttons.Restrict2SuperusersButton)

    def register_entity_filter(self, entity_filter_registry):
        from .core.entity_filter import condition_handler, operands

        entity_filter_registry.register_condition_handlers(
            condition_handler.SubFilterConditionHandler,
            condition_handler.RegularFieldConditionHandler,
            condition_handler.DateRegularFieldConditionHandler,
            condition_handler.CustomFieldConditionHandler,
            condition_handler.DateCustomFieldConditionHandler,
            condition_handler.RelationConditionHandler,
            condition_handler.RelationSubFilterConditionHandler,
            condition_handler.PropertyConditionHandler,
        ).register_operands(
            operands.CurrentUserOperand,
        )

    def register_enumerable(self, enumerable_registry):
        from . import enumerators, models

        enumerable_registry.register_related_model(models.EntityFilter,
                                                   enumerators.EntityFilterEnumerator,
                                                  )
        # TODO: register_related_model(models.HeaderFilter, ...) ?
        enumerable_registry.register_field_type(models.fields.EntityCTypeForeignKey,
                                                enumerators.EntityCTypeForeignKeyEnumerator,
                                               )

    def register_function_fields(self, function_field_registry):
        from .function_fields import PropertiesField
        from .models.entity import CremeEntity

        function_field_registry.register(CremeEntity, PropertiesField)

    def register_creme_config(self, config_registry):
        from . import models

        register_model = config_registry.register_model
        register_model(models.Language, 'language')
        register_model(models.Currency, 'currency')
        register_model(models.Vat,      'vat_value')

        if settings.TESTS_ON:
            from .tests import fake_models, fake_bricks

            # NB: see creme.creme_config.tests.test_generics_views.GenericModelConfigTestCase
            register_model(fake_models.FakeDocumentCategory, 'fake_documentcat')
            register_model(fake_models.FakeCivility,         'fake_civility')
            register_model(fake_models.FakeSector,           'fake_sector')
            register_model(fake_models.FakeProductType,      'fake_product_type')
            register_model(fake_models.FakeActivityType,     'fake_activity_type')
            register_model(fake_models.FakeTicketStatus,     'fake_ticket_status')
            register_model(fake_models.FakeTicketPriority,   'fake_ticket_priority')
            register_model(fake_models.FakeIngredient,       'fake_ingredient')

            # NB: we just need another URLs for creation/edition/deletion (even if these ones are stupid)
            register_model(fake_models.FakePosition, 'fake_position') \
                          .creation(enable_func=lambda user: False) \
                          .edition(url_name='creme_core__edit_fake_contact')
            register_model(fake_models.FakeLegalForm, 'fake_legalform') \
                          .creation(url_name='creme_core__create_fake_contact') \
                          .edition(enable_func=lambda instance, user: False)
            register_model(fake_models.FakeFolderCategory, 'fake_foldercat') \
                          .deletion(enable_func=lambda instance, user: False)
            register_model(fake_models.FakeImageCategory, 'fake_img_cat') \
                          .deletion(url_name='creme_core__edit_fake_organisation')

            config_registry.register_app_bricks('creme_core', fake_bricks.FakeAppPortalBrick)

    def register_sanboxes(self, sandbox_type_registry):
        from . import sandboxes

        sandbox_type_registry.register(sandboxes.OnlySuperusersType)

    def register_setting_keys(self, setting_key_registry):
        from . import setting_keys

        setting_key_registry.register(
            setting_keys.block_opening_key,
            setting_keys.block_showempty_key,
            setting_keys.currency_symbol_key,
        )

    # TODO: better API + move some code to creme_config ??
    @staticmethod
    def hook_fk_formfield():
        from django.db.models import ForeignKey

        from .forms.fields import CreatorEntityField
        from .models import CremeEntity

        from creme.creme_config.forms.fields import CreatorModelChoiceField

        original_fk_formfield = ForeignKey.formfield

        def new_fk_formfield(self, **kwargs):
            model = self.remote_field.model
            if issubclass(model, CremeEntity):
                return CreatorEntityField(label=self.verbose_name,
                                          model=model,
                                          required=not self.blank,
                                          q_filter=self.remote_field.limit_choices_to,
                                         )

            return original_fk_formfield(
                self, **{'form_class': CreatorModelChoiceField, **kwargs}
            )

        ForeignKey.formfield = new_fk_formfield

    @staticmethod
    def hook_fk_check():
        from django.db.models import ForeignKey

        from creme.creme_core.models.deletion import CREME_REPLACE_NULL

        original_fk_check = ForeignKey.check

        def new_fk_check(self, **kwargs):
            errors = original_fk_check(self, **kwargs)
            on_delete = getattr(self.remote_field, 'on_delete', None)

            if on_delete == CREME_REPLACE_NULL and not self.null:
                errors.append(
                    checks.Error(
                        'Field specifies on_delete=CREME_REPLACE_NULL, but cannot be null.',
                        hint='Set null=True argument on the field, or change the on_delete rule.',
                        obj=self,
                        id='creme.E009',
                    )
                )

            return errors

        ForeignKey.check = new_fk_check

    # TODO: see hook_fk_formfield()
    @staticmethod
    def hook_m2m_formfield():
        from django.db.models import ManyToManyField

        from .forms.fields import MultiCreatorEntityField
        from .models import CremeEntity

        from creme.creme_config.forms.fields import CreatorModelMultipleChoiceField

        original_m2m_formfield = ManyToManyField.formfield

        def new_m2m_formfield(self, **kwargs):
            model = self.remote_field.model

            if issubclass(model, CremeEntity):
                return MultiCreatorEntityField(label=self.verbose_name,
                                               model=model,
                                               required=not self.blank,
                                               q_filter=self.remote_field.limit_choices_to,
                                              )

            return original_m2m_formfield(
                self, **{'form_class': CreatorModelMultipleChoiceField, **kwargs})

        ManyToManyField.formfield = new_m2m_formfield

    @staticmethod
    def hook_datetime_widgets():
        from django import forms

        from creme.creme_core.forms import widgets

        forms.DateField.widget     = widgets.CalendarWidget
        forms.DateTimeField.widget = widgets.DateTimeWidget
        forms.TimeField.widget     = widgets.TimeWidget

    @staticmethod
    def hook_multiselection_widgets():
        from django import forms

        from creme.creme_core.forms import widgets

        forms.MultipleChoiceField.widget = forms.ModelMultipleChoiceField.widget = \
             widgets.UnorderedMultipleChoiceWidget

    @staticmethod
    def tag_ctype():
        from django.contrib.contenttypes.models import ContentType

        get_ct_field = ContentType._meta.get_field

        for fname in ('app_label', 'model'):
            get_ct_field(fname).set_tags(viewable=False)


def creme_app_configs():
    for app_config in apps.get_app_configs():
        if app_config.creme_app:
            yield app_config


def extended_app_configs(app_labels):
    """Get the AppConfigs corresponding to given labels, & their extending AppConfigs.
    @param app_labels: Iterable of app labels (eg: ['persons', documents']).
    @return: Set of AppConfig instances.
    """
    get_app_config = apps.get_app_config
    app_configs = set()

    for label in app_labels:
        try:
            app_config = get_app_config(label)
        except LookupError:
            logger.warning('The app "%s" seems not installed.', label)
        else:
            app_configs.add(app_config)
            app_configs.update(app_config.get_extending_app_configs())

    return app_configs
