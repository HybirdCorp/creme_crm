# -*- coding: utf-8 -*-

try:
    import string
    from datetime import datetime, date
    from functools import partial

    #import pytz

    from django.http import Http404
    from django.conf import settings

    from ..base import CremeTestCase
    from creme.creme_core.models import CremePropertyType, PreferedMenuItem
    from creme.creme_core.utils import (find_first, truncate_str, split_filter,
        create_if_needed, update_model_instance, get_from_GET_or_404, get_from_POST_or_404,
        safe_unicode, safe_unicode_error, int_2_roman)
    from creme.creme_core.utils.dates import (get_dt_from_str, get_date_from_str,
        get_dt_from_iso8601_str, get_dt_to_iso8601_str, date_2_dict)
                              #get_creme_dt_from_utc_dt get_utc_dt_from_creme_dt get_naive_dt_from_tzdate
    from creme.creme_core.utils.dependence_sort import dependence_sort, DependenciesLoopError
    from creme.creme_core.utils.queries import get_first_or_None

    from creme.persons.models import Civility, Contact
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class MiscTestCase(CremeTestCase):
    def test_find_first(self):
        class Info(object):
            def __init__(self, data): self.data = data

        i1, i2, i3, i4 = Info(1), Info(2), Info(2), Info(5)
        l = [i1, i2, i3, i4]

        self.assertIs(find_first(l, lambda i: i.data == 1), i1)
        self.assertIs(find_first(l, lambda i: i.data == 2), i2)
        self.assertIs(find_first(l, lambda i: i.data == 5), i4)

        self.assertIsNone(find_first(l, lambda i: i.data == 12, None))
        self.assertRaises(IndexError, find_first, l, lambda i: i.data == 12)

    def test_split_filter(self):
        ok, ko = split_filter((lambda x: x % 2), xrange(5))
        self.assertEqual([1, 3], ok)
        self.assertEqual([0, 2, 4], ko)

        ok, ko = split_filter((lambda x: 'k' in x), ['Naruto', 'Sasuke', 'Sakura', 'Kakashi'])
        self.assertEqual(['Sasuke', 'Sakura', 'Kakashi'], ok)
        self.assertEqual(['Naruto'], ko)

    def test_truncate_str_01(self):
        s = string.letters #Assuming len(s) == 52
        self.assertEqual(50, len(truncate_str(s, 50)))
        self.assertEqual(s[:-2], truncate_str(s, 50))

        expected = s[:-5] + "012"
        self.assertEqual(expected, truncate_str(s, 50, suffix="012"))

        self.assertEqual("",      truncate_str("",        0, suffix="01234"))
        self.assertEqual("01234", truncate_str("abcdef",  5, suffix="01234"))
        self.assertEqual("abc",   truncate_str("abcdef",  3, suffix=""))
        self.assertEqual("",      truncate_str("abcdef", -1, suffix=""))
        self.assertEqual("",      truncate_str("abcdef", -1, suffix="aaaaaa"))
        self.assertEqual("a",     truncate_str("b",       1, suffix="a"))

    def test_create_if_needed01(self):
        title = 'Mister'
        pk = 1024
        self.assertFalse(Civility.objects.filter(pk=pk).exists())

        civ = create_if_needed(Civility, {'pk': pk}, title=title)
        self.assertIsInstance(civ, Civility)
        self.assertEqual(pk,       civ.pk)
        self.assertEqual(title,    civ.title)

        civ = self.get_object_or_fail(Civility, pk=pk) #Check has been saved

        self.assertEqual(title, civ.title)

        civ = create_if_needed(Civility, {'pk': pk}, title=title + '2')
        self.assertEqual(title, civ.title)

    def test_create_if_needed02(self):
        self.login()
        user = self.user
        url = '/foo/bar'
        label = 'Oh yeah'
        order = 3
        pmi = create_if_needed(PreferedMenuItem, {'user': user, 'url': url}, label=label, order=order)

        self.assertIsInstance(pmi, PreferedMenuItem)
        self.assertEqual(user,   pmi.user)
        self.assertEqual(url,    pmi.url)
        self.assertEqual(label,  pmi.label)
        self.assertEqual(order,  pmi.order)

        pmi = self.get_object_or_fail(PreferedMenuItem, pk=pmi.pk) #Check has been saved

        self.assertEqual(label,  pmi.label)
        self.assertEqual(order,  pmi.order)

        pmi = create_if_needed(PreferedMenuItem, {'user': user, 'url': url}, label=label + ' new', order=order + 2)
        self.assertEqual(label,  pmi.label)
        self.assertEqual(order,  pmi.order)

    def test_update_model_instance01(self):
        self.login()

        first_name = 'punpun'
        last_name = 'punpunyama'
        pupun = Contact.objects.create(user=self.user, first_name=first_name, last_name=last_name)

        first_name = first_name.title()

        update_model_instance(pupun, first_name=first_name)
        self.assertEqual(first_name, self.refresh(pupun).first_name)

        with self.assertNumQueries(0):
            update_model_instance(pupun, last_name=last_name)

        self.assertRaises(AttributeError, update_model_instance,
                          pupun, first_name=first_name, unknown_field='??'
                         )

    def test_update_model_instance02(self):
        self.login()

        first_name = 'punpun'
        last_name = 'punpunyama'
        pupun = Contact.objects.create(user=self.user, first_name=first_name, last_name=last_name)

        first_name = first_name.title()
        last_name = last_name.title()
        update_model_instance(pupun, first_name=first_name, last_name=last_name)

        pupun = self.refresh(pupun)
        self.assertEqual(first_name, pupun.first_name)
        self.assertEqual(last_name,  pupun.last_name)

        with self.assertNumQueries(0):
            update_model_instance(pupun, first_name=first_name, last_name=last_name)

    def test_get_from_request_or_404(self):
        request = {'name': 'robert', 'age': '36'}

        self.assertRaises(Http404, get_from_GET_or_404, request, 'name_') # key error
        self.assertRaises(Http404, get_from_GET_or_404, request, 'name', int) # cast error
        self.assertRaises(Http404, get_from_GET_or_404, request, 'name_', int, default='string') #cast error

        self.assertEqual('36', get_from_POST_or_404(request, 'age'))
        self.assertEqual(36, get_from_POST_or_404(request, 'age', int))
        self.assertEqual(1,  get_from_POST_or_404(request, 'name_', int, default=1))

    def test_safe_unicode(self):
        self.assertEqual(u"kjøÔ€ôþâ", safe_unicode(u"kjøÔ€ôþâ"))
        self.assertEqual(u"aé‡ae15", safe_unicode("a\xe9\x87ae15"))
        self.assertEqual(u"aé‡ae15", safe_unicode("aé‡ae15"))

        # custom encoding list
        self.assertEqual(u"a\ufffdae15", safe_unicode("a\xe9\x87ae15", ('utf-8',)))
        self.assertEqual(u"aé‡ae15", safe_unicode("a\xe9\x87ae15", ('cp1252',)))

    def test_safe_unicode_object(self):
        class no_unicode_object(object):
            pass

        class unicode_object(object):
            def __unicode__(self):
                return u"aé‡ae15"

        class false_unicode_object(object):
            def __init__(self, text):
                self.text = text;

            def __unicode__(self):
                return self.text

        self.assertEqual(u"<class 'creme.creme_core.tests.utils.no_unicode_object'>", safe_unicode(no_unicode_object))
        self.assertEqual(u"aé‡ae15", safe_unicode(unicode_object()))
        self.assertEqual(u"aé‡ae15", safe_unicode(false_unicode_object(u"aé‡ae15")))
        self.assertEqual(u"aé‡ae15", safe_unicode(false_unicode_object("a\xe9\x87ae15")))

    def test_safe_unicode_error1(self):
        "Encoding errors"
        self.assertEqual(u"kjøÔ€ôþâ", safe_unicode_error(OSError(u"kjøÔ€ôþâ")))
        self.assertEqual(u"kjøÔ€ôþâ", safe_unicode_error(Exception(u"kjøÔ€ôþâ")))

        self.assertEqual(u"aé‡ae15", safe_unicode_error(OSError("a\xe9\x87ae15")))
        self.assertEqual(u"aé‡ae15", safe_unicode_error(Exception("a\xe9\x87ae15")))

        self.assertEqual(u"aé‡ae15", safe_unicode_error(OSError("aé‡ae15")))
        self.assertEqual(u"aé‡ae15", safe_unicode_error(Exception("aé‡ae15")))

        # custom encoding list
        self.assertEqual(u"a\ufffdae15", safe_unicode_error(OSError("a\xe9\x87ae15"), ('utf-8',)))
        self.assertEqual(u"a\ufffdae15", safe_unicode_error(Exception("a\xe9\x87ae15"), ('utf-8',)))

        self.assertEqual(u"aé‡ae15", safe_unicode_error(OSError("a\xe9\x87ae15"), ('cp1252',)))
        self.assertEqual(u"aé‡ae15", safe_unicode_error(Exception("a\xe9\x87ae15"), ('cp1252',)))

    def test_safe_unicode_error2(self):
        "'message' attribute is not a string/unicode (like ExpatError)"
        class MyAnnoyingException(Exception):
            class MyAnnoyingExceptionMsg:
                def __unicode__(self):
                    return u'My message'

            def __init__(self):
                self.message = self.MyAnnoyingExceptionMsg()

            def __unicode__(self):
                return unicode(self.message)

        self.assertEqual(u'My message', safe_unicode_error(MyAnnoyingException()))

    def test_date_2_dict(self):
        d = {'year': 2012, 'month': 6, 'day': 6}
        self.assertEqual(d, date_2_dict(date(**d)))

    def test_int_2_roman(self):
        self.assertEqual(['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
                          'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX'
                         ],
                         [int_2_roman(i) for i in xrange(1, 21)]
                        )
        self.assertEqual('MM',      int_2_roman(2000))
        self.assertEqual('MCMXCIX', int_2_roman(1999))


