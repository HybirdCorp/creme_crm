################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2025  Hybird
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
from collections.abc import Sequence
from sys import argv
from typing import TYPE_CHECKING

from django.apps import AppConfig, apps
from django.conf import settings
from django.contrib.contenttypes.apps import (
    ContentTypesConfig as VanillaContentTypesConfig,
)
from django.core import checks
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.core.field_tags import FieldTag

from .checks import (  # NB: it registers other checks too
    Tags,
    check_uninstalled_apps,
)
from .registry import CremeRegistry, creme_registry

if TYPE_CHECKING:
    from .auth.special import SpecialPermissionRegistry
    from .core.cloning import EntityClonerRegistry
    from .core.deletion import EntityDeletorRegistry
    from .core.download import FileFieldDownLoadRegistry
    from .core.entity_filter import EntityFilterRegistry
    from .core.enumerable import EnumerableRegistry
    from .core.function_field import FunctionFieldRegistry
    from .core.imprint import ImprintManager
    from .core.notification import NotificationRegistry
    from .core.reminder import ReminderRegistry
    from .core.sandbox import SandboxTypeRegistry
    from .core.setting_key import SettingKeyRegistry
    from .core.sorter import CellSorterRegistry
    from .core.workflow import WorkflowRegistry
    from .gui.actions import ActionRegistry
    from .gui.bricks import BrickRegistry
    from .gui.bulk_update import BulkUpdateRegistry
    from .gui.button_menu import ButtonRegistry
    from .gui.custom_form import CustomFormDescriptorRegistry
    from .gui.field_printers import FieldPrinterRegistry
    from .gui.fields_config import FieldsConfigRegistry
    from .gui.icons import IconRegistry
    from .gui.listview.aggregator import ListViewAggregatorRegistry
    from .gui.listview.search import ListViewSearchFieldRegistry
    from .gui.listview.smart_columns import SmartColumnsRegistry
    from .gui.mass_import import FormRegistry  # TODO: rename ?
    from .gui.menu import CreationMenuRegistry, MenuRegistry
    from .gui.merge import _MergeFormRegistry
    from .gui.quick_forms import QuickFormRegistry
    from .gui.statistics import StatisticRegistry

logger = logging.getLogger(__name__)


# Hooking of AppConfig ------------------

AppConfig.creme_app = False
AppConfig.extended_app = None  # If you extend an app by swapping its models. E.g. 'persons'
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
        self.hook_order()
        self.hook_str()
        self.hook_fields()
        self.hook_portable_key()

    def hook_order(self):
        from django.contrib.contenttypes.models import ContentType

        meta = ContentType._meta
        assert not meta.ordering, 'It seems ContentType has an ordering policy now?!'

        meta.ordering = ['id']

    def hook_str(self):
        from django.contrib.contenttypes.models import ContentType

        from .models.utils import model_verbose_name

        def ct_str(this):
            model = this.model_class()
            return this.model if model is None else model_verbose_name(model)

        # NB: the original prefix with app's name => ugly choices for final users
        ContentType.__str__ = ct_str

    def hook_fields(self):
        from django.contrib.contenttypes.models import ContentType

        get_ct_field = ContentType._meta.get_field
        for fname in ('app_label', 'model'):
            get_ct_field(fname).set_tags(viewable=False)

    def hook_portable_key(self):
        from django.contrib.contenttypes import models as ct_models

        def portable_key(this):
            return '.'.join(this.natural_key())

        def get_by_portable_key(this, key):
            app_label, model_name = key.split('.', 2)

            return this.get_by_natural_key(app_label=app_label, model=model_name)

        ct_models.ContentType.portable_key = portable_key
        ct_models.ContentTypeManager.get_by_portable_key = get_by_portable_key


