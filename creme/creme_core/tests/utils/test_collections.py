# -*- coding: utf-8 -*-

from creme.creme_core.utils.collections import (
    ClassKeyedMap,
    FluentList,
    InheritedDataChain,
    LimitedList,
    OrderedSet,
)

from ..base import CremeTestCase


class LimitedListTestCase(CremeTestCase):
    def test_main(self):
        ll = LimitedList(3)
        self.assertEqual(0, len(ll))
        self.assertListEqual([], [*ll])
        self.assertIs(False, bool(ll))

        ll.append(5)
        self.assertEqual(1, len(ll))
        self.assertListEqual([5], [*ll])
        self.assertIs(True, bool(ll))

        ll.append('6')
        self.assertEqual(2, len(ll))
        self.assertListEqual([5, '6'], [*ll])

        ll.append(7)
        ll.append(8)
        self.assertEqual(4, len(ll))
        self.assertListEqual([5, '6', 7], [*ll])


class FluentListTestCase(CremeTestCase):
    def test_inherited(self):
        flist = FluentList([1, 2])
        self.assertTrue(flist)
        self.assertEqual(2, len(flist))
        self.assertEqual(2, flist[1])

        with self.assertRaises(ValueError):
            flist.index(3)

        flist.append(3)
        self.assertEqual(3, len(flist))
        self.assertEqual(2, flist.index(3))

        flist.remove(2)
        self.assertEqual([1, 3], flist)

        flist.insert(1, 2)
        self.assertEqual([1, 2, 3], flist)

        flist.clear()
        self.assertFalse(flist)

    def test_append(self):
        "Fluent way."
        flist = FluentList([1]).append(2).append(3)
        self.assertIsInstance(flist, FluentList)
        self.assertEqual([1, 2, 3], flist)

    def test_remove(self):
        "Fluent way."
        flist = FluentList([1, 2, 3]).remove(2)
        self.assertIsInstance(flist, FluentList)
        self.assertEqual([1, 3], flist)

    def test_extend(self):
        "Fluent way."
        flist = FluentList(['1']).extend(['2', '3'])
        self.assertIsInstance(flist, FluentList)
        self.assertEqual(['1', '2', '3'], flist)

    def test_insert(self):
        "Fluent way."
        flist = FluentList([1, 3]).insert(1, 2)
        self.assertIsInstance(flist, FluentList)
        self.assertEqual([1, 2, 3], flist)

    def test_clear(self):
        "Fluent way."
        flist = FluentList([2, 1]).clear()
        self.assertIsInstance(flist, FluentList)
        self.assertFalse(flist)

    def test_sort(self):
        "Fluent way."
        flist = FluentList([2, 1, 3]).sort()
        self.assertIsInstance(flist, FluentList)
        self.assertEqual([1, 2, 3], flist)

    def test_reverse(self):
        "Fluent way."
        flist = FluentList([2, 1, 3]).reverse()
        self.assertIsInstance(flist, FluentList)
        self.assertEqual([3, 1, 2], flist)

    def test_replace01(self):
        flist = FluentList([1, 2])
        flist.replace(old=1, new=3)
        self.assertEqual([3, 2], flist)

    def test_replace02(self):
        "Other index."
        flist = FluentList([1, 2])
        flist.replace(old=2, new=3)
        self.assertEqual([1, 3], flist)

    def test_replace03(self):
        "Not found."
        flist = FluentList([1])

        with self.assertRaises(ValueError):
            flist.replace(old=2, new=3)


