# -*- coding: utf-8 -*-

try:
    from ..base import CremeTestCase
    from creme.creme_core.utils.collections import LimitedList, OrderedSet
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('LimitedListTestCase', 'OrderedSetTestCase')


class LimitedListTestCase(CremeTestCase):
    def test_main(self):
        ll = LimitedList(3)
        self.assertEqual(0, len(ll))
        self.assertEqual([], list(ll))
        self.assertIs(False, bool(ll))

        ll.append(5)
        self.assertEqual(1, len(ll))
        self.assertEqual([5], list(ll))
        self.assertIs(True, bool(ll))

        ll.append('6')
        self.assertEqual(2, len(ll))
        self.assertEqual([5, '6'], list(ll))

        ll.append(7)
        ll.append(8)
        self.assertEqual(4, len(ll))
        self.assertEqual([5, '6', 7], list(ll))


class OrderedSetTestCase(CremeTestCase):
    def test_main(self):
        s1 = OrderedSet('Futurama')
        self.assertEqual(['F','u', 't', 'r', 'a', 'm'], list(s1))

        s2 = OrderedSet([2, 1, 6, 5, 4, 6, 5, 4, 2, 1])
        self.assertEqual([2, 1, 6, 5, 4], list(s2))

    def test_operator01(self):
        "| operator and __eq__"
        s3 = OrderedSet('Futurama') | OrderedSet('Simpsons')
        self.assertIsInstance(s3, OrderedSet)

        content = ['F', 'u', 't', 'r', 'a', 'm', 'S', 'i', 'p', 's', 'o', 'n']
        self.assertEqual(content, list(s3))
        self.assertEqual(OrderedSet(content), s3)

        new_content = list(content)
        new_content[3], new_content[4] = new_content[4], new_content[3]
        self.assertNotEqual(OrderedSet(new_content), s3)

        self.assertNotEqual(OrderedSet(content[:-1]), s3)

    def test_operator02(self):
        "& operator"
        s3 = OrderedSet('Groening') & OrderedSet('Simpsons')
        self.assertIsInstance(s3, OrderedSet)
        self.assertEqual(['i', 'o', 'n'], list(s3))

    def test_operator03(self):
        "- operator"
        s3 = OrderedSet('Groening') | OrderedSet('Simpsons')
        self.assertIsInstance(s3, OrderedSet)
        self.assertEqual(['G', 'r', 'o', 'e', 'n', 'i', 'g', 'S', 'm', 'p', 's'],
                         list(s3)
                        )
