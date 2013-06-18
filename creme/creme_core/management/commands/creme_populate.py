# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from __future__ import print_function

import sys
from traceback import format_exception
from optparse import make_option, OptionParser
from imp import find_module

from django.db import connections, DEFAULT_DB_ALIAS
from django.db.models.signals import pre_save
from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.utils import translation
from django.conf import settings

from creme.creme_core.utils.dependence_sort import dependence_sort


PROJECT_PREFIX = 'creme.'

def _extended_app_name(app_name, app_names, raise_exception=True):
    if app_name in app_names:
        return app_name

    inner_app_name = PROJECT_PREFIX + app_name

    if inner_app_name not in app_names:
        if raise_exception:
            raise ValueError('%s seems not to be a Creme app (see settings.INSTALLED_CREME_APPS)' % app_name)

        return None

    return inner_app_name

class BasePopulator(object):
    dependencies = [] #eg ['appname1', 'appname2']

    def __init__(self, verbosity, app, all_apps, options):
        self.verbosity = verbosity
        self.app = app
        self.options = options
        self.build_dependencies(all_apps)

    def __repr__(self):
        return '<Populator(%s)>' % (self.app)

    def build_dependencies(self, apps_set):
        deps = []
        for dep in self.dependencies:
            ext_dep = _extended_app_name(dep, apps_set, raise_exception=False)
            if ext_dep is None:
                print('BEWARE: ignored dependencies "%s", it seems it is not an '
                      'installed Creme App (see settings.INSTALLED_CREME_APPS)' % dep
                     )
            else:
                deps.append(ext_dep)

        self.dependencies = deps

    def populate(self):
        raise NotImplementedError

    #def reset(self):
        #pass

    def get_app(self):
        return self.app

    def get_dependencies(self):
        return self.dependencies


class Command(BaseCommand):
    #option_list = BaseCommand.option_list + ( #TODO: when reset is possible
        #make_option("-R", "--reset",    action="store_const", const="reset",    dest="action"),
        #make_option("-P", "--populate", action="store_const", const="populate", dest="action"),
    #)
    help = ('Populates the database for the specified applications, or the '
            'entire site if no apps are specified.')
    args = '[appname ...]'

    def create_parser(self, prog_name, subcommand):
        """Create and return the ``OptionParser`` which will be used to parse
        the arguments to this command.
        """
        return OptionParser(prog=prog_name,
                            usage=self.usage(subcommand),
                            version=self.get_version(),
                            option_list=self.option_list,
                            conflict_handler="resolve",
                           )

    def handle(self, *app_names, **options):
        #action = options.get('action') or 'populate' #TODO: when reset is possible
        action = 'populate'

        translation.activate(settings.LANGUAGE_CODE)
        self._do_populate_action(action, app_names, **options)

    def _signal_handler(self, sender, instance, **kwargs):
        if instance.pk and not isinstance(instance.pk, basestring): # models with string pk should manage pk manually, so we can optimise
            self.models.add(sender)

    def _do_populate_action(self, name, applications, *args, **options):
        verbosity = int(options.get('verbosity'))
        all_apps = frozenset(settings.INSTALLED_CREME_APPS)

        if not applications:
            apps_2_populate = settings.INSTALLED_CREME_APPS
        else:
            apps_2_populate = []

            for app in applications:
                apps_2_populate.append(_extended_app_name(app, all_apps))

        #-----------------------------------------------------------------------
        populators = []
        populators_names = set() # names of populators that will be run
        total_deps = set() # populators names that are needed by our populators
        total_missing_deps = set() # all populators names that are added by
                                   # this script because of dependencies

        #while apps_2_populate: #can infinitely loops if an error occurs
        while True:
            changed = False

            for app in apps_2_populate:
                try:
                    populator = self._get_populate_module(app) \
                                    .populate \
                                    .Populator(verbosity, app, all_apps, options)
                except ImportError as e:
                    if verbosity >= 1:
                        print('disable populate for "%s": %s' % (app, e))
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
            print('additionnal dependencies will be populated:', ', '.join(total_missing_deps))

        # clean the dependencies (avoid dependencies that do not exist in
        # 'populators', which would cause Exception raising)
        for populator in populators:
            populator.build_dependencies(populators_names)

        populators = dependence_sort(populators,
                                     BasePopulator.get_app,
                                     BasePopulator.get_dependencies,
                                    )

        #-----------------------------------------------------------------------
        self.models = set()
        dispatch_uid = 'creme_core-populate_command'

        pre_save.connect(self._signal_handler, dispatch_uid=dispatch_uid)

        for populator in populators:
            if verbosity >= 1:
                print('populate "%s" ...' % populator.app)

            try:
                #getattr(populator, name)(*args, **options)
                getattr(populator, name)()
            except Exception as e:
                print('populate "%s" failed (%s)' % (populator.app, e))
                if verbosity >= 1:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    print(''.join(format_exception(exc_type, exc_value, exc_traceback)))

            if verbosity >= 1:
                print('populate "%s" done.' % populator.app)

        pre_save.disconnect(dispatch_uid=dispatch_uid)

        #-----------------------------------------------------------------------
        if verbosity >= 1:
            print('update sequences for models :', [model.__name__ for model in self.models])

        connection = connections[options.get('database', DEFAULT_DB_ALIAS)]
        cursor = connection.cursor()

        for line in connection.ops.sequence_reset_sql(no_style(), self.models):
            cursor.execute(line)

        #connection.close() #seems useless (& does not work with mysql)

        if verbosity >= 1:
            print('update sequences done.')

    def _get_populate_module(self, app):
        find_module('populate', __import__(app, globals(), locals(), [app.split('.')[-1]]).__path__)
        return __import__(app, globals(), locals(), ['populate'])
