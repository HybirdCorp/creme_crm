# -*- coding: utf-8 -*-

try:
    import string
    from datetime import datetime, date, timedelta
    from xml.etree.ElementTree import XML

    import pytz

    from django.db.models import fields
    from django.utils.translation import ugettext as _
    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import CremePropertyType, CremeProperty, CremeEntity, PreferedMenuItem
    from creme_core.utils import *
    from creme_core.utils import meta, chunktools
    from creme_core.utils.date_range import date_range_registry
    from creme_core.utils.dates import(get_dt_from_iso8601_str, get_dt_to_iso8601_str,
                                       get_naive_dt_from_tzdate, get_creme_dt_from_utc_dt, get_utc_dt_from_creme_dt)
    from creme_core.utils.queries import get_first_or_None
    from creme_core.utils.xml_utils import _element_iterator, xml_diff
    from creme_core.tests.base import CremeTestCase

    from persons.models import Civility, Contact

    from tickets.models import Ticket
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


class MetaTestCase(CremeTestCase):
    def test_get_instance_field_info(self):
        text = 'TEXT'

        user   = User.objects.create(username='name')
        ptype  = CremePropertyType.objects.create(text=text, is_custom=True)
        entity = CremeEntity.objects.create(user=user)
        prop   = CremeProperty(type=ptype, creme_entity=entity)

        self.assertEqual((fields.CharField,    text), meta.get_instance_field_info(prop, 'type__text'))
        self.assertEqual((fields.BooleanField, True), meta.get_instance_field_info(prop, 'type__is_custom'))

        self.assertEqual((None, ''), meta.get_instance_field_info(prop, 'foobar__is_custom'))
        self.assertEqual((None, ''), meta.get_instance_field_info(prop, 'type__foobar'))

        self.assertEqual(fields.CharField, meta.get_instance_field_info(prop, 'creme_entity__entity_type__name')[0])

    def test_get_model_field_info(self):
        self.assertEqual([], meta.get_model_field_info(CremeEntity, 'foobar'))
        self.assertEqual([], meta.get_model_field_info(CremeEntity, 'foo__bar'))

        #[{'field': <django.db.models.fields.related.ForeignKey object at ...>,
        #  'model': <class 'creme_core.models.creme_property.CremePropertyType'>}]
        with self.assertNoException():
            info = meta.get_model_field_info(CremeProperty, 'type')
            self.assertEqual(1, len(info))

            desc = info[0]
            self.assertIsInstance(desc['field'], fields.related.ForeignKey)
            self.assertEqual(CremePropertyType, desc['model'])

        #[{ 'field': <django.db.models.fields.related.ForeignKey object at ...>,
        #   'model': <class 'creme_core.models.creme_property.CremePropertyType'>},
        # {'field': <django.db.models.fields.CharField object at ...>,
        #   'model': None}]
        with self.assertNoException():
            info = meta.get_model_field_info(CremeProperty, 'type__text')
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
            info = meta.get_model_field_info(CremeProperty, 'creme_entity__entity_type__name')
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

    def test_field_enumerator01(self):
        expected = [('id',                         'ID'),
                    ('created',                    _('Creation date')),
                    ('modified',                   _('Last modification')),
                    #('entity_type',                'entity type'),
                    ('header_filter_search_field', 'header filter search field'),
                    ('is_deleted',                 'is deleted'),
                    ('is_actived',                 'is actived'),
                    #('user',                       _('User')),
                   ]
        choices = meta.ModelFieldEnumerator(CremeEntity).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(CremeEntity, only_leafs=True).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(CremeEntity, only_leafs=False).choices()
        self.assertEqual([('id',                         'ID'),
                          ('created',                    _('Creation date')),
                          ('modified',                   _('Last modification')),
                          ('entity_type',                'entity type'),
                          ('header_filter_search_field', 'header filter search field'),
                          ('is_deleted',                 'is deleted'),
                          ('is_actived',                 'is actived'),
                          ('user',                       _('User')),
                         ],
                         choices, choices
                        )

    def test_field_enumerator02(self): #filter, exclude (simple)
        expected = [('created',  _('Creation date')),
                    ('modified', _('Last modification')),
                    #('user',     _('User'))
                   ]
        choices = meta.ModelFieldEnumerator(CremeEntity).filter(viewable=True).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(CremeEntity).exclude(viewable=False).choices()
        self.assertEqual(expected, choices, choices)

        expected = [('created',  _('Creation date')),
                    ('modified', _('Last modification')),
                    ('user',     _('User'))
                   ]
        choices = meta.ModelFieldEnumerator(CremeEntity, only_leafs=False).filter(viewable=True).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(CremeEntity, only_leafs=False).exclude(viewable=False).choices()
        self.assertEqual(expected, choices, choices)

    def test_field_enumerator03(self): #deep = 1
        fs = u'[%s] - %%s' % _('User')
        expected = [('created',          _('Creation date')),
                    ('modified',         _('Last modification')),
                    #('user',             _('User')),
                    ('user__username',   fs % _('username')),
                    ('user__first_name', fs % _('first name')),
                    ('user__last_name',  fs % _('last name')),
                    ('user__email',      fs % _('e-mail address')),
                    #('user__role',       fs % _('Role')),
                    ('user__is_team',    fs % _('Is a team ?')),
                   ]
        self.assertEqual(expected, meta.ModelFieldEnumerator(CremeEntity, deep=1).filter(viewable=True).choices())
        self.assertEqual(expected, meta.ModelFieldEnumerator(CremeEntity, deep=1, only_leafs=True).filter(viewable=True).choices())
        self.assertEqual(meta.ModelFieldEnumerator(CremeEntity, deep=1, only_leafs=False).filter(viewable=True).choices(),
                         [('created',          _('Creation date')),
                          ('modified',         _('Last modification')),
                          ('user',             _('User')),
                          ('user__username',   fs % _('username')),
                          ('user__first_name', fs % _('first name')),
                          ('user__last_name',  fs % _('last name')),
                          ('user__email',      fs % _('e-mail address')),
                          ('user__role',       fs % _('Role')),
                          ('user__is_team',    fs % _('Is a team ?')),
                         ]
                        )

    def test_field_enumerator04(self): #filter with function, exclude
        self.assertEqual(meta.ModelFieldEnumerator(CremeEntity, deep=1).filter(lambda f: f.name.endswith('ied'), viewable=True).choices(),
                         [('modified', _('Last modification'))]
                        )
        self.assertEqual(meta.ModelFieldEnumerator(CremeEntity, deep=0).exclude(lambda f: f.name.endswith('ied'), viewable=False).choices(),
                         [('created',  _('Creation date')),
                          #('user',     _('User')),
                         ]
                        )

    def test_field_enumerator05(self): #other ct
        expected = [('created',     _('Creation date')),
                    ('modified',    _('Last modification')),
                    ('last_name',   _('Last name')),
                    ('first_name',  _('First name')),
                    ('description', _('Description')),
                    ('skype',       _('Skype')),
                    ('phone',       _('Phone number')),
                    ('mobile',      _('Mobile')),
                    ('fax',         _('Fax')),
                    ('email',       _('Email address')),
                    ('url_site',    _('Web Site')),
                    ('birthday',    _('Birthday')),
                   ]
        choices = meta.ModelFieldEnumerator(Contact).filter(viewable=True).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(Contact, only_leafs=False) \
                      .filter((lambda f: f.get_internal_type() != 'ForeignKey'), viewable=True) \
                      .choices()
        expected.append(('language',  _('Spoken language(s)'))) #TODO: test with another model with a m2m field when this field is removed....
        self.assertEqual(expected, choices, choices)

    def test_field_enumerator06(self): #filter/exclude : multiple conditions + field true attributes
        expected = [('user',             _('User')),
                    ('civility',         _('Civility')),
                    ('last_name',        _('Last name')),
                    ('first_name',       _('First name')),
                    ('description',      _('Description')),
                    ('skype',            _('Skype')),
                    ('phone',            _('Phone number')),
                    ('mobile',           _('Mobile')),
                    ('fax',              _('Fax')),
                    ('position',         _('Position')),
                    ('sector',           _('Line of business')),
                    ('email',            _('Email address')),
                    ('url_site',         _('Web Site')),
                    #('billing_address',  _('Billing address')),
                    #('shipping_address', _('Shipping address')),
                    #('is_user',          _('Is an user')),
                    ('birthday',         _('Birthday')),
                    ('image',            _('Photograph')),
                   ]
        choices = meta.ModelFieldEnumerator(Contact, only_leafs=False).filter(editable=True, viewable=True).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(Contact, only_leafs=False).exclude(editable=False, viewable=False).choices()
        self.assertEqual(expected, choices, choices)

    def test_field_enumerator07(self): #ordering of FKs
        choices = meta.ModelFieldEnumerator(Ticket, deep=1, only_leafs=False).filter(viewable=True).choices()
        fs = u'[%s] - %s'
        self.assertEqual([('created',           _('Creation date')),
                          ('modified',          _('Last modification')),
                          ('user',              _('User')),
                          ('title',             _('Title')),
                          ('description',       _('Description')),
                          ('status',            _('Status')),
                          ('priority',          _('Priority')),
                          ('criticity',         _('Criticity')),
                          ('solution',          _('Solution')),
                          ('closing_date',      _('Closing date')),
                          ('user__username',    fs % (_('User'), _('username'))),
                          ('user__first_name',  fs % (_('User'), _('first name'))),
                          ('user__last_name',   fs % (_('User'), _('last name'))),
                          ('user__email',       fs % (_('User'), _('e-mail address'))),
                          ('user__role',        fs % (_('User'), _('Role'))),
                          ('user__is_team',     fs % (_('User'), _('Is a team ?'))),
                          ('status__name',      fs % (_('Status'), _('Name'))),
                          ('status__is_custom', fs % (_('Status'), _('is custom'))),
                          ('priority__name',    fs % (_('Priority'), _('Name'))),
                          ('criticity__name',   fs % (_('Criticity'), _('Name'))),
                         ],
                         choices, choices
                        )

    #TODO: complete


