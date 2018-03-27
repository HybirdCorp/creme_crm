# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2018  Hybird
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
from json import dumps as jsondumps, loads as jsonloads

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import AppCommand, CommandError
from django.core.management.color import no_style
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.migrations.recorder import MigrationRecorder
from django.dispatch import receiver
from django.utils.encoding import force_unicode

from creme.creme_core.core.setting_key import setting_key_registry
from creme.creme_core.gui.bricks import Brick
from creme.creme_core.gui.button_menu import Button
from creme.creme_core.models import (CremeEntity, RelationType, CremePropertyType,
         EntityFilter, HistoryLine, SettingValue, Job,
         PreferedMenuItem, ButtonMenuItem,
         BlockDetailviewLocation, BlockPortalLocation, BlockMypageLocation,
         RelationBlockItem, InstanceBlockConfigItem, BlockState)
from creme.creme_core.utils import split_filter
from creme.creme_core.utils.collections import LimitedList
from creme.creme_core.signals import pre_uninstall_flush, post_uninstall_flush


MAX_ERRORS = 15  # Number of errors which are displayed when flushing instances #TODO: as argument ?


def uninstall_handler(msg):
    def decorator(handler):
        @wraps(handler)
        def _aux(sender, verbosity, stdout_write, style, **kwargs):
            if verbosity:
                stdout_write(msg)

            handler(sender=sender, verbosity=verbosity,
                    stdout_write=stdout_write, style=style, **kwargs
                   )

            if verbosity:
                stdout_write(' [OK]', style.MIGRATE_SUCCESS)

        return _aux

    return decorator


@receiver(pre_uninstall_flush)
@uninstall_handler('Deleting buttons...')
def _uninstall_buttons(sender, **kwargs):
    # Remove the button of the app (ie the classes of the buttons are defined in the app)
    # Button related to the app's model should be removed when the ContentTypes are removed.
    prefix = Button.generate_id(app_name=sender.label, name='')
    ButtonMenuItem.objects.filter(button_id__startswith=prefix).delete()


@receiver(pre_uninstall_flush)
@uninstall_handler('Deleting blocks...')
def _uninstall_blocks(sender, **kwargs):
    app_label = sender.label
    brick_ids = set()

    # RelationBlockItem --------------------------------------------------------
    rbi_brick_ids = RelationBlockItem.objects \
                                     .filter(relation_type__id__startswith=app_label + '-') \
                                     .values_list('brick_id', flat=True)

    brick_ids.update(rbi_brick_ids)
    BlockDetailviewLocation.objects.filter(brick_id__in=rbi_brick_ids).delete()
    # NB: concerned RelationBlockItems should be removed when RelationType are removed.

    # InstanceBlockConfigItem --------------------------------------------------
    ibc_items = InstanceBlockConfigItem.objects\
                                       .filter(brick_id__startswith=InstanceBlockConfigItem.
                                                                        generate_base_id(app_name=app_label,
                                                                                         name='',
                                                                                        )
                                              )

    ibci_brick_ids = [item.brick_id for item in ibc_items]
    brick_ids.update(ibci_brick_ids)
    BlockDetailviewLocation.objects.filter(brick_id__in=ibci_brick_ids).delete()
    BlockPortalLocation.objects.filter(brick_id__in=ibci_brick_ids).delete()
    BlockMypageLocation.objects.filter(brick_id__in=ibci_brick_ids).delete()
    ibc_items.delete()

    # Regular blocks -----------------------------------------------------------
    id_prefix = Brick.generate_id(app_name=app_label, name='')

    bdl = BlockDetailviewLocation.objects.filter(brick_id__startswith=id_prefix)
    brick_ids.update(bdl.values_list('brick_id', flat=True))
    bdl.delete()

    bpl = BlockPortalLocation.objects.filter(brick_id__startswith=id_prefix)
    brick_ids.update(bpl.values_list('brick_id', flat=True))
    bpl.delete()

    bmpl = BlockMypageLocation.objects.filter(brick_id__startswith=id_prefix)
    brick_ids.update(bmpl.values_list('brick_id', flat=True))
    bmpl.delete()

    BlockState.objects.filter(brick_id__in=brick_ids)

    # Blocks on the app's portal (not related to ContentTypes,
    # so they won't be removed automatically)
    BlockPortalLocation.objects.filter(app_name=app_label).delete()


@receiver(pre_uninstall_flush)
@uninstall_handler('Deleting preferred menu entries...')
def _uninstall_preferred_menu(sender, **kwargs):
    PreferedMenuItem.objects.filter(url__startswith='/%s/' % sender.label).delete()


