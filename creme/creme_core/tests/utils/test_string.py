from django.utils.translation import pgettext

from creme.creme_core.utils.string import multi_truncate, smart_split

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