class ClassKeyedMapTestCase(CremeTestCase):
    def test_main(self):
        class Klass1:
            pass

        class Klass2:
            pass

        class Klass3:
            pass

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
        self.assertSetEqual(keys_set, {*ckm})
        self.assertSetEqual(keys_set, {*ckm.keys()})

        self.assertSetEqual({1, 2, None}, {*ckm.values()})
        self.assertSetEqual(
            {(Klass1, 1), (Klass2, 2), (Klass3, None)}, {*ckm.items()}
        )

        self.assertStartsWith(repr(ckm), 'ClassKeyedMap(')

    def test_setitem(self):
        "Other default value + __setitem__."
        class Klass1:
            pass

        class Klass2:
            pass

        class Klass3:
            pass

        ckm = ClassKeyedMap(default=0)

        result = ckm[Klass1] = 1
        ckm[Klass2] = 2

        self.assertEqual(0, ckm[Klass3])
        self.assertEqual(1, ckm[Klass1])
        self.assertEqual(1, result)
        self.assertEqual(3, len(ckm))

        self.assertEqual(0, ckm[Klass3])  # 2nd access should hit the cache
        self.assertEqual(3, len(ckm))

    def test_inheritage01(self):
        "Inheriting values."
        class Klass1:
            pass

        class Klass2:
            pass

        class Klass3(Klass2):
            pass

        class Klass4(Klass3):
            pass

        ckm = ClassKeyedMap([(Klass1, 1), (Klass2, 2)])

        self.assertEqual(2, ckm[Klass3])
        self.assertEqual(2, ckm[Klass4])

        ckm[Klass3] = 3

        self.assertEqual(3, ckm[Klass3])
        self.assertEqual(3, ckm[Klass4])  # Cache must be updated

    def test_inheritage02(self):
        "Inheriting values: more complex case (the nearest parent should be found)."
        class Klass1:
            pass

        class Klass2(Klass1):
            pass

        class Klass3(Klass2):
            pass

        class Klass4(Klass3):
            pass

        ckm = ClassKeyedMap(
            [(Klass1, 1), (Klass2, 2), (Klass3, 3), (Klass4, 4)],
            default=0,
        )

        class Klass5(Klass4):
            pass

        self.assertEqual(4, ckm[Klass5])

    def test_inheritage03(self):
        "Inheritance order must be kept when cache is filled too."
        class Klass1:
            pass

        class Klass2(Klass1):
            pass

        class Klass3(Klass2):
            pass

        class Klass4(Klass3):
            pass

        ckm = ClassKeyedMap(
            [(Klass1, 1), (Klass3, 3)],  # Not 2 & 4
            default=0,
        )

        self.assertEqual(1, ckm[Klass2])
        self.assertEqual(3, ckm[Klass4])

    def test_nearest_parent_class(self):
        "Inheritance order must be kept when new value are added explicitly."
        class Klass1:
            pass

        class Klass2(Klass1):
            pass

        class Klass3(Klass2):
            pass

        class Klass4(Klass3):
            pass

        nearest = ClassKeyedMap._nearest_parent_class
        self.assertIs(Klass3, nearest(Klass4, [Klass3]))
        self.assertIs(Klass3, nearest(Klass4, [Klass3, Klass1]))
        self.assertIs(Klass3, nearest(Klass4, [Klass2, Klass3, Klass1]))
        self.assertIs(Klass2, nearest(Klass4, [Klass2, Klass1]))
        self.assertIs(Klass1, nearest(Klass4, [Klass1]))

        class Klass5(Klass4):
            pass

        self.assertIs(Klass3, nearest(Klass4, [Klass2, Klass5, Klass3, Klass1]))

        class Klass6:
            pass

        self.assertIs(Klass3, nearest(Klass4, [Klass2, Klass5, Klass3, Klass6, Klass1]))


class InheritedDataChainTestCase(CremeTestCase):
    def test_get_item(self):
        class Klass1:
            pass

        class Klass2:
            pass

        class InnerClass:
            pass

        idc = InheritedDataChain(InnerClass)

        with self.assertNoException():
            instance1 = idc[Klass1]

        self.assertIsInstance(instance1, InnerClass)
        self.assertIs(instance1, idc[Klass1])

        instance2 = idc[Klass2]
        self.assertIsInstance(instance2, InnerClass)
        self.assertIsNot(instance1, instance2)

        # Bad value key
        with self.assertRaises(ValueError):
            idc[1]  # NOQA

    def test_chain01(self):
        class Klass1:
            pass

        class Klass2:
            pass

        class InnerClass:
            pass

        idc = InheritedDataChain(InnerClass)

        with self.assertNoException():
            chain1 = [*idc.chain(Klass1)]

        self.assertFalse(chain1)

        instance1 = idc[Klass1]
        chain1 = [*idc.chain(Klass1)]
        self.assertEqual(1, len(chain1))
        self.assertIs(instance1, chain1[0])
        self.assertIs(instance1, next(idc.chain(Klass1)))

        instance2 = idc[Klass2]
        self.assertListEqual([instance2], [*idc.chain(Klass2)])

    def test_chain02(self):
        "Inheritance."
        class Klass1:
            pass

        class Klass2(Klass1):
            pass

        class Klass3(Klass2):
            pass

        class InnerClass:
            data = None

            def __repr__(self):
                return f'InnerClass(data={self.data})'

        idc = InheritedDataChain(InnerClass)
        instance1 = idc[Klass1]
        instance1.data = Klass1.__name__
        instance2 = idc[Klass2]
        instance2.data = Klass2.__name__
        self.assertListEqual(
            [instance1, instance2], [*idc.chain(Klass2)],
        )

        instance3 = idc[Klass3]
        instance3.data = Klass3.__name__
        self.assertListEqual(
            [instance1, instance2, instance3], [*idc.chain(Klass3)],
        )

        # Reversed
        self.assertListEqual(
            [instance3, instance2, instance1],
            [*idc.chain(Klass3, parent_first=False)],
        )

    def test_get(self):
        class Klass1:
            pass

        class InnerClass:
            pass

        idc = InheritedDataChain(InnerClass)
        self.assertIsNone(idc.get(Klass1))
        self.assertEqual(-1, idc.get(Klass1, -1))

        instance1 = idc[Klass1]
        self.assertEqual(instance1, idc.get(Klass1))

    def test_del(self):
        class Klass1:
            pass

        class InnerClass:
            pass

        idc = InheritedDataChain(InnerClass)
        __ = idc[Klass1]  # NOQA

        del idc[Klass1]
        self.assertIsNone(idc.get(Klass1))

    def test_contains(self):
        class Klass1:
            pass

        class Klass2:
            pass

        class InnerClass:
            pass

        idc = InheritedDataChain(InnerClass)
        self.assertNotIn(Klass1, idc)
        self.assertNotIn(Klass2, idc)
        self.assertNotIn(1,      idc)

        __ = idc[Klass1]  # NOQA
        self.assertIn(Klass1, idc)
        self.assertNotIn(Klass2, idc)


