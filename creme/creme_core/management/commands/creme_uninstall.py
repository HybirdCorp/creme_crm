################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2024  Hybird
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

from functools import wraps
from itertools import chain
from json import loads as json_load

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import AppCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.recorder import MigrationRecorder
from django.dispatch import receiver
from django.utils.encoding import force_str
from django.utils.functional import partition

from creme.creme_core.core.setting_key import setting_key_registry
from creme.creme_core.gui.bricks import Brick
from creme.creme_core.gui.button_menu import Button
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    BrickMypageLocation,
    BrickState,
    ButtonMenuItem,
    CremeEntity,
    CremePropertyType,
    CustomFormConfigItem,
    EntityFilter,
    HistoryLine,
    InstanceBrickConfigItem,
    Job,
    MenuConfigItem,
    RelationBrickItem,
    RelationType,
    SettingValue,
)
from creme.creme_core.signals import post_uninstall_flush, pre_uninstall_flush
from creme.creme_core.utils.collections import LimitedList
from creme.creme_core.utils.serializers import json_encode

# TODO: as argument ?
MAX_ERRORS = 15  # Number of errors which are displayed when flushing instances


def uninstall_handler(msg):
    def decorator(handler):
        @wraps(handler)
        def _aux(sender, verbosity, stdout_write, style, **kwargs):
            if verbosity:
                stdout_write(msg)

            handler(
                sender=sender, verbosity=verbosity,
                stdout_write=stdout_write, style=style,
                **kwargs
            )

            if verbosity:
                stdout_write(' [OK]', style.SUCCESS)

        return _aux

    return decorator


@receiver(pre_uninstall_flush)
@uninstall_handler('Deleting menu entries...')
def _uninstall_menu_entries(sender, **kwargs):
    MenuConfigItem.objects.filter(entry_id__startswith=f'{sender.label}-').delete()


@receiver(pre_uninstall_flush)
@uninstall_handler('Deleting buttons...')
def _uninstall_buttons(sender, **kwargs):
    # Remove the button of the app (ie the classes of the buttons are defined in the app)
    # Button related to the app's model should be removed when the ContentTypes are removed.
    prefix = Button.generate_id(app_name=sender.label, name='')
    ButtonMenuItem.objects.filter(button_id__startswith=prefix).delete()


@receiver(pre_uninstall_flush)
@uninstall_handler('Deleting bricks...')
def _uninstall_bricks(sender, **kwargs):
    app_label = sender.label
    brick_ids = set()

    # RelationBrickItem --------------------------------------------------------
    rbi_brick_ids = [
        rbi.brick_id for rbi in RelationBrickItem.objects.filter(
            relation_type__id__startswith=f'{app_label}-',
        )
    ]

    brick_ids.update(rbi_brick_ids)
    BrickDetailviewLocation.objects.filter(brick_id__in=rbi_brick_ids).delete()
    # NB: concerned RelationBrickItems should be removed when RelationType are removed.

    # InstanceBrickConfigItem --------------------------------------------------
    ibc_items = InstanceBrickConfigItem.objects.filter(
        brick_class_id__startswith=InstanceBrickConfigItem.generate_base_id(
            app_name=app_label, name='',
        ),
    )

    ibci_brick_ids = [item.brick_id for item in ibc_items]
    brick_ids.update(ibci_brick_ids)
    BrickDetailviewLocation.objects.filter(brick_id__in=ibci_brick_ids).delete()
    BrickHomeLocation.objects.filter(brick_id__in=ibci_brick_ids).delete()
    BrickMypageLocation.objects.filter(brick_id__in=ibci_brick_ids).delete()
    ibc_items.delete()

    # Regular blocks -----------------------------------------------------------
    id_prefix = Brick.generate_id(app_name=app_label, name='')

    bdl = BrickDetailviewLocation.objects.filter(brick_id__startswith=id_prefix)
    brick_ids.update(bdl.values_list('brick_id', flat=True))
    bdl.delete()

    bpl = BrickHomeLocation.objects.filter(brick_id__startswith=id_prefix)
    brick_ids.update(bpl.values_list('brick_id', flat=True))
    bpl.delete()

    bmpl = BrickMypageLocation.objects.filter(brick_id__startswith=id_prefix)
    brick_ids.update(bmpl.values_list('brick_id', flat=True))
    bmpl.delete()

    BrickState.objects.filter(brick_id__in=brick_ids)


