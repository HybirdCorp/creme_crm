# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2021  Hybird
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

# NB: works with factory_boy-3.2.0  TODO: in requirements ?

try:
    import factory
except ImportError:
    print('Please install the package "factory_boy".')
    exit()

import re
from contextlib import contextmanager
from functools import partial
from random import choice, random
from time import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections
from factory.django import DjangoModelFactory
from faker.config import AVAILABLE_LOCALES

# Move to creme_core.utils ? ---------------------------------------------------


@contextmanager
def print_time(name='TIME', mute=False):
    start = time()
    yield

    if not mute:
        print(name, time() - start)


# Move to creme_core.management.base ? -----------------------------------------
class ProgressBar:
    def __init__(self, max, stdout, length=80, char='='):
        self._stdout = stdout
        self._max = max
        self._value = 0
        self._length = length
        self._current_length = 0
        self._char = char

    def progress(self, incr=1):
        self._value += incr
        length = self._length

        new_length = (self._value * length) // self._max
        length_diff = new_length - self._current_length

        if length_diff:
            self._stdout.write(
                self._char * length_diff,
                ending='' if new_length != length else '\n',
            )
            self._stdout.flush()

        self._current_length = new_length

# ------------------------------------------------------------------------------


users: list = []


def get_user(entity):
    if not users:
        users.extend(get_user_model().objects.all())

        if not users:
            raise CommandError('No users in the DB')

    return choice(users)


def or_None(f):
    def _aux(*args, **kwargs):
        return f(*args, **kwargs) if random() > 0.9 else None

    return _aux


def or_blank(f):
    def _aux(*args, **kwargs):
        return f(*args, **kwargs) if random() > 0.9 else ''

    return _aux


def get_best_locale(language_code=None):
    def _get_best_prefixed_locale(prefix):
        prefixed_locales = {
            locale
            for locale in AVAILABLE_LOCALES
            if locale.startswith(prefix)
        }

        if prefixed_locales:
            best_locale = f'{prefix}_{prefix.upper()}'
            if best_locale in AVAILABLE_LOCALES:
                return best_locale

            return next(iter(prefixed_locales))

    language_code = language_code or settings.LANGUAGE_CODE

    assert language_code

    if '_' in language_code:
        if language_code in AVAILABLE_LOCALES:
            return language_code

        return _get_best_prefixed_locale(language_code.split('_', 1)[0])

    return _get_best_prefixed_locale(language_code)


# Factories => move to apps ----------------------------------------------------

def _get_contact_n_factory(locale):
    from creme.persons import get_contact_model

    Contact = get_contact_model()

    build_email_domain = partial(
        factory.Faker('free_email_domain', locale=locale).evaluate, step=None,
    )

    def build_email(contact):
        domain = build_email_domain(contact, extra={'locale': locale})
        return f'{contact.first_name}.{contact.last_name}@{domain}'.lower()

    class ContactFactory(DjangoModelFactory):
        class Meta:
            model = Contact

        user = factory.LazyAttribute(get_user)
        first_name = factory.Faker('first_name', locale=locale)
        last_name = factory.Faker('last_name', locale=locale)
        email = factory.LazyAttribute(or_blank(build_email))

    return Contact, ContactFactory


def _get_organisation_n_factory(locale):
    from creme.persons import get_organisation_model

    Organisation = get_organisation_model()

    build_email_domain = partial(
        factory.Faker('free_email_domain', locale=locale).evaluate, step=None,
    )

    def build_email(orga):
        domain = build_email_domain(orga, extra={'locale': locale})
        return f'{orga.name}@{domain}'.lower()

    class OrganisationFactory(DjangoModelFactory):
        class Meta:
            model = Organisation

        user = factory.LazyAttribute(get_user)
        name = factory.Faker('company', locale=locale)
        email = factory.LazyAttribute(or_blank(build_email))

    return Organisation, OrganisationFactory


# Optimizers -------------------------------------------------------------------

class BaseOptimizeContext:
    def __init__(self, cursor, verbosity, stdout):
        self.cursor = cursor
        self.verbosity = verbosity
        self.stdout = stdout

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class OptimizeMySQLContext(BaseOptimizeContext):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.engine = None
        self.flush_policy = None

    def __enter__(self):
        cursor = self.cursor
        cursor.execute("SHOW VARIABLES LIKE 'default_storage_engine'")
        self.engine = engine = cursor.fetchall()[0][1]

        if engine == 'InnoDB':
            cursor.execute("SHOW VARIABLES LIKE 'innodb_flush_log_at_trx_commit'")
            self.flush_policy = flush_policy = cursor.fetchall()[0][1]

            if flush_policy in {'1', '2'}:
                sql_cmd = 'SET GLOBAL innodb_flush_log_at_trx_commit=0'

                if self.verbosity:
                    self.stdout.write(f'Temporary optimization : {sql_cmd}')

                cursor.execute(sql_cmd)
        else:
            # TODO: manage other engine
            if self.verbosity:
                self.stdout.write(
                    f'Unknown engine "{engine}" : no optimisation available.'
                )

    def __exit__(self, exc_type, exc_value, traceback):
        cursor = self.cursor

        if self.engine == 'InnoDB':
            if self.flush_policy in {'1', '2'}:
                cursor.execute(
                    f'SET GLOBAL innodb_flush_log_at_trx_commit={self.flush_policy}'
                )
        # else: # TODO: manage other engine


