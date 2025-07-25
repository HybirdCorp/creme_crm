from functools import partial

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import DEFAULT_DB_ALIAS, connections

from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.models import (
    CremeEntity,
    FakeCivility,
    FakeContact,
    FakeDocument,
    FakeFolder,
    FakeOrganisation,
    FakePosition,
    FakeSector,
    Language,
    Relation,
)
from creme.creme_core.utils.db import (
    PreFetcher,
    build_columns_key,
    get_indexed_ordering,
    get_indexes_columns,
    populate_related,
)

from ..base import CremeTestCase


class DBTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # NB: We build an index, so it is not declared in the model's Meta
        #     => functions have to make introspection on the DB server.
        connection = connections[DEFAULT_DB_ALIAS]
        vendor = connection.vendor

        if vendor == 'mysql':
            sql = (
                "ALTER TABLE `creme_core_fakecontact` "
                "ADD INDEX `DBTestCase_index` (`birthday` ASC, `cremeentity_ptr_id` ASC);"
            )
        elif vendor == 'postgresql':
            sql = (
                "CREATE INDEX DBTestCase_index "
                "ON creme_core_fakecontact (birthday ASC NULLS FIRST, cremeentity_ptr_id ASC);"
            )
        elif vendor == 'sqlite':
            sql = (
                'CREATE INDEX "DBTestCase_index" '
                'ON creme_core_fakecontact (birthday ASC, cremeentity_ptr_id ASC);'
            )
        else:
            raise Exception(f'This DBMS is not managed: {vendor}')

        connection.cursor().execute(sql)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

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
        expected = {
            ('address_id',),
            ('sector_id',),
            ('legal_form_id',),
            ('image_id',),
            ('name', 'cremeentity_ptr_id'),
        }

        if is_my_sql:
            expected.add(('cremeentity_ptr_id',))

        self.assertSetEqual(
            expected,
            {tuple(cols) for cols in get_indexes_columns(FakeOrganisation)},
        )

        # FakeContact -------------------------
        expected = {
            ('position_id',),
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

        self.assertSetEqual(
            expected,
            {tuple(cols) for cols in get_indexes_columns(FakeContact)},
        )

    def test_buildcolumns_key(self):
        self.assertEqual(
            '#civility_id#',
            build_columns_key(('civility_id',))
        )
        self.assertEqual(
            '#last_name##first_name#',
            build_columns_key(('last_name', 'first_name')),
        )

    def test_indexed_ordering__organisation(self):
        self.assertIn(
            ['name', 'cremeentity_ptr'],
            [index.fields for index in FakeOrganisation._meta.indexes],
        )

        self.assertIsNone(get_indexed_ordering(FakeOrganisation, ['phone']))

        self.assertEqual(
            ('sector_id',),
            get_indexed_ordering(FakeOrganisation, ['sector_id']),
        )

        # TODO: ?
        # self.assertEqual(('sector',),
        #                  get_best_ordering(FakeOrganisation, ['sector_id'])
        #                 )

        self.assertEqual(
            ('name', 'cremeentity_ptr_id'),
            get_indexed_ordering(FakeOrganisation, ['name']),
        )

        # Order is important
        self.assertEqual(
            ('name', 'cremeentity_ptr_id'),
            get_indexed_ordering(FakeOrganisation, ['name', 'cremeentity_ptr_id'])
        )

        self.assertIsNone(
            get_indexed_ordering(FakeOrganisation, ['cremeentity_ptr_id', 'name'])
        )
        # TODO: M2M ?

    def test_indexed_ordering__contact(self):
        self.assertIn(
            ['last_name', 'first_name', 'cremeentity_ptr'],
            [index.fields for index in FakeContact._meta.indexes],
        )

        self.assertIsNone(get_indexed_ordering(FakeContact, ['phone']))
        self.assertIsNone(get_indexed_ordering(FakeContact, ['phone', 'email']))

        expected = ('last_name', 'first_name', 'cremeentity_ptr_id')
        self.assertEqual(
            expected, get_indexed_ordering(FakeContact, ['last_name']),
        )
        self.assertEqual(
            expected, get_indexed_ordering(FakeContact, ['last_name', 'first_name']),
        )
        self.assertEqual(
            expected,
            get_indexed_ordering(
                FakeContact, ['last_name', 'first_name', 'cremeentity_ptr_id'],
            )
        )

        self.assertIsNone(
            get_indexed_ordering(FakeContact, ['first_name', 'last_name'])
        )

    def test_indexed_ordering__desc(self):
        "DESC order => inverted index."
        expected = ('-name', '-cremeentity_ptr_id')
        self.assertEqual(
            expected,
            get_indexed_ordering(FakeOrganisation, ['-name']),
        )
        self.assertEqual(
            expected,
            get_indexed_ordering(
                FakeOrganisation, ['-name', '-cremeentity_ptr_id'],
            )
        )

    def test_indexed_ordering__blurred_query(self):
        expected = ('last_name', 'first_name', 'cremeentity_ptr_id')
        self.assertEqual(
            expected,
            get_indexed_ordering(
                FakeContact, ['last_name', '*', 'cremeentity_ptr_id'],
            ),
        )
        self.assertEqual(
            expected,
            get_indexed_ordering(
                FakeContact, ['*', 'first_name', 'cremeentity_ptr_id']
            ),
        )
        self.assertEqual(
            expected,
            get_indexed_ordering(FakeContact, ['last_name', 'first_name', '*']),
        )

        self.assertEqual(
            expected,
            get_indexed_ordering(
                FakeContact, ['last_name', 'first_name', '*', 'cremeentity_ptr_id'],
            )
        )
        self.assertEqual(
            expected,
            get_indexed_ordering(FakeContact, ['*', 'first_name', '*']),
        )
        self.assertEqual(
            expected,
            get_indexed_ordering(
                FakeContact, ['*', 'first_name', '*', 'cremeentity_ptr_id'],
            )
        )

        self.assertIsNone(
            get_indexed_ordering(FakeContact, ['last_name', '*', 'phone']),
        )

    def test_indexed_ordering__blurred_query_n_desc(self):
        "Blurred query + other model + DESC."
        self.assertEqual(
            ('name', 'cremeentity_ptr_id'),
            get_indexed_ordering(FakeOrganisation, ['name', '*']),
        )
        self.assertEqual(
            ('-name', '-cremeentity_ptr_id'),
            get_indexed_ordering(FakeOrganisation, ['-name', '*']),
        )

        self.assertEqual(
            ('-last_name', '-first_name', '-cremeentity_ptr_id'),
            get_indexed_ordering(
                FakeContact,
                ['-last_name', '-first_name', '*', '-cremeentity_ptr_id'],
            )
        )

    def test_indexed_ordering__wildcard_error(self):
        "Avoid successive wildcards."
        with self.assertRaises(ValueError):
            get_indexed_ordering(FakeContact, ['*', '*', 'cremeentity_ptr_id'])

        with self.assertRaises(ValueError):
            get_indexed_ordering(
                FakeContact, ['last_name', '*', '*', 'cremeentity_ptr_id'],
            )

    def _create_contacts(self, user=None):
        self.sector1, self.sector2 = FakeSector.objects.all()[:2]
        self.civ1, self.civ2 = FakeCivility.objects.all()[:2]

        create_contact = partial(
            FakeContact.objects.create, user=user or self.get_root_user(), last_name='Simpson',
        )
        contacts = [
            create_contact(first_name='Homer', sector=self.sector1),
            create_contact(first_name='Marge', sector=self.sector2, civility=self.civ1),
            create_contact(first_name='Bart'),
            create_contact(first_name='Lisa', civility=self.civ2),
        ]

        return [self.refresh(c) for c in contacts]

    def test_populate_related__one_field(self):
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

    def test_populate_related__two_fields(self):
        "Two fields."
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

    def test_populate_related__cache(self):
        "Do not retrieve already cached values."
        contacts = self._create_contacts()
        contacts[0].sector  # NOQA
        contacts[1].sector  # NOQA

        with self.assertNumQueries(1):
            populate_related(contacts, ['sector', 'civility'])

    def test_populate_related__partially_cached(self):
        contacts = self._create_contacts()
        contacts[0].sector  # NOQA
        # __ = contacts[1].sector # Not Cached

        with self.assertNumQueries(2):
            populate_related(contacts, ['sector', 'civility'])

    def test_populate_related__group_queries(self):
        "Two fields related to the same model."
        user = self.get_root_user()

        create_contact = partial(
            FakeContact.objects.create, user=user, last_name='Simpson',
        )
        marge = create_contact(first_name='Marge')
        homer = create_contact(first_name='Homer')

        rel = Relation.objects.create(
            user=user, type_id=REL_SUB_HAS, subject_entity=marge, object_entity=homer,
        )
        rel = self.refresh(rel)

        # NB: we fill the ContentType cache to not disturb assertNumQueries()
        ContentType.objects.get_for_model(CremeEntity)

        with self.assertNumQueries(1):
            populate_related([rel], ['subject_entity', 'object_entity'])

        with self.assertNumQueries(0):
            e1 = rel.subject_entity

        self.assertEqual(marge, e1.get_real_entity())

    def test_populate_related__depth_one(self):
        "depth = 1."
        contacts = self._create_contacts()

        with self.assertNumQueries(1):
            populate_related(contacts, ['sector__title'])

        with self.assertNumQueries(0):
            s1 = contacts[0].sector
        self.assertEqual(self.sector1, s1)

    def test_populate_related__depth_one_n_fk(self):
        "Field with depth=1 is a FK."
        user = self.get_root_user()

        create_folder = partial(FakeFolder.objects.create, user=user)
        folder1  = create_folder(title='Maps')
        folder11 = create_folder(title='Earth maps', parent=folder1)
        folder12 = create_folder(title='Mars maps',  parent=folder1)
        folder2  = create_folder(title='Blue prints')

        create_doc = partial(FakeDocument.objects.create, user=user)
        docs = [
            create_doc(title='Japan map part#1',   linked_folder=folder11),
            create_doc(title='Japan map part#2',   linked_folder=folder11),
            create_doc(title='Mars city 1',        linked_folder=folder12),
            create_doc(title='Swordfish',          linked_folder=folder2),
        ]
        docs = [self.refresh(c) for c in docs]

        with self.assertNumQueries(2):
            populate_related(docs, ['linked_folder__parent', 'title'])

        with self.assertNumQueries(0):
            f11 = docs[0].linked_folder
        self.assertEqual(folder11, f11)

        with self.assertNumQueries(0):
            f1 = f11.parent
        self.assertEqual(folder1, f1)

        with self.assertNumQueries(0):
            f2 = docs[3].linked_folder
        self.assertEqual(folder2, f2)

        with self.assertNumQueries(0):
            f_null = f2.parent
        self.assertIsNone(f_null)

    def test_populate_related__different_models(self):
        "Two fields + depth > 1  => instances of level 2 have different models."
        user1 = self.get_root_user()
        role = self.get_regular_role()
        user2 = self.create_user(role=role)

        create_folder = partial(FakeFolder.objects.create, user=user1)
        folder1 = create_folder(title='Maps')
        folder11 = create_folder(title='Earth maps', parent=folder1)
        folder2 = create_folder(title='Blue prints')

        create_doc = partial(FakeDocument.objects.create, user=user1)
        docs = [
            create_doc(title='Japan map part#1', linked_folder=folder1),
            create_doc(title='Mars city 1',      linked_folder=folder11),
            create_doc(title='Swordfish',        linked_folder=folder2, user=user2),
        ]
        docs = [self.refresh(c) for c in docs]

        # 3 queries:
        #   1 for fhe folders of the first level.
        #   0 for fhe folders of the second level, because already in the cache.
        #   1 for the users.
        #   1 for the roles.
        with self.assertNumQueries(3):
            populate_related(docs, ['linked_folder__parent', 'user__role'])

        # Folders
        with self.assertNumQueries(0):
            f1 = docs[0].linked_folder
        self.assertEqual(folder1, f1)

        with self.assertNumQueries(0):
            f11 = docs[1].linked_folder
        self.assertEqual(folder11, f11)

        with self.assertNumQueries(0):
            f1 = f11.parent
        self.assertEqual(folder1, f1)

        with self.assertNumQueries(0):
            f2 = docs[2].linked_folder
        self.assertEqual(folder2, f2)

        # Users
        with self.assertNumQueries(0):
            u1 = docs[0].user
        self.assertEqual(user1, u1)

        with self.assertNumQueries(0):
            u2 = docs[2].user
        self.assertEqual(user2, u2)

        with self.assertNumQueries(0):
            role2 = u2.role
        self.assertEqual(role, role2)

    def test_populate_related__level_two_is_cached(self):
        "Already cached field (level 2)."
        user1 = self.get_root_user()
        user2 = self.create_user(role=self.get_regular_role())

        create_contact = partial(
            FakeContact.objects.create, user=user1, last_name='Simpson',
        )
        contacts = [
            create_contact(first_name='Homer'),
            create_contact(first_name='Lisa', user=user2),
        ]

        contacts = [self.refresh(c) for c in contacts]
        _ = contacts[1].user  # 'user' is cached

        with self.assertNumQueries(2):
            populate_related(contacts, ['user__role__name'])

    def test_populate_related__m2m(self):
        user = self.get_root_user()
        l1, l2, l3 = Language.objects.all()[:3]

        create_contact = partial(FakeContact.objects.create, user=user, last_name='Simpson')
        lisa = create_contact(first_name='Lisa')
        maggie = create_contact(first_name='Marguerite')
        lisa.languages.set([l1, l2])
        maggie.languages.set([l1, l3])

        lisa = self.refresh(lisa)
        maggie = self.refresh(maggie)

        with self.assertNumQueries(1):
            populate_related([lisa, maggie], ['languages'])

        with self.assertNumQueries(0):
            self.assertCountEqual([l1, l2], lisa.languages.all())

        with self.assertNumQueries(0):
            self.assertCountEqual([l1, l3], maggie.languages.all())

    def test_prefetcher(self):
        sector1, sector2, sector3 = FakeSector.objects.all()[:3]

        fetcher = PreFetcher()

        with self.assertRaises(RuntimeError):
            fetcher.get(FakeSector, sector1.id)

        fetcher.order(FakeSector, [sector1.id, sector2.id])

        with self.assertNumQueries(1):
            fetcher.proceed()

        with self.assertNumQueries(0):
            retrieved_sector1 = fetcher.get(FakeSector, sector1.id)
        self.assertEqual(sector1, retrieved_sector1)

        with self.assertNumQueries(0):
            retrieved_sector2 = fetcher.get(FakeSector, sector2.id)
        self.assertEqual(sector2, retrieved_sector2)

        self.assertIsNone(fetcher.get(FakeSector, sector3.id))

        with self.assertRaises(KeyError):
            fetcher.get(FakePosition, 123)

        with self.assertRaises(RuntimeError):
            fetcher.order(FakePosition, [123])

        with self.assertRaises(RuntimeError):
            fetcher.proceed()

    def test_prefetcher__same_model(self):
        "Several calls to order() with the same model."
        sector1, sector2, sector3 = FakeSector.objects.all()[:3]

        fetcher = PreFetcher().order(
            FakeSector, [sector1.id],
        ).order(
            FakeSector, [sector3.id],
        )

        with self.assertNumQueries(1):
            fetcher.proceed()

        with self.assertNumQueries(0):
            retrieved_sector1 = fetcher.get(FakeSector, sector1.id)
        self.assertEqual(sector1, retrieved_sector1)

        with self.assertNumQueries(0):
            retrieved_sector3 = fetcher.get(FakeSector, sector3.id)
        self.assertEqual(sector3, retrieved_sector3)

        self.assertIsNone(fetcher.get(FakeSector, sector2.id))

    def test_prefetcher__different_models(self):
        "Several calls to order() with different models."
        sector1, sector2 = FakeSector.objects.all()[:2]
        position1, position2 = FakePosition.objects.all()[:2]

        fetcher = PreFetcher().order(
            FakeSector, [sector1.id, sector2.id],
        ).order(
            FakePosition, [position2.id, position1.id],
        )

        with self.assertNumQueries(2):
            fetcher.proceed()

        with self.assertNumQueries(0):
            retrieved_sector1 = fetcher.get(FakeSector, sector1.id)
        self.assertEqual(sector1, retrieved_sector1)

        with self.assertNumQueries(0):
            retrieved_position1 = fetcher.get(FakePosition, position1.id)
        self.assertEqual(position1, retrieved_position1)
