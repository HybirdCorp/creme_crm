################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

import sys
from collections.abc import Sequence
from copy import deepcopy
from importlib import import_module
from traceback import format_exception

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.models.signals import pre_save

from creme.creme_core.apps import creme_app_configs
from creme.creme_core.gui.custom_form import CustomFormDescriptor
from creme.creme_core.models import (
    ButtonMenuItem,
    CremePropertyType,
    CustomFormConfigItem,
    HeaderFilter,
    Job,
    MinionModel,
    NotificationChannel,
    Sandbox,
    SearchConfigItem,
    SettingValue,
)
from creme.creme_core.models.button_menu import ButtonMenuItemProxy
from creme.creme_core.models.creme_property import CremePropertyTypeProxy
from creme.creme_core.models.header_filter import HeaderFilterProxy
from creme.creme_core.models.relation import RelationTypeBuilder
from creme.creme_core.models.search import SearchConfigItemBuilder
from creme.creme_core.utils.collections import OrderedSet
from creme.creme_core.utils.content_type import entity_ctypes
from creme.creme_core.utils.dependence_sort import dependence_sort
from creme.creme_core.utils.imports import safe_import_object


def _checked_app_label(app_label, app_labels):
    if app_label not in app_labels:
        raise CommandError(
            f'"{app_label}" seems not to be a Creme app (see settings.INSTALLED_CREME_APPS)'
        )

    return app_label


