from string import ascii_letters

from django.utils.translation import gettext_lazy, pgettext

from creme.creme_core.utils.string import (
    multi_truncate,
    prefixed_truncate,
    smart_split,
    suffixed_truncate,
)

from ..base import CremeTestCase


class StringTestCase(CremeTestCase):
    def test_smart_split(self):
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

    def test_multi_truncate(self):
        self.assertListEqual(
            ['a', 'b'], multi_truncate(['a', 'b'], 10),
        )
        self.assertListEqual(
            ['123456789', 'b'], multi_truncate(['123456789', 'b'], 10),
        )

        msg = pgettext(
            "String to return when truncating text", "%(truncated_text)s…"
        )
        self.assertListEqual(
            [msg % {'truncated_text': '1234567'}, 'b'],
            multi_truncate(['123456789', 'b'], 9),
        )
        self.assertListEqual(
            [msg % {'truncated_text': '1234'}, '12', '12'],
            multi_truncate(['123456', '12', '12'], 9),
        )
        self.assertListEqual(
            [
                msg % {'truncated_text': '12'},
                '12',
                msg % {'truncated_text': '123'},
            ],  # ['123…', '12', '12…'] would be better...
            multi_truncate(['123456', '12', '12345'], 9),
        )

    def test_prefixed_truncate(self):
        s = 'Supercalifragilis Ticexpialidocious'
        self.assertEqual(s, prefixed_truncate(s, '(My prefix)', 49))
        self.assertEqual(
            '(My prefix)Supercalifragilis Tic',
            prefixed_truncate(s, prefix='(My prefix)', length=32),
        )

        with self.assertRaises(ValueError):
            prefixed_truncate(s, '(My prefix)', 10)  # Prefix is too short for this length

        self.assertEqual(
            '(My unlocated prefix)Supercalif',
            prefixed_truncate(s, gettext_lazy('(My unlocated prefix)'), 31),
        )

    def test_suffixed_truncate(self):
        s = ascii_letters
        self.assertEqual(52, len(s))

        truncated = suffixed_truncate(s, length=50)
        self.assertEqual(50,     len(truncated))
        self.assertEqual(s[:-2], truncated)

        expected = s[:-5] + '012'
        self.assertEqual(expected, suffixed_truncate(s, length=50, suffix='012'))

        self.assertEqual('',      suffixed_truncate('',       length=0,  suffix='01234'))
        self.assertEqual('01234', suffixed_truncate('abcdef', length=5,  suffix='01234'))
        self.assertEqual('abc',   suffixed_truncate('abcdef', length=3,  suffix=''))
        self.assertEqual('',      suffixed_truncate('abcdef', length=-1, suffix=''))
        self.assertEqual('',      suffixed_truncate('abcdef', length=-1, suffix='aaaaaa'))
        self.assertEqual('a',     suffixed_truncate('b',      length=1,  suffix='a'))
        self.assertEqual('abcd',  suffixed_truncate('abcdef', length=4,  suffix='01234'))
