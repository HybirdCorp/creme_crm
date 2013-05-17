# -*- coding: utf-8 -*-

from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.forms.formsets import BaseFormSet

from ..models import UserRole, RelationType, Relation, CremePropertyType
from ..management.commands.creme_populate import Command as PopulateCommand
from ..utils.xml_utils import xml_diff, XMLDiffError
from ..registry import creme_registry
from .. import autodiscover


class _AssertNoExceptionContext(object):
    """A context manager used by CremeTestCase.assertNoException method."""
    def __init__(self, test_case):
        self.exception = test_case.failureException

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type:
            raise self.exception('An exception <%s> occured: %s' % (exc_type.__name__, exc_value))

        return True


class _CremeTestCase(object):
    def login(self, is_superuser=True, allowed_apps=('creme_core',), creatable_models=None, admin_4_apps=()):
        password = 'test'

        superuser = User.objects.create(username='Kirika')
        superuser.set_password(password)
        superuser.is_superuser = True
        superuser.save()

        role = UserRole.objects.create(name='Basic')
        role.allowed_apps = allowed_apps
        role.admin_4_apps = admin_4_apps
        role.save()

        if creatable_models is not None:
            role.creatable_ctypes = [ContentType.objects.get_for_model(model) for model in creatable_models]

        self.role = role
        basic_user = User.objects.create(username='Mireille', role=role)
        basic_user.set_password(password)
        basic_user.save()

        self.user, self.other_user = (superuser, basic_user) if is_superuser else \
                                     (basic_user, superuser)

        logged = self.client.login(username=self.user.username, password=password)
        self.assertTrue(logged, 'Not logged in')

    @classmethod
    def populate(cls, *args):
        PopulateCommand().handle(application=args)

    @staticmethod
    def autodiscover():
        if not list(creme_registry.iter_apps()):
            autodiscover()

    def assertGET(self, expected_status, *args, **kwargs):
        response = self.client.get(*args, **kwargs)
        self.assertEqual(expected_status, response.status_code)

        return response

    def assertGET200(self, *args, **kwargs):
        return self.assertGET(200, *args, **kwargs)

    def assertGET403(self, *args, **kwargs):
        return self.assertGET(403, *args, **kwargs)

    def assertGET404(self, *args, **kwargs):
        return self.assertGET(404, *args, **kwargs)

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

    def assertRedirectsToLogin(self, response, url):
        self.assertRedirects(response, 'http://testserver/creme_login/?next=%s' % url)

    def assertGETRedirectsToLogin(self, url):
        self.assertRedirectsToLogin(self.client.get(url), url)

    def assertPOSTRedirectsToLogin(self, url, data):
        self.assertRedirectsToLogin(self.client.post(url, data=data), url)

    def assertNoException(self, function=None, *args, **kwargs):
        if function is None:
            return _AssertNoExceptionContext(self)

        try:
            function(*args, **kwargs)
        except Exception as e:
            raise self.failureException('An exception <%s> occured: %s' % (e.__class__.__name__, e))

    def assertFormSetError(self, response, form, index, fieldname, expected_errors=None):
        """Warning : this method has not the same behaviour than assertFormError()
        It checks both error and no error tests.
        """
        self.assertIn(form, response.context)
        fieldname = fieldname or '__all__'

        self.assertIsInstance(response.context[form], BaseFormSet, "context field '%s' is not a FormSet")
        self.assertGreaterEqual(index, 0)

        all_errors = response.context[form].errors

        if not all_errors:
            if expected_errors:
                self.fail("The field '%s' on formset '%s' number %d contains no errors, expected:%s" % (
                            fieldname, form, index, expected_errors
                        )
                     )
            return

        self.assertLess(index, len(all_errors))

        errors = all_errors[index]
        has_field_error = fieldname in errors.keys()

        if not has_field_error and not expected_errors:
            return

        if not has_field_error and expected_errors:
            self.fail("The field '%s' on formset '%s' number %d contains no errors, expected:%s" % (
                            fieldname, form, index, expected_errors
                        )
                     )

        if has_field_error and not expected_errors:
            self.fail("The field '%s' on formset '%s' number %d contains errors:%s, expected none" % (
                            fieldname, form, index, errors[fieldname]
                        )
                     )

        self.assertItemsEqual(expected_errors, errors[fieldname],
                              "The field '%s' on formset '%s' number %d errors are:%s, expected:%s" % (
                                    fieldname, form, index, errors[fieldname], expected_errors
                                )
                             )

    def assertNoFormError(self, response, status=200, form='form'):
        status_code = response.status_code

        if status_code != status:
            self.fail('Response status=%s (expected: %s)' % (status_code, status))

        try:
            errors = response.context[form].errors
        except Exception:
            pass
        else:
            if errors:
                self.fail(errors.as_text())

    def assertListContainsSubset(self, expected, actual, msg=None):
        "Checks whether actual is a superset of expected."
        old_index = -1

        for elt in expected:
            try:
                index = actual.index(elt)
            except ValueError:
                self.fail(self._formatMessage(msg, u'Element not found in the superset : "%s"' % elt))

            if index <= old_index:
                self.fail(self._formatMessage(msg, u'Order is different in the superset (problem with element : "%s")' % elt))

            old_index = index

    def assertRelationCount(self, count, subject_entity, type_id, object_entity):
        self.assertEqual(count,
                         Relation.objects.filter(subject_entity=subject_entity.id,
                                                 type=type_id,
                                                 object_entity=object_entity.id)
                                         .count()
                        )

    def assertXMLEqual(self, expected, actual):
        """Compare 2 strings representing XML document, with the XML semantic.
        @param expected XML string ; tip: better if it is well indented to have better error message.
        @param actual XML string.
        """
        try:
            diff = xml_diff(expected, actual)
        except XMLDiffError as e:
            raise self.failureException('Bad XML document [%s]' % e)

        if diff is not None:
            msg = diff.long_msg

            if self.maxDiff is not None and len(msg) > self.maxDiff:
                msg = '%s\n[maxDiff too small for larger message]' % diff.short_msg

            raise self.failureException('XML are not equal\n%s' % msg)

    def get_object_or_fail(self, model, **kwargs):
        try:
            obj = model.objects.get(**kwargs)
        except model.DoesNotExist as e:
            self.fail('Your object does not exist.\n'
                      ' Query model: %(model)s\n'
                      ' Query args %(args)s\n'
                      ' [original exception: %(exception)s]' % {
                            'model':     model,
                            'args':      kwargs,
                            'exception': e,
                         }
                     )
        except Exception as e:
            self.fail(str(e))

        return obj

    def get_relationtype_or_fail(self, pk, sub_models=(), obj_models=(), sub_props=(), obj_props=()):
        try:
            rt = RelationType.objects.get(pk=pk)
        except RelationType.DoesNotExist:
            self.fail('Bad populate: unfoundable RelationType with pk=%s' % pk)

        get_ct = ContentType.objects.get_for_model
        self.assertListEqual(sorted((get_ct(model) for model in sub_models), key=lambda ct: ct.id),
                             list(rt.subject_ctypes.order_by('id'))
                            )
        self.assertListEqual(sorted((get_ct(model) for model in obj_models), key=lambda ct: ct.id),
                             list(rt.object_ctypes.order_by('id'))
                            )

        self.assertEqual(set(sub_props), set(rt.subject_properties.values_list('id', flat=True)))
        self.assertEqual(set(obj_props), set(rt.object_properties.values_list('id', flat=True)))

        self.assertNotEqual(rt.pk, rt.symmetric_type_id, 'Be careful your type is its own symmetric type') #Common error

        return rt

    def get_propertytype_or_fail(self, pk, models=()):
        try:
            pt = CremePropertyType.objects.get(pk=pk)
        except CremePropertyType.DoesNotExist:
            self.fail('Bad populate: unfoundable CremePropertyType with pk=%s' % pk)

        get_ct = ContentType.objects.get_for_model
        self.assertEqual(set(get_ct(model).id for model in models),
                         set(pt.subject_ctypes.values_list('id', flat=True))
                        )
        return pt

    def refresh(self, obj):
        return obj.__class__.objects.get(pk=obj.pk)


class CremeTestCase(_CremeTestCase, TestCase): pass

class CremeTransactionTestCase(_CremeTestCase, TransactionTestCase): pass