class DependenceSortTestCase(CremeTestCase): #TODO: SimpleTestCase
    class DepSortable(object):
        def __init__(self, name, deps=None):
            self.name = name
            self.dependencies = deps or []

        def __repr__(self):
            return self.name

        def key(self):
            return self.name

        def deps(self): 
            return self.dependencies

    def test_dependence_sort01(self):
        self.assertEqual([], dependence_sort([], lambda ds: ds.name, lambda ds: ds.dependencies))

    def test_dependence_sort02(self):
        A = self.DepSortable('A')
        B = self.DepSortable('B')
        self.assertEqual([A, B], 
                         dependence_sort([A, B], lambda ds: ds.name, lambda ds: ds.dependencies)
                        )

    def test_dependence_sort03(self):
        DS = self.DepSortable
        A = DS('A', ['B'])
        B = DS('B')
        self.assertEqual([B, A],
                         dependence_sort([A, B], DS.key, DS.deps)
                        )

    def test_dependence_sort04(self):
        DS = self.DepSortable
        A = DS('A', ['C'])
        B = DS('B')
        C = DS('C', ['B'])
        self.assertEqual([B, C, A], dependence_sort([A, B, C], DS.key, DS.deps))

    def test_dependence_sort05(self):
        DS = self.DepSortable
        A = DS('A', ['C', 'D'])
        B = DS('B')
        C = DS('C', ['B'])
        D = DS('D')
        self.assertIn(dependence_sort([A, B, C, D], DS.key, DS.deps),
                      ([B, D, C, A],
                       [B, C, D, A],
                       [D, B, C, A],
                      )
                     )

    def test_dependence_sort06(self):
        DS = self.DepSortable
        A = DS('A', ['C'])
        B = DS('B')
        C = DS('C', ['A'])

        self.assertRaises(DependenciesLoopError, dependence_sort,
                          [A, B, C], DS.key, DS.deps,
                         )

    def test_dependence_sort07(self):
        DS = self.DepSortable
        A = DS('End', ['Middle'])
        B = DS('Start')
        C = DS('Middle', ['Start'])
        self.assertEqual([B, C, A], dependence_sort([A, B, C], DS.key, DS.deps))


