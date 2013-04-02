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


PROJECT_PREFIX = 'creme.'


class BasePopulator(object):
    dependencies = [] #eg ['appname1', 'appname2']

    def __init__(self, is_verbose, app):
        self.is_verbose = is_verbose
        self.app = app

    def populate(self, *args, **kwargs):
        raise NotImplementedError

    #def reset(self, *args, **kwargs):
        #pass


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        #make_option("-R", "--reset",    action="store_const", const="reset",    dest="action"),
        make_option("-P", "--populate", action="store_const", const="populate", dest="action"),

        make_option("-a", "--app",     action="append",      dest="application", default=None),
        make_option("-v", "--verbose", action="store_const", dest="verbose",     const="true"), #TODO: use inherited option (int)
                                                                                                       # action="store_true" ??
    )

    def create_parser(self, prog_name, subcommand):
        """ Create and return the ``OptionParser`` which will be used to parse
        the arguments to this command.
        """
        return OptionParser(prog=prog_name,
                            usage=self.usage(subcommand),
                            version=self.get_version(),
                            option_list=self.option_list,
                            conflict_handler="resolve",
                           )

    def handle(self, *args, **options):
        action = options.get('action') or 'populate'
        is_verbose = bool(options.get('verbose'))
        app = options.get('application')

        translation.activate(settings.LANGUAGE_CODE)
        self._do_populate_action(action, is_verbose, app, *args, **options)

    def _depencies_sort(self, a, b):
        a_depends_of_b = b.app in a.dependencies if hasattr(a, 'dependencies') else False #TODO: a_depends_of_b = b.app in getattr(a, 'dependencies', ())
        b_depends_of_a = a.app in b.dependencies if hasattr(b, 'dependencies') else False

        if a_depends_of_b and b_depends_of_a or not a_depends_of_b and not b_depends_of_a:
            return 0

        return 1 if a_depends_of_b else -1

    def _signal_handler(self, sender, instance, **kwargs):
        if instance.pk and not isinstance(instance.pk, basestring): # models with string pk should manage pk manually, so we can optimise
            self.models.add(sender)

    def _do_populate_action(self, name, is_verbose, applications, *args, **options):
        if not applications:
            apps_2_populate = settings.INSTALLED_CREME_APPS
        else:
            apps_2_populate = []
            all_apps = frozenset(settings.INSTALLED_CREME_APPS)

            for app in applications:
                if app in all_apps:
                    apps_2_populate.append(app)
                    continue

                project_app = PROJECT_PREFIX + app
                if project_app in all_apps:
                    apps_2_populate.append(project_app)
                    continue

                print app, 'seems not to be a Creme app (see settings.INSTALLED_CREME_APPS): aborting'
                return

        #-----------------------------------------------------------------------
        populates = []

        for app in apps_2_populate:
            try:
                populate_mod = self._get_populate_module(app)
                populate = populate_mod.populate.Populator(is_verbose, app)

                if hasattr(populate, name):
                    populates.append(populate)
            except (ImportError, AttributeError) as e:
                if is_verbose:
                    print 'disable populate for "%s": %s' % (app, e)

        populates.sort(cmp=lambda a, b: self._depencies_sort(a, b))

        #-----------------------------------------------------------------------
        self.models = set()
        dispatch_uid = 'creme_core-populate_command'

        pre_save.connect(self._signal_handler, dispatch_uid=dispatch_uid)

        for populate in populates:
            if is_verbose:
                print 'populate', populate.app, ' ...'

            try:
                getattr(populate, name)(*args, **options)
            except Exception, err:
                print 'populate', populate.app, 'failed :', err
                if is_verbose:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    print ''.join(format_exception(exc_type, exc_value, exc_traceback))

            if is_verbose:
                print 'populate', populate.app, 'done.'

        pre_save.disconnect(dispatch_uid=dispatch_uid)

        #-----------------------------------------------------------------------
        if is_verbose:
            print 'update sequences for models :', [model.__name__ for model in self.models]

        connection = connections[options.get('database', DEFAULT_DB_ALIAS)]
        cursor = connection.cursor()

        for line in connection.ops.sequence_reset_sql(no_style(), self.models):
            cursor.execute(line)

        #connection.close() #seems useless (& does not work with mysql)

        if is_verbose:
            print 'update sequences done.'

    def _get_populate_module(self, app):
        find_module('populate', __import__(app, globals(), locals(), [app.split('.')[-1]]).__path__)
        return __import__(app, globals(), locals(), ['populate'])