@receiver(pre_uninstall_flush)
@uninstall_handler('Deleting setting values...')
def _uninstall_setting_values(sender, **kwargs):
    app_label = sender.label
    SettingValue.objects\
                .filter(key_id__in=[skey.id
                                        for skey in setting_key_registry
                                            if skey.app_label == app_label
                                   ]
                       )\
                .delete()


@receiver(pre_uninstall_flush)
@uninstall_handler('Deleting jobs...')
def _uninstall_jobs(sender, **kwargs):
    for job in Job.objects.filter(type_id__startswith='%s-' % sender.label):
        job.delete()


@receiver(post_uninstall_flush)
@uninstall_handler('Deleting property types...')
def _uninstall_property_types(sender, **kwargs):
    CremePropertyType.objects.filter(id__startswith=sender.label + '-').delete()


@receiver(post_uninstall_flush)
@uninstall_handler('Deleting relationship types...')
def _uninstall_relation_types(sender, **kwargs):
    for rtype in RelationType.objects.filter(id__startswith=sender.label + '-subject_'):
        rtype.delete()  # Symmetrical type is deleted too


@receiver(post_uninstall_flush)
@uninstall_handler('Deleting entity filters types...')
def _uninstall_entity_filters(sender, content_types, stdout_write, style, **kwargs):
    ctype_ids = {ct.id for ct in content_types}

    for ctype in content_types:
        for efilter in EntityFilter.objects.filter(entity_type=ctype):
            parents = {cond.filter_id:  cond.filter
                        for cond in efilter._iter_parent_conditions()  # TODO: public method ?
                            if cond.filter.entity_type_id not in ctype_ids
                      }

            if parents:
                stdout_write(' Beware: the filter "%s" (id=%s) was used as '
                             'sub-filter by the following filter(s): %s' % (
                                    efilter.name,
                                    efilter.id,
                                    ', '.join('<"%s" (id="%s")>' % (p.name, p.id)
                                                  for p in parents.itervalues()
                                             ),
                                ),
                             style.NOTICE
                            )

            efilter.delete(check_orphan=False)


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
        d = jsonloads(user.json_settings)
        new_d = {}
        save = False

        for k, v in d.iteritems():
            if k.startswith(prefix):
                save = True
            else:
                new_d[k] = v

        if save:
            user.json_settings = jsondumps(new_d)
            user.save()