class OrderedSetTestCase(CremeTestCase):
    def test_main(self):
        s1 = OrderedSet('Futurama')
        self.assertListEqual(['F', 'u', 't', 'r', 'a', 'm'], [*s1])

        s2 = OrderedSet([2, 1, 6, 5, 4, 6, 5, 4, 2, 1])
        self.assertListEqual([2, 1, 6, 5, 4], [*s2])

    def test_operator01(self):
        "| operator and __eq__."
        s3 = OrderedSet('Futurama') | OrderedSet('Simpsons')
        self.assertIsInstance(s3, OrderedSet)

        content = ['F', 'u', 't', 'r', 'a', 'm', 'S', 'i', 'p', 's', 'o', 'n']
        self.assertListEqual(content, [*s3])
        self.assertEqual(OrderedSet(content), s3)

        new_content = [*content]
        new_content[3], new_content[4] = new_content[4], new_content[3]
        self.assertNotEqual(OrderedSet(new_content), s3)

        self.assertNotEqual(OrderedSet(content[:-1]), s3)

    def test_operator02(self):
        "& operator."
        s3 = OrderedSet('Groening') & OrderedSet('Simpsons')
        self.assertIsInstance(s3, OrderedSet)
        self.assertListEqual(['i', 'o', 'n'], [*s3])

    def test_operator03(self):
        "- operator."
        s3 = OrderedSet('Groening') | OrderedSet('Simpsons')
        self.assertIsInstance(s3, OrderedSet)
        self.assertListEqual(
            ['G', 'r', 'o', 'e', 'n', 'i', 'g', 'S', 'm', 'p', 's'], [*s3]
        )

    def test_eq(self):
        "__eq__ with a list"
        s = OrderedSet('Futurama')
        self.assertEqual(s, ['F', 'u', 't', 'r', 'a', 'm'])
        self.assertEqual(s, ['u', 't', 'r', 'a', 'm', 'F'])
        self.assertNotEqual(s, ['u', 't', 'r', 'a', 'm'])

    def test_discard(self):
        s = OrderedSet('Futurama')

        with self.assertNoException():
            s.discard('z')

        s.discard('a')
        self.assertListEqual(['F', 'u', 't', 'r', 'm'], [*s])

    def test_reversed(self):
        s = OrderedSet('Futurama')
        self.assertListEqual(['m', 'a', 'r', 't', 'u', 'F'], [*reversed(s)])

    def test_pop01(self):
        with self.assertRaises(KeyError):
            OrderedSet().pop()

    def test_pop02(self):
        s = OrderedSet('Futurama')
        self.assertEqual('m', s.pop())
        self.assertListEqual(['F', 'u', 't', 'r', 'a'], [*s])

        self.assertEqual('F', s.pop(last=False))
        self.assertListEqual(['u', 't', 'r', 'a'], [*s])

    def test_repr(self):
        self.assertEqual('OrderedSet()', repr(OrderedSet()))
        self.assertEqual("OrderedSet(['F', 'r', 'y'])", repr(OrderedSet('Fry')))
