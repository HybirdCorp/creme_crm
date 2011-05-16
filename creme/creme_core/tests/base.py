# -*- coding: utf-8 -*-

from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import UserRole
from creme_core.management.commands.creme_populate import Command as PopulateCommand


class CremeTestCase(TestCase):
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
        self.assert_(logged, 'Not logged in')

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
