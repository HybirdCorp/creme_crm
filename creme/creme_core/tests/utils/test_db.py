# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.db import connections, DEFAULT_DB_ALIAS

    from ..base import CremeTestCase
    from ..fake_models import (FakeContact, FakeOrganisation, FakeSector,
            FakeCivility, FakeFolder, FakeDocument)
    from creme.creme_core.models import Relation, CremeEntity
    from creme.creme_core.constants import REL_SUB_HAS
    from creme.creme_core.utils.db import (get_indexes_columns, get_indexed_ordering,
           build_columns_key, populate_related, reorder_instances)
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class DBTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        # CremeTestCase.setUpClass()
        super(DBTestCase, cls).setUpClass()
        # cls.populate('creme_core')

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
        # CremeTestCase.tearDownClass()
        super(DBTestCase, cls).tearDownClass()

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

    def _create_contacts(self):
        self.sector1, self.sector2 = FakeSector.objects.all()[:2]
        self.civ1, self.civ2 = FakeCivility.objects.all()[:2]

        create_contact = partial(FakeContact.objects.create, user=self.user, last_name='Simpson')
        contacts = [create_contact(first_name='Homer', sector=self.sector1),
                    create_contact(first_name='Marge', sector=self.sector2, civility=self.civ1),
                    create_contact(first_name='Bart'),
                    create_contact(first_name='Lisa', civility=self.civ2),
                   ]

        return [self.refresh(c) for c in contacts]

    def test_populate_related01(self):
        "One field"
        self.login()

        with self.assertNoException():
            populate_related([], ['sector'])

        contacts = self._create_contacts()

        with self.assertNumQueries(1):
            populate_related(contacts, ['sector'])

        with self.assertNumQueries(0):
            s1 = contacts[0].sector
        self.assertEqual(self.sector1, s1)

        with self.assertNumQueries(0):
            s2 = contacts[1].sector
        self.assertEqual(self.sector2, s2)

        self.assertIsNone(contacts[2].sector)

    def test_populate_related02(self):
        "Two fields"
        self.login()
        contacts = self._create_contacts()

        with self.assertNumQueries(2):
            populate_related(contacts, ['sector', 'civility', 'last_name'])

        with self.assertNumQueries(0):
            s1 = contacts[0].sector
        self.assertEqual(self.sector1, s1)

        with self.assertNumQueries(0):
            c1 = contacts[1].civility
        self.assertEqual(self.civ1, c1)

        self.assertIsNone(contacts[2].civility)

    def test_populate_related03(self):
        "Do not retrieve already cached values"
        self.login()

        contacts = self._create_contacts()
        contacts[0].sector
        contacts[1].sector

        with self.assertNumQueries(1):
            populate_related(contacts, ['sector', 'civility'])

    def test_populate_related04(self):
        "Partially cached"
        self.login()

        contacts = self._create_contacts()
        contacts[0].sector
        # contacts[1].sector # Not Cached

        with self.assertNumQueries(2):
            populate_related(contacts, ['sector', 'civility'])

    def test_populate_related05(self):
        "Two fields related to the same model"
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user, last_name='Simpson')
        marge = create_contact(first_name='Marge')
        homer = create_contact(first_name='Homer')

        rel = Relation.objects.create(user=user, type_id=REL_SUB_HAS,
                                      subject_entity=marge,
                                      object_entity=homer,
                                     )
        rel = self.refresh(rel)

        # NB: we fill the ContentType cache to not disturb assertNumQueries()
        ContentType.objects.get_for_model(CremeEntity)

        with self.assertNumQueries(1):
            populate_related([rel], ['subject_entity', 'object_entity'])

        with self.assertNumQueries(0):
             e1 = rel.subject_entity

        self.assertEqual(marge, e1.get_real_entity())

    def test_populate_related06(self):
        "depth = 1"
        self.login()

        contacts = self._create_contacts()

        with self.assertNumQueries(1):
            populate_related(contacts, ['sector__title'])

        with self.assertNumQueries(0):
            s1 = contacts[0].sector
        self.assertEqual(self.sector1, s1)

    def test_populate_related07(self):
        "Field with depth=1 is a FK"
        user = self.login()

        create_folder = partial(FakeFolder.objects.create, user=user)
        folder1  = create_folder(title='Maps')
        folder11 = create_folder(title='Earth maps', parent=folder1)
        folder12 = create_folder(title='Mars maps', parent=folder1)
        folder2  = create_folder(title='Blue prints')

        create_doc = partial(FakeDocument.objects.create, user=user)
        docs = [create_doc(title='Japan map part#1',   folder=folder11),
                create_doc(title='Japan map part#2',   folder=folder11),
                create_doc(title='Mars city 1',        folder=folder12),
                create_doc(title='Swordfish',          folder=folder2),
               ]
        docs = [self.refresh(c) for c in docs]

        with self.assertNumQueries(2):
            populate_related(docs, ['folder__parent', 'title'])

        with self.assertNumQueries(0):
            f11 = docs[0].folder
        self.assertEqual(folder11, f11)

        with self.assertNumQueries(0):
            f1 = f11.parent
        self.assertEqual(folder1, f1)

        with self.assertNumQueries(0):
            f2 = docs[3].folder
        self.assertEqual(folder2, f2)

        with self.assertNumQueries(0):
            f_null = f2.parent
        self.assertIsNone(f_null)

    def test_populate_related08(self):
        "Two fields + depth > 1  => instances of level 2 have different models"
        user = self.login()
        user2 = self.other_user

        create_folder = partial(FakeFolder.objects.create, user=user)
        folder1 = create_folder(title='Maps')
        folder11 = create_folder(title='Earth maps', parent=folder1)
        folder2 = create_folder(title='Blue prints')

        create_doc = partial(FakeDocument.objects.create, user=user)
        docs = [create_doc(title='Japan map part#1',   folder=folder1),
                create_doc(title='Mars city 1',        folder=folder11),
                create_doc(title='Swordfish',          folder=folder2, user=user2),
               ]
        docs = [self.refresh(c) for c in docs]

        # 3 queries:
        #   1 for fhe folders of the first level.
        #   0 for fhe folders of the second level, because already in the cache.
        #   1 for the users.
        #   1 for the roles.
        with self.assertNumQueries(3):
            populate_related(docs, ['folder__parent', 'user__role'])

        # Folders
        with self.assertNumQueries(0):
            f1 = docs[0].folder
        self.assertEqual(folder1, f1)

        with self.assertNumQueries(0):
            f11 = docs[1].folder
        self.assertEqual(folder11, f11)

        with self.assertNumQueries(0):
            f1 = f11.parent
        self.assertEqual(folder1, f1)

        with self.assertNumQueries(0):
            f2 = docs[2].folder
        self.assertEqual(folder2, f2)

        # Users
        with self.assertNumQueries(0):
             u1 = docs[0].user
        self.assertEqual(user, u1)

        with self.assertNumQueries(0):
             u2 = docs[2].user
        self.assertEqual(user2, u2)

        with self.assertNumQueries(0):
             role = u2.role
        self.assertEqual(self.role, role)

    def test_populate_related09(self):
        "Already cached field (level 2)"
        user = self.login()
        user2 = self.other_user

        create_contact = partial(FakeContact.objects.create, user=user, last_name='Simpson')
        contacts = [create_contact(first_name='Homer'),
                    create_contact(first_name='Lisa', user=user2),
                   ]

        contacts = [self.refresh(c) for c in contacts]
        _ = contacts[1].user  # 'user' is cached

        with self.assertNumQueries(2):
            populate_related(contacts, ['user__role__name'])

    def test_reorder_instances01(self):
        "Order + 1"
        initial_count = FakeSector.objects.count()
        create_sector = FakeSector.objects.create
        s1 = create_sector(title='Toys')
        s2 = create_sector(title='Video games')

        reorder_instances(s1, initial_count + 2)
        self.assertEqual(initial_count + 2, self.refresh(s1).order)
        self.assertEqual(initial_count + 1, self.refresh(s2).order)

        with self.assertRaises(IndexError):
            reorder_instances(s1, initial_count + 3)

        with self.assertRaises(IndexError):
            reorder_instances(s1, 0)

    def test_reorder_instances02(self):
        "Order - 2"
        initial_count = FakeSector.objects.count()

        create_sector = FakeSector.objects.create
        s1 = create_sector(title='Toys')
        s2 = create_sector(title='Video games')
        s3 = create_sector(title='Anime')

        reorder_instances(s3, initial_count + 1)
        self.assertEqual(initial_count + 1, self.refresh(s3).order)
        self.assertEqual(initial_count + 2, self.refresh(s1).order)
        self.assertEqual(initial_count + 3, self.refresh(s2).order)

    def test_reorder_instances03(self):
        "Queryset parameter"
        create_sector = FakeSector.objects.create
        s0 = create_sector(title='Cars')
        s1 = create_sector(title='Games - Toys')
        s2 = create_sector(title='Games - Video games')
        s3 = create_sector(title='Games - Dolls')
        s4 = create_sector(title='Food - Bakery')

        order0 = s0.order
        order4 = s4.order

        reorder_instances(moved_instance=s1, new_order=3,
                          queryset=FakeSector.objects.filter(title__startswith='Games - '),
                         )
        self.assertEqual(1, self.refresh(s2).order)
        self.assertEqual(2, self.refresh(s3).order)
        self.assertEqual(3, self.refresh(s1).order)

        self.assertEqual(order0, self.refresh(s0).order)
        self.assertEqual(order4, self.refresh(s4).order)

    def test_reorder_instances04(self):
        "Orders not contiguous => 1-Only indices are used  2-Orders are remapped"
        create_sector = FakeSector.objects.create
        s1 = create_sector(title='Games - Toys')
        s2 = create_sector(title='Games - Video games', order=s1.order + 2)
        s3 = create_sector(title='Games - Dolls',       order=s2.order + 2)
        s4 = create_sector(title='Games - Bikes',       order=s3.order + 2)
        s5 = create_sector(title='Games - Costumes',    order=s4.order + 2)
        self.assertEqual(2, s3.order - s2.order)

        reorder_instances(moved_instance=s2, new_order=4,
                          queryset=FakeSector.objects.filter(title__startswith='Games - '),
                         )
        self.assertEqual(1, self.refresh(s1).order)
        self.assertEqual(2, self.refresh(s3).order)
        self.assertEqual(3, self.refresh(s4).order)
        self.assertEqual(4, self.refresh(s2).order)
        self.assertEqual(5, self.refresh(s5).order)
