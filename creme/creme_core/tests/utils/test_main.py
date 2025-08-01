import string
from datetime import date, datetime
from functools import partial
from os.path import join

from django.conf import settings
from django.http import Http404
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import make_aware, zoneinfo
from django.utils.translation import gettext, gettext_lazy, ngettext
from django.utils.translation import override as override_language
from PIL.Image import open as open_img

from creme.creme_core.models import FakeContact, FakeOrganisation
from creme.creme_core.utils import (
    as_int,
    ellipsis,
    ellipsis_multi,
    entities_to_str,
    get_from_GET_or_404,
    get_from_POST_or_404,
    int_2_roman,
    prefixed_truncate,
    safe_unicode,
    truncate_str,
    update_model_instance,
)
from creme.creme_core.utils.crypto import SymmetricEncrypter
from creme.creme_core.utils.dates import (
    date_2_dict,
    date_from_ISO8601,
    date_from_str,
    date_to_ISO8601,
    dt_from_ISO8601,
    dt_from_str,
    dt_to_ISO8601,
    round_hour,
    to_utc,
)
from creme.creme_core.utils.dependence_sort import (
    DependenciesLoopError,
    dependence_sort,
)
from creme.creme_core.utils.html import (
    escapejson,
    render_limited_list,
    strip_html,
)
from creme.creme_core.utils.log import log_exceptions
from creme.creme_core.utils.secure_filename import secure_filename
from creme.creme_core.utils.url import TemplateURLBuilder, parse_path

from ..base import CremeTestCase


