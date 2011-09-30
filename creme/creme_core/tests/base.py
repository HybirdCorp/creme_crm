# -*- coding: utf-8 -*-

from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import UserRole, RelationType, CremePropertyType
from creme_core.management.commands.creme_populate import Command as PopulateCommand


class _CremeTestCase(object):
    def login(self, is_superuser=True, allowed_apps=('creme_core',), creatable_models=None):
        password = 'test'

        superuser = User.objects.create(username='Kirika')
        superuser.set_password(password)
        superuser.is_superuser = True
        superuser.save()

        role = UserRole.objects.create(name='Basic')
        role.allowed_apps = allowed_apps
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

    def populate(self, *args):
        PopulateCommand().handle(application=args)

    def assertNoFormError(self, response):
        try:
            errors = response.context['form'].errors
        except Exception, e:
            pass
        else:
            if errors:
                self.fail(errors)

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


class CremeTestCase(_CremeTestCase, TestCase): pass

class CremeTransactionTestCase(_CremeTestCase, TransactionTestCase): pass