@receiver(pre_uninstall_flush)
@uninstall_handler('Deleting setting values...')
def _uninstall_setting_values(sender, **kwargs):
    app_label = sender.label
    SettingValue.objects.filter(
        key_id__in=[
            skey.id
            for skey in setting_key_registry
            if skey.app_label == app_label
        ],
    ).delete()


@receiver(pre_uninstall_flush)
@uninstall_handler('Deleting jobs...')
def _uninstall_jobs(sender, **kwargs):
    for job in Job.objects.filter(type_id__startswith=f'{sender.label}-'):
        job.delete()


@receiver(post_uninstall_flush)
@uninstall_handler('Deleting property types...')
def _uninstall_property_types(sender, **kwargs):
    CremePropertyType.objects.filter(app_label=sender.label).delete()


@receiver(post_uninstall_flush)
@uninstall_handler('Deleting relationship types...')
def _uninstall_relation_types(sender, **kwargs):
    for rtype in RelationType.objects.filter(id__startswith=f'{sender.label}-subject_'):
        rtype.delete()  # Symmetrical type is deleted too


@receiver(post_uninstall_flush)
@uninstall_handler('Deleting entity filters types...')
def _uninstall_entity_filters(sender, content_types, stdout_write, style, **kwargs):
    ctype_ids = {ct.id for ct in content_types}

    for ctype in content_types:
        for efilter in EntityFilter.objects.filter(entity_type=ctype):
            parents = {
                cond.filter_id:  cond.filter
                for cond in efilter._iter_parent_conditions()  # TODO: public method ?
                if cond.filter.entity_type_id not in ctype_ids
            }

            if parents:
                stdout_write(
                    ' Beware: the filter "{name}" (id={id}) was used as '
                    'sub-filter by the following filter(s): {parents}'.format(
                        name=efilter.name,
                        id=efilter.id,
                        parents=', '.join(
                            f'<"{p.name}" (id="{p.id}")>' for p in parents.values()
                        ),
                    ),
                    style.NOTICE,
                )

            efilter.delete(check_orphan=False)


@receiver(post_uninstall_flush)
@uninstall_handler('Deleting custom forms...')
def _uninstall_custom_forms(sender, **kwargs):
    CustomFormConfigItem.objects.filter(
        descriptor_id__startswith=f'{sender.label}-',
    ).delete()


@receiver(post_uninstall_flush)
@uninstall_handler('Deleting history lines...')
def _uninstall_history_lines(sender, content_types, **kwargs):
    # NB: we delete HistoryLine manually, in order to delete related lines too.
    HistoryLine.delete_lines(HistoryLine.objects.filter(entity_ctype__in=content_types))


@receiver(post_uninstall_flush)
@uninstall_handler('Deleting user setting values...')
def _uninstall_user_setting_values(sender, **kwargs):
    prefix = sender.label + '-'

    for user in get_user_model().objects.all():
        d = json_load(user.json_settings)
        new_d = {}
        save = False

        for k, v in d.items():
            if k.startswith(prefix):
                save = True
            else:
                new_d[k] = v

        if save:
            user.json_settings = json_encode(new_d)
            user.save()