class MiscTestCase(CremeTestCase):
    def test_truncate_str_01(self):
        s = string.ascii_letters
        self.assertEqual(52, len(s))

        truncated = truncate_str(s, 50)
        self.assertEqual(50,     len(truncated))
        self.assertEqual(s[:-2], truncated)

        expected = s[:-5] + '012'
        self.assertEqual(expected, truncate_str(s, 50, suffix='012'))

        self.assertEqual('',      truncate_str('',        0, suffix='01234'))
        self.assertEqual('01234', truncate_str('abcdef',  5, suffix='01234'))
        self.assertEqual('abc',   truncate_str('abcdef',  3, suffix=''))
        self.assertEqual('',      truncate_str('abcdef', -1, suffix=''))
        self.assertEqual('',      truncate_str('abcdef', -1, suffix='aaaaaa'))
        self.assertEqual('a',     truncate_str('b',       1, suffix='a'))
        self.assertEqual('abcd',  truncate_str('abcdef',  4, suffix='01234'))

    def test_update_model_instance01(self):
        user = self.get_root_user()
        first_name = 'punpun'
        last_name = 'punpunyama'
        pupun = FakeContact.objects.create(
            user=user, first_name=first_name, last_name=last_name,
        )

        first_name = first_name.title()

        update_model_instance(pupun, first_name=first_name)
        self.assertEqual(first_name, self.refresh(pupun).first_name)

        with self.assertNumQueries(0):
            update_model_instance(pupun, last_name=last_name)

        self.assertRaises(
            AttributeError,
            update_model_instance,
            pupun, first_name=first_name, unknown_field='??',
        )

    def test_update_model_instance02(self):
        first_name = 'punpun'
        last_name = 'punpunyama'
        pupun = FakeContact.objects.create(
            user=self.get_root_user(), first_name=first_name, last_name=last_name,
        )

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

        # Key error
        self.assertRaises(Http404, get_from_GET_or_404, request, 'name_')

        # Cast error
        self.assertRaises(Http404, get_from_GET_or_404, request, 'name', int)

        # Cast error
        self.assertRaises(Http404, get_from_GET_or_404, request, 'name_', int, default='string')

        self.assertEqual('36', get_from_POST_or_404(request, 'age'))
        self.assertEqual(36, get_from_POST_or_404(request, 'age', int))
        self.assertEqual(1,  get_from_POST_or_404(request, 'name_', int, default=1))

    def test_safe_unicode(self):
        self.assertEqual('kjøÔ€ôþâ', safe_unicode('kjøÔ€ôþâ'))
        self.assertEqual('aé‡ae15', safe_unicode(b'a\xe9\x87ae15'))
        self.assertEqual('aé‡ae15', safe_unicode('aé‡ae15'))

        # Custom encoding list
        self.assertEqual('a\ufffdae15', safe_unicode(b'a\xe9\x87ae15', ['utf-8']))
        self.assertEqual('aé‡ae15',     safe_unicode(b'a\xe9\x87ae15', ('cp1252',)))

    def test_safe_unicode_object(self):
        class no_unicode_object:
            pass

        class unicode_object:
            def __str__(self):
                return 'aé‡ae15'

        self.assertEqual(
            "<class 'creme.creme_core.tests.utils."
            "test_main.MiscTestCase.test_safe_unicode_object.<locals>.no_unicode_object'>",
            safe_unicode(no_unicode_object)
        )
        self.assertEqual('aé‡ae15', safe_unicode(unicode_object()))

    def test_date_2_dict(self):
        d = {'year': 2012, 'month': 6, 'day': 6}
        self.assertEqual(d, date_2_dict(date(**d)))

    def test_as_int(self):
        self.assertEqual(1, as_int('1'))
        self.assertEqual(42, as_int('42'))
        self.assertEqual(-12, as_int('-12'))

        self.assertEqual(0, as_int('foo'))
        self.assertEqual(0, as_int([]))
        self.assertEqual(-1, as_int('foo', default=-1))

    def test_int_2_roman(self):
        self.assertListEqual(
            [
                'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
                'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX'
            ],
            [int_2_roman(i) for i in range(1, 21)],
        )
        self.assertEqual('MM',        int_2_roman(2000))
        self.assertEqual('MCMXCIX',   int_2_roman(1999))
        self.assertEqual('MMMCMXCIX', int_2_roman(3999))

        with self.assertLogs(level='CRITICAL'):
            self.assertEqual('?', int_2_roman(4000))

    def test_ellipsis(self):
        self.assertEqual('123456789', ellipsis('123456789', 9))
        self.assertEqual('1234567…',  ellipsis('123456789', 8))

    def test_ellipsis_multi(self):
        self.assertListEqual(
            ['a', 'b'], ellipsis_multi(['a', 'b'], 10),
        )
        self.assertListEqual(
            ['123456789', 'b'], ellipsis_multi(['123456789', 'b'], 10),
        )
        self.assertListEqual(
            ['1234567…', 'b'], ellipsis_multi(['123456789', 'b'], 9),
        )
        self.assertListEqual(
            ['1234…', '12', '12'], ellipsis_multi(['123456', '12', '12'], 9),
        )
        self.assertListEqual(
            ['12…', '12', '123…'],  # ['123…', '12', '12…'] would be better...
            ellipsis_multi(['123456', '12', '12345'], 9),
        )

    def test_prefixed_truncate(self):
        s = 'Supercalifragilis Ticexpialidocious'
        self.assertEqual(s, prefixed_truncate(s, '(My prefix)', 49))
        self.assertEqual(
            '(My prefix)Supercalifragilis Tic',
            prefixed_truncate(s, '(My prefix)', 32),
        )

        with self.assertRaises(ValueError):
            prefixed_truncate(s, '(My prefix)', 10)  # Prefix is too short for this length

        self.assertEqual(
            '(My unlocated prefix)Supercalif',
            prefixed_truncate(s, gettext_lazy('(My unlocated prefix)'), 31),
        )

    def test_log_exception(self):
        class Logger:
            def __init__(self):
                self.data = []

            def warn(self, s):
                self.data.append(s)

        my_logger = Logger()

        @log_exceptions(printer=my_logger.warn)
        def no_problemo(a, b):
            return a + b

        res = no_problemo(1, b=2)
        self.assertEqual(3, res)
        self.assertFalse(my_logger.data)

        # ----
        @log_exceptions(printer=my_logger.warn)
        def error_paluzza():
            raise ValueError('Mayday')

        with self.assertRaises(ValueError):
            error_paluzza()

        self.assertEqual(1, len(my_logger.data))
        self.assertStartsWith(
            my_logger.data[0], 'An exception occurred in <error_paluzza>.\n',
        )

    # TODO: add test for Windows
    def test_secure_filename(self):
        self.assertEqual('My_cool_movie.mov', secure_filename('My cool movie.mov'))
        self.assertEqual('etc_passwd',        secure_filename('../../../etc/passwd'))
        self.assertEqual(
            'i_contain_cool_umlauts.txt',
            secure_filename('i contain cool \xfcml\xe4uts.txt'),
        )
        self.assertEqual(
            'i_contain_weird_characters.txt',
            secure_filename('i contain weird châräctérs.txt'),
        )

        with self.assertNoException():
            with open_img(join(settings.CREME_ROOT, 'static', 'common', 'images',
                               secure_filename('500_200.png'))) as img_fd:
                size = img_fd.size
        self.assertEqual((200, 200), size)

    def test_escapejson(self):
        self.assertEqual(escapejson('&'), '\\u0026')
        self.assertEqual(escapejson('\\'), '\\u005C')
        self.assertEqual(
            escapejson('{"a": 12, "b": "-->alert();<script/>"}'),
            '{"a": 12, "b": "--\\u003Ealert();\\u003Cscript/\\u003E"}',
        )

    def test_strip_html(self):
        self.assertEqual('foobar',     strip_html('foobar'))
        self.assertEqual('foobar',     strip_html('<b>foobar</b>'))
        self.assertEqual('97%',        strip_html('97&#x0025;'))
        self.assertEqual('97%',        strip_html('97&#37;'))
        self.assertEqual('97&#abc;',   strip_html('97&#abc;'))
        self.assertEqual('foo bar', strip_html('foo&nbsp;bar'))

        self.assertEqual(
            'Taste our new recipe which is 72%\n'
            'better & lighter than the previous one.\n'
            '\n'
            'Visit our site !',
            # 'Visit our site (https://slurm.com) !',  TODO ??,
            strip_html('''
<html>
<head></head>
<body style="margin:0px; padding:0px;">
<table width="640" cellpadding="0" cellspacing="0" border="0">
<tbody>
<tr>
<td valign="top" align="center"></td>
<td width="320"><p style="text-align: justify;">
Taste our <span style="text-decoration:underline;">new recipe</span> which is 72%
better &amp; lighter than the previous one.
</p></td>
<td valign="top" align="center">Visit our <a href="https://slurm.com">site</a> !</td>
</body>
</html>
''').strip()
        )

    def test_string_smart_split(self):
        from creme.creme_core.utils.string import smart_split

        self.assertEqual([], smart_split(''))
        self.assertEqual(['foobar'], smart_split('foobar'))

        self.assertEqual(['foo', 'bar'], smart_split('foo bar'))
        self.assertEqual(['foo', 'bar', 'baz'], smart_split('foo bar baz'))

        self.assertEqual(['foo bar', 'baz'], smart_split('"foo bar" baz'))
        # TODO: self.assertEqual(['foo', 'bar', ' baz kuu'], smart_split('foo bar " baz kuu"'))  ?
        self.assertEqual(['foo', 'bar', 'baz kuu'], smart_split('foo bar " baz kuu" '))

        self.assertEqual(['baz'], smart_split('"" baz'))
        self.assertEqual(['baz'], smart_split('" " baz'))

        # Missing second "
        self.assertEqual(['foo', 'bar', 'baz'], smart_split('foo bar" baz'))

        # Special char \"
        self.assertEqual(['foobar"'], smart_split(r'foobar\"'))
        self.assertEqual(['"foobar'], smart_split(r'\"foobar'))

        self.assertEqual(['foo "bar', 'baz'], smart_split('"foo \\"bar" baz'))

        # Missing second " + special char \"
        self.assertEqual(['foo', 'bar', '"baz'], smart_split('foo bar" \\"baz '))

    def test_render_limited_list(self):
        self.assertEqual('', render_limited_list(items=[], limit=200))
        self.assertEqual('Penpen', render_limited_list(items=['Penpen'], limit=200))

        items = ['EVA-00', 'EVA-01', 'EVA-02<script>']
        self.assertHTMLEqual(
            f'<ul class="limited-list">'
            f' <li>{items[0]}</li>'
            f' <li>{items[1]}</li>'
            f' <li>EVA-02&lt;script&gt;</li>'
            f'</ul>',
            render_limited_list(items=items, limit=3),
        )

        one_extra = ngettext(
            '{count} more element', '{count} more elements', 1,
        ).format(count=1)
        self.assertHTMLEqual(
            f'<ul class="limited-list">'
            f' <li>{items[0]}</li>'
            f' <li>{items[1]}</li>'
            f' <li><span class="more-elements">{one_extra}</span></li>'
            f'</ul>',
            render_limited_list(items=items, limit=2),
        )

        two_extra = ngettext(
            '{count} more element', '{count} more elements', 2,
        ).format(count=2)
        self.assertHTMLEqual(
            f'<ul class="limited-list">'
            f' <li>{items[0]}</li>'
            f' <li><span class="more-elements">{two_extra}</span></li>'
            f'</ul>',
            render_limited_list(items=items, limit=1),
        )

    def test_entities_to_str(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, own=['VIEW'])

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Acme#1')
        orga2 = create_orga(name='Acme#2')
        orga3 = create_orga(name='Acme#3', user=self.get_root_user())

        self.assertEqual('', entities_to_str([], user))
        self.assertEqual(orga1.name, entities_to_str([orga1], user))
        self.assertEqual(orga2.name, entities_to_str([orga2], user))
        self.assertEqual(
            gettext('Entity #{id} (not viewable)').format(id=orga3.id),
            entities_to_str([orga3], user),
        )
        self.assertEqual(
            f'{orga1.name}, {orga2.name}',
            entities_to_str([orga1, orga2], user),
        )


