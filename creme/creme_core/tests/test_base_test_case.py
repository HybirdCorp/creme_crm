from datetime import date, datetime, timedelta

from django import forms
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.utils.translation import override as override_language

from .base import CremeTestCase
from .fake_models import FakeSector


class BaseTestCaseTestCase(CremeTestCase):
    def test_assertNoException(self):
        with self.assertNoException():
            pass

        # ---
        def foo(a, b):
            return a + b

        result = self.assertNoException(foo, 1, b=2)
        self.assertEqual(3, result)

        # ---
        msg = 'on fire'
        with self.assertRaises(self.failureException) as cm1:
            with self.assertNoException():
                raise ValueError(msg)
        self.assertEqual(
            f'An exception <ValueError> occurred: {msg}',
            str(cm1.exception),
        )

        # ---
        def fails():
            raise ValueError(msg)

        with self.assertRaises(self.failureException) as cm2:
            self.assertNoException(fails)
        self.assertEqual(
            f'An exception <ValueError> occurred: {msg}',
            str(cm2.exception),
        )

    def test_assertHasAttr(self):
        self.assertHasAttr(1, 'bit_length')
        self.assertHasAttr([], 'append')

        with self.assertRaises(self.failureException) as cm1:
            self.assertHasAttr(1, 'invalid')
        self.assertEqual(
            '<1> has no attribute named "invalid".',
            str(cm1.exception),
        )

        with self.assertRaises(self.failureException) as cm2:
            self.assertHasAttr([], 'unknown')
        self.assertEqual(
            '<[]> has no attribute named "unknown".',
            str(cm2.exception),
        )

    def test_assertHasNoAttr(self):
        self.assertHasNoAttr(1, 'invalid')
        self.assertHasNoAttr([], 'unknown')

        with self.assertRaises(self.failureException) as cm1:
            self.assertHasNoAttr(1, 'bit_length')
        self.assertEqual(
            '<1> has unexpectedly an attribute named "bit_length".',
            str(cm1.exception),
        )

        with self.assertRaises(self.failureException) as cm2:
            self.assertHasNoAttr([], 'append')
        self.assertEqual(
            '<[]> has unexpectedly an attribute named "append".',
            str(cm2.exception),
        )

    def test_assertCountOccurrences(self):
        self.assertCountOccurrences('foo', 'foobarbaz', 1)
        self.assertCountOccurrences('bar', 'foobarbazbar', 2)

        with self.assertRaises(self.failureException) as cm:
            self.assertCountOccurrences('foo', 'foobarbaz', 2)
        self.assertEqual(
            "'foo' found 1 time(s) in 'foobarbaz' (2 expected)",
            str(cm.exception),
        )

        with self.assertRaises(self.failureException) as cm:
            self.assertCountOccurrences('bar', 'whatever', 1, msg='bad data')
        self.assertEqual(
            "'bar' found 0 time(s) in 'whatever' (1 expected) : bad data",
            str(cm.exception),
        )

    def test_assertDatetimesAlmostEqual(self):
        dt = datetime(year=2021, month=9, day=20, hour=14, minute=15, second=13)

        self.assertDatetimesAlmostEqual(dt, dt + timedelta(seconds=10))
        self.assertDatetimesAlmostEqual(dt, dt + timedelta(seconds=11), seconds=11)

        with self.assertRaises(self.failureException) as cm:
            self.assertDatetimesAlmostEqual(dt, dt + timedelta(seconds=11))
        self.assertEqual(
            '<2021-09-20 14:15:13> & <2021-09-20 14:15:24> are not almost equal: '
            'delta is <0:00:11>',
            str(cm.exception),
        )

    def test_assertDoesNotExist(self):
        instance = FakeSector.objects.create(title='Delete me')

        with self.assertRaises(self.failureException) as cm:
            self.assertDoesNotExist(instance)
        self.assertEqual('Your object still exists.', str(cm.exception))

        FakeSector.objects.filter(id=instance.id).delete()
        self.assertDoesNotExist(instance)

    def test_assertStillExists(self):
        instance = FakeSector.objects.create(title='Delete me')
        self.assertStillExists(instance)

        FakeSector.objects.filter(id=instance.id).delete()

        with self.assertRaises(self.failureException) as cm:
            self.assertStillExists(instance)
        self.assertEqual('Your object does not exist any more.', str(cm.exception))

    def test_assertFound(self):
        idx1 = self.assertFound('bar', 'foobar')
        self.assertEqual(3, idx1)

        idx2 = self.assertFound('baz', 'foobarbazqux')
        self.assertEqual(6, idx2)

        with self.assertRaises(self.failureException) as cm1:
            self.assertFound('bar', 'foo')
        self.assertEqual(
            "'bar' not found in 'foo'",
            str(cm1.exception),
        )

        with self.assertRaises(self.failureException) as cm2:
            self.assertFound('bar', 'foo', msg='bad data')
        self.assertEqual(
            "'bar' not found in 'foo' : bad data",
            str(cm2.exception),
        )

    def test_assertInChoices(self):
        choices = [(1, 'one'), (2, 'two')]
        self.assertInChoices(1, 'one', choices)
        self.assertInChoices(value=2, label='two', choices=choices)

        # ---
        with self.assertRaises(self.failureException) as cm1:
            self.assertInChoices(3, 'three', choices)
        self.assertEqual(
            'The choice "3" has not been found in [1, 2].',
            str(cm1.exception),
        )

        # ---
        with self.assertRaises(self.failureException) as cm2:
            self.assertInChoices(1, 'three', choices)
        self.assertEqual(
            'The choice "1" has been found, but with the label "one", not "three".',
            str(cm2.exception),
        )

    def test_assertNotInChoices(self):
        choices = [(1, 'one'), (2, 'two')]
        self.assertNotInChoices(3, choices)
        self.assertNotInChoices(value=4, choices=choices)

        with self.assertRaises(self.failureException) as cm1:
            self.assertNotInChoices(1, choices)
        self.assertEqual(
            'The choice "1" has been unexpectedly found with label="one".',
            str(cm1.exception),
        )

    def test_assertFormInstanceErrors(self):
        class MyForm(forms.Form):
            name = forms.CharField()
            extra = forms.CharField(required=False, max_length=3)

        form1 = MyForm(data={})
        self.assertFormInstanceErrors(form1, ('name', _('This field is required.')))

        # ---
        form2 = MyForm(data={'name': 'foo'})
        with self.assertRaises(self.failureException) as cm2:
            self.assertFormInstanceErrors(form2, ('extra', 'What ever'))
        self.assertEqual(
            'The error "extra" has not been found in the form (fields: [])',
            str(cm2.exception),
        )

        # ---
        msg = 'Bad error message.'
        with self.assertRaises(self.failureException) as cm2:
            self.assertFormInstanceErrors(form1, ('name', msg))
        self.assertEqual(
            'The error "{}" has not been found in the field errors '
            '(<ul class="errorlist"><li>{}</li></ul>)'.format(
                msg,
                _('This field is required.'),
            ),
            str(cm2.exception),
        )

        # ---
        value = 'ths value is too long'
        form3 = MyForm(data={'extra': value})
        with self.assertRaises(self.failureException) as cm3:
            self.assertFormInstanceErrors(form3, ('name', _('This field is required.')))
        self.assertEqual(
            "Unexpected errors have been found in the form: {}".format([
                (
                    'extra',
                    [
                        ngettext(
                            'Ensure this value has at most %(limit_value)d character '
                            '(it has %(show_value)d).',
                            'Ensure this value has at most %(limit_value)d characters '
                            '(it has %(show_value)d).',
                            3
                        ) % {
                            'limit_value': 3,
                            'show_value': len(value),
                        },
                    ]
                ),
            ]),
            str(cm3.exception),
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
            "<class 'creme.creme_core.tests.test_base_test_case.BaseTestCaseTestCase."
            "test_assertIsSubclass.<locals>.B'> is not a subclass of <class "
            "'creme.creme_core.tests.test_base_test_case.BaseTestCaseTestCase."
            "test_assertIsSubclass.<locals>.A'> "
            "[list of parent classes "
            "(<class 'creme.creme_core.tests.test_base_test_case.BaseTestCaseTestCase."
            "test_assertIsSubclass.<locals>.B'>, "
            "<class 'object'>)]",
            str(cm.exception),
        )

        msg = 'My message'
        with self.assertRaises(self.failureException) as cm:
            self.assertIsSubclass(B, A, msg=msg)
        self.assertEqual(msg, str(cm.exception))

    def test_assertIsList(self):
        empty_list = []
        self.assertIsList(empty_list)

        with self.assertRaises(self.failureException) as cm1:
            self.assertIsList(())
        self.assertEqual(
            "() is not an instance of <class 'list'>",
            str(cm1.exception),
        )

        # ---
        self.assertIsList(empty_list, length=0)

        self.assertIsList(empty_list, max_length=0)
        self.assertIsList(empty_list, max_length=1)

        self.assertIsList(empty_list, min_length=0)

        with self.assertRaises(ValueError) as cm2:
            self.assertIsList(empty_list, invalid=12)
        self.assertEqual(
            'assertIsList: unknown argument "invalid"',
            str(cm2.exception),
        )

        # ---
        list1 = [1]
        self.assertIsList(list1, length=1)
        self.assertIsList(list1, max_length=1)

        self.assertIsList(list1, min_length=0)
        self.assertIsList(list1, min_length=1)

        # ---
        with self.assertRaises(self.failureException) as cm3:
            self.assertIsList(empty_list, length=1)
        self.assertEqual(
            'This list has not the expected length of 1: []',
            str(cm3.exception),
        )

        with self.assertRaises(self.failureException) as cm4:
            self.assertIsList(list1, max_length=0)
        self.assertEqual(
            'This list is not shorter than 0: [1]',
            str(cm4.exception),
        )

        with self.assertRaises(self.failureException) as cm5:
            self.assertIsList(empty_list, min_length=1)
        self.assertEqual(
            'This list is not longer than 1: []',
            str(cm5.exception),
        )

    def test_assertIsDict(self):
        empty_dict = {}
        self.assertIsDict(empty_dict)

        with self.assertRaises(self.failureException) as cm1:
            self.assertIsDict(())
        self.assertEqual(
            "() is not an instance of <class 'dict'>",
            str(cm1.exception),
        )

        # ---
        self.assertIsDict(empty_dict, length=0)

        self.assertIsDict(empty_dict, max_length=0)
        self.assertIsDict(empty_dict, max_length=1)

        self.assertIsDict(empty_dict, min_length=0)

        with self.assertRaises(ValueError) as cm2:
            self.assertIsDict(empty_dict, invalid=12)
        self.assertEqual(
            'assertIsDict: unknown argument "invalid"',
            str(cm2.exception),
        )

        # ---
        dict1 = {1: 'a'}
        self.assertIsDict(dict1, length=1)
        self.assertIsDict(dict1, max_length=1)

        self.assertIsDict(dict1, min_length=0)
        self.assertIsDict(dict1, min_length=1)

        # ---
        with self.assertRaises(self.failureException) as cm3:
            self.assertIsDict(empty_dict, length=1)
        self.assertEqual(
            'This dict has not the expected length of 1: {}',
            str(cm3.exception),
        )

        with self.assertRaises(self.failureException) as cm4:
            self.assertIsDict(dict1, max_length=0)
        self.assertEqual(
            "This dict is not shorter than 0: {1: 'a'}",
            str(cm4.exception),
        )

        with self.assertRaises(self.failureException) as cm5:
            self.assertIsDict(empty_dict, min_length=1)
        self.assertEqual(
            'This dict is not longer than 1: {}',
            str(cm5.exception),
        )

    def test_assertIsTuple(self):
        self.assertIsTuple((),     length=0)
        self.assertIsTuple((1,),   length=1)
        self.assertIsTuple((1, 2), length=2)

        with self.assertRaises(self.failureException) as cm1:
            self.assertIsTuple([], length=0)
        self.assertEqual(
            "[] is not an instance of <class 'tuple'>",
            str(cm1.exception),
        )

        with self.assertRaises(self.failureException) as cm2:
            self.assertIsTuple((1, 2), length=1)
        self.assertEqual(
            'This tuple has not the expected length of 1: (1, 2)',
            str(cm2.exception),
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

    def test_assertStartsWith(self):
        self.assertStartsWith('Hello world', 'Hello')
        self.assertStartsWith('foobar', 'foo')

        with self.assertRaises(self.failureException) as cm:
            self.assertStartsWith('Hello world', 'foo')
        self.assertEqual(
            "The string 'Hello world' does not start with 'foo'",
            str(cm.exception),
        )

    def test_assertEndsWith(self):
        self.assertEndsWith('Hello world', 'orld')
        self.assertEndsWith('foobar', 'bar')

        with self.assertRaises(self.failureException) as cm:
            self.assertEndsWith('Hello world', 'bar')
        self.assertEqual(
            "The string 'Hello world' does not end with 'bar'",
            str(cm.exception),
        )

    def test_get_alone_element(self):
        with self.assertNoException():
            e1 = self.get_alone_element([1])
        self.assertEqual(1, e1)

        # Other value returned ---
        with self.assertNoException():
            e2 = self.get_alone_element(['2'])
        self.assertEqual('2', e2)

        # Failure with list + length==2 ---
        with self.assertRaises(self.failureException) as cm1:
            self.get_alone_element([1, 2])
        self.assertEqual(
            'The iterable has 2 elements, not 1',
            str(cm1.exception),
        )

        # Failure with range() + length==3 ---
        with self.assertRaises(self.failureException) as cm2:
            self.get_alone_element(range(1, 4))
        self.assertEqual(
            'The iterable has 3 elements, not 1',
            str(cm2.exception),
        )

        # Failure with generator ---
        with self.assertRaises(self.failureException) as cm3:
            self.get_alone_element(i * i for i in range(3))
        self.assertEqual(
            'The iterable has 3 elements, not 1',
            str(cm3.exception),
        )

    def test_get_object_or_fail(self):
        sector1 = FakeSector.objects.create(title='Catch me')

        sector2 = self.get_object_or_fail(FakeSector, id=sector1.id)
        self.assertEqual(sector1, sector2)

        sector3 = self.get_object_or_fail(FakeSector, title__startswith='Catch')
        self.assertEqual(sector1, sector3)

        # ---
        with self.assertRaises(self.failureException) as cm1:
            self.get_object_or_fail(FakeSector, title='I do not exist')
        self.assertEqual(
            "Your object does not exist.\n"
            " Query model: <class 'creme.creme_core.tests.fake_models.FakeSector'>\n"
            " Query args {'title': 'I do not exist'}\n"
            " [original exception: FakeSector matching query does not exist.]",
            str(cm1.exception),
        )

        # ---
        FakeSector.objects.create(title='Catch meeeeee')

        with self.assertRaises(self.failureException) as cm2:
            self.get_object_or_fail(FakeSector, title__startswith='Catch')
        self.assertEqual(
            'get() returned more than one FakeSector -- it returned 2!',
            str(cm2.exception),
        )

    def test_get_choices_group_or_fail(self):
        grouped_choices = [
            (
                'numbers',
                [(1, 'one'), (2, 'two')],
            ),
            (
                'colors',
                [('red', 'Red'), ('green', 'Green')],
            )
        ]

        choices1 = self.get_choices_group_or_fail('numbers', grouped_choices)
        self.assertListEqual([(1, 'one'), (2, 'two')], choices1)

        choices2 = self.get_choices_group_or_fail(label='colors', choices=grouped_choices)
        self.assertListEqual([('red', 'Red'), ('green', 'Green')], choices2)

        # ---
        label = 'unknown'
        with self.assertRaises(self.failureException) as cm:
            self.get_choices_group_or_fail(label, grouped_choices)
        self.assertEqual(f'Group "{label}" not found.', str(cm.exception))

    def test_formfield_value_date(self):
        date_obj = date(year=2022, month=2, day=24)

        with self.settings(USE_L10N=False, DATE_INPUT_FORMATS=['%Y-%m-%d', '%d/%m/%Y']):
            date_str1 = self.formfield_value_date(date_obj)
            date_str2 = self.formfield_value_date(2023, 6, 12)
        self.assertEqual('2022-02-24', date_str1)
        self.assertEqual('2023-06-12', date_str2)

        with self.settings(USE_L10N=True):
            with override_language('en'):
                date_str_en = self.formfield_value_date(date_obj)
            self.assertEqual('2022-02-24', date_str_en)

            with override_language('fr'):
                with self.settings(USE_L10N=True):
                    date_str_fr = self.formfield_value_date(date_obj)
            self.assertEqual('24/02/2022', date_str_fr)

    def test_formfield_value_datetime(self):
        date_obj = date(year=2022, month=2, day=24)
        dt_obj = datetime(year=2023, month=3, day=21, hour=18, minute=53)

        with self.settings(
            USE_L10N=False,
            DATE_INPUT_FORMATS=['%Y-%m-%d', '%d/%m/%Y'],
            DATETIME_INPUT_FORMATS=['%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M'],
        ):
            date_str1 = self.formfield_value_datetime(date_obj)
            dt_str1 = self.formfield_value_datetime(dt_obj)
            dt_str2 = self.formfield_value_datetime(
                year=2024, month=8, day=25, hour=19, minute=48,
            )

        self.assertEqual('2022-02-24', date_str1)
        self.assertEqual('2023-03-21 18:53:00', dt_str1)
        self.assertEqual('2024-08-25 19:48:00', dt_str2)

        with self.settings(USE_L10N=True):
            with override_language('en'):
                date_str_en = self.formfield_value_datetime(date_obj)
                dt_str_en = self.formfield_value_datetime(dt_obj)
            self.assertEqual('2022-02-24', date_str_en)
            self.assertEqual('2023-03-21 18:53:00', dt_str_en)

            with override_language('fr'):
                with self.settings(USE_L10N=True):
                    date_str_fr = self.formfield_value_datetime(date_obj)
                    dt_str_fr = self.formfield_value_datetime(dt_obj)
            self.assertEqual('24/02/2022', date_str_fr)
            self.assertEqual('21/03/2023 18:53:00', dt_str_fr)

# TODO: complete
#   assertGETXXX
#   assertPOSTXXX
#   assertNoFormError
#   assertNoFormsetError
#   assertNoWizardFormError
#   assertQuerysetSQLEqual
#   assertQEqual
#   assertSameProperties
#   assertSameRelations
#   assertSameRelationsNProperties
#   assertXMLEqualv2
#   get_deletion_command_or_fail
#   get_relationtype_or_fail
#   get_propertytype_or_fail