class OptimizePGSQLContext(BaseOptimizeContext):
    def __enter__(self):
        cursor = self.cursor

        # synchronous_commit -------
        cursor.execute('SHOW synchronous_commit;')

        if cursor.fetchall()[0][0] == 'on':
            sql_cmd = 'SET synchronous_commit=off;'

            if self.verbosity:
                self.stdout.write(f'Temporary optimization : {sql_cmd}')

            cursor.execute(sql_cmd)

        # wal_writer_delay -------
        cursor.execute('SHOW wal_writer_delay;')
        delay = cursor.fetchall()[0][0]
        match = re.match(r'^(?P<value>\d+)(?P<unit>(ms|s)+)$', delay)

        if match is None:
            print(f'DEBUG: invalid delay "{delay}" ?!')
        else:
            value = int(match['value'])

            if match['unit'] == 's':
                value *= 1000

            if value < 1000:
                print(
                    'HINT: you could try the following optimisation: '
                    '"ALTER SYSTEM SET wal_writer_delay=1000;"'
                )


# Command ----------------------------------------------------------------------

class Command(BaseCommand):
    help = 'Create a lot of fake entities in order to test performances.'
    leave_locale_alone = True
    requires_migrations_checks = True

    TYPES = {
        'contact':      _get_contact_n_factory,
        'organisation': _get_organisation_n_factory,
    }

    SQL_OPTIMISERS = {
        'django.db.backends.mysql': OptimizeMySQLContext,
        'django.db.backends.postgresql': OptimizePGSQLContext,
        # TODO: other DBRMS ?
    }

    def add_arguments(self, parser):
        add_argument = parser.add_argument
        add_argument(
            '-n', '--number',
            action='store', dest='number', type=int, default=100,
            help='How many entities are created. [default: %(default)s]',
        )
        add_argument(
            '-t', '--type',
            action='store', dest='type', default='contact',
            help='What type of entities are created. [default: %(default)s]',
        )
        add_argument(
            '-l', '--list',
            action='store_true', dest='list_types', default=False,
            help='List the available type of entities',
        )
        add_argument(
            '-c', '--language',
            action='store', dest='language_code', default='',
            help='Locale used for random data. [default: see settings.LANGUAGE_CODE]',
        )

    def handle(self, *args, **options):
        get_opt = options.get

        if get_opt('list_types'):
            self.stdout.write('\n'.join(f' - {m}' for m in self.TYPES))
            return

        e_type = get_opt('type')

        try:
            _get_model_n_factory = self.TYPES[e_type]
        except KeyError:
            self.stderr.write(
                f'"{e_type}" is not a valid type ; use the -l option to get the valid types.'
            )
            return

        locale = get_best_locale(get_opt('language_code'))

        verbosity = get_opt('verbosity')
        number = get_opt('number')  # TODO: min ? max ?

        entity_model, entity_factory = _get_model_n_factory(locale)
        verbose_name = entity_model._meta.verbose_name_plural

        cursor = connections[DEFAULT_DB_ALIAS].cursor()

        db_settings = settings.DATABASES['default']
        # TODO: add an argument to avoid optimisations ?
        optimiser_class = self.SQL_OPTIMISERS.get(
            db_settings['ENGINE'], BaseOptimizeContext,
        )

        if verbosity:
            if db_settings['CONN_MAX_AGE'] != 0:
                self.stdout.write(
                    # 'You can try to set "CONN_MAX_AGE = None" in your '
                    # 'settings.py to improve the performances.'
                    'You can try to set <CONN_MAX_AGE": None> in your '
                    'settings.py => DATABASES["default"] to improve the performances.'
                )

            self.stdout.write(f'Locale: "{locale}" ')
            self.stdout.write(f'Original "{verbose_name}" count: {entity_model.objects.count()}')

        # todo: only count queries, to reduce memory usage
        # from creme.creme_core.utils.profiling import CaptureQueriesContext
        # context = CaptureQueriesContext()
        #
        # with context:
        #     entity_factory.create_batch(number)

        create = entity_factory.create
        progress = ProgressBar(
            max=number, stdout=self.stdout,
        ).progress if verbosity else lambda: None

        # with print_time(mute=not verbosity):
        with optimiser_class(cursor, verbosity, self.stdout):
            for _ in range(number):
                create()
                progress()

        if verbosity:
            # self.stdout.write('Queries count: %s' % len(context.captured_queries))
            # self.stdout.write('Queries: %s' % context.captured_queries)
            self.stdout.write(f'New "{verbose_name}" count: {entity_model.objects.count()}')
