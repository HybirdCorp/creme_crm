# -*- coding: utf-8 -*-

from datetime import date, timedelta

from django.db.models import fields
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core import models
from creme_core.utils import *
from creme_core.utils import meta, chunktools
from creme_core.utils.date_range import date_range_registry
#from creme_core.utils.date import date_range_registry
from creme_core.tests.base import CremeTestCase


class MiscTestCase(CremeTestCase):
    def test_find_first(self):
        class Info(object):
            def __init__(self, data): self.data = data

        i1, i2, i3, i4 = Info(1), Info(2), Info(2), Info(5)
        l = [i1, i2, i3, i4]

        self.assert_(find_first(l, lambda i: i.data == 1) is i1)
        self.assert_(find_first(l, lambda i: i.data == 2) is i2)
        self.assert_(find_first(l, lambda i: i.data == 5) is i4)

        self.assert_(find_first(l, lambda i: i.data == 12, None) is None)
        self.assertRaises(IndexError, find_first, l, lambda i: i.data == 12)


class MetaTestCase(CremeTestCase):
    def test_get_field_infos(self):
        text = 'TEXT'

        user   = User.objects.create(username='name')
        ptype  = models.CremePropertyType.objects.create(text=text, is_custom=True)
        entity = models.CremeEntity.objects.create(user=user)
        prop   = models.CremeProperty(type=ptype, creme_entity=entity)

        self.assertEqual((fields.CharField,    text), meta.get_field_infos(prop, 'type__text'))
        self.assertEqual((fields.BooleanField, True), meta.get_field_infos(prop, 'type__is_custom'))

        self.assertEqual((None, ''), meta.get_field_infos(prop, 'foobar__is_custom'))
        self.assertEqual((None, ''), meta.get_field_infos(prop, 'type__foobar'))

        self.assertEqual(fields.CharField, meta.get_field_infos(prop, 'creme_entity__entity_type__name')[0])

    def test_get_model_field_infos(self):
        self.assertEqual([], meta.get_model_field_infos(models.CremeEntity, 'foobar'))
        self.assertEqual([], meta.get_model_field_infos(models.CremeEntity, 'foo__bar'))

        #[{'field': <django.db.models.fields.related.ForeignKey object at ...>,
        #  'model': <class 'creme_core.models.creme_property.CremePropertyType'>}]
        try:
            info = meta.get_model_field_infos(models.CremeProperty, 'type')
            self.assertEqual(1, len(info))

            desc = info[0]
            self.assert_(isinstance(desc['field'], fields.related.ForeignKey))
            self.assertEqual(models.CremePropertyType, desc['model'])
        except Exception, e:
            self.fail(str(e))

        #[{ 'field': <django.db.models.fields.related.ForeignKey object at ...>,
        #   'model': <class 'creme_core.models.creme_property.CremePropertyType'>},
        # {'field': <django.db.models.fields.CharField object at ...>,
        #   'model': None}]
        try:
            info = meta.get_model_field_infos(models.CremeProperty, 'type__text')
            self.assertEqual(2, len(info))

            desc = info[0]
            self.assert_(isinstance(desc['field'], fields.related.ForeignKey))
            self.assertEqual(models.CremePropertyType, desc['model'])

            desc = info[1]
            self.assert_(isinstance(desc['field'], fields.CharField))
            self.assert_(desc['model'] is None)
        except Exception, e:
            self.fail(str(e))

        #[{'field': <django.db.models.fields.related.ForeignKey object at 0x9d123ec>,
        #  'model': <class 'creme_core.models.entity.CremeEntity'>},
        # {'field': <django.db.models.fields.related.ForeignKey object at 0x9d0378c>,
        #  'model': <class 'django.contrib.contenttypes.models.ContentType'>},
        # {'field': <django.db.models.fields.CharField object at 0x99d302c>,
        #  'model': None}]
        try:
            info = meta.get_model_field_infos(models.CremeProperty, 'creme_entity__entity_type__name')
            self.assertEqual(3, len(info))

            desc = info[0]
            self.assert_(isinstance(desc['field'], fields.related.ForeignKey))
            self.assertEqual(models.CremeEntity, desc['model'])

            desc = info[1]
            self.assert_(isinstance(desc['field'], fields.related.ForeignKey))
            self.assertEqual(ContentType, desc['model'])

            desc = info[2]
            self.assert_(isinstance(desc['field'], fields.CharField))
            self.assert_(desc['model'] is None)
        except Exception, e:
            self.fail(str(e))

    def test_get_date_fields(self):
        entity = models.CremeEntity()
        get_field = entity._meta.get_field
        self.assert_(meta.is_date_field(get_field('created')))
        self.failIf(meta.is_date_field(get_field('user')))

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
            self.assert_(isinstance(chunk, list))

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


