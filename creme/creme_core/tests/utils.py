# -*- coding: utf-8 -*-

try:
    import string
    from datetime import datetime, date, timedelta

    import pytz

    from django.db.models import fields
    from django.utils.translation import ugettext as _
    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import CremePropertyType, CremeProperty, CremeEntity, PreferedMenuItem
    from creme_core.utils import *
    from creme_core.utils import meta, chunktools
    from creme_core.utils.date_range import date_range_registry
    from creme_core.utils.dates import(get_dt_from_iso8601_str, get_dt_from_iso8601_str, get_dt_to_iso8601_str,
                                       get_naive_dt_from_tzdate, get_creme_dt_from_utc_dt, get_utc_dt_from_creme_dt)
    from creme_core.tests.base import CremeTestCase

    from persons.models import Civility
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class MiscTestCase(CremeTestCase):
    def test_find_first(self):
        class Info(object):
            def __init__(self, data): self.data = data

        i1, i2, i3, i4 = Info(1), Info(2), Info(2), Info(5)
        l = [i1, i2, i3, i4]

        self.assert_(find_first(l, lambda i: i.data == 1) is i1)
        self.assert_(find_first(l, lambda i: i.data == 2) is i2)
        self.assert_(find_first(l, lambda i: i.data == 5) is i4)

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


class MetaTestCase(CremeTestCase):
    def test_get_field_infos(self):
        text = 'TEXT'

        user   = User.objects.create(username='name')
        ptype  = CremePropertyType.objects.create(text=text, is_custom=True)
        entity = CremeEntity.objects.create(user=user)
        prop   = CremeProperty(type=ptype, creme_entity=entity)

        self.assertEqual((fields.CharField,    text), meta.get_field_infos(prop, 'type__text'))
        self.assertEqual((fields.BooleanField, True), meta.get_field_infos(prop, 'type__is_custom'))

        self.assertEqual((None, ''), meta.get_field_infos(prop, 'foobar__is_custom'))
        self.assertEqual((None, ''), meta.get_field_infos(prop, 'type__foobar'))

        self.assertEqual(fields.CharField, meta.get_field_infos(prop, 'creme_entity__entity_type__name')[0])

    def test_get_model_field_infos(self):
        self.assertEqual([], meta.get_model_field_infos(CremeEntity, 'foobar'))
        self.assertEqual([], meta.get_model_field_infos(CremeEntity, 'foo__bar'))

        #[{'field': <django.db.models.fields.related.ForeignKey object at ...>,
        #  'model': <class 'creme_core.models.creme_property.CremePropertyType'>}]
        with self.assertNoException():
            info = meta.get_model_field_infos(CremeProperty, 'type')
            self.assertEqual(1, len(info))

            desc = info[0]
            self.assertIsInstance(desc['field'], fields.related.ForeignKey)
            self.assertEqual(CremePropertyType, desc['model'])

        #[{ 'field': <django.db.models.fields.related.ForeignKey object at ...>,
        #   'model': <class 'creme_core.models.creme_property.CremePropertyType'>},
        # {'field': <django.db.models.fields.CharField object at ...>,
        #   'model': None}]
        with self.assertNoException():
            info = meta.get_model_field_infos(CremeProperty, 'type__text')
            self.assertEqual(2, len(info))

            desc = info[0]
            self.assertIsInstance(desc['field'], fields.related.ForeignKey)
            self.assertEqual(CremePropertyType, desc['model'])

            desc = info[1]
            self.assertIsInstance(desc['field'], fields.CharField)
            self.assertIsNone(desc['model'])

        #[{'field': <django.db.models.fields.related.ForeignKey object at 0x9d123ec>,
        #  'model': <class 'creme_core.models.entity.CremeEntity'>},
        # {'field': <django.db.models.fields.related.ForeignKey object at 0x9d0378c>,
        #  'model': <class 'django.contrib.contenttypes.models.ContentType'>},
        # {'field': <django.db.models.fields.CharField object at 0x99d302c>,
        #  'model': None}]
        with self.assertNoException():
            info = meta.get_model_field_infos(CremeProperty, 'creme_entity__entity_type__name')
            self.assertEqual(3, len(info))

            desc = info[0]
            self.assertIsInstance(desc['field'], fields.related.ForeignKey)
            self.assertEqual(CremeEntity, desc['model'])

            desc = info[1]
            self.assertIsInstance(desc['field'], fields.related.ForeignKey)
            self.assertEqual(ContentType, desc['model'])

            desc = info[2]
            self.assertIsInstance(desc['field'], fields.CharField)
            self.assertIsNone(desc['model'])

    def test_get_date_fields(self):
        entity = CremeEntity()
        get_field = entity._meta.get_field
        self.assertTrue(meta.is_date_field(get_field('created')))
        self.assertFalse(meta.is_date_field(get_field('user')))

        datefields = meta.get_date_fields(entity)
        self.assertEqual(2, len(datefields))
        self.assertEqual(set(('created', 'modified')), set(f.name for f in datefields))

    #TODO: test get_flds_with_fk_flds etc...


