from __future__ import annotations

import sys
import warnings
from contextlib import ContextDecorator
from datetime import date, datetime, timedelta, timezone
from json import dumps as json_dump
from os.path import basename
from tempfile import NamedTemporaryFile
from typing import Iterable
from unittest import skipIf
from unittest.util import safe_repr

from bleach._vendor import html5lib
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.backends.base import SessionBase
from django.core.management import call_command
from django.db.models.query_utils import Q
from django.forms.formsets import BaseFormSet
from django.test import RequestFactory, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils.formats import get_format
# from django.utils.timezone import utc
from django.utils.timezone import get_current_timezone, make_aware

from ..constants import ROOT_PASSWORD, ROOT_USERNAME
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
    """Overrides SettingKey value for tests"""
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __enter__(self):
        self._previous = SettingValue.objects.get_4_key(self.key).value
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

    @classmethod
    def setUpClass(cls):
        warnings.filterwarnings(
            'error', r"(.)* received a naive datetime (.)*",
            RuntimeWarning, r'django\.db\.models\.fields',
        )
        cls.request_factory = RequestFactory()

    def setUp(self):
        clear_global_info()

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

        # user.set_password(cls.USER_PASSWORD)
        if password:
            user.set_password(password)

        return user

    @classmethod
    def create_user(cls, index=0, **kwargs):
        user = cls.build_user(index=index, **kwargs)
        user.save()

        return user

    @classmethod
    def create_team(cls, name, *users):
        team = CremeUser.objects.create(username=name, is_team=True)
        team.teammates = users

        return team

    @classmethod
    def create_role(self, *,
                    name='Test',
                    creatable_models: Iterable[type[CremeEntity]] = (),
                    exportable_models: Iterable[type[CremeEntity]] = (),
                    **kwargs
                    ) -> UserRole:
        role = UserRole.objects.create(name=name, **kwargs)

        if creatable_models:
            get_ct = ContentType.objects.get_for_model
            role.creatable_ctypes.set([get_ct(model) for model in creatable_models])

        if exportable_models:
            get_ct = ContentType.objects.get_for_model
            role.exportable_ctypes.set([get_ct(model) for model in exportable_models])

        return role

    @classmethod
    def get_root_user(cls) -> CremeUser:
        # Should exist (see 'creme_core.populate.py')
        return CremeUser.objects.get(username=ROOT_USERNAME)

    def login_as_root(self) -> None:
        # Should exist (see 'creme_core.populate.py')
        self.client.login(username=ROOT_USERNAME, password=ROOT_PASSWORD)

    def login_as_root_and_get(self) -> CremeUser:
        self.login_as_root()
        return self.get_root_user()

    def login_as_super(self,
                       is_staff=False,
                       index: int = 0,
                       password: str = 'test',
                       ) -> CremeUser:
        user = self.create_user(index=index, is_staff=is_staff, password=password)

        logged = self.client.login(username=user.username, password=password)
        self.assertTrue(logged, 'Not logged in')

        return user

    def login_as_standard(self, *,
                          allowed_apps: Iterable[str] = ('creme_core',),
                          admin_4_apps: Iterable[str] = (),
                          creatable_models: Iterable[type[CremeEntity]] = (),
                          exportable_models: Iterable[type[CremeEntity]] = (),
                          index: int = 0,
                          password: str = 'test',
                          ) -> CremeUser:
        role = self.create_role(
            name='Basic',
            allowed_apps=allowed_apps,
            admin_4_apps=admin_4_apps,
            creatable_models=creatable_models,
            exportable_models=exportable_models,
        )
        user = self.create_user(index=index, role=role, password=password)

        logged = self.client.login(username=user.username, password=password)
        self.assertTrue(logged, 'Not logged in')

        return user

    def login(self, is_superuser=True, is_staff=False, allowed_apps=('creme_core',),
              creatable_models=None, admin_4_apps=()):
        warnings.warn(
            f'The method {type(self).__name__}.login() is deprecated;'
            f'use the methods login_as_*() instead.',
            DeprecationWarning
        )
        self.password = password = 'test'

        superuser = self.create_user(
            index=0,
            is_staff=is_staff,
        )

        role = UserRole(name='Basic')
        role.allowed_apps = allowed_apps
        role.admin_4_apps = admin_4_apps
        role.save()

        if creatable_models is not None:
            get_ct = ContentType.objects.get_for_model
            role.creatable_ctypes.set([get_ct(model) for model in creatable_models])

        self.role = role

        basic_user = self.create_user(
            index=1,
            role=role,
        )

        self.user, self.other_user = (
            superuser, basic_user,
        ) if is_superuser else (
            basic_user, superuser,
        )

        logged = self.client.login(username=self.user.username, password=password)
        self.assertTrue(logged, 'Not logged in')

        return self.user

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
        delta = max(dt1, dt2) - min(dt1, dt2)

        if delta > timedelta(seconds=seconds):
            self.fail(f'<{dt1}> & <{dt2}> are not almost equal: delta is <{delta}>')

    def assertDoesNotExist(self, instance):
        model = instance.__class__

        try:
            model.objects.get(pk=instance.pk)
        except model.DoesNotExist:
            return

        self.fail('Your object still exists.')

    def assertStillExists(self, instance):
        model = instance.__class__

        pk = instance.pk
        self.assertIsNotNone(pk)

        try:
            return model.objects.get(pk=pk)
        except model.DoesNotExist:
            self.fail('Your object does not exist any more.')

    def assertGET(self, expected_status, *args, **kwargs):
        response = self.client.get(*args, **kwargs)
        # self.assertEqual(expected_status, response.status_code)
        code = response.status_code
        if expected_status != code:
            error_msg = response.context.get('exception') if response.context else None
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
        self.assertEqual(expected_status, response.status_code)

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
            if k == 'length':
                if length != v:
                    self.fail(f'This dict has not the expected length of {v}: {o}')
            elif k == 'min_length':
                if length < v:
                    self.fail(f'This dict is not longer than {v}: {o}')
            elif k == 'max_length':
                if length > v:
                    self.fail(f'This dict is not shorter than {v}: {o}')
            else:
                raise ValueError(f'assertIsDict: unknown argument "{k}"')

    def assertIsList(self, o, **kwargs):
        self.assertIsInstance(o, list)

        length = len(o)
        for k, v in kwargs.items():
            if k == 'length':
                if length != v:
                    self.fail(f'This list has not the expected length of {v}: {o}')
            elif k == 'min_length':
                if length < v:
                    self.fail(f'This list is not longer than {v}: {o}')
            elif k == 'max_length':
                if length > v:
                    self.fail(f'This list is not shorter than {v}: {o}')
            else:
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
        for i, (choice_value, choice_label) in enumerate(choices):
            if value == choice_value:
                if choice_label != label:
                    self.fail(
                        f'The choice "{value}" has been found, but with the '
                        f'label "{choice_label}", not "{label}".'
                    )

                return i

        self.fail(
            'The choice "{value}" has not been found in {values}.'.format(
                value=value,
                values=[c[0] for c in choices],
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

    def assertFormInstanceErrors(self, form, *errors):
        form_errors = form.errors
        field_names = set()

        for field_name, message in errors:
            # TODO: test all the errors in the field
            if field_name not in form_errors:
                self.fail(
                    'The error "{field}" has not been found in the form '
                    '(fields: {fields})'.format(
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

    def assertHasProperty(self, entity: CremeEntity | int, ptype: CremePropertyType | str):
        if not CremeProperty.objects.filter(
            type_id=ptype.id if isinstance(ptype, CremePropertyType) else ptype,
            creme_entity_id=entity.id if isinstance(entity, CremeEntity) else entity,
        ).exists():
            self.fail(f'<{entity}> has no property with type <{ptype}>')

    def assertHasNoProperty(self, entity: CremeEntity | int, ptype: CremePropertyType | str):
        if CremeProperty.objects.filter(
            type_id=ptype.id if isinstance(ptype, CremePropertyType) else ptype,
            creme_entity_id=entity.id if isinstance(entity, CremeEntity) else entity,
        ).exists():
            self.fail(f'<{entity}> has property with type <{ptype}>')

    def assertRelationCount(self, count, subject_entity, type_id, object_entity):
        self.assertEqual(
            count,
            Relation.objects.filter(
                subject_entity=subject_entity.id,
                type=type_id,
                object_entity=object_entity.id,
            ).count(),
        )

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

    def assertXMLEqualv2(self, expected, actual):
        """Compare 2 strings representing XML document, with the XML semantic.
        @param expected XML string ;
               tip: better if it is well indented to have better error message.
        @param actual XML string.
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

    # def build_filedata(self, content_str, suffix='.txt'):
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

    # def build_request(self, url='/', user=None):
    def build_request(self, *, url='/', user=None):
        request = self.request_factory.get(url)
        request.session = SessionBase()
        # request.user = user or self.user

        if user is None:
            warnings.warn(
                f'Passing no "user" argument to the method '
                f'{type(self).__name__}.build_request() is deprecated.',
                DeprecationWarning
            )
            request.user = self.user
        else:
            request.user = user

        return request

    # TODO: @classmethod (build_request() too)
    def build_context(self, user, url=None, instance=None):
        from django.template.context import make_context
        from django.template.engine import Engine

        if not url:
            url = reverse('creme_core__home') if instance is None else instance.get_absolute_url()

        request = self.build_request(url=url, user=user)

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
                                 sub_models=(), obj_models=(),
                                 sub_props=(), obj_props=(),
                                 ):
        try:
            rt = RelationType.objects.get(pk=pk)
        except RelationType.DoesNotExist:
            self.fail(f'Bad populate: RelationType with pk={pk} cannot be found')

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
            sub_props, rt.subject_properties.values_list('id', flat=True),
        )
        self.assertCountEqual(
            obj_props, rt.object_properties.values_list('id', flat=True),
        )

        self.assertNotEqual(
            rt.pk, rt.symmetric_type_id,
            'Be careful your type is its own symmetric type'
        )  # Common error

        return rt

    def get_propertytype_or_fail(self, pk, models=()):
        try:
            pt = CremePropertyType.objects.get(pk=pk)
        except CremePropertyType.DoesNotExist:
            self.fail(f'Bad populate: unfoundable CremePropertyType with pk={pk}')

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

    # @staticmethod
    # def http_file(file_path):
    #     """Get the HTTP URL to retrieve a static file.
    #     @param file_path: path ('/' separated) relative to "creme/"'s parent.
    #     """
    #     from creme.creme_core.utils.test import http_port
    #     return f'http://localhost:{http_port()}/{file_path}'


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
