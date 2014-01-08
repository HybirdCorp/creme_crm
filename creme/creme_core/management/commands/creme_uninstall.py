# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014  Hybird
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

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import AppCommand, CommandError
from django.core.management.color import no_style
from django.core.management.sql import sql_delete
from django.db import connections, transaction, DEFAULT_DB_ALIAS

from creme.creme_core.models import CremeEntity, PreferedMenuItem
from creme.creme_core.utils import split_filter

from creme.creme_config.models import SettingKey, SettingValue


MAX_ERRORS = 15 #maximum errors count before aborting #TODO: as argument


#TODO: emit a signal ??
class Command(AppCommand):
    #option_list = AppCommand.option_list + ( #TODO ??
        #make_option('--noinput', action='store_false', dest='interactive', default=True,
            #help='Tells Django to NOT prompt the user for input of any kind.'),
        #make_option('--database', action='store', dest='database',
            #default=DEFAULT_DB_ALIAS, help='Nominates a database to reset. '
                #'Defaults to the "default" database.'),
    #)

    help = 'Uninstall Creme apps correctly, by removing remaining data in DB.' #TODO; and tables ????
    args = '[appname ...]'

    def _delete(self, models, verbosity):
        errors = 0

        #TODO: implement a True dependencies solver ??
        for model in models:
            if verbosity > 1:
                self.stdout.write('Trying to delete "%s" instances\n' % model)

            if issubclass(model, CremeEntity):
                pre_delete = lambda i: i.relations.filter(type__is_internal=False).delete()
            else:
                pre_delete = lambda i: None

            for instance in model.objects.all():
                try:
                    pre_delete(instance)
                    instance.delete()
                except Exception as e:
                    errors += 1
                    self.stderr.write('ERROR: unable to delete "%s" [%s]\n' % (instance, e))

                    if errors > MAX_ERRORS:
                        raise CommandError('Too many errors: aborting. '
                                           'Please delete the problematic instances (see above) manually before re-run this command.'
                                          )

        return  errors

    def handle_app(self, app, **options):
        app_name = app.__name__.split('.')[-2] #__name__ is on the form 'my_app.models' or 'creme.my_app.models'
        verbosity = int(options.get('verbosity'))
        creme_apps = settings.INSTALLED_CREME_APPS

        if app_name not in creme_apps and 'creme.' + app_name not in creme_apps:
            raise CommandError('"%s" seems not to be a Creme app (see settings.INSTALLED_CREME_APPS)' % app_name)

        app_label = app_name.split('.')[-1] #eg 'creme.removeme'  => 'removeme'
        ctypes = ContentType.objects.filter(app_label=app_label)

        #NB: we delete first the entities models because it will probably avoid major dependencies problems.
        for models in split_filter(lambda m: issubclass(m, CremeEntity),
                                   (ct.model_class() for ct in ctypes)
                                  ):
            if self._delete(models, verbosity):
                raise CommandError('There were errors when trying to delete instances: aborting. '
                                   'Please delete the problematic instances (see above) manually before re-run this command.'
                                  )

        PreferedMenuItem.objects.filter(url__startswith='/%s/' % app_label).delete()

        SettingValue.objects.filter(key__app_label=app_label).delete()
        SettingKey.objects.filter(app_label=app_label).delete()

        if 'south' not in settings.INSTALLED_APPS:
            self.stderr.write('ERROR: "south" seems to be not installed (it should be...). Continuing anyway.\n')
        else:
            from south.models import MigrationHistory
            MigrationHistory.objects.filter(app_name=app_label).delete()

        if verbosity > 1:
            self.stdout.write('Trying to delete ContentTypes\n')

        #deleting the ContentType should delete the useless block config, search config, history lines etc...
        try:
            for ctype in ctypes:
                ctype.delete()
        except Exception as e:
            raise CommandError('There were errors when trying to delete a ContentType: aborting. (original error: %s)'
                               'Sadly you have to solve this problem manually before re-run this command.' % e
                              )

        #connection = connections[options.get('database')] TODO ?
        connection = connections[DEFAULT_DB_ALIAS]

        if verbosity > 1:
            self.stdout.write('Trying to delete tables.\n')

        sql_commands = sql_delete(app, no_style(), connection)

        try:
            cursor = connection.cursor()

            for sql_command in sql_commands:
                cursor.execute(sql_command)
        except Exception as e:
            transaction.rollback_unless_managed()

            raise CommandError(u"""Error: tables of "%(app_name)s" couldn't be dropped."""
                               u"""Original error "%(error)s"."""
                               u"""Tried SQL commands: %(commands)s"""
                               u"""Sadly you have to SOLVE this problem MANUALLY, and THEN REMOVE "%(app_name)s" from your settings.""" % {
                                        'app_name': app_name,
                                        'error':    e,
                                        'commands': u'\n'.join(sql_commands).encode('utf-8')
                                    }
                               )

        transaction.commit_unless_managed()

        self.stdout.write('Uninstall is OK.\n'
                          'You should now remove "%s" from your settings.\n' % app_name
                         )
