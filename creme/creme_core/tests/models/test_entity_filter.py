# -*- coding: utf-8 -*-
from creme.creme_core.tests.fake_models import FakeDocument, FakeFolder

try:
    from datetime import date, timedelta
    from functools import partial
    from logging import info

    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth import get_user_model
    from django.db.models.query import QuerySet
    from django.utils.timezone import now

    from creme import __version__

    from ..base import CremeTestCase
    from ..fake_models import FakeContact, FakeCivility, FakeOrganisation, FakeImage
    from creme.creme_core.global_info import set_global_info
    from creme.creme_core.models import (CremeEntity, Language,
            Relation, RelationType, CremeProperty, CremePropertyType,
            CustomField, CustomFieldInteger, CustomFieldString, CustomFieldFloat,
            CustomFieldBoolean, CustomFieldDateTime, CustomFieldEnum, CustomFieldEnumValue,
            EntityFilter, EntityFilterCondition)
    from creme.creme_core.models.entity_filter import EntityFilterList
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class EntityFiltersTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super(EntityFiltersTestCase, cls).setUpClass()

        cls._excluded_ids = frozenset(CremeEntity.objects.values_list('id', flat=True))

    def setUp(self):
        self.login()

        create = partial(FakeContact.objects.create, user=self.user)

        self.civ_miss   = miss   = FakeCivility.objects.create(title='Miss')
        self.civ_mister = mister = FakeCivility.objects.create(title='Mister')

        self.contacts = {
            'spike':  create(first_name=u'Spike',  last_name=u'Spiegel',   civility=mister),
            'jet':    create(first_name=u'Jet',    last_name=u'Black',     civility=mister),
            'faye':   create(first_name=u'Faye',   last_name=u'Valentine', civility=miss,
                             description=u'Sexiest woman is the universe',
                            ),
            'ed':     create(first_name=u'Ed',     last_name=u'Wong', description=u''),
            'rei':    create(first_name=u'Rei',    last_name=u'Ayanami'),
            'misato': create(first_name=u'Misato', last_name=u'Katsuragi',
                             birthday=date(year=1986, month=12, day=8)
                            ),
            'asuka':  create(first_name=u'Asuka',  last_name=u'Langley',
                             birthday=date(year=2001, month=12, day=4)
                            ),
            'shinji': create(first_name=u'Shinji', last_name=u'Ikari',
                             birthday=date(year=2001, month=6, day=6)
                            ),
            'yui':    create(first_name=u'Yui',    last_name=u'Ikari'),
            'gendou': create(first_name=u'Gendô',  last_name=u'IKARI'),
            'genji':  create(first_name=u'Genji',  last_name=u'Ikaru'),
            'risato': create(first_name=u'Risato', last_name=u'Katsuragu'),
        }

        self.contact_ct = ContentType.objects.get_for_model(FakeContact)

    def assertExpectedFiltered(self, efilter, model, ids, case_insensitive=False, use_distinct=False):
        msg = '(NB: maybe you have case sensitive problems with your DB configuration).' if case_insensitive else ''

        from creme.creme_core.utils.profiling import CaptureQueriesContext
        context = CaptureQueriesContext()

        with context:
            filtered = list(efilter.filter(model.objects.exclude(id__in=self._excluded_ids)))

        self.assertEqual(len(ids), len(filtered), str(filtered) + msg)
        self.assertEqual(set(ids), {c.id for c in filtered})

        if use_distinct:
            for query_info in context.captured_queries:
                if 'DISTINCT' in query_info['sql']:
                    break
            else:
                self.fail('No DISTINCT found')

        else:
            for query_info in context.captured_queries:
                self.assertNotIn('DISTINCT', query_info['sql'])

    def _get_ikari_case_sensitive(self):
        ikaris = FakeContact.objects.filter(last_name__exact="Ikari")

        if len(ikaris) == 3:
            info('INFO: your DB is Case insentive')

        return [ikari.id for ikari in ikaris]

    def _list_contact_ids(self, *short_names, **kwargs):
        contacts = self.contacts

        if kwargs.get('exclude', False):
            excluded = frozenset(short_names)
            ids = [c.id for sn, c in contacts.iteritems() if sn not in excluded]
        else:
            ids = [contacts[sn].id for sn in short_names]

        return ids

    def test_create01(self):
        "Custom=False"
        pk = 'test-filter01'
        name = 'Ikari'
        model = FakeContact

        with self.assertRaises(ValueError):
            EntityFilter.create(pk, name, model)

        efilter = EntityFilter.create(pk, name, model,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                            model=FakeContact,
                                                            operator=EntityFilterCondition.EQUALS,
                                                            name='last_name', values=['Ikari'],
                                                           ),
                                                 ],
                                     )

        self.assertIsInstance(efilter, EntityFilter)
        self.assertEqual(pk,    efilter.id)
        self.assertEqual(name,  efilter.name)
        self.assertEqual(model, efilter.entity_type.model_class())
        self.assertIsNone(efilter.user)
        self.assertIs(efilter.use_or,     False)
        self.assertIs(efilter.is_custom,  False)
        self.assertIs(efilter.is_private, False)

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD, condition.type)
        self.assertEqual('last_name',                     condition.name)
        self.assertEqual({'operator': EntityFilterCondition.EQUALS, 'values': ['Ikari']},
                         condition.decoded_value
                        )

        self.assertTrue(efilter.entities_are_distinct)

    def test_create02(self):
        "A owner, custom filter"
        pk = 'test-filter_nerv'
        name = 'Nerv'
        model = FakeOrganisation
        user = self.user
        efilter = EntityFilter.create(pk, name, model, user=user, use_or=True,
                                      is_custom=True, is_private=True,
                                     )
        self.assertEqual(pk,    efilter.id)
        self.assertEqual(name,  efilter.name)
        self.assertEqual(model, efilter.entity_type.model_class())
        self.assertEqual(user,  efilter.user)
        self.assertTrue(efilter.use_or)
        self.assertTrue(efilter.is_custom)
        self.assertTrue(efilter.is_private)

        self.assertFalse(efilter.conditions.all())
        self.assertTrue(efilter.entities_are_distinct)

    def test_create03(self):
        "'admin' owner"
        efilter = EntityFilter.create('test-filter', 'Misato', FakeContact, user='admin', is_custom=True)
        owner = efilter.user
        self.assertTrue(owner.is_superuser)
        self.assertFalse(owner.is_staff)

    def test_create_subfilters_n_private(self):
        """Private sub-filters
            - must belong to the same user
            - OR to one one his teams
        """
        user = self.user
        other_user = self.other_user
        User = get_user_model()

        team = User.objects.create(username='TeamTitan', is_team=True)
        team.teammates = [user, other_user]

        other_team = User.objects.create(username='A-Team', is_team=True)
        other_team.teammates = [other_user]

        def create_subfilter(idx, owner):
            return EntityFilter.create('creme_core-subfilter%s' % idx, 'Misato', model=FakeContact,
                                       user=owner, is_private=True, is_custom=True,
                                       conditions=[EntityFilterCondition.build_4_field(
                                                        model=FakeContact,
                                                        operator=EntityFilterCondition.EQUALS,
                                                        name='first_name', values=['Misato'],
                                                    ),
                                                   ],
                                       )
        subfilter1 = create_subfilter(1, other_user)
        subfilter2 = create_subfilter(2, user)
        subfilter3 = create_subfilter(3, other_team)
        subfilter4 = create_subfilter(4, team)

        conds = [EntityFilterCondition.build_4_field(
                            model=FakeContact,
                            operator=EntityFilterCondition.EQUALS,
                            name='last_name', values=['Katsuragi'],
                        ),
                     ]

        with self.assertRaises(EntityFilter.PrivacyError):
            EntityFilter.create('creme_core-filter1', 'Misato Katsuragi', model=FakeContact,
                                is_custom=True,
                                conditions=conds + [EntityFilterCondition.build_4_subfilter(subfilter1)],
                               )

        with self.assertRaises(EntityFilter.PrivacyError):
            EntityFilter.create('creme_core-filter2', 'Misato Katsuragi', model=FakeContact,
                                user=user, is_private=True, is_custom=True,
                                conditions=conds + [EntityFilterCondition.build_4_subfilter(subfilter1)],
                               )

        with self.assertNoException():
            EntityFilter.create('creme_core-filter3', 'Misato Katsuragi', model=FakeContact,
                                user=user, is_private=True, is_custom=True,
                                conditions=conds + [EntityFilterCondition.build_4_subfilter(subfilter2)],
                               )

        with self.assertRaises(EntityFilter.PrivacyError):
            EntityFilter.create('creme_core-filter4', 'Misato Katsuragi', model=FakeContact,
                                user=user, is_private=True, is_custom=True,
                                conditions=conds + [EntityFilterCondition.build_4_subfilter(subfilter3)],
                               )

        with self.assertNoException():
            EntityFilter.create('creme_core-filter5', 'Misato Katsuragi', model=FakeContact,
                                user=user, is_private=True, is_custom=True,
                                conditions=conds + [EntityFilterCondition.build_4_subfilter(subfilter4)],
                               )

    def test_get_latest_version(self):
        base_pk = 'creme_core-testfilter'

        with self.assertRaises(EntityFilter.DoesNotExist):
             EntityFilter.get_latest_version(base_pk)

        create_ef = partial(EntityFilter.objects.create,
                            entity_type=ContentType.objects.get_for_model(FakeContact),
                           )

        create_ef(pk=base_pk, name='Base filter')

        efilter2 = create_ef(pk=base_pk + '[1.5]', name='Filter [1.5]')
        self.assertEqual(efilter2, EntityFilter.get_latest_version(base_pk))

        efilter3 = create_ef(pk=base_pk + '[1.7]', name='Filter [1.7]')
        create_ef(pk=base_pk + '[1.6]', name='Filter [1.6]')
        self.assertEqual(efilter3, EntityFilter.get_latest_version(base_pk))

        efilter5 = create_ef(pk=base_pk + '[1.8 alpha]', name='Filter [1.8 alpha]')
        self.assertEqual(efilter5, EntityFilter.get_latest_version(base_pk))

        efilter6 = create_ef(pk=base_pk + '[1.9 beta]', name='Filter [1.9 beta]')
        create_ef(pk=base_pk + '[1.9 alpha]', name='Filter [1.9 ~alpha]')  # NB: '~' annoys stupid name ordering
        self.assertEqual(efilter6, EntityFilter.get_latest_version(base_pk))

        efilter8 = create_ef(pk=base_pk + '[1.10]', name='Filter [1.10]')
        self.assertEqual(efilter8, EntityFilter.get_latest_version(base_pk))

        efilter9 = create_ef(pk=base_pk + '[1.10.1]', name='Filter [1.10.1]')
        self.assertEqual(efilter9, EntityFilter.get_latest_version(base_pk))

        create_ef(pk=base_pk + '[1.10.2 alpha]', name='Filter [1.10.2 alpha]')
        create_ef(pk=base_pk + '[1.10.2 beta]', name='Filter | 1.10.2 beta')
        efilter12 = create_ef(pk=base_pk + '[1.10.2 rc]', name='Filter [1.10.2 rc]')
        self.assertEqual(efilter12, EntityFilter.get_latest_version(base_pk))

        create_ef(pk=base_pk + '[1.10.2 rc2]', name='Filter [1.10.2 rc2]')
        efilter14 = create_ef(pk=base_pk + '[1.10.2 rc11]', name='Filter [1.10.2 rc11]')
        self.assertEqual(efilter14, EntityFilter.get_latest_version(base_pk))

        create_ef(pk=base_pk + '[1.10.2 rc11]3', name=u'Filter | 1.10.2 rc11 | n°3')
        efilter16 = create_ef(pk=base_pk + '[1.10.2 rc11]12', name='Filter [1.10.2 rc11]#12')
        self.assertEqual(efilter16, EntityFilter.get_latest_version(base_pk))

    def test_conditions_equal(self):
        equal = EntityFilterCondition.conditions_equal
        self.assertIs(equal([], []), True)

        build_4_field = partial(EntityFilterCondition.build_4_field,
                                model=FakeContact,
                                operator=EntityFilterCondition.EQUALS,
                                name='last_name', values=['Ikari'],
                               )
        conditions1 = [build_4_field()]
        self.assertIs(equal([], conditions1), False)
        self.assertTrue(equal(conditions1, conditions1))

        self.assertFalse(equal(conditions1, [build_4_field(name='first_name')]))
        self.assertFalse(equal(conditions1, [build_4_field(values=['Katsuragi'])]))
        self.assertFalse(equal(conditions1,
                               [build_4_field(operator=EntityFilterCondition.CONTAINS)]
                              )
                         )

        ptype = CremePropertyType.create(str_pk='test-prop_kawaii', text=u'Kawaii')
        hates = RelationType.create(('test-subject_hate', u'Is hating'),
                                    ('test-object_hate',  u'Is hated by')
                                   )[0]

        cond1 = build_4_field()
        cond2 = EntityFilterCondition.build_4_property(ptype=ptype, has=True)
        cond3 = EntityFilterCondition.build_4_relation(rtype=hates, has=True)
        self.assertFalse(equal([cond1, cond2],
                               [cond2, cond3]
                              )
                        )
        self.assertTrue(equal([cond1, cond2, cond3],
                              [cond2, cond3, cond1]
                             )
                       )

    def test_create_condition_creatorfield_fk(self):
        equal = EntityFilterCondition.conditions_equal
        folder = FakeFolder.objects.create(title='Folder 01', user=self.user)
        other_folder = FakeFolder.objects.create(title='Folder 02', user=self.other_user)
        self.assertIs(equal([], []), True)

        build_4_field = partial(EntityFilterCondition.build_4_field,
                                model=FakeDocument,
                                operator=EntityFilterCondition.EQUALS,
                                name='folder'
                               )

        # user can link Document on "Folder 01" (owner=user)
        self.assertNoException(lambda: build_4_field(values=[str(folder.id)], user=self.user))
        # user can link Document on "Folder 02" (owner=other_user)
        self.assertNoException(lambda: build_4_field(values=[str(other_folder.id)], user=self.user))

        # other_user cannot link (not authenticated)
        with self.assertRaises(EntityFilterCondition.ValueError) as e:
            build_4_field(values=[str(folder.id)], user=self.other_user)

    def test_create_again01(self):
        "is_custom=True -> override"
        efilter = EntityFilter.create('test-filter', 'Ikari', FakeContact,
                                      is_custom=True, use_or=True,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=FakeContact,
                                                        operator=EntityFilterCondition.EQUALS,
                                                        name='last_name', values=['Ikari'],
                                                    ),
                                                 ]
                                      )
        count = EntityFilter.objects.count()

        user = self.user
        name = 'Misato my love'
        efilter = EntityFilter.create('test-filter', name, FakeContact,
                                      is_custom=True, user=user, use_or=False,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=FakeContact,
                                                        operator=EntityFilterCondition.IEQUALS,
                                                        name='first_name', values=['Gendo'],
                                                    ),
                                                 ]
                                      )
        self.assertEqual(name, efilter.name)
        self.assertEqual(user, efilter.user)
        self.assertFalse(efilter.use_or)

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD, condition.type)
        self.assertEqual('first_name',                    condition.name)
        self.assertEqual({'operator': EntityFilterCondition.IEQUALS, 'values': ['Gendo']},
                         condition.decoded_value
                        )

        self.assertEqual(count, EntityFilter.objects.count())

        with self.assertRaises(ValueError):
            EntityFilter.create('test-filter', name, FakeContact,
                                user=user, use_or=False, is_custom=False,  # <==== cannot become custom False
                                conditions=[EntityFilterCondition.build_4_field(
                                                    model=FakeContact,
                                                    operator=EntityFilterCondition.IEQUALS,
                                                    name='first_name', values=['Gendo'],
                                                ),
                                           ],
                               )

    def test_create_again02(self):
        "is_custom=False + no change -> override name (but not user)"
        conditions = [EntityFilterCondition.build_4_field(
                            model=FakeContact,
                            operator=EntityFilterCondition.EQUALS,
                            name='last_name', values=['Ikari'],
                        ),
                     ]
        pk = 'test-filter'
        EntityFilter.create(pk, 'Misato', FakeContact, user=self.other_user, conditions=conditions)
        count = EntityFilter.objects.count()

        name = 'Misato my love'
        efilter = EntityFilter.create(pk, name, FakeContact, user=self.user, conditions=conditions)
        self.assertEqual(name, efilter.name)
        self.assertEqual(self.other_user, efilter.user)

        self.assertEqual(count, EntityFilter.objects.count())

        with self.assertRaises(ValueError):
            EntityFilter.create(pk, name, FakeContact, user=self.user, conditions=conditions,
                                is_custom=True,
                               )

    def test_create_again03(self):
        "CT changes -> error (is_custom=False)"
        pk = 'test-filter'
        EntityFilter.create(pk, 'Misato', FakeContact,
                            conditions=[EntityFilterCondition.build_4_field(
                                                model=FakeContact,
                                                operator=EntityFilterCondition.EQUALS,
                                                name='last_name', values=['Katsuragi'],
                                            ),
                                       ]
                           )

        with self.assertRaises(ValueError):
            EntityFilter.create(pk, 'Nerv', FakeOrganisation,
                                conditions=[EntityFilterCondition.build_4_field(
                                                model=FakeOrganisation,
                                                operator=EntityFilterCondition.EQUALS,
                                                name='name', values=['Nerv'],
                                            ),
                                           ],
                               )

    def test_create_again04(self):
        "CT changes -> error (is_custom=True)"
        pk = 'test-filter'
        EntityFilter.create(pk, 'Misato', FakeContact, is_custom=True,
                            conditions=[EntityFilterCondition.build_4_field(
                                                model=FakeContact,
                                                operator=EntityFilterCondition.EQUALS,
                                                name='last_name', values=['Katsuragi'],
                                            ),
                                       ]
                           )

        with self.assertRaises(ValueError):
            EntityFilter.create(pk, 'Nerv', FakeOrganisation, is_custom=True,
                                conditions=[EntityFilterCondition.build_4_field(
                                                model=FakeOrganisation,
                                                operator=EntityFilterCondition.EQUALS,
                                                name='name', values=['Nerv'],
                                            ),
                                       ]
                                )

    def test_create_again05(self):
        "is_custom=False + changes -> new versioned filter"
        pk = 'test-filter'

        def create_filter(use_or=False, value='Ikari'):
            return EntityFilter.create(pk, 'Nerv member', FakeContact, is_custom=False, use_or=use_or,
                                       conditions=[EntityFilterCondition.build_4_field(
                                                        model=FakeContact,
                                                        operator=EntityFilterCondition.EQUALS,
                                                        name='last_name', values=[value],
                                                    ),
                                                  ]
                                      )

        qs = EntityFilter.objects.filter(pk__startswith=pk)
        efilter1 = create_filter()
        self.assertEqual(pk, efilter1.pk)
        self.assertEqual(1, qs.count())

        # --------------------------
        efilter2 = create_filter(use_or=True)
        self.assertEqual('%s[%s]' % (pk, __version__), efilter2.pk)
        self.assertEqual('Nerv member [%s]' % __version__, efilter2.name)
        self.assertEqual(2, qs.count())

        # --------------------------
        create_filter(use_or=True)
        self.assertEqual(2, qs.count())

        # --------------------------
        efilter3 = create_filter(use_or=True, value='Katsuragu')
        self.assertEqual(3, qs.count())
        self.assertEqual('%s[%s]2' % (pk, __version__), efilter3.pk)
        self.assertEqual('Nerv member [%s](2)' % __version__, efilter3.name)

        # --------------------------
        efilter4 = create_filter(use_or=True, value='Katsuragi')
        self.assertEqual(4, qs.count())
        self.assertEqual('%s[%s]3' % (pk, __version__), efilter4.pk)
        self.assertEqual('Nerv member [%s](3)' % __version__, efilter4.name)

    def test_create_errors(self):
        "Invalid chars in PK"

        def create_filter(pk):
            return EntityFilter.create(pk, 'Nerv member', FakeContact, is_custom=True)

        with self.assertRaises(ValueError):
            create_filter('creme_core-test_filter[1')

        with self.assertRaises(ValueError):
            create_filter('creme_core-test_filter1]')

        with self.assertRaises(ValueError):
            create_filter('creme_core-test_filter#1')

        with self.assertRaises(ValueError):
            create_filter('creme_core-test_filter?1')

        # Private + no user => error
        with self.assertRaises(ValueError):
            EntityFilter.create('creme_core-test_filter', 'Nerv member',
                                FakeContact, is_custom=True, is_private=True,
                               )

        # Private + not is_custom => error
        with self.assertRaises(ValueError):
            EntityFilter.create('creme_core-test_filter', 'Nerv member',
                                FakeContact, is_custom=False,
                                is_private=True, user=self.user,
                                conditions=[EntityFilterCondition.build_4_field(
                                                 model=FakeContact,
                                                 operator=EntityFilterCondition.EQUALS,
                                                 name='last_name', values=['Ikari'],
                                             ),
                                           ],
                               )

    def test_ct_cache(self):
        efilter = EntityFilter.create('test-filter01', 'Ikari', FakeContact, is_custom=True)

        with self.assertNumQueries(0):
            ContentType.objects.get_for_id(efilter.entity_type_id)

        efilter = self.refresh(efilter)

        with self.assertNumQueries(0):
            ct = efilter.entity_type

        self.assertIsInstance(ct, ContentType)

    def test_filter_field_equals01(self):
        efilter = EntityFilter.create('test-filter01', 'Ikari', FakeContact,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=FakeContact,
                                                        operator=EntityFilterCondition.EQUALS,
                                                        name='last_name', values=['Ikari'],
                                                    ),
                                                 ],
                                     )
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(self.refresh(efilter), FakeContact, self._get_ikari_case_sensitive())

        with self.assertNumQueries(0):
            conds = efilter.get_conditions()

        self.assertEqual(1, len(conds))

        cond = conds[0]
        self.assertIsInstance(cond, EntityFilterCondition)
        self.assertEqual('last_name', cond.name)

    def test_filter_field_equals02(self):
        efilter = EntityFilter.create('test-filter01', 'Spike & Faye', FakeContact,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=FakeContact,
                                                        operator=EntityFilterCondition.EQUALS,
                                                        name='first_name',
                                                        values=['Spike', 'Faye'],
                                                    ),
                                                 ],
                                     )
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(self.refresh(efilter), FakeContact, self._list_contact_ids('spike', 'faye'))

    def test_filter_field_equals_boolean(self):
        "Boolean field"
        contacts = self.contacts
        ed  = contacts['ed'];  ed.is_a_nerd = True;  ed.save()
        yui = contacts['yui']; yui.is_a_nerd = True; yui.save()

        def build_cond(value):
            return EntityFilterCondition.build_4_field(model=FakeContact,
                                                       operator=EntityFilterCondition.EQUALS,
                                                       name='is_a_nerd',
                                                       values=[value],
                                                      )

        efilter = EntityFilter.create(pk='test-filter01', name='is a nerd', model=FakeContact, is_custom=True,
                                      conditions=[build_cond(True)],
                                     )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('ed', 'yui'))

        efilter = EntityFilter.create(pk='test-filter02', name='is a not nerd', model=FakeContact, is_custom=True,
                                      conditions=[build_cond(False)],
                                     )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('ed', 'yui', exclude=True))

        # Old (buggy ?) format
        efilter = EntityFilter.create(pk='test-filter02', name='is a not nerd v2', model=FakeContact, is_custom=True,
                                      conditions=[build_cond('False')],
                                     )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('ed', 'yui', exclude=True))

    def test_filter_field_equals_currentuser(self):
        set_global_info(user=self.user)

        efilter = EntityFilter.create('test-filter01', 'Spike & Faye', FakeContact,
                                      conditions=[EntityFilterCondition.build_4_field(model=FakeContact,
                                                                                      operator=EntityFilterCondition.EQUALS,
                                                                                      name='user',
                                                                                      values=['__currentuser__'],
                                                                                      )
                                                 ],
                                     )

        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(self.refresh(efilter), FakeContact,
                                    self._list_contact_ids('mireille', exclude=True)
                                   )

        for name in ('rei', 'asuka'):
            c = self.contacts.get(name)
            c.user = self.other_user
            c.save()

        set_global_info(user=self.other_user)
        self.assertExpectedFiltered(self.refresh(efilter), FakeContact,
                                    self._list_contact_ids('asuka', 'rei')
                                   )

    def test_filter_field_iequals(self):
        efilter = EntityFilter.create('test-filter01', 'Ikari (insensitive)', FakeContact,
                                      user=self.user, is_custom=False,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=FakeContact,
                                                        operator=EntityFilterCondition.IEQUALS,
                                                        name='last_name', values=['Ikari']
                                                       ),
                                                 ],
                                     )
        self.assertExpectedFiltered(efilter, FakeContact,
                                    self._list_contact_ids('shinji', 'yui', 'gendou'),
                                    case_insensitive=True
                                   )

    def test_filter_field_not_equals(self):
        efilter = EntityFilter.create('test-filter01', 'Not Ikari', FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.EQUALS_NOT,
                                                                    name='last_name', values=['Ikari']
                                                                    )
                               ])

        excluded = frozenset(self._get_ikari_case_sensitive())
        self.assertExpectedFiltered(efilter, FakeContact,
                                    [c.id for c in self.contacts.itervalues() if c.id not in excluded]
                                   )

    def test_filter_field_not_iequals(self):
        pk = 'test-filter01'
        name = 'Not Ikari (case insensitive)'
        efilter = EntityFilter.create(pk, name, FakeContact, is_custom=True)

        efilters = EntityFilter.objects.filter(pk='test-filter01', name=name)
        self.assertEqual(1,                  len(efilters))
        self.assertEqual(self.contact_ct.id, efilters[0].entity_type.id)
        self.assertEqual(efilter.id,         efilters[0].id)

        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.IEQUALS_NOT,
                                                                    name='last_name', values=['Ikari']
                                                                    )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact,
                                    self._list_contact_ids('shinji', 'yui', 'gendou', exclude=True)
                                   )

    def test_filter_field_contains(self):
        efilter = EntityFilter.create('test-filter01', name='Contains "isat"', model=FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.CONTAINS,
                                                                    name='first_name', values=['isat']
                                                                    )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('misato', 'risato'))

    def test_filter_field_icontains(self):
        efilter = EntityFilter.create(pk='test-filter01', name='Not contains "Misa"',
                                      model=FakeContact, user=self.user, is_custom=True,
                                     )
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.ICONTAINS,
                                                                    name='first_name', values=['misa']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['misato'].id], True)

    def test_filter_field_contains_not(self):
        efilter = EntityFilter.create('test-filter01', 'Not Ikari', FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.CONTAINS_NOT,
                                                                    name='first_name', values=['sato']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('misato', 'risato', exclude=True))

    def test_filter_field_icontains_not(self):
        efilter = EntityFilter.create('test-filter01', 'Not contains "sato" (ci)', FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.ICONTAINS_NOT,
                                                                    name='first_name', values=['sato']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact,
                                    self._list_contact_ids('misato', 'risato', exclude=True),
                                    case_insensitive=True
                                   )

    def test_filter_field_gt(self):
        efilter = EntityFilter.create(pk='test-filter01', name='> Yua', model=FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.GT,
                                                                    name='first_name', values=['Yua']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['yui'].id])

    def test_filter_field_gte(self):
        efilter = EntityFilter.create('test-filter01', '>= Spike', FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.GTE,
                                                                    name='first_name', values=['Spike']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('spike', 'yui'))

    def test_filter_field_lt(self):
        efilter = EntityFilter.create('test-filter01', '< Faye', FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.LT,
                                                                    name='first_name', values=['Faye']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('ed', 'asuka'))

    def test_filter_field_lte(self):
        efilter = EntityFilter.create('test-filter01', '<= Faye', FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.LTE,
                                                                    name='first_name', values=['Faye']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('faye', 'ed', 'asuka'))

    def test_filter_field_startswith(self):
        efilter = EntityFilter.create(pk='test-filter01', name='starts "Gen"', model=FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.STARTSWITH,
                                                                    name='first_name', values=['Gen']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('gendou', 'genji'))

    def test_filter_field_istartswith(self):
        efilter = EntityFilter.create(pk='test-filter01', name='starts "Gen" (ci)', model=FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.ISTARTSWITH,
                                                                    name='first_name', values=['gen']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('gendou', 'genji'))

    def test_filter_field_startswith_not(self):
        efilter = EntityFilter.create(pk='test-filter01', name='starts not "Asu"', model=FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.STARTSWITH_NOT,
                                                                    name='first_name', values=['Asu']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('asuka', exclude=True))

    def test_filter_field_istartswith_not(self):
        efilter = EntityFilter.create('test-filter01', 'starts not "asu"', FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.ISTARTSWITH_NOT,
                                                                    name='first_name', values=['asu']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('asuka', exclude=True))

    def test_filter_field_endswith(self):
        efilter = EntityFilter.create('test-filter01', 'ends "sato"', FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.ENDSWITH,
                                                                    name='first_name', values=['sato']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('misato', 'risato'))

    def test_filter_field_iendswith(self):
        efilter = EntityFilter.create('test-filter01', 'ends "SATO"', FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.IENDSWITH,
                                                                    name='first_name', values=['SATO']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('misato', 'risato'))

    def test_filter_field_endswith_not(self):
        efilter = EntityFilter.create('test-filter01', 'ends not "sato"', FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.ENDSWITH_NOT,
                                                                    name='first_name', values=['sato']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('misato', 'risato', exclude=True))

    def test_filter_field_iendswith_not(self):
        efilter = EntityFilter.create('test-filter01', 'ends not "SATO" (ci)', FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.IENDSWITH_NOT,
                                                                    name='first_name', values=['SATO']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('misato', 'risato', exclude=True))

    def test_filter_field_isempty01(self):
        efilter = EntityFilter.create(pk='test-filter01', name='is empty', model=FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.ISEMPTY,
                                                                    name='description', values=[True]
                                                                   )
                               ])
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('faye', exclude=True))

    def test_filter_field_isempty02(self):
        efilter = EntityFilter.create('test-filter01', 'is not empty', FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.ISEMPTY,
                                                                    name='description', values=[False]
                                                                   )
                               ])
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['faye'].id])

    def test_filter_field_isempty03(self):
        "Not a CharField"
        create_orga = partial(FakeOrganisation.objects.create, user=self.user)
        create_orga(name='Bebop & cie', capital=None)
        orga02 = create_orga(name='Nerv', capital=10000)

        efilter = EntityFilter.create('test-filter01', 'is not null', FakeOrganisation, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeOrganisation,
                                                                    operator=EntityFilterCondition.ISEMPTY,
                                                                    name='capital', values=[False]
                                                                   )
                               ])
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(efilter, FakeOrganisation, [orga02.id])

    def test_filter_field_isempty04(self):
        "Subfield of FK"
        efilter = EntityFilter.create(pk='test-filter01', name='civility is empty', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=FakeContact,
                                                        operator=EntityFilterCondition.ISEMPTY,
                                                        name='civility__title', values=[True]
                                                       ),
                                                 ],
                                      )
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('spike', 'jet', 'faye', exclude=True))

    def test_filter_field_range(self):
        create_orga = partial(FakeOrganisation.objects.create, user=self.user)
        create_orga(name='Bebop & cie',    capital=1000)
        orga02 = create_orga(name='Nerv',  capital=10000)
        orga03 = create_orga(name='Seele', capital=100000)

        efilter = EntityFilter.create('test-filter01', name='Between 5K & 500K',
                                      model=FakeOrganisation, is_custom=True,
                                      )
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeOrganisation,
                                                                    operator=EntityFilterCondition.RANGE,
                                                                    name='capital', values=(5000, 500000)
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, FakeOrganisation, [orga02.id, orga03.id])

    def test_filter_fk01(self):
        build_4_field = EntityFilterCondition.build_4_field
        efilter = EntityFilter.create('test-filter01', 'Misters', FakeContact, is_custom=True)
        efilter.set_conditions([build_4_field(model=FakeContact,
                                              operator=EntityFilterCondition.EQUALS,
                                              name='civility', values=[self.civ_mister.id]  # TODO: "self.mister" ??
                                             )
                               ])
        self.assertTrue(efilter.entities_are_distinct)
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('spike', 'jet'))

        efilter = EntityFilter.create('test-filter02', 'Not Misses', FakeContact, is_custom=True)
        efilter.set_conditions([build_4_field(model=FakeContact,
                                              operator=EntityFilterCondition.EQUALS_NOT,
                                              name='civility', values=[self.civ_miss.id]
                                             )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('faye', exclude=True))

    def test_filter_fk02(self):
        efilter = EntityFilter.create('test-filter01', 'Mist..', FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.ISTARTSWITH,
                                                                    name='civility__title', values=['Mist'],
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('spike', 'jet'))

    def test_filter_m2m(self):
        create_language = Language.objects.create
        l1 = create_language(name='Japanese', code='JP')
        l2 = create_language(name='German',   code='G')
        l3 = create_language(name='Engrish',  code='EN')

        contacts = self.contacts
        jet   = contacts['jet'];   jet.languages   = [l1, l3]
        rei   = contacts['rei'];   rei.languages   = [l1]
        asuka = contacts['asuka']; asuka.languages = [l1, l2, l3]
        faye  = contacts['faye'];  faye.languages  = [l2, l3]
        yui   = contacts['yui'];   yui.languages   = [l3]

        filter_contacts = FakeContact.objects.filter
        self.assertEqual(3, filter_contacts(languages__code='JP').count())
        self.assertEqual(5, filter_contacts(languages__name__contains='an').count())  # BEWARE: duplicates !!
        self.assertEqual(4, filter_contacts(languages__name__contains='an').distinct().count())

        efilter = EntityFilter.create('test-filter01', 'JP', FakeContact, is_custom=True)
        build_4_field = EntityFilterCondition.build_4_field
        efilter.set_conditions([build_4_field(model=FakeContact,
                                              operator=EntityFilterCondition.IEQUALS,
                                              name='languages__code', values=['JP'],
                                             )
                               ])
        self.assertFalse(efilter.entities_are_distinct)
        self.assertExpectedFiltered(efilter, FakeContact, [jet.id, rei.id, asuka.id], use_distinct=True)

        efilter = EntityFilter.create('test-filter02', 'lang contains "an"', FakeContact, is_custom=True)
        efilter.set_conditions([build_4_field(model=FakeContact,
                                              operator=EntityFilterCondition.ICONTAINS,
                                              name='languages__name', values=['an'],
                                             )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, [jet.id, rei.id, asuka.id, faye.id], use_distinct=True)

        # Empty
        efilter = EntityFilter.create('test-filter03', 'has a language', FakeContact, is_custom=True,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                            model=FakeContact,
                                                            operator=EntityFilterCondition.ISEMPTY,
                                                            name='languages', values=[True],
                                                        ),
                                                 ],
                                     )
        self.assertExpectedFiltered(efilter, FakeContact,
                                    self._list_contact_ids('jet', 'rei', 'asuka', 'faye', 'yui', exclude=True),
                                    use_distinct=True,
                                   )

        # Not empty
        efilter = EntityFilter.create('test-filter04', 'has no language', FakeContact, is_custom=True,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                            model=FakeContact,
                                                            operator=EntityFilterCondition.ISEMPTY,
                                                            name='languages', values=[False],
                                                        ),
                                                 ],
                                     )
        self.assertExpectedFiltered(efilter, FakeContact,
                                    [jet.id, rei.id, asuka.id, faye.id, yui.id],
                                    use_distinct=True,
                                   )

    def test_problematic_validation_fields(self):
        efilter = EntityFilter.create('test-filter01', 'Mist..', FakeOrganisation, is_custom=True)
        build = EntityFilterCondition.build_4_field

        with self.assertNoException():
            # Problem a part of a email address is not a valid email address
            efilter.set_conditions([build(model=FakeOrganisation,
                                          operator=EntityFilterCondition.ISTARTSWITH,
                                          name='email', values=['misato'],
                                         ),
                                   ]
                                  )

        with self.assertNoException():
            efilter.set_conditions([build(model=FakeOrganisation,
                                          operator=EntityFilterCondition.RANGE,
                                          name='email', values=['misato', 'yui'],
                                         )
                                   ],
                                  )

        with self.assertNoException():
            efilter.set_conditions([build(model=FakeOrganisation,
                                          operator=EntityFilterCondition.EQUALS,
                                          name='email', values=['misato@nerv.jp'],
                                         )
                                   ],
                                  )

        self.assertRaises(EntityFilterCondition.ValueError, build,
                          model=FakeOrganisation, operator=EntityFilterCondition.EQUALS,
                          name='email', values=['misato'],
                         )

    def test_build_condition(self):
        "Errors"
        ValueError = EntityFilterCondition.ValueError
        build_4_field = EntityFilterCondition.build_4_field

        self.assertRaises(ValueError, build_4_field,
                          model=FakeContact, operator=EntityFilterCondition.CONTAINS, name='unknown_field', values=['Misato'],
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=FakeOrganisation, operator=EntityFilterCondition.GT, name='capital', values=['Not an integer']
                         )
        self.assertRaises(ValueError, build_4_field,
                          # ISEMPTY => boolean
                          model=FakeContact, operator=EntityFilterCondition.ISEMPTY, name='description', values=['Not a boolean'],
                         )
        self.assertRaises(ValueError, build_4_field,
                          # Only one boolean is expected
                          model=FakeContact, operator=EntityFilterCondition.ISEMPTY, name='description', values=[True, True],
                          )
        self.assertRaises(ValueError, build_4_field,
                          model=FakeContact, operator=EntityFilterCondition.STARTSWITH, name='civility__unknown', values=['Mist']
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=FakeOrganisation, operator=EntityFilterCondition.RANGE, name='capital', values=[5000]
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=FakeOrganisation, operator=EntityFilterCondition.RANGE, name='capital', values=[5000, 50000, 100000]
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=FakeOrganisation, operator=EntityFilterCondition.RANGE, name='capital', values=['not an integer', 500000]
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=FakeOrganisation, operator=EntityFilterCondition.RANGE, name='capital', values=[500000, 'not an integer']
                         )

    def test_condition_update(self):
        build = partial(EntityFilterCondition.build_4_field, model=FakeContact)
        EQUALS = EntityFilterCondition.EQUALS
        IEQUALS = EntityFilterCondition.IEQUALS
        cond1 = build(operator=EQUALS, name='first_name', values=['Jet'])
        self.assertFalse(build(operator=EQUALS, name='first_name', values=['Jet']).update(cond1))
        self.assertTrue(build(operator=IEQUALS, name='first_name', values=['Jet']).update(cond1))
        self.assertTrue(build(operator=EQUALS,  name='last_name',  values=['Jet']).update(cond1))
        self.assertTrue(build(operator=EQUALS,  name='first_name', values=['Ed']).update(cond1))
        self.assertTrue(build(operator=IEQUALS, name='last_name',  values=['Jet']).update(cond1))
        self.assertTrue(build(operator=IEQUALS, name='last_name',  values=['Ed']).update(cond1))

    def test_set_conditions01(self):
        build = partial(EntityFilterCondition.build_4_field, model=FakeContact)
        efilter = EntityFilter.create('test-filter01', 'Jet', FakeContact, is_custom=True)
        efilter.set_conditions([build(operator=EntityFilterCondition.EQUALS, name='first_name', values=['Jet'])])

        # NB: create an other condition that has he last id (so if we delete the
        #     first condition, and recreate another one, the id will be different)
        EntityFilter.create('test-filter02', 'Faye', FakeContact, is_custom=True) \
                    .set_conditions([build(operator=EntityFilterCondition.EQUALS, name='first_name', values=['Faye'])])

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))
        old_id = conditions[0].id

        operator = EntityFilterCondition.CONTAINS
        name = 'last_name'
        value = 'Black'
        efilter.set_conditions([build(operator=operator, name=name, values=[value])])

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,           condition.type)
        self.assertEqual(name,                                      condition.name)
        self.assertEqual({'operator': operator, 'values': [value]}, condition.decoded_value)
        self.assertEqual(old_id,                                    condition.id)

    def test_set_conditions02(self):
        efilter = EntityFilter.create('test-filter01', 'Jet', FakeContact, is_custom=True)

        kwargs1 = {'model':     FakeContact,
                   'operator':  EntityFilterCondition.EQUALS,
                   'name':      'first_name',
                   'values':    ['Jet'],
                  }
        kwargs2 = dict(kwargs1)
        kwargs2['operator'] = EntityFilterCondition.IEQUALS

        build = EntityFilterCondition.build_4_field
        efilter.set_conditions([build(**kwargs1), build(**kwargs2)])

        # NB: see test_set_conditions01()
        EntityFilter.create('test-filter02', 'Faye', FakeContact, is_custom=True) \
                    .set_conditions([build(model=FakeContact, operator=EntityFilterCondition.EQUALS, name='first_name', values=['Faye'])])

        conditions = efilter.conditions.order_by('id')
        self.assertEqual(2, len(conditions))

        for kwargs, condition in zip([kwargs1, kwargs2], conditions):
            self.assertEqual(EntityFilterCondition.EFC_FIELD, condition.type)
            self.assertEqual(kwargs['name'],                  condition.name)
            self.assertEqual({'operator': kwargs['operator'], 'values': kwargs['values']}, condition.decoded_value)

        old_id = conditions[0].id

        kwargs1['operator'] = EntityFilterCondition.GT
        efilter.set_conditions([build(**kwargs1)])

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,                                condition.type)
        self.assertEqual(kwargs1['name'],                                                condition.name)
        self.assertEqual({'operator': kwargs1['operator'], 'values': kwargs1['values']}, condition.decoded_value)
        self.assertEqual(old_id,                                                         condition.id)

    def test_set_conditions03(self):
        "Set an erroneous condition on an existing filter -> try to delete a condition without PK (BUGFIX)"
        efilter = EntityFilter.create('test-filter', 'Misato', FakeContact,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                            model=FakeContact,
                                                            operator=EntityFilterCondition.EQUALS,
                                                            name='last_name', values=['Katsuragi'],
                                                        ),
                                                 ],
                                     )
        efilter.set_conditions([EntityFilterCondition.build_4_field(
                                        model=FakeOrganisation,  # Not the same CT !!
                                        operator=EntityFilterCondition.EQUALS,
                                        name='name', values=['Nerv'],
                                    ),
                               ]
                              )
        self.assertFalse(efilter.get_conditions())
        self.assertFalse(efilter.conditions.all())

    def test_multi_conditions_and01(self):
        efilter = EntityFilter.create(pk='test-filter01', name='Filter01',
                                      model=FakeContact, is_custom=True,
                                     )
        build = EntityFilterCondition.build_4_field
        efilter.set_conditions([build(model=FakeContact, operator=EntityFilterCondition.EQUALS,
                                      name='last_name', values=['Ikari']
                                     ),
                                build(model=FakeContact, operator=EntityFilterCondition.STARTSWITH,
                                      name='first_name', values=['Shin']
                                     )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['shinji'].id])

        self.assertEqual(2, len(efilter.get_conditions()))

    def test_multi_conditions_or01(self):
        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=FakeContact,
                                      use_or=True, is_custom=True,
                                      )
        build = EntityFilterCondition.build_4_field
        efilter.set_conditions([build(model=FakeContact, operator=EntityFilterCondition.EQUALS,
                                      name='last_name', values=['Spiegel']
                                     ),
                                build(model=FakeContact, operator=EntityFilterCondition.STARTSWITH,
                                      name='first_name', values=['Shin']
                                     )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('spike', 'shinji'))

    def test_subfilter01(self):
        build_4_field = partial(EntityFilterCondition.build_4_field, model=FakeContact)
        build_sf      = EntityFilterCondition.build_4_subfilter
        sub_efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=FakeContact, use_or=True, is_custom=True)
        sub_efilter.set_conditions([build_4_field(operator=EntityFilterCondition.EQUALS,     name='last_name',  values=['Spiegel']),
                                    build_4_field(operator=EntityFilterCondition.STARTSWITH, name='first_name', values=['Shin']),
                                   ])
        efilter = EntityFilter.create(pk='test-filter02', name='Filter02', model=FakeContact, use_or=False, is_custom=True)
        conds = [build_4_field(operator=EntityFilterCondition.STARTSWITH, name='first_name', values=['Spi']),
                 build_sf(sub_efilter),
                ]

        with self.assertNoException():
            efilter.check_cycle(conds)

        efilter.set_conditions(conds)
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['spike'].id])

        # Test that a CycleError is not raised
        sub_sub_efilter = EntityFilter.create(pk='test-filter03', name='Filter03', model=FakeContact, is_custom=True)
        sub_sub_efilter.set_conditions([build_4_field(operator=EntityFilterCondition.EQUALS,     name='last_name',  values=['Black']),
                                        build_4_field(operator=EntityFilterCondition.STARTSWITH, name='first_name', values=['Jet'])
                                       ])

        conds = [build_4_field(operator=EntityFilterCondition.STARTSWITH, name='first_name', values=['Spi']),
                 build_sf(sub_sub_efilter),
                ]

        with self.assertNoException():
            sub_efilter.check_cycle(conds)

    def test_subfilter02(self):
        "Cycle error (length = 0)"
        efilter = EntityFilter.create(pk='test-filter02', name='Filter01',
                                      model=FakeContact, use_or=False, is_custom=True,
                                     )
        conds = [EntityFilterCondition.build_4_field(model=FakeContact, operator=EntityFilterCondition.STARTSWITH,
                                                     name='first_name', values=['Spi']
                                                    ),
                 EntityFilterCondition.build_4_subfilter(efilter),
                ]
        self.assertRaises(EntityFilter.CycleError, efilter.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter.set_conditions, conds)

    def test_subfilter03(self):
        "Cycle error (length = 1)"
        build_4_field = partial(EntityFilterCondition.build_4_field, model=FakeContact)
        build_sf = EntityFilterCondition.build_4_subfilter

        efilter01 = EntityFilter.create(pk='test-filter01', name='Filter01', model=FakeContact, use_or=True, is_custom=True)
        efilter01.set_conditions([build_4_field(operator=EntityFilterCondition.EQUALS, name='last_name', values=['Spiegel'])])

        efilter02 = EntityFilter.create(pk='test-filter02', name='Filter02', model=FakeContact, use_or=False, is_custom=True)
        self.assertEqual({efilter02.id}, efilter02.get_connected_filter_ids())

        efilter02.set_conditions([build_4_field(operator=EntityFilterCondition.STARTSWITH, name='first_name', values=['Spi']),
                                  build_sf(efilter01),
                                 ])

        conds = [build_4_field(operator=EntityFilterCondition.CONTAINS, name='first_name', values=['Faye']),
                 build_sf(efilter02),
                ]
        efilter01 = self.refresh(efilter01)
        self.assertEqual({efilter01.id, efilter02.id}, efilter01.get_connected_filter_ids())
        self.assertRaises(EntityFilter.CycleError, efilter01.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter01.set_conditions, conds)

    def test_subfilter04(self):
        "Cycle error (length = 2)"
        build_4_field = partial(EntityFilterCondition.build_4_field, model=FakeContact)
        build_sf = EntityFilterCondition.build_4_subfilter

        efilter01 = EntityFilter.create(pk='test-filter01', name='Filter01', model=FakeContact, use_or=True, is_custom=True)
        efilter01.set_conditions([build_4_field(operator=EntityFilterCondition.EQUALS, name='last_name', values=['Spiegel'])])

        efilter02 = EntityFilter.create(pk='test-filter02', name='Filter02', model=FakeContact, use_or=False, is_custom=True)
        efilter02.set_conditions([build_4_field(operator=EntityFilterCondition.STARTSWITH, values=['Spi'], name='first_name'),
                                  build_sf(efilter01),
                                 ])

        efilter03 = EntityFilter.create(pk='test-filter03', name='Filter03', model=FakeContact, use_or=False, is_custom=True)
        efilter03.set_conditions([build_4_field(operator=EntityFilterCondition.ISTARTSWITH, values=['Misa'], name='first_name'),
                                  build_sf(efilter02),
                                 ])

        conds = [build_4_field(operator=EntityFilterCondition.EQUALS, name='last_name', values=['Spiegel']),
                 build_sf(efilter03),
                ]
        efilter01 = self.refresh(efilter01)
        self.assertRaises(EntityFilter.CycleError, efilter01.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter01.set_conditions, conds)

    def test_properties01(self):
        ptype = CremePropertyType.create(str_pk='test-prop_kawaii', text=u'Kawaii')
        cute_ones = ('faye', 'rei', 'misato', 'asuka')

        for fn in cute_ones:
            CremeProperty.objects.create(type=ptype, creme_entity=self.contacts[fn])

        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_property(ptype=ptype, has=True)])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids(*cute_ones))

        efilter.set_conditions([EntityFilterCondition.build_4_property(ptype=ptype, has=False)])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids(*cute_ones, exclude=True))

    def test_properties02(self):
        "Several conditions on properties"
        create_ptype = CremePropertyType.create
        ptype1 = create_ptype(str_pk='test-prop_pretty',    text=u'Pretty')
        ptype2 = create_ptype(str_pk='test-prop_beautiful', text=u'Beautiful')

        pretty_ones    = ('rei', 'asuka')
        beautiful_ones = ('asuka', 'misato')

        create_prop = CremeProperty.objects.create

        for fn in pretty_ones:
             create_prop(type=ptype1, creme_entity=self.contacts[fn])

        for fn in beautiful_ones:
             create_prop(type=ptype2, creme_entity=self.contacts[fn])

        build_cond = EntityFilterCondition.build_4_property
        efilter = EntityFilter.create(pk='test-filter', name='Cute & pretty',
                                      model=FakeContact, is_custom=True,
                                      conditions=[build_cond(ptype=ptype1, has=True),
                                                  build_cond(ptype=ptype2, has=True),
                                                 ]
                                     )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('asuka'))

    def _aux_test_relations(self):
        self.loves, self.loved = RelationType.create(('test-subject_love', u'Is loving'),
                                                     ('test-object_love',  u'Is loved by')
                                                    )

        self.hates, self.hated = RelationType.create(('test-subject_hate', u'Is hating'),
                                                     ('test-object_hate',  u'Is hated by')
                                                    )

        bebop = FakeOrganisation.objects.create(user=self.user, name='Bebop')

        loves = self.loves
        c = self.contacts
        create = Relation.objects.create
        create(subject_entity=c['faye'],   type=loves, object_entity=c['spike'], user=self.user)
        create(subject_entity=c['shinji'], type=loves, object_entity=c['rei'],   user=self.user)
        create(subject_entity=c['gendou'], type=loves, object_entity=c['rei'],   user=self.user)
        create(subject_entity=c['jet'],    type=loves, object_entity=bebop,      user=self.user)

        create(subject_entity=c['shinji'], type=self.hates, object_entity=c['gendou'],  user=self.user)

        return loves

    def test_relations01(self):
        "No CT/entity"
        loves = self._aux_test_relations()
        in_love = ('faye', 'shinji', 'gendou', 'jet')

        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=True)])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids(*in_love))

        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=False)])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids(*in_love, exclude=True))

    def test_relations02(self):
        "Wanted CT"
        loves = self._aux_test_relations()
        in_love = ('faye', 'shinji', 'gendou')  # Not 'jet' ('bebop' not is a Contact)

        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=True, ct=self.contact_ct)])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids(*in_love))

        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=False, ct=self.contact_ct)])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids(*in_love, exclude=True))

    def test_relations03(self):
        "Wanted entity"
        loves = self._aux_test_relations()
        in_love = ('shinji', 'gendou')
        rei = self.contacts['rei']

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01', model=FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=True, entity=rei)])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids(*in_love))

        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=False, entity=rei)])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids(*in_love, exclude=True))

    def test_relations04(self):
        "Wanted entity is deleted"
        loves = self._aux_test_relations()
        rei = self.contacts['rei']

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01', model=FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=True, entity=rei)])

        with self.assertNoException():
            Relation.objects.filter(object_entity=rei.id).delete()
            rei.delete()

        self.assertExpectedFiltered(efilter, FakeContact, [])

    def test_relations05(self):
        "RelationType is deleted"
        loves = self._aux_test_relations()

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01', model=FakeContact, is_custom=True)
        build = EntityFilterCondition.build_4_relation
        efilter.set_conditions([build(rtype=loves,      has=True, entity=self.contacts['rei']),
                                build(rtype=self.loved, has=True, ct=self.contact_ct),
                                build(rtype=self.hates, has=True),
                               ])

        loves.delete()
        self.assertEqual([self.hates.id], [cond.name for cond in efilter.conditions.all()])

    def test_relations06(self):
        "Several conditions on relations (with OR)"
        loves = self._aux_test_relations()
        gendo = self.contacts['gendou']

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01',
                                      model=FakeContact, use_or=True, is_custom=True,
                                     )
        build = EntityFilterCondition.build_4_relation
        efilter.set_conditions([build(rtype=loves,      has=True, entity=self.contacts['rei']),
                                build(rtype=self.hates, has=True, entity=gendo),
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['shinji'].id, gendo.id])

    def test_relations07(self):
        "Several conditions on relations (with AND)"
        loves = self._aux_test_relations()

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01',
                                      model=FakeContact, use_or=False, is_custom=True,
                                     )
        build = EntityFilterCondition.build_4_relation
        efilter.set_conditions([build(rtype=loves,      has=True, entity=self.contacts['rei']),
                                build(rtype=self.hates, has=True, entity=self.contacts['gendou']),
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['shinji'].id])

    def test_relations_subfilter01(self):
        loves = self._aux_test_relations()
        in_love = ('shinji', 'gendou')

        sub_efilter = EntityFilter.create(pk='test-filter01', name='Filter Rei', model=FakeContact, is_custom=True)
        build_4_field = partial(EntityFilterCondition.build_4_field, model=FakeContact)
        sub_efilter.set_conditions([build_4_field(operator=EntityFilterCondition.STARTSWITH, name='last_name',  values=['Ayanami']),
                                    build_4_field(operator=EntityFilterCondition.EQUALS,     name='first_name', values=['Rei']),
                                   ])
        self.assertExpectedFiltered(sub_efilter, FakeContact, [self.contacts['rei'].id])

        efilter = EntityFilter.create(pk='test-filter02', name='Filter Rei lovers', model=FakeContact, is_custom=True)
        conds = [EntityFilterCondition.build_4_relation_subfilter(rtype=loves, has=True, subfilter=sub_efilter)]

        with self.assertNoException():
            efilter.check_cycle(conds)

        efilter.set_conditions(conds)
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids(*in_love))

        efilter.set_conditions([EntityFilterCondition.build_4_relation_subfilter(rtype=loves, has=False, subfilter=sub_efilter)])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids(*in_love, exclude=True))

    def test_relations_subfilter02(self):
        "Cycle error (length = 0)"
        loves = self._aux_test_relations()

        efilter = EntityFilter.create(pk='test-filter01', name='Filter Rei lovers', model=FakeContact, is_custom=True)
        conds = [EntityFilterCondition.build_4_relation_subfilter(rtype=loves, has=True, subfilter=efilter)]

        self.assertRaises(EntityFilter.CycleError, efilter.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter.set_conditions, conds)

    def test_relations_subfilter03(self):
        "Cycle error (length = 1)"
        loves = self._aux_test_relations()

        efilter01 = EntityFilter.create(pk='test-filter01', name='Filter 01', model=FakeContact, is_custom=True)
        efilter01.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact, operator=EntityFilterCondition.EQUALS,
                                                                      name='last_name', values=['Ayanami'])
                                 ])

        efilter02 = EntityFilter.create(pk='test-filter02', name='Filter 02', model=FakeContact, is_custom=True)
        efilter02.set_conditions([EntityFilterCondition.build_4_relation_subfilter(rtype=loves, has=True, subfilter=efilter01)])

        conds = [EntityFilterCondition.build_4_relation_subfilter(rtype=self.hates, has=False, subfilter=efilter02)]
        efilter01 = self.refresh(efilter01)
        self.assertRaises(EntityFilter.CycleError, efilter01.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter01.set_conditions, conds)

    def test_relations_subfilter04(self):
        "RelationType is deleted"
        loves = self._aux_test_relations()
        build_4_field = partial(EntityFilterCondition.build_4_field, model=FakeContact)

        sub_efilter01 = EntityFilter.create(pk='test-filter01', name='Filter Rei', model=FakeContact,
                                            conditions=[build_4_field(operator=EntityFilterCondition.STARTSWITH,
                                                                      name='last_name',  values=['Ayanami'],
                                                                     ),
                                                       ],
                                           )

        sub_efilter02 = EntityFilter.create(pk='test-filter02', name='Filter Rei', model=FakeContact,
                                            conditions=[build_4_field(operator=EntityFilterCondition.STARTSWITH,
                                                                      name='first_name',  values=['Misa'],
                                                                     ),
                                                       ],
                                           )

        efilter = EntityFilter.create(pk='test-filter03', name='Filter Rei lovers', model=FakeContact, is_custom=True)
        build = EntityFilterCondition.build_4_relation_subfilter
        efilter.set_conditions([build(rtype=loves,      has=True, subfilter=sub_efilter01),
                                build(rtype=self.hates, has=True, subfilter=sub_efilter02),
                               ])

        loves.delete()
        self.assertEqual([self.hates.id], [cond.name for cond in efilter.conditions.all()])

    def test_relations_subfilter05(self):
        "Several conditions (with OR)"
        loves = self._aux_test_relations()

        build_4_field = partial(EntityFilterCondition.build_4_field, model=FakeContact)

        sub_efilter01 = EntityFilter.create(pk='test-filter01', name='Filter Rei', model=FakeContact,
                                            conditions=[build_4_field(operator=EntityFilterCondition.STARTSWITH, name='last_name',  values=['Ayanami']),
                                                        build_4_field(operator=EntityFilterCondition.EQUALS,     name='first_name', values=['Rei']),
                                                       ],
                                           )
        self.assertExpectedFiltered(sub_efilter01, FakeContact, [self.contacts['rei'].id])

        sub_efilter02 = EntityFilter.create(pk='test-filter02', name=u'Filter Gendô', model=FakeContact,
                                            conditions=[build_4_field(operator=EntityFilterCondition.EQUALS, name='first_name', values=[u'Gendô'])],
                                           )
        self.assertExpectedFiltered(sub_efilter02, FakeContact, [self.contacts['gendou'].id])

        efilter = EntityFilter.create(pk='test-filter03', name='Filter with 2 sublovers',
                                      model=FakeContact, use_or=True, is_custom=True,
                                     )
        build = EntityFilterCondition.build_4_relation_subfilter
        efilter.set_conditions([build(rtype=loves,      has=True, subfilter=sub_efilter01),
                                build(rtype=self.hates, has=True, subfilter=sub_efilter02),
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('shinji', 'gendou'))

    def test_relations_subfilter06(self):
        "Several conditions (with AND)"
        loves = self._aux_test_relations()

        build_4_field = partial(EntityFilterCondition.build_4_field, model=FakeContact)

        sub_efilter01 = EntityFilter.create(pk='test-filter01', name='Filter Rei', model=FakeContact, is_custom=True)
        sub_efilter01.set_conditions([build_4_field(operator=EntityFilterCondition.STARTSWITH, name='last_name',  values=['Ayanami']),
                                      build_4_field(operator=EntityFilterCondition.EQUALS,     name='first_name', values=['Rei'])
                                    ])
        self.assertExpectedFiltered(sub_efilter01, FakeContact, [self.contacts['rei'].id])

        sub_efilter02 = EntityFilter.create(pk='test-filter02', name='Filter Gendo', model=FakeContact, is_custom=True)
        sub_efilter02.set_conditions([build_4_field(operator=EntityFilterCondition.EQUALS, name='first_name', values=[u'Gendô'])])
        self.assertExpectedFiltered(sub_efilter02, FakeContact, [self.contacts['gendou'].id])

        efilter = EntityFilter.create(pk='test-filter03', name='Filter with 2 sublovers',
                                      model=FakeContact, use_or=False, is_custom=True,
                                     )
        build_4_relsubfilter = partial(EntityFilterCondition.build_4_relation_subfilter, has=True)
        efilter.set_conditions([build_4_relsubfilter(rtype=loves,      subfilter=sub_efilter01),
                                build_4_relsubfilter(rtype=self.hates, subfilter=sub_efilter02),
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['shinji'].id])

    def test_date01(self):
        "GTE operator"
        efilter = EntityFilter.create('test-filter01', 'After 2000-1-1', FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=FakeContact, name='birthday',
                                                                   start=date(year=2000, month=1, day=1),
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('asuka', 'shinji'))

    def test_date02(self):
        "LTE operator"
        efilter = EntityFilter.create('test-filter01', 'Before 1999-12-31', FakeContact,
                                      conditions=[EntityFilterCondition.build_4_date(
                                                        model=FakeContact, name='birthday',
                                                        end=date(year=1999, month=12, day=31),
                                                       ),
                                                 ],
                                     )
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['misato'].id])

    def test_date03(self):
        "Range"
        efilter = EntityFilter.create('test-filter01', name='Between 2001-1-1 & 2001-12-1',
                                      model=FakeContact, is_custom=True,
                                     )
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=FakeContact, name='birthday',
                                                                   start=date(year=2001, month=1, day=1),
                                                                   end=date(year=2001, month=12, day=1),
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['shinji'].id])

    def test_date04(self):
        "Relative to now"
        faye = self.contacts['faye']
        future = date.today()
        future = future.replace(year=future.year + 100)
        faye.birthday = future
        faye.save()

        efilter = EntityFilter.create('test-filter01', name='In the future', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_date(
                                                        model=FakeContact, name='birthday',
                                                        date_range='in_future',
                                                       ),
                                                 ],
                                     )
        self.assertExpectedFiltered(efilter, FakeContact, [faye.id])

    def test_datetime01(self):
        "Previous year"
        faye = self.contacts['faye']
        FakeContact.objects.filter(pk=faye.id).update(created=faye.created - timedelta(days=faye.created.month * 31))

        efilter = EntityFilter.create('test-filter01', name='Created during previous year', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_date(
                                                      model=FakeContact, name='created',
                                                      date_range='previous_year',
                                                  ),
                                                 ],
                                     )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('faye'))

    def test_datetime02(self):
        "Current year"
        faye = self.contacts['faye']
        FakeContact.objects.filter(pk=faye.id).update(created=faye.created - timedelta(days=faye.created.month * 31))

        efilter = EntityFilter.create('test-filter01', name='Created during current year', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_date(
                                                      model=FakeContact, name='created',
                                                      date_range='current_year',
                                                  ),
                                                 ],
                                     )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('faye', exclude=True))

    def test_datetime03(self):
        "Next year"
        faye = self.contacts['faye']
        FakeContact.objects.filter(pk=faye.id)\
                           .update(created=faye.created + timedelta(days=(13 - faye.created.month) * 31))

        efilter = EntityFilter.create('test-filter01', name='Created during next year (?!)',
                                      model=FakeContact, is_custom=True,
                                     )
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=FakeContact, name='created',
                                                                   date_range='next_year',
                                                                  ),
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('faye'))

    def test_datetime04(self):
        "Current month"
        faye = self.contacts['faye']
        FakeContact.objects.filter(pk=faye.id).update(created=faye.created - timedelta(days=31))

        efilter = EntityFilter.create('test-filter01', name='Created during current month',
                                      model=FakeContact, is_custom=True,
                                     )
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=FakeContact, name='created',
                                                                   date_range='current_month',
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('faye', exclude=True))

    def test_datetime05(self):
        "Current quarter"
        faye = self.contacts['faye']
        FakeContact.objects.filter(pk=faye.id).update(created=faye.created - timedelta(days=4 * 31))

        efilter = EntityFilter.create('test-filter01', name='Created during current quarter', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_date(
                                                      model=FakeContact, name='created',
                                                      date_range='current_quarter',
                                                  ),
                                                 ],
                                     )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('faye', exclude=True))

    def test_datetime06(self):
        "Sub-field"
        contacts = self.contacts
        spike = contacts['spike']
        jet   = contacts['jet']

        create_image = partial(FakeImage.objects.create, user=self.user)
        spike.image = img1 = create_image(name="Spike's' face"); spike.save()
        jet.image          = create_image(name="Jet's' face");   jet.save()

        FakeImage.objects.filter(pk=img1.id).update(created=img1.created - timedelta(days=4 * 31))

        efilter = EntityFilter.create('test-filter01', name='Recent images content', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_date(
                                                      model=FakeContact, name='image__created',
                                                      date_range='current_quarter',
                                                  ),
                                                 ],
                                     )
        self.assertExpectedFiltered(efilter, FakeContact, [jet.id])

    def test_date_field_empty(self):
        efilter = EntityFilter.create('test-filter01', name='Birthday is null', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_date(
                                                      model=FakeContact, name='birthday',
                                                      date_range='empty',
                                                  ),
                                                 ],
                                      )

        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('misato', 'asuka', 'shinji', exclude=True))

    def test_date_field_not_empty(self):
        efilter = EntityFilter.create('test-filter01', name='Birthday is null', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_date(
                                                            model=FakeContact, name='birthday',
                                                            date_range='not_empty',
                                                  ),
                                                 ],
                                      )

        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('misato', 'asuka', 'shinji'))

    def test_build_date(self):
        "Errors"
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_date,
                          model=FakeContact, name='unknown_field', start=date(year=2001, month=1, day=1)
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_date,
                          model=FakeContact, name='first_name', start=date(year=2001, month=1, day=1)  # Not a date
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_date,
                          model=FakeContact, name='birthday',  # No date given
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_date,
                          model=FakeContact, name='birthday', date_range='unknown_range',
                         )

    def test_customfield01(self):
        "INT, only one CustomField, LTE operator"
        rei = self.contacts['rei']

        custom_field = CustomField.objects.create(name='size (cm)', content_type=self.contact_ct, field_type=CustomField.INT)
        custom_field.get_value_class()(custom_field=custom_field, entity=rei).set_value_n_save(150)
        custom_field.get_value_class()(custom_field=custom_field, entity=self.contacts['misato']).set_value_n_save(170)
        self.assertEqual(2, CustomFieldInteger.objects.count())

        efilter = EntityFilter.create('test-filter01', name='Small', model=FakeContact, is_custom=True)
        cond = EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                         operator=EntityFilterCondition.LTE,
                                                         value=[155]
                                                        )
        self.assertEqual(EntityFilterCondition.EFC_CUSTOMFIELD, cond.type)

        efilter.set_conditions([cond])
        self.assertExpectedFiltered(efilter, FakeContact, [rei.id])

    def test_customfield02(self):
        "2 INT CustomFields (can interfere), GTE operator"
        contacts = self.contacts
        asuka = contacts['asuka']

        custom_field01 = CustomField.objects.create(name='size (cm)', content_type=self.contact_ct, field_type=CustomField.INT)
        custom_field01.get_value_class()(custom_field=custom_field01, entity=contacts['rei']).set_value_n_save(150)
        custom_field01.get_value_class()(custom_field=custom_field01, entity=asuka).set_value_n_save(160)

        # Should not be retrieved, because filter is relative to 'custom_field01'
        custom_field02 = CustomField.objects.create(name='weight (pound)', content_type=self.contact_ct, field_type=CustomField.INT)
        custom_field02.get_value_class()(custom_field=custom_field02, entity=self.contacts['spike']).set_value_n_save(156)

        self.assertEqual(3, CustomFieldInteger.objects.count())

        efilter = EntityFilter.create('test-filter01', name='Not so small', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_customfield(
                                                      custom_field=custom_field01,
                                                      operator=EntityFilterCondition.GTE,
                                                      value=[155]
                                                  ),
                                                 ]
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, [asuka.id])

    def test_customfield03(self):
        "STR, CONTAINS_NOT operator (negate)"
        custom_field = CustomField.objects.create(name='Eva', content_type=self.contact_ct, field_type=CustomField.STR)
        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=self.contacts['rei']).set_value_n_save('Eva-00')
        klass(custom_field=custom_field, entity=self.contacts['shinji']).set_value_n_save('Eva-01')
        klass(custom_field=custom_field, entity=self.contacts['misato']).set_value_n_save('Eva-02')
        self.assertEqual(3, CustomFieldString.objects.count())

        efilter = EntityFilter.create('test-filter01', name='not 00', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_customfield(
                                                      custom_field=custom_field,
                                                      operator=EntityFilterCondition.CONTAINS_NOT,
                                                      value=['00'],
                                                  ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('rei', exclude=True))

        # Old filter format compatibility
        cfield_rname = custom_field.get_value_class().get_related_name()
        efilter = EntityFilter.create('test-filter01-old', name='not 00', model=FakeContact,
                                      conditions=[EntityFilterCondition(
                                                      type=EntityFilterCondition.EFC_CUSTOMFIELD,
                                                      name=str(custom_field.id),
                                                      value=EntityFilterCondition.encode_value({
                                                          'operator': EntityFilterCondition.CONTAINS_NOT,
                                                          'value': '00',
                                                          'rname': cfield_rname,
                                                      }),
                                                  ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('rei', exclude=True))

    def test_customfield04(self):
        "2 INT CustomFields with 2 conditions"
        contacts = self.contacts
        asuka = contacts['asuka']
        spike = contacts['spike']

        create_cf = partial(CustomField.objects.create, content_type=self.contact_ct, field_type=CustomField.INT)
        custom_field01 = create_cf(name='size (cm)')
        klass = custom_field01.get_value_class()
        klass(custom_field=custom_field01, entity=spike).set_value_n_save(180)
        klass(custom_field=custom_field01, entity=contacts['rei']).set_value_n_save(150)
        klass(custom_field=custom_field01, entity=asuka).set_value_n_save(160)

        custom_field02 = create_cf(name='weight (pound)')
        klass = custom_field02.get_value_class()
        klass(custom_field=custom_field02, entity=spike).set_value_n_save(156)
        klass(custom_field=custom_field02, entity=asuka).set_value_n_save(80)

        build_cond = EntityFilterCondition.build_4_customfield
        efilter = EntityFilter.create('test-filter01', name='Not so small but light', model=FakeContact,
                                      conditions=[build_cond(custom_field=custom_field01,
                                                             operator=EntityFilterCondition.GTE,
                                                             value=[155]
                                                            ),
                                                  build_cond(custom_field=custom_field02,
                                                             operator=EntityFilterCondition.LTE,
                                                             value=[100]
                                                            ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, [asuka.id])

        # Old filter format compatibility
        cfield01_rname = custom_field01.get_value_class().get_related_name()
        cfield02_rname = custom_field02.get_value_class().get_related_name()
        efilter = EntityFilter.create('test-filter01-old', name='Not so small but light', model=FakeContact,
                                      conditions=[EntityFilterCondition(type=EntityFilterCondition.EFC_CUSTOMFIELD,
                                                                        name=str(custom_field01.id),
                                                                        value=EntityFilterCondition.encode_value({
                                                                            'operator': EntityFilterCondition.GTE,
                                                                            'value': 155,
                                                                            'rname': cfield01_rname,
                                                                        })
                                                                       ),
                                                  EntityFilterCondition(type=EntityFilterCondition.EFC_CUSTOMFIELD,
                                                                        name=str(custom_field02.id),
                                                                        value=EntityFilterCondition.encode_value({
                                                                            'operator': EntityFilterCondition.LTE,
                                                                            'value': 100,
                                                                            'rname': cfield02_rname,
                                                                        })
                                                                       ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, [asuka.id])

    def test_customfield05(self):
        "FLOAT"
        contacts = self.contacts
        ed  = contacts['ed']
        rei = contacts['rei']

        custom_field = CustomField.objects.create(name='Weight (kg)',
                                                  content_type=self.contact_ct,
                                                  field_type=CustomField.FLOAT,
                                                 )
        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=ed).set_value_n_save('38.20')
        klass(custom_field=custom_field, entity=rei).set_value_n_save('40.00')
        klass(custom_field=custom_field, entity=contacts['asuka']).set_value_n_save('40.5')

        self.assertEqual(3, CustomFieldFloat.objects.count())

        efilter = EntityFilter.create('test-filter01', name='<= 40', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_customfield(
                                                            custom_field=custom_field,
                                                            operator=EntityFilterCondition.LTE,
                                                            value=['40']
                                                        ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, [ed.id, rei.id])

        # Old filter format compatibility
        cfield_rname = custom_field.get_value_class().get_related_name()
        efilter = EntityFilter.create('test-filter01-old', name='<= 40', model=FakeContact,
                                      conditions=[EntityFilterCondition(type=EntityFilterCondition.EFC_CUSTOMFIELD,
                                                                        name=str(custom_field.id),
                                                                        value=EntityFilterCondition.encode_value({
                                                                            'operator': EntityFilterCondition.LTE,
                                                                            'value': '40',
                                                                            'rname': cfield_rname,
                                                                        })
                                                                       ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, [ed.id, rei.id])

    def test_customfield_boolean(self):
        "Boolean field"
        contacts = self.contacts
        ed  = contacts['ed']
        rei = contacts['rei']

        custom_field = CustomField.objects.create(name='Is Valid ?',
                                                  content_type=self.contact_ct,
                                                  field_type=CustomField.BOOL,
                                                 )
        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=ed).set_value_n_save(True)
        klass(custom_field=custom_field, entity=rei).set_value_n_save(True)
        klass(custom_field=custom_field, entity=contacts['asuka']).set_value_n_save(False)

        self.assertEqual(3, CustomFieldBoolean.objects.count())

        efilter = EntityFilter.create('test-filter01', name='is valid', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_customfield(
                                                            custom_field=custom_field,
                                                            operator=EntityFilterCondition.EQUALS,
                                                            value=[True]
                                                        ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, [ed.id, rei.id])

        # Old filter format compatibility
        cfield_rname = custom_field.get_value_class().get_related_name()
        efilter = EntityFilter.create('test-filter01-old', name='is valid', model=FakeContact,
                                      conditions=[EntityFilterCondition(type=EntityFilterCondition.EFC_CUSTOMFIELD,
                                                                        name=str(custom_field.id),
                                                                        value=EntityFilterCondition.encode_value({
                                                                            'operator': EntityFilterCondition.EQUALS,
                                                                            'value': 'True',
                                                                            'rname': cfield_rname,
                                                                        })
                                                                       ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, [ed.id, rei.id])

    def test_customfield_boolean_false(self):
        "Boolean field"
        contacts = self.contacts
        ed  = contacts['ed']
        rei = contacts['rei']

        custom_field = CustomField.objects.create(name='Is Valid ?',
                                                  content_type=self.contact_ct,
                                                  field_type=CustomField.BOOL,
                                                 )
        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=ed).set_value_n_save(True)
        klass(custom_field=custom_field, entity=rei).set_value_n_save(True)
        klass(custom_field=custom_field, entity=contacts['asuka']).set_value_n_save(False)

        self.assertEqual(3, CustomFieldBoolean.objects.count())

        efilter = EntityFilter.create('test-filter01', name='is valid', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_customfield(
                                                            custom_field=custom_field,
                                                            operator=EntityFilterCondition.EQUALS,
                                                            value=[False]
                                                        ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, [contacts['asuka'].id])

        # Old filter format compatibility
        cfield_rname = custom_field.get_value_class().get_related_name()
        efilter = EntityFilter.create('test-filter01-old', name='is valid', model=FakeContact,
                                      conditions=[EntityFilterCondition(type=EntityFilterCondition.EFC_CUSTOMFIELD,
                                                                        name=str(custom_field.id),
                                                                        value=EntityFilterCondition.encode_value({
                                                                            'operator': EntityFilterCondition.EQUALS,
                                                                            'value': 'False',
                                                                            'rname': cfield_rname,
                                                                        })
                                                                       ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, [contacts['asuka'].id])

    def test_customfield06(self):
        "ENUM"
        rei = self.contacts['rei']

        custom_field = CustomField.objects.create(name='Eva',
                                                  content_type=self.contact_ct,
                                                  field_type=CustomField.ENUM,
                                                 )
        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=custom_field)
        eva00 = create_evalue(value='Eva-00')
        create_evalue(value='Eva-01')
        eva02 = create_evalue(value='Eva-02')

        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=rei).set_value_n_save(eva00.id)
        klass(custom_field=custom_field, entity=self.contacts['asuka']).set_value_n_save(eva02.id)

        self.assertEqual(2, CustomFieldEnum.objects.count())

        efilter = EntityFilter.create('test-filter01', name='Eva-00', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_customfield(
                                                         custom_field=custom_field,
                                                         operator=EntityFilterCondition.EQUALS,
                                                         value=[eva00.id],  # TODO: "value=eva00"
                                                        ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, [rei.id])

        # Old filter format compatibility
        cfield_rname = custom_field.get_value_class().get_related_name()
        efilter = EntityFilter.create('test-filter01-old', name='Eva-00', model=FakeContact,
                                      conditions=[EntityFilterCondition(type=EntityFilterCondition.EFC_CUSTOMFIELD,
                                                                        name=str(custom_field.id),
                                                                        value=EntityFilterCondition.encode_value({
                                                                            'operator': EntityFilterCondition.EQUALS,
                                                                            'value': eva00.id,
                                                                            'rname': cfield_rname,
                                                                        })
                                                                       ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, [rei.id])

    def test_customfield_enum_multiple(self):
        "ENUM"
        rei = self.contacts['rei']
        asuka = self.contacts['asuka']
        shinji = self.contacts['shinji']

        custom_field = CustomField.objects.create(name='Eva',
                                                  content_type=self.contact_ct,
                                                  field_type=CustomField.ENUM,
                                                 )
        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=custom_field)
        eva00 = create_evalue(value='Eva-00')
        eva01 = create_evalue(value='Eva-01')
        eva02 = create_evalue(value='Eva-02')

        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=rei).set_value_n_save(eva00.id)
        klass(custom_field=custom_field, entity=asuka).set_value_n_save(eva02.id)
        klass(custom_field=custom_field, entity=shinji).set_value_n_save(eva01.id)

        self.assertEqual(3, CustomFieldEnum.objects.count())

        efilter = EntityFilter.create('test-filter01', name='Eva-00', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_customfield(
                                                         custom_field=custom_field,
                                                         operator=EntityFilterCondition.EQUALS,
                                                         value=[eva00.id, eva02.id],  # TODO: "value=eva00"
                                                        ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, [rei.id, asuka.id])

    def test_customfield07(self):
        "BOOL"
        rei = self.contacts['rei']

        custom_field = CustomField.objects.create(name='cute ??',
                                                  content_type=self.contact_ct,
                                                  field_type=CustomField.BOOL,
                                                 )
        value_class = custom_field.get_value_class()
        value_class(custom_field=custom_field, entity=rei).set_value_n_save(True)
        value_class(custom_field=custom_field, entity=self.contacts['jet']).set_value_n_save(False)
        self.assertEqual(2, CustomFieldBoolean.objects.count())

        efilter = EntityFilter.create('test-filter01', name='Cuties', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_customfield(
                                                            custom_field=custom_field,
                                                            operator=EntityFilterCondition.EQUALS,
                                                            value=[True],
                                                           ),
                                                 ]
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, [rei.id])

        efilter = EntityFilter.create('test-filter02', name='Cuties', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_customfield(
                                                            custom_field=custom_field,
                                                            operator=EntityFilterCondition.EQUALS_NOT,
                                                            value=[True],
                                                           ),
                                                 ]
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('rei', exclude=True))

    def test_customfield_boolean_unsupported(self):
        "BOOL"
        rei = self.contacts['rei']

        custom_field = CustomField.objects.create(name='cute ??', content_type=self.contact_ct, field_type=CustomField.BOOL)
        value_class = custom_field.get_value_class()
        value_class(custom_field=custom_field, entity=rei).set_value_n_save(True)
        value_class(custom_field=custom_field, entity=self.contacts['jet']).set_value_n_save(False)
        self.assertEqual(2, CustomFieldBoolean.objects.count())

        with self.assertRaises(EntityFilterCondition.ValueError) as err:
            EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                      operator=EntityFilterCondition.GT,
                                                      value=[True])

        self.assertEqual(str(err.exception),
                         'build_4_customfield(): '
                         'BOOL type is only compatible with EQUALS, EQUALS_NOT and ISEMPTY operators'
                        )

    def test_customfield08(self):
        "CustomField is deleted"
        create_cf = partial(CustomField.objects.create, content_type=self.contact_ct, field_type=CustomField.INT)
        custom_field01 = create_cf(name='Size (cm)')
        custom_field02 = create_cf(name='IQ')

        efilter = EntityFilter.create('test-filter01', name='Small', model=FakeContact, is_custom=True)
        build = partial(EntityFilterCondition.build_4_customfield, operator=EntityFilterCondition.LTE, value=[155])
        efilter.set_conditions([build(custom_field=custom_field01),
                                build(custom_field=custom_field02),
                               ])

        custom_field01.delete()
        self.assertEqual([unicode(custom_field02.id)], [cond.name for cond in efilter.conditions.all()])

    def test_customfield_number_isempty(self):
        rei = self.contacts['rei']

        custom_field = CustomField.objects.create(name='Weight (kg)',
                                                  content_type=self.contact_ct,
                                                  field_type=CustomField.FLOAT,
                                                 )
        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=rei).set_value_n_save('40.00')
        klass(custom_field=custom_field, entity=self.contacts['asuka']).set_value_n_save('40.5')

        self.assertEqual(2, CustomFieldFloat.objects.count())

        efilter = EntityFilter.create('test-filter01', name='empty', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_customfield(
                                                         custom_field=custom_field,
                                                         operator=EntityFilterCondition.ISEMPTY,
                                                         value=[True]
                                                        ),
                                                 ]
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('rei', 'asuka', exclude=True))

        efilter = EntityFilter.create('test-filter02', name='not empty', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_customfield(
                                                         custom_field=custom_field,
                                                         operator=EntityFilterCondition.ISEMPTY,
                                                         value=[False],
                                                        ),
                                                 ]
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('rei', 'asuka'))

    def test_customfield_enum_isempty(self):
        rei = self.contacts['rei']

        custom_field = CustomField.objects.create(name='Eva',
                                                  content_type=self.contact_ct,
                                                  field_type=CustomField.ENUM,
                                                 )
        create_evalue = CustomFieldEnumValue.objects.create
        eva00 = create_evalue(custom_field=custom_field, value='Eva-00')

        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=rei).set_value_n_save(eva00.id)
        klass(custom_field=custom_field, entity=self.contacts['asuka']).set_value_n_save(eva00.id)

        self.assertEqual(2, CustomFieldEnum.objects.count())

        efilter = EntityFilter.create('test-filter01', name='empty', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_customfield(
                                                         custom_field=custom_field,
                                                         operator=EntityFilterCondition.ISEMPTY,
                                                         value=[True],
                                                        ),
                                                 ]
                                      )

        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('rei', 'asuka', exclude=True))

        efilter = EntityFilter.create('test-filter02', name='not empty', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_customfield(
                                                         custom_field=custom_field,
                                                         operator=EntityFilterCondition.ISEMPTY,
                                                         value=[False]
                                                        ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('rei', 'asuka'))

    def test_customfield_string_isempty(self):
        custom_field = CustomField.objects.create(name='Eva',
                                                  content_type=self.contact_ct,
                                                  field_type=CustomField.STR,
                                                 )
        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=self.contacts['rei']).set_value_n_save('Eva-00')
        klass(custom_field=custom_field, entity=self.contacts['shinji']).set_value_n_save('Eva-01')

        self.assertEqual(2, CustomFieldString.objects.count())

        efilter = EntityFilter.create('test-filter01', name='empty', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_customfield(
                                                            custom_field=custom_field,
                                                            operator=EntityFilterCondition.ISEMPTY,
                                                            value=[True],
                                                           )
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('rei', 'shinji', exclude=True))

        efilter = EntityFilter.create('test-filter01', name='not empty', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_customfield(
                                                        custom_field=custom_field,
                                                        operator=EntityFilterCondition.ISEMPTY,
                                                        value=[False],
                                                       ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('rei', 'shinji'))

    def test_customfield_boolean_isempty(self):
        custom_field = CustomField.objects.create(name='Eva ?',
                                                  content_type=self.contact_ct,
                                                  field_type=CustomField.BOOL,
                                                 )
        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=self.contacts['rei']).set_value_n_save(True)
        klass(custom_field=custom_field, entity=self.contacts['shinji']).set_value_n_save(True)
        klass(custom_field=custom_field, entity=self.contacts['asuka']).set_value_n_save(True)

        self.assertEqual(3, CustomFieldBoolean.objects.count())

        efilter = EntityFilter.create('test-filter01', name='empty', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_customfield(
                                                            custom_field=custom_field,
                                                            operator=EntityFilterCondition.ISEMPTY,
                                                            value=[True],
                                                           )
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('rei', 'shinji', 'asuka', exclude=True))

        efilter = EntityFilter.create('test-filter01', name='not empty', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_customfield(
                                                        custom_field=custom_field,
                                                        operator=EntityFilterCondition.ISEMPTY,
                                                        value=[False],
                                                       ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('rei', 'shinji', 'asuka'))

    def test_build_customfield(self):
        "Errors"
        create_cf = partial(CustomField.objects.create, content_type=self.contact_ct)
        cf_int = create_cf(name='size (cm)', field_type=CustomField.INT)
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_customfield,
                          custom_field=cf_int, operator=1216, value=155  # Invalid operator
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_customfield,
                          custom_field=cf_int, operator=EntityFilterCondition.CONTAINS, value='not an int'
                         )

        cf_date = create_cf(name='Day', field_type=CustomField.DATETIME)
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_customfield,
                          custom_field=cf_date, operator=EntityFilterCondition.EQUALS, value=2011  # DATE
                         )

        cf_bool = create_cf(name='Cute ?', field_type=CustomField.BOOL)
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_customfield,
                          custom_field=cf_bool, operator=EntityFilterCondition.CONTAINS, value=True  # Bad operator
                         )

    def _aux_test_datecf(self):
        custom_field = CustomField.objects.create(name='First fight',
                                                  content_type=self.contact_ct,
                                                  field_type=CustomField.DATETIME,
                                                 )

        contacts = self.contacts
        klass = partial(custom_field.get_value_class(), custom_field=custom_field)
        create_dt = self.create_datetime
        klass(entity=contacts['rei']).set_value_n_save(create_dt(year=2015, month=3, day=14))
        klass(entity=contacts['shinji']).set_value_n_save(create_dt(year=2015, month=4, day=21))
        klass(entity=contacts['asuka']).set_value_n_save(create_dt(year=2015, month=5, day=3))
        self.assertEqual(3, CustomFieldDateTime.objects.count())

        return custom_field

    def test_datecustomfield01(self):
        "GTE operator"
        custom_field = self._aux_test_datecf()

        efilter = EntityFilter.create('test-filter01', 'After April', FakeContact, is_custom=True)
        cond = EntityFilterCondition.build_4_datecustomfield(custom_field=custom_field,
                                                             start=date(year=2015, month=4, day=1),
                                                            )
        self.assertEqual(EntityFilterCondition.EFC_DATECUSTOMFIELD, cond.type)

        efilter.set_conditions([cond])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('asuka', 'shinji'))

    def test_datecustomfield02(self):
        "LTE operator"
        custom_field = self._aux_test_datecf()

        efilter = EntityFilter.create('test-filter01', 'Before May', FakeContact,
                                      conditions=[EntityFilterCondition.build_4_datecustomfield(
                                                        custom_field=custom_field,
                                                        end=date(year=2015, month=5, day=1),
                                                       ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('shinji', 'rei'))

    def test_datecustomfield03(self):
        "Range"
        custom_field = self._aux_test_datecf()

        efilter = EntityFilter.create('test-filter01', 'In April', FakeContact,
                                      conditions=[EntityFilterCondition.build_4_datecustomfield(
                                                        custom_field=custom_field,
                                                        start=date(year=2015, month=4, day=1),
                                                        end=date(year=2015, month=4, day=30),
                                                       ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['shinji'].id])

    def test_datecustomfield04(self):
        "Relative to now"
        custom_field = CustomField.objects.create(name='First flight',
                                                  content_type=self.contact_ct,
                                                  field_type=CustomField.DATETIME,
                                                 )

        contacts = self.contacts
        spike = contacts['spike']
        jet   = contacts['jet']
        dt_now = now()

        klass = partial(custom_field.get_value_class(), custom_field=custom_field)
        klass(entity=contacts['faye']).set_value_n_save(self.create_datetime(year=2000, month=3, day=14))
        klass(entity=spike).set_value_n_save(dt_now + timedelta(days=3650))
        klass(entity=jet).set_value_n_save(dt_now + timedelta(days=700))

        efilter = EntityFilter.create('test-filter01', name='In the future', model=FakeContact,
                                      conditions=[EntityFilterCondition.build_4_datecustomfield(
                                                            custom_field=custom_field,
                                                            date_range='in_future'
                                                           ),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, [spike.id, jet.id])

    def test_datecustomfield05(self):
        "2 DATE CustomFields with 2 conditions"
        contacts = self.contacts
        shinji = contacts['shinji']
        custom_field01 = self._aux_test_datecf()
        custom_field02 = CustomField.objects.create(name='Last fight',
                                                    content_type=self.contact_ct,
                                                    field_type=CustomField.DATETIME,
                                                   )

        klass = partial(custom_field02.get_value_class(), custom_field=custom_field02)
        create_dt = self.create_datetime
        klass(entity=contacts['rei']).set_value_n_save(create_dt(year=2020, month=3, day=14))
        klass(entity=shinji).set_value_n_save(create_dt(year=2030, month=4, day=21))
        klass(entity=contacts['asuka']).set_value_n_save(create_dt(year=2040, month=5, day=3))

        build_cond = EntityFilterCondition.build_4_datecustomfield
        efilter = EntityFilter.create('test-filter01', 'Complex filter', FakeContact, use_or=False,
                                      conditions=[build_cond(custom_field=custom_field01, start=date(year=2015, month=4, day=1)),
                                                  build_cond(custom_field=custom_field02, end=date(year=2040, month=1, day=1)),
                                                 ],
                                      )
        self.assertExpectedFiltered(efilter, FakeContact, [shinji.id])

    def test_build_datecustomfield(self):
        "Errors"
        create_cf = partial(CustomField.objects.create, content_type=self.contact_ct)
        custom_field = create_cf(name='First flight', field_type=CustomField.INT)  # Not a DATE
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_datecustomfield,
                          custom_field=custom_field, date_range='in_future',
                         )

        custom_field = create_cf(name='Day', field_type=CustomField.DATETIME)
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_datecustomfield,
                          custom_field=custom_field,  # No date is given
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_datecustomfield,
                          custom_field=custom_field, date_range='unknown_range',
                         )

    def test_invalid_field(self):
        efilter = EntityFilter.create('test-filter01', 'Ikari', FakeContact, is_custom=True)
        build = partial(EntityFilterCondition.build_4_field, model=FakeContact,
                        operator=EntityFilterCondition.EQUALS, values=['Ikari'],
                        )
        cond1 = build(name='last_name')
        cond2 = build(name='first_name')
        cond2.name = 'invalid'

        efilter.set_conditions([cond1, cond2])

        with self.assertNoException():
            filtered = list(efilter.filter(FakeContact.objects.all()))

        self.assertDoesNotExist(cond2)
        self.assertEqual(set(self._get_ikari_case_sensitive()), {c.id for c in filtered})

        self.assertEqual(1, len(efilter.get_conditions()))

    def test_invalid_datefield(self):
        efilter = EntityFilter.create('test-filter01', 'Ikari', FakeContact, is_custom=True)
        cond1 = EntityFilterCondition.build_4_field(model=FakeContact, name='last_name',
                                                    operator=EntityFilterCondition.EQUALS,
                                                    values=['Ikari'],
                                                   )
        cond2 = EntityFilterCondition.build_4_date(model=FakeContact, name='birthday',
                                                   start=date(year=2000, month=1, day=1),
                                                  )
        cond2.name = 'invalid'

        efilter.set_conditions([cond1, cond2])
        self.assertEqual(1, len(efilter.get_conditions()))

        with self.assertNoException():
            filtered = list(efilter.filter(FakeContact.objects.all()))

        self.assertDoesNotExist(cond2)
        self.assertEqual(set(self._get_ikari_case_sensitive()), {c.id for c in filtered})

    def test_invalid_currentuser(self):
        efilter = EntityFilter.create('test-filter01', 'Spike & Faye', FakeContact, is_custom=True)

        with self.assertRaises(EntityFilterCondition.ValueError):
            efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                        operator=EntityFilterCondition.EQUALS,
                                                                        name='birthday',
                                                                        values=['__currentuser__']
                                                                       ),
                                   ])

        with self.assertNoException():
            efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                        operator=EntityFilterCondition.EQUALS,
                                                                        name='last_name',
                                                                        values=['__currentuser__']
                                                                       ),
                                   ])

    def test_invalid_subfilter(self):
        build_4_field = partial(EntityFilterCondition.build_4_field, model=FakeContact, operator=EntityFilterCondition.CONTAINS)
        sub_efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=FakeContact,
                                          conditions=[build_4_field(name='last_name',  values=['Spiegel'])],
                                         )

        sub_cond = EntityFilterCondition.build_4_subfilter(sub_efilter)
        with self.assertNumQueries(0):
            error = sub_cond.error
        self.assertIsNone(error)

        efilter = EntityFilter.create(pk='test-filter02', name='Filter02', model=FakeContact,
                                      conditions=[build_4_field(name='first_name', values=['Spi']),
                                                  sub_cond,
                                                 ],
                                      )

        EntityFilter.objects.filter(pk=sub_efilter.pk).delete()
        self.assertDoesNotExist(sub_efilter)
        efilter = self.assertStillExists(efilter)

        conditions = efilter.get_conditions()
        self.assertEqual(1, len(conditions))

    def test_invalid_relations_subfilter(self):
        loves = self._aux_test_relations()

        build_4_field = partial(EntityFilterCondition.build_4_field, model=FakeContact, operator=EntityFilterCondition.EQUALS)
        sub_efilter = EntityFilter.create(pk='test-filter01', name='Filter Rei', model=FakeContact,
                                          conditions=[build_4_field(name='last_name', values=['Ayanami'])],
                                         )

        sub_cond = EntityFilterCondition.build_4_relation_subfilter(rtype=loves, has=True, subfilter=sub_efilter)
        with self.assertNumQueries(0):
            error = sub_cond.error
        self.assertIsNone(error)

        efilter = EntityFilter.create(pk='test-filter02', name='Filter Rei lovers', model=FakeContact,
                                      conditions=[build_4_field(name='first_name', values=['rei']),
                                                  sub_cond,
                                                 ],
                                     )

        EntityFilter.objects.filter(pk=sub_efilter.pk).delete()
        self.assertDoesNotExist(sub_efilter)
        efilter = self.assertStillExists(efilter)

        conditions = efilter.get_conditions()
        self.assertEqual(1, len(conditions))

    def test_get_for_user(self):
        user = self.user
        create_ef = partial(EntityFilter.create, name='Misatos',
                            model=FakeContact,
                            conditions=[EntityFilterCondition.build_4_field(
                                                model=FakeContact,
                                                operator=EntityFilterCondition.EQUALS,
                                                name='first_name', values=['Misato'],
                                            ),
                                       ],
                           )

        ef1 = create_ef(pk='test-ef_contact1')
        ef2 = create_ef(pk='test-ef_contact2', user=user)
        ef3 = create_ef(pk='test-ef_orga', model=FakeOrganisation, name='NERV',
                        conditions=[EntityFilterCondition.build_4_field(
                                            model=FakeOrganisation,
                                            operator=EntityFilterCondition.IEQUALS,
                                            name='name', values=['NERV'],
                                        ),
                                   ],
                        )
        ef4 = create_ef(pk='test-ef_contact3', user=self.other_user)
        ef5 = create_ef(pk='test-ef_contact4', user=self.other_user,
                        is_private=True, is_custom=True,
                       )

        efilters = EntityFilter.get_for_user(user, self.contact_ct)
        self.assertIsInstance(efilters, QuerySet)

        efilters_set = set(efilters)
        self.assertIn(ef1, efilters_set)
        self.assertIn(ef2, efilters_set)
        self.assertIn(ef4, efilters_set)

        self.assertNotIn(ef3, efilters_set)
        self.assertNotIn(ef5, efilters_set)

        # ----
        orga_ct = ContentType.objects.get_for_model(FakeOrganisation)
        orga_efilters_set = set(EntityFilter.get_for_user(user, orga_ct))
        self.assertIn(ef3, orga_efilters_set)

        self.assertNotIn(ef1, orga_efilters_set)
        self.assertNotIn(ef2, orga_efilters_set)
        self.assertNotIn(ef4, orga_efilters_set)
        self.assertNotIn(ef5, orga_efilters_set)

        # ----
        persons_efilters_set = set(EntityFilter.get_for_user(user, (self.contact_ct, orga_ct)))
        self.assertIn(ef1, persons_efilters_set)
        self.assertIn(ef3, persons_efilters_set)

        self.assertEqual(persons_efilters_set,
                         set(EntityFilter.get_for_user(user, [self.contact_ct, orga_ct]))
                        )

    def test_filterlist01(self):
        user = self.user
        create_ef = partial(EntityFilter.create, name='Misatos',
                            model=FakeContact,
                            conditions=[EntityFilterCondition.build_4_field(
                                                model=FakeContact,
                                                operator=EntityFilterCondition.EQUALS,
                                                name='first_name', values=['Misato'],
                                            ),
                                       ]
                            )

        ef1 = create_ef(pk='test-ef_contact1')
        ef2 = create_ef(pk='test-ef_contact2', user=user)
        ef3 = create_ef(pk='test-ef_orga', model=FakeOrganisation, name='NERV',
                        conditions=[EntityFilterCondition.build_4_field(
                                            model=FakeOrganisation,
                                            operator=EntityFilterCondition.IEQUALS,
                                            name='name', values=['NERV'],
                                        ),
                                   ],
                        )
        ef4 = create_ef(pk='test-ef_contact3', user=self.other_user)

        ct = self.contact_ct
        efl = EntityFilterList(ct, user)
        self.assertIn(ef1, efl)
        self.assertIn(ef2, efl)
        self.assertIn(ef4, efl)
        self.assertEqual(ef1, efl.select_by_id(ef1.id))
        self.assertEqual(ef2, efl.select_by_id(ef2.id))
        self.assertEqual(ef2, efl.select_by_id('unknown_id', ef2.id))

        self.assertEqual(ef1.can_view(user), (True, 'OK'))
        self.assertEqual(ef1.can_view(user, ct), (True, 'OK'))

        self.assertEqual(ef3.can_view(user, ct), (False, 'Invalid entity type'))
        self.assertNotIn(ef3, efl)

    def test_filterlist02(self):
        "Private filters + not super user (+ team management)"
        self.client.logout()

        super_user = self.other_user
        other_user = self.user

        logged = self.client.login(username=super_user.username, password=self.password)
        self.assertTrue(logged)

        User = get_user_model()
        teammate = User.objects.create(username='fulbertc',
                                       email='fulbnert@creme.org', role=self.role,
                                       first_name='Fulbert', last_name='Creme',
                                      )

        tt_team = User.objects.create(username='TeamTitan', is_team=True)
        tt_team.teammates = [super_user, teammate]

        a_team = User.objects.create(username='A-Team', is_team=True)
        a_team.teammates = [other_user]

        conditions = [EntityFilterCondition.build_4_field(
                            model=FakeContact,
                            operator=EntityFilterCondition.EQUALS,
                            name='first_name', values=['Misato'],
                        ),
                     ]

        def create_ef(id, **kwargs):
            return EntityFilter.create(pk='test-ef_contact%s' % id,
                                       name='Filter #%s' % id,
                                       model=FakeContact, conditions=conditions,
                                       **kwargs
                                      )

        ef01 = create_ef(1)
        ef02 = create_ef(2,  user=super_user)
        ef03 = create_ef(3,  user=other_user)
        ef04 = create_ef(4,  user=tt_team)
        ef05 = create_ef(5,  user=a_team)
        ef06 = create_ef(6,  user=super_user, is_private=True, is_custom=True)
        ef07 = create_ef(7,  user=tt_team,    is_private=True, is_custom=True)
        ef08 = create_ef(8,  user=other_user, is_private=True, is_custom=True)
        ef09 = create_ef(9,  user=a_team,     is_private=True, is_custom=True)
        ef10 = create_ef(10, user=teammate,   is_private=True, is_custom=True)

        self.assertEqual(ef01.can_view(super_user), (True, 'OK'))
        self.assertIs(ef08.can_view(super_user)[0], False)

        efl = EntityFilterList(self.contact_ct, super_user)
        self.assertIn(ef01, efl)
        self.assertIn(ef02, efl)
        self.assertIn(ef03, efl)
        self.assertIn(ef04, efl)
        self.assertIn(ef05, efl)
        self.assertIn(ef06, efl)
        self.assertIn(ef07, efl)
        self.assertNotIn(ef08, efl)
        self.assertNotIn(ef09, efl)
        self.assertNotIn(ef10, efl)

    def test_filterlist03(self):
        "Staff user -> can see all filters"
        user = self.user
        user.is_staff = True
        user.save()

        other_user = self.other_user

        conditions = [EntityFilterCondition.build_4_field(
                            model=FakeContact,
                            operator=EntityFilterCondition.EQUALS,
                            name='first_name', values=['Misato'],
                        ),
                     ]

        def create_ef(id, **kwargs):
            return EntityFilter.create(pk='test-ef_contact%s' % id,
                                       name='Filter #%s' % id,
                                       model=FakeContact, conditions=conditions,
                                       **kwargs
                                      )

        ef1 = create_ef(1)

        with self.assertRaises(ValueError):
            create_ef(2, user=user)

        ef3 = create_ef(3, user=other_user)

        # This one can not be seen by not staff users
        ef4 = create_ef(4, user=other_user, is_private=True, is_custom=True)

        efl = EntityFilterList(self.contact_ct, user)
        self.assertIn(ef1, efl)
        self.assertIn(ef3, efl)
        self.assertIn(ef4, efl)
