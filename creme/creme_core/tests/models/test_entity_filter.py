# -*- coding: utf-8 -*-

from datetime import date, timedelta
from functools import partial
from logging import info

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models.query import QuerySet
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme import __version__
from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    EF_USER,
    entity_filter_registries,
    operands,
    operators,
)
from creme.creme_core.core.entity_filter.condition_handler import (
    CustomFieldConditionHandler,
    DateCustomFieldConditionHandler,
    DateRegularFieldConditionHandler,
    PropertyConditionHandler,
    RegularFieldConditionHandler,
    RelationConditionHandler,
    RelationSubFilterConditionHandler,
    SubFilterConditionHandler,
)
from creme.creme_core.global_info import set_global_info
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    CremeUser,
    CustomField,
    CustomFieldBoolean,
    CustomFieldDateTime,
    CustomFieldEnum,
    CustomFieldEnumValue,
    CustomFieldFloat,
    CustomFieldInteger,
    CustomFieldString,
    EntityFilter,
    EntityFilterCondition,
    FakeCivility,
    FakeContact,
    FakeImage,
    FakeOrganisation,
    Language,
    Relation,
    RelationType,
)
from creme.creme_core.models.entity_filter import EntityFilterList

from ..base import CremeTestCase


class EntityFiltersTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._excluded_ids = frozenset(CremeEntity.objects.values_list('id', flat=True))

    def setUp(self):
        super().setUp()
        user = self.login()

        create = partial(FakeContact.objects.create, user=user)

        create_civ = FakeCivility.objects.create
        self.civ_miss   = miss   = create_civ(title='Miss')
        self.civ_mister = mister = create_civ(title='Mister')

        self.contacts = {
            'spike':  create(first_name='Spike', last_name='Spiegel', civility=mister),
            'jet':    create(first_name='Jet',   last_name='Black',   civility=mister),
            'faye':   create(
                first_name='Faye',   last_name='Valentine', civility=miss,
                description='Sexiest woman is the universe',
            ),
            'ed':     create(first_name='Ed',     last_name='Wong', description=''),
            'rei':    create(first_name='Rei',    last_name='Ayanami'),
            'misato': create(
                first_name='Misato', last_name='Katsuragi',
                birthday=date(year=1986, month=12, day=8),
            ),
            'asuka':  create(
                first_name='Asuka', last_name='Langley',
                birthday=date(year=2001, month=12, day=4),
            ),
            'shinji': create(
                first_name='Shinji', last_name='Ikari',
                birthday=date(year=2001, month=6, day=6),
            ),
            'yui':    create(first_name='Yui',    last_name='Ikari'),
            'gendou': create(first_name='Gendô',  last_name='IKARI'),
            'genji':  create(first_name='Genji',  last_name='Ikaru'),
            'risato': create(first_name='Risato', last_name='Katsuragu'),
        }

        self.contact_ct = ContentType.objects.get_for_model(FakeContact)

    def assertExpectedFiltered(
            self,
            efilter, model, ids, case_insensitive=False, use_distinct=False):
        msg = (
            '(NB: maybe you have case sensitive problems with your DB configuration).'
            if case_insensitive else ''
        )

        from creme.creme_core.utils.profiling import CaptureQueriesContext
        context = CaptureQueriesContext()

        with context:
            filtered = [*efilter.filter(model.objects.exclude(id__in=self._excluded_ids))]

        self.assertEqual(len(ids), len(filtered), str(filtered) + msg)
        self.assertSetEqual({*ids}, {c.id for c in filtered})

        if use_distinct:
            for query_info in context.captured_queries:
                if 'DISTINCT' in query_info['sql']:
                    break
            else:
                self.fail('No DISTINCT found')

        else:
            for query_info in context.captured_queries:
                self.assertNotIn('DISTINCT', query_info['sql'])

    @staticmethod
    def _get_ikari_case_sensitive():
        ikaris = FakeContact.objects.filter(last_name__exact='Ikari')

        if len(ikaris) == 3:
            info('INFO: your DB is Case insensitive')

        return [ikari.id for ikari in ikaris]

    def _list_contact_ids(self, *short_names, **kwargs):
        contacts = self.contacts

        if kwargs.get('exclude', False):
            excluded = frozenset(short_names)
            ids = [c.id for sn, c in contacts.items() if sn not in excluded]
        else:
            ids = [contacts[sn].id for sn in short_names]

        return ids

    # def test_create(self):  # DEPRECATED
    #     "Custom=False."
    #     pk = 'test-filter01'
    #     name = 'Ikari family'
    #     model = FakeContact
    #     fname = 'last_name'
    #     operator_id = operators.EQUALS
    #     value = 'Ikari'
    #
    #     with self.assertRaises(ValueError):
    #         EntityFilter.create(pk, name, model)
    #
    #     efilter = EntityFilter.create(
    #         pk, name, model,
    #         conditions=[
    #             RegularFieldConditionHandler.build_condition(
    #                 model=FakeContact,
    #                 operator=operator_id,
    #                 field_name=fname, values=[value],
    #             ),
    #         ],
    #     )
    #
    #     self.assertIsInstance(efilter, EntityFilter)
    #     self.assertEqual(pk,      efilter.id)
    #     self.assertEqual(name,    efilter.name)
    #     self.assertEqual(EF_USER, efilter.filter_type)
    #     self.assertEqual(model, efilter.entity_type.model_class())
    #     self.assertIsNone(efilter.user)
    #     self.assertIs(efilter.use_or,     False)
    #     self.assertIs(efilter.is_custom,  False)
    #     self.assertIs(efilter.is_private, False)
    #
    #     self.assertEqual(entity_filter_registries[EF_USER], efilter.registry)
    #
    #     conditions = efilter.conditions.all()
    #     self.assertEqual(1, len(conditions))
    #
    #     condition = conditions[0]
    #     self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
    #     self.assertEqual(fname,                                condition.name)
    #     self.assertEqual(
    #         {'operator': operator_id, 'values': [value]}, condition.value,
    #     )
    #
    #     self.assertTrue(efilter.entities_are_distinct)
    #
    #     handler = condition.handler
    #     self.assertIsInstance(handler, RegularFieldConditionHandler)
    #     self.assertEqual(fname,       handler._field_name)
    #     self.assertEqual(operator_id, handler._operator_id)
    #     self.assertEqual([value],     handler._values)

    def test_manager_smart_update_or_create01(self):
        "Custom=False."
        pk = 'test-filter01'
        name = 'Ikari family'
        model = FakeContact
        fname = 'last_name'
        operator_id = operators.EQUALS
        value = 'Ikari'

        with self.assertRaises(ValueError):
            EntityFilter.objects.smart_update_or_create(pk, name, model)

        efilter = EntityFilter.objects.smart_update_or_create(
            pk, name, model,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operator_id,
                    field_name=fname, values=[value],
                ),
            ],
        )

        self.assertIsInstance(efilter, EntityFilter)
        self.assertEqual(pk,      efilter.id)
        self.assertEqual(name,    efilter.name)
        self.assertEqual(EF_USER, efilter.filter_type)
        self.assertEqual(model, efilter.entity_type.model_class())
        self.assertIsNone(efilter.user)
        self.assertIs(efilter.use_or,     False)
        self.assertIs(efilter.is_custom,  False)
        self.assertIs(efilter.is_private, False)

        self.assertEqual(entity_filter_registries[EF_USER], efilter.registry)

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(fname,                                condition.name)
        self.assertEqual(
            {'operator': operator_id, 'values': [value]}, condition.value,
        )

        self.assertTrue(efilter.entities_are_distinct)

        handler = condition.handler
        self.assertIsInstance(handler, RegularFieldConditionHandler)
        self.assertEqual(fname,       handler._field_name)
        self.assertEqual(operator_id, handler._operator_id)
        self.assertEqual([value],     handler._values)

    def test_manager_smart_update_or_create02(self):
        "A owner, custom filter."
        pk = 'test-filter_nerv'
        name = 'Nerv'
        model = FakeOrganisation
        user = self.user
        efilter = EntityFilter.objects.smart_update_or_create(
            pk, name, model, user=user, use_or=True,
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

    def test_manager_smart_update_or_create03(self):
        "'admin' owner."
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Misato', FakeContact, user='admin', is_custom=True,
        )
        owner = efilter.user
        self.assertTrue(owner.is_superuser)
        self.assertFalse(owner.is_staff)

    def test_manager_smart_update_or_create04(self):
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
            return EntityFilter.objects.smart_update_or_create(
                f'creme_core-subfilter{idx}', 'Misato', model=FakeContact,
                user=owner, is_private=True, is_custom=True,
                conditions=[
                    RegularFieldConditionHandler.build_condition(
                        model=FakeContact,
                        operator=operators.EQUALS,
                        field_name='first_name', values=['Misato'],
                    ),
                ],
            )

        subfilter1 = create_subfilter(1, other_user)
        subfilter2 = create_subfilter(2, user)
        subfilter3 = create_subfilter(3, other_team)
        subfilter4 = create_subfilter(4, team)

        cond1 = RegularFieldConditionHandler.build_condition(
            model=FakeContact, field_name='last_name',
            operator=operators.EQUALS, values=['Katsuragi'],
        )

        build_subfilter_cond = SubFilterConditionHandler.build_condition

        with self.assertRaises(EntityFilter.PrivacyError):
            EntityFilter.objects.smart_update_or_create(
                'creme_core-filter1', 'Misato Katsuragi', model=FakeContact,
                is_custom=True,
                conditions=[cond1, build_subfilter_cond(subfilter1)],
            )

        with self.assertRaises(EntityFilter.PrivacyError):
            EntityFilter.objects.smart_update_or_create(
                'creme_core-filter2', 'Misato Katsuragi', model=FakeContact,
                user=user, is_private=True, is_custom=True,
                conditions=[cond1, build_subfilter_cond(subfilter1)],
            )

        with self.assertNoException():
            EntityFilter.objects.smart_update_or_create(
                'creme_core-filter3', 'Misato Katsuragi', model=FakeContact,
                user=user, is_private=True, is_custom=True,
                conditions=[cond1, build_subfilter_cond(subfilter2)],
            )

        with self.assertRaises(EntityFilter.PrivacyError):
            EntityFilter.objects.smart_update_or_create(
                'creme_core-filter4', 'Misato Katsuragi', model=FakeContact,
                user=user, is_private=True, is_custom=True,
                conditions=[cond1, build_subfilter_cond(subfilter3)],
            )

        with self.assertNoException():
            EntityFilter.objects.smart_update_or_create(
                'creme_core-filter5', 'Misato Katsuragi', model=FakeContact,
                user=user, is_private=True, is_custom=True,
                conditions=[cond1, build_subfilter_cond(subfilter4)],
            )

    # def test_get_latest_version(self):  # DEPRECATED
    #     base_pk = 'creme_core-testfilter'
    #
    #     with self.assertRaises(EntityFilter.DoesNotExist):
    #         EntityFilter.get_latest_version(base_pk)
    #
    #     create_ef = partial(EntityFilter.objects.create,
    #                         entity_type=ContentType.objects.get_for_model(FakeContact),
    #                        )
    #
    #     create_ef(pk=base_pk, name='Base filter')
    #
    #     efilter2 = create_ef(pk=base_pk + '[1.5]', name='Filter [1.5]')
    #     self.assertEqual(efilter2, EntityFilter.get_latest_version(base_pk))
    #
    #     efilter3 = create_ef(pk=base_pk + '[1.7]', name='Filter [1.7]')
    #     create_ef(pk=base_pk + '[1.6]', name='Filter [1.6]')
    #     self.assertEqual(efilter3, EntityFilter.get_latest_version(base_pk))
    #
    #     efilter5 = create_ef(pk=base_pk + '[1.8 alpha]', name='Filter [1.8 alpha]')
    #     self.assertEqual(efilter5, EntityFilter.get_latest_version(base_pk))
    #
    #     efilter6 = create_ef(pk=base_pk + '[1.9 beta]', name='Filter [1.9 beta]')
    #
    #     # NB: '~' annoys stupid name ordering
    #     create_ef(pk=base_pk + '[1.9 alpha]', name='Filter [1.9 ~alpha]')
    #     self.assertEqual(efilter6, EntityFilter.get_latest_version(base_pk))
    #
    #     efilter8 = create_ef(pk=base_pk + '[1.10]', name='Filter [1.10]')
    #     self.assertEqual(efilter8, EntityFilter.get_latest_version(base_pk))
    #
    #     efilter9 = create_ef(pk=base_pk + '[1.10.1]', name='Filter [1.10.1]')
    #     self.assertEqual(efilter9, EntityFilter.get_latest_version(base_pk))
    #
    #     create_ef(pk=base_pk + '[1.10.2 alpha]', name='Filter [1.10.2 alpha]')
    #     create_ef(pk=base_pk + '[1.10.2 beta]', name='Filter | 1.10.2 beta')
    #     efilter12 = create_ef(pk=base_pk + '[1.10.2 rc]', name='Filter [1.10.2 rc]')
    #     self.assertEqual(efilter12, EntityFilter.get_latest_version(base_pk))
    #
    #     create_ef(pk=base_pk + '[1.10.2 rc2]', name='Filter [1.10.2 rc2]')
    #     efilter14 = create_ef(pk=base_pk + '[1.10.2 rc11]', name='Filter [1.10.2 rc11]')
    #     self.assertEqual(efilter14, EntityFilter.get_latest_version(base_pk))
    #
    #     create_ef(pk=base_pk + '[1.10.2 rc11]3', name='Filter | 1.10.2 rc11 | n°3')
    #     efilter16 = create_ef(pk=base_pk + '[1.10.2 rc11]12', name='Filter [1.10.2 rc11]#12')
    #     self.assertEqual(efilter16, EntityFilter.get_latest_version(base_pk))

    def test_manager_get_latest_version(self):
        base_pk = 'creme_core-testfilter'
        get_latest_version = EntityFilter.objects.get_latest_version

        with self.assertRaises(EntityFilter.DoesNotExist):
            get_latest_version(base_pk)

        create_ef = partial(
            EntityFilter.objects.create,
            entity_type=ContentType.objects.get_for_model(FakeContact),
        )

        create_ef(pk=base_pk, name='Base filter')

        efilter2 = create_ef(pk=base_pk + '[1.5]', name='Filter [1.5]')
        self.assertEqual(efilter2, get_latest_version(base_pk))

        efilter3 = create_ef(pk=base_pk + '[1.7]', name='Filter [1.7]')
        create_ef(pk=base_pk + '[1.6]', name='Filter [1.6]')
        self.assertEqual(efilter3, get_latest_version(base_pk))

        efilter5 = create_ef(pk=base_pk + '[1.8 alpha]', name='Filter [1.8 alpha]')
        self.assertEqual(efilter5, get_latest_version(base_pk))

        efilter6 = create_ef(pk=base_pk + '[1.9 beta]', name='Filter [1.9 beta]')
        # NB: '~' annoys stupid name ordering
        create_ef(pk=base_pk + '[1.9 alpha]', name='Filter [1.9 ~alpha]')
        self.assertEqual(efilter6, get_latest_version(base_pk))

        efilter8 = create_ef(pk=base_pk + '[1.10]', name='Filter [1.10]')
        self.assertEqual(efilter8, get_latest_version(base_pk))

        efilter9 = create_ef(pk=base_pk + '[1.10.1]', name='Filter [1.10.1]')
        self.assertEqual(efilter9, get_latest_version(base_pk))

        create_ef(pk=base_pk + '[1.10.2 alpha]', name='Filter [1.10.2 alpha]')
        create_ef(pk=base_pk + '[1.10.2 beta]', name='Filter | 1.10.2 beta')
        efilter12 = create_ef(pk=base_pk + '[1.10.2 rc]', name='Filter [1.10.2 rc]')
        self.assertEqual(efilter12, get_latest_version(base_pk))

        create_ef(pk=base_pk + '[1.10.2 rc2]', name='Filter [1.10.2 rc2]')
        efilter14 = create_ef(pk=base_pk + '[1.10.2 rc11]', name='Filter [1.10.2 rc11]')
        self.assertEqual(efilter14, get_latest_version(base_pk))

        create_ef(pk=base_pk + '[1.10.2 rc11]3', name='Filter | 1.10.2 rc11 | n°3')
        efilter16 = create_ef(pk=base_pk + '[1.10.2 rc11]12', name='Filter [1.10.2 rc11]#12')
        self.assertEqual(efilter16, get_latest_version(base_pk))

    def test_conditions_equal01(self):
        equal = EntityFilterCondition.conditions_equal
        self.assertIs(equal([], []), True)

        build_cond = partial(
            RegularFieldConditionHandler.build_condition,
            model=FakeContact,
            operator=operators.EQUALS,
            field_name='last_name',
            values=['Ikari'],
        )
        conditions1 = [build_cond()]
        self.assertIs(equal([], conditions1), False)
        self.assertTrue(equal(conditions1, conditions1))

        self.assertFalse(equal(conditions1, [build_cond(field_name='first_name')]))
        self.assertFalse(equal(conditions1, [build_cond(values=['Katsuragi'])]))
        self.assertFalse(equal(
            conditions1,
            [build_cond(operator=operators.CONTAINS)],
        ))

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_kawaii', text='Kawaii',
        )
        hates = RelationType.objects.smart_update_or_create(
            ('test-subject_hate', 'Is hating'),
            ('test-object_hate',  'Is hated by'),
        )[0]

        cond1 = build_cond()
        cond2 = PropertyConditionHandler.build_condition(model=FakeContact, ptype=ptype, has=True)
        cond3 = RelationConditionHandler.build_condition(model=FakeContact, rtype=hates, has=True)
        self.assertFalse(equal([cond1, cond2], [cond2, cond3]))
        self.assertTrue(equal([cond1, cond2, cond3], [cond2, cond3, cond1]))

    def test_conditions_equal02(self):
        "Does not compare JSON but dict (Py3k bug)."
        equal = EntityFilterCondition.conditions_equal
        type_id = RegularFieldConditionHandler.type_id

        cond1 = EntityFilterCondition(
            model=FakeContact,
            type=type_id,
            name='first_name',
            raw_value='{"operator": 1, "values": ["Ikari"]}',
        )
        cond2 = EntityFilterCondition(
            model=FakeContact,
            type=type_id,
            name='first_name',
            raw_value='{"operator": 1, "values": ["Ikari"]}',
        )
        cond3 = EntityFilterCondition(
            model=FakeContact,
            type=type_id,
            name='first_name',
            # Different strings, but same JSONified dict....
            raw_value='{"values": ["Ikari"], "operator": 1}',
        )
        self.assertTrue(equal([cond1], [cond2]))
        self.assertTrue(equal([cond1], [cond3]))

    # def test_create_again(self):  # DEPRECATED
    #     "is_custom=True -> override."
    #     EntityFilter.create(
    #         'test-filter', 'Ikari', FakeContact,
    #         is_custom=True, use_or=True,
    #         conditions=[
    #             RegularFieldConditionHandler.build_condition(
    #                 model=FakeContact,
    #                 operator=operators.EQUALS,
    #                 field_name='last_name', values=['Ikari'],
    #             ),
    #         ],
    #     )
    #     count = EntityFilter.objects.count()
    #
    #     user = self.user
    #     name = 'Misato my love'
    #     efilter = EntityFilter.create(
    #         'test-filter', name, FakeContact,
    #         is_custom=True, user=user, use_or=False,
    #         conditions=[
    #             RegularFieldConditionHandler.build_condition(
    #                 model=FakeContact,
    #                 operator=operators.IEQUALS,
    #                 field_name='first_name', values=['Gendo'],
    #             ),
    #         ],
    #     )
    #     self.assertEqual(name, efilter.name)
    #     self.assertEqual(user, efilter.user)
    #     self.assertFalse(efilter.use_or)
    #
    #     conditions = efilter.conditions.all()
    #     self.assertEqual(1, len(conditions))
    #
    #     condition = conditions[0]
    #     self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
    #     self.assertEqual('first_name',                         condition.name)
    #     self.assertEqual(
    #         {'operator': operators.IEQUALS, 'values': ['Gendo']},
    #         condition.value,
    #     )
    #
    #     self.assertEqual(count, EntityFilter.objects.count())
    #
    #     with self.assertRaises(ValueError):
    #         EntityFilter.create(
    #             'test-filter', name, FakeContact,
    #             user=user, use_or=False, is_custom=False,  # <==== cannot become custom False
    #             conditions=[
    #                 RegularFieldConditionHandler.build_condition(
    #                     model=FakeContact,
    #                     operator=operators.IEQUALS,
    #                     field_name='first_name', values=['Gendo'],
    #                 ),
    #             ],
    #         )

    def test_manager_smart_update_or_create_again01(self):
        "is_custom=True -> override."
        create_efilter = EntityFilter.objects.smart_update_or_create
        create_efilter(
            'test-filter', 'Ikari', FakeContact,
            is_custom=True, use_or=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='last_name', values=['Ikari'],
                ),
            ],
        )
        count = EntityFilter.objects.count()

        user = self.user
        name = 'Misato my love'
        efilter = create_efilter(
            'test-filter', name, FakeContact,
            is_custom=True, user=user, use_or=False,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='first_name', values=['Gendo'],
                ),
            ],
        )
        self.assertEqual(name, efilter.name)
        self.assertEqual(user, efilter.user)
        self.assertFalse(efilter.use_or)

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual('first_name',                         condition.name)
        self.assertEqual(
            {'operator': operators.IEQUALS, 'values': ['Gendo']},
            condition.value,
        )

        self.assertEqual(count, EntityFilter.objects.count())

        with self.assertRaises(ValueError):
            create_efilter(
                'test-filter', name, FakeContact,
                user=user, use_or=False, is_custom=False,  # <==== cannot become custom False
                conditions=[
                    RegularFieldConditionHandler.build_condition(
                        model=FakeContact,
                        operator=operators.IEQUALS,
                        field_name='first_name', values=['Gendo'],
                    ),
                ],
            )

    def test_manager_smart_update_or_create_again02(self):
        "is_custom=False + no change -> override name (but not user)."
        create_efilter = EntityFilter.objects.smart_update_or_create
        conditions = [
            RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator=operators.EQUALS,
                field_name='last_name', values=['Ikari'],
            ),
        ]
        pk = 'test-filter'
        create_efilter(pk, 'Misato', FakeContact, user=self.other_user, conditions=conditions)
        count = EntityFilter.objects.count()

        name = 'Misato my love'
        efilter = create_efilter(pk, name, FakeContact, user=self.user, conditions=conditions)
        self.assertEqual(name, efilter.name)
        self.assertEqual(self.other_user, efilter.user)

        self.assertEqual(count, EntityFilter.objects.count())

        with self.assertRaises(ValueError):
            create_efilter(
                pk, name, FakeContact,
                user=self.user, conditions=conditions, is_custom=True,
            )

    def test_manager_smart_update_or_create_again03(self):
        "CT changes -> error (is_custom=False)."
        create_efilter = EntityFilter.objects.smart_update_or_create
        pk = 'test-filter'
        create_efilter(
            pk, 'Misato', FakeContact,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='last_name', values=['Katsuragi'],
                ),
            ],
        )

        with self.assertRaises(ValueError):
            create_efilter(
                pk, 'Nerv', FakeOrganisation,
                conditions=[
                    RegularFieldConditionHandler.build_condition(
                        model=FakeOrganisation,
                        operator=operators.EQUALS,
                        field_name='name', values=['Nerv'],
                    ),
                ],
            )

    def test_manager_smart_update_or_create_again04(self):
        "CT changes -> error (is_custom=True)."
        create_efilter = EntityFilter.objects.smart_update_or_create
        pk = 'test-filter'
        create_efilter(
            pk, 'Misato', FakeContact,
            is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='last_name', values=['Katsuragi'],
                )
            ],
        )

        with self.assertRaises(ValueError):
            create_efilter(
                pk, 'Nerv', FakeOrganisation,
                is_custom=True,
                conditions=[
                    RegularFieldConditionHandler.build_condition(
                        model=FakeOrganisation,
                        operator=operators.EQUALS,
                        field_name='name', values=['Nerv'],
                    ),
                ],
            )

    def test_manager_smart_update_or_create_again05(self):
        "is_custom=False + changes -> new versioned filter."
        pk = 'test-filter'

        def create_filter(use_or=False, value='Ikari'):
            return EntityFilter.objects.smart_update_or_create(
                pk, 'Nerv member', FakeContact, is_custom=False, use_or=use_or,
                conditions=[
                    RegularFieldConditionHandler.build_condition(
                        model=FakeContact,
                        operator=operators.EQUALS,
                        field_name='last_name', values=[value],
                    ),
                ],
            )

        qs = EntityFilter.objects.filter(pk__startswith=pk)
        efilter1 = create_filter()
        self.assertEqual(pk, efilter1.pk)
        self.assertEqual(1, qs.count())

        # --------------------------
        efilter2 = create_filter(use_or=True)
        self.assertEqual(f'{pk}[{__version__}]', efilter2.pk)
        self.assertEqual(f'Nerv member [{__version__}]', efilter2.name)
        self.assertEqual(2, qs.count())

        # --------------------------
        create_filter(use_or=True)
        self.assertEqual(2, qs.count())

        # --------------------------
        efilter3 = create_filter(use_or=True, value='Katsuragu')
        self.assertEqual(3, qs.count())
        self.assertEqual(f'{pk}[{__version__}]2', efilter3.pk)
        self.assertEqual(f'Nerv member [{__version__}](2)', efilter3.name)

        # --------------------------
        efilter4 = create_filter(use_or=True, value='Katsuragi')
        self.assertEqual(4, qs.count())
        self.assertEqual(f'{pk}[{__version__}]3', efilter4.pk)
        self.assertEqual(f'Nerv member [{__version__}](3)', efilter4.name)

    def test_manager_smart_update_or_create_errors(self):
        "Invalid chars in PK."
        def create_filter(pk):
            return EntityFilter.objects.smart_update_or_create(
                pk, 'Nerv member', FakeContact, is_custom=True,
            )

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
            EntityFilter.objects.smart_update_or_create(
                'creme_core-test_filter', 'Nerv member',
                FakeContact, is_custom=True, is_private=True,
            )

        # Private + not is_custom => error
        with self.assertRaises(ValueError):
            EntityFilter.objects.smart_update_or_create(
                'creme_core-test_filter', 'Nerv member',
                FakeContact, is_custom=False,
                is_private=True, user=self.user,
                conditions=[
                    RegularFieldConditionHandler.build_condition(
                        model=FakeContact,
                        operator=operators.EQUALS,
                        field_name='last_name', values=['Ikari'],
                    ),
                ],
            )

    def test_ct_cache(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Ikari', FakeContact, is_custom=True,
        )

        with self.assertNumQueries(0):
            ContentType.objects.get_for_id(efilter.entity_type_id)

        efilter = self.refresh(efilter)

        with self.assertNumQueries(0):
            ct = efilter.entity_type

        self.assertIsInstance(ct, ContentType)

    def test_filter_field_equals01(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Ikari', FakeContact,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='last_name', values=['Ikari'],
                ),
            ],
        )
        self.assertEqual(1, efilter.conditions.count())

        with self.assertNumQueries(0):
            conds = efilter.get_conditions()

        self.assertEqual(1, len(conds))

        cond = conds[0]
        self.assertIsInstance(cond, EntityFilterCondition)
        self.assertEqual('last_name', cond.name)

        # ---
        efilter = self.refresh(efilter)
        self.assertExpectedFiltered(
            efilter, FakeContact, self._get_ikari_case_sensitive()
        )

        user = CremeUser.objects.create(
            username='Kanna', email='kanna@century.jp',
            first_name='Kanna', last_name='Gendou',
            password='uselesspw',
        )

        cond_accept = partial(cond.accept, user=user)
        filter_accept = partial(efilter.accept, user=user)
        contacts = self.contacts

        shinji = contacts['shinji']
        self.assertIs(cond_accept(shinji), True)
        self.assertIs(filter_accept(shinji), True)

        yui = contacts['yui']
        self.assertIs(cond_accept(yui), True)
        self.assertIs(filter_accept(yui), True)

        spike = contacts['spike']
        self.assertIs(cond_accept(spike), False)
        self.assertIs(filter_accept(spike), False)

    def test_filter_field_equals02(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Spike & Faye', FakeContact,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='first_name',
                    values=['Spike', 'Faye'],
                ),
            ],
        )
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(
            self.refresh(efilter), FakeContact, self._list_contact_ids('spike', 'faye'),
        )

    def test_filter_field_equals_boolean(self):
        "Boolean field."
        contacts = self.contacts

        ed = contacts['ed']
        ed.is_a_nerd = True
        ed.save()

        yui = contacts['yui']
        yui.is_a_nerd = True
        yui.save()

        def build_cond(value):
            return RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator=operators.EQUALS,
                field_name='is_a_nerd',
                values=[value],
            )

        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='is a nerd', model=FakeContact, is_custom=True,
            conditions=[build_cond(True)],
        )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('ed', 'yui'))

        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter02', name='is a not nerd', model=FakeContact, is_custom=True,
            conditions=[build_cond(False)],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('ed', 'yui', exclude=True),
        )

        # Old (buggy ?) format
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter02', name='is a not nerd v2', model=FakeContact, is_custom=True,
            conditions=[build_cond('False')],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('ed', 'yui', exclude=True),
        )

    def test_filter_field_equals_currentuser01(self):
        other_user = self.other_user

        contacts = self.contacts
        first_names = ('rei', 'asuka')

        for first_name in first_names:
            c = contacts[first_name]
            c.user = other_user
            c.save()

        set_global_info(user=self.user)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter_mycontacts', 'My contacts', FakeContact,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='user',
                    values=['__currentuser__'],
                ),
            ],
        )

        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(
            self.refresh(efilter), FakeContact,
            self._list_contact_ids(*first_names, exclude=True)
        )

        set_global_info(user=other_user)
        self.assertExpectedFiltered(
            self.refresh(efilter), FakeContact, self._list_contact_ids(*first_names),
        )

    def test_filter_field_equals_currentuser02(self):
        "Teams."
        user = self.user
        other_user = self.other_user

        User = get_user_model()
        teammate = User.objects.create(
            username='fulbertc',
            email='fulbert@creme.org', role=self.role,
            first_name='Fulbert', last_name='Creme',
        )

        tt_team = User.objects.create(username='TeamTitan', is_team=True)
        tt_team.teammates = [user, teammate]

        a_team = User.objects.create(username='A-Team', is_team=True)
        a_team.teammates = [other_user]

        contacts = self.contacts

        def set_owner(short_name, owner):
            c = contacts[short_name]
            c.user = owner
            c.save()

        set_owner('rei',    tt_team)     # Included
        set_owner('asuka',  other_user)  # Excluded
        set_owner('shinji', a_team)      # Excluded

        set_global_info(user=user)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter_mycontacts', 'My contacts', FakeContact,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='user',
                    values=[operands.CurrentUserOperand.type_id],
                ),
            ],
        )
        self.assertExpectedFiltered(
            self.refresh(efilter), FakeContact,
            self._list_contact_ids('asuka', 'shinji', exclude=True)
        )

    def test_filter_field_not_equals_currentuser(self):
        user = self.user
        other_user = self.other_user

        User = get_user_model()
        teammate = User.objects.create(
            username='fulbertc',
            email='fulbert@creme.org', role=self.role,
            first_name='Fulbert', last_name='Creme',
        )

        tt_team = User.objects.create(username='TeamTitan', is_team=True)
        tt_team.teammates = [user, teammate]

        a_team = User.objects.create(username='A-Team', is_team=True)
        a_team.teammates = [other_user]

        contacts = self.contacts

        def set_owner(short_name, owner):
            c = contacts[short_name]
            c.user = owner
            c.save()

        set_owner('rei',    tt_team)     # Excluded
        set_owner('asuka',  other_user)  # Included
        set_owner('shinji', a_team)      # Included

        set_global_info(user=user)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter_mycontacts', 'My contacts', FakeContact,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS_NOT,
                    field_name='user',
                    values=[operands.CurrentUserOperand.type_id],
                ),
            ],
        )

        self.assertExpectedFiltered(
            self.refresh(efilter), FakeContact,
            self._list_contact_ids('asuka', 'shinji')
        )

    def test_filter_field_iequals(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Ikari (insensitive)', FakeContact,
            user=self.user, is_custom=False,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='last_name', values=['Ikari'],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('shinji', 'yui', 'gendou'),
            case_insensitive=True,
        )

    def test_filter_field_not_equals(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Not Ikari', FakeContact, is_custom=True,
        )
        efilter.set_conditions([
            RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator=operators.EQUALS_NOT,
                field_name='last_name', values=['Ikari'],
            ),
        ])

        excluded = frozenset(self._get_ikari_case_sensitive())
        self.assertExpectedFiltered(
            efilter, FakeContact,
            [c.id for c in self.contacts.values() if c.id not in excluded]
        )

    def test_filter_field_not_iequals(self):
        pk = 'test-filter01'
        name = 'Not Ikari (case insensitive)'
        efilter = EntityFilter.objects.smart_update_or_create(
            pk, name, FakeContact, is_custom=True,
        )

        efilters = EntityFilter.objects.filter(pk='test-filter01', name=name)
        self.assertEqual(1,                  len(efilters))
        self.assertEqual(self.contact_ct.id, efilters[0].entity_type.id)
        self.assertEqual(efilter.id,         efilters[0].id)

        efilter.set_conditions([
            RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator=operators.IEQUALS_NOT,
                field_name='last_name', values=['Ikari'],
            ),
        ])
        self.assertExpectedFiltered(
            efilter, FakeContact,
            self._list_contact_ids('shinji', 'yui', 'gendou', exclude=True)
        )

    def test_filter_field_contains(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Contains "isat"',
            model=FakeContact, is_custom=True,
        )
        efilter.set_conditions([
            RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator=operators.CONTAINS,
                field_name='first_name', values=['isat'],
            ),
        ])
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('misato', 'risato')
        )

    def test_filter_field_icontains(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Not contains "Misa"',
            model=FakeContact, user=self.user, is_custom=True,
        )
        efilter.set_conditions([
            RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator=operators.ICONTAINS,
                field_name='first_name', values=['misa'],
            ),
        ])
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['misato'].id], True)

    def test_filter_field_contains_not(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Not Ikari', FakeContact, is_custom=True,
        )
        efilter.set_conditions([
            RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator=operators.CONTAINS_NOT,
                field_name='first_name', values=['sato'],
            ),
        ])
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('misato', 'risato', exclude=True)
        )

    def test_filter_field_icontains_not(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Not contains "sato" (ci)', FakeContact, is_custom=True,
        )
        efilter.set_conditions([
            RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator=operators.ICONTAINS_NOT,
                field_name='first_name', values=['sato'],
            ),
        ])
        self.assertExpectedFiltered(
            efilter, FakeContact,
            self._list_contact_ids('misato', 'risato', exclude=True),
            case_insensitive=True,
        )

    def test_filter_field_gt(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='> Yua', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.GT,
                    field_name='first_name', values=['Yua'],
                ),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['yui'].id])

    def test_filter_field_gte(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', '>= Spike', FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.GTE,
                    field_name='first_name', values=['Spike'],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('spike', 'yui')
        )

    def test_filter_field_lt(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', '< Faye', FakeContact, is_custom=True,
        )
        efilter.set_conditions([
            RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator=operators.LT,
                field_name='first_name', values=['Faye'],
            ),
        ])
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('ed', 'asuka'))

    def test_filter_field_lte(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', '<= Faye', FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.LTE,
                    field_name='first_name', values=['Faye'],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('faye', 'ed', 'asuka'),
        )

    def test_filter_field_startswith(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='starts "Gen"', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.STARTSWITH,
                    field_name='first_name', values=['Gen'],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('gendou', 'genji')
        )

    def test_filter_field_istartswith(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='starts "Gen" (ci)', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.ISTARTSWITH,
                    field_name='first_name', values=['gen'],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('gendou', 'genji')
        )

    def test_filter_field_startswith_not(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='starts not "Asu"',
            model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.STARTSWITH_NOT,
                    field_name='first_name', values=['Asu'],
                ),
            ]
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('asuka', exclude=True),
        )

    def test_filter_field_istartswith_not(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'starts not "asu"', FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.ISTARTSWITH_NOT,
                    field_name='first_name', values=['asu'],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('asuka', exclude=True)
        )

    def test_filter_field_endswith(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'ends "sato"', FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.ENDSWITH,
                    field_name='first_name', values=['sato'],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('misato', 'risato')
        )

    def test_filter_field_iendswith(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'ends "SATO"', FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IENDSWITH,
                    field_name='first_name', values=['SATO'],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('misato', 'risato')
        )

    def test_filter_field_endswith_not(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'ends not "sato"', FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.ENDSWITH_NOT,
                    field_name='first_name', values=['sato'],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact,
            self._list_contact_ids('misato', 'risato', exclude=True),
        )

    def test_filter_field_iendswith_not(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'ends not "SATO" (ci)', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IENDSWITH_NOT,
                    field_name='first_name', values=['SATO'],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact,
            self._list_contact_ids('misato', 'risato', exclude=True),
        )

    def test_filter_field_isempty01(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='is empty', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.ISEMPTY,
                    field_name='description', values=[True],
                ),
            ],
        )
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('faye', exclude=True),
        )

    def test_filter_field_isempty02(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'is not empty', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.ISEMPTY,
                    field_name='description', values=[False],
                ),
            ],
        )
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['faye'].id])

    def test_filter_field_isempty03(self):
        "Not a CharField."
        create_orga = partial(FakeOrganisation.objects.create, user=self.user)
        create_orga(name='Bebop & cie', capital=None)
        orga02 = create_orga(name='Nerv', capital=10000)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'is not null', model=FakeOrganisation, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.ISEMPTY,
                    field_name='capital', values=[False],
                ),
            ],
        )
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(efilter, FakeOrganisation, [orga02.id])

    def test_filter_field_isempty04(self):
        "Subfield of FK."
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='civility is empty', model=FakeContact,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.ISEMPTY,
                    field_name='civility__title', values=[True],
                ),
            ],
        )
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(
            efilter, FakeContact,
            self._list_contact_ids('spike', 'jet', 'faye', exclude=True),
        )

    def test_filter_field_range(self):
        create_orga = partial(FakeOrganisation.objects.create, user=self.user)
        create_orga(name='Bebop & cie',    capital=1000)
        orga02 = create_orga(name='Nerv',  capital=10000)
        orga03 = create_orga(name='Seele', capital=100000)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Between 5K & 500K', model=FakeOrganisation, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.RANGE,
                    field_name='capital', values=(5000, 500000),
                ),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeOrganisation, [orga02.id, orga03.id])

    def test_filter_fk01(self):
        efilter1 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Misters', FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='civility',
                    values=[self.civ_mister.id],  # TODO: "self.mister" ??
                ),
            ],
        )
        self.assertTrue(efilter1.entities_are_distinct)
        self.assertExpectedFiltered(
            efilter1, FakeContact, self._list_contact_ids('spike', 'jet'),
        )

        efilter2 = EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Not Misses', FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS_NOT,
                    field_name='civility', values=[self.civ_miss.id],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter2, FakeContact, self._list_contact_ids('faye', exclude=True),
        )

    def test_filter_fk02(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Mist..', FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.ISTARTSWITH,
                    field_name='civility__title', values=['Mist'],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('spike', 'jet')
        )

    def test_filter_m2m(self):
        create_language = Language.objects.create
        l1 = create_language(name='Japanese')  # code='JP'
        l2 = create_language(name='German')  # code='G'
        l3 = create_language(name='Engrish')  # code='EN'

        contacts = self.contacts

        def build_contact(name, languages):
            contact = contacts[name]
            contact.languages.set(languages)

            return contact

        jet   = build_contact('jet',   [l1, l3])
        rei   = build_contact('rei',   [l1])
        asuka = build_contact('asuka', [l1, l2, l3])
        faye  = build_contact('faye',  [l2, l3])
        yui   = build_contact('yui',   [l3])

        filter_contacts = FakeContact.objects.filter
        # self.assertEqual(3, filter_contacts(languages__code='JP').count())
        self.assertEqual(3, filter_contacts(languages__name='Japanese').count())

        # BEWARE: duplicates !!
        self.assertEqual(5, filter_contacts(languages__name__contains='an').count())

        self.assertEqual(4, filter_contacts(languages__name__contains='an').distinct().count())

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'JP', FakeContact, is_custom=True,
        )
        build_cond = RegularFieldConditionHandler.build_condition
        efilter.set_conditions([
            build_cond(
                model=FakeContact,
                operator=operators.IEQUALS,
                # field_name='languages__code', values=['JP'],
                field_name='languages__name', values=['Japanese'],
            ),
        ])
        self.assertFalse(efilter.entities_are_distinct)
        self.assertExpectedFiltered(
            efilter, FakeContact, [jet.id, rei.id, asuka.id], use_distinct=True,
        )

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'lang contains "an"',
            model=FakeContact, is_custom=True,
        )
        efilter.set_conditions([
            build_cond(
                model=FakeContact,
                operator=operators.ICONTAINS,
                field_name='languages__name', values=['an'],
            ),
        ])
        self.assertExpectedFiltered(
            efilter, FakeContact, [jet.id, rei.id, asuka.id, faye.id],
            use_distinct=True,
        )

        # Empty
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter03', 'has a language', FakeContact, is_custom=True,
            conditions=[
                build_cond(
                    model=FakeContact,
                    operator=operators.ISEMPTY,
                    field_name='languages', values=[True],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact,
            self._list_contact_ids('jet', 'rei', 'asuka', 'faye', 'yui', exclude=True),
            use_distinct=True,
        )

        # Not empty
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter04', 'has no language', FakeContact, is_custom=True,
            conditions=[
                build_cond(
                    model=FakeContact,
                    operator=operators.ISEMPTY,
                    field_name='languages', values=[False],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, [jet.id, rei.id, asuka.id, faye.id, yui.id],
            use_distinct=True,
        )

    def test_accept01(self):
        "One condition."
        user = CremeUser.objects.create(
            username='Kanna', email='kanna@century.jp',
            first_name='Kanna', last_name='Gendou',
            password='uselesspw',
        )
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Ikari', FakeContact,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='last_name', values=['IKARI'],
                ),
            ],
        )

        accept = partial(efilter.accept, user=user)
        contacts = self.contacts
        self.assertIs(accept(contacts['shinji']), True)
        self.assertIs(accept(contacts['yui']),    True)
        self.assertIs(accept(contacts['spike']),  False)

    def test_accept02(self):
        "Two conditions + AND."
        user = CremeUser.objects.create(
            username='Kanna', email='kanna@century.jp',
            first_name='Kanna', last_name='Gendou',
            password='uselesspw',
        )
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Ikari', FakeContact,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='last_name', values=['IKARI'],
                ),
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IENDSWITH,
                    field_name='first_name', values=['I'],
                ),
            ],
        )

        accept = partial(efilter.accept, user=user)
        contacts = self.contacts
        self.assertIs(accept(contacts['shinji']), True)
        self.assertIs(accept(contacts['yui']),    True)
        self.assertIs(accept(contacts['gendou']), False)

    def test_accept03(self):
        "Two conditions + OR."
        user = CremeUser.objects.create(
            username='Kanna', email='kanna@century.jp',
            first_name='Kanna', last_name='Gendou',
            password='uselesspw',
        )
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Ikari', FakeContact,
            use_or=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='last_name', values=['IKARI'],
                ),
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IENDSWITH,
                    field_name='first_name', values=['I'],
                ),
            ],
        )

        accept = partial(efilter.accept, user=user)
        contacts = self.contacts
        self.assertIs(accept(contacts['shinji']), True)
        self.assertIs(accept(contacts['yui']),    True)
        self.assertIs(accept(contacts['gendou']), True)
        self.assertIs(accept(contacts['rei']),    True)
        self.assertIs(accept(contacts['spike']),  False)

    def test_condition_update(self):
        build = partial(RegularFieldConditionHandler.build_condition, model=FakeContact)
        EQUALS = operators.EQUALS
        IEQUALS = operators.IEQUALS
        cond = build(operator=EQUALS, field_name='first_name', values=['Jet'])
        self.assertFalse(
            build(operator=EQUALS, field_name='first_name', values=['Jet']).update(cond)
        )
        self.assertTrue(
            build(operator=IEQUALS, field_name='first_name', values=['Jet']).update(cond)
        )
        self.assertTrue(
            build(operator=EQUALS,  field_name='last_name',  values=['Jet']).update(cond)
        )
        self.assertTrue(
            build(operator=EQUALS,  field_name='first_name', values=['Ed']).update(cond)
        )
        self.assertTrue(
            build(operator=IEQUALS, field_name='last_name',  values=['Jet']).update(cond)
        )
        self.assertTrue(
            build(operator=IEQUALS, field_name='last_name',  values=['Ed']).update(cond)
        )

    def test_set_conditions01(self):
        build = partial(RegularFieldConditionHandler.build_condition, model=FakeContact)
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Jet', FakeContact, is_custom=True,
        )
        efilter.set_conditions([
            build(operator=operators.EQUALS, field_name='first_name', values=['Jet']),
        ])

        # NB: create an other condition that has he last id (so if we delete the
        #     first condition, and recreate another one, the id will be different)
        EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Faye', FakeContact, is_custom=True,
        ).set_conditions([
            build(operator=operators.EQUALS, field_name='first_name', values=['Faye']),
        ])

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))
        old_id = conditions[0].id

        operator = operators.CONTAINS
        name = 'last_name'
        value = 'Black'
        efilter.set_conditions([build(operator=operator, field_name=name, values=[value])])

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,   condition.name)
        self.assertEqual(old_id, condition.id)
        self.assertDictEqual({'operator': operator, 'values': [value]}, condition.value)

    def test_set_conditions02(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Jet', FakeContact, is_custom=True,
        )

        kwargs1 = {
            'model':      FakeContact,
            'operator':   operators.EQUALS,
            'field_name': 'first_name',
            'values':     ['Jet'],
        }
        kwargs2 = {**kwargs1}
        kwargs2['operator'] = operators.IEQUALS

        build = RegularFieldConditionHandler.build_condition
        efilter.set_conditions([build(**kwargs1), build(**kwargs2)])

        # NB: see test_set_conditions01()
        EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Faye', FakeContact, is_custom=True,
        ).set_conditions([
            build(
                model=FakeContact, operator=operators.EQUALS,
                field_name='first_name', values=['Faye'],
            ),
        ])

        conditions = efilter.conditions.order_by('id')
        self.assertEqual(2, len(conditions))

        for kwargs, condition in zip([kwargs1, kwargs2], conditions):
            self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
            self.assertEqual(kwargs['field_name'],                 condition.name)
            self.assertDictEqual(
                {'operator': kwargs['operator'], 'values': kwargs['values']},
                condition.value,
            )

        old_id = conditions[0].id

        kwargs1['operator'] = operators.GT
        efilter.set_conditions([build(**kwargs1)])

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(kwargs1['field_name'],                condition.name)
        self.assertEqual(old_id,                               condition.id)
        self.assertDictEqual(
            {'operator': kwargs1['operator'], 'values': kwargs1['values']},
            condition.value,
        )

    def test_set_conditions03(self):
        """Set an erroneous condition on an existing filter."""
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Misato', FakeContact,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='last_name', values=['Katsuragi'],
                ),
            ],
        )
        efilter.set_conditions([
            EntityFilterCondition(
                model=FakeContact,
                type=SubFilterConditionHandler.type_id,
                name='invalid_id',
            )
        ])
        self.assertFalse(efilter.get_conditions())

        conditions = [*efilter.conditions.all()]
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(SubFilterConditionHandler.type_id, condition.type)
        self.assertEqual('invalid_id',                      condition.name)

    def test_set_conditions04(self):
        "Related ContentTypes are different between filter & condition => error."
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Misato', FakeContact,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.EQUALS,
                    field_name='name', values=['Nerv'],
                ),
            ],
        )
        self.assertFalse(efilter.get_conditions())
        self.assertFalse(efilter.conditions.all())

    def test_conditions_errors(self):
        "@error"
        operator_id = operators.EQUALS
        fname = 'last_name'
        value = ['Ikari']
        condition1 = RegularFieldConditionHandler.build_condition(
            model=FakeContact,
            operator=operator_id,
            field_name=fname, values=[value],
        )
        self.assertIsNone(condition1.error)
        self.assertEqual(fname, condition1.name)
        self.assertEqual(
            {'operator': operator_id, 'values': [value]},
            condition1.value,
        )

        # ---
        condition2 = EntityFilterCondition(
            model=FakeContact,
            type=condition1.type,
            name='invalid',
            value=condition1.value,
        )
        self.assertEqual(
            "FakeContact has no field named 'invalid'",
            condition2.error,
        )

        # ---
        condition3 = EntityFilterCondition(
            model=FakeContact,
            type=condition1.type,
            name=condition1.name,
            value='[]',  # Not a serialized dictionary
        )
        self.assertEqual('Invalid data, cannot build a handler', condition3.error)

    def test_get_conditions_errors(self):
        "Invalid stored data."
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Test', model=FakeContact, is_custom=True,
        )
        condition = RegularFieldConditionHandler.build_condition(
            model=FakeContact,
            operator=operators.EQUALS,
            field_name='last_name', values=['Ikari'],
        )
        condition.filter = efilter
        condition.save()

        conditions = self.refresh(efilter).get_conditions()
        self.assertEqual(1, len(conditions))

        EntityFilterCondition.objects.filter(id=conditions[0].id).update(raw_value='[]')
        self.assertFalse(self.refresh(efilter).get_conditions())

    def test_multi_conditions_and01(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01',
            model=FakeContact, is_custom=True,
        )
        build = RegularFieldConditionHandler.build_condition
        efilter.set_conditions([
            build(
                model=FakeContact, operator=operators.EQUALS,
                field_name='last_name', values=['Ikari'],
            ),
            build(
                model=FakeContact, operator=operators.STARTSWITH,
                field_name='first_name', values=['Shin'],
            ),
        ])
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['shinji'].id])

        self.assertEqual(2, len(efilter.get_conditions()))

    def test_multi_conditions_or01(self):
        build = partial(RegularFieldConditionHandler.build_condition, model=FakeContact)
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeContact, is_custom=True,
            use_or=True,  # <==
            conditions=[
                build(
                    operator=operators.EQUALS,
                    field_name='last_name', values=['Spiegel'],
                ),
                build(
                    operator=operators.STARTSWITH,
                    field_name='first_name', values=['Shin'],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('spike', 'shinji'),
        )

    def test_subfilter01(self):
        build_4_field = partial(RegularFieldConditionHandler.build_condition, model=FakeContact)
        build_sf      = SubFilterConditionHandler.build_condition
        sub_efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeContact, use_or=True, is_custom=True,
            conditions=[
                build_4_field(
                    operator=operators.EQUALS,     field_name='last_name',  values=['Spiegel'],
                ),
                build_4_field(
                    operator=operators.STARTSWITH, field_name='first_name', values=['Shin'],
                ),
            ],
        )

        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter02', name='Filter02', model=FakeContact,
            use_or=False, is_custom=True,
        )
        conds = [
            build_4_field(operator=operators.STARTSWITH, field_name='first_name', values=['Spi']),
            build_sf(sub_efilter),
        ]

        with self.assertNoException():
            efilter.check_cycle(conds)

        efilter.set_conditions(conds)
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['spike'].id])

        # Test that a CycleError is not raised
        sub_sub_efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter03', name='Filter03', model=FakeContact, is_custom=True,
        )
        sub_sub_efilter.set_conditions([
            build_4_field(
                operator=operators.EQUALS,     field_name='last_name',  values=['Black'],
            ),
            build_4_field(
                operator=operators.STARTSWITH, field_name='first_name', values=['Jet'],
            )
        ])

        conds = [
            build_4_field(operator=operators.STARTSWITH, field_name='first_name', values=['Spi']),
            build_sf(sub_sub_efilter),
        ]

        with self.assertNoException():
            sub_efilter.check_cycle(conds)

    def test_subfilter02(self):
        "Cycle error (length = 0)."
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter02', name='Filter01',
            model=FakeContact, use_or=False, is_custom=True,
        )
        conds = [
            RegularFieldConditionHandler.build_condition(
                model=FakeContact, field_name='first_name',
                operator=operators.STARTSWITH, values=['Spi'],
            ),
            SubFilterConditionHandler.build_condition(efilter),
        ]
        self.assertRaises(EntityFilter.CycleError, efilter.check_cycle,    conds)
        self.assertRaises(EntityFilter.CycleError, efilter.set_conditions, conds)

    def test_subfilter03(self):
        "Cycle error (length = 1)."
        build_4_field = partial(RegularFieldConditionHandler.build_condition, model=FakeContact)
        build_sf = SubFilterConditionHandler.build_condition

        efilter01 = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeContact, use_or=True, is_custom=True,
            conditions=[
                build_4_field(
                    operator=operators.EQUALS, field_name='last_name', values=['Spiegel'],
                ),
            ],
        )

        efilter02 = EntityFilter.objects.smart_update_or_create(
            pk='test-filter02', name='Filter02', model=FakeContact, use_or=False, is_custom=True,
        )
        self.assertSetEqual({efilter02.id}, efilter02.get_connected_filter_ids())

        efilter02.set_conditions([
            build_4_field(operator=operators.STARTSWITH, field_name='first_name', values=['Spi']),
            build_sf(efilter01),
        ])

        conds = [
            build_4_field(operator=operators.CONTAINS, field_name='first_name', values=['Faye']),
            build_sf(efilter02),
        ]
        efilter01 = self.refresh(efilter01)
        self.assertSetEqual({efilter01.id, efilter02.id}, efilter01.get_connected_filter_ids())
        self.assertRaises(EntityFilter.CycleError, efilter01.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter01.set_conditions, conds)

    def test_subfilter04(self):
        "Cycle error (length = 2)."
        build_4_field = partial(RegularFieldConditionHandler.build_condition, model=FakeContact)
        build_sf = SubFilterConditionHandler.build_condition

        efilter01 = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeContact, use_or=True, is_custom=True,
            conditions=[
                build_4_field(
                    operator=operators.EQUALS, field_name='last_name', values=['Spiegel'],
                ),
            ]
        )

        efilter02 = EntityFilter.objects.smart_update_or_create(
            pk='test-filter02', name='Filter02', model=FakeContact, use_or=False, is_custom=True,
            conditions=[
                build_4_field(
                    operator=operators.STARTSWITH, field_name='first_name', values=['Spi'],
                ),
                build_sf(efilter01),
            ],
        )

        efilter03 = EntityFilter.objects.smart_update_or_create(
            pk='test-filter03', name='Filter03', model=FakeContact, use_or=False, is_custom=True,
            conditions=[
                build_4_field(
                    operator=operators.ISTARTSWITH, field_name='first_name', values=['Misa'],
                ),
                build_sf(efilter02),
            ],
        )

        conds = [
            build_4_field(operator=operators.EQUALS, field_name='last_name', values=['Spiegel']),
            build_sf(efilter03),
        ]
        efilter01 = self.refresh(efilter01)
        self.assertRaises(EntityFilter.CycleError, efilter01.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter01.set_conditions, conds)

    def test_properties01(self):
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_kawaii', text='Kawaii',
        )
        cute_ones = ('faye', 'rei', 'misato', 'asuka')

        for fn in cute_ones:
            CremeProperty.objects.create(type=ptype, creme_entity=self.contacts[fn])

        build_cond = partial(PropertyConditionHandler.build_condition, model=FakeContact)
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeContact, is_custom=True,
            conditions=[build_cond(ptype=ptype, has=True)],
        )
        self.assertIsInstance(efilter.get_conditions()[0].handler, PropertyConditionHandler)
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids(*cute_ones),
        )

        efilter.set_conditions([build_cond(ptype=ptype, has=False)])
        self.assertExpectedFiltered(
            efilter, FakeContact,
            self._list_contact_ids(*cute_ones, exclude=True),
        )

    def test_properties02(self):
        "Several conditions on properties."
        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_pretty',    text='Pretty')
        ptype2 = create_ptype(str_pk='test-prop_beautiful', text='Beautiful')

        pretty_ones    = ('rei', 'asuka')
        beautiful_ones = ('asuka', 'misato')

        create_prop = CremeProperty.objects.create

        for fn in pretty_ones:
            create_prop(type=ptype1, creme_entity=self.contacts[fn])

        for fn in beautiful_ones:
            create_prop(type=ptype2, creme_entity=self.contacts[fn])

        build_cond = partial(PropertyConditionHandler.build_condition, model=FakeContact)
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter', name='Cute & pretty',
            model=FakeContact, is_custom=True,
            conditions=[
                build_cond(ptype=ptype1, has=True),
                build_cond(ptype=ptype2, has=True),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('asuka'))

    def test_property_deletion01(self):
        "Delete CremePropertyType => delete related conditions."
        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_pretty',    text='Pretty')
        ptype2 = create_ptype(str_pk='test-prop_beautiful', text='Beautiful')

        # We want a condition with the same name than the one for ptype1
        subfilter = EntityFilter.objects.create(
            id=ptype1.id,
            name='Do not delete me please',
            entity_type=FakeContact,
        )

        build = partial(PropertyConditionHandler.build_condition, model=FakeContact)
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Propertieeesss', model=FakeContact, is_custom=True,
            conditions=[
                build(ptype=ptype1),
                build(ptype=ptype2),
                SubFilterConditionHandler.build_condition(subfilter),  # <= should not be deleted
            ],
        )

        ptype1.delete()
        self.assertSetEqual(
            {
                (SubFilterConditionHandler.type_id, str(subfilter.id)),
                (PropertyConditionHandler.type_id,  ptype2.id),
            },
            {*efilter.conditions.values_list('type', 'name')},
        )

    def _aux_test_relations(self):
        create_rtype = RelationType.objects.smart_update_or_create
        self.loves, self.loved = create_rtype(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by'),
        )

        self.hates, self.hated = create_rtype(
            ('test-subject_hate', 'Is hating'),
            ('test-object_hate',  'Is hated by'),
        )

        bebop = FakeOrganisation.objects.create(user=self.user, name='Bebop')

        loves = self.loves
        c = self.contacts
        create = partial(Relation.objects.create, user=self.user)
        create(subject_entity=c['faye'],   type=loves, object_entity=c['spike'])
        create(subject_entity=c['shinji'], type=loves, object_entity=c['rei'])
        create(subject_entity=c['gendou'], type=loves, object_entity=c['rei'])
        create(subject_entity=c['jet'],    type=loves, object_entity=bebop)

        create(subject_entity=c['shinji'], type=self.hates, object_entity=c['gendou'])

        return loves

    def test_relations01(self):
        "No CT/entity."
        loves = self._aux_test_relations()
        in_love = ('faye', 'shinji', 'gendou', 'jet')

        build_cond = partial(RelationConditionHandler.build_condition, model=FakeContact)
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeContact, is_custom=True,
            conditions=[build_cond(rtype=loves, has=True)],
        )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids(*in_love))

        efilter.set_conditions([build_cond(rtype=loves, has=False)])
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids(*in_love, exclude=True),
        )

    def test_relations02(self):
        "Wanted CT."
        loves = self._aux_test_relations()
        in_love = ('faye', 'shinji', 'gendou')  # Not 'jet' ('bebop' not is a Contact)

        build_cond = partial(RelationConditionHandler.build_condition, model=FakeContact)

        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeContact, is_custom=True,
            conditions=[build_cond(rtype=loves, has=True, ct=self.contact_ct)],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids(*in_love)
        )

        efilter.set_conditions([build_cond(rtype=loves, has=False, ct=self.contact_ct)])
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids(*in_love, exclude=True),
        )

    def test_relations03(self):
        "Wanted entity."
        loves = self._aux_test_relations()
        in_love = ('shinji', 'gendou')
        rei = self.contacts['rei']

        build_cond = partial(RelationConditionHandler.build_condition, model=FakeContact)
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter 01', model=FakeContact, is_custom=True,
            conditions=[build_cond(rtype=loves, has=True, entity=rei)],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids(*in_love),
        )

        efilter.set_conditions([build_cond(rtype=loves, has=False, entity=rei)])
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids(*in_love, exclude=True),
        )

    def test_relations04(self):
        "Wanted entity is deleted."
        loves = self._aux_test_relations()
        rei = self.contacts['rei']

        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter 01', model=FakeContact, is_custom=True,
            conditions=[
                RelationConditionHandler.build_condition(
                    model=FakeContact, rtype=loves, has=True, entity=rei,
                ),
            ],
        )

        with self.assertNoException():
            Relation.objects.filter(object_entity=rei.id).delete()
            rei.delete()

        self.assertExpectedFiltered(efilter, FakeContact, [])

    def test_relations05(self):
        "RelationType is deleted."
        loves = self._aux_test_relations()

        # We want a condition with the same name than the one for loves
        subfilter = EntityFilter.objects.create(
            id=str(loves.id),
            name='Do not delete me please',
            entity_type=FakeContact,
        )

        build = partial(RelationConditionHandler.build_condition, model=FakeContact)
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter 01', model=FakeContact, is_custom=True,
            conditions=[
                build(rtype=loves,      has=True, entity=self.contacts['rei']),
                build(rtype=self.loved, has=True, ct=self.contact_ct),
                build(rtype=self.hates, has=True),
                SubFilterConditionHandler.build_condition(subfilter),  # <= should not be deleted
            ],
        )

        loves.delete()
        self.assertSetEqual(
            {
                (SubFilterConditionHandler.type_id, str(subfilter.id)),
                (RelationConditionHandler.type_id,  str(self.hates.id)),
            },
            {*efilter.conditions.values_list('type', 'name')}
        )

    def test_relations06(self):
        "Several conditions on relations (with OR)."
        loves = self._aux_test_relations()
        gendo = self.contacts['gendou']

        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter 01',
            model=FakeContact, use_or=True, is_custom=True,
        )
        build = partial(RelationConditionHandler.build_condition, model=FakeContact)
        efilter.set_conditions([
            build(rtype=loves,      has=True, entity=self.contacts['rei']),
            build(rtype=self.hates, has=True, entity=gendo),
        ])
        self.assertExpectedFiltered(
            efilter, FakeContact, [self.contacts['shinji'].id, gendo.id],
        )

    def test_relations07(self):
        "Several conditions on relations (with AND)."
        loves = self._aux_test_relations()
        c = self.contacts

        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter 01',
            model=FakeContact, use_or=False, is_custom=True,
        )
        build = partial(RelationConditionHandler.build_condition, model=FakeContact)
        efilter.set_conditions([
            build(rtype=loves,      has=True, entity=c['rei']),
            build(rtype=self.hates, has=True, entity=c['gendou']),
        ])
        self.assertExpectedFiltered(efilter, FakeContact, [c['shinji'].id])

    def test_relations_subfilter01(self):
        loves = self._aux_test_relations()
        in_love = ('shinji', 'gendou')

        sub_efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter Rei',
            model=FakeContact, is_custom=True,
        )
        build_4_field = partial(RegularFieldConditionHandler.build_condition, model=FakeContact)
        sub_efilter.set_conditions([
            build_4_field(
                operator=operators.STARTSWITH, field_name='last_name',  values=['Ayanami'],
            ),
            build_4_field(
                operator=operators.EQUALS,     field_name='first_name', values=['Rei'],
            ),
        ])
        self.assertExpectedFiltered(sub_efilter, FakeContact, [self.contacts['rei'].id])

        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter02', name='Filter Rei lovers', model=FakeContact, is_custom=True,
        )

        build_subfilter = partial(
            RelationSubFilterConditionHandler.build_condition, model=FakeContact,
        )
        conds = [build_subfilter(rtype=loves, has=True, subfilter=sub_efilter)]

        with self.assertNoException():
            efilter.check_cycle(conds)

        efilter.set_conditions(conds)
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids(*in_love))

        efilter.set_conditions([build_subfilter(rtype=loves, has=False, subfilter=sub_efilter)])
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids(*in_love, exclude=True)
        )

    def test_relations_subfilter02(self):
        "Cycle error (length = 0)."
        loves = self._aux_test_relations()

        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter Rei lovers', model=FakeContact, is_custom=True,
        )
        conds = [
            RelationSubFilterConditionHandler.build_condition(
                model=FakeContact, rtype=loves, has=True, subfilter=efilter,
            ),
        ]
        self.assertRaises(EntityFilter.CycleError, efilter.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter.set_conditions, conds)

    def test_relations_subfilter03(self):
        "Cycle error (length = 1)."
        loves = self._aux_test_relations()

        efilter01 = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter 01', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, operator=operators.EQUALS,
                    field_name='last_name', values=['Ayanami'],
                ),
            ],
        )

        build_4_relfilter = partial(
            RelationSubFilterConditionHandler.build_condition, model=FakeContact,
        )
        efilter02 = EntityFilter.objects.smart_update_or_create(
            pk='test-filter02', name='Filter 02', model=FakeContact, is_custom=True,
            conditions=[
                build_4_relfilter(rtype=loves, has=True, subfilter=efilter01),
            ],
        )

        conds = [build_4_relfilter(rtype=self.hates, has=False, subfilter=efilter02)]
        efilter01 = self.refresh(efilter01)
        self.assertRaises(EntityFilter.CycleError, efilter01.check_cycle,    conds)
        self.assertRaises(EntityFilter.CycleError, efilter01.set_conditions, conds)

    def test_relations_subfilter04(self):
        "RelationType is deleted."
        loves = self._aux_test_relations()
        build_4_field = partial(RegularFieldConditionHandler.build_condition, model=FakeContact)

        sub_efilter01 = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter Rei', model=FakeContact,
            conditions=[
                build_4_field(
                    operator=operators.STARTSWITH, field_name='last_name', values=['Ayanami'],
                ),
            ],
        )

        sub_efilter02 = EntityFilter.objects.smart_update_or_create(
            pk='test-filter02', name='Filter Rei', model=FakeContact,
            conditions=[
                build_4_field(
                    operator=operators.STARTSWITH, field_name='first_name', values=['Misa'],
                ),
            ],
        )

        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter03', name='Filter Rei lovers',
            model=FakeContact, is_custom=True,
        )
        build = partial(RelationSubFilterConditionHandler.build_condition, model=FakeContact)
        efilter.set_conditions([
            build(rtype=loves,      has=True, subfilter=sub_efilter01),
            build(rtype=self.hates, has=True, subfilter=sub_efilter02),
        ])

        loves.delete()
        self.assertListEqual(
            [self.hates.id],
            [cond.name for cond in efilter.conditions.all()]
        )

    def test_relations_subfilter05(self):
        "Several conditions (with OR)."
        loves = self._aux_test_relations()

        build_4_field = partial(RegularFieldConditionHandler.build_condition, model=FakeContact)
        sub_efilter01 = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter Rei', model=FakeContact,
            conditions=[
                build_4_field(
                    operator=operators.STARTSWITH, field_name='last_name',  values=['Ayanami'],
                ),
                build_4_field(
                    operator=operators.EQUALS,     field_name='first_name', values=['Rei'],
                ),
            ],
        )
        self.assertExpectedFiltered(sub_efilter01, FakeContact, [self.contacts['rei'].id])

        sub_efilter02 = EntityFilter.objects.smart_update_or_create(
            pk='test-filter02', name='Filter Gendô', model=FakeContact,
            conditions=[
                build_4_field(
                    operator=operators.EQUALS, field_name='first_name', values=['Gendô'],
                )
            ],
        )
        self.assertExpectedFiltered(sub_efilter02, FakeContact, [self.contacts['gendou'].id])

        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter03', name='Filter with 2 sublovers',
            model=FakeContact, use_or=True, is_custom=True,
        )
        build = partial(RelationSubFilterConditionHandler.build_condition, model=FakeContact)
        efilter.set_conditions([
            build(rtype=loves,      has=True, subfilter=sub_efilter01),
            build(rtype=self.hates, has=True, subfilter=sub_efilter02),
        ])
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('shinji', 'gendou'),
        )

    def test_relations_subfilter06(self):
        "Several conditions (with AND)."
        loves = self._aux_test_relations()

        build_4_field = partial(RegularFieldConditionHandler.build_condition, model=FakeContact)

        sub_efilter01 = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter Rei', model=FakeContact, is_custom=True,
            conditions=[
                build_4_field(
                    operator=operators.STARTSWITH, field_name='last_name',  values=['Ayanami'],
                ),
                build_4_field(
                    operator=operators.EQUALS,     field_name='first_name', values=['Rei'],
                ),
            ],
        )
        self.assertExpectedFiltered(sub_efilter01, FakeContact, [self.contacts['rei'].id])

        sub_efilter02 = EntityFilter.objects.smart_update_or_create(
            pk='test-filter02', name='Filter Gendo', model=FakeContact, is_custom=True,
        )
        sub_efilter02.set_conditions([
            build_4_field(operator=operators.EQUALS, field_name='first_name', values=['Gendô']),
        ])
        self.assertExpectedFiltered(sub_efilter02, FakeContact, [self.contacts['gendou'].id])

        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter03', name='Filter with 2 sublovers',
            model=FakeContact, use_or=False, is_custom=True,
        )
        build_4_relsubfilter = partial(
            RelationSubFilterConditionHandler.build_condition, model=FakeContact, has=True,
        )
        efilter.set_conditions([
            build_4_relsubfilter(rtype=loves,      subfilter=sub_efilter01),
            build_4_relsubfilter(rtype=self.hates, subfilter=sub_efilter02),
        ])
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['shinji'].id])

    def test_date01(self):
        "GTE operator."
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'After 2000-1-1', FakeContact, is_custom=True,
            conditions=[
                DateRegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='birthday',
                    start=date(year=2000, month=1, day=1),
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('asuka', 'shinji'),
        )

    def test_date02(self):
        "LTE operator."
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Before 1999-12-31', FakeContact,
            conditions=[
                DateRegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='birthday',
                    end=date(year=1999, month=12, day=31),
                ),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['misato'].id])

    def test_date03(self):
        "Range."
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Between 2001-1-1 & 2001-12-1',
            model=FakeContact, is_custom=True,
            conditions=[
                DateRegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='birthday',
                    start=date(year=2001, month=1, day=1),
                    end=date(year=2001, month=12, day=1),
                ),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['shinji'].id])

    def test_date04(self):
        "Relative to now."
        faye = self.contacts['faye']
        future = date.today()
        future = future.replace(year=future.year + 100)
        faye.birthday = future
        faye.save()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='In the future', model=FakeContact,
            conditions=[
                DateRegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='birthday', date_range='in_future',
                ),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeContact, [faye.id])

    def test_datetime01(self):
        "Previous year."
        faye = self.contacts['faye']
        FakeContact.objects.filter(pk=faye.id).update(
            created=faye.created - timedelta(days=faye.created.month * 31),
        )

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Created during previous year', model=FakeContact,
            conditions=[
                DateRegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='created', date_range='previous_year',
                ),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('faye'))

    def test_datetime02(self):
        "Current year."
        faye = self.contacts['faye']
        FakeContact.objects.filter(pk=faye.id).update(
            created=faye.created - timedelta(days=faye.created.month * 31),
        )

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Created during current year', model=FakeContact,
            conditions=[
                DateRegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='created', date_range='current_year',
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('faye', exclude=True),
        )

    def test_datetime03(self):
        "Next year."
        faye = self.contacts['faye']
        FakeContact.objects.filter(pk=faye.id).update(
            created=faye.created + timedelta(days=(13 - faye.created.month) * 31),
        )

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Created during next year (?!)',
            model=FakeContact, is_custom=True,
            conditions=[
                DateRegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='created', date_range='next_year',
                ),
            ]
        )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('faye'))

    def test_datetime04(self):
        "Current month."
        faye = self.contacts['faye']
        FakeContact.objects.filter(pk=faye.id).update(created=faye.created - timedelta(days=31))

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Created during current month',
            model=FakeContact, is_custom=True,
            conditions=[
                DateRegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='created', date_range='current_month',
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('faye', exclude=True),
        )

    def test_datetime05(self):
        "Current quarter."
        faye = self.contacts['faye']
        FakeContact.objects.filter(pk=faye.id).update(
            created=faye.created - timedelta(days=4 * 31),
        )

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Created during current quarter', model=FakeContact,
            conditions=[
                DateRegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='created', date_range='current_quarter',
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('faye', exclude=True),
        )

    def test_datetime06(self):
        "Sub-field."
        contacts = self.contacts
        spike = contacts['spike']
        jet   = contacts['jet']

        create_image = partial(FakeImage.objects.create, user=self.user)
        spike.image = img1 = create_image(name="Spike's' face")
        spike.save()

        jet.image = create_image(name="Jet's' face")
        jet.save()

        FakeImage.objects.filter(pk=img1.id).update(
            created=img1.created - timedelta(days=4 * 31),
        )

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Recent images content', model=FakeContact,
            conditions=[
                DateRegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='image__created',
                    date_range='current_quarter',
                ),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeContact, [jet.id])

    def test_date_field_empty(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Birthday is null', model=FakeContact,
            conditions=[
                DateRegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='birthday', date_range='empty',
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact,
            self._list_contact_ids('misato', 'asuka', 'shinji', exclude=True)
        )

    def test_date_field_not_empty(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Birthday is null', model=FakeContact,
            conditions=[
                DateRegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='birthday', date_range='not_empty',
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact,
            self._list_contact_ids('misato', 'asuka', 'shinji')
        )

    def test_customfield01(self):
        "INT, only one CustomField, LTE operator."
        rei = self.contacts['rei']

        custom_field = CustomField.objects.create(
            name='size (cm)', content_type=self.contact_ct, field_type=CustomField.INT,
        )

        klass = custom_field.value_class
        klass(custom_field=custom_field, entity=rei).set_value_n_save(150)
        klass(custom_field=custom_field, entity=self.contacts['misato']).set_value_n_save(170)
        self.assertEqual(2, CustomFieldInteger.objects.count())

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Small', model=FakeContact, is_custom=True,
        )
        cond = CustomFieldConditionHandler.build_condition(
            custom_field=custom_field,
            operator=operators.LTE,
            values=[155],
        )
        efilter.set_conditions([cond])
        self.assertExpectedFiltered(efilter, FakeContact, [rei.id])

    def test_customfield02(self):
        "2 INT CustomFields (can interfere), GTE operator."
        contacts = self.contacts
        asuka = contacts['asuka']

        custom_field01 = CustomField.objects.create(
            name='size (cm)', content_type=self.contact_ct, field_type=CustomField.INT,
        )

        klass = custom_field01.value_class
        klass(custom_field=custom_field01, entity=contacts['rei']).set_value_n_save(150)
        klass(custom_field=custom_field01, entity=asuka).set_value_n_save(160)

        # Should not be retrieved, because filter is relative to 'custom_field01'
        custom_field02 = CustomField.objects.create(
            name='weight (pound)', content_type=self.contact_ct, field_type=CustomField.INT,
        )
        custom_field02.value_class(
            custom_field=custom_field02, entity=self.contacts['spike'],
        ).set_value_n_save(156)

        self.assertEqual(3, CustomFieldInteger.objects.count())

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Not so small', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field01,
                    operator=operators.GTE,
                    values=[155],
                ),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeContact, [asuka.id])

    def test_customfield03(self):
        "STR, CONTAINS_NOT operator (negate)."
        custom_field = CustomField.objects.create(
            name='Eva', content_type=self.contact_ct, field_type=CustomField.STR,
        )

        c = self.contacts
        klass = custom_field.value_class
        klass(custom_field=custom_field, entity=c['rei']).set_value_n_save('Eva-00')
        klass(custom_field=custom_field, entity=c['shinji']).set_value_n_save('Eva-01')
        klass(custom_field=custom_field, entity=c['misato']).set_value_n_save('Eva-02')
        self.assertEqual(3, CustomFieldString.objects.count())

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='not 00', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    operator=operators.CONTAINS_NOT,
                    values=['00'],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('rei', exclude=True),
        )

    def test_customfield04(self):
        "2 INT CustomFields with 2 conditions."
        contacts = self.contacts
        asuka = contacts['asuka']
        spike = contacts['spike']

        create_cf = partial(
            CustomField.objects.create,
            content_type=self.contact_ct, field_type=CustomField.INT,
        )
        custom_field01 = create_cf(name='size (cm)')
        klass = custom_field01.value_class
        klass(custom_field=custom_field01, entity=spike).set_value_n_save(180)
        klass(custom_field=custom_field01, entity=contacts['rei']).set_value_n_save(150)
        klass(custom_field=custom_field01, entity=asuka).set_value_n_save(160)

        custom_field02 = create_cf(name='weight (pound)')
        klass = custom_field02.value_class
        klass(custom_field=custom_field02, entity=spike).set_value_n_save(156)
        klass(custom_field=custom_field02, entity=asuka).set_value_n_save(80)

        build_cond = CustomFieldConditionHandler.build_condition
        efilter1 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Not so small but light', model=FakeContact,
            conditions=[
                build_cond(
                    custom_field=custom_field01,
                    operator=operators.GTE,
                    values=[155],
                ),
                build_cond(
                    custom_field=custom_field02,
                    operator=operators.LTE,
                    values=[100],
                ),
            ],
        )
        self.assertExpectedFiltered(efilter1, FakeContact, [asuka.id])

        # String format (TO BE REMOVED ??)
        efilter2 = EntityFilter.objects.smart_update_or_create(
            'test-filter02', name='Not so small but light', model=FakeContact,
            conditions=[
                build_cond(
                    custom_field=custom_field01,
                    operator=operators.GTE,
                    values=['155'],
                ),
                build_cond(
                    custom_field=custom_field02,
                    operator=operators.LTE,
                    values=['100'],
                ),
            ],
        )
        self.assertExpectedFiltered(efilter2, FakeContact, [asuka.id])

    def test_customfield05(self):
        "FLOAT."
        contacts = self.contacts
        ed  = contacts['ed']
        rei = contacts['rei']

        custom_field = CustomField.objects.create(
            name='Weight (kg)', content_type=self.contact_ct, field_type=CustomField.FLOAT,
        )
        klass = custom_field.value_class
        klass(custom_field=custom_field, entity=ed).set_value_n_save('38.20')
        klass(custom_field=custom_field, entity=rei).set_value_n_save('40.00')
        klass(custom_field=custom_field, entity=contacts['asuka']).set_value_n_save('40.5')

        self.assertEqual(3, CustomFieldFloat.objects.count())

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='<= 40', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    operator=operators.LTE,
                    values=['40']
                ),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeContact, [ed.id, rei.id])

    def test_customfield06(self):
        "ENUM."
        rei = self.contacts['rei']

        custom_field = CustomField.objects.create(
            name='Eva', content_type=self.contact_ct, field_type=CustomField.ENUM,
        )
        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=custom_field)
        eva00 = create_evalue(value='Eva-00')
        create_evalue(value='Eva-01')
        eva02 = create_evalue(value='Eva-02')

        klass = custom_field.value_class
        klass(custom_field=custom_field, entity=rei).set_value_n_save(eva00.id)
        klass(custom_field=custom_field, entity=self.contacts['asuka']).set_value_n_save(eva02.id)

        self.assertEqual(2, CustomFieldEnum.objects.count())

        efilter1 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Eva-00', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    operator=operators.EQUALS,
                    values=[eva00.id],
                ),
            ],
        )
        self.assertExpectedFiltered(efilter1, FakeContact, [rei.id])

        # String format
        efilter2 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Eva-00', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    operator=operators.EQUALS,
                    values=[str(eva00.id)],
                ),
            ],
        )
        self.assertExpectedFiltered(efilter2, FakeContact, [rei.id])

    def test_customfield_boolean(self):
        "Boolean field."
        contacts = self.contacts
        ed  = contacts['ed']
        rei = contacts['rei']

        custom_field = CustomField.objects.create(
            name='Is Valid ?', content_type=self.contact_ct, field_type=CustomField.BOOL,
        )
        klass = custom_field.value_class
        klass(custom_field=custom_field, entity=ed).set_value_n_save(True)
        klass(custom_field=custom_field, entity=rei).set_value_n_save(True)
        klass(custom_field=custom_field, entity=contacts['asuka']).set_value_n_save(False)

        self.assertEqual(3, CustomFieldBoolean.objects.count())

        efilter1 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='is valid', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    operator=operators.EQUALS,
                    values=[True],
                ),
            ],
        )
        self.assertExpectedFiltered(efilter1, FakeContact, [ed.id, rei.id])

        # String format
        efilter2 = EntityFilter.objects.smart_update_or_create(
            'test-filter01-old', name='is valid', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    operator=operators.EQUALS,
                    values=['True'],
                ),
            ],
        )
        self.assertExpectedFiltered(efilter2, FakeContact, [ed.id, rei.id])

    def test_customfield_boolean_false(self):
        "Boolean field."
        contacts = self.contacts
        ed  = contacts['ed']
        rei = contacts['rei']

        custom_field = CustomField.objects.create(
            name='Is Valid ?', content_type=self.contact_ct, field_type=CustomField.BOOL,
        )
        klass = custom_field.value_class
        klass(custom_field=custom_field, entity=ed).set_value_n_save(True)
        klass(custom_field=custom_field, entity=rei).set_value_n_save(True)
        klass(custom_field=custom_field, entity=contacts['asuka']).set_value_n_save(False)

        self.assertEqual(3, CustomFieldBoolean.objects.count())

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='is valid', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    operator=operators.EQUALS,
                    values=[False],
                ),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeContact, [contacts['asuka'].id])

        # Old filter format compatibility
        cfield_rname = custom_field.value_class.get_related_name()
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01-old', name='is valid', model=FakeContact,
            conditions=[
                EntityFilterCondition(
                    type=20,
                    model=FakeContact,
                    name=str(custom_field.id),
                    value={
                        'operator': operators.EQUALS,
                        'values': ['False'],
                        'rname': cfield_rname,
                    },
                ),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeContact, [contacts['asuka'].id])

    def test_customfield_enum_multiple(self):
        "ENUM."
        c = self.contacts
        rei    = c['rei']
        asuka  = c['asuka']
        shinji = c['shinji']

        custom_field = CustomField.objects.create(
            name='Eva', content_type=self.contact_ct, field_type=CustomField.ENUM,
        )
        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=custom_field)
        eva00 = create_evalue(value='Eva-00')
        eva01 = create_evalue(value='Eva-01')
        eva02 = create_evalue(value='Eva-02')

        klass = custom_field.value_class
        klass(custom_field=custom_field, entity=rei).set_value_n_save(eva00.id)
        klass(custom_field=custom_field, entity=asuka).set_value_n_save(eva02.id)
        klass(custom_field=custom_field, entity=shinji).set_value_n_save(eva01.id)

        self.assertEqual(3, CustomFieldEnum.objects.count())

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Eva-00', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    operator=operators.EQUALS,
                    values=[eva00.id, eva02.id],  # TODO: "value=eva00"
                ),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeContact, [rei.id, asuka.id])

    def test_customfield07(self):
        "BOOL."
        rei = self.contacts['rei']

        custom_field = CustomField.objects.create(
            name='cute ??', content_type=self.contact_ct, field_type=CustomField.BOOL,
        )
        value_class = custom_field.value_class
        value_class(custom_field=custom_field, entity=rei).set_value_n_save(True)
        value_class(custom_field=custom_field, entity=self.contacts['jet']).set_value_n_save(False)
        self.assertEqual(2, CustomFieldBoolean.objects.count())

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Cuties', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    operator=operators.EQUALS,
                    values=[True],
                ),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeContact, [rei.id])

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter02', name='Cuties', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    operator=operators.EQUALS_NOT,
                    values=[True],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('rei', exclude=True)
        )

    def test_customfield_deletion01(self):
        create_cf = partial(
            CustomField.objects.create,
            content_type=self.contact_ct, field_type=CustomField.INT,
        )
        custom_field01 = create_cf(name='Size (cm)')
        custom_field02 = create_cf(name='IQ')

        # We want a condition with the same name than the one for custom_field01
        subfilter = EntityFilter.objects.create(
            id=str(custom_field01.id),
            name='Do not delete me please',
            entity_type=FakeContact,
        )

        build = partial(
            CustomFieldConditionHandler.build_condition,
            operator=operators.LTE, values=[155],
        )
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Small', model=FakeContact, is_custom=True,
            conditions=[
                build(custom_field=custom_field01),
                build(custom_field=custom_field02),
                SubFilterConditionHandler.build_condition(subfilter),  # <= should not be deleted
            ],
        )

        custom_field01.delete()
        self.assertSetEqual(
            {
                (SubFilterConditionHandler.type_id,   str(subfilter.id)),
                (CustomFieldConditionHandler.type_id, str(custom_field02.id)),
            },
            {*efilter.conditions.values_list('type', 'name')},
        )

    def test_customfield_deletion02(self):
        "Date custom field."
        create_cf = partial(
            CustomField.objects.create,
            content_type=self.contact_ct, field_type=CustomField.DATETIME,
        )
        custom_field01 = create_cf(name='Holidays')
        custom_field02 = create_cf(name='Favorite day')

        build = partial(
            DateCustomFieldConditionHandler.build_condition,
            start=date(year=2019, month=7, day=31),
        )

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01',
            name='Break', model=FakeContact, is_custom=True,
            conditions=[
                build(custom_field=custom_field01),
                build(custom_field=custom_field02),
            ],
        )

        custom_field01.delete()
        self.assertListEqual(
            [str(custom_field02.id)],
            [*efilter.conditions.values_list('name', flat=True)],
        )

    def test_customfield_number_isempty(self):
        rei = self.contacts['rei']

        custom_field = CustomField.objects.create(
            name='Weight (kg)', content_type=self.contact_ct, field_type=CustomField.FLOAT,
        )
        klass = custom_field.value_class
        klass(custom_field=custom_field, entity=rei).set_value_n_save('40.00')
        klass(custom_field=custom_field, entity=self.contacts['asuka']).set_value_n_save('40.5')

        self.assertEqual(2, CustomFieldFloat.objects.count())

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='empty', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    operator=operators.ISEMPTY,
                    values=[True],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('rei', 'asuka', exclude=True),
        )

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter02', name='not empty', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    operator=operators.ISEMPTY,
                    values=[False],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('rei', 'asuka')
        )

    def test_customfield_enum_isempty(self):
        contacts = self.contacts
        rei = contacts['rei']

        custom_field = CustomField.objects.create(
            name='Eva', content_type=self.contact_ct, field_type=CustomField.ENUM,
        )
        eva00 = CustomFieldEnumValue.objects.create(custom_field=custom_field, value='Eva-00')

        klass = custom_field.value_class
        klass(custom_field=custom_field, entity=rei).set_value_n_save(eva00.id)
        klass(custom_field=custom_field, entity=contacts['asuka']).set_value_n_save(eva00.id)

        self.assertEqual(2, CustomFieldEnum.objects.count())

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='empty', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    operator=operators.ISEMPTY,
                    values=[True],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact,
            self._list_contact_ids('rei', 'asuka', exclude=True),
        )

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter02', name='not empty', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    operator=operators.ISEMPTY,
                    values=[False],
                ),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('rei', 'asuka'))

    def test_customfield_string_isempty(self):
        c = self.contacts

        custom_field = CustomField.objects.create(
            name='Eva', content_type=self.contact_ct, field_type=CustomField.STR,
        )
        klass = custom_field.value_class
        klass(custom_field=custom_field, entity=c['rei']).set_value_n_save('Eva-00')
        klass(custom_field=custom_field, entity=c['shinji']).set_value_n_save('Eva-01')

        self.assertEqual(2, CustomFieldString.objects.count())

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='empty', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    operator=operators.ISEMPTY,
                    values=[True],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact,
            self._list_contact_ids('rei', 'shinji', exclude=True),
        )

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='not empty', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    operator=operators.ISEMPTY,
                    values=[False],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('rei', 'shinji'),
        )

    def test_customfield_boolean_isempty(self):
        custom_field = CustomField.objects.create(
            name='Eva ?', content_type=self.contact_ct, field_type=CustomField.BOOL,
        )

        c = self.contacts
        klass = custom_field.value_class
        klass(custom_field=custom_field, entity=c['rei']).set_value_n_save(True)
        klass(custom_field=custom_field, entity=c['shinji']).set_value_n_save(True)
        klass(custom_field=custom_field, entity=c['asuka']).set_value_n_save(True)

        self.assertEqual(3, CustomFieldBoolean.objects.count())

        efilter1 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='empty', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    operator=operators.ISEMPTY,
                    values=[True],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter1, FakeContact,
            self._list_contact_ids('rei', 'shinji', 'asuka', exclude=True),
        )

        # ---
        efilter2 = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='not empty', model=FakeContact,
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    operator=operators.ISEMPTY,
                    values=[False],
                ),
            ],
        )
        self.assertExpectedFiltered(
            efilter2, FakeContact,
            self._list_contact_ids('rei', 'shinji', 'asuka'),
        )

    def _aux_test_datecf(self):
        custom_field = CustomField.objects.create(
            name='First fight', content_type=self.contact_ct, field_type=CustomField.DATETIME,
        )

        c = self.contacts
        klass = partial(custom_field.value_class, custom_field=custom_field)
        create_dt = self.create_datetime
        klass(entity=c['rei']).set_value_n_save(create_dt(year=2015, month=3, day=14))
        klass(entity=c['shinji']).set_value_n_save(create_dt(year=2015, month=4, day=21))
        klass(entity=c['asuka']).set_value_n_save(create_dt(year=2015, month=5, day=3))
        self.assertEqual(3, CustomFieldDateTime.objects.count())

        return custom_field

    def test_datecustomfield01(self):
        "GTE operator."
        custom_field = self._aux_test_datecf()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'After April', FakeContact, is_custom=True,
        )
        cond = DateCustomFieldConditionHandler.build_condition(
            custom_field=custom_field, start=date(year=2015, month=4, day=1),
        )

        efilter.set_conditions([cond])
        self.assertExpectedFiltered(
            efilter, FakeContact, self._list_contact_ids('asuka', 'shinji')
        )

    def test_datecustomfield02(self):
        "LTE operator."
        custom_field = self._aux_test_datecf()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Before May', FakeContact,
            conditions=[
                DateCustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    end=date(year=2015, month=5, day=1),
                ),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeContact, self._list_contact_ids('shinji', 'rei'))

    def test_datecustomfield03(self):
        "Range."
        custom_field = self._aux_test_datecf()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'In April', FakeContact,
            conditions=[
                DateCustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    start=date(year=2015, month=4, day=1),
                    end=date(year=2015, month=4, day=30),
                ),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeContact, [self.contacts['shinji'].id])

    def test_datecustomfield04(self):
        "Relative to now."
        custom_field = CustomField.objects.create(
            name='First flight', content_type=self.contact_ct, field_type=CustomField.DATETIME,
        )

        c = self.contacts
        spike = c['spike']
        jet   = c['jet']
        dt_now = now()

        klass = partial(custom_field.value_class, custom_field=custom_field)
        klass(entity=c['faye']).set_value_n_save(self.create_datetime(year=2000, month=3, day=14))
        klass(entity=spike).set_value_n_save(dt_now + timedelta(days=3650))
        klass(entity=jet).set_value_n_save(dt_now + timedelta(days=700))

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='In the future', model=FakeContact,
            conditions=[
                DateCustomFieldConditionHandler.build_condition(
                    custom_field=custom_field,
                    date_range='in_future'
                ),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeContact, [spike.id, jet.id])

    def test_datecustomfield05(self):
        "2 DATE CustomFields with 2 conditions."
        contacts = self.contacts
        shinji = contacts['shinji']
        custom_field01 = self._aux_test_datecf()
        custom_field02 = CustomField.objects.create(
            name='Last fight', content_type=self.contact_ct, field_type=CustomField.DATETIME,
        )

        klass = partial(custom_field02.value_class, custom_field=custom_field02)
        create_dt = self.create_datetime
        klass(entity=contacts['rei']).set_value_n_save(create_dt(year=2020, month=3, day=14))
        klass(entity=shinji).set_value_n_save(create_dt(year=2030, month=4, day=21))
        klass(entity=contacts['asuka']).set_value_n_save(create_dt(year=2040, month=5, day=3))

        build_cond = DateCustomFieldConditionHandler.build_condition
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Complex filter', FakeContact, use_or=False,
            conditions=[
                build_cond(custom_field=custom_field01, start=date(year=2015, month=4, day=1)),
                build_cond(custom_field=custom_field02, end=date(year=2040, month=1, day=1)),
            ],
        )
        self.assertExpectedFiltered(efilter, FakeContact, [shinji.id])

    def test_invalid_field(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Ikari', FakeContact, is_custom=True,
        )
        build = partial(
            RegularFieldConditionHandler.build_condition,
            model=FakeContact, operator=operators.EQUALS, values=['Ikari'],
        )
        cond1 = build(field_name='last_name')
        cond2 = build(field_name='first_name')
        cond2.name = 'invalid'

        efilter.set_conditions([cond1, cond2])

        with self.assertNoException():
            filtered = [*efilter.filter(FakeContact.objects.all())]

        self.assertSetEqual(
            {*self._get_ikari_case_sensitive()}, {c.id for c in filtered},
        )
        self.assertEqual(1, len(efilter.get_conditions()))

    def test_invalid_datefield(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Ikari', FakeContact, is_custom=True,
        )
        cond1 = RegularFieldConditionHandler.build_condition(
            model=FakeContact, field_name='last_name',
            operator=operators.EQUALS, values=['Ikari'],
        )
        cond2 = DateRegularFieldConditionHandler.build_condition(
            model=FakeContact, field_name='birthday',
            start=date(year=2000, month=1, day=1),
        )
        cond2.name = 'invalid'

        efilter.set_conditions([cond1, cond2])
        self.assertEqual(1, len(efilter.get_conditions()))

        with self.assertNoException():
            filtered = [*efilter.filter(FakeContact.objects.all())]

        self.assertSetEqual(
            {*self._get_ikari_case_sensitive()}, {c.id for c in filtered},
        )

    def test_invalid_subfilter(self):
        build_4_field = partial(
            RegularFieldConditionHandler.build_condition,
            model=FakeContact, operator=operators.CONTAINS,
        )

        sub_efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter01', model=FakeContact,
            conditions=[build_4_field(field_name='last_name', values=['Spiegel'])],
        )

        sub_cond = SubFilterConditionHandler.build_condition(sub_efilter)
        with self.assertNumQueries(0):
            error = sub_cond.error
        self.assertIsNone(error)

        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter02', name='Filter02', model=FakeContact,
            conditions=[
                build_4_field(field_name='first_name', values=['Spi']),
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

        build_4_field = partial(
            RegularFieldConditionHandler.build_condition,
            model=FakeContact, operator=operators.EQUALS,
        )
        sub_efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter Rei', model=FakeContact,
            conditions=[build_4_field(field_name='last_name', values=['Ayanami'])],
        )

        sub_cond = RelationSubFilterConditionHandler.build_condition(
            model=FakeContact, rtype=loves, has=True, subfilter=sub_efilter,
        )
        with self.assertNumQueries(0):
            error = sub_cond.error
        self.assertIsNone(error)

        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter02', name='Filter Rei lovers', model=FakeContact,
            conditions=[
                build_4_field(field_name='first_name', values=['rei']),
                sub_cond,
            ],
        )

        EntityFilter.objects.filter(pk=sub_efilter.pk).delete()
        self.assertDoesNotExist(sub_efilter)
        efilter = self.assertStillExists(efilter)

        conditions = efilter.get_conditions()
        self.assertEqual(1, len(conditions))

    # def test_get_for_user(self):  # DEPRECATED
    #     user = self.user
    #     other_user = self.other_user
    #
    #     create_ef = partial(
    #         EntityFilter.create, name='Misatos',
    #         model=FakeContact,
    #         conditions=[
    #             RegularFieldConditionHandler.build_condition(
    #                 model=FakeContact,
    #                 operator=operators.EQUALS,
    #                 field_name='first_name', values=['Misato'],
    #             ),
    #         ],
    #     )
    #
    #     ef1 = create_ef(pk='test-ef_contact1')
    #     ef2 = create_ef(pk='test-ef_contact2', user=user)
    #     ef3 = create_ef(
    #         pk='test-ef_orga', model=FakeOrganisation, name='NERV',
    #         conditions=[
    #             RegularFieldConditionHandler.build_condition(
    #                 model=FakeOrganisation,
    #                 operator=operators.IEQUALS,
    #                 field_name='name', values=['NERV'],
    #             ),
    #         ],
    #     )
    #     ef4 = create_ef(pk='test-ef_contact3', user=other_user)
    #     ef5 = create_ef(pk='test-ef_contact4', user=other_user,
    #                     is_private=True, is_custom=True,
    #                    )
    #     ef6 = EntityFilter.objects.create(
    #         pk='test-ef_contact5',
    #         name='My contacts',
    #         entity_type=FakeContact,
    #         filter_type=EF_CREDENTIALS,  # <==
    #     )
    #
    #     efilters = EntityFilter.get_for_user(user, self.contact_ct)
    #     self.assertIsInstance(efilters, QuerySet)
    #
    #     efilters_set = {*efilters}
    #     self.assertIn(ef1, efilters_set)
    #     self.assertIn(ef2, efilters_set)
    #     self.assertIn(ef4, efilters_set)
    #
    #     self.assertNotIn(ef3, efilters_set)
    #     self.assertNotIn(ef5, efilters_set)
    #     self.assertNotIn(ef6, efilters_set)
    #
    #     # ----
    #     orga_ct = ContentType.objects.get_for_model(FakeOrganisation)
    #     orga_efilters_set = {*EntityFilter.get_for_user(user, orga_ct)}
    #     self.assertIn(ef3, orga_efilters_set)
    #
    #     self.assertNotIn(ef1, orga_efilters_set)
    #     self.assertNotIn(ef2, orga_efilters_set)
    #     self.assertNotIn(ef4, orga_efilters_set)
    #     self.assertNotIn(ef5, orga_efilters_set)
    #
    #     # ----
    #     persons_efilters_set = {*EntityFilter.get_for_user(user, (self.contact_ct, orga_ct))}
    #     self.assertIn(ef1, persons_efilters_set)
    #     self.assertIn(ef3, persons_efilters_set)
    #
    #     self.assertSetEqual(
    #         persons_efilters_set,
    #         {*EntityFilter.get_for_user(user, [self.contact_ct, orga_ct])}
    #     )

    def test_manager_filter_by_user(self):
        user = self.user
        other_user = self.other_user

        User = get_user_model()
        teammate = User.objects.create(
            username='fulbertc',
            email='fulbert@creme.org', role=self.role,
            first_name='Fulbert', last_name='Creme',
        )

        tt_team = User.objects.create(username='TeamTitan', is_team=True)
        tt_team.teammates = [user, teammate]

        a_team = User.objects.create(username='A-Team', is_team=True)
        a_team.teammates = [other_user]

        create_ef = partial(
            EntityFilter.objects.smart_update_or_create,
            name='Misatos',
            model=FakeContact,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='first_name', values=['Misato'],
                ),
            ],
        )

        ef1 = create_ef(pk='test-ef_contact1')
        ef2 = create_ef(pk='test-ef_contact2', user=user)
        ef3 = create_ef(pk='test-ef_contact3', user=user, is_private=True, is_custom=True)
        ef4 = create_ef(
            pk='test-ef_orga', model=FakeOrganisation, name='NERV',
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.IEQUALS,
                    field_name='name', values=['NERV'],
                ),
            ],
        )
        ef5 = create_ef(pk='test-ef_contact5', user=other_user)
        ef6 = create_ef(
            pk='test-ef_contact6', user=tt_team, is_private=True, is_custom=True,
        )
        ef7 = create_ef(pk='test-ef_contact7', user=a_team)
        ef8 = create_ef(
            pk='test-ef_contact8', user=other_user, is_private=True, is_custom=True,
        )
        ef9 = create_ef(
            pk='test-ef_contact9', user=a_team, is_private=True, is_custom=True,
        )
        ef10 = EntityFilter.objects.create(
            pk='test-ef_contact10',
            name='My contacts',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,  # <==
        )

        efilters1 = EntityFilter.objects.filter_by_user(user)
        self.assertIsInstance(efilters1, QuerySet)

        efilters_set1 = {*efilters1}
        self.assertIn(ef1, efilters_set1)
        self.assertIn(ef2, efilters_set1)
        self.assertIn(ef3, efilters_set1)
        self.assertIn(ef4, efilters_set1)
        self.assertIn(ef5, efilters_set1)
        self.assertIn(ef6, efilters_set1)
        self.assertIn(ef7, efilters_set1)

        self.assertNotIn(ef8, efilters_set1)
        self.assertNotIn(ef9, efilters_set1)
        self.assertNotIn(ef10, efilters_set1)

        # ---
        with self.assertRaises(ValueError):
            EntityFilter.objects.filter_by_user(tt_team)

        # ---
        staff = User.objects.create(
            username='staffito', email='staff@creme.org',
            is_superuser=True, is_staff=True,
            first_name='Staffito', last_name='Creme',
        )
        efilters_set2 = [*EntityFilter.objects.filter_by_user(staff)]
        self.assertIn(ef1, efilters_set2)
        self.assertIn(ef2, efilters_set2)
        self.assertIn(ef3, efilters_set2)
        self.assertIn(ef4, efilters_set2)
        self.assertIn(ef5, efilters_set2)
        self.assertIn(ef6, efilters_set2)
        self.assertIn(ef7, efilters_set2)
        self.assertIn(ef8, efilters_set2)
        self.assertIn(ef9, efilters_set2)
        self.assertNotIn(ef10, efilters_set2)

    def test_get_verbose_conditions01(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-ef_contact', name='My filter', model=FakeContact,
            is_custom=True, conditions=[],
        )

        self.assertEqual([], [*efilter.get_verbose_conditions(self.user)])

    def test_get_verbose_conditions02(self):
        "One condition."
        first_name = 'Misato'
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-ef_contact', name='My filter', model=FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='first_name', values=[first_name],
                ),
            ],
        )

        msg = _('«{field}» is {values}').format(
            field=_('First name'),
            values=_('«{enum_value}»').format(enum_value=first_name),
        )
        self.assertEqual(
            msg,
            efilter.get_conditions()[0].description(self.user),
        )
        self.assertListEqual(
            [msg],
            [*efilter.get_verbose_conditions(self.user)],
        )

    def test_get_verbose_conditions03(self):
        "Several conditions."
        name = 'Nerv'
        desc1 = 'important'
        desc2 = 'beware'
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-ef_orga', name='My filter', model=FakeOrganisation, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.STARTSWITH,
                    field_name='name', values=[name],
                ),
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.CONTAINS,
                    field_name='description', values=[desc1, desc2],
                ),
            ],
        )

        fmt_value = _('«{enum_value}»').format
        self.assertListEqual(
            [
                _('«{field}» starts with {values}').format(
                    field=_('Name'),
                    values=fmt_value(enum_value=name),
                ),
                _('«{field}» contains {values}').format(
                    field=_('Description'),
                    values=_('{first} or {last}').format(
                        first=fmt_value(enum_value=desc1),
                        last=fmt_value(enum_value=desc2),
                    ),
                ),
            ],
            [*efilter.get_verbose_conditions(self.user)],
        )

    def test_applicable_on_entity_base(self):
        efilter1 = EntityFilter.objects.smart_update_or_create(
            pk='test-ef_orga1', name='My name filter',
            model=FakeOrganisation, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.STARTSWITH,
                    field_name='name', values=['House'],
                ),
            ],
        )
        self.assertIs(efilter1.applicable_on_entity_base, False)

        efilter2 = EntityFilter.objects.smart_update_or_create(
            pk='test-ef_orga2', name='My description filter',
            model=FakeOrganisation, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.ICONTAINS,
                    field_name='description', values=['House'],
                ),
            ],
        )
        self.assertIs(efilter2.applicable_on_entity_base, True)

        efilter3 = EntityFilter.objects.smart_update_or_create(
            pk='test-ef_orga3', name='My empty filter',
            model=FakeOrganisation, is_custom=True,
        )
        self.assertIs(efilter3.applicable_on_entity_base, True)

        efilter4 = EntityFilter.objects.smart_update_or_create(
            pk='test-ef_orga4', name='My complex filter',
            model=FakeOrganisation, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.ICONTAINS,
                    field_name='description', values=['House'],
                ),
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.STARTSWITH,
                    field_name='name', values=['House'],
                ),
            ],
        )
        self.assertIs(efilter4.applicable_on_entity_base, False)

    def test_filterlist01(self):
        user = self.user
        create_ef = partial(
            EntityFilter.objects.smart_update_or_create,
            name='Misatos',
            model=FakeContact,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='first_name', values=['Misato'],
                ),
            ],
        )

        ef1 = create_ef(pk='test-ef_contact1')
        ef2 = create_ef(pk='test-ef_contact2', user=user)
        ef3 = create_ef(
            pk='test-ef_orga', model=FakeOrganisation, name='NERV',
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.IEQUALS,
                    field_name='name', values=['NERV'],
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
        "Private filters + not super user (+ team management)."
        self.client.logout()

        super_user = self.other_user
        other_user = self.user

        logged = self.client.login(username=super_user.username, password=self.password)
        self.assertTrue(logged)

        User = get_user_model()
        teammate = User.objects.create(
            username='fulbertc',
            email='fulbert@creme.org', role=self.role,
            first_name='Fulbert', last_name='Creme',
        )

        tt_team = User.objects.create(username='TeamTitan', is_team=True)
        tt_team.teammates = [super_user, teammate]

        a_team = User.objects.create(username='A-Team', is_team=True)
        a_team.teammates = [other_user]

        conditions = [
            RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator=operators.EQUALS,
                field_name='first_name', values=['Misato'],
            ),
        ]

        def create_ef(id, **kwargs):
            return EntityFilter.objects.smart_update_or_create(
                pk=f'test-ef_contact{id}',
                name=f'Filter #{id}',
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
        "Staff user -> can see all filters."
        user = self.user
        user.is_staff = True
        user.save()

        other_user = self.other_user

        conditions = [
            RegularFieldConditionHandler.build_condition(
                model=FakeContact,
                operator=operators.EQUALS,
                field_name='first_name', values=['Misato'],
            ),
        ]

        def create_ef(id, **kwargs):
            return EntityFilter.objects.smart_update_or_create(
                pk=f'test-ef_contact{id}',
                name=f'Filter #{id}',
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
