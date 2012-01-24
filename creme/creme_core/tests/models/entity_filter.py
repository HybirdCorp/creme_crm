# -*- coding: utf-8 -*-

try:
    from datetime import date
    from logging import info

    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import *
    from creme_core.models.header_filter import *
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact, Organisation, Civility
except Exception as e:
    print 'Error:', e


__all__ = ('EntityFiltersTestCase',)


class EntityFiltersTestCase(CremeTestCase):
    def setUp(self):
        self.login()

        create = Contact.objects.create
        user = self.user

        self.civ_miss   = miss   = Civility.objects.create(title='Miss')
        self.civ_mister = mister = Civility.objects.create(title='Mister')

        self.contacts = [
            create(user=user, first_name=u'Spike',  last_name=u'Spiegel',   civility=mister), #0
            create(user=user, first_name=u'Jet',    last_name=u'Black',     civility=mister), #1
            create(user=user, first_name=u'Faye',   last_name=u'Valentine', civility=miss,
                   description=u'Sexiest woman is the universe'),                             #2
            create(user=user, first_name=u'Ed',     last_name=u'Wong', description=u''),      #3
            create(user=user, first_name=u'Rei',    last_name=u'Ayanami'),   #4
            create(user=user, first_name=u'Misato', last_name=u'Katsuragi',
                  birthday=date(year=1986, month=12, day=8)),                #5
            create(user=user, first_name=u'Asuka',  last_name=u'Langley',
                   birthday=date(year=2001, month=12, day=4)),               #6
            create(user=user, first_name=u'Shinji', last_name=u'Ikari',
                   birthday=date(year=2001, month=6, day=6)),                #7
            create(user=user, first_name=u'Yui',    last_name=u'Ikari'),     #8
            create(user=user, first_name=u'Gendô',  last_name=u'IKARI'),     #9
            create(user=user, first_name=u'Genji',  last_name=u'Ikaru'),     #10 NB: startswith 'Gen'
            create(user=user, first_name=u'Risato', last_name=u'Katsuragu'), #11 NB contains 'isat' like #5
        ]

        self.contact_ct = ContentType.objects.get_for_model(Contact)

    def assertExpectedFiltered(self, efilter, model, ids, case_insensitive=False):
        msg = '(NB: maybe you have case sensitive problems with your DB configuration).' if case_insensitive else ''
        filtered = list(efilter.filter(model.objects.all()))
        self.assertEqual(len(ids), len(filtered), str(filtered) + msg)
        self.assertEqual(set(ids), set(c.id for c in filtered))

    def _get_ikari_case_sensitive(self):
        ikaris = Contact.objects.filter(last_name__exact="Ikari")

        if len(ikaris) == 3:
            info('INFO: your DB is Case insentive')

        return [ikari.id for ikari in ikaris]

    def test_filter_field_equals01(self):
        self.assertEqual(len(self.contacts), Contact.objects.count())

        efilter = EntityFilter.create('test-filter01', 'Ikari', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.EQUALS,
                                                                    name='last_name', values=['Ikari']
                                                                   )
                               ])
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(self.refresh(efilter), Contact, self._get_ikari_case_sensitive())

    def test_filter_field_equals02(self):
        efilter = EntityFilter.create('test-filter01', 'Spike & Faye', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.EQUALS,
                                                                    name='first_name',
                                                                    values=['Spike', 'Faye']
                                                                   )
                               ])
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(self.refresh(efilter), Contact, [self.contacts[0].id, self.contacts[2].id])

    def test_filter_field_iequals(self):
        efilter = EntityFilter.create('test-filter01', 'Ikari (insensitive)', Contact,
                                      user=self.user, is_custom=False
                                     )
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IEQUALS,
                                                                    name='last_name', values=['Ikari']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[i].id for i in (7, 8, 9)], True)

    def test_filter_field_not_equals(self):
        efilter = EntityFilter.create('test-filter01', 'Not Ikari', Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.EQUALS_NOT,
                                                                    name='last_name', values=['Ikari']
                                                                   )
                               ])

        exclude = set(self._get_ikari_case_sensitive())
        self.assertExpectedFiltered(efilter, Contact, [c.id for c in self.contacts if c.id not in exclude])

    def test_filter_field_not_iequals(self):
        pk = 'test-filter01'
        name = 'Not Ikari (case insensitive)'
        efilter = EntityFilter.create(pk, name, Contact)

        efilters = EntityFilter.objects.filter(pk='test-filter01', name=name)
        self.assertEqual(1,                  len(efilters))
        self.assertEqual(self.contact_ct.id, efilters[0].entity_type.id)
        self.assertEqual(efilter.id,         efilters[0].id)

        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IEQUALS_NOT,
                                                                    name='last_name', values=['Ikari']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in (7, 8, 9)])

    def test_filter_field_contains(self):
        efilter = EntityFilter.create('test-filter01', name='Contains "isat"', model=Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.CONTAINS,
                                                                    name='first_name', values=['isat']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[5].id, self.contacts[11].id])

    def test_filter_field_icontains(self):
        efilter = EntityFilter.create(pk='test-filter01', name='Not contains "Misa"', model=Contact, user=self.user)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ICONTAINS,
                                                                    name='first_name', values=['misa']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[5].id], True)

    def test_filter_field_contains_not(self):
        efilter = EntityFilter.create('test-filter01', 'Not Ikari', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.CONTAINS_NOT,
                                                                    name='first_name', values=['sato']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in (5, 11)])

    def test_filter_field_icontains_not(self):
        efilter = EntityFilter.create('test-filter01', 'Not contains "sato" (ci)', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ICONTAINS_NOT,
                                                                    name='first_name', values=['sato']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in (5, 11)], True)

    def test_filter_field_gt(self):
        efilter = EntityFilter.create(pk='test-filter01', name='> Yua', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.GT,
                                                                    name='first_name', values=['Yua']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[8].id])

    def test_filter_field_gte(self):
        efilter = EntityFilter.create('test-filter01', '>= Spike', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.GTE,
                                                                    name='first_name', values=['Spike']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[0].id, self.contacts[8].id])

    def test_filter_field_lt(self):
        efilter = EntityFilter.create('test-filter01', '< Faye', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.LT,
                                                                    name='first_name', values=['Faye']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[3].id, self.contacts[6].id])

    def test_filter_field_lte(self):
        efilter = EntityFilter.create('test-filter01', '<= Faye', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.LTE,
                                                                    name='first_name', values=['Faye']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[i].id for i in (2, 3, 6)])

    def test_filter_field_startswith(self):
        efilter = EntityFilter.create(pk='test-filter01', name='starts "Gen"', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.STARTSWITH,
                                                                    name='first_name', values=['Gen']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[9].id, self.contacts[10].id])

    def test_filter_field_istartswith(self):
        efilter = EntityFilter.create(pk='test-filter01', name='starts "Gen" (ci)', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ISTARTSWITH,
                                                                    name='first_name', values=['gen']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[9].id, self.contacts[10].id])

    def test_filter_field_startswith_not(self):
        efilter = EntityFilter.create(pk='test-filter01', name='starts not "Asu"', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.STARTSWITH_NOT,
                                                                    name='first_name', values=['Asu']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i != 6])

    def test_filter_field_istartswith_not(self):
        efilter = EntityFilter.create('test-filter01', 'starts not "asu"', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ISTARTSWITH_NOT,
                                                                    name='first_name', values=['asu']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i != 6])

    def test_filter_field_endswith(self):
        efilter = EntityFilter.create('test-filter01', 'ends "sato"', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ENDSWITH,
                                                                    name='first_name', values=['sato']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[5].id, self.contacts[11].id])

    def test_filter_field_iendswith(self):
        efilter = EntityFilter.create('test-filter01', 'ends "SATO"', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IENDSWITH,
                                                                    name='first_name', values=['SATO']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[5].id, self.contacts[11].id])

    def test_filter_field_endswith_not(self):
        efilter = EntityFilter.create('test-filter01', 'ends not "sato"', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ENDSWITH_NOT,
                                                                    name='first_name', values=['sato']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in (5, 11)])

    def test_filter_field_iendswith_not(self):
        efilter = EntityFilter.create('test-filter01', 'ends not "SATO" (ci)', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IENDSWITH_NOT,
                                                                    name='first_name', values=['SATO']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in (5, 11)])

    def test_filter_field_isempty01(self):
        efilter = EntityFilter.create(pk='test-filter01', name='is empty', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ISEMPTY,
                                                                    name='description', values=[True]
                                                                   )
                               ])
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i != 2])

    def test_filter_field_isempty02(self):
        efilter = EntityFilter.create('test-filter01', 'is not empty', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ISEMPTY,
                                                                    name='description', values=[False]
                                                                   )
                               ])
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[2].id])

    def test_filter_field_isempty03(self): #not charfield
        create = Organisation.objects.create
        user = self.user
        orga01 = create(user=user, name='Bebop & cie', capital=None)
        orga02 = create(user=user, name='Nerv',        capital=10000)

        efilter = EntityFilter.create('test-filter01', 'is not null', Organisation)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Organisation,
                                                                    operator=EntityFilterCondition.ISEMPTY,
                                                                    name='capital', values=[False]
                                                                   )
                               ])
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(efilter, Organisation, [orga02.id])

    def test_filter_field_isempty04(self): #subfield of fk
        efilter = EntityFilter.create(pk='test-filter01', name='civility is empty', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ISEMPTY,
                                                                    name='civility__title', values=[True]
                                                                   )
                               ])
        self.assertEqual(1, efilter.conditions.count())

        excluded = set([0, 1, 2]) #Spike, Jet & Faye
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in excluded])

    def test_filter_field_range(self):
        create = Organisation.objects.create
        user = self.user
        orga01 = create(user=user, name='Bebop & cie', capital=1000)
        orga02 = create(user=user, name='Nerv',        capital=10000)
        orga03 = create(user=user, name='Seele',       capital=100000)

        efilter = EntityFilter.create('test-filter01', name='Between 5K & 500K', model=Organisation)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Organisation,
                                                                    operator=EntityFilterCondition.RANGE,
                                                                    name='capital', values=(5000, 500000)
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Organisation, [orga02.id, orga03.id])

    def test_filter_fk01(self):
        efilter = EntityFilter.create('test-filter01', 'Misters', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.EQUALS,
                                                                    name='civility', values=[self.civ_mister.id] #TODO: "self.mister" ??
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[0].id, self.contacts[1].id])

        efilter = EntityFilter.create('test-filter01', 'Not Misses', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.EQUALS_NOT,
                                                                    name='civility', values=[self.civ_miss.id]
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i != 2])

    def test_filter_fk02(self):
        efilter = EntityFilter.create('test-filter01', 'Mist..', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ISTARTSWITH,
                                                                    name='civility__title', values=['Mist']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[0].id, self.contacts[1].id])

    def test_filter_m2m(self):
        l1 = Language.objects.create(name='Japanese', code='JP')
        l2 = Language.objects.create(name='German',   code='G')
        l3 = Language.objects.create(name='Engrish',  code='EN')

        jet = self.contacts[1];     jet.language   = [l1, l3]
        rei = self.contacts[4];     rei.language   = [l1]
        asuka = self.contacts[6];   asuka.language = [l1, l2, l3]

        self.assertEqual(3, Contact.objects.filter(language__code='JP').count())
        self.assertEqual(4, Contact.objects.filter(language__name__contains='an').count()) #BEWARE: doublon !!
        self.assertEqual(3, Contact.objects.filter(language__name__contains='an').distinct().count())

        efilter = EntityFilter.create('test-filter01', 'JP', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IEQUALS,
                                                                    name='language__code', values=['JP']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [jet.id, rei.id, asuka.id])

        efilter = EntityFilter.create('test-filter02', 'lang contains "an"', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ICONTAINS,
                                                                    name='language__name', values=['an']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [jet.id, rei.id, asuka.id])

    def test_problematic_validation_fields(self):
        efilter = EntityFilter.create('test-filter01', 'Mist..', Contact)
        build = EntityFilterCondition.build_4_field

        try:
            #Problem a part of a email address is not a valid email address
            efilter.set_conditions([build(model=Contact, operator=EntityFilterCondition.ISTARTSWITH, name='email', values=['misato'])])
        except Exception as e:
            self.fail(str(e))

        try:
            efilter.set_conditions([build(model=Contact, operator=EntityFilterCondition.RANGE, name='email', values=['misato', 'yui'])])
        except Exception as e:
            self.fail(str(e))

        try:
            efilter.set_conditions([build(model=Contact, operator=EntityFilterCondition.EQUALS, name='email', values=['misato@nerv.jp'])])
        except Exception as e:
            self.fail(str(e))

        self.assertRaises(EntityFilterCondition.ValueError, build,
                          model=Contact, operator=EntityFilterCondition.EQUALS, name='email', values=['misato'],
                         )

    def test_build_condition(self): #errors
        ValueError = EntityFilterCondition.ValueError
        build_4_field = EntityFilterCondition.build_4_field

        self.assertRaises(ValueError, build_4_field,
                          model=Contact, operator=EntityFilterCondition.CONTAINS, name='unknown_field', values=['Misato'],
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=Organisation, operator=EntityFilterCondition.GT, name='capital', values=['Not an integer']
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=Contact, operator=EntityFilterCondition.ISEMPTY, name='description', values=['Not a boolean'], #ISEMPTY => boolean
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=Contact, operator=EntityFilterCondition.ISEMPTY, name='description', values=[True, True], #only one boolean is expected
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=Contact, operator=EntityFilterCondition.STARTSWITH, name='civility__unknown', values=['Mist']
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=Organisation, operator=EntityFilterCondition.RANGE, name='capital', values=[5000]
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=Organisation, operator=EntityFilterCondition.RANGE, name='capital', values=[5000, 50000, 100000]
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=Organisation, operator=EntityFilterCondition.RANGE, name='capital', values=['not an integer', 500000]
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=Organisation, operator=EntityFilterCondition.RANGE, name='capital', values=[500000, 'not an integer']
                         )

    def test_condition_update(self):
        build = EntityFilterCondition.build_4_field
        cond1 = build(model=Contact, operator=EntityFilterCondition.EQUALS,  name='first_name', values=['Jet'])
        self.assertFalse(build(model=Contact, operator=EntityFilterCondition.EQUALS,  name='first_name', values=['Jet']).update(cond1))
        self.assertTrue(build(model=Contact,  operator=EntityFilterCondition.IEQUALS, name='first_name', values=['Jet']).update(cond1))
        self.assertTrue(build(model=Contact,  operator=EntityFilterCondition.EQUALS,  name='last_name',  values=['Jet']).update(cond1))
        self.assertTrue(build(model=Contact,  operator=EntityFilterCondition.EQUALS,  name='first_name', values=['Ed']).update(cond1))
        self.assertTrue(build(model=Contact,  operator=EntityFilterCondition.IEQUALS, name='last_name',  values=['Jet']).update(cond1))
        self.assertTrue(build(model=Contact,  operator=EntityFilterCondition.IEQUALS, name='last_name',  values=['Ed']).update(cond1))

    def test_set_conditions01(self):
        build = EntityFilterCondition.build_4_field
        efilter = EntityFilter.create('test-filter01', 'Jet', Contact)
        efilter.set_conditions([build(model=Contact, operator=EntityFilterCondition.EQUALS, name='first_name', values=['Jet'])])

        #NB: create an other condition that has he last id (so if we delete the
        #    first condition, and recreate another one, the id will be different)
        EntityFilter.create('test-filter02', 'Faye', Contact) \
                    .set_conditions([build(model=Contact, operator=EntityFilterCondition.EQUALS, name='first_name', values=['Faye'])])

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))
        old_id = conditions[0].id

        operator = EntityFilterCondition.CONTAINS
        name = 'last_name'
        value = 'Black'
        efilter.set_conditions([build(model=Contact, operator=operator, name=name, values=[value])])

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,           condition.type)
        self.assertEqual(name,                                      condition.name)
        self.assertEqual({'operator': operator, 'values': [value]}, condition.decoded_value)
        self.assertEqual(old_id,                                    condition.id)

    def test_set_conditions02(self):
        efilter = EntityFilter.create('test-filter01', 'Jet', Contact)

        kwargs1 = {'model':     Contact,
                   'operator':  EntityFilterCondition.EQUALS,
                   'name':      'first_name',
                   'values':    ['Jet'],
                  }
        kwargs2 = dict(kwargs1)
        kwargs2['operator'] = EntityFilterCondition.IEQUALS

        build = EntityFilterCondition.build_4_field
        efilter.set_conditions([build(**kwargs1), build(**kwargs2)])

        #NB: see test_set_conditions01()
        EntityFilter.create('test-filter02', 'Faye', Contact) \
                    .set_conditions([build(model=Contact, operator=EntityFilterCondition.EQUALS, name='first_name', values=['Faye'])])

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

    def test_multi_conditions_and01(self):
        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact)
        build = EntityFilterCondition.build_4_field
        efilter.set_conditions([build(model=Contact, operator=EntityFilterCondition.EQUALS,
                                      name='last_name', values=['Ikari']
                                     ),
                                build(model=Contact, operator=EntityFilterCondition.STARTSWITH,
                                      name='first_name', values=['Shin']
                                     )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[7].id])

    def test_multi_conditions_or01(self):
        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact, use_or=True)
        build = EntityFilterCondition.build_4_field
        efilter.set_conditions([build(model=Contact, operator=EntityFilterCondition.EQUALS,
                                      name='last_name', values=['Spiegel']
                                     ),
                                build(model=Contact, operator=EntityFilterCondition.STARTSWITH,
                                      name='first_name', values=['Shin']
                                     )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[0].id, self.contacts[7].id])

    def test_subfilter01(self):
        build_4_field = EntityFilterCondition.build_4_field
        build_sf      = EntityFilterCondition.build_4_subfilter
        sub_efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact, use_or=True)
        sub_efilter.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS,     name='last_name',  values=['Spiegel']),
                                    build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='first_name', values=['Shin'])
                                   ])
        efilter = EntityFilter.create(pk='test-filter02', name='Filter02', model=Contact, use_or=False)
        conds = [build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='first_name', values=['Spi']),
                 build_sf(sub_efilter),
                ]
        try:
            efilter.check_cycle(conds)
        except Exception as e:
            self.fail(str(e))

        efilter.set_conditions(conds)
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[0].id])

        #Test that a CycleError is not raised
        sub_sub_efilter = EntityFilter.create(pk='test-filter03', name='Filter03', model=Contact)
        sub_sub_efilter.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS,     name='last_name',  values=['Black']),
                                        build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='first_name', values=['Jet'])
                                       ])

        conds = [build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='first_name', values=['Spi']),
                 build_sf(sub_sub_efilter),
                ]
        try:
            sub_efilter.check_cycle(conds)
        except Exception as e:
            self.fail(str(e))

    def test_subfilter02(self): #cycle error (lenght = 0)
        efilter = EntityFilter.create(pk='test-filter02', name='Filter01', model=Contact, use_or=False)
        conds = [EntityFilterCondition.build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH,
                                                     name='first_name', values=['Spi']
                                                    ),
                 EntityFilterCondition.build_4_subfilter(efilter),
                ]
        self.assertRaises(EntityFilter.CycleError, efilter.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter.set_conditions, conds)

    def test_subfilter03(self): #cycle error (lenght = 1)
        build_4_field = EntityFilterCondition.build_4_field
        build_sf = EntityFilterCondition.build_4_subfilter

        efilter01 = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact, use_or=True)
        efilter01.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS, name='last_name', values=['Spiegel'])])

        efilter02 = EntityFilter.create(pk='test-filter02', name='Filter02', model=Contact, use_or=False)
        self.assertEqual(set([efilter02.id]), efilter02.get_connected_filter_ids())

        efilter02.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='first_name', values=['Spi']),
                                  build_sf(efilter01),
                                 ])

        conds = [build_4_field(model=Contact, operator=EntityFilterCondition.CONTAINS, name='first_name', values=['Faye']),
                 build_sf(efilter02),
                ]
        efilter01 = self.refresh(efilter01)
        self.assertEqual(set([efilter01.id, efilter02.id]), efilter01.get_connected_filter_ids())
        self.assertRaises(EntityFilter.CycleError, efilter01.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter01.set_conditions, conds)

    def test_subfilter04(self): #cycle error (lenght = 2)
        build_4_field = EntityFilterCondition.build_4_field
        build_sf = EntityFilterCondition.build_4_subfilter

        efilter01 = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact, use_or=True)
        efilter01.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS, name='last_name', values=['Spiegel'])])

        efilter02 = EntityFilter.create(pk='test-filter02', name='Filter02', model=Contact, use_or=False)
        efilter02.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, values=['Spi'], name='first_name'),
                                  build_sf(efilter01),
                                 ])

        efilter03 = EntityFilter.create(pk='test-filter03', name='Filter03', model=Contact, use_or=False)
        efilter03.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.ISTARTSWITH, values=['Misa'], name='first_name'),
                                  build_sf(efilter02),
                                 ])

        conds = [build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS, name='last_name', values=['Spiegel']),
                 build_sf(efilter03),
                ]
        efilter01 = self.refresh(efilter01)
        self.assertRaises(EntityFilter.CycleError, efilter01.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter01.set_conditions, conds)

    def test_properties01(self):
        ptype = CremePropertyType.create(str_pk='test-prop_kawaii', text=u'Kawaii')
        cute_ones = (2, 4, 5, 6)

        for girl_id in cute_ones:
            CremeProperty.objects.create(type=ptype, creme_entity=self.contacts[girl_id])

        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_property(ptype=ptype, has=True)])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[i].id for i in cute_ones])

        efilter.set_conditions([EntityFilterCondition.build_4_property(ptype=ptype, has=False)])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in cute_ones])

    def _aux_test_relations(self):
        self.loves, self.loved = RelationType.create(('test-subject_love', u'Is loving'),
                                                     ('test-object_love',  u'Is loved by')
                                                    )

        self.hates, self.hated = RelationType.create(('test-subject_hate', u'Is hating'),
                                                     ('test-object_hate',  u'Is hated by')
                                                    )

        bebop = Organisation.objects.create(user=self.user, name='Bebop')

        loves = self.loves
        c = self.contacts
        create = Relation.objects.create
        create(subject_entity=c[2], type=loves, object_entity=c[0],  user=self.user)
        create(subject_entity=c[7], type=loves, object_entity=c[4],  user=self.user)
        create(subject_entity=c[9], type=loves, object_entity=c[4],  user=self.user)
        create(subject_entity=c[1], type=loves, object_entity=bebop, user=self.user)

        create(subject_entity=c[7], type=self.hates, object_entity=c[9],  user=self.user)

        return loves

    def test_relations01(self): #no ct/entity
        loves = self._aux_test_relations()
        in_love = [self.contacts[2].id, self.contacts[7].id, self.contacts[9].id, self.contacts[1].id]

        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=True)])
        self.assertExpectedFiltered(efilter, Contact, in_love)

        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=False)])
        self.assertExpectedFiltered(efilter, Contact, [c.id for c in self.contacts if c.id not in in_love])

    def test_relations02(self): #wanted ct
        loves = self._aux_test_relations()
        in_love = [self.contacts[2].id, self.contacts[7].id, self.contacts[9].id] # not 'jet' ('bebop' not is a Contact)

        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=True, ct=self.contact_ct)])
        self.assertExpectedFiltered(efilter, Contact, in_love)

        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=False, ct=self.contact_ct)])
        self.assertExpectedFiltered(efilter, Contact, [c.id for c in self.contacts if c.id not in in_love])

    def test_relations03(self): #wanted entity
        loves = self._aux_test_relations()
        in_love = [self.contacts[7].id, self.contacts[9].id]
        rei = self.contacts[4]

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=True, entity=rei)])
        self.assertExpectedFiltered(efilter, Contact, in_love)

        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=False, entity=rei)])
        self.assertExpectedFiltered(efilter, Contact, [c.id for c in self.contacts if c.id not in in_love])

    def test_relations04(self): #wanted entity is deleted
        loves = self._aux_test_relations()
        rei = self.contacts[4]

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=True, entity=rei)])

        try:
            Relation.objects.filter(object_entity=rei.id).delete()
            rei.delete()
        except Exception as e:
            self.fail('Problem with entity deletion:' + str(e))

        self.assertExpectedFiltered(efilter, Contact, [])

    def test_relations05(self): #RelationType is deleted
        loves = self._aux_test_relations()

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01', model=Contact)
        build = EntityFilterCondition.build_4_relation
        efilter.set_conditions([build(rtype=loves,      has=True, entity=self.contacts[4]),
                                build(rtype=self.loved, has=True, ct=self.contact_ct),
                                build(rtype=self.hates, has=True),
                               ])

        loves.delete()
        self.assertEqual([self.hates.id], [cond.name for cond in efilter.conditions.all()])

    def test_relations06(self): #several conditions on relations (with OR)
        loves = self._aux_test_relations()
        gendo = self.contacts[9]

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01', model=Contact, use_or=True)
        build = EntityFilterCondition.build_4_relation
        efilter.set_conditions([build(rtype=loves,      has=True, entity=self.contacts[4]),
                                build(rtype=self.hates, has=True, entity=gendo),
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[7].id, gendo.id])

    def test_relations07(self): #several conditions on relations (with AND)
        loves = self._aux_test_relations()

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01', model=Contact, use_or=False)
        build = EntityFilterCondition.build_4_relation
        efilter.set_conditions([build(rtype=loves,      has=True, entity=self.contacts[4]),
                                build(rtype=self.hates, has=True, entity=self.contacts[9]),
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[7].id])

    def test_relations_subfilter01(self):
        loves = self._aux_test_relations()
        in_love = [self.contacts[7].id, self.contacts[9].id]

        sub_efilter = EntityFilter.create(pk='test-filter01', name='Filter Rei', model=Contact)
        build_4_field = EntityFilterCondition.build_4_field
        sub_efilter.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='last_name',  values=['Ayanami']),
                                    build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS,     name='first_name', values=['Rei'])
                                   ])
        self.assertExpectedFiltered(sub_efilter, Contact, [self.contacts[4].id])

        efilter = EntityFilter.create(pk='test-filter02', name='Filter Rei lovers', model=Contact)
        conds = [EntityFilterCondition.build_4_relation_subfilter(rtype=loves, has=True, subfilter=sub_efilter)]

        try:
            efilter.check_cycle(conds)
        except Exception as e:
            self.fail(str(e))

        efilter.set_conditions(conds)
        self.assertExpectedFiltered(efilter, Contact, in_love)

        efilter.set_conditions([EntityFilterCondition.build_4_relation_subfilter(rtype=loves, has=False, subfilter=sub_efilter)])
        self.assertExpectedFiltered(efilter, Contact, [c.id for c in self.contacts if c.id not in in_love])

    def test_relations_subfilter02(self): #cycle error (lenght = 0)
        loves = self._aux_test_relations()

        efilter = EntityFilter.create(pk='test-filter01', name='Filter Rei lovers', model=Contact)
        conds = [EntityFilterCondition.build_4_relation_subfilter(rtype=loves, has=True, subfilter=efilter)]

        self.assertRaises(EntityFilter.CycleError, efilter.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter.set_conditions, conds)

    def test_relations_subfilter03(self): #cycle error (lenght = 1)
        loves = self._aux_test_relations()

        efilter01 = EntityFilter.create(pk='test-filter01', name='Filter 01', model=Contact)
        efilter01.set_conditions([EntityFilterCondition.build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS,
                                                                      name='last_name', values=['Ayanami'])
                                 ])

        efilter02 = EntityFilter.create(pk='test-filter02', name='Filter 02', model=Contact)
        efilter02.set_conditions([EntityFilterCondition.build_4_relation_subfilter(rtype=loves, has=True, subfilter=efilter01)])

        conds = [EntityFilterCondition.build_4_relation_subfilter(rtype=self.hates, has=False, subfilter=efilter02)]
        efilter01 = EntityFilter.objects.get(pk=efilter01.pk) #refresh
        self.assertRaises(EntityFilter.CycleError, efilter01.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter01.set_conditions, conds)

    def test_relations_subfilter04(self): #RelationType is deleted
        loves = self._aux_test_relations()
        build_4_field = EntityFilterCondition.build_4_field

        sub_efilter01 = EntityFilter.create(pk='test-filter01', name='Filter Rei', model=Contact)
        sub_efilter01.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='last_name',  values=['Ayanami'])])

        sub_efilter02 = EntityFilter.create(pk='test-filter02', name='Filter Rei', model=Contact)
        sub_efilter02.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='first_name',  values=['Misa'])])

        efilter = EntityFilter.create(pk='test-filter03', name='Filter Rei lovers', model=Contact)
        build = EntityFilterCondition.build_4_relation_subfilter
        efilter.set_conditions([build(rtype=loves,      has=True, subfilter=sub_efilter01),
                                build(rtype=self.hates, has=True, subfilter=sub_efilter02),
                               ])

        loves.delete()
        self.assertEqual([self.hates.id], [cond.name for cond in efilter.conditions.all()])

    def test_relations_subfilter05(self): #several conditions (with OR)
        loves = self._aux_test_relations()

        build_4_field = EntityFilterCondition.build_4_field

        sub_efilter01 = EntityFilter.create(pk='test-filter01', name='Filter Rei', model=Contact)
        sub_efilter01.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='last_name',  values=['Ayanami']),
                                      build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS,     name='first_name', values=['Rei'])
                                    ])
        self.assertExpectedFiltered(sub_efilter01, Contact, [self.contacts[4].id])

        sub_efilter02 = EntityFilter.create(pk='test-filter02', name='Filter Gendo', model=Contact)
        sub_efilter02.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS, name='first_name', values=[u'Gendô'])])
        self.assertExpectedFiltered(sub_efilter02, Contact, [self.contacts[9].id])

        efilter = EntityFilter.create(pk='test-filter03', name='Filter with 2 sublovers', model=Contact, use_or=True)
        build = EntityFilterCondition.build_4_relation_subfilter
        efilter.set_conditions([build(rtype=loves,      has=True, subfilter=sub_efilter01),
                                build(rtype=self.hates, has=True, subfilter=sub_efilter02),
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[7].id, self.contacts[9].id])

    def test_relations_subfilter06(self): #several conditions (with AND)
        loves = self._aux_test_relations()

        build_4_field = EntityFilterCondition.build_4_field

        sub_efilter01 = EntityFilter.create(pk='test-filter01', name='Filter Rei', model=Contact)
        sub_efilter01.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='last_name',  values=['Ayanami']),
                                      build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS,     name='first_name', values=['Rei'])
                                    ])
        self.assertExpectedFiltered(sub_efilter01, Contact, [self.contacts[4].id])

        sub_efilter02 = EntityFilter.create(pk='test-filter02', name='Filter Gendo', model=Contact)
        sub_efilter02.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS, name='first_name', values=[u'Gendô'])])
        self.assertExpectedFiltered(sub_efilter02, Contact, [self.contacts[9].id])

        efilter = EntityFilter.create(pk='test-filter03', name='Filter with 2 sublovers', model=Contact, use_or=False)
        build = EntityFilterCondition.build_4_relation_subfilter
        efilter.set_conditions([build(rtype=loves,      has=True, subfilter=sub_efilter01),
                                build(rtype=self.hates, has=True, subfilter=sub_efilter02),
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[7].id])

    def test_date01(self): # GTE operator
        efilter = EntityFilter.create('test-filter01', 'After 2000-1-1', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=Contact, name='birthday',
                                                                   start=date(year=2000, month=1, day=1),
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[6].id, self.contacts[7].id])

    def test_date02(self): # LTE operator
        efilter = EntityFilter.create('test-filter01', 'Before 1999-12-31', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=Contact, name='birthday',
                                                                   end=date(year=1999, month=12, day=31),
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[5].id])

    def test_date03(self): #range
        efilter = EntityFilter.create('test-filter01', name='Between 2001-1-1 & 2001-12-1', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=Contact, name='birthday',
                                                                   start=date(year=2001, month=1, day=1),
                                                                   end=date(year=2001, month=12, day=1),
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[7].id])

    def test_date04(self): #relative to now
        faye = self.contacts[2]
        future = date.today()
        future = future.replace(year=future.year + 100)
        faye.birthday = future
        faye.save()

        efilter = EntityFilter.create('test-filter01', name='In the future', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=Contact, name='birthday',
                                                                   date_range='in_future',
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [faye.id])

    def test_build_date(self): #errors
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_date,
                          model=Contact, name='unknown_field', start=date(year=2001, month=1, day=1)
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_date,
                          model=Contact, name='first_name', start=date(year=2001, month=1, day=1) #not a date
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_date,
                          model=Contact, name='birthday' #no date
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_date,
                          model=Contact, name='birthday', date_range='unknown_range',
                         )

    def test_customfield01(self): #INT, only one CustomField, LTE operator
        rei = self.contacts[4]

        custom_field = CustomField.objects.create(name='size (cm)', content_type=self.contact_ct, field_type=CustomField.INT)
        custom_field.get_value_class()(custom_field=custom_field, entity=rei).set_value_n_save(150)
        custom_field.get_value_class()(custom_field=custom_field, entity=self.contacts[5]).set_value_n_save(170)
        self.assertEqual(2, CustomFieldInteger.objects.count())

        efilter = EntityFilter.create('test-filter01', name='Small', model=Contact)
        cond = EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                         operator=EntityFilterCondition.LTE,
                                                         value=155
                                                        )
        self.assertEqual(EntityFilterCondition.EFC_CUSTOMFIELD, cond.type)

        efilter.set_conditions([cond])
        self.assertExpectedFiltered(efilter, Contact, [rei.id])

    def test_customfield02(self): #2 INT CustomFields (can interfere), GTE operator
        asuka = self.contacts[6]

        custom_field01 = CustomField.objects.create(name='size (cm)', content_type=self.contact_ct, field_type=CustomField.INT)
        custom_field01.get_value_class()(custom_field=custom_field01, entity=self.contacts[4]).set_value_n_save(150)
        custom_field01.get_value_class()(custom_field=custom_field01, entity=asuka).set_value_n_save(160)

        #should not be retrieved, because fiklter is relative to 'custom_field01'
        custom_field02 = CustomField.objects.create(name='weight (pound)', content_type=self.contact_ct, field_type=CustomField.INT)
        custom_field02.get_value_class()(custom_field=custom_field02, entity=self.contacts[0]).set_value_n_save(156)

        self.assertEqual(3, CustomFieldInteger.objects.count())

        efilter = EntityFilter.create('test-filter01', name='Not so small', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_customfield(custom_field=custom_field01,
                                                                          operator=EntityFilterCondition.GTE,
                                                                          value=155
                                                                         )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [asuka.id])

    def test_customfield03(self): #STR, CONTAINS_NOT operator (negate)
        custom_field = CustomField.objects.create(name='Eva', content_type=self.contact_ct, field_type=CustomField.STR)
        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=self.contacts[4]).set_value_n_save('Eva-00')
        klass(custom_field=custom_field, entity=self.contacts[7]).set_value_n_save('Eva-01')
        klass(custom_field=custom_field, entity=self.contacts[5]).set_value_n_save('Eva-02')
        self.assertEqual(3, CustomFieldString.objects.count())

        efilter = EntityFilter.create('test-filter01', name='not 00', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                                          operator=EntityFilterCondition.CONTAINS_NOT,
                                                                          value='00'
                                                                         )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i != 4])

    def test_customfield04(self): #2 INT CustomFields with 2 conditions
        asuka = self.contacts[6]
        spike = self.contacts[0]

        custom_field01 = CustomField.objects.create(name='size (cm)', content_type=self.contact_ct, field_type=CustomField.INT)
        klass = custom_field01.get_value_class()
        klass(custom_field=custom_field01, entity=spike).set_value_n_save(180)
        klass(custom_field=custom_field01, entity=self.contacts[4]).set_value_n_save(150)
        klass(custom_field=custom_field01, entity=asuka).set_value_n_save(160)

        custom_field02 = CustomField.objects.create(name='weight (pound)', content_type=self.contact_ct, field_type=CustomField.INT)
        klass = custom_field02.get_value_class()
        klass(custom_field=custom_field02, entity=spike).set_value_n_save(156)
        klass(custom_field=custom_field02, entity=asuka).set_value_n_save(80)

        efilter = EntityFilter.create('test-filter01', name='Not so small but light', model=Contact)
        build_cond = EntityFilterCondition.build_4_customfield
        efilter.set_conditions([build_cond(custom_field=custom_field01,
                                           operator=EntityFilterCondition.GTE,
                                           value=155
                                          ),
                                build_cond(custom_field=custom_field02,
                                           operator=EntityFilterCondition.LTE,
                                           value=100
                                          ),
                               ])
        self.assertExpectedFiltered(efilter, Contact, [asuka.id])

    def test_customfield05(self): #FLOAT
        ed  = self.contacts[3]
        rei = self.contacts[4]

        custom_field = CustomField.objects.create(name='Weight (kg)', content_type=self.contact_ct, field_type=CustomField.FLOAT)
        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=ed).set_value_n_save('38.20')
        klass(custom_field=custom_field, entity=rei).set_value_n_save('40.00')
        klass(custom_field=custom_field, entity=self.contacts[6]).set_value_n_save('40.5')

        self.assertEqual(3, CustomFieldFloat.objects.count())

        efilter = EntityFilter.create('test-filter01', name='<= 40', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                         operator=EntityFilterCondition.LTE,
                                                         value='40'
                                                        )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [ed.id, rei.id])

    def test_customfield06(self): #ENUM
        rei = self.contacts[4]

        custom_field = CustomField.objects.create(name='Eva', content_type=self.contact_ct, field_type=CustomField.ENUM)
        create_evalue = CustomFieldEnumValue.objects.create
        eva00 = create_evalue(custom_field=custom_field, value='Eva-00')
        eva01 = create_evalue(custom_field=custom_field, value='Eva-01')
        eva02 = create_evalue(custom_field=custom_field, value='Eva-02')

        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=rei).set_value_n_save(eva00.id)
        klass(custom_field=custom_field, entity=self.contacts[6]).set_value_n_save(eva02.id)

        self.assertEqual(2, CustomFieldEnum.objects.count())

        efilter = EntityFilter.create('test-filter01', name='Eva-00', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                         operator=EntityFilterCondition.EQUALS,
                                                         value=eva00.id #TODO: "value=eva00"
                                                        )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [rei.id])

    def test_customfield07(self): #BOOL
        rei = self.contacts[4]

        custom_field = CustomField.objects.create(name='cute ??', content_type=self.contact_ct, field_type=CustomField.BOOL)
        custom_field.get_value_class()(custom_field=custom_field, entity=rei).set_value_n_save(True)
        custom_field.get_value_class()(custom_field=custom_field, entity=self.contacts[1]).set_value_n_save(False)
        self.assertEqual(2, CustomFieldBoolean.objects.count())

        efilter = EntityFilter.create('test-filter01', name='Cuties', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                                          operator=EntityFilterCondition.EQUALS,
                                                                          value=True
                                                                         )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [rei.id])

    def test_customfield08(self): #CustomField is deleted
        rei = self.contacts[4]

        custom_field01 = CustomField.objects.create(name='Size (cm)', content_type=self.contact_ct, field_type=CustomField.INT)
        custom_field02 = CustomField.objects.create(name='IQ',        content_type=self.contact_ct, field_type=CustomField.INT)

        efilter = EntityFilter.create('test-filter01', name='Small', model=Contact)
        build = EntityFilterCondition.build_4_customfield
        efilter.set_conditions([build(custom_field=custom_field01, operator=EntityFilterCondition.LTE, value=155),
                                build(custom_field=custom_field02, operator=EntityFilterCondition.LTE, value=155),
                               ])

        custom_field01.delete()
        self.assertEqual([unicode(custom_field02.id)], [cond.name for cond in efilter.conditions.all()])

    def test_build_customfield(self): #errors
        custom_field = CustomField.objects.create(name='size (cm)', content_type=self.contact_ct, field_type=CustomField.INT)
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_customfield,
                          custom_field=custom_field, operator=1216, value=155 #invalid operator
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_customfield,
                          custom_field=custom_field, operator=EntityFilterCondition.CONTAINS, value='not an int'
                         )

        custom_field = CustomField.objects.create(name='Day', content_type=self.contact_ct, field_type=CustomField.DATE)
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_customfield,
                          custom_field=custom_field, operator=EntityFilterCondition.EQUALS, value=2011 #DATE
                         )

        custom_field = CustomField.objects.create(name='Cute ?', content_type=self.contact_ct, field_type=CustomField.BOOL)
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_customfield,
                          custom_field=custom_field, operator=EntityFilterCondition.CONTAINS, value=True #bad operator
                         )

    def _aux_test_datecf(self):
        custom_field = CustomField.objects.create(name='First fight', content_type=self.contact_ct, field_type=CustomField.DATE)

        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=self.contacts[4]).set_value_n_save(date(year=2015, month=3, day=14))
        klass(custom_field=custom_field, entity=self.contacts[7]).set_value_n_save(date(year=2015, month=4, day=21))
        klass(custom_field=custom_field, entity=self.contacts[6]).set_value_n_save(date(year=2015, month=5, day=3))

        self.assertEqual(3, CustomFieldDateTime.objects.count())

        return custom_field

    def test_datecustomfield01(self): # GTE operator
        custom_field = self._aux_test_datecf()

        year = 2015; month = 4; day = 1
        efilter = EntityFilter.create('test-filter01', 'After April', Contact)
        cond = EntityFilterCondition.build_4_datecustomfield(custom_field=custom_field,
                                                             start=date(year=year, month=month, day=day),
                                                            )
        self.assertEqual(EntityFilterCondition.EFC_DATECUSTOMFIELD, cond.type)

        efilter.set_conditions([cond])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[6].id, self.contacts[7].id])

    def test_datecustomfield02(self): # LTE operator
        custom_field = self._aux_test_datecf()

        year = 2015; month = 5; day = 1
        efilter = EntityFilter.create('test-filter01', 'Before May', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_datecustomfield(custom_field=custom_field,
                                                                              end=date(year=year, month=month, day=day),
                                                                             )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[4].id, self.contacts[7].id])

    def test_datecustomfield03(self): #range
        custom_field = self._aux_test_datecf()

        efilter = EntityFilter.create('test-filter01', 'In April', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_datecustomfield(custom_field=custom_field,
                                                                              start=date(year=2015, month=4, day=1),
                                                                              end=date(year=2015, month=4, day=30),
                                                                             )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[7].id])

    def test_datecustomfield04(self): #relative to now
        custom_field = CustomField.objects.create(name='First flight', content_type=self.contact_ct, field_type=CustomField.DATE)

        spike = self.contacts[0]
        jet   = self.contacts[1]
        today = date.today()

        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=self.contacts[2]).set_value_n_save(date(year=2000, month=3, day=14))
        klass(custom_field=custom_field, entity=spike).set_value_n_save(today.replace(year=today.year + 100))
        klass(custom_field=custom_field, entity=jet).set_value_n_save(today.replace(year=today.year + 95))

        efilter = EntityFilter.create('test-filter01', name='In the future', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_datecustomfield(custom_field=custom_field,
                                                                              date_range='in_future'
                                                                             )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [spike.id, jet.id])

    def test_datecustomfield05(self): #2 DATE CustomFields with 2 conditions
        shinji = self.contacts[7]
        custom_field01 = self._aux_test_datecf()
        custom_field02 = CustomField.objects.create(name='Last fight', content_type=self.contact_ct, field_type=CustomField.DATE)

        klass = custom_field02.get_value_class()
        klass(custom_field=custom_field02, entity=self.contacts[4]).set_value_n_save(date(year=2020, month=3, day=14))
        klass(custom_field=custom_field02, entity=shinji).set_value_n_save(date(year=2030, month=4, day=21))
        klass(custom_field=custom_field02, entity=self.contacts[6]).set_value_n_save(date(year=2040, month=5, day=3))

        efilter = EntityFilter.create('test-filter01', 'Complex filter', Contact, use_or=False)
        build_cond = EntityFilterCondition.build_4_datecustomfield
        efilter.set_conditions([build_cond(custom_field=custom_field01, start=date(year=2015, month=4, day=1)),
                                build_cond(custom_field=custom_field02, end=date(year=2040, month=1, day=1))
                               ])
        self.assertExpectedFiltered(efilter, Contact, [shinji.id])

    def test_build_datecustomfield(self): #errors
        custom_field = CustomField.objects.create(name='First flight', content_type=self.contact_ct, field_type=CustomField.INT) #not a DATE
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_datecustomfield,
                          custom_field=custom_field, date_range='in_future'
                         )

        custom_field = CustomField.objects.create(name='Day', content_type=self.contact_ct, field_type=CustomField.DATE)
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_datecustomfield,
                          custom_field=custom_field, #no date
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_datecustomfield,
                          custom_field=custom_field, date_range='unknown_range'
                         )