class ChunkToolsTestCase(CremeTestCase):
    data = """04 05 99 66 54
055 6 5322 1 2

98

    456456 455 12
        45 156
dfdsfds
s556"""

    def assertRightEntries(self, entries):
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

        self.assertRightEntries(entries)

    def test_iter_splitchunks02(self):
        #Test big_chunks
        chunk_size = len(self.data) / 2
        entries = list(chunktools.iter_splitchunks(self.chunks(chunk_size), '\n', ChunkToolsTestCase.filter))

        self.assertRightEntries(entries)

    def test_iter_splitchunks03(self):
        #Test with one chunk
        chunk_size = len(self.data) * 2
        entries = list(chunktools.iter_splitchunks(self.chunks(chunk_size), '\n', ChunkToolsTestCase.filter))

        self.assertRightEntries(entries)


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


class QueriesTestCase(CremeTestCase):
    def test_get_first_or_None01(self):
        ptype = CremePropertyType.objects.create(text='Is cute', is_custom=True)
        self.assertIsInstance(get_first_or_None(CremePropertyType), CremePropertyType)

    def test_get_first_or_None02(self):
        Civility.objects.all().delete()
        self.assertIsNone(get_first_or_None(Civility))

    #TODO: test get_q_from_dict()


class XMLUtilsTestCase(CremeTestCase):
    def test_iter(self):
        def make_tuples(xml):
            return [(deep_change, elt.tag) for (deep_change, elt) in _element_iterator(XML(xml))]

        self.assertEqual([(0, 'commands')],
                         make_tuples('<?xml version="1.0" encoding="UTF-8"?>'
                                     '<commands></commands>'
                                    )
                        )
        self.assertEqual([(0, 'commands'), (1, 'create')],
                         make_tuples('<commands><create /></commands>')
                        )
        self.assertEqual([(0, 'commands'), (1, 'create'), (1, 'entity')],
                         make_tuples('<commands><create><entity /></create></commands>')
                        )
        self.assertEqual([(0, 'commands'), (1, 'create'), (1, 'entity'), (0, 'entity'), (-1, 'update')],
                         make_tuples('<commands>'
                                     '  <create><entity /><entity />'
                                     '  </create>'
                                     '  <update />'
                                     '</commands>'
                                    )
                        )
        self.assertEqual([(0, 'commands'), (1, 'create'), (1, 'entity'),
                          (0, 'entity'), (1, 'field'), (-2, 'update'),
                         ],
                         make_tuples('<commands>'
                                     '  <create><entity /><entity><field id="5" /></entity></create>'
                                     '  <update />'
                                     '</commands>'
                                    )
                        )
        self.assertEqual([(0, 'commands'), (1, 'create'), (1, 'entity'), (0, 'entity'),
                          (1, 'field'), (-1, 'entity'), (-1, 'update'), (1, 'entity'),
                         ],
                         make_tuples('<commands>'
                                     '  <create>'
                                     '      <entity />'
                                     '      <entity><field id="5" /></entity>'
                                     '      <entity />'
                                     '  </create>'
                                     '  <update><entity /></update>'
                                     '</commands>'
                                    )
                        )

    def test_xml_diff01(self):
        xml01 = '<?xml version="1.0" encoding="UTF-8"?><commands></commands>'
        xml02 = '<?xml version="1.0" encoding="UTF-8"?><commands />'
        self.assertIsNone(xml_diff(xml01, xml02))

        xml01 = u'<?xml version="1.0" encoding="utf-8"?><créer></créer>'
        xml02 = u'<?xml version="1.0" encoding="UTF-8"?><créer />'
        self.assertIsNone(xml_diff(xml01, xml02))

    def test_xml_diff02(self): # attributes order can vary
        xml01 = ('<?xml version="1.0" encoding="UTF-8"?>'
                 '<commands attr1="foo" attr2="bar"></commands>'
                )
        self.assertIsNone(xml_diff(xml01, '<commands attr2="bar" attr1="foo" />'))

    def test_xml_diff03(self): #attributes value difference
        diff = xml_diff('<commands attr1="foo" attr2="bar"></commands>',
                        '<commands attr2="bar" attr1="stuff" />'
                       )
        self.assertIsNotNone(diff)
        self.assertEqual('<commands> ===> Attribute "attr1": "foo" != "stuff"', diff.short_msg)
        self.assertEqual('<commands attr1="foo" attr2="bar">'
                         ' -================= HERE : Attribute "attr1": "foo" != "stuff" ==========</commands>',
                         diff.long_msg
                        )
        #self.assertEqual('<commands attr1="foo" attr2="bar" /> -================= HERE : Attribute "attr1": "foo" != "stuff" ==========',
                         #diff.long_msg
                        #)

    def test_xml_diff04(self): #additional attribute
        xml01 = ('<commands attr1="foo">\n'
                 '    <create />\n'
                 '</commands>'
                )
        xml02 = ('<commands attr2="bar" attr1="foo" >'
                 ' <create />'
                 '</commands>'
                )
        diff = xml_diff(xml01, xml02)
        self.assertIsNotNone(diff)
        self.assertEqual('<commands> ===> Attribute "attr2" is missing in the first document',
                         diff.short_msg
                        )
        self.assertEqual('<commands attr1="foo"> -================= HERE : '
                         'Attribute "attr2" is missing in the first document ==========\n'
                         '    <create />\n'
                         '</commands>',
                         diff.long_msg
                        )
        #self.assertEqual('<commands attr1="foo">\n'
                         #'    <create />\n'
                         #'</commands> -================= HERE : Attribute "attr2" is missing in the first document ==========',
                         #diff.long_msg
                        #)

    def test_xml_diff05(self): #missing attribute
        diff = xml_diff('<commands attr1="bar" attr2="stuff" />', '<commands attr2="stuff" />')
        self.assertIsNotNone(diff)
        self.assertEqual('<commands> ===> Attribute "attr1" is missing in the second document',
                         diff.short_msg
                        )
        self.assertEqual('<commands attr1="bar" attr2="stuff"> -================= HERE : '
                         'Attribute "attr1" is missing in the second document ==========</commands>',
                         diff.long_msg
                        )

    def test_xml_diff06(self):
        xml01 = ('<commands attr1="foo" attr2="bar">'
                    '<create attr3="xxx" >'
                    '</create>'
                 '</commands>'
                )
        xml02 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />'
                 '</commands>'
                )
        self.assertIsNone(xml_diff(xml01, xml02))

    def test_xml_diff07(self): #tag difference
        xml01 = ('<commands attr1="foo" attr2="bar">\n'
                 '   <create attr3="xxx" >\n'
                 '   </create>\n'
                 '</commands>'
                )
        xml02 = ('<commands attr2="bar" attr1="foo" >'
                 '   <update />'
                 '</commands>'
                )
        diff = xml_diff(xml01, xml02)
        self.assertIsNotNone(diff)
        self.assertEqual('<create> ===> Tag "create" != "update"', diff.short_msg)
        self.assertEqual('<commands attr1="foo" attr2="bar">\n'
                         '   <create attr3="xxx"> -================= HERE : Tag "create" != "update" ==========\n'
                         '   </create>\n'
                         '</commands>',
                         diff.long_msg
                        )

    def test_xml_diff08(self): #missing child
        xml01 = ('<commands attr1="foo" attr2="bar">\n'
                 '   <create attr3="xxx" >\n'
                 '      <update />'
                 '   </create>\n'
                 '</commands>'
                )
        xml02 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />'
                 '   <update />'
                 '</commands>'
                )
        diff = xml_diff(xml01, xml02)
        self.assertIsNotNone(diff)
        self.assertEqual('<update> ===> Does not exist', diff.short_msg)

    def test_xml_diff09(self): # child becomes sibling
        xml01 = ('<commands attr1="foo" attr2="bar">\n'
                 '   <create attr3="xxx" >\n'
                 '      <field name="uuid" />\n'
                 '      <update />'
                 '   </create>\n'
                 '</commands>'
                )
        xml02 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" >\n'
                 '      <field name="uuid" />\n'
                 '   </create>\n'
                 '   <update />'
                 '</commands>'
                )
        diff = xml_diff(xml01, xml02)
        self.assertIsNotNone(diff)
        self.assertEqual('<update> ===> Does not exist', diff.short_msg)

    def test_xml_diff10(self): #additional child
        xml01 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />'
                 '   <update />'
                 '</commands>'
                )
        xml02 = ('<commands attr1="foo" attr2="bar">\n'
                 '   <create attr3="xxx" >\n'
                 '      <update />'
                 '   </create>\n'
                 '</commands>'
                )
        diff = xml_diff(xml01, xml02)
        self.assertIsNotNone(diff)
        self.assertEqual('<create> ===> Additional sibling or child element in the second document',
                         diff.short_msg
                        )

    def test_xml_diff11(self): #text difference
        xml01 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />'
                 '   <update />'
                 '</commands>'
                )
        xml02 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />'
                 '   <update>Text element</update>'
                 '</commands>'
                )
        diff = xml_diff(xml01, xml02)
        self.assertIsNotNone(diff)
        self.assertEqual('<update> ===> Text "" != "Text element"', diff.short_msg)

    def test_xml_diff12(self): #missing tag
        xml01 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />'
                 '   <update />'
                 '</commands>'
                )
        diff = xml_diff(xml01, '<commands attr2="bar" attr1="foo" />')
        self.assertIsNotNone(diff)
        self.assertEqual('<create> ===> Does not exist in second document', diff.short_msg)

    def test_xml_diff13(self): #additional tags
        xml02 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />'
                 '   <update />'
                 '</commands>'
                )
        diff = xml_diff('<commands attr2="bar" attr1="foo" />', xml02)
        self.assertIsNotNone(diff)
        self.assertEqual('<commands> ===> Additional sibling or child element in the second document',
                         diff.short_msg
                        )

    def test_xml_diff14(self): #tail difference
        xml01 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />My Tail'
                 '   <update />'
                 '</commands>'
                )
        xml02 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />'
                 '   <update />'
                 '</commands>'
                )
        diff = xml_diff(xml01, xml02)
        self.assertIsNotNone(diff)
        self.assertEqual('<create> ===> Tail "My Tail" != ""', diff.short_msg)

    def test_assert_xml_equal(self):
        xml01 = ('<commands attr2="bar" attr1="foo" >'
                 '   <create attr3="xxx" />'
                 '   <update />'
                 '</commands>'
                )
        self.assertXMLEqual(xml01,
                            '<commands attr1="foo" attr2="bar" >'
                            ' <create attr3="xxx" />'
                            ' <update></update>'
                            '</commands>'
                           )

        self.assertRaises(AssertionError, self.assertXMLEqual, xml01,
                          '<commands attr2="bar" >'
                          '   <create attr3="xxx" />'
                          '   <update />'
                          '</commands>'
                         )
        self.assertRaises(AssertionError, self.assertXMLEqual,
                          '<commands attr2="bar" attr1="foo" >', #syntax error
                          '<commands attr2="bar" attr1="foo" />',
                         )
