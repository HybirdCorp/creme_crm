# -*- coding: utf-8 -*-

try:
    import string
    from datetime import datetime

    from django.http import Http404

    import pytz

    from creme_core.tests.base import CremeTestCase
    from creme_core.models import CremePropertyType, PreferedMenuItem
    from creme_core.utils import (find_first, truncate_str, create_if_needed, 
                                  get_from_GET_or_404, get_from_POST_or_404)
    from creme_core.utils.dates import(get_dt_from_iso8601_str, get_dt_to_iso8601_str,
                                       get_naive_dt_from_tzdate, get_creme_dt_from_utc_dt,
                                       get_utc_dt_from_creme_dt)
    from creme_core.utils.queries import get_first_or_None

    from persons.models import Civility
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


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

    def test_get_from_request_or_404(self):
        request = {'name': 'robert', 'age': '36'}

        self.assertRaises(Http404, get_from_GET_or_404, request, 'name_') # key error
        self.assertRaises(Http404, get_from_GET_or_404, request, 'name', int) # cast error
        self.assertRaises(Http404, get_from_GET_or_404, request, 'name_', int, default='string') #cast error

        self.assertEqual('36', get_from_POST_or_404(request, 'age'))
        self.assertEqual(36, get_from_POST_or_404(request, 'age', int))
        self.assertEqual(1,  get_from_POST_or_404(request, 'name_', int, default=1))


class DatesTestCase(CremeTestCase):
    def test_get_dt_from_iso8601_str_01(self):
        dt = get_dt_from_iso8601_str('20110522T223000Z')
        self.assertEqual(datetime(2011, 05, 22, 22, 30, 00), dt)

    def test_get_dt_to_iso8601_str_01(self):
        dt = datetime(2011, 05, 22, 22, 30, 00)
        self.assertEqual('20110522T223000Z', get_dt_to_iso8601_str(dt))

    def test_get_naive_dt_from_tzdate_01(self):
        dt_localized = pytz.utc.localize(datetime(2011, 05, 22, 22, 30, 00))
        dt = get_naive_dt_from_tzdate(dt_localized)
        self.assertEqual(datetime(2011, 05, 22, 22, 30, 00), dt)

    def test_get_creme_dt_from_utc_dt_01(self):
        dt_localized = pytz.utc.localize(datetime(2011, 05, 22, 22, 30, 00))
        utc_dt = get_utc_dt_from_creme_dt(get_creme_dt_from_utc_dt(dt_localized))
        self.assertEqual(dt_localized, utc_dt)


class QueriesTestCase(CremeTestCase):
    def test_get_first_or_None01(self):
        CremePropertyType.objects.create(text='Is cute', is_custom=True)
        self.assertIsInstance(get_first_or_None(CremePropertyType), CremePropertyType)

    def test_get_first_or_None02(self):
        Civility.objects.all().delete()
        self.assertIsNone(get_first_or_None(Civility))

    #TODO: test get_q_from_dict()


from meta import *
from chunktools import *
from date_range import *
from xml_utils import *

