# -*- coding: utf-8 -*-

try:
    from django.conf import settings
    from django.db import connections, DEFAULT_DB_ALIAS

    from ..base import CremeTestCase
    from ..fake_models import FakeContact, FakeOrganisation
    from creme.creme_core.utils.db import (get_indexes_columns, get_keyed_indexes_columns, \
                                           get_indexed_ordering, build_columns_key)
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class DBTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()

        # NB: We build an index, so it is not declared in the model's Meta
        #     => functions have to make introspection on the DB server.
        connection = connections[DEFAULT_DB_ALIAS]
        vendor = connection.vendor

        if vendor == 'mysql':
            sql = "ALTER TABLE `creme_core_fakecontact` " \
                  "ADD INDEX `DBTestCase_index` (`birthday` ASC, `cremeentity_ptr_id` ASC);"
        elif vendor == 'postgresql':
            sql = "CREATE INDEX DBTestCase_index " \
                  "ON creme_core_fakecontact (birthday ASC NULLS FIRST, cremeentity_ptr_id ASC);"
        elif vendor == 'sqlite':
            sql = 'CREATE INDEX "DBTestCase_index" ' \
                  'ON creme_core_fakecontact (birthday ASC, cremeentity_ptr_id ASC);'
        else:
            raise Exception('This DBMS is not managed: %s' % vendor)

        connection.cursor().execute(sql)

    @classmethod
    def tearDownClass(cls):
        CremeTestCase.tearDownClass()

        connection = connections[DEFAULT_DB_ALIAS]
        vendor = connection.vendor
        sql = ''

        if vendor == 'mysql':
            sql = "DROP INDEX DBTestCase_index ON creme_core_fakecontact"
        elif vendor == 'postgresql':
            # sql = "DROP INDEX DBTestCase_index"
            pass
        elif vendor == 'sqlite':
            # sql = "DROP INDEX DBTestCase_index"
            pass
        else:
            raise Exception('This DBMS is not managed')

        if sql:
            connection.cursor().execute(sql)

    def test_get_indexes_columns(self):
        is_my_sql = (settings.DATABASES['default']['ENGINE'] == 'django.db.backends.mysql')

        # FakeOrganisation --------------------
        expected = {('address_id',),
                    ('sector_id',),
                    ('legal_form_id',),
                    ('image_id',),
                    ('name', 'cremeentity_ptr_id'),
                   }

        if is_my_sql:
            expected.add(('cremeentity_ptr_id',))

        self.assertEqual(expected,
                         {tuple(cols) for cols in get_indexes_columns(FakeOrganisation)}
                        )

        # FakeContact -------------------------
        expected = {('position_id',),
                    ('civility_id',),
                    ('is_user_id',),
                    ('sector_id',),
                    ('address_id',),
                    ('image_id',),
                    ('last_name', 'first_name', 'cremeentity_ptr_id'),
                    ('birthday', 'cremeentity_ptr_id'),  # Added by setUpClass()
                   }

        if is_my_sql:
            expected.add(('cremeentity_ptr_id',))

        self.assertEqual(expected,
                         {tuple(cols) for cols in get_indexes_columns(FakeContact)}
                        )

    def test_buildcolumns_key(self):
        self.assertEqual('#civility_id#',
                         build_columns_key(('civility_id',))
                        )
        self.assertEqual('#last_name##first_name#',
                         build_columns_key(('last_name', 'first_name'))
                        )

    def test_indexed_ordering01(self):
        "FakeOrganisation"
        self.assertEqual((('name', 'cremeentity_ptr'),),
                         FakeOrganisation._meta.index_together
                        )

        self.assertIsNone(get_indexed_ordering(FakeOrganisation, ['phone']))

        self.assertEqual(('sector_id',),
                         get_indexed_ordering(FakeOrganisation, ['sector_id'])
                        )

        # TODO: ?
        # self.assertEqual(('sector',),
        #                  get_best_ordering(FakeOrganisation, ['sector_id'])
        #                 )

        self.assertEqual(('name', 'cremeentity_ptr_id'),
                         get_indexed_ordering(FakeOrganisation, ['name'])
                        )

        # Order is important
        self.assertEqual(('name', 'cremeentity_ptr_id'),
                         get_indexed_ordering(FakeOrganisation, ['name', 'cremeentity_ptr_id'])
                        )

        self.assertIsNone(get_indexed_ordering(FakeOrganisation, ['cremeentity_ptr_id', 'name']))
        # TODO: M2M ?

    def test_indexed_ordering02(self):
        "FakeContact"
        self.assertEqual((('last_name', 'first_name', 'cremeentity_ptr'),),
                         FakeContact._meta.index_together
                        )

        self.assertIsNone(get_indexed_ordering(FakeContact, ['phone']))
        self.assertIsNone(get_indexed_ordering(FakeContact, ['phone', 'email']))

        expected = ('last_name', 'first_name', 'cremeentity_ptr_id')
        self.assertEqual(expected, get_indexed_ordering(FakeContact, ['last_name']))
        self.assertEqual(expected, get_indexed_ordering(FakeContact, ['last_name', 'first_name']))
        self.assertEqual(expected, get_indexed_ordering(FakeContact, ['last_name', 'first_name', 'cremeentity_ptr_id']))

        self.assertIsNone(get_indexed_ordering(FakeContact, ['first_name', 'last_name']))

    def test_indexed_ordering03(self):
        "DESC order => inverted index"
        expected = ('-name', '-cremeentity_ptr_id')
        self.assertEqual(expected,
                         get_indexed_ordering(FakeOrganisation, ['-name'])
                        )
        self.assertEqual(expected,
                         get_indexed_ordering(FakeOrganisation, ['-name', '-cremeentity_ptr_id'])
                        )

    def test_indexed_ordering04(self):
        "Blurred query"
        expected = ('last_name', 'first_name', 'cremeentity_ptr_id')
        self.assertEqual(expected, get_indexed_ordering(FakeContact, ['last_name', '*', 'cremeentity_ptr_id']))
        self.assertEqual(expected, get_indexed_ordering(FakeContact, ['*', 'first_name', 'cremeentity_ptr_id']))
        self.assertEqual(expected, get_indexed_ordering(FakeContact, ['last_name', 'first_name', '*']))

        self.assertEqual(expected, get_indexed_ordering(FakeContact, ['last_name', 'first_name', '*', 'cremeentity_ptr_id']))
        # self.assertEqual(expected, get_indexed_ordering(FakeContact, ['*', 'cremeentity_ptr_id']))  # Ambiguous
        self.assertEqual(expected, get_indexed_ordering(FakeContact, ['*', 'first_name', '*']))
        # self.assertEqual(expected, get_indexed_ordering(FakeContact, ['*', 'cremeentity_ptr_id', '*'])) # Ambiguous
        self.assertEqual(expected, get_indexed_ordering(FakeContact, ['*', 'first_name', '*', 'cremeentity_ptr_id']))

        self.assertIsNone(get_indexed_ordering(FakeContact, ['last_name', '*', 'phone']))

    def test_indexed_ordering05(self):
        "Blurred query + other model + DESC"
        self.assertEqual(('name', 'cremeentity_ptr_id'),
                         get_indexed_ordering(FakeOrganisation, ['name', '*'])
                        )
        self.assertEqual(('-name', '-cremeentity_ptr_id'),
                         get_indexed_ordering(FakeOrganisation, ['-name', '*'])
                        )

        self.assertEqual(('-last_name', '-first_name', '-cremeentity_ptr_id'),
                         get_indexed_ordering(FakeContact, ['-last_name', '-first_name', '*', '-cremeentity_ptr_id'])
                        )

    def test_indexed_ordering06(self):
        "Avoid successive wildcards"
        with self.assertRaises(ValueError):
            get_indexed_ordering(FakeContact, ['*', '*', 'cremeentity_ptr_id'])

        with self.assertRaises(ValueError):
            get_indexed_ordering(FakeContact, ['last_name', '*', '*', 'cremeentity_ptr_id'])