class Command(AppCommand):
# TODO ??
#    option_list = AppCommand.option_list + (
#        make_option('--database', action='store', dest='database',
#                    default=DEFAULT_DB_ALIAS,
#                    help='Nominates a database to reset. Defaults to the "default" database.',
#                   ),
#    )
    help = 'Uninstall Creme apps correctly, by removing remaining data in DB.'  # TODO: and tables ????
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
            raise CommandError('The following app(s) depend(s) on "%s" & '
                               'must be uninstalled before:\n%s' % (
                                       app_config.label,
                                       '\n'.join(' - ' + name
                                                    for name in depending_app_names
                                                ),
                                   )
                              )

    def _delete_instances(self, models, verbosity):
        if verbosity > 1:
            self.stdout.write('Processing deletion...\n')

        # TODO: implement a True dependencies solver ??
        # NB: we delete first the entities models because it will probably
        #     avoid major dependencies problems.
        models_info = [(model, True)  # True means 'First deletion trial"
                           for model in chain(*split_filter(lambda m: issubclass(m, CremeEntity), models))
                      ]

        while True:
            errors = LimitedList(MAX_ERRORS)
            next_models_info = []
            progress = False

            for model, first_trial in models_info:
                count = model.objects.count()

                if not count:
                    if verbosity:
                        self.stdout.write('No "%s" instance to delete.\n' % model.__name__)

                    continue

                if verbosity:
                    self.stdout.write('Trying to flush "%s" (%s%s instances)...\n' % (
                                            model.__name__,
                                            count,
                                            '' if first_trial else ' remaining',
                                        )
                                     )

                if issubclass(model, CremeEntity):
                    pre_delete = lambda i: i.relations.filter(type__is_internal=False).delete()
                else:
                    pre_delete = lambda i: None

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
                    self.stdout.write(' [OK] All instances have been deleted.',
                                      self.style.MIGRATE_SUCCESS,
                                     )

            if not next_models_info:
                return

            if not progress:
                extra_errors = max(0, len(errors) - errors.max_size)

                raise CommandError('[KO] Cannot flush all instances: aborting.\n'
                                   '%s\n%s'
                                   'Please delete the problematic instances '
                                   'manually before re-run this command.' % (
                                        '\n'.join('- Cannot delete "%s" (id=%s) (original error: %s)' % (
                                                        obj, obj.id, error,
                                                    ) for obj, error in errors
                                                 ),
                                        '(%s extra error(s))\n' % extra_errors if extra_errors else '',
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
                    self.stdout.write('Trying to delete the ContentType "%s" (id=%s)%s...\n' % (
                                            ctype,
                                            ctype.id,
                                            '' if error is None else ' again',
                                        )
                                     )

                try:
                    ctype.delete()
                except Exception as e:
                    next_ctypes_info.append((ctype, str(e)))
                else:
                    progress = True

                    if verbosity:
                        self.stdout.write(' [OK]', self.style.MIGRATE_SUCCESS)

            ctypes_info = next_ctypes_info

            if not ctypes_info or not progress:
                break

        if ctypes_info:
            raise CommandError('There were errors when trying to the ContentTypes: aborting.\n'
                               '%s\n'
                               'Sadly you have to solve this problem manually '
                               'before re-run this command.' %
                                    '\n'.join('- Cannot delete ContentType for "%s" '
                                              '(original error: %s)' % ci
                                                for ci in ctypes_info
                                             ),
                              )

        if verbosity > 1:
            self.stdout.write(' [OK] All related ContentTypes have been deleted.',
                              self.style.MIGRATE_SUCCESS
                             )

    def _delete_migrations(self, app_label, verbosity):
        if verbosity:
            self.stdout.write('Deleting migrations...\n')

        MigrationRecorder.Migration.objects.filter(app=app_label).delete()

        if verbosity:
            self.stdout.write(' [OK]', self.style.MIGRATE_SUCCESS)

    # TODO: close cursor
    def _delete_tables(self, app_config, app_label, verbosity):
        connection = connections[DEFAULT_DB_ALIAS]  # TODO: options.get('database') ?

#         sql_commands = sql_delete(app, no_style(), connection)
#         sql_commands = sql_delete(app_config, no_style(), connection, close_connection=False)
        sql_commands, dep_error = sql_delete_V2(app_config, no_style(), connection)

        if dep_error:
            self.stderr.write(u" [KO] Dependencies loop (cannot find a safe deletion order).\n"
                              u"SQL commands:\n%s\n" %
                                u'\n'.join(sql_commands)  # TODO: .encode('utf-8')  ??
                             )

            raise CommandError('Sadly you have to DELETE the remaining tables MANUALLY, '
                               'and THEN REMOVE "%s" from your settings.' % app_label,
                              )

        if sql_commands:
            if verbosity:
                self.stdout.write('Trying to delete tables...')

            try:
                cursor = connection.cursor()

                while sql_commands:
                    sql_command = sql_commands.pop(0)

                    if verbosity:
                        self.stdout.write(sql_command)

                    cursor.execute(sql_command)

                    if verbosity:
                        self.stdout.write(' [OK]', self.style.MIGRATE_SUCCESS)
            except Exception as e:
                self.stderr.write(u" [KO] Original error: %(error)s.\n"
                                  u"Remaining SQL commands:\n"
                                  u"%(commands)s\n" % {
                                        'error': force_unicode(e),  # PostGreSQL returns localized errors...
                                        'commands': u'\n'.join(sql_commands),  # TODO: .encode('utf-8')  ??
                                      }
                                 )

                raise CommandError('Sadly you have to DELETE the remaining tables MANUALLY, '
                                   'and THEN REMOVE "%s" from your settings.' % app_label,
                                  )

            if verbosity > 1:
                self.stdout.write(' [OK] All tables have been deleted',
                                  self.style.MIGRATE_SUCCESS
                                 )
        elif verbosity:
            self.stdout.write('No table to delete.')

    def handle_app_config(self, app_config, **options):
        verbosity = options.get('verbosity')
        app_label = app_config.label

        # self._check_creme_app(app_label)
        if not app_config.creme_app:
            raise CommandError('"%s" seems not to be a Creme app '
                               '(see settings.INSTALLED_CREME_APPS)' % app_label
                              )

        self._check_apps_dependencies(app_config)

        HistoryLine.ENABLED = False
        ctypes = ContentType.objects.filter(app_label=app_label)

        pre_uninstall_flush.send(app_config, content_types=ctypes, verbosity=verbosity,
                                 stdout_write=self.stdout.write,
                                 stderr_write=self.stderr.write, style=self.style,
                                )
        self._delete_instances([ct.model_class() for ct in ctypes], verbosity)
        post_uninstall_flush.send(app_config, content_types=ctypes, verbosity=verbosity,
                                  stdout_write=self.stdout.write,
                                  stderr_write=self.stderr.write, style=self.style,
                                 )

        self._delete_ctypes(ctypes, verbosity)
        self._delete_migrations(app_label, verbosity)
        self._delete_tables(app_config, app_label, verbosity)

        if verbosity:
            self.stdout.write('\nUninstall is OK.\n'
                              'You should now remove "%s" from your settings.\n' % app_config.name,
                              self.style.MIGRATE_SUCCESS
                             )


################################################################################
# Copyright (c) Django Software Foundation and individual contributors.
# Copyright (c) Hybird - 2015
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

# NOT USED
# NB: copied from django/core/management/sql.py  (+ check_for_migrations removed)
# 1 - check_for_migrations() annoys us because we want to uninstall Creme apps,
#     which have migrations ; it dnagerous but we know what we are doing
# 2 - sql_destroy_model() strangely returns references that cause errors with MySQL & PGSQL !
def sql_delete(app_config, style, connection, close_connection=True):
    "Returns a list of the DROP TABLE SQL statements for the given app."
#    check_for_migrations(app_config, connection)

    from django.db import router

    # This should work even if a connection isn't available
    try:
        cursor = connection.cursor()
    except Exception:
        cursor = None

    try:
        # Figure out which tables already exist
        if cursor:
            table_names = connection.introspection.table_names(cursor)
        else:
            table_names = []

        output = []

        # Output DROP TABLE statements for standard application tables.
        to_delete = set()

        references_to_delete = {}
        app_models = router.get_migratable_models(app_config, connection.alias, include_auto_created=True)
        for model in app_models:
            if cursor and connection.introspection.table_name_converter(model._meta.db_table) in table_names:
                # The table exists, so it needs to be dropped
                opts = model._meta
                for f in opts.local_fields:
                    # if f.rel and f.rel.to not in to_delete:
                    if f.remote_field and f.remote_field.model not in to_delete:
                        # references_to_delete.setdefault(f.rel.to, []).append((model, f))
                        references_to_delete.setdefault(f.remote_field.model, []).append((model, f))

                to_delete.add(model)

        for model in app_models:
            if connection.introspection.table_name_converter(model._meta.db_table) in table_names:
                output.extend(connection.creation.sql_destroy_model(model, references_to_delete, style))
    finally:
        # Close database connection explicitly, in case this output is being piped
        # directly into a database client, to avoid locking issues.
        if cursor and close_connection:
            cursor.close()
            connection.close()

    # if not output:
    #     output.append('-- App creates no tables in the database. Nothing to do.')

    return output[::-1]  # Reverse it, to deal with table dependencies.


# Creme version of sql_delete, which does not alter FK columns but drops tables
# in an correct order.
# TODO: use sql_destroy_indexes() ??
def sql_delete_V2(app_config, style, connection):
    """SQL queries which drop tables of the given app.
    @return A tuple (command, loop_error).
            'command' is a list of the DROP TABLE SQL statements (strings)
            'loop_error' is a boolean which indicates dependencies loop error.
    """
    from django.db import router
    from django.utils.datastructures import OrderedSet

    from creme.creme_core.utils.dependence_sort import dependence_sort, DependenciesLoopError

    class ModelInfo(object):
        def __init__(self, model, dependencies, sql_cmd):
            self.model = model
            self.dependencies = dependencies
            self.sql_cmd = sql_cmd

    models_info = []
    cursor = connection.cursor()

    try:
        table_names = set(connection.introspection.table_names(cursor))
        app_models = OrderedSet(router.get_migratable_models(app_config,
                                                             connection.alias,
                                                             include_auto_created=True,
                                                            )
                               )

        for model in app_models:
            meta = model._meta

            if connection.introspection.table_name_converter(meta.db_table) in table_names:
                dependencies = []

                for f in meta.local_fields:
                    # if f.rel:
                    if f.remote_field:
                        # related_model = f.rel.to
                        related_model = f.remote_field.model

                        if related_model in app_models:
                            dependencies.append(related_model)

                models_info.append(ModelInfo(model=model,
                                             dependencies=dependencies,
                                             sql_cmd=connection.creation.sql_destroy_model(model, [], style)[0],
                                            )
                                  )

    finally:
        cursor.close()

    dep_error = False
    try:
        models_info = dependence_sort(models_info,
                                      get_key=lambda mi: mi.model,
                                      get_dependencies=lambda mi: mi.dependencies,
                                     )
    except DependenciesLoopError:
        dep_error = True
    else:
        models_info.reverse()  # The dependencies must be deleted _after_

    return [mi.sql_cmd for mi in models_info], dep_error
