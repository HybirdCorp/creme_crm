import sys
import warnings
from collections.abc import Iterable
from contextlib import ContextDecorator
from datetime import date, datetime, timedelta, timezone
from functools import reduce
from json import dumps as json_dump
from operator import or_
from os.path import basename
from tempfile import NamedTemporaryFile
from unittest import skipIf
from unittest.util import safe_repr
from uuid import UUID

from bleach._vendor import html5lib
from django import forms
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.backends.base import SessionBase
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db.models import Model
from django.db.models.query_utils import Q
from django.forms.formsets import BaseFormSet
from django.test import RequestFactory, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils.formats import get_format
from django.utils.timezone import get_current_timezone, make_aware
from django.utils.translation import gettext as _

from ..auth import EntityCredentials
from ..auth.special import SpecialPermission
from ..constants import ROOT_PASSWORD, ROOT_USERNAME
from ..core.setting_key import SettingKey
from ..global_info import clear_global_info
from ..gui.icons import get_icon_by_name, get_icon_size_px
from ..management.commands.creme_populate import Command as PopulateCommand
from ..models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    CremeUser,
    DeletionCommand,
    Relation,
    RelationType,
    SetCredentials,
    SettingValue,
    UserRole,
)
from ..utils import print_traceback
from ..utils.media import get_current_theme
from ..utils.xml_utils import XMLDiffError, xml_diff


def skipIfCustomUser(test_func):
    return skipIf(
        settings.AUTH_USER_MODEL != 'creme_core.CremeUser',
        'Custom User model in use'
    )(test_func)


def skipIfNotInstalled(app_name):
    return skipIf(
        not apps.is_installed(app_name),
        f"Skip this test which is related to the uninstalled app '{app_name}'"
    )


class OverrideSettingValueContext(ContextDecorator):
    """Overrides SettingKey value for tests."""
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __enter__(self):
        # self._previous = SettingValue.objects.get_4_key(self.key).value
        self._previous = SettingValue.objects.get_4_key(self.key, default=None).value
        SettingValue.objects.set_4_key(self.key, self.value)

    def __exit__(self, *exc):
        SettingValue.objects.set_4_key(self.key, self._previous)


class _AssertNoExceptionContext:
    """A context manager used by CremeTestCase.assertNoException method."""
    def __init__(self, test_case):
        self.exception = test_case.failureException

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type:
            print_traceback()

            raise self.exception(
                f'An exception <{exc_type.__name__}> occurred: {exc_value}'
            )

        return True


