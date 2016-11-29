# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from imp import find_module
import sys
from traceback import format_exception

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.models.signals import pre_save

from creme.creme_core.apps import creme_app_configs
# from creme.creme_core.registry import creme_registry
from creme.creme_core.utils.collections import OrderedSet
from creme.creme_core.utils.dependence_sort import dependence_sort


def _checked_app_label(app_label, app_labels):
    if app_label not in app_labels:
        raise CommandError('"%s" seems not to be a Creme app '
                           '(see settings.INSTALLED_CREME_APPS)' % app_label
                          )

    return app_label


class BasePopulator(object):
    dependencies = []  # eg: ['appname1', 'appname2']

    def __init__(self, verbosity, app, all_apps, options, stdout, style):
        self.verbosity = verbosity
        self.app = app
        self.options = options
        self.stdout = stdout
        self.style  = style
        self.build_dependencies(all_apps)

    def __repr__(self):
        return '<Populator(%s)>' % self.app

    def build_dependencies(self, apps_set):
        deps = []

        for dep in self.dependencies:
            try:
                deps.append(_checked_app_label(dep, apps_set))
            except CommandError as e:
                self.stdout.write('BEWARE: ignored dependencies "%s", %s' % (dep, e),
                                  self.style.NOTICE,
                                 )

        self.dependencies = deps

    def populate(self):
        raise NotImplementedError

    def get_app(self):
        return self.app

    def get_dependencies(self):
        return self.dependencies


class Command(BaseCommand):
    help = ('Populates the database for the specified applications, or the '
            'entire site if no apps are specified.')
    args = '[appname ...]'
    leave_locale_alone = True

    def _signal_handler(self, sender, instance, **kwargs):
        if instance.pk and not isinstance(instance.pk, basestring):
            # Models with string pk should manage pk manually, so we can optimise
            self.models.add(sender)

    def handle(self, *app_names, **options):
        verbosity = options.get('verbosity')

        # eg: 'persons', 'creme_core'...
        # all_apps = OrderedSet(creme_app.name for creme_app in creme_registry.iter_apps())
        all_apps = OrderedSet(app_config.label for app_config in creme_app_configs())

        apps_2_populate = all_apps if not app_names else \
                          [_checked_app_label(app, all_apps) for app in app_names]

        # ----------------------------------------------------------------------
        populators = []
        populators_names = set()  # Names of populators that will be run
        total_deps = set()  # Populators names that are needed by our populators
        total_missing_deps = set()  # All populators names that are added by
                                    # this script because of dependencies

        while True:
            changed = False

            for app in apps_2_populate:
                try:
                    populator = self._get_populate_module(app) \
                                    .populate \
                                    .Populator(verbosity, app, all_apps, options, self.stdout, self.style)
                except ImportError:
                    if verbosity >= 1:
                        self.stdout.write(self.style.NOTICE('Disable populate for "%s": '
                                                            'it does not have any "populate.py" script.' % app
                                                           )
                                         )
                else:
                    assert isinstance(populator, BasePopulator)
                    populators.append(populator)
                    populators_names.add(app)
                    total_deps.update(populator.dependencies)
                    changed = True

            if not changed: break

            apps_2_populate = total_deps - populators_names
            total_missing_deps |= apps_2_populate

        if total_missing_deps and verbosity >= 1:
            self.stdout.write('Additional dependencies will be populated: %s' %
                                ', '.join(total_missing_deps),
                              self.style.NOTICE
                             )

        # Clean the dependencies (avoid dependencies that do not exist in
        # 'populators', which would cause Exception raising)
        for populator in populators:
            populator.build_dependencies(populators_names)

        populators = dependence_sort(populators,
                                     BasePopulator.get_app,
                                     BasePopulator.get_dependencies,
                                    )

        # ----------------------------------------------------------------------
        self.models = set()
        dispatch_uid = 'creme_core-populate_command'

        pre_save.connect(self._signal_handler, dispatch_uid=dispatch_uid)

        for populator in populators:
            if verbosity >= 1:
                self.stdout.write('Populate "%s" ...' % populator.app, ending='')
                self.stdout.flush()

            try:
                populator.populate()
            except Exception as e:
                self.stderr.write(' Populate "%s" failed (%s)' % (populator.app, e))
                if verbosity >= 1:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    self.stderr.write(''.join(format_exception(exc_type, exc_value, exc_traceback)))

            if verbosity >= 1:
                self.stdout.write(' OK', self.style.MIGRATE_SUCCESS)

        pre_save.disconnect(dispatch_uid=dispatch_uid)

        # ----------------------------------------------------------------------
        if self.models:
            if verbosity >= 1:
                self.stdout.write('Update sequences for models : %s' %
                                    [model.__name__ for model in self.models],
                                  ending='',
                                 )
                self.stdout.flush()

            connection = connections[options.get('database', DEFAULT_DB_ALIAS)]
            cursor = connection.cursor()

            for line in connection.ops.sequence_reset_sql(no_style(), self.models):
                cursor.execute(line)

            # connection.close() #seems useless (& does not work with mysql)

            if verbosity >= 1:
                self.stdout.write(self.style.MIGRATE_SUCCESS(' OK'))
        elif verbosity >= 1:
                self.stdout.write('No sequence to update.')

        if verbosity >= 1:
            self.stdout.write(self.style.MIGRATE_SUCCESS('Populate is OK.'))

    def _get_populate_module(self, app_label):
        app_name = apps.get_app_config(app_label).name
        find_module('populate', __import__(app_name, globals(), locals(), [app_label]).__path__)

        return __import__(app_name, globals(), locals(), ['populate'])