class DependenceSortTestCase(CremeTestCase):  # TODO: SimpleTestCase
    class DepSortable:
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
        self.assertListEqual(
            [],
            dependence_sort([], lambda ds: ds.name, lambda ds: ds.dependencies),
        )

    def test_dependence_sort02(self):
        A = self.DepSortable('A')
        B = self.DepSortable('B')
        self.assertListEqual(
            [A, B],
            dependence_sort([A, B], lambda ds: ds.name, lambda ds: ds.dependencies),
        )

    def test_dependence_sort03(self):
        DS = self.DepSortable
        A = DS('A', ['B'])
        B = DS('B')
        self.assertListEqual(
            [B, A], dependence_sort([A, B], DS.key, DS.deps),
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
        self.assertIn(
            dependence_sort([A, B, C, D], DS.key, DS.deps),
            (
                [B, D, C, A],
                [B, C, D, A],
                [D, B, C, A],
            ),
        )

    def test_dependence_sort06(self):
        DS = self.DepSortable
        A = DS('A', ['C'])
        B = DS('B')
        C = DS('C', ['A'])

        self.assertRaises(
            DependenciesLoopError,
            dependence_sort,
            [A, B, C], DS.key, DS.deps,
        )

    def test_dependence_sort07(self):
        DS = self.DepSortable
        A = DS('End', ['Middle'])
        B = DS('Start')
        C = DS('Middle', ['Start'])
        self.assertListEqual([B, C, A], dependence_sort([A, B, C], DS.key, DS.deps))


class DatesTestCase(CremeTestCase):
    def test_dt_from_ISO8601(self):
        self.assertEqual(
            self.create_datetime(
                year=2014, month=3, day=17, hour=15,
                minute=22, second=3, microsecond=357000,
                utc=True,
            ),
            dt_from_ISO8601('2014-03-17T15:22:03.357Z'),
        )
        self.assertEqual(
            self.create_datetime(
                year=2015, month=1, day=16, hour=15,
                minute=22, second=3, microsecond=123456,
                utc=True,
            ),
            dt_from_ISO8601('2015-01-16T15:22:03.123456Z'),
        )
        self.assertEqual(
            self.create_datetime(
                year=999, month=1, day=16, hour=15,
                minute=22, second=3, microsecond=123456,
                utc=True,
            ),
            dt_from_ISO8601('0999-01-16T15:22:03.123456Z'),
        )

    def test_dt_to_ISO8601(self):
        self.assertEqual(
            '2015-01-16T15:22:03.357000Z',
            dt_to_ISO8601(self.create_datetime(
                year=2015, month=1, day=16, hour=15,
                minute=22, second=3, microsecond=357000,
                utc=True,
            )),
        )
        self.assertEqual(
            '2018-02-04T18:41:25.123000Z',
            dt_to_ISO8601(make_aware(
                datetime(
                    year=2018, month=2, day=4, hour=19,
                    minute=41, second=25, microsecond=123000,
                ),
                timezone=zoneinfo.ZoneInfo('Europe/Paris'),  # DST: +1h
            )),
        )
        self.assertEqual(
            '2018-03-05T19:41:25.123000Z',
            dt_to_ISO8601(datetime(
                year=2018, month=3, day=5, hour=19,
                minute=41, second=25, microsecond=123000,
            )),
        )
        self.assertEqual(
            '0999-03-05T19:41:25.123000Z',
            dt_to_ISO8601(datetime(
                year=999, month=3, day=5, hour=19,
                minute=41, second=25, microsecond=123000,
            )),
        )

    @override_language('en')
    def test_dt_from_str__en(self):
        create_dt = self.create_datetime
        self.assertEqual(
            create_dt(year=2013, month=7, day=25, hour=12, minute=28, second=45),
            dt_from_str('2013-07-25 12:28:45'),
        )
        self.assertEqual(
            create_dt(year=2013, month=7, day=25, hour=8, utc=True),
            dt_from_str('2013-07-25 11:00:00+03:00'),
        )
        self.assertIsNone(dt_from_str('25-07-2013 11:00:00'))

        self.assertEqual(
            create_dt(year=2014, month=8, day=26),
            dt_from_str('2014-08-26'),
        )
        self.assertIsNone(dt_from_str('25/07/2013'))

        self.assertEqual(
            create_dt(year=2013, month=7, day=25, hour=12, minute=28, second=45),
            dt_from_str('2013-07-25 12:28:45'),
        )

    @override_language('fr')
    def test_dt_from_str__fr(self):
        create_dt = self.create_datetime
        self.assertEqual(
            create_dt(year=2013, month=7, day=25, hour=12, minute=28, second=45),
            dt_from_str('2013-07-25 12:28:45'),
        )
        self.assertEqual(
            create_dt(year=2013, month=7, day=25, hour=8, utc=True),
            dt_from_str('2013-07-25 11:00:00+03:00'),
        )
        self.assertIsNone(dt_from_str('25-07-2013 11:00:00'))

        self.assertEqual(
            create_dt(year=2013, month=7, day=25),
            dt_from_str('25/07/2013'),
        )
        self.assertEqual(
            create_dt(year=2014, month=8, day=26),
            dt_from_str('2014-08-26'),
        )
        self.assertIsNone(dt_from_str('2013/07/25'))

        self.assertEqual(
            create_dt(year=2013, month=7, day=25, hour=12, minute=28, second=45),
            dt_from_str('2013-07-25 12:28:45'),
        )

    @override_language('en')
    def test_date_from_str__en(self):
        self.assertEqual(date(year=2014, month=8, day=26), date_from_str('2014-08-26'))
        self.assertEqual(date(year=2014, month=8, day=26), date_from_str('08/26/2014'))
        self.assertIsNone(date_from_str('25/07/2013'))
        self.assertIsNone(date_from_str('2014/08/26'))

    @override_language('fr')
    def test_date_from_str__fr(self):
        self.assertEqual(date(year=2013, month=7, day=25), date_from_str('25/07/2013'))
        self.assertEqual(date(year=2014, month=8, day=26), date_from_str('2014-08-26'))
        self.assertIsNone(date_from_str('2014/08/26'))
        self.assertIsNone(date_from_str('08/26/2014'))

    def test_round_datetime(self):
        create_dt = self.create_datetime
        self.assertEqual(
            create_dt(
                year=2013, month=7, day=25, hour=12, minute=0, second=0, microsecond=0,
            ),
            round_hour(create_dt(
                year=2013, month=7, day=25, hour=12, minute=28, second=45, microsecond=516,
            )),
        )

    def test_to_utc(self):
        dt = datetime(
            year=2016, month=11, day=23, hour=18, minute=28,
            tzinfo=zoneinfo.ZoneInfo('Europe/Paris'),  # +01:00
        )
        self.assertEqual(
            datetime(year=2016, month=11, day=23, hour=17, minute=28),
            to_utc(dt),
        )

    def test_date_from_ISO8601(self):
        self.assertEqual(
            date(year=2016, month=11, day=23),
            date_from_ISO8601('2016-11-23'),
        )
        self.assertEqual(
            date(year=999, month=2, day=3),
            date_from_ISO8601('0999-02-03'),
        )

    def test_date_to_ISO8601(self):
        self.assertEqual(
            '2016-11-23',
            date_to_ISO8601(date(year=2016, month=11, day=23)),
        )
        self.assertEqual(
            '0999-02-03',
            date_to_ISO8601(date(year=999, month=2, day=3)),
        )


class UnicodeCollationTestCase(CremeTestCase):
    def test_uca01(self):
        from creme.creme_core.utils.unicode_collation import collator

        sort = partial(sorted, key=collator.sort_key)
        words = ['Caff', 'Cafe', 'Cafard', 'Café']
        self.assertListEqual(['Cafard', 'Cafe', 'Caff', 'Café'], sorted(words))  # Standard sort
        self.assertListEqual(['Cafard', 'Cafe', 'Café', 'Caff'], sort(words))

        self.assertListEqual(
            ['La', 'Là', 'Lä', 'Las', 'Le'],
            sort(['La', 'Là', 'Le', 'Lä', 'Las']),
        )
        self.assertListEqual(
            ['gloves', 'ĝloves', 'hats', 'shoes'],
            sort(['hats', 'gloves', 'shoes', 'ĝloves']),
        )

    # NB: keep this comment (until we use the real 'pyuca' lib)
    # def test_uca02(self):
    #     "Original lib"
    #     from os.path import join
    #     from pyuca import Collator
    #
    #     path = join(settings.CREME_ROOT, 'creme_core', 'utils', 'allkeys.txt')
    #     collator = Collator(path)
    #     sort = partial(sorted, key=collator.sort_key)
    #     words = ['Caff', 'Cafe', 'Cafard', 'Café']
    #     self.assertEqual(['Cafard', 'Cafe', 'Caff', u'Café'], sorted(words)) # standard sort
    #     self.assertEqual(['Cafard', 'Cafe', 'Café', 'Caff'], sort(words))
    #
    #     self.assertEqual(['La', 'Là', 'Lä', 'Las', 'Le'],
    #                      sort(['La', 'Là', 'Le', 'Lä', 'Las'])
    #                     )
    #     self.assertEqual(['gloves', 'ĝloves', 'hats', 'shoes'],
    #                      sort(['hats', 'gloves', 'shoes', 'ĝloves']),
    #                     )
    #
    #     #test memory consumption
    #     #from time import sleep
    #     #sleep(10)


class CryptoTestCase(CremeTestCase):
    def test_symmetric_encrypter(self):
        se = SymmetricEncrypter(salt='my_app.my_model')
        data = b'Secret message!'
        encrypted = se.encrypt(data)
        self.assertNotEqual(data, encrypted)
        self.assertEqual(data, se.decrypt(encrypted))

        # ---
        se2 = SymmetricEncrypter(salt='other_salt')
        with self.assertRaises(SymmetricEncrypter.Error) as cm:
            se2.decrypt(encrypted)
        self.assertEqual(
            'SymmetricEncrypter.decrypt: invalid token', str(cm.exception),
        )


class CurrencyFormatTestCase(CremeTestCase):
    def test_currency(self):
        from decimal import Decimal

        from creme.creme_core.models import Currency, SettingValue
        from creme.creme_core.setting_keys import currency_symbol_key
        from creme.creme_core.utils.currency_format import currency

        sv = self.get_object_or_fail(SettingValue, key_id=currency_symbol_key.id)
        self.assertTrue(sv.value)

        result1 = currency(3)
        self.assertIsInstance(result1, str)
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
        self.clear_global_info()
        result5 = currency(5, currency_or_id=my_currency)
        self.assertIn('5', result5)
        self.assertIn(my_currency.international_symbol, result5)
        self.assertNotIn(my_currency.local_symbol, result5)

        result6 = currency(5, currency_or_id=my_currency.id)
        self.assertEqual(result5, result6)

        result7 = currency(-5, currency_or_id=my_currency)
        self.assertNotEqual(result6, result7)


class TemplateURLBuilderTestCase(CremeTestCase):
    def test_place_holder01(self):
        "Word."
        ph = TemplateURLBuilder.Word('$name', 'name')
        self.assertEqual('__placeholder0__', ph.tmp_name(0, 0))
        self.assertEqual('__placeholder1__', ph.tmp_name(1, 0))
        self.assertEqual('__PLACEHOLDER0__', ph.tmp_name(0, 1))

    def test_place_holder02(self):
        "Int."
        ph = TemplateURLBuilder.Int('$ct_id', 'ctype_id')
        self.assertEqual('1234567890', ph.tmp_name(0, 0))
        self.assertEqual('1234567891', ph.tmp_name(1, 0))
        self.assertEqual('9876543210', ph.tmp_name(0, 1))

    def test_one_place_holder01(self):
        "Word placeholder."
        vname = 'creme_core__batch_process_ops'
        placeholder = 'XXXXXX'
        final_value = '${name}'  # This string does not match with (?P<field>[\w]+)

        tub = TemplateURLBuilder(field=(TemplateURLBuilder.Word, final_value))

        self.assertEqual(
            reverse(vname, args=(65, placeholder)).replace(placeholder, final_value),
            tub.resolve(vname, kwargs={'ct_id': 65}),
        )

    def test_one_place_holder02(self):
        "Int placeholder."
        vname = 'creme_core__batch_process_ops'
        placeholder = '123456'
        final_value = '${ct}'  # This string does not match with (?P<ct_id>\d+)

        tub = TemplateURLBuilder(ct_id=(TemplateURLBuilder.Int, final_value))

        self.assertEqual(
            reverse(vname, args=(placeholder, 'name')).replace(placeholder, final_value),
            tub.resolve(vname, kwargs={'field': 'name'}),
        )

    def test_two_place_holders01(self):
        "1 word & 1 int placeholders."
        vname = 'creme_core__batch_process_ops'

        placeholder1 = '123456'
        final_value1 = '${ct}'

        placeholder2 = 'XXXXXX'
        final_value2 = '${name}'

        tub = TemplateURLBuilder(
            ct_id=(TemplateURLBuilder.Int,  final_value1),
            field=(TemplateURLBuilder.Word, final_value2),
        )

        self.assertEqual(
            reverse(
                vname, args=(placeholder1, placeholder2),
            ).replace(placeholder1, final_value1)
             .replace(placeholder2, final_value2),
            tub.resolve(vname),
        )

    def test_two_place_holders02(self):
        "2 int placeholders."
        vname = 'creme_core__inner_edition'

        placeholder1 = '123456'
        final_value1 = '${id1}'

        placeholder2 = '789456'
        final_value2 = '${id2}'

        tub = TemplateURLBuilder(
            ct_id=(TemplateURLBuilder.Int, final_value1),
            id=(TemplateURLBuilder.Int, final_value2),
        )
        self.assertEqual(
            reverse(
                vname, args=(placeholder1, placeholder2)
            ).replace(placeholder1, final_value1).replace(placeholder2, final_value2),
            tub.resolve(vname),
        )


class TestPath(TestCase):
    def test_empty(self):
        self.assertEqual('', parse_path('').geturl())
        self.assertEqual('/', parse_path('/').geturl())
        self.assertEqual('file://', parse_path('file://').geturl())

    def test_file(self):
        self.assertEqual('file://C/test', parse_path(r'C:\test').geturl())
        self.assertEqual('file://C/test', parse_path(r'file://C:/test').geturl())
        self.assertEqual('test', parse_path(r'test').geturl())

    def test_protocol(self):
        self.assertEqual('https://test', parse_path(r'https://test').geturl())
        self.assertEqual('https://C:/test', parse_path(r'https://C:/test').geturl())