class DateRangeTestCase(CremeTestCase):
    def test_future(self):
        date_range = date_range_registry.get_range('in_future')
        self.assert_(date_range is not None)
        self.assertEqual(_(u"In the future"), unicode(date_range.verbose_name))

        today = date.today()
        self.assertEqual({'birthday__gte': today},
                         date_range.get_q_dict(field='birthday', today=today)
                        )

    def test_past(self):
        today = date.today()
        date_range = date_range_registry.get_range(name='in_past')
        self.assert_(date_range is not None)
        self.assertEqual({'created__lte': today},
                         date_range.get_q_dict(field='created', today=today)
                        )

    def test_custom_start(self):
        today = date.today()
        date_range = date_range_registry.get_range(start=today)
        self.assert_(date_range is not None)
        self.assertEqual({'created__gte': today},
                         date_range.get_q_dict(field='created', today=today)
                        )

    def test_custom_end(self):
        today = date.today()
        date_range = date_range_registry.get_range(end=today)
        self.assert_(date_range is not None)
        self.assertEqual({'modified__lte': today},
                         date_range.get_q_dict(field='modified', today=today)
                        )

    def test_custom_range(self):
        today = date.today()
        tomorrow = today + timedelta(days=1)
        date_range = date_range_registry.get_range(start=today, end=tomorrow)
        self.assert_(date_range is not None)
        self.assertEqual({'modified__range': (today, tomorrow)},
                         date_range.get_q_dict(field='modified', today=today)
                        )

    def test_previous_year(self):
        today = date(year=2011, month=4, day=24)
        date_range = date_range_registry.get_range(name='previous_year')
        self.assert_(date_range is not None)
        self.assertEqual({'modified__range': (date(year=2010, month=1,  day=1),
                                              date(year=2010, month=12, day=31)
                                             )
                         },
                         date_range.get_q_dict(field='modified', today=today)
                        )

    def test_current_year(self):
        today = date(year=2011, month=4, day=24)
        date_range = date_range_registry.get_range(name='current_year')
        self.assert_(date_range is not None)
        self.assertEqual({'modified__range': (date(year=2011, month=1,  day=1),
                                              date(year=2011, month=12, day=31)
                                             )
                         },
                         date_range.get_q_dict(field='modified', today=today)
                        )

    def test_next_year(self):
        today = date(year=2011, month=4, day=24)
        date_range = date_range_registry.get_range(name='next_year')
        self.assert_(date_range is not None)
        self.assertEqual({'modified__range': (date(year=2012, month=1,  day=1),
                                              date(year=2012, month=12, day=31)
                                             )
                         },
                         date_range.get_q_dict(field='modified', today=today)
                        )

    def test_previous_month01(self):
        today = date(year=2011, month=4, day=24)
        date_range = date_range_registry.get_range(name='previous_month')
        self.assert_(date_range is not None)
        self.assertEqual({'modified__range': (date(year=2011, month=3, day=1),
                                              date(year=2011, month=3, day=31)
                                             )
                         },
                         date_range.get_q_dict(field='modified', today=today)
                        )

    def test_previous_month02(self):
        today = date(year=2011, month=3, day=12)
        self.assertEqual({'modified__range': (date(year=2011, month=2, day=1),
                                              date(year=2011, month=2, day=28)
                                             )
                         },
                         date_range_registry.get_range(name='previous_month')\
                                            .get_q_dict(field='modified', today=today)
                        )

    def test_previous_month03(self):
        today = date(year=2011, month=1, day=12)
        self.assertEqual({'modified__range': (date(year=2010, month=12, day=1),
                                              date(year=2010, month=12, day=31)
                                             )
                         },
                         date_range_registry.get_range(name='previous_month')\
                                            .get_q_dict(field='modified', today=today)
                        )

    def test_current_month01(self):
        today = date(year=2011, month=1, day=15)
        date_range = date_range_registry.get_range(name='current_month')
        self.assert_(date_range is not None)
        self.assertEqual({'modified__range': (date(year=2011, month=1, day=1),
                                              date(year=2011, month=1, day=31)
                                             )
                         },
                         date_range.get_q_dict(field='modified', today=today)
                        )

    def test_current_month02(self):
        today = date(year=2011, month=2, day=15)
        self.assertEqual({'modified__range': (date(year=2011, month=2, day=1),
                                              date(year=2011, month=2, day=28) #<--28
                                             )
                         },
                         date_range_registry.get_range(name='current_month')\
                                            .get_q_dict(field='modified', today=today)
                        )

    def test_current_month03(self):
        today = date(year=2012, month=2, day=15)
        self.assertEqual({'modified__range': (date(year=2012, month=2, day=1),
                                              date(year=2012, month=2, day=29) #<--29
                                             )
                         },
                         date_range_registry.get_range(name='current_month')\
                                            .get_q_dict(field='modified', today=today)
                        )

    def test_next_month01(self):
        today = date(year=2011, month=10, day=20)
        date_range = date_range_registry.get_range(name='next_month')
        self.assert_(date_range is not None)
        self.assertEqual({'modified__range': (date(year=2011, month=11, day=1),
                                              date(year=2011, month=11, day=30)
                                             )
                         },
                         date_range.get_q_dict(field='modified', today=today)
                        )

    def test_next_month02(self):
        today = date(year=2011, month=11, day=21)
        self.assertEqual({'modified__range': (date(year=2011, month=12, day=1),
                                              date(year=2011, month=12, day=31)
                                             )
                         },
                         date_range_registry.get_range(name='next_month')\
                                            .get_q_dict(field='modified', today=today)
                        )

    def test_next_month03(self):
        today = date(year=2011, month=12, day=23)
        self.assertEqual({'modified__range': (date(year=2012, month=1, day=1),
                                              date(year=2012, month=1, day=31)
                                             )
                         },
                         date_range_registry.get_range(name='next_month')\
                                            .get_q_dict(field='modified', today=today)
                        )

    def test_previous_quarter01(self):
        today = date(year=2011, month=4, day=24)
        date_range = date_range_registry.get_range(name='previous_quarter')
        self.assert_(date_range is not None)
        self.assertEqual({'modified__range': (date(year=2011, month=1, day=1),
                                              date(year=2011, month=3, day=31)
                                             )
                         },
                         date_range.get_q_dict(field='modified', today=today)
                        )

    def test_previous_quarter02(self):
        today = date(year=2011, month=6, day=12)
        self.assert_(date_range is not None)
        self.assertEqual({'modified__range': (date(year=2011, month=1, day=1),
                                              date(year=2011, month=3, day=31)
                                             )
                         },
                         date_range_registry.get_range(name='previous_quarter')\
                                            .get_q_dict(field='modified', today=today)
                        )

    def test_previous_quarter03(self):
        today = date(year=2011, month=2, day=8)
        self.assert_(date_range is not None)
        self.assertEqual({'modified__range': (date(year=2010, month=10, day=1),
                                              date(year=2010, month=12, day=31)
                                             )
                         },
                         date_range_registry.get_range(name='previous_quarter')\
                                            .get_q_dict(field='modified', today=today)
                        )

    def test_current_quarter01(self):
        today = date(year=2011, month=7, day=21)
        date_range = date_range_registry.get_range(name='current_quarter')
        self.assert_(date_range is not None)
        self.assertEqual({'modified__range': (date(year=2011, month=7, day=1),
                                              date(year=2011, month=9, day=30)
                                             )
                         },
                         date_range.get_q_dict(field='modified', today=today)
                        )

    def test_next_quarter01(self):
        today = date(year=2011, month=4, day=21)
        date_range = date_range_registry.get_range(name='next_quarter')
        self.assert_(date_range is not None)
        self.assertEqual({'modified__range': (date(year=2011, month=7, day=1),
                                              date(year=2011, month=9, day=30)
                                             )
                         },
                         date_range.get_q_dict(field='modified', today=today)
                        )

    def test_next_quarter02(self):
        today = date(year=2011, month=12, day=3)
        self.assertEqual({'modified__range': (date(year=2012, month=1, day=1),
                                              date(year=2012, month=3, day=31)
                                             )
                         },
                         date_range_registry.get_range(name='next_quarter')\
                                            .get_q_dict(field='modified', today=today)
                        )