class BasePopulator:
    dependencies: list[str] = []  # Example: ['appname1', 'appname2']

    PROPERTY_TYPES: list[CremePropertyType | CremePropertyTypeProxy] = [
        # Example:
        # CremePropertyType.objects.proxy(
        #     uuid=constants.UUID_PROP_MY_PROPERTY,
        #     app_label='my_app',
        #     text=_('is ....'),
        #     subject_models=[Contact, Document],
        # ),
        # Notice: custom types are only built during the 1rst run
    ]
    RELATION_TYPES: list[RelationTypeBuilder] = [
        # Example:
        # RelationType.objects.proxy(
        #     id=constants.REL_SUB_MY_RELATIONSHIP,
        #     predicate=_('is ....'),
        #     is_custom=True,
        #     models=[Contact, Organisation],
        #     properties=[constants.UUID_PROP_MY_PROPERTY],
        #     forbidden_properties=[constants.UUID_PROP_OTHER_PROPERTY],
        # ).symmetric(
        #     id=object_id,
        #     predicate=_('has ....'),
        #     models=[Document],
        # ),
        # Notice: custom types are only built during the 1rst run
    ]
    JOBS: list[Job] = []
    SANDBOXES: list[Sandbox] = []
    CUSTOM_FORMS: list[CustomFormDescriptor] = []
    SETTING_VALUES: list[SettingValue] = []
    HEADER_FILTERS: list[HeaderFilterProxy] = [
        # Example:
        # HeaderFilter.objects.proxy(
        #     id=constants.DEFAULT_HFILTER_MY_MODEL,
        #     name=_('My model view'),
        #     model=MyModel,
        #     cells=[
        #         (EntityCellRegularField, 'name'),
        #         (EntityCellRegularField, 'status'),
        #         (EntityCellRelation,     constants.REL_OBJ_RELATED),
        #     ],
        # ),
    ]
    NOTIFICATION_CHANNELS: list[NotificationChannel] = []
    BUTTONS: list[ButtonMenuItem | ButtonMenuItemProxy] = [
        # Example:
        # ButtonMenuItem(button=MyButton1, order=1), # No model, no role
        # ButtonMenuItem.objects.proxy(button=MyButton2, order=5, model=MyModel),
        # ButtonMenuItem.objects.proxy(button=MyButton3, order=8, role="superuser"),
        # ButtonMenuItem.objects.proxy(
        #     button=MyButton4, order=8, role=MY_ROLE_UUID, model=MyModel,
        # ),
    ]
    SEARCH: list[SearchConfigItemBuilder] = [
        # Example:
        # SearchConfigItem.objects.builder(
        #     model=MyModel, fields=['name', 'description'],
        # ),
    ]

    def __init__(self, verbosity, app, all_apps, options, stdout, style):
        self.verbosity = verbosity
        self.app = app
        self.options = options
        self.stdout = stdout
        self.style = style
        self.build_dependencies(all_apps)

    def __repr__(self):
        return f'<Populator({self.app})>'

    def build_dependencies(self, apps_set) -> None:
        deps = []

        for dep in self.dependencies:
            try:
                deps.append(_checked_app_label(dep, apps_set))
            except CommandError as e:
                self.stdout.write(
                    f'BEWARE: ignored dependencies "{dep}", {e}',
                    self.style.NOTICE,
                )

        self.dependencies = deps

    def populate(self) -> None:
        self.already_populated = already = self._already_populated()
        self._populate()

        if not already:
            self._first_populate()

    def _already_populated(self) -> bool:
        raise NotImplementedError

    def _populate(self) -> None:
        self._populate_property_types()
        self._populate_relation_types()
        self._populate_workflows()
        self._populate_entity_filters()
        self._populate_header_filters()
        self._populate_jobs()
        self._populate_sandboxes()
        self._populate_custom_forms()
        self._populate_search_config()
        self._populate_setting_values()
        self._populate_notification_channels()

    def _first_populate(self) -> None:
        self._populate_menu_config()
        self._populate_buttons_config()
        self._populate_bricks_config()

    # Sub-populators -----------------------------------------------------------
    # - Called every time the command is run:
    def _populate_property_types(self) -> None:
        for ptype in self.PROPERTY_TYPES:
            if isinstance(ptype, CremePropertyType):
                ptype = CremePropertyTypeProxy(instance=ptype)
            elif not isinstance(ptype, CremePropertyTypeProxy):
                raise TypeError(
                    f'{ptype} is not an instance of CremePropertyType|CremePropertyTypeProxy'
                )

            if ptype.is_custom:
                if not self.already_populated:
                    ptype.get_or_create()
            else:
                ptype.update_or_create()

    def _populate_relation_types(self) -> None:
        for rtype in self.RELATION_TYPES:
            if rtype.is_custom:
                if not self.already_populated:
                    rtype.get_or_create()
            else:
                rtype.update_or_create()

    # TODO: declarative way with an attribute 'WORKFLOWS'
    #       BEWARE: a WorkflowProxy is mandatory to manage the attribute "content_type"
    #       (in order to keep a model class as long as possible to avoid inconsistent
    #       ContentType IDs in unit tests)
    def _populate_workflows(self) -> None:
        pass

    def _populate_entity_filters(self) -> None:
        pass

    def _populate_header_filters(self) -> None:
        for hf_proxy in self.HEADER_FILTERS:
            if not isinstance(hf_proxy, HeaderFilterProxy):
                raise TypeError(f'{hf_proxy} is not a HeaderFilterProxy')

            if hf_proxy.is_custom:
                if not self.already_populated:
                    hf_proxy.get_or_create()
            else:
                hf_proxy.get_or_create()

    def _populate_jobs(self) -> None:
        # These are system jobs, with only one instance per type.
        for job in self.JOBS:
            if not isinstance(job, Job):
                raise TypeError(f'{job} is not a Job')

            if job.pk is not None:
                raise ValueError(f'{job} is already saved in DB')

        for job in deepcopy(self.JOBS):
            if not Job.objects.filter(type_id=job.type_id).exists():
                job.language = settings.LANGUAGE_CODE
                job.status = Job.STATUS_OK
                job.save()

    def _populate_sandboxes(self) -> None:
        for sandbox in self.SANDBOXES:
            if not isinstance(sandbox, Sandbox):
                raise TypeError(f'{sandbox} is not a Sandbox')

            if sandbox.pk is not None:
                raise ValueError(f'{sandbox} is already saved in DB')

        for sandbox in deepcopy(self.SANDBOXES):
            if not Sandbox.objects.filter(uuid=sandbox.uuid).exists():
                sandbox.save()

    def _populate_custom_forms(self) -> None:
        create_cfci = CustomFormConfigItem.objects.create_if_needed
        for descriptor in self.CUSTOM_FORMS:
            create_cfci(descriptor=descriptor)

    def _populate_search_config(self) -> None:
        for sc_builder in self.SEARCH:
            sc_builder.get_or_create()

    def _populate_setting_values(self) -> None:
        for svalue in self.SETTING_VALUES:
            if not isinstance(svalue, SettingValue):
                raise TypeError(f'{svalue} is not a SettingValue')

            if svalue.pk is not None:
                raise ValueError(f'{svalue} is already saved in DB')

        for svalue in deepcopy(self.SETTING_VALUES):
            if not SettingValue.objects.filter(key_id=svalue.key_id).exists():
                svalue.save()

    def _populate_notification_channels(self) -> None:
        for channel in self.NOTIFICATION_CHANNELS:
            if not isinstance(channel, NotificationChannel):
                raise TypeError(f'{channel} is not a NotificationChannel')

            if channel.pk is not None:
                raise ValueError(f'{channel} is already saved in DB')

        for channel in deepcopy(self.NOTIFICATION_CHANNELS):
            if not NotificationChannel.objects.filter(uuid=channel.uuid).exists():
                channel.save()

    # - Called only the first time the command is run:
    def _populate_menu_config(self) -> None:
        pass

    def _populate_buttons_config(self) -> None:
        for button in self.BUTTONS:
            if isinstance(button, ButtonMenuItem):
                button = ButtonMenuItemProxy(instance=button, model=None, role=None)
            elif not isinstance(button, ButtonMenuItemProxy):
                raise TypeError(
                    f'{button} is not an instance of ButtonMenuItem|ButtonMenuItemProxy'
                )

            button.get_or_create()

    def _populate_bricks_config(self) -> None:
        pass

    # Sub-populators [END] -----------------------------------------------------

    # Helpers ------------------------------------------------------------------
    def _save_minions(self, unsaved_instances: Sequence[MinionModel]) -> None:
        """Save smartly some instances of model inheriting MinionModel.
        Instances with is_custom=False are created if they do not already exist.
        Instances with is_custom=True are created only during the first execution
        of the populator.
        """
        if not unsaved_instances:
            return

        model = type(unsaved_instances[0])
        if not issubclass(model, MinionModel):
            raise ValueError(f'{model} does not inherit MinionModel')

        for o in unsaved_instances:
            if not isinstance(o, model):
                raise ValueError(f'{o} is not an instance of {model}')

            if o.pk is not None:
                raise ValueError(f'{o} is already saved in DB')

        unsaved_instances = deepcopy(unsaved_instances)

        for instance in unsaved_instances:
            if not instance.is_custom and not model.objects.filter(uuid=instance.uuid).exists():
                instance.save()

        if not self.already_populated:
            for instance in unsaved_instances:
                if instance.is_custom:
                    instance.save()

    # Helpers [END]-------------------------------------------------------------

    def get_app(self):
        return self.app

    def get_dependencies(self) -> list[str]:
        return self.dependencies