class DatesTestCase(CremeTestCase):
    def test_get_dt_from_iso8601_str_01(self):
        dt = get_dt_from_iso8601_str('20110522T223000Z')
        self.assertEqual(datetime(2011, 5, 22, 22, 30, 0), dt)

    def test_get_dt_to_iso8601_str_01(self):
        dt = datetime(2011, 5, 22, 22, 30, 0)
        self.assertEqual('20110522T223000Z', get_dt_to_iso8601_str(dt))

    #def test_get_naive_dt_from_tzdate_01(self):
        #dt_localized = pytz.utc.localize(datetime(2011, 5, 22, 22, 30, 0))
        #dt = get_naive_dt_from_tzdate(dt_localized)
        #self.assertEqual(datetime(2011, 5, 22, 22, 30, 0), dt)

    #def test_get_creme_dt_from_utc_dt_01(self):
        #dt_localized = pytz.utc.localize(datetime(2011, 5, 22, 22, 30, 0))
        #utc_dt = get_utc_dt_from_creme_dt(get_creme_dt_from_utc_dt(dt_localized))
        #self.assertEqual(dt_localized, utc_dt)

    def test_get_dt_from_str(self):
        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2013, month=7, day=25, hour=12, minute=28, second=45),
                         get_dt_from_str('2013-07-25 12:28:45')
                        )
        self.assertEqual(create_dt(year=2013, month=7, day=25, hour=8, utc=True),
                         get_dt_from_str('2013-07-25 11:00:00+03:00')
                        )

        DATETIME_INPUT_FORMATS = settings.DATETIME_INPUT_FORMATS

        def check(fmt, dt_str, **kwargs):
            if fmt in DATETIME_INPUT_FORMATS:
                self.assertEqual(create_dt(**kwargs), get_dt_from_str(dt_str))
            else:
                print 'DatesTestCase: skipped datetime format:', fmt

        check('%d-%m-%Y', '25/07/2013', year=2013, month=7, day=25)
        check('%Y-%m-%d', '2014-08-26', year=2014, month=8, day=26)

        check('%Y-%m-%dT%H:%M:%S.%fZ', '2013-07-25 12:28:45',
              year=2013, month=7, day=25, hour=12, minute=28, second=45
             )

    def test_get_date_from_str(self):
        DATE_INPUT_FORMATS = settings.DATE_INPUT_FORMATS

        def check(fmt, date_str, **kwargs):
            if fmt in DATE_INPUT_FORMATS:
                self.assertEqual(date(**kwargs), get_date_from_str(date_str))
            else:
                print 'DatesTestCase: skipped date format:', fmt

        check('%d-%m-%Y', '25/07/2013', year=2013, month=7, day=25)
        check('%Y-%m-%d', '2014-08-26', year=2014, month=8, day=26)


