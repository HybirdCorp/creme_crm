# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from os import remove as delete_file, listdir, makedirs
from os import path as os_path
from unittest import skipIf
from unittest.util import safe_repr
import warnings

from django.test import TestCase, TransactionTestCase
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db.models.query_utils import Q
from django.forms.formsets import BaseFormSet
from django.utils.timezone import utc, get_current_timezone, make_aware

from ..global_info import clear_global_info
from ..management.commands.creme_populate import Command as PopulateCommand
from ..models import CremeUser, UserRole, RelationType, Relation, CremePropertyType
from ..utils import print_traceback
from ..utils.xml_utils import xml_diff, XMLDiffError


def skipIfNotInstalled(app_name):
    return skipIf(not apps.is_installed(app_name),
                  "Skip this test which is related to the uninstalled app '%s'" % app_name
                 )


class _AssertNoExceptionContext(object):
    """A context manager used by CremeTestCase.assertNoException method."""
    def __init__(self, test_case):
        self.exception = test_case.failureException

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type:
            print_traceback()

            raise self.exception('An exception <%s> occurred: %s' % (exc_type.__name__, exc_value))

        return True


class _CremeTestCase(object):
    # NB: set this line in inherited classes to clean upload/documents directory in tearDown
    # clean_files_in_teardown = True

    @classmethod
    def setUpClass(cls):
        cls.documents_dir = documents_dir = os_path.join(settings.MEDIA_ROOT,
                                                         'upload',
                                                         'documents',
                                                        )

        if os_path.exists(documents_dir):
            cls.existing_doc_files = set(listdir(documents_dir))
        else:
            makedirs(documents_dir, 0755)
            cls.existing_doc_files = set()

        warnings.filterwarnings('error', r"(.)* received a naive datetime (.)*",
                                RuntimeWarning, r'django\.db\.models\.fields',
                               )

    def tearDown(self):
        if getattr(self, 'clean_files_in_teardown', False):
            existing_files = self.existing_doc_files
            dir_path = self.documents_dir

            for filename in listdir(dir_path):
                if filename not in existing_files:
                    delete_file(os_path.join(dir_path, filename))

        clear_global_info()

    def login(self, is_superuser=True, is_staff=False, allowed_apps=('creme_core',),
              creatable_models=None, admin_4_apps=()):
        self.password = password = 'test'

        superuser = CremeUser(username='kirika', email='kirika@noir.jp',
                              first_name='Kirika', last_name='Yumura',
                              is_superuser=True or is_staff,
                              is_staff=is_staff,
                             )
        superuser.set_password(password)
        superuser.save()

        role = UserRole(name='Basic')
        role.allowed_apps = allowed_apps
        role.admin_4_apps = admin_4_apps
        role.save()

        if creatable_models is not None:
            role.creatable_ctypes = [ContentType.objects.get_for_model(model) for model in creatable_models]

        self.role = role

        basic_user = CremeUser(username='mireille', email='mireille@noir.jp', role=role,
                               first_name='Mireille', last_name='Bouquet',
                              )
        basic_user.set_password(password)
        basic_user.save()

        self.user, self.other_user = (superuser, basic_user) if is_superuser else \
                                     (basic_user, superuser)

        logged = self.client.login(username=self.user.username, password=password)
        self.assertTrue(logged, 'Not logged in')

        return self.user

    # @classmethod
    # def populate(cls, *args):
    #     warnings.warn("_CremeTestCase.populate() method is deprecated, "
    #                   "because it's useless if you are not in a CremeTransactionTestCase.",
    #                   DeprecationWarning
    #                  )
    #
    #     PopulateCommand().execute(*args, verbosity=0)

    def assertCountOccurrences(self, member, container, count, msg=None):
        """Like self.assertEqual(count, container.count(member),
        but with a nicer default message.
        """
        occ_count = container.count(member)

        if occ_count != count:
            std_msg = '%(member)s found %(occ)s time(s) in %(container)s (%(exp)s expected)' % {
                            'member':    safe_repr(member),
                            'container': safe_repr(container),
                            'occ': occ_count,
                            'exp': count,
            }
            self.fail(self._formatMessage(msg, std_msg))

    def assertDatetimesAlmostEqual(self, dt1, dt2, seconds=10):
        delta = max(dt1, dt2) - min(dt1, dt2)

        if delta > timedelta(seconds=seconds):
            self.fail('<%s> & <%s> are not almost equal: delta is <%s>' % (
                            dt1, dt2, delta
                        )
                     )

    def assertDoesNotExist(self, instance):
        model = instance.__class__

        try:
            model.objects.get(pk=instance.pk)
        except model.DoesNotExist:
            return

        self.fail('Your object still exists.')

    def assertStillExists(self, instance):
        model = instance.__class__

        try:
            return model.objects.get(pk=instance.pk)
        except model.DoesNotExist:
            self.fail('Your object does not exist any more.')

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

    def assertPOST409(self, *args, **kwargs):
        return self.assertPOST(409, *args, **kwargs)

    def assertFound(self, x, string, msg=None):
        idx = string.find(x)

        if idx == -1:
            std_msg = '%(sub)s not found in %(string)s' % {
                            'sub':    safe_repr(x),
                            'string': safe_repr(string),
            }
            self.fail(self._formatMessage(msg, std_msg))

        return idx

    def assertIndex(self, elt, sequence):
        try:
            index = sequence.index(elt)
        except ValueError:
            self.fail('{0} not found'.format(elt))

        return index

    def assertIsSubclass(self, cls, parent_cls, msg=None):
        if not issubclass(cls, parent_cls):
            if msg is None:
                msg = '{0} is not a subclass of {1} [list of parent classes {2}'.format(cls, parent_cls, cls.__mro__)

            self.fail(msg)

    def assertNoException(self, function=None, *args, **kwargs):
        if function is None:
            return _AssertNoExceptionContext(self)

        try:
            function(*args, **kwargs)
        except Exception as e:
            print_traceback()

            raise self.failureException('An exception <%s> occured: %s' % (e.__class__.__name__, e))

    # TODO: add an argument 'field' like assertNoFormsetError()
    def assertNoFormError(self, response, status=200, form='form'):
        status_code = response.status_code

        if status_code != status:
            self.fail('Response status={status} (expected: {expected}) [redirections={redirect}; content={content}]'.format(
                            status=status_code,
                            expected=status,
                            redirect=response.redirect_chain,
                            content=response.content
                     ))

        try:
            errors = response.context[form].errors
        except Exception:
            pass
        else:
            if errors:
                self.fail(errors.as_text())

    def assertNoFormsetError(self, response, formset, form_index, field=None, status=200):
        """
        @param field Field name (can be '__all__' for gloabl errors) or None
                     (which means 'No error at all').
        """
        status_code = response.status_code

        if status_code != status:
            self.fail('Response status=%s (expected: %s)' % (status_code, status))

        try:
            formset_obj = response.context[formset]
        except Exception:
            pass
        else:
            all_errors = formset_obj.errors

            if not all_errors:
                return

            self.assertIsInstance(formset_obj, BaseFormSet, "context field '%s' is not a FormSet")
            self.assertGreaterEqual(form_index, 0)
            self.assertLess(form_index, len(all_errors))

            errors = all_errors[form_index]

            if field is None:
                if errors:
                    self.fail("The formset '%s' number %d contains errors: %s" % (
                                    formset, form_index, errors
                                )
                             )
            else:
                try:
                    field_errors = errors[field]
                except KeyError:
                    pass
                else:
                    self.fail("The field '%s' on formset '%s' number %d contains errors: %s" % (
                                    field, formset, form_index, field_errors
                                )
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

    def assertQuerysetSQLEqual(self, qs1, qs2):
        self.assertEqual(qs1.query.get_compiler('default').as_sql(),
                         qs2.query.get_compiler('default').as_sql()
                        )

    def assertQEqual(self, q1, q2):
        self.assertIsInstance(q1, Q)
        self.assertIsInstance(q2, Q)
        self.assertEqual(unicode(q1), unicode(q2))

    def assertRelationCount(self, count, subject_entity, type_id, object_entity):
        self.assertEqual(count,
                         Relation.objects.filter(subject_entity=subject_entity.id,
                                                 type=type_id,
                                                 object_entity=object_entity.id)
                                         .count()
                        )

    def assertSameProperties(self, entity1, entity2):
        properties_desc = lambda entity: list(entity.properties.values_list('type', flat=True))

        pd1 = properties_desc(entity1)
        pd2 = properties_desc(entity2)
        self.assertEqual(len(pd1), len(pd2))
        self.assertEqual(set(pd1), set(pd2))

    def assertSameRelations(self, entity1, entity2, exclude_internal=True):
        def relations_desc(entity):
            qs = entity.relations.values_list('type', 'object_entity')

            if exclude_internal:
                qs = qs.exclude(type__is_internal=True)

            return list(qs)

        rd1 = relations_desc(entity1)
        rd2 = relations_desc(entity2)
        self.assertEqual(len(rd1), len(rd2))
        self.assertEqual(set(rd1), set(rd2))

    def assertSameRelationsNProperties(self, entity1, entity2, exclude_internal=True):
        self.assertSameProperties(entity1, entity2)
        self.assertSameRelations(entity1, entity2, exclude_internal)

    def assertXMLEqualv2(self, expected, actual):
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

    def build_merge_url(self, entity1, entity2):
        return reverse('creme_core__merge_entities') + '?id1=%s&id2=%s' % (entity1.id, entity2.id)

    def create_datetime(self, *args, **kwargs):
        tz = utc if kwargs.pop('utc', False) else get_current_timezone()
        return make_aware(datetime(*args, **kwargs), tz)

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
        self.assertEqual({get_ct(model).id for model in models},
                         set(pt.subject_ctypes.values_list('id', flat=True))
                        )
        return pt

    @staticmethod
    def refresh(obj):
        return obj.__class__.objects.get(pk=obj.pk)

    @staticmethod
    def build_inneredit_url(entity, fieldname):
        return reverse('creme_core__inner_edition',
                       args=(ContentType.objects.get_for_model(entity).pk,
                             entity.pk,
                             fieldname,
                            ),
                      )

    # @staticmethod
    # def build_bulkedit_url(entities, fieldname=None):
    #     args = [ContentType.objects.get_for_model(entities[0]).pk,
    #             ','.join(str(e.pk) for e in entities),
    #            ]
    #     if fieldname:
    #         args.append(fieldname)
    #
    #     return reverse('creme_core__bulk_edit_field_legacy', args=args)

    @staticmethod
    def build_bulkupdate_url(model, fieldname=None):
        args = [ContentType.objects.get_for_model(model).id]
        if fieldname:
            args.append(fieldname)

        return reverse('creme_core__bulk_update', args=args)


class CremeTestCase(TestCase, _CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super(CremeTestCase, cls).setUpClass()
        _CremeTestCase.setUpClass()

    def tearDown(self):
        super(CremeTestCase, self).tearDown()
        _CremeTestCase.tearDown(self)


class CremeTransactionTestCase(TransactionTestCase, _CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super(CremeTransactionTestCase, cls).setUpClass()
        _CremeTestCase.setUpClass()

    def tearDown(self):
        super(CremeTransactionTestCase, self).tearDown()
        _CremeTestCase.tearDown(self)

    @classmethod
    def populate(cls, *args):
        PopulateCommand().execute(*args, verbosity=0)