class _CremeTestCase:
    UNUSED_PK = sys.maxsize
    request_factory: RequestFactory

    @classmethod
    def setUpClass(cls):
        # Django's warnings about naive datetime are transformed into errors
        warnings.filterwarnings(
            action='error',
            message=r"(.)* received a naive datetime (.)*",
            category=RuntimeWarning,
            module=r'django\.db\.models\.fields',
        )
        # Creme's warnings about remaining events are transformed into errors
        warnings.filterwarnings(
            action='error',
            message='Some workflow events have not been managed',
            category=RuntimeWarning,
        )
        cls.request_factory = RequestFactory()

    @classmethod
    def clear_global_info(cls):
        clear_global_info()

    def setUp(self):
        self.clear_global_info()

    USER_PASSWORD = 'test'
    USERS_DATA = [
        {
            'username': 'kirika',
            'first_name': 'Kirika',
            'last_name': 'Yumura',
            'email': 'kirika@noir.jp',
        }, {
            'username': 'mireille',
            'first_name': 'Mireille',
            'last_name': 'Bouquet',
            'email': 'mireille@noir.jp',
        }, {
            'username': 'chloe',
            'first_name': 'Chloé',
            'last_name': 'Noir',
            'email': 'chloe@noir.jp',
        }, {
            'username': 'altena',
            'first_name': 'Alténa',
            'last_name': 'Soldat',
            'email': 'altena@noir.jp',
        },
    ]

    @classmethod
    def build_user(cls, index=0, password='', **kwargs):
        user_data = {
            **cls.USERS_DATA[index],
            **kwargs,
        }

        if not user_data.get('role'):
            user_data['is_superuser'] = True

        user = CremeUser(**user_data)

        if password:
            user.set_password(password)

        return user

    @classmethod
    def create_user(cls, index=0, *, roles=(), **kwargs):
        user = cls.build_user(index=index, **kwargs)
        user.save()

        if roles:
            assert user.role
            user.roles.set(roles)

        return user

    @classmethod
    def create_team(cls, name, *users):
        team = CremeUser.objects.create(username=name, is_team=True)
        team.teammates = users

        return team

    @classmethod
    def create_role(cls, *,
                    name='Test',
                    creatable_models: Iterable[type[CremeEntity]] = (),
                    listable_models: Iterable[type[CremeEntity]] = (),
                    exportable_models: Iterable[type[CremeEntity]] = (),
                    **kwargs
                    ) -> UserRole:
        return UserRole.objects.smart_create(
            name=name,
            creatable_models=creatable_models,
            listable_models=listable_models,
            exportable_models=exportable_models,
            **kwargs
        )

    @classmethod
    def get_root_user(cls) -> CremeUser:
        # Should exist (see 'creme_core.populate.py')
        return CremeUser.objects.get(username=ROOT_USERNAME)

    @classmethod
    def get_regular_role(cls) -> UserRole:
        # Should exist (see 'creme_core.populate.py')
        return UserRole.objects.get(name=_('Regular user'))

    _CREDS = {
        'VIEW':   EntityCredentials.VIEW,
        'CHANGE': EntityCredentials.CHANGE,
        'DELETE': EntityCredentials.DELETE,
        'LINK':   EntityCredentials.LINK,
        'UNLINK': EntityCredentials.UNLINK,
    }

    # TODO: "efilter"
    # TODO: return instances?
    @classmethod
    def add_credentials(cls, role: UserRole,
                        all=None, own=None,
                        forbidden_all=None, forbidden_own=None,
                        model: ContentType | type[CremeEntity] = None,
                        ) -> None:
        """Create up to 2 SetCredentials instances related to a given role.
        @param role: Related userRole.
        @param all: ESET_ALL credentials. It can be:
               - <None>: (default value) No credential is created.
               - <'*'>: All permissions are granted (VIEW, CHANGE etc...).
               - A list of strings; each value must be in
                 {'VIEW', 'CHANGE', 'DELETE', 'LINK', 'UNLINK'}.
               - A string starting by "!" followed by a value in {'VIEW', 'CHANGE'...}.
                 It means "All permissions are granted excepted this one"
                 (e.g. "!CHANGE").
        @param own: ESET_OWN credentials. Same values than "all" parameter.

        >> self.add_credentials(user.role, all='*', own='!DELETE')
        """
        CREDS = cls._CREDS

        def create(set_type, flags, forbidden=False):
            if isinstance(flags, str):
                if flags == '*':
                    value = reduce(or_, CREDS.values())
                else:
                    assert flags.startswith('!')
                    excluded = flags[1:]
                    assert excluded in CREDS
                    value = reduce(
                        or_,
                        (perm for flag, perm in CREDS.items() if flag != excluded)
                    )
            else:
                assert isinstance(flags, list | tuple)
                value = reduce(or_, (CREDS[flag] for flag in flags))

            SetCredentials.objects.create(
                role=role, value=value, set_type=set_type, ctype=model, forbidden=forbidden,
            )

        if all:
            create(SetCredentials.ESET_ALL, all)

        if own:
            create(SetCredentials.ESET_OWN, own)

        if forbidden_all:
            create(SetCredentials.ESET_ALL, forbidden_all, forbidden=True)

        if forbidden_own:
            create(SetCredentials.ESET_OWN, forbidden_own, forbidden=True)

    def login_as_root(self) -> None:
        # Should exist (see 'creme_core.populate.py')
        self.client.login(username=ROOT_USERNAME, password=ROOT_PASSWORD)

    def login_as_root_and_get(self) -> CremeUser:
        self.login_as_root()
        return self.get_root_user()

    def login_as_super(self,
                       is_staff=False,
                       index: int = 0,
                       # password: str = 'test',
                       password: str = USER_PASSWORD,
                       ) -> CremeUser:
        user = self.create_user(index=index, is_staff=is_staff, password=password)

        logged = self.client.login(username=user.username, password=password)
        self.assertTrue(logged, 'Not logged in')

        return user

    def login_as_standard(self, *,
                          allowed_apps: Iterable[str] = ('creme_core',),
                          admin_4_apps: Iterable[str] = (),
                          creatable_models: Iterable[type[CremeEntity]] = (),
                          listable_models: Iterable[type[CremeEntity]] = (),
                          exportable_models: Iterable[type[CremeEntity]] = (),
                          special_permissions: Iterable[SpecialPermission] = (),
                          index: int = 0,
                          # password: str = 'test',
                          password: str = USER_PASSWORD,
                          ) -> CremeUser:
        role = self.create_role(
            name='Basic',
            allowed_apps=allowed_apps,
            admin_4_apps=admin_4_apps,
            creatable_models=creatable_models,
            listable_models=listable_models,
            exportable_models=exportable_models,
            special_permissions=special_permissions,
        )
        user = self.create_user(index=index, role=role, password=password, roles=[role])

        logged = self.client.login(username=user.username, password=password)
        self.assertTrue(logged, 'Not logged in')

        return user

    def assertCountOccurrences(self, member, container, count, msg=None):
        """Like <self.assertEqual(count, container.count(member))>
        but with a nicer default message.
        """
        occ_count = container.count(member)

        if occ_count != count:
            std_msg = '{member} found {occ} time(s) in {container} ({exp} expected)'.format(
                member=safe_repr(member),
                container=safe_repr(container),
                occ=occ_count,
                exp=count,
            )
            self.fail(self._formatMessage(msg, std_msg))

    def assertDatetimesAlmostEqual(self, dt1, dt2, seconds=10):
        self.assertIsInstance(dt1, datetime)
        self.assertIsInstance(dt2, datetime)

        delta = max(dt1, dt2) - min(dt1, dt2)

        if delta > timedelta(seconds=seconds):
            self.fail(f'<{dt1}> & <{dt2}> are not almost equal: delta is <{delta}>')

    def assertDoesNotExist(self, instance: Model) -> None:
        model = instance.__class__

        try:
            model.objects.get(pk=instance.pk)
        except model.DoesNotExist:
            return

        self.fail('Your object still exists.')

    def assertStillExists(self, instance: Model) -> Model:
        model = instance.__class__

        pk = instance.pk
        self.assertIsNotNone(pk)

        try:
            return model.objects.get(pk=pk)
        except model.DoesNotExist:
            self.fail('Your object does not exist any more.')

    def assertGET(self, expected_status, *args, **kwargs):
        response = self.client.get(*args, **kwargs)
        code = response.status_code
        if expected_status != code:
            context = response.context
            if context:
                error_msg = context.get('exception') or context.get('error_message')
            else:
                error_msg = None

            if error_msg:
                self.fail(
                    f'Expected status was <{expected_status}>. '
                    f'Got status <{code}>. '
                    f'Content is <{error_msg}>'
                )
            else:
                self.fail(
                    f'Expected status was <{expected_status}>. '
                    f'Got status <{code}>.'
                )

        return response

    def assertGET200(self, *args, **kwargs):
        return self.assertGET(200, *args, **kwargs)

    def assertGET403(self, *args, **kwargs):
        return self.assertGET(403, *args, **kwargs)

    def assertGET404(self, *args, **kwargs):
        return self.assertGET(404, *args, **kwargs)

    def assertGET405(self, *args, **kwargs):
        return self.assertGET(405, *args, **kwargs)

    def assertGET409(self, *args, **kwargs):
        return self.assertGET(409, *args, **kwargs)

    def assertPOST(self, expected_status, *args, **kwargs):
        response = self.client.post(*args, **kwargs)
        # self.assertEqual(expected_status, response.status_code)
        self.assertEqual(expected_status, response.status_code, response.text)

        return response

    def assertPOST200(self, *args, **kwargs):
        return self.assertPOST(200, *args, **kwargs)

    def assertPOST403(self, *args, **kwargs):
        return self.assertPOST(403, *args, **kwargs)

    def assertPOST404(self, *args, **kwargs):
        return self.assertPOST(404, *args, **kwargs)

    def assertPOST405(self, *args, **kwargs):
        return self.assertPOST(405, *args, **kwargs)

    def assertPOST409(self, *args, **kwargs):
        return self.assertPOST(409, *args, **kwargs)

    def assertHasAttr(self, o, attr_name):
        if not hasattr(o, attr_name):
            self.fail(f'<{o}> has no attribute named "{attr_name}".')

    def assertHasNoAttr(self, o, attr_name):
        if hasattr(o, attr_name):
            self.fail(f'<{o}> has unexpectedly an attribute named "{attr_name}".')

    def assertFound(self, x, string, msg=None):
        idx = string.find(x)

        if idx == -1:
            std_msg = '{sub} not found in {string}'.format(
                sub=safe_repr(x),
                string=safe_repr(string),
            )
            self.fail(self._formatMessage(msg, std_msg))

        return idx

    def assertIndex(self, elt, sequence):
        try:
            index = sequence.index(elt)
        except ValueError:
            self.fail(f'{elt} not found in {sequence}')

        return index

    def assertIsSubclass(self, cls, parent_cls, msg=None):
        if not issubclass(cls, parent_cls):
            if msg is None:
                msg = f'{cls} is not a subclass of {parent_cls} ' \
                      f'[list of parent classes {cls.__mro__}]'

            self.fail(msg)

    def assertIsDict(self, o, **kwargs):
        self.assertIsInstance(o, dict)

        length = len(o)
        for k, v in kwargs.items():
            match k:
                case 'length':
                    if length != v:
                        self.fail(f'This dict has not the expected length of {v}: {o}')
                case 'min_length':
                    if length < v:
                        self.fail(f'This dict is not longer than {v}: {o}')
                case 'max_length':
                    if length > v:
                        self.fail(f'This dict is not shorter than {v}: {o}')
                case _:
                    raise ValueError(f'assertIsDict: unknown argument "{k}"')

    def assertIsList(self, o, **kwargs):
        self.assertIsInstance(o, list)

        length = len(o)
        for k, v in kwargs.items():
            match k:
                case 'length':
                    if length != v:
                        self.fail(f'This list has not the expected length of {v}: {o}')
                case 'min_length':
                    if length < v:
                        self.fail(f'This list is not longer than {v}: {o}')
                case 'max_length':
                    if length > v:
                        self.fail(f'This list is not shorter than {v}: {o}')
                case _:
                    raise ValueError(f'assertIsList: unknown argument "{k}"')

    def assertIsTuple(self, o, *, length):
        self.assertIsInstance(o, tuple)

        if length != len(o):
            self.fail(f'This tuple has not the expected length of {length}: {o}')

    def assertNoException(self, function=None, *args, **kwargs):
        if function is None:
            return _AssertNoExceptionContext(self)

        try:
            return function(*args, **kwargs)
        except Exception as e:
            print_traceback()

            raise self.failureException(
                f'An exception <{e.__class__.__name__}> occurred: {e}'
            ) from e

    def assertInChoices(self, value, label, choices):
        """Search a choice among a classical sequence of Django's choices
        (i.e. tuples (value, label)).
        """
        value = str(value)

        for i, (choice_value, choice_label) in enumerate(choices):
            if value == str(choice_value):
                if choice_label != label:
                    self.fail(
                        f'The choice "{value}" has been found, but with the '
                        f'label "{choice_label}", not "{label}".'
                    )

                return i

        self.fail(
            'The choice "{value}" has not been found in {values}.'.format(
                value=value,
                values=[str(c[0]) for c in choices],
            )
        )

    def assertNotInChoices(self, value, choices):
        """Check a choice's value is not found in a classical sequence of
        Django's choices (i.e. tuples (value, label)).
        """
        for choice_value, choice_label in choices:
            if choice_value == value:
                self.fail(
                    f'The choice "{value}" has been unexpectedly found with '
                    f'label="{choice_label}".'
                )

    def assertFormfieldError(self, *, field: forms.Field, value,
                             messages: str | list[str],
                             codes: str | list[str | None] | None = None,
                             ):
        """Check that calling the method 'clean()' of a form-field with a given
        value causes a certain validationError to be risen.
        See 'assertValidationError()' for explanation on possible values for
        "messages" & "codes".
        """
        with self.assertRaises(ValidationError) as cm:
            field.clean(value)

        self.assertValidationError(
            error=cm.exception,
            messages=messages,
            codes=codes,
        )

    def assertFormInstanceErrors(self, form, *errors):
        form_errors = form.errors
        field_names = set()

        for field_name, message in errors:
            # TODO: test all the errors in the field
            if field_name not in form_errors:
                self.fail(
                    'The error "{field}" has not been found in the form '
                    '(fields with errors: {fields})'.format(
                        field=field_name,
                        fields=[*form_errors.keys()],
                    )
                )

            field_errors = form_errors[field_name]
            if message not in field_errors:
                self.fail(
                    f'The error "{message}" has not been found in the field '
                    f'errors ({field_errors})'
                )

            field_names.add(field_name)

        remaining_errors = {*form_errors.keys()} - field_names
        if remaining_errors:
            self.fail(
                'Unexpected errors have been found in the form: {}'.format(
                    [(name, form_errors[name]) for name in remaining_errors]
                )
            )

    # TODO: add an argument 'field' like assertNoFormsetError()
    def assertNoFormError(self, response, status=200, form='form'):
        status_code = response.status_code

        if status_code != status:
            redirect = 'NO'
            if hasattr(response, 'redirect_chain'):
                redirect = response.redirect_chain
            elif hasattr(response, 'url'):
                redirect = response.url

            self.fail(
                f'Response status={status_code} (expected: {status}) '
                f'[redirections={redirect}; content={response.content}]'
            )

        try:
            errors = response.context[form].errors
        except Exception:
            pass
        else:
            if errors:
                self.fail(errors.as_text())

    def assertNoFormsetError(self, response, formset, form_index, field=None, status=200):
        """
        @param field: Field name (can be '__all__' for global errors) or None
               (which means 'No error at all').
        """
        status_code = response.status_code

        if status_code != status:
            self.fail(f'Response status={status_code} (expected: {status})')

        try:
            formset_obj = response.context[formset]
        except Exception:
            pass
        else:
            all_errors = formset_obj.errors

            if not all_errors:
                return

            self.assertIsInstance(
                formset_obj, BaseFormSet,
                f"context field '{formset_obj}' is not a FormSet"
            )
            self.assertGreaterEqual(form_index, 0)
            self.assertLess(form_index, len(all_errors))

            errors = all_errors[form_index]

            if field is None:
                if errors:
                    self.fail(
                        f"The formset '{formset}' number {form_index} contains "
                        f"errors: {errors}"
                    )
            else:
                try:
                    field_errors = errors[field]
                except KeyError:
                    pass
                else:
                    self.fail(
                        f"The field '{field}' on formset '{formset}' number "
                        f"{form_index} contains errors: {field_errors}"
                    )

    def assertNoWizardFormError(self, response, status=200, wizard='wizard'):
        self.assertEqual(status, response.status_code)

        try:
            errors = response.context[wizard]['form'].errors
        except Exception:
            pass
        else:
            if errors:
                self.fail(errors.as_text())

    def assertListContainsSubset(self, expected, actual, msg=None):
        "Checks whether 'actual' is a superset of 'expected'."
        old_index = -1

        for elt in expected:
            try:
                index = actual.index(elt)
            except ValueError:
                self.fail(
                    self._formatMessage(
                        msg,
                        f'Element not found in the superset : "{elt}"',
                    )
                )

            if index <= old_index:
                self.fail(
                    self._formatMessage(
                        msg,
                        f'Order is different in the superset '
                        f'(problem with element : "{elt}")'
                    )
                )

            old_index = index

    def assertQuerysetSQLEqual(self, qs1, qs2):
        self.assertEqual(
            qs1.query.get_compiler('default').as_sql(),
            qs2.query.get_compiler('default').as_sql()
        )

    def assertQEqual(self, q1, q2):
        self.assertIsInstance(q1, Q)
        self.assertIsInstance(q2, Q)
        self.assertEqual(str(q1), str(q2))

    def assertUUIDEqual(self, uid1: str | UUID, uid2: str | UUID):
        if isinstance(uid1, str):
            uid1 = UUID(uid1)
        else:
            self.assertIsInstance(uid1, UUID)

        if isinstance(uid2, str):
            uid2 = UUID(uid2)
        else:
            self.assertIsInstance(uid2, UUID)

        if uid1 != uid2:
            self.fail(f'The UUIDs are not equal: "{uid1}" != "{uid2}".')

    def __get_creme_properties(self,
                               entity: CremeEntity | int,
                               ptype: CremePropertyType | int | str,
                               ):
        kwargs = {'creme_entity_id': entity.id if isinstance(entity, CremeEntity) else entity}
        if isinstance(ptype, CremePropertyType):
            kwargs['type'] = ptype
        elif isinstance(ptype, int):
            kwargs['type_id'] = ptype
        else:
            assert isinstance(ptype, str)  # TODO: <UUID> ?
            kwargs['type__uuid'] = ptype

        return CremeProperty.objects.filter(**kwargs)

    def assertHasProperty(self, entity: CremeEntity | int, ptype: CremePropertyType | int | str):
        if not self.__get_creme_properties(entity=entity, ptype=ptype).exists():
            self.fail(f'<{entity}> has no property with type <{ptype}>')

    def assertHasNoProperty(self, entity: CremeEntity | int, ptype: CremePropertyType | int | str):
        if self.__get_creme_properties(entity=entity, ptype=ptype).exists():
            self.fail(f'<{entity}> has property with type <{ptype}>')

    # def assertRelationCount(self, count, subject_entity, type_id, object_entity):
    #     warnings.warn(
    #         'assertRelationCount() is deprecated;'
    #         'use assertHaveRelation()/assertHaveNoRelation() instead.',
    #         DeprecationWarning
    #     )
    #     self.assertEqual(
    #         count,
    #         Relation.objects.filter(
    #             subject_entity=subject_entity.id,
    #             type=type_id,
    #             object_entity=object_entity.id,
    #         ).count(),
    #     )

    def assertHaveRelation(self,
                           subject: CremeEntity | int,
                           type: RelationType | str,
                           object: CremeEntity | int,
                           ) -> Relation:
        relation = Relation.objects.filter(
            subject_entity=subject, type=type, object_entity=object,
        ).first()
        if relation is None:
            self.fail(f'<{subject}> is not related to <{object}> with type <{type}>')

        return relation

    def assertHaveNoRelation(self,
                             subject: CremeEntity | int,
                             type: RelationType | str,
                             object: CremeEntity | int,
                             ) -> None:
        if Relation.objects.filter(
            subject_entity=subject, type=type, object_entity=object,
        ).exists():
            self.fail(f'<{subject}> is related to <{object}> with type <{type}>')

    def assertSameProperties(self, entity1, entity2):
        self.assertCountEqual(
            entity1.properties.values_list('type', flat=True),
            entity2.properties.values_list('type', flat=True),
        )

    def assertSameRelations(self, entity1, entity2, exclude_internal=True):
        def relations_desc(entity):
            qs = entity.relations.values_list('type', 'object_entity')

            if exclude_internal:
                qs = qs.exclude(type__is_internal=True)

            return qs

        self.assertCountEqual(relations_desc(entity1), relations_desc(entity2))

    def assertSameRelationsNProperties(self, entity1, entity2, exclude_internal=True):
        self.assertSameProperties(entity1, entity2)
        self.assertSameRelations(entity1, entity2, exclude_internal)

    def assertStartsWith(self, s, prefix):
        if not s.startswith(prefix):
            raise self.failureException(f'The string {s!r} does not start with {prefix!r}')

    def assertEndsWith(self, s, prefix):
        if not s.endswith(prefix):
            raise self.failureException(f'The string {s!r} does not end with {prefix!r}')

    # TODO: add a context manager assertRaisesValidationError() ?
    def assertValidationError(
        self, error: ValidationError, *,
        messages: str | list[str] | dict[str, str | list[str]],
        codes: str | list[str | None] | dict[str, str | list[str] | None] | None = None,
    ):
        """Check the content of a ValidationError instances
        @param error: Exception to instance to test.
        @param messages: Mandatory argument to test the messages contained by
               the error (notice that a ValidationError can contain other
               ValidationErrors). It can be:
               - a list of strings
               - a simple string (it's a shortcut for a list with only one string element).
               - a dictionary with string keys ; each value can be
                   - a list of strings
                   - a simple string (it's a shortcut like above)
        @param codes: Optional argument used to test the contained codes. If this
               argument is not given, codes are just not checked. If given, the
               value can have the same form as "messages" (notably simple strings
               as shortcuts), excepted that 'None' is a possible value for list
               elements & dictionary values.
        """
        if isinstance(messages, dict):
            try:
                err_messages = error.message_dict
            except AttributeError:
                self.fail('The given exception does not use an error dictionary.')

            exp_messages = {
                k: v if isinstance(v, list) else [v]
                for k, v in messages.items()
            }
            if exp_messages != err_messages:
                self.fail(
                    f'The messages differ. Expected: {exp_messages!r}. Got: {err_messages!r}'
                )

            if codes is not None:
                if not isinstance(codes, dict):
                    raise TypeError('The argument "codes" must be a dictionary in this case.')

                exp_codes = {
                    k: v if isinstance(v, list) else [v]
                    for k, v in codes.items()
                }

                err_codes = {
                    k: [e.code for e in errors]
                    for k, errors in error.error_dict.items()
                }
                if exp_codes != err_codes:
                    self.fail(f'The codes differ. Expected: {exp_codes!r}. Got: {err_codes!r}')
        else:
            if hasattr(error, 'error_dict'):
                self.fail('The given exception uses an error dictionary.')

            if not isinstance(messages, list):
                messages = [messages]

            err_messages = error.messages
            if messages != err_messages:
                self.fail(f'The messages differ. Expected: {messages!r}. Got: {err_messages!r}')

            if codes is not None:
                if isinstance(codes, str):
                    codes = [codes]
                elif not isinstance(codes, list):
                    raise TypeError(
                        'The argument "codes" must be a list or a string in this case.'
                    )

                err_codes = [e.code for e in error.error_list]
                if codes != err_codes:
                    self.fail(f'The codes differ. Expected: {codes!r}. Got: {err_codes!r}')

    # TODO: unit test
    def assertSettingValueEqual(self, key: SettingKey | str, value):
        sv = self.get_object_or_fail(
            SettingValue, key_id=(key if isinstance(key, str) else key.id),
        )
        self.assertEqual(value, sv.value)

    def assertXMLEqualv2(self, expected, actual):
        """Compare 2 strings representing XML document, with the XML semantic.
        @param expected: XML string ;
               tip: better if it is well indented to have better error message.
        @param actual: XML string.
        """
        try:
            diff = xml_diff(expected, actual)
        except XMLDiffError as e:
            raise self.failureException(f'Bad XML document [{e}]') from e

        if diff is not None:
            msg = diff.long_msg

            if self.maxDiff is not None and len(msg) > self.maxDiff:
                msg = f'{diff.short_msg}\n[maxDiff too small for larger message]'

            raise self.failureException(f'XML are not equal\n{msg}')

    @staticmethod
    def build_filedata(content, suffix='.txt'):
        tmpfile = NamedTemporaryFile(suffix=suffix)
        tmpfile.write(content.encode() if isinstance(content, str) else content)
        tmpfile.flush()

        filedata = tmpfile.file
        filedata.seek(0)

        tmpfile.base_name = basename(tmpfile.name)

        return tmpfile

    @staticmethod
    def build_merge_url(entity1, entity2):
        id1 = entity1.id if isinstance(entity1, CremeEntity) else entity1
        id2 = entity2.id if isinstance(entity2, CremeEntity) else entity2
        return reverse('creme_core__merge_entities') + f'?id1={id1}&id2={id2}'

    @classmethod
    def build_request(cls, *, user=None, url='/', data=None):
        request = cls.request_factory.get(url, data=data)
        request.session = SessionBase()
        request.user = user or cls.get_root_user()

        return request

    @classmethod
    def build_context(cls, user, url=None, instance=None, request_data=None):
        from django.template.context import make_context
        from django.template.engine import Engine

        if not url:
            url = reverse('creme_core__home') if instance is None else instance.get_absolute_url()

        request = cls.build_request(url=url, user=user, data=request_data)

        context = make_context({}, request)

        for processor in Engine.get_default().template_context_processors:
            context.update(processor(request))

        if instance is not None:
            context['object'] = instance

        return context.flatten()

    @staticmethod
    def create_datetime(*args, **kwargs):
        tz = timezone.utc if kwargs.pop('utc', False) else get_current_timezone()
        return make_aware(datetime(*args, **kwargs), tz)

    @staticmethod
    def create_uploaded_file(*,
                             file_name: str,
                             dir_name: str,
                             content: str | list[str] = 'I am the content',
                             ) -> str:
        from os import path as os_path
        from shutil import copy

        from creme.creme_core.utils.file_handling import FileCreator

        rel_media_dir_path = os_path.join('creme_core-tests', dir_name)
        final_path = FileCreator(
            os_path.join(settings.MEDIA_ROOT, rel_media_dir_path),
            file_name,
        ).create()

        if isinstance(content, list):
            copy(os_path.join(*content), final_path)
        elif isinstance(content, str):
            with open(final_path, 'w') as f:
                f.write(content)

        return os_path.join(rel_media_dir_path, os_path.basename(final_path))

    def get_object_or_fail(self, model, **kwargs):
        try:
            obj = model.objects.get(**kwargs)
        except model.DoesNotExist as e:
            self.fail(
                f'Your object does not exist.\n'
                f' Query model: {model}\n'
                f' Query args {kwargs}\n'
                f' [original exception: {e}]'
            )
        except Exception as e:
            self.fail(str(e))

        return obj

    def get_alone_element(self, iterable):
        """Check that an iterable has only one element, which is returned."""
        listified = [*iterable]
        length = len(listified)
        if length != 1:
            self.fail(f'The iterable has {length} elements, not 1')

        return listified[0]

    def get_choices_group_or_fail(self, label, choices):
        for choice in choices:
            if choice[0] == label:
                return choice[1]

        self.fail(f'Group "{label}" not found.')

    def get_deletion_command_or_fail(self, model):
        return self.get_object_or_fail(
            DeletionCommand,
            content_type=ContentType.objects.get_for_model(model),
        )

    def get_relationtype_or_fail(self, pk,
                                 sub_models: Iterable[type[CremeEntity]] = (),
                                 obj_models: Iterable[type[CremeEntity]] = (),
                                 sub_props: Iterable[CremePropertyType | str] = (),
                                 obj_props: Iterable[CremePropertyType | str] = (),
                                 ):
        try:
            rt = RelationType.objects.get(pk=pk)
        except RelationType.DoesNotExist:
            self.fail(f'Bad populate: RelationType with id="{pk}" cannot be found')

        get_ct = ContentType.objects.get_for_model
        self.assertCountEqual(
            [get_ct(model) for model in sub_models],
            rt.subject_ctypes.all(),
        )
        self.assertCountEqual(
            [get_ct(model) for model in obj_models],
            rt.object_ctypes.order_by('id'),
        )

        self.assertCountEqual(
            [ptype if isinstance(ptype, str) else str(ptype.uuid) for ptype in sub_props],
            [str(uid) for uid in rt.subject_properties.values_list('uuid', flat=True)],
        )
        self.assertCountEqual(
            [ptype if isinstance(ptype, str) else str(ptype.uuid) for ptype in obj_props],
            [str(uid) for uid in rt.object_properties.values_list('uuid', flat=True)],
        )

        self.assertNotEqual(
            rt.pk, rt.symmetric_type_id,
            'Be careful your type is its own symmetric type'
        )  # Common error

        return rt

    def get_propertytype_or_fail(self,
                                 uid: str | UUID,
                                 models: Iterable[type[CremeEntity]] = (),
                                 ):
        try:
            pt = CremePropertyType.objects.get(uuid=uid)
        except CremePropertyType.DoesNotExist:
            self.fail(f'Bad populate: CremePropertyType with uuid="{uid}" cannot be found')

        get_ct = ContentType.objects.get_for_model
        self.assertCountEqual(
            [get_ct(model) for model in models],
            pt.subject_ctypes.all(),
        )

        return pt

    @staticmethod
    def refresh(obj):
        return obj.__class__.objects.get(pk=obj.pk)

    @staticmethod
    def build_inneredit_uri(entity, *fields):
        url = reverse(
            'creme_core__inner_edition',
            args=(ContentType.objects.get_for_model(entity).pk, entity.pk),
        )
        return f'{url}?' + '&'.join(
            f'cell=regular_field-{field}'
            if isinstance(field, str) else
            f'cell=custom_field-{field.id}'
            for field in fields
        )

    @staticmethod
    def build_bulkupdate_uri(*, model, field=None, entities=()):
        args = [ContentType.objects.get_for_model(model).id]
        if field is not None:
            args.append(
                f'regular_field-{field}'
                if isinstance(field, str) else
                f'custom_field-{field.id}'
            )

        url = reverse('creme_core__bulk_update', args=args)
        ids = '.'.join(str(e.id if isinstance(e, CremeEntity) else e) for e in entities)

        return f"{url}?entities={ids}" if ids else url

    def clone(self, entity):
        model = type(entity)
        old_count = model.objects.count()

        self.assertPOST200(
            entity.get_clone_absolute_url(), data={'id': entity.id}, follow=True,
        )
        self.assertEqual(old_count + 1, model.objects.count())

        return model.objects.order_by('-id').first()

    @staticmethod
    def formfield_value_date(*args):
        if len(args) == 1:
            date_obj = args[0]
        else:
            year, month, day = args
            date_obj = date(year, month, day)

        return date_obj.strftime(get_format('DATE_INPUT_FORMATS')[0])

    @staticmethod
    def formfield_value_datetime(dt_obj=None, **kwargs):
        if kwargs:
            dt_obj = datetime(**kwargs)

        return dt_obj.strftime(
            get_format(
                'DATETIME_INPUT_FORMATS' if isinstance(dt_obj, datetime) else 'DATE_INPUT_FORMATS'
            )[0]
        )

    @staticmethod
    def formfield_value_generic_entity(entity):
        return json_dump({
            'ctype': {'id': str(entity.entity_type_id)},
            'entity': str(entity.id),
        })

    @staticmethod
    def formfield_value_multi_generic_entity(*entities):
        return json_dump([
            {
                'ctype': {'id': str(entity.entity_type_id)},
                'entity': str(entity.id),
            } for entity in entities
        ])

    @staticmethod
    def formfield_value_multi_creator_entity(*entities):
        return json_dump([entity.id for entity in entities])

    @staticmethod
    def formfield_value_relation_entity(rtype, entity):
        return json_dump({
            'rtype':  rtype.id if isinstance(rtype, RelationType) else rtype,
            'ctype':  str(entity.entity_type_id),
            'entity': str(entity.id),
        })

    @staticmethod
    def formfield_value_multi_relation_entity(*relations):
        return json_dump([
            {
                'rtype':  rtype.id if isinstance(rtype, RelationType) else rtype,
                'ctype':  str(entity.entity_type_id),
                'entity': str(entity.id),
            } for rtype, entity in relations
        ])

    @staticmethod
    def formfield_value_filtered_entity_type(ctype=None, efilter=None):
        return json_dump({
            'ctype': str(ctype.id if ctype else 0),
            'efilter': efilter.id if efilter else '',
        })

    def get_form_or_fail(self, response, form_name='form'):
        context = response.context
        self.assertIsNotNone(
            context, msg='No context found in the response (no validation error)',
        )

        form = response.context.get(form_name)
        self.assertIsNotNone(
            form, msg='No form found in the response (no validation error)',
        )

        return form

    @staticmethod
    def get_html_tree(content):
        return html5lib.parse(content, namespaceHTMLElements=False)

    def get_html_node_or_fail(self, parent_node, path):
        child = parent_node.find(path)

        if child is None:
            self.fail(f'The HTML node with path <{path}> has not been found.')

        return child

    @staticmethod
    def get_icon(name, size, label=''):
        theme = get_current_theme()

        return get_icon_by_name(
            name, theme,
            size_px=get_icon_size_px(theme, size),
            label=label,
        )


class CremeTestCase(TestCase, _CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _CremeTestCase.setUpClass()

    def setUp(self):
        super().setUp()
        _CremeTestCase.setUp(self)


class CremeTransactionTestCase(TransactionTestCase, _CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _CremeTestCase.setUpClass()

    def setUp(self):
        super().setUp()
        _CremeTestCase.setUp(self)

    @classmethod
    def populate(cls, *args):
        call_command(PopulateCommand(), verbosity=0)