class Command(AppCommand):
    # TODO ??
    #    option_list = AppCommand.option_list + (
    #        make_option(
    #            '--database', action='store', dest='database',
    #            default=DEFAULT_DB_ALIAS,
    #            help='Nominates a database to reset. Defaults to the "default" database.',
    #       ),
    #    )

    # TODO: and tables ??
    help = 'Uninstall Creme apps correctly, by removing remaining data in DB.'
    args = '[appname ...]'
    requires_migrations_checks = True

    def _check_apps_dependencies(self, app_config):
        depending_app_names = []
        app_name = app_config.name

        for other_app_config in apps.get_app_configs():
            other_name = other_app_config.name

            if other_name != app_name:
                dependencies = getattr(other_app_config, 'dependencies', ())

                if app_name in dependencies:
                    depending_app_names.append(other_name)

        if depending_app_names:
            raise CommandError(
                'The following app(s) depend(s) on "{app}" & '
                'must be uninstalled before:\n{apps}'.format(
                    app=app_config.label,
                    apps='\n'.join(f' - {name}' for name in depending_app_names),
                )
            )

    def _delete_instances(self, models, verbosity):
        if verbosity > 1:
            self.stdout.write('Processing deletion...\n')

        # TODO: implement a True dependencies solver ??
        # NB: we delete first the entities models because it will probably
        #     avoid major dependencies problems.
        models_info = [
            (model, True)  # True means "First deletion trial"
            for model in chain(*partition(lambda m: not issubclass(m, CremeEntity), models))
        ]

        while True:
            errors = LimitedList(MAX_ERRORS)
            next_models_info = []
            progress = False

            for model, first_trial in models_info:
                count = model.objects.count()

                if not count:
                    if verbosity:
                        self.stdout.write(f'No "{model.__name__}" instance to delete.\n')

                    continue

                if verbosity:
                    self.stdout.write(
                        'Trying to flush "{model}" ({count}{adj} instances)...\n'.format(
                            model=model.__name__,
                            count=count,
                            adj='' if first_trial else ' remaining',
                        )
                    )

                if issubclass(model, CremeEntity):
                    def pre_delete(i):
                        i.relations.filter(type__is_internal=False).delete()
                else:
                    def pre_delete(i):
                        pass

                local_errors = False

                for instance in model.objects.all():
                    try:
                        pre_delete(instance)
                        instance.delete()
                    except Exception as e:
                        local_errors = True
                        errors.append((instance, str(e)))
                    else:
                        progress = True

                if local_errors:
                    next_models_info.append((model, False))
                elif verbosity:
                    self.stdout.write(
                        ' [OK] All instances have been deleted.',
                        self.style.SUCCESS,
                    )

            if not next_models_info:
                return

            if not progress:
                extra_errors = max(0, len(errors) - errors.max_size)

                raise CommandError(
                    '[KO] Cannot flush all instances: aborting.\n'
                    '{errors}\n{extra_errors}'
                    'Please delete the problematic instances '
                    'manually before re-run this command.'.format(
                        errors='\n'.join(
                            f'- Cannot delete "{obj}" (id={obj.id}) (original error: {error})'
                            for obj, error in errors
                        ),
                        extra_errors=f'({extra_errors} extra error(s))\n' if extra_errors else '',
                    )
                )

            models_info = next_models_info

    def _delete_ctypes(self, ctypes, verbosity):
        # NB: Deleting the ContentType should delete the useless block config,
        #     search config, history lines etc...

        if verbosity > 1:
            self.stdout.write('Processing ContentTypes deletion...\n')

        ctypes_info = [(ctype, None) for ctype in ctypes]  # 'None' means: "no error"

        while True:
            progress = False
            next_ctypes_info = []

            for ctype, error in ctypes_info:
                if verbosity:
                    self.stdout.write(
                        'Trying to delete the ContentType "{ctype}" (id={id}){again}...\n'.format(
                            ctype=ctype,
                            id=ctype.id,
                            again='' if error is None else ' again',
                        )
                    )

                try:
                    ctype.delete()
                except Exception as e:
                    next_ctypes_info.append((ctype, str(e)))
                else:
                    progress = True

                    if verbosity:
                        self.stdout.write(' [OK]', self.style.SUCCESS)

            ctypes_info = next_ctypes_info

            if not ctypes_info or not progress:
                break

        if ctypes_info:
            raise CommandError(
                'There were errors when trying to the ContentTypes: aborting.\n'
                '{}\n'
                'Sadly you have to solve this problem manually '
                'before re-run this command.'.format(
                    '\n'.join(
                        '- Cannot delete ContentType for "{}" '
                        '(original error: {})'.format(*ci)
                        for ci in ctypes_info
                    ),
                )
            )

        if verbosity > 1:
            self.stdout.write(
                ' [OK] All related ContentTypes have been deleted.',
                self.style.SUCCESS,
            )

    def _delete_migrations(self, app_label, verbosity):
        if verbosity:
            self.stdout.write('Deleting migrations...\n')

        MigrationRecorder.Migration.objects.filter(app=app_label).delete()

        if verbosity:
            self.stdout.write(' [OK]', self.style.SUCCESS)

    # TODO: close cursor
    def _delete_tables(self, app_config, app_label, verbosity):
        connection = connections[DEFAULT_DB_ALIAS]  # TODO: options.get('database') ?

        models, dep_error = ordered_models_to_delete(app_config, connection)

        if dep_error:
            self.stderr.write(
                ' [KO] Dependencies loop (cannot find a safe deletion order).\n'
                'Tables:\n{}\n'.format(
                    '\n'.join(model._meta.db_table for model in models),
                )
            )

            raise CommandError(
                f'Sadly you have to DELETE the remaining tables MANUALLY, '
                f'and THEN REMOVE "{app_label}" from your settings.',
            )

        if models:
            if verbosity:
                self.stdout.write('Trying to delete tables...')

            try:
                with connection.schema_editor() as schema_editor:
                    while models:
                        model = models.pop(0)

                        if verbosity:
                            meta = model._meta
                            self.stdout.write(
                                f' Drop the model "{meta.app_label}.{model.__name__}" '
                                f'(table: "{meta.db_table}").'
                            )

                        schema_editor.delete_model(model)

                        if verbosity:
                            self.stdout.write(' [OK]', self.style.SUCCESS)
            except Exception as e:
                self.stderr.write(
                    ' [KO] Original error: {error}.\n'
                    'Remaining tables:\n'
                    '{models}\n'.format(
                        error=force_str(e),  # PostGreSQL returns localized errors...
                        models='\n'.join(model._meta.db_table for model in models),
                    )
                )

                raise CommandError(
                    f'Sadly you have to DELETE the remaining tables MANUALLY, '
                    f'and THEN REMOVE "{app_label}" from your settings.',
                )

            if verbosity > 1:
                self.stdout.write(
                    ' [OK] All tables have been deleted', self.style.SUCCESS,
                )
        elif verbosity:
            self.stdout.write('No table to delete.')

    def handle_app_config(self, app_config, **options):
        verbosity = options.get('verbosity')
        app_label = app_config.label

        if not app_config.creme_app:
            raise CommandError(
                f'"{app_label}" seems not to be a Creme app '
                f'(see settings.INSTALLED_CREME_APPS)'
            )

        self._check_apps_dependencies(app_config)

        HistoryLine.ENABLED = False
        ctypes = ContentType.objects.filter(app_label=app_label)

        pre_uninstall_flush.send(
            app_config,
            content_types=ctypes, verbosity=verbosity,
            stdout_write=self.stdout.write,
            stderr_write=self.stderr.write, style=self.style,
        )
        self._delete_instances([ct.model_class() for ct in ctypes], verbosity)
        post_uninstall_flush.send(
            app_config,
            content_types=ctypes, verbosity=verbosity,
            stdout_write=self.stdout.write,
            stderr_write=self.stderr.write, style=self.style,
        )

        self._delete_ctypes(ctypes, verbosity)
        self._delete_migrations(app_label, verbosity)
        self._delete_tables(app_config, app_label, verbosity)

        if verbosity:
            self.stdout.write(
                f'\nUninstall is OK.\n'
                f'You should now remove "{app_config.name}" from your settings.\n',
                self.style.SUCCESS,
            )