class ChunkToolsTestCase(CremeTestCase):
    data = """04 05 99 66 54
055 6 5322 1 2

98

    456456 455 12
        45 156
dfdsfds
s556"""

    def assert_entries(self, entries):
        self.assertEqual(6, len(entries))
        self.assertEqual('0405996654',  entries[0])
        self.assertEqual('0556532212',  entries[1])
        self.assertEqual('98',          entries[2])
        self.assertEqual('45645645512', entries[3])
        self.assertEqual('45156',       entries[4])
        self.assertEqual('556',         entries[5])

    def chunks(self, chunk_size):
        for chunk in chunktools.iter_as_chunk(self.data, chunk_size):
            yield ''.join(chunk)

    @staticmethod
    def filter(entry):
        return ''.join(char for char in entry if char.isdigit())

    def test_iter_as_slices01(self):
        chunks = list(chunktools.iter_as_slices(self.data, 1000))

        self.assertEqual(1, len(chunks))
        self.assertEqual(self.data, ''.join(chunks))

    def test_iter_as_slices02(self):
        assert len(self.data) % 5 == 0
        chunks = list(chunktools.iter_as_slices(self.data, 5))

        self.assertEqual(16, len(chunks))

        for i, chunk in enumerate(chunks):
            self.assertEqual(5, len(chunk), 'Bad size for chunk %i : %s' % (i, chunk))

        self.assertEqual(self.data, ''.join(chunks))

    def test_iter_as_slices03(self):
        data = self.data + '9'
        assert len(data) % 5 == 1
        chunks = list(chunktools.iter_as_slices(data, 5))

        self.assertEqual(17, len(chunks))

        for i, chunk in enumerate(chunks[:-1]):
            self.assertEqual(5, len(chunk), 'Bad size for chunk %i : %s' % (i, chunk))

        self.assertEqual('9', chunks[-1])

        self.assertEqual(data, ''.join(chunks))

    def test_iter_as_chunks01(self):
        chunks = list(chunktools.iter_as_chunk(self.data, 1000))
        self.assertEqual(1, len(chunks))
        self.assertEqual(self.data, ''.join(chunks[0]))

    def test_iter_as_chunks02(self):
        assert len(self.data) % 5 == 0
        chunks = list(chunktools.iter_as_chunk(self.data, 5))

        self.assertEqual(16, len(chunks))

        for i, chunk in enumerate(chunks):
            self.assertEqual(5, len(chunk), 'Bad size for chunk %i : %s' % (i, chunk))
            self.assertIsInstance(chunk, list)

        self.assertEqual(self.data, ''.join(''.join(chunk) for chunk in chunks))

    def test_iter_as_chunks03(self):
        data = self.data + '9'
        assert len(data) % 5 == 1
        chunks = list(chunktools.iter_as_chunk(data, 5))

        self.assertEqual(17, len(chunks))

        for i, chunk in enumerate(chunks[:-1]):
            self.assertEqual(5, len(chunk), 'Bad size for chunk %i : %s' % (i, chunk))

        self.assertEqual(['9'], chunks[-1])

        self.assertEqual(data, ''.join(''.join(chunk) for chunk in chunks))

    def test_iter_splitchunks01(self):
        #Tests small_chunks
        chunk_size = 5
        entries = list(chunktools.iter_splitchunks(self.chunks(chunk_size), '\n', ChunkToolsTestCase.filter))

        self.assert_entries(entries)

    def test_iter_splitchunks02(self):
        #Test big_chunks
        chunk_size = len(self.data) / 2
        entries = list(chunktools.iter_splitchunks(self.chunks(chunk_size), '\n', ChunkToolsTestCase.filter))

        self.assert_entries(entries)

    def test_iter_splitchunks03(self):
        #Test with one chunk
        chunk_size = len(self.data) * 2
        entries = list(chunktools.iter_splitchunks(self.chunks(chunk_size), '\n', ChunkToolsTestCase.filter))

        self.assert_entries(entries)


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