def check_hfilters():
    ctypes = {ctype.id: ctype for ctype in entity_ctypes()}
    missing_ct_ids = {*ctypes.keys()} - {
        *HeaderFilter.objects.filter(
            user=None, is_custom=False,
        ).values_list('entity_type', flat=True),
    }

    if missing_ct_ids:
        yield (
            'BEWARE, these types of entity do not have default configuration '
            'for views of list (i.e. HeaderFilter): '
            + ', '.join(str(ctypes[ct_id]) for ct_id in missing_ct_ids)
        )


def check_search():
    ctypes = {ctype.id: ctype for ctype in entity_ctypes()}
    missing_ct_ids = {*ctypes.keys()} - {
        *SearchConfigItem.objects.filter(
            role=None, superuser=False,
        ).values_list('content_type', flat=True),
    }

    if missing_ct_ids:
        yield (
            'BEWARE, these types of entity do not have default configuration '
            'for global search (i.e. SearchConfigItem): '
            + ', '.join(str(ctypes[ct_id]) for ct_id in missing_ct_ids)
        )


class Command(BaseCommand):
    help = ('Populates the database for the specified applications, or the '
            'entire site if no apps are specified.')
    # args = '[appname ...]'
    leave_locale_alone = True
    requires_migrations_checks = True

    end_checks = [
        check_hfilters,
        check_search,
    ]

    def _signal_handler(self, sender, instance, **kwargs):
        if instance.pk and not isinstance(instance.pk, str):
            # Models with string pk should manage pk manually, so we can optimise
            self.models.add(sender)

    def add_arguments(self, parser):
        parser.add_argument(
            'args', metavar='app_labels', nargs='*',
            help='Optionally one or more application label.',
        )

    def handle(self, *app_labels, **options):
        verbosity = options.get('verbosity')

        # e.g. 'persons', 'creme_core'...
        all_apps = OrderedSet(app_config.label for app_config in creme_app_configs())

        apps_2_populate = (
            all_apps
            if not app_labels else
            [_checked_app_label(app, all_apps) for app in app_labels]
        )

        # ----------------------------------------------------------------------
        populators = []
        populators_names = set()  # Names of populators that will be run.
        total_deps = set()  # Populators names that are needed by our populators.

        # All populators names that are added by this script because of dependencies.
        total_missing_deps = set()

        while True:
            changed = False

            for app_label in apps_2_populate:
                populator = self._get_populator(
                    app_label=app_label, verbosity=verbosity, all_apps=all_apps,
                    options=options,
                )

                if populator is not None:
                    populators.append(populator)
                    populators_names.add(app_label)
                    total_deps.update(populator.dependencies)
                    changed = True

            if not changed:
                break

            apps_2_populate = total_deps - populators_names
            total_missing_deps |= apps_2_populate

        if total_missing_deps and verbosity >= 1:
            self.stdout.write(
                'Additional dependencies will be populated: {}'.format(
                    ', '.join(total_missing_deps)
                ),
                self.style.NOTICE
            )

        # Clean the dependencies (avoid dependencies that do not exist in
        # 'populators', which would cause Exception raising)
        for populator in populators:
            populator.build_dependencies(populators_names)

        populators = dependence_sort(
            populators,
            BasePopulator.get_app,
            BasePopulator.get_dependencies,
        )

        # ----------------------------------------------------------------------
        fatal_error = False
        self.models = set()
        dispatch_uid = 'creme_core-populate_command'

        pre_save.connect(self._signal_handler, dispatch_uid=dispatch_uid)

        for populator in populators:
            if verbosity >= 1:
                self.stdout.write(f'Populate "{populator.app}" ...', ending='')
                self.stdout.flush()

            try:
                populator.populate()
            except Exception as e:
                self.stderr.write(f' Populate "{populator.app}" failed ({type(e)}: {e})')
                if verbosity >= 1 or settings.TESTS_ON:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    self.stderr.write(
                        ''.join(format_exception(exc_type, exc_value, exc_traceback))
                    )

                fatal_error = True
                break
            else:
                if verbosity >= 1:
                    self.stdout.write(' OK', self.style.SUCCESS)

        pre_save.disconnect(dispatch_uid=dispatch_uid)

        # ----------------------------------------------------------------------
        if self.models:
            if verbosity >= 1:
                self.stdout.write(
                    'Update sequences for models : {}'.format(
                        [model.__name__ for model in self.models]
                    ),
                    ending='',
                )
                self.stdout.flush()

            connection = connections[options.get('database', DEFAULT_DB_ALIAS)]
            cursor = connection.cursor()

            for line in connection.ops.sequence_reset_sql(no_style(), self.models):
                cursor.execute(line)

            # connection.close() #seems useless (& does not work with mysql)

            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS(' OK'))
        elif verbosity >= 1:
            self.stdout.write('No sequence to update.')

        # ----------------------------------------------------------------------
        if verbosity:
            for end_check in self.end_checks:
                for message in end_check():
                    self.stdout.write(message)

        # ----------------------------------------------------------------------
        if fatal_error:
            raise CommandError('Populate has been interrupted (see error above).')
        elif verbosity >= 1:
            self.stdout.write(self.style.SUCCESS('Populate is OK.'))

    def _get_populator(self,
                       app_label,
                       verbosity,
                       all_apps,
                       options,
                       ) -> BasePopulator | None:
        custom_class_path = settings.POPULATORS.get(app_label)

        if custom_class_path:
            if verbosity >= 1:
                self.stdout.write(self.style.NOTICE(
                    f'The populator for "{app_label}" has been overridden '
                    f'(class "{custom_class_path}" will be used).'
                ))

            populator_class = safe_import_object(custom_class_path)
            if populator_class is None:
                raise CommandError(
                    f'Your settings value POPULATORS is invalid (currently '
                    f'{settings.POPULATORS}). This path, used for the app '
                    f'"{app_label}", is invalid: <{custom_class_path}>.'
                )
        else:
            try:
                mod = import_module(f'{apps.get_app_config(app_label).name}.populate')
            except ModuleNotFoundError:
                if verbosity >= 1:
                    self.stdout.write(self.style.NOTICE(
                        f'Disable populate for "{app_label}": '
                        f'it does not have any "populate.py" script.'
                    ))

                return None
            except ImportError as e:
                if verbosity >= 1:
                    self.stderr.write(self.style.NOTICE(
                        f'Disable populate for "{app_label}": '
                        f'error when importing the populate package [{e}].'
                    ))

                return None

            populator_class = getattr(mod, 'Populator', None)

            if populator_class is None:
                if verbosity >= 1:
                    self.stdout.write(self.style.NOTICE(
                        f'Disable populate for "{app_label}": '
                        f'its populate.py script has no "Populator" class.'
                    ))

                return None

        try:
            populator = populator_class(
                verbosity, app_label, all_apps, options, self.stdout, self.style,
            )
        except Exception as e:
            self.stderr.write(
                f'Disable populate for "{app_label}": '
                f'error when creating populator [{e}].'
            )
        else:
            return populator

        return None