################################################################################
# Copyright (c) Django Software Foundation and individual contributors.
# Copyright (c) Hybird - 2018-2024
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright notice,
#        this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
#
#     3. Neither the name of Django nor the names of its contributors may be used
#        to endorse or promote products derived from this software without
#        specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
################################################################################

def ordered_models_to_delete(app_config, connection):
    """Models of the given app to delete.
    @return A tuple (models, loop_error).
            'models' is a list of the models classes to delete ;
                     the order respects the dependencies between the models.
            'loop_error' is a boolean which indicates dependencies loop error.
    """
    from django.db import router
    from django.utils.datastructures import OrderedSet

    from creme.creme_core.utils.dependence_sort import (
        DependenciesLoopError,
        dependence_sort,
    )

    class ModelInfo:
        def __init__(self, model, dependencies):
            self.model = model
            self.dependencies = dependencies

        def __str__(self):
            return 'ModelInfo(model={model}, dependencies={dependencies})'.format(
                model=self.model.__name__,
                dependencies=[d.__name__ for d in self.dependencies],
            )

    models_info = []
    cursor = connection.cursor()

    try:
        table_names = {*connection.introspection.table_names(cursor)}
        app_models = OrderedSet(router.get_migratable_models(
            app_config,
            connection.alias,
            # NB: the auto created tables are automatically
            #     deleted by schema_editor.delete_model(model)
            include_auto_created=False,
        ))

        for model in app_models:
            meta = model._meta

            if meta.db_table in table_names:
                dependencies = set()  # We use a set to avoid duplicates

                for f in meta.local_fields:
                    if f.remote_field:
                        related_model = f.remote_field.model

                        # NB: we avoid self-referencing (TODO: improve dependence_sort() ?)
                        if related_model is not model and related_model in app_models:
                            dependencies.add(related_model)

                models_info.append(
                    ModelInfo(model=model, dependencies=dependencies)
                )
    finally:
        cursor.close()

    dep_error = False
    try:
        models_info = dependence_sort(
            models_info,
            get_key=lambda mi: mi.model,
            get_dependencies=lambda mi: mi.dependencies,
        )
    except DependenciesLoopError:
        dep_error = True
    else:
        models_info.reverse()  # The dependencies must be deleted _after_

    return [mi.model for mi in models_info], dep_error
