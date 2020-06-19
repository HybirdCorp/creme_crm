# -*- coding: utf-8 -*-

from .base import CremeTestCase


class BaseTestCaseTestCase(CremeTestCase):
    def test_assertCountOccurrences(self):
        self.assertCountOccurrences('foo', 'foobarbaz', 1)
        self.assertCountOccurrences('bar', 'foobarbazbar', 2)

        with self.assertRaises(self.failureException) as cm:
            self.assertCountOccurrences('foo', 'foobarbaz', 2)
        self.assertEqual(
            "'foo' found 1 time(s) in 'foobarbaz' (2 expected)",
            str(cm.exception)
        )

        with self.assertRaises(self.failureException) as cm:
            self.assertCountOccurrences('bar', 'whatever', 1, msg='bad data')
        self.assertEqual(
            "'bar' found 0 time(s) in 'whatever' (1 expected) : bad data",
            str(cm.exception)
        )

    def test_assertFound(self):
        idx1 = self.assertFound('bar', 'foobar')
        self.assertEqual(3, idx1)

        idx2 = self.assertFound('baz', 'foobarbazqux')
        self.assertEqual(6, idx2)

        with self.assertRaises(self.failureException) as cm:
            self.assertFound('bar', 'foo')
        self.assertEqual(
            "'bar' not found in 'foo'",
            str(cm.exception)
        )

        with self.assertRaises(self.failureException) as cm:
            self.assertFound('bar', 'foo', msg='bad data')
        self.assertEqual(
            "'bar' not found in 'foo' : bad data",
            str(cm.exception)
        )

    def test_assertIndex(self):
        idx1 = self.assertIndex(2, [1, 2, 3])
        self.assertEqual(1, idx1)

        idx2 = self.assertIndex('baz', ['foo', 'bar', 'baz'])
        self.assertEqual(2, idx2)

        with self.assertRaises(self.failureException) as cm:
            self.assertIndex(4, [1, 2, 3])
        self.assertEqual(
            "4 not found in [1, 2, 3]",
            str(cm.exception)
        )

    def test_assertIsSubclass(self):
        class A:
            pass

        class B:
            pass

        class C(A):
            pass

        self.assertIsSubclass(C, A)

        with self.assertRaises(self.failureException) as cm:
            self.assertIsSubclass(B, A)
        self.assertEqual(
            "<class 'creme.creme_core.tests.test_base_test_case.BaseTestCaseTestCase.test_assertIsSubclass.<locals>.B'> "
            "is not a subclass of <class 'creme.creme_core.tests.test_base_test_case.BaseTestCaseTestCase.test_assertIsSubclass.<locals>.A'> "
            "[list of parent classes "
            "(<class 'creme.creme_core.tests.test_base_test_case.BaseTestCaseTestCase.test_assertIsSubclass.<locals>.B'>, "
            "<class 'object'>)]",
            str(cm.exception)
        )

    def test_assertListContainsSubset01(self):
        self.assertListContainsSubset(
            actual=[1, 2, 3, 4],
            expected=[1, 2],
        )
        self.assertListContainsSubset(
            actual=[1, 2, 3, 4],
            expected=[2, 3],
        )

        with self.assertRaises(self.failureException) as cm:
            self.assertListContainsSubset(
                actual=[1, 2, 4],
                expected=[2, 3],
            )
        self.assertEqual(
            'Element not found in the superset : "3"',
            str(cm.exception)
        )

        with self.assertRaises(self.failureException) as cm:
            self.assertListContainsSubset(
                actual=[1, 3, 2],
                expected=[2, 3],
            )
        self.assertEqual(
            'Order is different in the superset (problem with element : "3")',
            str(cm.exception)
        )

    def test_assertListContainsSubset02(self):
        "<msg> argument."
        with self.assertRaises(self.failureException) as cm:
            self.assertListContainsSubset(
                actual=[1, 2, 4],
                expected=[2, 3],
                msg='bad data',
            )
        self.assertEqual(
            'Element not found in the superset : "3" : bad data',
            str(cm.exception)
        )

        with self.assertRaises(self.failureException) as cm:
            self.assertListContainsSubset(
                actual=[1, 3, 2],
                expected=[2, 3],
                msg='bad data',
            )
        self.assertEqual(
            'Order is different in the superset (problem with element : "3") : bad data',
            str(cm.exception)
        )

# TODO: complete
#   assertDatetimesAlmostEqual
#   assertDoesNotExist
#   assertStillExists
#   assertGETXXX
#   assertPOSTXXX
#   assertNoException
#   assertInChoices
#   assertNotInChoices
#   assertFormInstanceErrors
#   assertNoFormError
#   assertNoFormsetError
#   assertNoWizardFormError
#   assertQuerysetSQLEqual
#   assertQEqual
#   assertSameProperties
#   assertSameRelations
#   assertSameRelationsNProperties
#   assertXMLEqualv2
#   get_object_or_fail
#   get_choices_group_or_fail
#   get_deletion_command_or_fail
#   get_relationtype_or_fail
#   get_propertytype_or_fail