class CremeAppConfig(AppConfig):
    # True => App can be used by some services
    #        (urls.py automatically used, 'creme_populate command' etc...)
    creme_app: bool = True

    # Names of the apps on which this app depends ;
    # an error is raised if the dependencies are not installed.
    # E.g. ['creme.persons']
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
            from .auth.special import special_perm_registry
            from .core import (
                cloning,
                deletion,
                download,
                entity_filter,
                enumerable,
                function_field,
                imprint,
                notification,
                reminder,
                sandbox,
                setting_key,
                sorter,
                workflow,
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

            self.register_permissions(special_perm_registry)

            self.register_actions(actions.action_registry)
            self.register_aggregators(listview.aggregator_registry)
            self.register_bricks(bricks.brick_registry)
            self.register_bulk_update(bulk_update.bulk_update_registry)
            self.register_buttons(button_menu.button_registry)
            self.register_cell_sorters(sorter.cell_sorter_registry)
            self.register_cloners(cloning.entity_cloner_registry)
            self.register_deletors(deletion.entity_deletor_registry)
            self.register_credentials(
                entity_filter.entity_filter_registries[entity_filter.EF_CREDENTIALS]
            )
            self.register_entity_filter(
                entity_filter.entity_filter_registries[entity_filter.EF_REGULAR]
            )
            self.register_custom_forms(custom_form.customform_descriptor_registry)
            self.register_enumerable(enumerable.enumerable_registry)
            self.register_fields_config(fields_config.fields_config_registry)
            self.register_field_printers(field_printers.field_printer_registry)
            self.register_filefields_download(download.filefield_download_registry)
            self.register_function_fields(function_field.function_field_registry)
            self.register_icons(icons.icon_registry)
            self.register_imprints(imprint.imprint_manager)
            self.register_mass_import(mass_import.import_form_registry)
            self.register_menu_entries(menu.menu_registry)
            self.register_creation_menu(menu.creation_menu_registry)
            self.register_merge_forms(merge.merge_form_registry)
            self.register_notification(notification.notification_registry)
            self.register_quickforms(quick_forms.quickform_registry)
            self.register_reminders(reminder.reminder_registry)
            self.register_sandboxes(sandbox.sandbox_type_registry)
            self.register_search_fields(listview.search_field_registry)
            self.register_setting_keys(setting_key.setting_key_registry)
            self.register_statistics(statistics.statistic_registry)
            self.register_smart_columns(listview.smart_columns_registry)
            self.register_user_setting_keys(setting_key.user_setting_key_registry)
            self.register_workflows(workflow.workflow_registry)

    def register_entity_models(self, creme_registry: CremeRegistry) -> None:
        pass

    def register_permissions(self, special_perm_registry: 'SpecialPermissionRegistry') -> None:
        pass

    def register_actions(self, action_registry: 'ActionRegistry') -> None:
        pass

    def register_aggregators(self, aggregator_registry: 'ListViewAggregatorRegistry') -> None:
        pass

    def register_bricks(self, brick_registry: 'BrickRegistry') -> None:
        pass

    def register_bulk_update(self, bulk_update_registry: 'BulkUpdateRegistry') -> None:
        pass

    def register_buttons(self, button_registry: 'ButtonRegistry') -> None:
        pass

    def register_cell_sorters(self, cell_sorter_registry: 'CellSorterRegistry') -> None:
        pass

    def register_cloners(self, entity_cloner_registry: 'EntityClonerRegistry') -> None:
        pass

    def register_deletors(self, entity_deletor_registry: 'EntityDeletorRegistry') -> None:
        pass

    def register_credentials(self, entity_filter_registry: 'EntityFilterRegistry') -> None:
        pass

    def register_entity_filter(self, entity_filter_registry: 'EntityFilterRegistry') -> None:
        pass

    def register_custom_forms(self, cform_registry: 'CustomFormDescriptorRegistry') -> None:
        pass

    def register_enumerable(self, enumerable_registry: 'EnumerableRegistry') -> None:
        pass

    def register_fields_config(self, fields_config_registry: 'FieldsConfigRegistry') -> None:
        pass

    def register_field_printers(self, field_printer_registry: 'FieldPrinterRegistry') -> None:
        pass

    def register_filefields_download(
            self,
            filefield_download_registry: 'FileFieldDownLoadRegistry') -> None:
        pass

    def register_function_fields(self, function_field_registry: 'FunctionFieldRegistry') -> None:
        pass

    def register_icons(self, icon_registry: 'IconRegistry') -> None:
        pass

    def register_imprints(self, imprint_manager: 'ImprintManager') -> None:
        pass

    def register_mass_import(self, import_form_registry: 'FormRegistry') -> None:
        pass

    def register_menu_entries(self, menu_registry: 'MenuRegistry') -> None:
        pass

    def register_creation_menu(self, creation_menu_registry: 'CreationMenuRegistry') -> None:
        pass

    def register_merge_forms(self, merge_form_registry: '_MergeFormRegistry') -> None:
        pass

    def register_notification(self, notification_registry: 'NotificationRegistry') -> None:
        pass

    def register_quickforms(self, quickform_registry: 'QuickFormRegistry') -> None:
        pass

    def register_reminders(self, reminder_registry: 'ReminderRegistry') -> None:
        pass

    def register_sandboxes(self, sandbox_type_registry: 'SandboxTypeRegistry') -> None:
        pass

    def register_search_fields(self, search_field_registry: 'ListViewSearchFieldRegistry') -> None:
        pass

    def register_setting_keys(self, setting_key_registry: 'SettingKeyRegistry') -> None:
        pass

    def register_smart_columns(self, smart_columns_registry: 'SmartColumnsRegistry') -> None:
        pass

    def register_statistics(self, statistic_registry: 'StatisticRegistry') -> None:
        pass

    def register_user_setting_keys(self, user_setting_key_registry: 'SettingKeyRegistry') -> None:
        pass

    def register_workflows(self, workflow_registry: 'WorkflowRegistry') -> None:
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

        self.hook_fk_formfield()
        self.hook_fk_check()
        self.hook_m2m_formfield()
        self.hook_textfield_formfield()
        self.hook_datetime_widgets()
        self.hook_multiselection_widgets()
        self.hook_nullboolean_widget()
        self.hook_typedchoice_widget()

        if settings.TESTS_ON:
            from .tests.fake_apps import ready
            ready()

        super().all_apps_ready()

    def register_menu_entries(self, menu_registry):
        from . import menu

        menu_registry.register(
            menu.CremeEntry,
            # menu.RecentEntitiesEntry,
            menu.QuickAccessEntry,
            menu.JobsEntry,
            menu.QuickFormsEntries,
            menu.EntitiesCreationEntry,
        )

    def register_actions(self, action_registry):
        from . import actions

        action_registry.register_instance_actions(
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
            bricks.ButtonsBrick,
            bricks.PropertiesBrick,
            bricks.RelationsBrick,
            bricks.CustomFieldsBrick,
            bricks.HistoryBrick,
            bricks.ImprintsBrick,
            bricks.TrashBrick,
            bricks.RecentEntitiesBrick,
            bricks.PinnedEntitiesBrick,
            bricks.StatisticsBrick,
            bricks.JobsBrick,
            bricks.MyJobsBrick,
            bricks.NotificationsBrick,
        )

    def register_bulk_update(self, bulk_update_registry):
        from .models import CustomEntityType

        for kls in CustomEntityType.custom_classes.values():
            bulk_update_registry.register(model=kls)

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

    def register_cloners(self, entity_cloner_registry):
        from .models import CustomEntityType

        for kls in CustomEntityType.custom_classes.values():
            entity_cloner_registry.register(model=kls)

    def register_deletors(self, entity_deletor_registry):
        from .models import CustomEntityType

        for kls in CustomEntityType.custom_classes.values():
            entity_deletor_registry.register(kls)

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
        from .core.enumerable import QSEnumerator

        # TODO: improve the registry to write this
        #       (see 'core.enumerable._EnumerableRegistry._enumerator()') :
        # enumerable_registry.register_related_model(
        #     models.CremeEntity,
        #     enumerators.EntityEnumerator,
        # )
        enumerable_registry.register_related_model(
            model=get_user_model(),
            enumerator_class=enumerators.UserEnumerator,
        ).register_related_model(
            model=models.UserRole,
            enumerator_class=QSEnumerator,
        ).register_related_model(
            model=models.EntityFilter,
            enumerator_class=enumerators.EntityFilterEnumerator,
        ).register_related_model(
            model=models.Vat,
            enumerator_class=enumerators.VatEnumerator,
        ).register_field_type(
            field_class=models.fields.EntityCTypeForeignKey,
            enumerator_class=enumerators.EntityCTypeForeignKeyEnumerator,
        ).register_field(
            model=models.HeaderFilter,
            field_name='user',
            enumerator_class=enumerators.UserEnumerator,
        ).register_field(
            model=models.EntityFilter,
            field_name='user',
            enumerator_class=enumerators.UserEnumerator,
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

    def register_mass_import(self, import_form_registry):
        from .models import CustomEntityType

        for kls in CustomEntityType.custom_classes.values():
            import_form_registry.register(kls)

    def register_notification(self, notification_registry):
        from . import notification as core_notif
        from .core import notification

        notification_registry.register_output(
            # Default output
            value=notification.OUTPUT_WEB, label=_('Web browser'),
        ).register_output(
            value=notification.OUTPUT_EMAIL, label=pgettext_lazy('creme_core', 'Email'),
        ).register_channel_types(
            core_notif.SystemChannelType,
            core_notif.AdministrationChannelType,
            core_notif.JobsChannelType,
            core_notif.RemindersChannelType,
        ).register_content(
            content_cls=notification.SimpleNotifContent,
        ).register_content(
            content_cls=core_notif.UpgradeAnnouncement,
        ).register_content(
            content_cls=core_notif.MassImportDoneContent,
        )

    def register_creme_config(self, config_registry):
        from . import models

        register_model = config_registry.register_model
        register_model(models.Language, 'language')
        register_model(models.Currency, 'currency')
        register_model(models.Vat,      'vat_value').edition(
            # TODO: should we provide a customised error message?
            #       (e.g. which instances are blocking edition)
            enable_func=lambda instance, user: not instance.is_referenced
        )

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
            register_model(fake_models.FakeIngredientGroup,  'fake_ingredient_group')
            register_model(fake_models.FakeSkill,            'fake_skill')
            register_model(fake_models.FakeTraining,         'fake_training')

            # NB: we just need another URLs for creation/edition/deletion
            # (even if these are stupid)
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

            config_registry.register_portal_bricks(fake_bricks.FakePortalBrick)
            config_registry.register_app_bricks('creme_core', fake_bricks.FakeAppPortalBrick)

    def register_sandboxes(self, sandbox_type_registry):
        from . import sandboxes

        sandbox_type_registry.register(sandboxes.OnlySuperusersType)

    def register_setting_keys(self, setting_key_registry):
        from . import setting_keys

        setting_key_registry.register(
            setting_keys.global_filters_edition_key,
            setting_keys.brick_opening_key,
            setting_keys.brick_showempty_key,
            setting_keys.currency_symbol_key,
        )

    def register_workflows(self, workflow_registry):
        from . import workflows

        workflow_registry.register_triggers(
            workflows.EntityCreationTrigger,
            workflows.EntityEditionTrigger,
            workflows.PropertyAddingTrigger,
            workflows.RelationAddingTrigger,
        ).register_sources(
            workflows.CreatedEntitySource,
            workflows.EditedEntitySource,
            workflows.TaggedEntitySource,
            workflows.SubjectEntitySource,
            workflows.ObjectEntitySource,
            workflows.FixedEntitySource,
            workflows.EntityFKSource,
            workflows.FirstRelatedEntitySource,
        ).register_actions(
            workflows.PropertyAddingAction,
            workflows.RelationAddingAction,
        )

    # TODO: set Meta.formfield_callback for Creme(Model)Form instead?
    # TODO: better API + move some code to creme_config ??
    @staticmethod
    def hook_fk_formfield():
        from django.db.models import ForeignKey

        from creme.creme_config.forms import fields as config_fields

        from .forms import fields as core_fields
        from .models import CremeEntity

        class NotEnumerableFKFallbackField(core_fields.ReadonlyMessageField):
            def __init__(this, *, label,
                         initial=(
                             'The FK is not enumerable, you should define a '
                             'specific form-field if you want to keep it editable.'
                         ),
                         **kwargs
                         ):
                super().__init__(label=label, initial=initial)

        original_fk_formfield = ForeignKey.formfield

        def new_fk_formfield(self, **kwargs):
            remote_field = self.remote_field
            remote_model = remote_field.model
            limit_choices_to = remote_field.limit_choices_to

            if issubclass(remote_model, CremeEntity):
                if remote_model is CremeEntity:
                    if limit_choices_to is not None:
                        logger.warning(
                            'GenericEntityField currently does not manage "q_filter".'
                        )

                    return core_fields.GenericEntityField(
                        label=self.verbose_name,
                        required=not self.blank,
                    )

                return core_fields.CreatorEntityField(
                    label=self.verbose_name,
                    model=remote_model,
                    required=not self.blank,
                    q_filter=limit_choices_to,
                    help_text=self.help_text,
                )
            elif self.get_tag(FieldTag.ENUMERABLE):
                required = kwargs.pop('required', False)

                return config_fields.CreatorEnumerableModelChoiceField(
                    model=self.model,
                    field_name=self.name,
                    required=not self.blank or required,
                    label=self.verbose_name,
                    help_text=self.help_text,
                    **kwargs
                )

            return original_fk_formfield(
                self, **{'form_class': NotEnumerableFKFallbackField, **kwargs}
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
    def hook_nullboolean_widget():
        from django import forms

        from creme.creme_core.forms import widgets

        forms.NullBooleanField.widget = widgets.PrettyNullBooleanSelect

    @staticmethod
    def hook_typedchoice_widget():
        from django import forms

        from creme.creme_core.forms import widgets

        forms.TypedChoiceField.widget = widgets.PrettySelect


def creme_app_configs():
    for app_config in apps.get_app_configs():
        if app_config.creme_app:
            yield app_config


def extended_app_configs(app_labels):
    """Get the AppConfigs corresponding to given labels, & their extending AppConfigs.
    @param app_labels: Iterable of app labels (e.g. ['persons', documents']).
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