class QueriesTestCase(CremeTestCase):
    def test_get_first_or_None01(self):
        CremePropertyType.objects.create(text='Is cute', is_custom=True)
        self.assertIsInstance(get_first_or_None(CremePropertyType), CremePropertyType)

    def test_get_first_or_None02(self):
        Civility.objects.all().delete()
        self.assertIsNone(get_first_or_None(Civility))

    #TODO: test get_q_from_dict()


class UnicodeCollationTestCase(CremeTestCase):
    def test_uca01(self):
        from creme.creme_core.utils.unicode_collation import collator

        sort = partial(sorted, key=collator.sort_key)
        words = ['Caff', 'Cafe', 'Cafard', u'Café']
        self.assertEqual(['Cafard', 'Cafe', 'Caff', u'Café'], sorted(words)) # standard sort
        self.assertEqual(['Cafard', 'Cafe', u'Café', 'Caff'], sort(words))

        self.assertEqual(['La', u'Là', u'Lä', 'Las', 'Le'],
                         sort(['La', u'Là', 'Le', u'Lä', 'Las'])
                        )
        self.assertEqual(['gloves', u'ĝloves', 'hats', 'shoes'],
                         sort(['hats', 'gloves', 'shoes', u'ĝloves']),
                        )

    #def test_uca02(self):
        #"Original lib"
        #from os.path import join
        #from pyuca import Collator

        #path = join(settings.CREME_ROOT, 'creme_core', 'utils', 'allkeys.txt')
        #collator = Collator(path)
        #sort = partial(sorted, key=collator.sort_key)
        #words = ['Caff', 'Cafe', 'Cafard', u'Café']
        #self.assertEqual(['Cafard', 'Cafe', 'Caff', u'Café'], sorted(words)) # standard sort
        #self.assertEqual(['Cafard', 'Cafe', u'Café', 'Caff'], sort(words))

        #self.assertEqual(['La', u'Là', u'Lä', 'Las', 'Le'],
                         #sort(['La', u'Là', 'Le', u'Lä', 'Las'])
                        #)
        #self.assertEqual(['gloves', u'ĝloves', 'hats', 'shoes'],
                         #sort(['hats', 'gloves', 'shoes', u'ĝloves']),
                        #)

        ##test memory comsumption
        ##from time import sleep
        ##sleep(10)


class CurrencyFormatTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core')

    def test_currency(self):
        from decimal import Decimal

        from creme.creme_core.constants import DISPLAY_CURRENCY_LOCAL_SYMBOL
        from creme.creme_core.models import Currency, SettingValue
        from creme.creme_core.utils.currency_format import currency

        #sk = self.get_object_or_fail(SettingKey, pk=DISPLAY_CURRENCY_LOCAL_SYMBOL)
        #sv = self.get_object_or_fail(SettingValue, key=sk)
        sv = self.get_object_or_fail(SettingValue, key_id=DISPLAY_CURRENCY_LOCAL_SYMBOL)
        self.assertTrue(sv.value)

        result1 = currency(3)
        self.assertIsInstance(result1, basestring)
        self.assertIn('3', result1)

        result2 = currency(3, currency_or_id=None)
        self.assertEqual(result1, result2)

        result3 = currency(Decimal('3.52'))
        self.assertIn('3',  result3)
        self.assertIn('52', result3)

        my_currency = Currency.objects.all()[0]
        result4 = currency(5, currency_or_id=my_currency)
        self.assertIn('5', result4)
        self.assertIn(my_currency.local_symbol, result4)
        self.assertNotIn(my_currency.international_symbol, result4)

        sv.value = False
        sv.save()
        result5 = currency(5, currency_or_id=my_currency)
        self.assertIn('5', result5)
        self.assertIn(my_currency.international_symbol, result5)
        self.assertNotIn(my_currency.local_symbol, result5)

        result6 = currency(5, currency_or_id=my_currency.id)
        self.assertEqual(result5, result6)

        result7 = currency(-5, currency_or_id=my_currency)
        self.assertNotEqual(result6, result7)


from .chunktools import *
from .collections import *
from .date_period import *
from .date_range import *
from .meta import *
from .xml_utils import *
from .xls_utils import *