class DateRangeTestCase(CremeTestCase):
    def test_future(self):
        date_range = date_range_registry.get_range('in_future')
        self.assertIsNotNone(date_range)
        self.assertEqual(_(u"In the future"), unicode(date_range.verbose_name))

        now = datetime.now()
        self.assertEqual({'birthday__gte': now},
                         date_range.get_q_dict(field='birthday', now=now)
                        )

    def test_past(self):
        now = datetime.now()
        date_range = date_range_registry.get_range(name='in_past')
        self.assertIsNotNone(date_range)
        self.assertEqual({'created__lte': now},
                         date_range.get_q_dict(field='created', now=now)
                        )

    def test_custom_start01(self):
        now = date(year=2011, month=6, day=1)
        date_range = date_range_registry.get_range(start=now)
        self.assertIsNotNone(date_range)
        self.assertEqual({'created__gte': datetime(year=2011, month=6, day=1, hour=0, minute=0, second=0)},
                         date_range.get_q_dict(field='created', now=datetime.now())
                        )

    def test_custom_start02(self):
        now = datetime(year=2011, month=6, day=1, hour=12, minute=36, second=12)
        date_range = date_range_registry.get_range(start=now)
        self.assertIsNotNone(date_range)
        self.assertEqual({'created__gte': datetime(year=2011, month=6, day=1, hour=12, minute=36, second=12)},
                         date_range.get_q_dict(field='created', now=datetime.now())
                        )

    def test_custom_end01(self):
        now = date(year=2012, month=7, day=15)
        date_range = date_range_registry.get_range(end=now)
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__lte': datetime(year=2012, month=7, day=15, hour=23, minute=59, second=59)},
                         date_range.get_q_dict(field='modified', now=datetime.now())
                        )

    def test_custom_end02(self):
        now = datetime(year=2012, month=7, day=15, hour=10, minute=21, second=50)
        date_range = date_range_registry.get_range(end=now)
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__lte': datetime(year=2012, month=7, day=15, hour=10, minute=21, second=50)},
                         date_range.get_q_dict(field='modified', now=datetime.now())
                        )

    def test_custom_range01(self):
        today    = date(year=2011, month=8, day=2)
        tomorrow = date(year=2011, month=8, day=3)
        date_range = date_range_registry.get_range(start=today, end=tomorrow)
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2011, month=8, day=2, hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=8, day=3, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=datetime.now())
                        )

    def test_previous_year(self):
        today = datetime(year=2011, month=4, day=24)
        date_range = date_range_registry.get_range(name='previous_year')
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2010, month=1,  day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2010, month=12, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=today)
                        )

    def test_current_year(self):
        today = datetime(year=2011, month=4, day=24)
        date_range = date_range_registry.get_range(name='current_year')
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2011, month=1,  day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=12, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=today)
                        )

    def test_next_year(self):
        today = datetime(year=2011, month=4, day=24)
        date_range = date_range_registry.get_range(name='next_year')
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2012, month=1,  day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2012, month=12, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=today)
                        )

    def test_previous_month01(self):
        today = datetime(year=2011, month=4, day=24)
        date_range = date_range_registry.get_range(name='previous_month')
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2011, month=3, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=3, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=today)
                        )

    def test_previous_month02(self):
        today = datetime(year=2011, month=3, day=12)
        self.assertEqual({'modified__range': (datetime(year=2011, month=2, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=2, day=28, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='previous_month')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_previous_month03(self):
        today = datetime(year=2011, month=1, day=12)
        self.assertEqual({'modified__range': (datetime(year=2010, month=12, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2010, month=12, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='previous_month')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_current_month01(self):
        today = datetime(year=2011, month=1, day=15)
        date_range = date_range_registry.get_range(name='current_month')
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2011, month=1, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=1, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=today)
                        )

    def test_current_month02(self):
        today = datetime(year=2011, month=2, day=15)
        self.assertEqual({'modified__range': (datetime(year=2011, month=2, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=2, day=28, hour=23, minute=59, second=59) #<--28
                                             )
                         },
                         date_range_registry.get_range(name='current_month')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_current_month03(self):
        today = datetime(year=2012, month=2, day=15)
        self.assertEqual({'modified__range': (datetime(year=2012, month=2, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2012, month=2, day=29, hour=23, minute=59, second=59) #<--29
                                             )
                         },
                         date_range_registry.get_range(name='current_month')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_next_month01(self):
        today = datetime(year=2011, month=10, day=20)
        date_range = date_range_registry.get_range(name='next_month')
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2011, month=11, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=11, day=30, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=today)
                        )

    def test_next_month02(self):
        today = datetime(year=2011, month=11, day=21)
        self.assertEqual({'modified__range': (datetime(year=2011, month=12, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=12, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='next_month')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_next_month03(self):
        today = datetime(year=2011, month=12, day=23)
        self.assertEqual({'modified__range': (datetime(year=2012, month=1, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2012, month=1, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='next_month')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_previous_quarter01(self):
        today = datetime(year=2011, month=4, day=24)
        date_range = date_range_registry.get_range(name='previous_quarter')
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2011, month=1, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=3, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=today)
                        )

    def test_previous_quarter02(self):
        today = datetime(year=2011, month=6, day=12)
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2011, month=1, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=3, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='previous_quarter')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_previous_quarter03(self):
        today = datetime(year=2011, month=2, day=8)
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2010, month=10, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2010, month=12, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='previous_quarter')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_current_quarter01(self):
        today = datetime(year=2011, month=7, day=21)
        date_range = date_range_registry.get_range(name='current_quarter')
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2011, month=7, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=9, day=30, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=today)
                        )

    def test_next_quarter01(self):
        today = datetime(year=2011, month=4, day=21)
        date_range = date_range_registry.get_range(name='next_quarter')
        self.assertIsNotNone(date_range)
        self.assertEqual({'modified__range': (datetime(year=2011, month=7, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=9, day=30, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range.get_q_dict(field='modified', now=today)
                        )

    def test_next_quarter02(self):
        today = datetime(year=2011, month=12, day=3)
        self.assertEqual({'modified__range': (datetime(year=2012, month=1, day=1,  hour=0,  minute=0,  second=0),
                                              datetime(year=2012, month=3, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='next_quarter')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_yesterday01(self):
        today = datetime(year=2011, month=6, day=1, hour=14, minute=14, second=37)
        self.assertEqual({'modified__range': (datetime(year=2011, month=5, day=31, hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=5, day=31, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='yesterday')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_yesterday02(self):
        today = datetime(year=2011, month=6, day=2, hour=14, minute=14, second=37)
        self.assertEqual({'modified__range': (datetime(year=2011, month=6, day=1, hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=6, day=1, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='yesterday')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_today(self):
        today = datetime(year=2011, month=6, day=1, hour=14, minute=14, second=37)
        self.assertEqual({'modified__range': (datetime(year=2011, month=6, day=1, hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=6, day=1, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='today')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_tomorrow01(self):
        today = datetime(year=2011, month=6, day=1, hour=14, minute=14, second=37)
        self.assertEqual({'modified__range': (datetime(year=2011, month=6, day=2, hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=6, day=2, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='tomorrow')\
                                            .get_q_dict(field='modified', now=today)
                        )

    def test_tomorrow02(self):
        today = datetime(year=2011, month=6, day=30, hour=14, minute=14, second=37)
        self.assertEqual({'modified__range': (datetime(year=2011, month=7, day=1, hour=0,  minute=0,  second=0),
                                              datetime(year=2011, month=7, day=1, hour=23, minute=59, second=59)
                                             )
                         },
                         date_range_registry.get_range(name='tomorrow')\
                                            .get_q_dict(field='modified', now=today)
                        )
