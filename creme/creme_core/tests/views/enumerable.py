# -*- coding: utf-8 -*-

try:
    import json

    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType

    from .base import ViewsTestCase

    from creme.persons.models import Contact, Civility
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('EnumerableViewsTestCase', )

class EnumerableViewsTestCase(ViewsTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_config')
        cls.autodiscover()

    def _build_enum_url(self, model):
        return '/creme_core/enumerable/%s/json' % ContentType.objects.get_for_model(model).id

    def test_model_not_registered(self):
        self.login()

        url = self._build_enum_url(Contact)
        response = self.assertGET404(url)
        self.assertContains(response, 'Content type is not registered in config', status_code=404)

    def test_model_app_not_allowed(self):
        self.login(is_superuser=False)

        self.assertFalse(self.user.has_perm(ContentType.objects.get_for_model(Civility).app_label))

        url = self._build_enum_url(Civility)
        response = self.assertGET404(url)
        self.assertContains(response, 'You are not allowed to acceed to this app', status_code=404)

    def test_contenttype_not_exists(self):
        self.login()

        url = '/creme_core/enumerable/%d/json' % 1045
        response = self.assertGET404(url)
        self.assertContains(response, 'No content type with this id', status_code=404)

    def test_model_enumerable(self):
        self.login()

        self.assertTrue(self.user.has_perm(ContentType.objects.get_for_model(Civility).app_label))

        url = self._build_enum_url(Civility)
        response = self.assertGET200(url)
        self.assertEqual([[c.id, unicode(c)] for c in Civility.objects.all()], json.loads(response.content))

    def test_model_user(self):
        self.login()

        url = self._build_enum_url(User)
        response = self.assertGET200(url)
        self.assertEqual([[c.id, unicode(c)] for c in User.objects.all()], json.loads(response.content))
