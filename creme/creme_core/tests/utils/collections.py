# -*- coding: utf-8 -*-

try:
    from ..base import CremeTestCase
    from creme.creme_core.utils.collections import LimitedList, ClassKeyedMap, OrderedSet
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('LimitedListTestCase', 'ClassKeyedMapTestCase', 'OrderedSetTestCase')


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


class ClassKeyedMapTestCase(CremeTestCase):
    def test_main(self):
        class Klass1(object): pass
        class Klass2(object): pass
        class Klass3(object): pass

        ckm = ClassKeyedMap([(Klass1, 1), (Klass2, 2)])
        self.assertEqual(1, ckm[Klass1])
        self.assertEqual(2, ckm[Klass2])
        self.assertEqual(2, len(ckm))

        self.assertIsNone(ckm[Klass3])
        self.assertEqual(3, len(ckm))

        self.assertIsNone(ckm.default)

        self.assertTrue(hasattr(ckm, '__contains__'))
        self.assertIn(Klass1, ckm)

        empty = ClassKeyedMap()
        self.assertIs(True,  bool(ckm))
        self.assertIs(False, bool(empty))
        self.assertEqual(0, len(empty))
        self.assertNotIn(Klass1, empty)

        keys_set = {Klass1, Klass2, Klass3}
        self.assertEqual(keys_set, set(ckm))
        self.assertEqual(keys_set, set(ckm.keys()))

        self.assertEqual({1, 2, None}, set(ckm.values()))
        self.assertEqual({(Klass1, 1), (Klass2, 2), (Klass3, None)},
                         set(ckm.items())
                        )

        r = repr(ckm)
        self.assertTrue(r.startswith('ClassKeyedMap('))

    def test_setitem(self):
        "Other default value + __setitem__"
        class Klass1(object): pass
        class Klass2(object): pass
        class Klass3(object): pass

        ckm = ClassKeyedMap(default=0)

        result = ckm[Klass1] = 1
        ckm[Klass2] = 2

        self.assertEqual(0, ckm[Klass3])
        self.assertEqual(1, ckm[Klass1])
        self.assertEqual(1, result)
        self.assertEqual(3, len(ckm))

        self.assertEqual(0, ckm[Klass3]) #2nd access should hit the cache
        self.assertEqual(3, len(ckm))

    def test_inheritage01(self):
        "Inheriting values"
        class Klass1(object): pass
        class Klass2(object): pass
        class Klass3(Klass2): pass
        class Klass4(Klass3): pass

        ckm = ClassKeyedMap([(Klass1, 1), (Klass2, 2)])

        self.assertEqual(2, ckm[Klass3])
        self.assertEqual(2, ckm[Klass4])

        ckm[Klass3] = 3

        self.assertEqual(3, ckm[Klass3])
        self.assertEqual(3, ckm[Klass4]) #cache must be updated

    def test_inheritage02(self):
        "Inheriting values: more complex case (the nearest parent should be found)"
        class Klass1(object): pass
        class Klass2(Klass1): pass
        class Klass3(Klass2): pass
        class Klass4(Klass3): pass

        ckm = ClassKeyedMap([(Klass1, 1), (Klass2, 2), (Klass3, 3), (Klass4, 4)],
                             default=0
                            )

        class Klass5(Klass4): pass

        self.assertEqual(4, ckm[Klass5])

    def test_inheritage03(self):
        "Inheritance order must be kept when cache is filled too"
        class Klass1(object): pass
        class Klass2(Klass1): pass
        class Klass3(Klass2): pass
        class Klass4(Klass3): pass

        ckm = ClassKeyedMap([(Klass1, 1), (Klass3, 3)], #not 2 & 4
                             default=0
                            )

        self.assertEqual(1, ckm[Klass2])
        self.assertEqual(3, ckm[Klass4])

    def test_nearest_parent_class(self):
        "Inheritance order must be kept when new value are added explicitely"
        class Klass1(object): pass
        class Klass2(Klass1): pass
        class Klass3(Klass2): pass
        class Klass4(Klass3): pass

        nearest = ClassKeyedMap._nearest_parent_class
        self.assertIs(Klass3, nearest(Klass4, [Klass3]))
        self.assertIs(Klass3, nearest(Klass4, [Klass3, Klass1]))
        self.assertIs(Klass3, nearest(Klass4, [Klass2, Klass3, Klass1]))
        self.assertIs(Klass2, nearest(Klass4, [Klass2, Klass1]))
        self.assertIs(Klass1, nearest(Klass4, [Klass1]))

        class Klass5(Klass4): pass
        self.assertIs(Klass3, nearest(Klass4, [Klass2, Klass5, Klass3, Klass1]))

        class Klass6(object): pass
        self.assertIs(Klass3, nearest(Klass4, [Klass2, Klass5, Klass3, Klass6, Klass1]))


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
