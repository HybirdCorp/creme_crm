from datetime import date, datetime, timedelta
from functools import partial
from uuid import UUID, uuid4

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.utils.translation import override as override_language

from ..auth import EntityCredentials
from ..models import (
    CremeProperty,
    CremePropertyType,
    CremeUser,
    FakeContact,
    FakeOrganisation,
    FakeSector,
    Relation,
    RelationType,
    SetCredentials,
    UserRole,
)
from .base import CremeTestCase


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
            '''The choice "3" has not been found in ['1', '2'].''',
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
        validation_msg = _('This field is required.')
        self.assertFormInstanceErrors(form1, ('name', validation_msg))

        # ---
        form2 = MyForm(data={'name': 'foo'})
        with self.assertRaises(self.failureException) as cm1:
            self.assertFormInstanceErrors(form2, ('extra', 'What ever'))
        self.assertEqual(
            'The error "extra" has not been found in the form (fields with errors: [])',
            str(cm1.exception),
        )

        # ---
        msg = 'Bad error message.'
        with self.assertRaises(self.failureException) as cm2:
            self.assertFormInstanceErrors(form1, ('name', msg))
        self.assertEqual(
            f'The error "{msg}" has not been found in the field errors '
            f'(<ul class="errorlist" id="id_name_error"><li>{validation_msg}</li></ul>)',
            str(cm2.exception),
        )

        # ---
        value = 'the value is too long'
        form3 = MyForm(data={'extra': value})
        with self.assertRaises(self.failureException) as cm3:
            self.assertFormInstanceErrors(form3, ('name', validation_msg))
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

    def test_assertValidationError01(self):
        err = ValidationError(message='Foo')
        self.assertValidationError(err, messages='Foo')
        self.assertValidationError(err, messages=['Foo'])
        self.assertValidationError(err, messages='Foo', codes=None)
        self.assertValidationError(err, messages='Foo', codes=[None])

        # ---
        with self.assertRaises(self.failureException) as cm1:
            self.assertValidationError(err, messages='Bar')
        self.assertEqual(
            "The messages differ. Expected: ['Bar']. Got: ['Foo']",
            str(cm1.exception),
        )

        # ---
        with self.assertRaises(self.failureException) as cm2:
            self.assertValidationError(err, messages='Foo', codes='bar')
        self.assertEqual(
            "The codes differ. Expected: ['bar']. Got: [None]",
            str(cm2.exception),
        )

        # ---
        with self.assertRaises(self.failureException) as cm3:
            self.assertValidationError(err, messages={'foo': 'Bar'})
        self.assertEqual(
            'The given exception does not use an error dictionary.',
            str(cm3.exception),
        )

    def test_assertValidationError02(self):
        err = ValidationError(message='Bar', code='invalid')
        self.assertValidationError(err, messages='Bar')
        self.assertValidationError(err, messages='Bar', codes='invalid')
        self.assertValidationError(err, messages=['Bar'], codes=['invalid'])

        # ---
        with self.assertRaises(self.failureException) as cm1:
            self.assertValidationError(err, messages='Bar', codes='bad_choice')
        self.assertEqual(
            "The codes differ. Expected: ['bad_choice']. Got: ['invalid']",
            str(cm1.exception),
        )

        # ---
        with self.assertRaises(self.failureException) as cm2:
            self.assertValidationError(err, messages='Bar', codes=['bad', 'choice'])
        self.assertEqual(
            "The codes differ. Expected: ['bad', 'choice']. Got: ['invalid']",
            str(cm2.exception),
        )

        # ---
        with self.assertRaises(TypeError) as cm3:
            self.assertValidationError(err, messages='Bar', codes={'choice': 'bad'})
        self.assertEqual(
            'The argument "codes" must be a list or a string in this case.',
            str(cm3.exception),
        )

    def test_assertValidationError03(self):
        err = ValidationError([
            ValidationError(message='Foo'), ValidationError(message='Bar', code='deleted'),
        ])
        self.assertValidationError(err, messages=['Foo', 'Bar'])
        self.assertValidationError(err, messages=['Foo', 'Bar'], codes=[None, 'deleted'])

        # ---
        with self.assertRaises(self.failureException) as cm1:
            self.assertValidationError(err, messages=['Baz'])
        self.assertEqual(
            "The messages differ. Expected: ['Baz']. Got: ['Foo', 'Bar']",
            str(cm1.exception),
        )

        # ---
        with self.assertRaises(self.failureException) as cm2:
            self.assertValidationError(err, messages=['Foo', 'Bar'], codes=['bad_choice'])
        self.assertEqual(
            "The codes differ. Expected: ['bad_choice']. Got: [None, 'deleted']",
            str(cm2.exception),
        )

    def test_assertValidationError04(self):
        err = ValidationError({
            'foo': 'Invalid foo',
            'bar': ValidationError(message='Bar', code='no_choice'),
        })
        self.assertValidationError(err, messages={'foo': 'Invalid foo', 'bar': 'Bar'})
        self.assertValidationError(
            err,
            messages={'foo': 'Invalid foo', 'bar': 'Bar'},
            codes={'foo': None, 'bar': 'no_choice'},
        )

        # ---
        with self.assertRaises(self.failureException) as cm1:
            self.assertValidationError(err, messages={'bar': 'Bar'})
        self.assertEqual(
            "The messages differ. "
            "Expected: {'bar': ['Bar']}. "
            "Got: {'foo': ['Invalid foo'], 'bar': ['Bar']}",
            str(cm1.exception),
        )

        # ---
        with self.assertRaises(self.failureException) as cm2:
            self.assertValidationError(
                err,
                messages={'foo': ['Invalid foo'], 'bar': ['Bar']},
                codes={'bar': 'no_choice'},
            )
        self.assertEqual(
            "The codes differ. "
            "Expected: {'bar': ['no_choice']}. "
            "Got: {'foo': [None], 'bar': ['no_choice']}",
            str(cm2.exception),
        )

        # ---
        with self.assertRaises(self.failureException) as cm3:
            self.assertValidationError(err, messages='Bar')
        self.assertEqual(
            'The given exception uses an error dictionary.',
            str(cm3.exception),
        )

        # ---
        with self.assertRaises(TypeError) as cm4:
            self.assertValidationError(
                err,
                messages={'foo': ['Invalid foo'], 'bar': ['Bar']},
                codes=['no_choice'],
            )
        self.assertEqual(
            'The argument "codes" must be a dictionary in this case.',
            str(cm4.exception),
        )

    def test_assertUUIDEqual(self):
        str_uid1 = '432469ec-8f93-4105-b2c8-5dda8b1d6a52'
        str_uid2 = '32f6ee9c-7204-4ebc-a9d1-8b8e19d9f8ed'

        with self.assertNoException():
            self.assertUUIDEqual(UUID(str_uid1), UUID(str_uid1))

        with self.assertNoException():
            self.assertUUIDEqual(UUID(str_uid2), UUID(str_uid2))

        with self.assertRaises(self.failureException) as cm1:
            self.assertUUIDEqual(UUID(str_uid1), UUID(str_uid2))
        self.assertEqual(
            f'The UUIDs are not equal: "{str_uid1}" != "{str_uid2}".',
            str(cm1.exception),
        )

        with self.assertNoException():
            self.assertUUIDEqual(str_uid1, UUID(str_uid1))

        with self.assertNoException():
            self.assertUUIDEqual(UUID(str_uid1), str_uid1)

        with self.assertNoException():
            self.assertUUIDEqual(str_uid1, str_uid1)

        with self.assertRaises(self.failureException) as cm2:
            self.assertUUIDEqual(str_uid1, str_uid2)
        self.assertEqual(
            f'The UUIDs are not equal: "{str_uid1}" != "{str_uid2}".',
            str(cm2.exception),
        )

        with self.assertRaises(self.failureException) as cm3:
            self.assertUUIDEqual(123654, str_uid2)
        self.assertEqual(
            "123654 is not an instance of <class 'uuid.UUID'>",
            str(cm3.exception),
        )

        with self.assertRaises(self.failureException) as cm4:
            self.assertUUIDEqual(str_uid1, 78965)
        self.assertEqual(
            "78965 is not an instance of <class 'uuid.UUID'>",
            str(cm4.exception),
        )

    def test_assertGET(self):
        self.login_as_standard()

        url404 = reverse('creme_core__view_fake_contact', args=(self.UNUSED_PK,))
        with self.assertRaises(self.failureException) as cm404:
            self.assertGET(200, url404)
        self.assertStartsWith(
            str(cm404.exception),
            'Expected status was <200>. Got status <404>. Content is ',
        )

        # -----------------------
        url403 = reverse('creme_core__create_fake_contact')
        with self.assertRaises(self.failureException) as cm403:
            self.assertGET(200, url403)
        self.assertStartsWith(
            str(cm403.exception),
            'Expected status was <200>. Got status <403>. Content is ',
        )

        # -----------------------
        with self.assertNoException():
            self.assertGET(200, reverse('creme_core__home'))

    def test_assertNoFormError(self):
        user = self.login_as_root_and_get()

        url = reverse('creme_core__create_fake_contact')
        response1 = self.client.post(url, data={'user': user.id}, follow=True)

        with self.assertRaises(self.failureException) as cm1:
            self.assertNoFormError(response1, status=404)

        self.assertStartsWith(str(cm1.exception), 'Response status=200 (expected: 404)')

        # ---
        with self.assertRaises(self.failureException) as cm2:
            self.assertNoFormError(response1)

        self.assertEqual(
            f'* last_name\n'
            f'  * {_("This field is required.")}',
            str(cm2.exception),
        )

        # ---
        response2 = self.client.post(
            url, data={'user': user.id, 'last_name': 'Doe'}, follow=True,
        )
        with self.assertNoException():
            self.assertNoFormError(response2)

    def test_assertHasProperty(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity1 = create_orga(name='TOA industries')
        entity2 = create_orga(name='DRF')

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Military')
        ptype2 = create_ptype(text='Hi-tech')

        create_prop = CremeProperty.objects.create
        create_prop(creme_entity=entity1, type=ptype2)
        create_prop(creme_entity=entity2, type=ptype1)

        # Failures -------------------------------------------------------------
        # Arguments are instances
        with self.assertRaises(self.failureException) as cm1:
            self.assertHasProperty(entity=entity1, ptype=ptype1)
        self.assertEqual(
            f'<{entity1.name}> has no property with type <{ptype1.text}>',
            str(cm1.exception),
        )

        # Arguments are IDs
        with self.assertRaises(self.failureException) as cm2:
            self.assertHasProperty(entity=entity1.id, ptype=ptype1.id)
        self.assertEqual(
            f'<{entity1.id}> has no property with type <{ptype1.id}>',
            str(cm2.exception),
        )

        # Argument is a UUID
        with self.assertRaises(self.failureException) as cm3:
            self.assertHasProperty(entity=entity1, ptype=str(ptype1.uuid))
        self.assertEqual(
            f'<{entity1}> has no property with type <{ptype1.uuid}>',
            str(cm3.exception),
        )

        # Successes ------------------------------------------------------------
        create_prop(creme_entity=entity1, type=ptype1)

        with self.assertNoException():
            self.assertHasProperty(entity=entity1, ptype=ptype1)

        with self.assertNoException():
            self.assertHasProperty(entity=entity1.id, ptype=ptype1.id)

        with self.assertNoException():
            self.assertHasProperty(entity=entity1, ptype=str(ptype1.uuid))

    def test_assertHasNoProperty(self):
        user = self.get_root_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity1 = create_orga(name='TOA industries')
        entity2 = create_orga(name='DRF')

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Military')
        ptype2 = create_ptype(text='Hi-tech')

        create_prop = CremeProperty.objects.create
        create_prop(creme_entity=entity1, type=ptype2)
        create_prop(creme_entity=entity2, type=ptype1)

        # Successes ------------------------------------------------------------
        with self.assertNoException():
            self.assertHasNoProperty(entity=entity1, ptype=ptype1)

        with self.assertNoException():
            self.assertHasNoProperty(entity=entity1.id, ptype=ptype1.id)

        with self.assertNoException():
            self.assertHasNoProperty(entity=entity1, ptype=str(ptype1.uuid))

        # Failures -------------------------------------------------------------
        create_prop(creme_entity=entity1, type=ptype1)

        # Arguments are instances
        with self.assertRaises(self.failureException) as cm1:
            self.assertHasNoProperty(entity=entity1, ptype=ptype1)
        self.assertEqual(
            f'<{entity1.name}> has property with type <{ptype1.text}>',
            str(cm1.exception),
        )

        # Arguments are IDs
        with self.assertRaises(self.failureException) as cm2:
            self.assertHasNoProperty(entity=entity1.id, ptype=ptype1.id)
        self.assertEqual(
            f'<{entity1.id}> has property with type <{ptype1.id}>',
            str(cm2.exception),
        )

        # Argument is a UUID
        with self.assertRaises(self.failureException) as cm3:
            self.assertHasNoProperty(entity=entity1, ptype=str(ptype1.uuid))
        self.assertEqual(
            f'<{entity1}> has property with type <{ptype1.uuid}>',
            str(cm3.exception),
        )

    def test_assertHaveRelation(self):
        user = self.get_root_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity1 = create_orga(name='TOA industries')
        entity2 = create_orga(name='DRF')
        entity3 = create_orga(name='Generator')

        rtype1 = RelationType.objects.builder(
            id='test-subject_foobar', predicate='is destroying',
        ).symmetric(
            id='test-object_foobar', predicate='is destroyed by',
        ).get_or_create()[0]
        rtype2 = rtype1.symmetric_type

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=entity1, type=rtype1, object_entity=entity2)
        create_rel(subject_entity=entity1, type=rtype2, object_entity=entity3)

        with self.assertNoException():
            self.assertHaveRelation(entity1, rtype1, entity2)

        with self.assertNoException():
            self.assertHaveRelation(subject=entity1, type=rtype1, object=entity2)

        with self.assertNoException():
            self.assertHaveRelation(subject=entity1.id, type=rtype1.id, object=entity2.id)

        with self.assertRaises(self.failureException) as cm1:
            self.assertHaveRelation(entity1, rtype2, entity2)
        self.assertEqual(
            f'<{entity1}> is not related to <{entity2}> with type <{rtype2}>',
            str(cm1.exception),
        )

        with self.assertRaises(self.failureException):
            self.assertHaveRelation(subject=entity1.id, type=rtype2.id, object=entity2.id)

    def test_assertHaveNoRelation(self):
        user = self.get_root_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity1 = create_orga(name='TOA industries')
        entity2 = create_orga(name='DRF')
        entity3 = create_orga(name='Generator')

        rtype1 = RelationType.objects.builder(
            id='test-subject_foobar', predicate='is destroying',
        ).symmetric(id='test-object_foobar', predicate='is destroyed by').get_or_create()[0]
        rtype2 = rtype1.symmetric_type

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=entity1, type=rtype1, object_entity=entity2)
        create_rel(subject_entity=entity1, type=rtype2, object_entity=entity3)

        with self.assertNoException():
            self.assertHaveNoRelation(entity1, rtype2, entity2)

        with self.assertNoException():
            self.assertHaveNoRelation(subject=entity1, type=rtype2, object=entity2)

        with self.assertNoException():
            self.assertHaveNoRelation(subject=entity1.id, type=rtype2.id, object=entity2.id)

        with self.assertRaises(self.failureException) as cm1:
            self.assertHaveNoRelation(entity1, rtype1, entity2)
        self.assertEqual(
            f'<{entity1}> is related to <{entity2}> with type <{rtype1}>',
            str(cm1.exception),
        )

        with self.assertRaises(self.failureException):
            self.assertHaveNoRelation(subject=entity1.id, type=rtype1.id, object=entity2.id)

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

    def test_get_relationtype_or_fail(self):
        type_id = 'test-subject_testbase'
        sym_type_id = 'test-object_testbase'

        with self.assertRaises(self.failureException) as cm1:
            self.get_relationtype_or_fail(type_id)
        self.assertEqual(
            f'Bad populate: RelationType with id="{type_id}" cannot be found',
            str(cm1.exception),
        )

        # ---
        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Military')
        ptype2 = create_ptype(text='Hi-tech')
        ptype3 = create_ptype(text='Bio-tech')

        rtype = RelationType.objects.builder(
            id=type_id, predicate='is hiring',
            models=[FakeContact, FakeOrganisation], properties=[ptype1, ptype2],
        ).symmetric(
            id=sym_type_id, predicate='is hived by',
            models=[FakeContact], properties=[ptype3],
        ).get_or_create()[0]

        with self.assertNoException():
            result = self.get_relationtype_or_fail(
                type_id,
                sub_models=[FakeContact, FakeOrganisation],
                obj_models=[FakeContact],
                sub_props=[ptype1, ptype2],
                obj_props=[ptype3],
            )

        self.assertEqual(rtype, result)

        # Models constraints (subjects)
        with self.assertRaises(self.failureException):
            self.get_relationtype_or_fail(
                type_id,
                sub_models=[FakeContact],  # FakeOrganisation
                obj_models=[FakeContact],
                sub_props=[ptype1, ptype2.uuid],
                obj_props=[ptype3],
            )

        # Models constraints (objects)
        with self.assertRaises(self.failureException):
            self.get_relationtype_or_fail(
                type_id,
                sub_models=[FakeContact, FakeOrganisation],
                obj_models=[FakeOrganisation],  # <==
                sub_props=[ptype1.uuid, ptype2],
                obj_props=[ptype3.uuid],
            )

        # Properties constraints (subjects)
        with self.assertRaises(self.failureException):
            self.get_relationtype_or_fail(
                type_id,
                sub_models=[FakeContact, FakeOrganisation],
                obj_models=[FakeContact],
                sub_props=[ptype3],  # <===
                obj_props=[ptype3],
            )

        # Properties constraints (objects)
        with self.assertRaises(self.failureException):
            self.get_relationtype_or_fail(
                type_id,
                sub_models=[FakeContact, FakeOrganisation],
                obj_models=[FakeContact],
                sub_props=[ptype1, ptype2],  # <===
                obj_props=[ptype1],
            )

    def test_get_propertytype_or_fail(self):
        uid = str(uuid4())

        with self.assertRaises(self.failureException) as cm1:
            self.get_propertytype_or_fail(uid)
        self.assertEqual(
            f'Bad populate: CremePropertyType with uuid="{uid}" cannot be found',
            str(cm1.exception),
        )

        # ---
        ptype = CremePropertyType.objects.create(
            uuid=uid, text='Military',
        ).set_subject_ctypes(FakeContact, FakeOrganisation)

        with self.assertNoException():
            result = self.get_propertytype_or_fail(uid, models=[FakeContact, FakeOrganisation])

        self.assertEqual(ptype, result)

        # Properties constraints
        with self.assertRaises(self.failureException):
            self.get_propertytype_or_fail(uid, models=[FakeContact])  # FakeOrganisation

    def test_get_choices_group_or_fail(self):
        grouped_choices = [
            ('numbers', [(1, 'one'), (2, 'two')]),
            ('colors',  [('red', 'Red'), ('green', 'Green')]),
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

    def test_get_html_node_or_fail(self):
        tree = self.get_html_tree(
"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">
<head>
    <meta http-equiv="Content-type" content="text/html; charset=utf-8" />
</head>
<body>
    <div class="main-content">Hi</div>
</body>
""")  # NOQA

        with self.assertRaises(self.failureException) as cm:
            self.get_html_node_or_fail(tree, './/div[@class="content"]')
        self.assertEqual(
            'The HTML node with path <.//div[@class="content"]> has not been found.',
            str(cm.exception),
        )

        with self.assertNoException():
            node = self.get_html_node_or_fail(tree, './/div[@class="main-content"]')
        self.assertEqual('Hi', node.text)

    def test_formfield_value_date(self):
        date_obj = date(year=2022, month=2, day=24)

        with override_language('en'):
            date_str_en = self.formfield_value_date(date_obj)
        self.assertEqual('2022-02-24', date_str_en)

        with override_language('fr'):
            date_str_fr = self.formfield_value_date(date_obj)
        self.assertEqual('24/02/2022', date_str_fr)

    def test_formfield_value_datetime(self):
        date_obj = date(year=2022, month=2, day=24)
        dt_obj = datetime(year=2023, month=3, day=21, hour=18, minute=53)

        with override_language('en'):
            date_str_en = self.formfield_value_datetime(date_obj)
            dt_str_en = self.formfield_value_datetime(dt_obj)
        self.assertEqual('2022-02-24', date_str_en)
        self.assertEqual('2023-03-21 18:53:00', dt_str_en)

        with override_language('fr'):
            date_str_fr = self.formfield_value_datetime(date_obj)
            dt_str_fr = self.formfield_value_datetime(dt_obj)
        self.assertEqual('24/02/2022', date_str_fr)
        self.assertEqual('21/03/2023 18:53:00', dt_str_fr)

    def test_add_credentials01(self):
        "ALL + wildcard."
        role = UserRole.objects.create(name='Boss')
        self.assertFalse(SetCredentials.objects.filter(role=role))

        self.add_credentials(role, all='*')
        creds = self.get_alone_element(SetCredentials.objects.filter(role=role))
        self.assertEqual(
            EntityCredentials.VIEW
            | EntityCredentials.CHANGE
            | EntityCredentials.DELETE
            | EntityCredentials.LINK
            | EntityCredentials.UNLINK,
            creds.value,
        )
        self.assertEqual(SetCredentials.ESET_ALL, creds.set_type)
        self.assertIsNone(creds.ctype)
        self.assertIsNone(creds.efilter)
        self.assertFalse(creds.forbidden)

    def test_add_credentials02(self):
        "ALL + specific flags."
        role = UserRole.objects.create(name='Boss')
        self.assertFalse(SetCredentials.objects.filter(role=role))

        self.add_credentials(role, all=['VIEW', 'CHANGE', 'DELETE'])
        creds1 = self.get_alone_element(SetCredentials.objects.filter(role=role))
        self.assertEqual(
            EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.DELETE,
            creds1.value,
        )
        self.assertEqual(SetCredentials.ESET_ALL, creds1.set_type)

        # ---
        self.add_credentials(role, all=['LINK', 'UNLINK'])
        creds2 = self.get_alone_element(
            SetCredentials.objects.filter(role=role).exclude(id=creds1.id)
        )
        self.assertEqual(
            EntityCredentials.LINK | EntityCredentials.UNLINK,
            creds2.value,
        )
        self.assertEqual(SetCredentials.ESET_ALL, creds2.set_type)

    def test_add_credentials03(self):
        "OWN + wildcard."
        role = UserRole.objects.create(name='Boss')
        self.assertFalse(SetCredentials.objects.filter(role=role))

        self.add_credentials(role, own='*')
        creds = self.get_alone_element(SetCredentials.objects.filter(role=role))
        self.assertEqual(
            EntityCredentials.VIEW
            | EntityCredentials.CHANGE
            | EntityCredentials.DELETE
            | EntityCredentials.LINK
            | EntityCredentials.UNLINK,
            creds.value,
        )
        self.assertEqual(SetCredentials.ESET_OWN, creds.set_type)

    def test_add_credentials04(self):
        "OWN + specific flags."
        role = UserRole.objects.create(name='Boss')
        self.assertFalse(SetCredentials.objects.filter(role=role))

        self.add_credentials(role, own=['VIEW', 'CHANGE', 'LINK'])
        creds = self.get_alone_element(SetCredentials.objects.filter(role=role))
        self.assertEqual(
            EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            creds.value,
        )
        self.assertEqual(SetCredentials.ESET_OWN, creds.set_type)

    def test_add_credentials05(self):
        "Negative flags."
        role = UserRole.objects.create(name='Boss')
        self.assertFalse(SetCredentials.objects.filter(role=role))

        self.add_credentials(role, own='!CHANGE')
        creds = self.get_alone_element(SetCredentials.objects.filter(role=role))
        self.assertEqual(
            EntityCredentials.VIEW
            # | EntityCredentials.CHANGE
            | EntityCredentials.DELETE
            | EntityCredentials.LINK
            | EntityCredentials.UNLINK,
            creds.value,
        )
        self.assertEqual(SetCredentials.ESET_OWN, creds.set_type)

    def test_add_credentials__ctype01(self):
        "Content Type."
        role = UserRole.objects.create(name='Boss')
        ctype = ContentType.objects.get_for_model(FakeContact)

        self.add_credentials(role, all=['VIEW'], model=ctype)
        creds = self.get_alone_element(SetCredentials.objects.filter(role=role))
        self.assertEqual(EntityCredentials.VIEW, creds.value)
        self.assertEqual(SetCredentials.ESET_ALL, creds.set_type)
        self.assertEqual(ctype, creds.ctype)
        self.assertIsNone(creds.efilter)
        self.assertFalse(creds.forbidden)

    def test_add_credentials__ctype02(self):
        "Class."
        role = UserRole.objects.create(name='Boss')

        self.add_credentials(role, all=['VIEW'], model=FakeOrganisation)
        creds = self.get_alone_element(SetCredentials.objects.filter(role=role))
        self.assertEqual(EntityCredentials.VIEW, creds.value)
        self.assertEqual(SetCredentials.ESET_ALL, creds.set_type)
        self.assertEqual(FakeOrganisation, creds.ctype.model_class())
        self.assertIsNone(creds.efilter)
        self.assertFalse(creds.forbidden)

    def test_add_credentials__forbidden01(self):
        "ALL."
        role = UserRole.objects.create(name='Boss')

        self.add_credentials(role, forbidden_all=['VIEW'])
        creds = self.get_alone_element(SetCredentials.objects.filter(role=role))
        self.assertEqual(EntityCredentials.VIEW, creds.value)
        self.assertEqual(SetCredentials.ESET_ALL, creds.set_type)
        self.assertIsNone(creds.ctype)
        self.assertIsNone(creds.efilter)
        self.assertTrue(creds.forbidden)

    def test_add_credentials__forbidden02(self):
        "OWN."
        role = UserRole.objects.create(name='Boss')

        self.add_credentials(role, forbidden_own=['VIEW'])
        creds = self.get_alone_element(SetCredentials.objects.filter(role=role))
        self.assertEqual(EntityCredentials.VIEW, creds.value)
        self.assertEqual(SetCredentials.ESET_OWN, creds.set_type)
        self.assertIsNone(creds.ctype)
        self.assertIsNone(creds.efilter)
        self.assertTrue(creds.forbidden)

    def test_create_role01(self):
        role = self.create_role()
        self.assertIsInstance(role, UserRole)
        self.assertIsNotNone(role.pk)
        self.assertEqual('Test', role.name)
        self.assertFalse(role.allowed_apps)
        self.assertFalse(role.admin_4_apps)
        self.assertFalse(role.creatable_ctypes.all())
        self.assertFalse(role.exportable_ctypes.all())

    def test_create_role02(self):
        name = 'Boss'
        role = self.create_role(
            name=name,
            allowed_apps=['creme_core', 'persons'],
            admin_4_apps=['persons'],
            creatable_models=[FakeContact, FakeOrganisation],
            exportable_models=[FakeContact],
        )
        self.assertEqual(name, role.name)
        self.assertSetEqual({'creme_core', 'persons'}, role.allowed_apps)
        self.assertSetEqual({'persons'},               role.admin_4_apps)
        self.assertCountEqual(
            [FakeContact, FakeOrganisation],
            [ctype.model_class() for ctype in role.creatable_ctypes.all()],
        )
        self.assertListEqual(
            [FakeContact],
            [ctype.model_class() for ctype in role.exportable_ctypes.all()],
        )

    def test_build_user(self):
        user1 = self.build_user()
        self.assertIsInstance(user1, CremeUser)
        self.assertIsNone(user1.pk)
        self.assertEqual('kirika', user1.username)
        self.assertEqual('Kirika', user1.first_name)
        self.assertEqual('Yumura', user1.last_name)
        self.assertEqual('kirika@noir.jp', user1.email)
        self.assertEqual('', user1.password)

        password = 'test'
        user2 = self.build_user(index=1, password=password)
        self.assertEqual('mireille', user2.username)
        self.assertEqual('Mireille', user2.first_name)
        self.assertEqual('Bouquet', user2.last_name)
        self.assertEqual('mireille@noir.jp', user2.email)
        self.assertNotEqual('', user2.password)

    def test_create_user(self):
        password = 'my very good password'
        user = self.create_user(password=password)
        self.assertIsInstance(user, CremeUser)
        self.assertIsNotNone(user.pk)
        self.assertEqual('kirika', user.username)
        self.assertEqual('Kirika', user.first_name)
        self.assertEqual('Yumura', user.last_name)
        self.assertEqual('kirika@noir.jp', user.email)
        self.assertTrue(user.check_password(password))

    def test_create_team(self):
        user1 = self.create_user(index=0)
        user2 = self.create_user(index=1)

        name = 'Noir'
        team = self.create_team(name, user1, user2)
        self.assertIsNotNone(team.pk)
        self.assertEqual(name, team.username)
        self.assertFalse(team.first_name)
        self.assertFalse(team.last_name)
        self.assertFalse(team.email)
        self.assertCountEqual([user1, user2], team.teammates_set.all())

# TODO: complete
#   assertGETXXX
#   assertPOSTXXX
#   assertNoFormsetError
#   assertNoWizardFormError
#   assertQuerysetSQLEqual
#   assertQEqual
#   assertSameProperties
#   assertSameRelations
#   assertSameRelationsNProperties
#   assertXMLEqualv2
#   get_deletion_command_or_fail
