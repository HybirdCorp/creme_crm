# -*- coding: utf-8 -*-

try:
    from datetime import date, timedelta
    from functools import partial
    from logging import info

    from django.contrib.contenttypes.models import ContentType
    from django.utils.timezone import now

    from creme.creme_core.global_info import set_global_info
    from creme.creme_core.models import *
    from ..base import CremeTestCase

    from creme.persons.models import Contact, Organisation, Civility
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('EntityFiltersTestCase',)


class EntityFiltersTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        #Contact.objects.all().delete()
        #Organisation.objects.all().delete()

        cls._excluded_ids = frozenset(CremeEntity.objects.values_list('id', flat=True))

    def setUp(self):
        self.login()

        create = partial(Contact.objects.create, user=self.user)

        self.civ_miss   = miss   = Civility.objects.create(title='Miss')
        self.civ_mister = mister = Civility.objects.create(title='Mister')

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

            'kirika':   self.user.linked_contact,
            'mireille': self.other_user.linked_contact,
        }

        self.contact_ct = ContentType.objects.get_for_model(Contact)

    def assertExpectedFiltered(self, efilter, model, ids, case_insensitive=False):
        msg = '(NB: maybe you have case sensitive problems with your DB configuration).' if case_insensitive else ''
        #filtered = list(efilter.filter(model.objects.all()))
        filtered = list(efilter.filter(model.objects.exclude(id__in=self._excluded_ids)))
        self.assertEqual(len(ids), len(filtered), str(filtered) + msg)
        self.assertEqual(set(ids), set(c.id for c in filtered))

    def _get_ikari_case_sensitive(self):
        ikaris = Contact.objects.filter(last_name__exact="Ikari")

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

    def test_ct_cache(self):
        efilter = EntityFilter.create('test-filter01', 'Ikari', Contact)

        with self.assertNumQueries(0):
            ContentType.objects.get_for_id(efilter.entity_type_id)

        efilter = self.refresh(efilter)

        with self.assertNumQueries(0):
            efilter.entity_type

    def test_filter_field_equals01(self):
        #self.assertEqual(len(self.contacts), Contact.objects.count())

        efilter = EntityFilter.create('test-filter01', 'Ikari', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.EQUALS,
                                                                    name='last_name', values=['Ikari']
                                                                   )
                               ])
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(self.refresh(efilter), Contact, self._get_ikari_case_sensitive())

        with self.assertNumQueries(0):
            conds = efilter.get_conditions()

        self.assertEqual(1, len(conds))

        cond = conds[0]
        self.assertIsInstance(cond, EntityFilterCondition)
        self.assertEqual('last_name', cond.name)

    def test_filter_field_equals02(self):
        efilter = EntityFilter.create('test-filter01', 'Spike & Faye', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.EQUALS,
                                                                    name='first_name',
                                                                    values=['Spike', 'Faye']
                                                                   )
                               ])
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(self.refresh(efilter), Contact, self._list_contact_ids('spike', 'faye'))

    def test_filter_field_equals_currentuser(self):
        set_global_info(user=self.user)

        efilter = EntityFilter.create('test-filter01', 'Spike & Faye', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.EQUALS,
                                                                    name='user',
                                                                    values=['__currentuser__']
                                                                   )
                               ])

        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(self.refresh(efilter), Contact, 
                                    #self._list_contact_ids(*self.contacts.keys())
                                    self._list_contact_ids('mireille', exclude=True)
                                   )

        #self.contacts.get('spike').user = self.other_user
        #self.contacts.get('spike').save()

        #self.contacts.get('rei').user = self.other_user
        #self.contacts.get('rei').save()

        rei = self.contacts.get('rei')
        rei.user = self.other_user
        rei.save()

        #self.assertExpectedFiltered(self.refresh(efilter), Contact,
                                    #self._list_contact_ids('jet', 'faye', 'ed', 'misato', 'asuka', 'shinji', 'yui', 'gendou', 'genji', 'risato')
                                   #)

        set_global_info(user=self.other_user)
        self.assertExpectedFiltered(self.refresh(efilter), Contact,
                                    #self._list_contact_ids('spike', 'rei')
                                    self._list_contact_ids('mireille', 'rei')
                                   )

    def test_filter_field_iequals(self):
        efilter = EntityFilter.create('test-filter01', 'Ikari (insensitive)', Contact,
                                      user=self.user, is_custom=False
                                     )
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IEQUALS,
                                                                    name='last_name', values=['Ikari']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact,
                                    self._list_contact_ids('shinji', 'yui', 'gendou'),
                                    case_insensitive=True
                                   )

    def test_filter_field_not_equals(self):
        efilter = EntityFilter.create('test-filter01', 'Not Ikari', Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.EQUALS_NOT,
                                                                    name='last_name', values=['Ikari']
                                                                   )
                               ])

        excluded = frozenset(self._get_ikari_case_sensitive())
        self.assertExpectedFiltered(efilter, Contact,
                                    [c.id for c in self.contacts.itervalues() if c.id not in excluded]
                                   )

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
        self.assertExpectedFiltered(efilter, Contact,
                                    self._list_contact_ids('shinji', 'yui', 'gendou', exclude=True)
                                   )

    def test_filter_field_contains(self):
        efilter = EntityFilter.create('test-filter01', name='Contains "isat"', model=Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.CONTAINS,
                                                                    name='first_name', values=['isat']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('misato', 'risato'))

    def test_filter_field_icontains(self):
        efilter = EntityFilter.create(pk='test-filter01', name='Not contains "Misa"', model=Contact, user=self.user)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ICONTAINS,
                                                                    name='first_name', values=['misa']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts['misato'].id], True)

    def test_filter_field_contains_not(self):
        efilter = EntityFilter.create('test-filter01', 'Not Ikari', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.CONTAINS_NOT,
                                                                    name='first_name', values=['sato']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('misato', 'risato', exclude=True))

    def test_filter_field_icontains_not(self):
        efilter = EntityFilter.create('test-filter01', 'Not contains "sato" (ci)', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ICONTAINS_NOT,
                                                                    name='first_name', values=['sato']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact,
                                    self._list_contact_ids('misato', 'risato', exclude=True),
                                    case_insensitive=True
                                   )

    def test_filter_field_gt(self):
        efilter = EntityFilter.create(pk='test-filter01', name='> Yua', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.GT,
                                                                    name='first_name', values=['Yua']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts['yui'].id])

    def test_filter_field_gte(self):
        efilter = EntityFilter.create('test-filter01', '>= Spike', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.GTE,
                                                                    name='first_name', values=['Spike']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('spike', 'yui'))

    def test_filter_field_lt(self):
        efilter = EntityFilter.create('test-filter01', '< Faye', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.LT,
                                                                    name='first_name', values=['Faye']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('ed', 'asuka'))

    def test_filter_field_lte(self):
        efilter = EntityFilter.create('test-filter01', '<= Faye', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.LTE,
                                                                    name='first_name', values=['Faye']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('faye', 'ed', 'asuka'))

    def test_filter_field_startswith(self):
        efilter = EntityFilter.create(pk='test-filter01', name='starts "Gen"', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.STARTSWITH,
                                                                    name='first_name', values=['Gen']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('gendou', 'genji'))

    def test_filter_field_istartswith(self):
        efilter = EntityFilter.create(pk='test-filter01', name='starts "Gen" (ci)', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ISTARTSWITH,
                                                                    name='first_name', values=['gen']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('gendou', 'genji'))

    def test_filter_field_startswith_not(self):
        efilter = EntityFilter.create(pk='test-filter01', name='starts not "Asu"', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.STARTSWITH_NOT,
                                                                    name='first_name', values=['Asu']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('asuka', exclude=True))

    def test_filter_field_istartswith_not(self):
        efilter = EntityFilter.create('test-filter01', 'starts not "asu"', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ISTARTSWITH_NOT,
                                                                    name='first_name', values=['asu']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('asuka', exclude=True))

    def test_filter_field_endswith(self):
        efilter = EntityFilter.create('test-filter01', 'ends "sato"', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ENDSWITH,
                                                                    name='first_name', values=['sato']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('misato', 'risato'))

    def test_filter_field_iendswith(self):
        efilter = EntityFilter.create('test-filter01', 'ends "SATO"', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IENDSWITH,
                                                                    name='first_name', values=['SATO']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('misato', 'risato'))

    def test_filter_field_endswith_not(self):
        efilter = EntityFilter.create('test-filter01', 'ends not "sato"', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ENDSWITH_NOT,
                                                                    name='first_name', values=['sato']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('misato', 'risato', exclude=True))

    def test_filter_field_iendswith_not(self):
        efilter = EntityFilter.create('test-filter01', 'ends not "SATO" (ci)', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IENDSWITH_NOT,
                                                                    name='first_name', values=['SATO']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('misato', 'risato', exclude=True))

    def test_filter_field_isempty01(self):
        efilter = EntityFilter.create(pk='test-filter01', name='is empty', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ISEMPTY,
                                                                    name='description', values=[True]
                                                                   )
                               ])
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('faye', exclude=True))

    def test_filter_field_isempty02(self):
        efilter = EntityFilter.create('test-filter01', 'is not empty', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ISEMPTY,
                                                                    name='description', values=[False]
                                                                   )
                               ])
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(efilter, Contact, [self.contacts['faye'].id])

    def test_filter_field_isempty03(self): #not charfield
        create = Organisation.objects.create
        user = self.user
        create(user=user,          name='Bebop & cie', capital=None)
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
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('spike', 'jet', 'faye', exclude=True))

    def test_filter_field_range(self):
        create = Organisation.objects.create
        user = self.user
        create(user=user,          name='Bebop & cie', capital=1000)
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
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('spike', 'jet'))

        efilter = EntityFilter.create('test-filter01', 'Not Misses', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.EQUALS_NOT,
                                                                    name='civility', values=[self.civ_miss.id]
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('faye', exclude=True))

    def test_filter_fk02(self):
        efilter = EntityFilter.create('test-filter01', 'Mist..', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ISTARTSWITH,
                                                                    name='civility__title', values=['Mist']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('spike', 'jet'))

    def test_filter_m2m(self):
        l1 = Language.objects.create(name='Japanese', code='JP')
        l2 = Language.objects.create(name='German',   code='G')
        l3 = Language.objects.create(name='Engrish',  code='EN')

        contacts = self.contacts
        jet   = contacts['jet'];   jet.language   = [l1, l3]
        rei   = contacts['rei'];   rei.language   = [l1]
        asuka = contacts['asuka']; asuka.language = [l1, l2, l3]

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

        with self.assertNoException():
            #Problem a part of a email address is not a valid email address
            efilter.set_conditions([build(model=Contact, operator=EntityFilterCondition.ISTARTSWITH, name='email', values=['misato'])])

        with self.assertNoException():
            efilter.set_conditions([build(model=Contact, operator=EntityFilterCondition.RANGE, name='email', values=['misato', 'yui'])])

        with self.assertNoException():
            efilter.set_conditions([build(model=Contact, operator=EntityFilterCondition.EQUALS, name='email', values=['misato@nerv.jp'])])

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
        EQUALS = EntityFilterCondition.EQUALS
        IEQUALS = EntityFilterCondition.IEQUALS
        cond1 = build(model=Contact, operator=EQUALS,  name='first_name', values=['Jet'])
        self.assertFalse(build(model=Contact, operator=EQUALS,  name='first_name', values=['Jet']).update(cond1))
        self.assertTrue(build(model=Contact,  operator=IEQUALS, name='first_name', values=['Jet']).update(cond1))
        self.assertTrue(build(model=Contact,  operator=EQUALS,  name='last_name',  values=['Jet']).update(cond1))
        self.assertTrue(build(model=Contact,  operator=EQUALS,  name='first_name', values=['Ed']).update(cond1))
        self.assertTrue(build(model=Contact,  operator=IEQUALS, name='last_name',  values=['Jet']).update(cond1))
        self.assertTrue(build(model=Contact,  operator=IEQUALS, name='last_name',  values=['Ed']).update(cond1))

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
        self.assertExpectedFiltered(efilter, Contact, [self.contacts['shinji'].id])

        self.assertEqual(2, len(efilter.get_conditions()))

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
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('spike', 'shinji'))

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

        with self.assertNoException():
            efilter.check_cycle(conds)

        efilter.set_conditions(conds)
        self.assertExpectedFiltered(efilter, Contact, [self.contacts['spike'].id])

        #Test that a CycleError is not raised
        sub_sub_efilter = EntityFilter.create(pk='test-filter03', name='Filter03', model=Contact)
        sub_sub_efilter.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS,     name='last_name',  values=['Black']),
                                        build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='first_name', values=['Jet'])
                                       ])

        conds = [build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='first_name', values=['Spi']),
                 build_sf(sub_sub_efilter),
                ]

        with self.assertNoException():
            sub_efilter.check_cycle(conds)

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
        cute_ones = ('faye', 'rei', 'misato', 'asuka')

        for fn in cute_ones:
            CremeProperty.objects.create(type=ptype, creme_entity=self.contacts[fn])

        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_property(ptype=ptype, has=True)])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids(*cute_ones))

        efilter.set_conditions([EntityFilterCondition.build_4_property(ptype=ptype, has=False)])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids(*cute_ones, exclude=True))

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
        create(subject_entity=c['faye'],   type=loves, object_entity=c['spike'], user=self.user)
        create(subject_entity=c['shinji'], type=loves, object_entity=c['rei'],   user=self.user)
        create(subject_entity=c['gendou'], type=loves, object_entity=c['rei'],   user=self.user)
        create(subject_entity=c['jet'],    type=loves, object_entity=bebop,      user=self.user)

        create(subject_entity=c['shinji'], type=self.hates, object_entity=c['gendou'],  user=self.user)

        return loves

    def test_relations01(self): #no ct/entity
        loves = self._aux_test_relations()
        in_love = ('faye', 'shinji', 'gendou', 'jet')

        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=True)])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids(*in_love))

        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=False)])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids(*in_love, exclude=True))

    def test_relations02(self): #wanted ct
        loves = self._aux_test_relations()
        in_love = ('faye', 'shinji', 'gendou') # not 'jet' ('bebop' not is a Contact)

        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=True, ct=self.contact_ct)])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids(*in_love))

        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=False, ct=self.contact_ct)])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids(*in_love, exclude=True))

    def test_relations03(self): #wanted entity
        loves = self._aux_test_relations()
        in_love = ('shinji', 'gendou')
        rei = self.contacts['rei']

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=True, entity=rei)])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids(*in_love))

        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=False, entity=rei)])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids(*in_love, exclude=True))

    def test_relations04(self): #wanted entity is deleted
        loves = self._aux_test_relations()
        rei = self.contacts['rei']

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=True, entity=rei)])

        with self.assertNoException():
            Relation.objects.filter(object_entity=rei.id).delete()
            rei.delete()

        self.assertExpectedFiltered(efilter, Contact, [])

    def test_relations05(self): #RelationType is deleted
        loves = self._aux_test_relations()

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01', model=Contact)
        build = EntityFilterCondition.build_4_relation
        efilter.set_conditions([build(rtype=loves,      has=True, entity=self.contacts['rei']),
                                build(rtype=self.loved, has=True, ct=self.contact_ct),
                                build(rtype=self.hates, has=True),
                               ])

        loves.delete()
        self.assertEqual([self.hates.id], [cond.name for cond in efilter.conditions.all()])

    def test_relations06(self): #several conditions on relations (with OR)
        loves = self._aux_test_relations()
        gendo = self.contacts['gendou']

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01', model=Contact, use_or=True)
        build = EntityFilterCondition.build_4_relation
        efilter.set_conditions([build(rtype=loves,      has=True, entity=self.contacts['rei']),
                                build(rtype=self.hates, has=True, entity=gendo),
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts['shinji'].id, gendo.id])

    def test_relations07(self): #several conditions on relations (with AND)
        loves = self._aux_test_relations()

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01', model=Contact, use_or=False)
        build = EntityFilterCondition.build_4_relation
        efilter.set_conditions([build(rtype=loves,      has=True, entity=self.contacts['rei']),
                                build(rtype=self.hates, has=True, entity=self.contacts['gendou']),
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts['shinji'].id])

    def test_relations_subfilter01(self):
        loves = self._aux_test_relations()
        in_love = ('shinji', 'gendou')

        sub_efilter = EntityFilter.create(pk='test-filter01', name='Filter Rei', model=Contact)
        build_4_field = EntityFilterCondition.build_4_field
        sub_efilter.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='last_name',  values=['Ayanami']),
                                    build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS,     name='first_name', values=['Rei'])
                                   ])
        self.assertExpectedFiltered(sub_efilter, Contact, [self.contacts['rei'].id])

        efilter = EntityFilter.create(pk='test-filter02', name='Filter Rei lovers', model=Contact)
        conds = [EntityFilterCondition.build_4_relation_subfilter(rtype=loves, has=True, subfilter=sub_efilter)]

        with self.assertNoException():
            efilter.check_cycle(conds)

        efilter.set_conditions(conds)
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids(*in_love))

        efilter.set_conditions([EntityFilterCondition.build_4_relation_subfilter(rtype=loves, has=False, subfilter=sub_efilter)])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids(*in_love, exclude=True))

    def test_relations_subfilter02(self):
        "Cycle error (lenght = 0)"
        loves = self._aux_test_relations()

        efilter = EntityFilter.create(pk='test-filter01', name='Filter Rei lovers', model=Contact)
        conds = [EntityFilterCondition.build_4_relation_subfilter(rtype=loves, has=True, subfilter=efilter)]

        self.assertRaises(EntityFilter.CycleError, efilter.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter.set_conditions, conds)

    def test_relations_subfilter03(self):
        "Cycle error (lenght = 1)"
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

    def test_relations_subfilter05(self):
        "Several conditions (with OR)"
        loves = self._aux_test_relations()

        build_4_field = EntityFilterCondition.build_4_field

        sub_efilter01 = EntityFilter.create(pk='test-filter01', name='Filter Rei', model=Contact)
        sub_efilter01.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='last_name',  values=['Ayanami']),
                                      build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS,     name='first_name', values=['Rei'])
                                    ])
        self.assertExpectedFiltered(sub_efilter01, Contact, [self.contacts['rei'].id])

        sub_efilter02 = EntityFilter.create(pk='test-filter02', name=u'Filter Gendô', model=Contact)
        sub_efilter02.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS, name='first_name', values=[u'Gendô'])])
        self.assertExpectedFiltered(sub_efilter02, Contact, [self.contacts['gendou'].id])

        efilter = EntityFilter.create(pk='test-filter03', name='Filter with 2 sublovers', model=Contact, use_or=True)
        build = EntityFilterCondition.build_4_relation_subfilter
        efilter.set_conditions([build(rtype=loves,      has=True, subfilter=sub_efilter01),
                                build(rtype=self.hates, has=True, subfilter=sub_efilter02),
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('shinji', 'gendou'))

    def test_relations_subfilter06(self): #several conditions (with AND)
        loves = self._aux_test_relations()

        build_4_field = EntityFilterCondition.build_4_field

        sub_efilter01 = EntityFilter.create(pk='test-filter01', name='Filter Rei', model=Contact)
        sub_efilter01.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='last_name',  values=['Ayanami']),
                                      build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS,     name='first_name', values=['Rei'])
                                    ])
        self.assertExpectedFiltered(sub_efilter01, Contact, [self.contacts['rei'].id])

        sub_efilter02 = EntityFilter.create(pk='test-filter02', name='Filter Gendo', model=Contact)
        sub_efilter02.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS, name='first_name', values=[u'Gendô'])])
        self.assertExpectedFiltered(sub_efilter02, Contact, [self.contacts['gendou'].id])

        efilter = EntityFilter.create(pk='test-filter03', name='Filter with 2 sublovers', model=Contact, use_or=False)
        build = EntityFilterCondition.build_4_relation_subfilter
        efilter.set_conditions([build(rtype=loves,      has=True, subfilter=sub_efilter01),
                                build(rtype=self.hates, has=True, subfilter=sub_efilter02),
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts['shinji'].id])

    def test_date01(self):
        "GTE operator"
        efilter = EntityFilter.create('test-filter01', 'After 2000-1-1', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=Contact, name='birthday',
                                                                   start=date(year=2000, month=1, day=1),
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('asuka', 'shinji'))

    def test_date02(self):
        "LTE operator"
        efilter = EntityFilter.create('test-filter01', 'Before 1999-12-31', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=Contact, name='birthday',
                                                                   end=date(year=1999, month=12, day=31),
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts['misato'].id])

    def test_date03(self):
        "Range"
        efilter = EntityFilter.create('test-filter01', name='Between 2001-1-1 & 2001-12-1', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=Contact, name='birthday',
                                                                   start=date(year=2001, month=1, day=1),
                                                                   end=date(year=2001, month=12, day=1),
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts['shinji'].id])

    def test_date04(self):
        "Relative to now"
        faye = self.contacts['faye']
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

    def test_datetime01(self):
        "Previous year"
        faye = self.contacts['faye']
        Contact.objects.filter(pk=faye.id).update(created=faye.created - timedelta(days=faye.created.month * 31))

        efilter = EntityFilter.create('test-filter01', name='Created during previous year', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=Contact, name='created',
                                                                   date_range='previous_year',
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('faye'))

    def test_datetime02(self):
        "Current year"
        faye = self.contacts['faye']
        Contact.objects.filter(pk=faye.id).update(created=faye.created - timedelta(days=faye.created.month * 31))

        efilter = EntityFilter.create('test-filter01', name='Created during current year', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=Contact, name='created',
                                                                   date_range='current_year',
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('faye', exclude=True))

    def test_datetime03(self):
        "Next year"
        faye = self.contacts['faye']
        Contact.objects.filter(pk=faye.id).update(created=faye.created + timedelta(days=(13 - faye.created.month) * 31))

        efilter = EntityFilter.create('test-filter01', name='Created during next year (?!)', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=Contact, name='created',
                                                                   date_range='next_year',
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('faye'))

    def test_datetime04(self):
        "Current month"
        faye = self.contacts['faye']
        Contact.objects.filter(pk=faye.id).update(created=faye.created - timedelta(days=31))

        efilter = EntityFilter.create('test-filter01', name='Created during current month', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=Contact, name='created',
                                                                   date_range='current_month',
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('faye', exclude=True))

    def test_datetime05(self):
        "Current quarter"
        faye = self.contacts['faye']
        Contact.objects.filter(pk=faye.id).update(created=faye.created - timedelta(days=4*31))

        efilter = EntityFilter.create('test-filter01', name='Created during current quarter', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=Contact, name='created',
                                                                   date_range='current_quarter',
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('faye', exclude=True))

    def test_build_date(self):
        "Errors"
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

    def test_customfield01(self):
        "INT, only one CustomField, LTE operator"
        rei = self.contacts['rei']

        custom_field = CustomField.objects.create(name='size (cm)', content_type=self.contact_ct, field_type=CustomField.INT)
        custom_field.get_value_class()(custom_field=custom_field, entity=rei).set_value_n_save(150)
        custom_field.get_value_class()(custom_field=custom_field, entity=self.contacts['misato']).set_value_n_save(170)
        self.assertEqual(2, CustomFieldInteger.objects.count())

        efilter = EntityFilter.create('test-filter01', name='Small', model=Contact)
        cond = EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                         operator=EntityFilterCondition.LTE,
                                                         value=155
                                                        )
        self.assertEqual(EntityFilterCondition.EFC_CUSTOMFIELD, cond.type)

        efilter.set_conditions([cond])
        self.assertExpectedFiltered(efilter, Contact, [rei.id])

    def test_customfield02(self):
        "2 INT CustomFields (can interfere), GTE operator"
        contacts = self.contacts
        asuka = contacts['asuka']

        custom_field01 = CustomField.objects.create(name='size (cm)', content_type=self.contact_ct, field_type=CustomField.INT)
        custom_field01.get_value_class()(custom_field=custom_field01, entity=contacts['rei']).set_value_n_save(150)
        custom_field01.get_value_class()(custom_field=custom_field01, entity=asuka).set_value_n_save(160)

        #should not be retrieved, because fiklter is relative to 'custom_field01'
        custom_field02 = CustomField.objects.create(name='weight (pound)', content_type=self.contact_ct, field_type=CustomField.INT)
        custom_field02.get_value_class()(custom_field=custom_field02, entity=self.contacts['spike']).set_value_n_save(156)

        self.assertEqual(3, CustomFieldInteger.objects.count())

        efilter = EntityFilter.create('test-filter01', name='Not so small', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_customfield(custom_field=custom_field01,
                                                                          operator=EntityFilterCondition.GTE,
                                                                          value=155
                                                                         )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [asuka.id])

    def test_customfield03(self):
        "STR, CONTAINS_NOT operator (negate)"
        custom_field = CustomField.objects.create(name='Eva', content_type=self.contact_ct, field_type=CustomField.STR)
        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=self.contacts['rei']).set_value_n_save('Eva-00')
        klass(custom_field=custom_field, entity=self.contacts['shinji']).set_value_n_save('Eva-01')
        klass(custom_field=custom_field, entity=self.contacts['misato']).set_value_n_save('Eva-02')
        self.assertEqual(3, CustomFieldString.objects.count())

        efilter = EntityFilter.create('test-filter01', name='not 00', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                                          operator=EntityFilterCondition.CONTAINS_NOT,
                                                                          value='00'
                                                                         )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('rei', exclude=True))

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

    def test_customfield05(self):
        "FLOAT"
        contacts = self.contacts
        ed  = contacts['ed']
        rei = contacts['rei']

        custom_field = CustomField.objects.create(name='Weight (kg)', content_type=self.contact_ct, field_type=CustomField.FLOAT)
        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=ed).set_value_n_save('38.20')
        klass(custom_field=custom_field, entity=rei).set_value_n_save('40.00')
        klass(custom_field=custom_field, entity=contacts['asuka']).set_value_n_save('40.5')

        self.assertEqual(3, CustomFieldFloat.objects.count())

        efilter = EntityFilter.create('test-filter01', name='<= 40', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                         operator=EntityFilterCondition.LTE,
                                                         value='40'
                                                        )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [ed.id, rei.id])

    def test_customfield06(self):
        "ENUM"
        rei = self.contacts['rei']

        custom_field = CustomField.objects.create(name='Eva', content_type=self.contact_ct, field_type=CustomField.ENUM)
        create_evalue = CustomFieldEnumValue.objects.create
        eva00 = create_evalue(custom_field=custom_field, value='Eva-00')
        create_evalue(custom_field=custom_field,         value='Eva-01')
        eva02 = create_evalue(custom_field=custom_field, value='Eva-02')

        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=rei).set_value_n_save(eva00.id)
        klass(custom_field=custom_field, entity=self.contacts['asuka']).set_value_n_save(eva02.id)

        self.assertEqual(2, CustomFieldEnum.objects.count())

        efilter = EntityFilter.create('test-filter01', name='Eva-00', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                         operator=EntityFilterCondition.EQUALS,
                                                         value=eva00.id #TODO: "value=eva00"
                                                        )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [rei.id])

    def test_customfield07(self): #BOOL
        rei = self.contacts['rei']

        custom_field = CustomField.objects.create(name='cute ??', content_type=self.contact_ct, field_type=CustomField.BOOL)
        value_class = custom_field.get_value_class()
        value_class(custom_field=custom_field, entity=rei).set_value_n_save(True)
        value_class(custom_field=custom_field, entity=self.contacts['jet']).set_value_n_save(False)
        self.assertEqual(2, CustomFieldBoolean.objects.count())

        efilter = EntityFilter.create('test-filter01', name='Cuties', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                                          operator=EntityFilterCondition.EQUALS,
                                                                          value=True
                                                                         )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [rei.id])

    def test_customfield08(self): #CustomField is deleted
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

        custom_field = CustomField.objects.create(name='Day', content_type=self.contact_ct, field_type=CustomField.DATETIME)
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
        custom_field = CustomField.objects.create(name='First fight',
                                                  content_type=self.contact_ct,
                                                  field_type=CustomField.DATETIME,
                                                 )

        #klass = custom_field.get_value_class()
        contacts = self.contacts
        #klass(custom_field=custom_field, entity=contacts['rei']).set_value_n_save(date(year=2015, month=3, day=14))
        #klass(custom_field=custom_field, entity=contacts['shinji']).set_value_n_save(date(year=2015, month=4, day=21))
        #klass(custom_field=custom_field, entity=contacts['asuka']).set_value_n_save(date(year=2015, month=5, day=3))
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

        efilter = EntityFilter.create('test-filter01', 'After April', Contact)
        cond = EntityFilterCondition.build_4_datecustomfield(custom_field=custom_field,
                                                             start=date(year=2015, month=4, day=1),
                                                             #start=self.create_datetime(year=2015, month=4, day=1),
                                                            )
        self.assertEqual(EntityFilterCondition.EFC_DATECUSTOMFIELD, cond.type)

        efilter.set_conditions([cond])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('asuka', 'shinji'))

    def test_datecustomfield02(self):
        "LTE operator"
        custom_field = self._aux_test_datecf()

        efilter = EntityFilter.create('test-filter01', 'Before May', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_datecustomfield(custom_field=custom_field,
                                                                              end=date(year=2015, month=5, day=1),
                                                                             )
                               ])
        self.assertExpectedFiltered(efilter, Contact, self._list_contact_ids('shinji', 'rei'))

    def test_datecustomfield03(self):
        "Range"
        custom_field = self._aux_test_datecf()

        efilter = EntityFilter.create('test-filter01', 'In April', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_datecustomfield(custom_field=custom_field,
                                                                              start=date(year=2015, month=4, day=1),
                                                                              end=date(year=2015, month=4, day=30),
                                                                             )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts['shinji'].id])

    def test_datecustomfield04(self):
        "Relative to now"
        custom_field = CustomField.objects.create(name='First flight',
                                                  content_type=self.contact_ct,
                                                  field_type=CustomField.DATETIME,
                                                 )

        contacts = self.contacts
        spike = contacts['spike']
        jet   = contacts['jet']
        #today = date.today()
        dt_now = now()

        #klass = custom_field.get_value_class()
        #klass(custom_field=custom_field, entity=contacts['faye']).set_value_n_save(date(year=2000, month=3, day=14))
        #klass(custom_field=custom_field, entity=spike).set_value_n_save(today.replace(year=today.year + 100))
        #klass(custom_field=custom_field, entity=jet).set_value_n_save(today.replace(year=today.year + 95))
        klass = partial(custom_field.get_value_class(), custom_field=custom_field)
        klass(entity=contacts['faye']).set_value_n_save(self.create_datetime(year=2000, month=3, day=14))
        klass(entity=spike).set_value_n_save(dt_now + timedelta(days=3650))
        klass(entity=jet).set_value_n_save(dt_now + timedelta(days=700))

        efilter = EntityFilter.create('test-filter01', name='In the future', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_datecustomfield(custom_field=custom_field,
                                                                              date_range='in_future'
                                                                             )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [spike.id, jet.id])

    def test_datecustomfield05(self):
        "2 DATE CustomFields with 2 conditions"
        contacts = self.contacts
        shinji = contacts['shinji']
        custom_field01 = self._aux_test_datecf()
        custom_field02 = CustomField.objects.create(name='Last fight',
                                                    content_type=self.contact_ct,
                                                    field_type=CustomField.DATETIME,
                                                   )

        #klass = custom_field02.get_value_class()
        #klass(custom_field=custom_field02, entity=contacts['rei']).set_value_n_save(date(year=2020, month=3, day=14))
        #klass(custom_field=custom_field02, entity=shinji).set_value_n_save(date(year=2030, month=4, day=21))
        #klass(custom_field=custom_field02, entity=contacts['asuka']).set_value_n_save(date(year=2040, month=5, day=3))
        klass = partial(custom_field02.get_value_class(), custom_field=custom_field02)
        create_dt = self.create_datetime
        klass(entity=contacts['rei']).set_value_n_save(create_dt(year=2020, month=3, day=14))
        klass(entity=shinji).set_value_n_save(create_dt(year=2030, month=4, day=21))
        klass(entity=contacts['asuka']).set_value_n_save(create_dt(year=2040, month=5, day=3))

        efilter = EntityFilter.create('test-filter01', 'Complex filter', Contact, use_or=False)
        build_cond = EntityFilterCondition.build_4_datecustomfield
        efilter.set_conditions([build_cond(custom_field=custom_field01, start=date(year=2015, month=4, day=1)),
                                build_cond(custom_field=custom_field02, end=date(year=2040, month=1, day=1))
                               ])
        self.assertExpectedFiltered(efilter, Contact, [shinji.id])

    def test_build_datecustomfield(self):
        "Errors"
        create_cf = CustomField.objects.create
        custom_field = create_cf(name='First flight', content_type=self.contact_ct, field_type=CustomField.INT) #not a DATE
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_datecustomfield,
                          custom_field=custom_field, date_range='in_future',
                         )

        custom_field = create_cf(name='Day', content_type=self.contact_ct, field_type=CustomField.DATETIME)
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_datecustomfield,
                          custom_field=custom_field, #no date
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_datecustomfield,
                          custom_field=custom_field, date_range='unknown_range',
                         )

    def test_invalid_field(self):
        efilter = EntityFilter.create('test-filter01', 'Ikari', Contact)
        build = partial(EntityFilterCondition.build_4_field, model=Contact,
                        operator=EntityFilterCondition.EQUALS, values=['Ikari'],
                       )
        cond1 = build(name='last_name')
        cond2 = build(name='first_name')
        cond2.name = 'invalid'

        efilter.set_conditions([cond1, cond2])

        with self.assertNoException():
            filtered = list(efilter.filter(Contact.objects.all()))

        self.assertFalse(EntityFilterCondition.objects.filter(pk=cond2.pk).exists())
        self.assertEqual(set(self._get_ikari_case_sensitive()), set(c.id for c in filtered))

    def test_invalid_datefield(self):
        efilter = EntityFilter.create('test-filter01', 'Ikari', Contact)
        cond1 = EntityFilterCondition.build_4_field(model=Contact, name='last_name',
                                                    operator=EntityFilterCondition.EQUALS,
                                                    values=['Ikari'],
                                                   )
        cond2 = EntityFilterCondition.build_4_date(model=Contact, name='birthday',
                                                   start=date(year=2000, month=1, day=1),
                                                  )
        cond2.name = 'invalid'

        efilter.set_conditions([cond1, cond2])
        self.assertEqual(1, len(efilter.get_conditions()))

        with self.assertNoException():
            filtered = list(efilter.filter(Contact.objects.all()))

        self.assertDoesNotExist(cond2)
        self.assertEqual(set(self._get_ikari_case_sensitive()), set(c.id for c in filtered))

    def test_invalid_currentuser(self):
        efilter = EntityFilter.create('test-filter01', 'Spike & Faye', Contact)

        with self.assertRaises(EntityFilterCondition.ValueError):
            efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                        operator=EntityFilterCondition.EQUALS,
                                                                        name='birthday',
                                                                        values=['__currentuser__']
                                                                       )
                                   ])

        with self.assertNoException():
            efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                        operator=EntityFilterCondition.EQUALS,
                                                                        name='last_name',
                                                                        values=['__currentuser__']
                                                                       )
                                   ])
