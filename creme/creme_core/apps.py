# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2021  Hybird
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
from typing import TYPE_CHECKING, Sequence

from django.apps import AppConfig, apps
from django.conf import settings
from django.contrib.contenttypes.apps import (
    ContentTypesConfig as VanillaContentTypesConfig,
)
from django.core import checks
from django.utils.translation import gettext_lazy as _

from .checks import (  # NB: it registers other checks too
    Tags,
    check_uninstalled_apps,
)
from .registry import CremeRegistry, creme_registry

if TYPE_CHECKING:
    from .core.download import FileFieldDownLoadRegistry
    from .core.entity_filter import _EntityFilterRegistry
    from .core.enumerable import _EnumerableRegistry
    from .core.function_field import _FunctionFieldRegistry
    from .core.imprint import _ImprintManager
    from .core.reminder import ReminderRegistry
    from .core.sandbox import _SandboxTypeRegistry
    from .core.setting_key import _SettingKeyRegistry
    from .core.sorter import CellSorterRegistry
    from .gui.actions import ActionsRegistry
    from .gui.bricks import _BrickRegistry
    from .gui.bulk_update import _BulkUpdateRegistry
    from .gui.button_menu import ButtonsRegistry
    from .gui.custom_form import CustomFormDescriptorRegistry
    from .gui.field_printers import _FieldPrintersRegistry
    from .gui.fields_config import FieldsConfigRegistry
    from .gui.icons import IconRegistry
    from .gui.listview.search import ListViewSearchFieldRegistry
    from .gui.listview.smart_columns import SmartColumnsRegistry
    from .gui.mass_import import FormRegistry  # TODO: rename ?
    # from .gui.menu import Menu
    from .gui.menu import CreationMenuRegistry, MenuRegistry
    from .gui.merge import _MergeFormRegistry
    from .gui.quick_forms import QuickFormsRegistry
    from .gui.statistics import _StatisticsRegistry

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

    def _build_MEDIA_BUNDLES(self):
        is_installed = apps.is_installed

        MEDIA_BUNDLES = [
            settings.CREME_I18N_JS,
            [
                *settings.CREME_LIB_JS,
                *(js for app, js in settings.CREME_OPTLIB_JS if is_installed(app)),
            ],
            [
                *settings.CREME_CORE_JS,
                *(js for app, js in settings.CREME_OPT_JS if is_installed(app)),
            ],
        ]

        if settings.FORCE_JS_TESTVIEW:
            MEDIA_BUNDLES.append(settings.TEST_CREME_LIB_JS)
            MEDIA_BUNDLES.append([
                *settings.TEST_CREME_CORE_JS,
                *(js for app, js in settings.TEST_CREME_OPT_JS if is_installed(app)),
            ])

        MEDIA_BUNDLES += settings.CREME_OPT_MEDIA_BUNDLES

        CREME_CSS = [
            *settings.CREME_CORE_CSS,
            *(css for app, css in settings.CREME_OPT_CSS if is_installed(app)),
        ]
        MEDIA_BUNDLES.extend(
            [
                theme_dir + CREME_CSS[0],
                *(
                    css_file if isinstance(css_file, dict) else f'{theme_dir}/{css_file}'
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

        meta = ContentType._meta
        assert not meta.ordering, 'It seems ContentType has an ordering policy now ?!'

        # meta.ordering = ('id', )
        meta.ordering = ['id']

        get_ct_field = meta.get_field
        for fname in ('app_label', 'model'):
            get_ct_field(fname).set_tags(viewable=False)

        # NB: the original prefix with app's name => ugly choices for final users
        #     => use gettext+context had smooth translation instead
        ContentType.__str__ = lambda this: this.name


class CremeAppConfig(AppConfig):
    # True => App can be used by some services
    #        (urls.py automatically used, 'creme_populate command' etc...)
    creme_app: bool = True

    # Names of the apps on which this app depends ;
    # an error is raised if the dependencies are not installed.
    # Eg: ['creme.persons']
    dependencies: Sequence[str] = ()

    CRED_NONE    = 0b00
    CRED_REGULAR = 0b01
    CRED_ADMIN   = 0b10
    credentials = CRED_REGULAR | CRED_ADMIN

    # Lots of problems with ContentType table which can be not created yet.
    MIGRATION_MODE = any(cmd in argv for cmd in settings.NO_SQL_COMMANDS)  # TODO: rename

    @property
    def url_root(self):
        return self.label + '/'

    def ready(self):
        # NB: it seems we cannot transform this a check_deps(self, **kwargs) method
        # because we get an error from django:
        # [AttributeError: 'instancemethod' object has no attribute 'tags']
        @checks.register(Tags.settings)
        def check_deps(**kwargs):
            return [
                checks.Error(
                    f"depends on the app '{dep}' which is not installed.",
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
                    errors.append(checks.Error(
                        f"extends the app '{app_name}' which is not installed.",
                        hint='Check the INSTALLED_CREME_APPS setting in your'
                             ' local_settings.py/project_settings.py',
                        obj=self.name,
                        id='creme.E006',
                    ))

                if self.credentials != self.CRED_NONE:
                    errors.append(checks.Error(
                        f"The app '{self.name}' is an extending app & "
                        f"so it cannot have its own credentials.",
                        hint='Set "credentials = CremeAppConfig.CRED_NONE" in the AppConfig.',
                        obj=self.name,
                        id='creme.E007',
                    ))

            return errors

    def all_apps_ready(self):
        if not self.MIGRATION_MODE:
            from .core import (
                download,
                entity_filter,
                enumerable,
                function_field,
                imprint,
                reminder,
                sandbox,
                setting_key,
                sorter,
            )
            from .gui import (
                actions,
                bricks,
                bulk_update,
                button_menu,
                custom_form,
                field_printers,
                fields_config,
                icons,
                listview,
                mass_import,
                menu,
                merge,
                quick_forms,
                statistics,
            )

            self.register_entity_models(creme_registry)

            self.register_actions(actions.actions_registry)
            self.register_bricks(bricks.brick_registry)
            self.register_bulk_update(bulk_update.bulk_update_registry)
            self.register_buttons(button_menu.button_registry)
            self.register_cell_sorters(sorter.cell_sorter_registry)
            self.register_credentials(
                entity_filter.entity_filter_registries[entity_filter.EF_CREDENTIALS]
            )
            self.register_entity_filter(
                entity_filter.entity_filter_registries[entity_filter.EF_USER]
            )
            self.register_custom_forms(custom_form.customform_descriptor_registry)
            self.register_enumerable(enumerable.enumerable_registry)
            self.register_fields_config(fields_config.fields_config_registry)
            self.register_field_printers(field_printers.field_printers_registry)
            self.register_filefields_download(download.filefield_download_registry)
            self.register_function_fields(function_field.function_field_registry)
            self.register_icons(icons.icon_registry)
            self.register_imprints(imprint.imprint_manager)
            self.register_mass_import(mass_import.import_form_registry)
            # self.register_menu(menu.creme_menu)
            self.register_menu_entries(menu.menu_registry)
            self.register_creation_menu(menu.creation_menu_registry)
            self.register_merge_forms(merge.merge_form_registry)
            self.register_quickforms(quick_forms.quickforms_registry)
            self.register_reminders(reminder.reminder_registry)
            self.register_sanboxes(sandbox.sandbox_type_registry)
            self.register_search_fields(listview.search_field_registry)
            self.register_setting_keys(setting_key.setting_key_registry)
            self.register_statistics(statistics.statistics_registry)
            self.register_smart_columns(listview.smart_columns_registry)
            self.register_user_setting_keys(setting_key.user_setting_key_registry)

    def register_entity_models(self, creme_registry: CremeRegistry) -> None:
        pass

    def register_actions(self, actions_registry: 'ActionsRegistry') -> None:
        pass

    def register_bricks(self, brick_registry: '_BrickRegistry') -> None:
        pass

    def register_bulk_update(self, bulk_update_registry: '_BulkUpdateRegistry') -> None:
        pass

    def register_buttons(self, button_registry: 'ButtonsRegistry') -> None:
        pass

    def register_cell_sorters(self, cell_sorter_registry: 'CellSorterRegistry') -> None:
        pass

    def register_credentials(self, entity_filter_registry: '_EntityFilterRegistry') -> None:
        pass

    def register_entity_filter(self, entity_filter_registry: '_EntityFilterRegistry') -> None:
        pass

    def register_custom_forms(self, cform_registry: 'CustomFormDescriptorRegistry') -> None:
        pass

    def register_enumerable(self, enumerable_registry: '_EnumerableRegistry') -> None:
        pass

    def register_fields_config(self, fields_config_registry: 'FieldsConfigRegistry') -> None:
        pass

    def register_field_printers(self, field_printers_registry: '_FieldPrintersRegistry') -> None:
        pass

    def register_filefields_download(
            self,
            filefield_download_registry: 'FileFieldDownLoadRegistry') -> None:
        pass

    def register_function_fields(self, function_field_registry: '_FunctionFieldRegistry') -> None:
        pass

    def register_icons(self, icon_registry: 'IconRegistry') -> None:
        pass

    def register_imprints(self, imprint_manager: '_ImprintManager') -> None:
        pass

    def register_mass_import(self, import_form_registry: 'FormRegistry') -> None:
        pass

    # def register_menu(self, creme_menu: 'Menu') -> None:
    #     pass

    def register_menu_entries(self, menu_registry: 'MenuRegistry') -> None:
        pass

    def register_creation_menu(self, creation_menu_registry: 'CreationMenuRegistry') -> None:
        pass

    def register_merge_forms(self, merge_form_registry: '_MergeFormRegistry') -> None:
        pass

    def register_quickforms(self, quickforms_registry: 'QuickFormsRegistry') -> None:
        pass

    def register_reminders(self, reminder_registry: 'ReminderRegistry') -> None:
        pass

    def register_sanboxes(self, sandbox_type_registry: '_SandboxTypeRegistry') -> None:
        pass

    def register_search_fields(self, search_field_registry: 'ListViewSearchFieldRegistry') -> None:
        pass

    def register_setting_keys(self, setting_key_registry: '_SettingKeyRegistry') -> None:
        pass

    def register_smart_columns(self, smart_columns_registry: 'SmartColumnsRegistry') -> None:
        pass

    def register_statistics(self, statistics_registry: '_StatisticsRegistry') -> None:
        pass

    def register_user_setting_keys(self, user_setting_key_registry: '_SettingKeyRegistry') -> None:
        pass


class CremeCoreConfig(CremeAppConfig):
    default = True
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

        # self.tag_ctype()

        self.hook_fk_formfield()
        self.hook_fk_check()
        self.hook_m2m_formfield()
        self.hook_textfield_formfield()
        self.hook_datetime_widgets()
        self.hook_multiselection_widgets()
        self.hook_select_template()

        if settings.TESTS_ON:
            from .tests.fake_apps import ready
            ready()

        super().all_apps_ready()

    # def register_menu(self, creme_menu):
    #     from django.urls import reverse_lazy as reverse
    #
    #     from .auth import SUPERUSER_PERM
    #     from .gui.menu import (
    #         ContainerItem,
    #         CreationFormsItem,
    #         ItemGroup,
    #         LastViewedEntitiesItem,
    #         QuickCreationItemGroup,
    #         TrashItem,
    #         URLItem,
    #     )
    #     from .gui.quick_forms import quickforms_registry
    #
    #     creme_menu.add(
    #         ContainerItem(
    #             'creme', label='Creme',
    #         ).add(
    #             URLItem('home', url=reverse('creme_core__home'), label=_('Home')), priority=10,
    #         ).add(
    #             TrashItem('trash'), priority=20,  # TODO: icon ?
    #         ).add(
    #             ItemGroup(
    #                 'user', label=_('User'),
    #             ).add(
    #                 URLItem('my_page', url=reverse('creme_core__my_page'), label=_('My page')),
    #                 priority=10,
    #             ).add(
    #                 URLItem('my_jobs', url=reverse('creme_core__my_jobs'), label=_('My jobs')),
    #                 priority=20,
    #             ),
    #             priority=30,
    #         ).add(
    #             URLItem('logout', url=reverse('creme_logout'), label=_('Log out')), priority=40,
    #         ),
    #         priority=10,
    #     ).add(
    #         ItemGroup(
    #             'features',
    #         ).add(
    #             ContainerItem(
    #                 'tools', label=_('Tools'),
    #             ).add(
    #                 URLItem(
    #                     'creme_core-jobs', url=reverse('creme_core__jobs'),
    #                     label=_('Jobs'), perm=SUPERUSER_PERM,
    #                 ),
    #                 priority=5,
    #             ),
    #             priority=100,
    #         ),
    #         priority=20,
    #     ).add(
    #         ContainerItem(
    #             'creation', label=_('+ Creation'),
    #         ).add(
    #             ItemGroup('main_entities', label=_('Main entities')),
    #             priority=10,
    #         ).add(
    #             QuickCreationItemGroup('quick_forms', registry=quickforms_registry),
    #             priority=20,
    #         ).add(
    #             CreationFormsItem('any_forms', label=_('Other type of entity')),
    #             priority=30,
    #         ),
    #         priority=30,
    #     ).add(
    #         LastViewedEntitiesItem('recent_entities', label=_('Recent entities')),
    #         priority=40,
    #     )

    def register_menu_entries(self, menu_registry):
        from . import menu

        menu_registry.register(
            menu.CremeEntry,
            menu.RecentEntitiesEntry,
            menu.JobsEntry,
            menu.QuickFormsEntries,
            menu.EntitiesCreationEntry,
        )

    def register_actions(self, actions_registry):
        from . import actions

        actions_registry.register_instance_actions(
            actions.EditAction,
            actions.CloneAction,
            actions.DeleteAction,
            actions.ViewAction,
        ).register_bulk_actions(
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

        # TODO: tags modifiable=False ??
        bulk_update_registry.register(CremeProperty, exclude=('type', 'creme_entity'))

    def register_buttons(self, button_registry):
        from . import buttons

        button_registry.register(buttons.Restrict2SuperusersButton)

    def register_credentials(self, entity_filter_registry):
        from .core.entity_filter import condition_handler, operands, operators

        # BEWARE: other handler classes are not complete for credentials
        # (accept() methods to be done)
        entity_filter_registry.register_condition_handlers(
            condition_handler.RegularFieldConditionHandler,
            condition_handler.CustomFieldConditionHandler,
            condition_handler.RelationConditionHandler,
            condition_handler.PropertyConditionHandler,
        ).register_operators(
            *operators.all_operators,
        ).register_operands(
            *operands.all_operands,
        )

    def register_entity_filter(self, entity_filter_registry):
        from .core.entity_filter import condition_handler, operands, operators

        entity_filter_registry.register_condition_handlers(
            *condition_handler.all_handlers,
        ).register_operators(
            *operators.all_operators,
        ).register_operands(
            *operands.all_operands,
        )

    def register_enumerable(self, enumerable_registry):
        from django.contrib.auth import get_user_model

        from . import enumerators, models

        enumerable_registry.register_related_model(
            get_user_model(),
            enumerators.UserEnumerator,
        ).register_related_model(
            models.EntityFilter,
            enumerators.EntityFilterEnumerator,
        ).register_field_type(
            models.fields.EntityCTypeForeignKey,
            enumerators.EntityCTypeForeignKeyEnumerator,
        )
        # TODO: register_related_model(models.HeaderFilter, ...) ?

    def register_function_fields(self, function_field_registry):
        from .function_fields import PropertiesField
        from .models.entity import CremeEntity

        function_field_registry.register(CremeEntity, PropertiesField)

    def register_filefields_download(self, filefield_download_registry):
        from .models import FileRef

        filefield_download_registry.register(
            model=FileRef,
            field_name='filedata',
            basename_builder=(lambda instance, field, file_obj: instance.basename),
        )

    def register_creme_config(self, config_registry):
        from . import models

        register_model = config_registry.register_model
        register_model(models.Language, 'language')
        register_model(models.Currency, 'currency')
        register_model(models.Vat,      'vat_value')

        if settings.TESTS_ON:
            from .tests import fake_bricks, fake_models

            # NB: see creme.creme_config.tests.test_generics_views.GenericModelConfigTestCase
            register_model(fake_models.FakeDocumentCategory, 'fake_documentcat')
            register_model(fake_models.FakeCivility,         'fake_civility')
            register_model(fake_models.FakeSector,           'fake_sector')
            register_model(fake_models.FakeProductType,      'fake_product_type')
            register_model(fake_models.FakeActivityType,     'fake_activity_type')
            register_model(fake_models.FakeTicketStatus,     'fake_ticket_status')
            register_model(fake_models.FakeTicketPriority,   'fake_ticket_priority')
            register_model(fake_models.FakeIngredient,       'fake_ingredient')

            # NB: we just need another URLs for creation/edition/deletion
            # (even if these ones are stupid)
            register_model(
                fake_models.FakePosition, 'fake_position',
            ).creation(
                enable_func=lambda user: False,
            ).edition(url_name='creme_core__edit_fake_contact')
            register_model(
                fake_models.FakeLegalForm, 'fake_legalform',
            ).creation(
                url_name='creme_core__create_fake_contact',
            ).edition(enable_func=lambda instance, user: False)
            register_model(
                fake_models.FakeFolderCategory, 'fake_foldercat',
            ).deletion(enable_func=lambda instance, user: False)
            register_model(
                fake_models.FakeImageCategory, 'fake_img_cat',
            ).deletion(url_name='creme_core__edit_fake_organisation')

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

        from creme.creme_config.forms.fields import CreatorModelChoiceField

        from .forms.fields import CreatorEntityField, GenericEntityField
        from .models import CremeEntity

        original_fk_formfield = ForeignKey.formfield

        def new_fk_formfield(self, **kwargs):
            remote_field = self.remote_field
            model = remote_field.model
            limit_choices_to = remote_field.limit_choices_to

            if issubclass(model, CremeEntity):
                if model is CremeEntity:
                    if limit_choices_to is not None:
                        logger.warning(
                            'GenericEntityField currently does not manage "q_filter".'
                        )

                    return GenericEntityField(
                        label=self.verbose_name,
                        required=not self.blank,
                    )

                return CreatorEntityField(
                    label=self.verbose_name,
                    model=model,
                    required=not self.blank,
                    q_filter=limit_choices_to,
                    help_text=self.help_text,
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

        from creme.creme_config.forms.fields import (
            CreatorModelMultipleChoiceField,
        )

        from .forms.fields import MultiCreatorEntityField
        from .models import CremeEntity

        original_m2m_formfield = ManyToManyField.formfield

        def new_m2m_formfield(self, **kwargs):
            model = self.remote_field.model

            if issubclass(model, CremeEntity):
                return MultiCreatorEntityField(
                    label=self.verbose_name,
                    model=model,
                    required=not self.blank,
                    q_filter=self.remote_field.limit_choices_to,
                )

            return original_m2m_formfield(
                self, **{'form_class': CreatorModelMultipleChoiceField, **kwargs})

        ManyToManyField.formfield = new_m2m_formfield

    @staticmethod
    def hook_textfield_formfield():
        from django.db.models import TextField

        from creme.creme_core.forms.widgets import CremeTextarea

        # NB: we want CremeTextarea as often as possible, but the widget is
        #     given by TextField.formfield() with Textarea hard-coded,
        #     so we override it.
        def formfield(this, **kwargs):
            return super(TextField, this).formfield(**{
                'max_length': this.max_length,
                **({} if this.choices else {'widget': CremeTextarea}),
                **kwargs,
            })

        TextField.formfield = formfield

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
    def hook_select_template():
        from django.forms.widgets import Select

        Select.template_name = 'creme_core/forms/widgets/select.html'

    # @staticmethod
    # def tag_ctype():
    #     from django.contrib.contenttypes.models import ContentType
    #
    #     get_ct_field = ContentType._meta.get_field
    #
    #     for fname in ('app_label', 'model'):
    #         get_ct_field(fname).set_tags(viewable=False)


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
