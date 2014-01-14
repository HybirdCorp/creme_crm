# -*- coding: utf-8 -*-
try:
    import json

    from django.utils.translation import ugettext as _
    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType

    from .base import ViewsTestCase
    from creme.creme_core.models import CustomField, CustomFieldEnumValue

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
        self.assertContains(response, "You are not allowed to acceed to the app 'persons'", status_code=404)

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

    def test_userfilter_list(self):
        self.login()

        response = self.assertGET200('/creme_core/enumerable/userfilter/json')
        self.assertEqual([['__currentuser__', _('Current user')]] +
                         [[u.id, unicode(u)] for u in User.objects.all()],
                         json.loads(response.content)
                        )

    def test_custom_enum_not_exists(self):
        self.login()

        url  = '/creme_core/enumerable/custom/%s/json' % 666
        response = self.assertGET404(url)
        self.assertContains(response, 'No CustomField matches the given query', status_code=404)

    def test_custom_enum(self):
        self.login()

        custom_field = CustomField.objects.create(name='Eva', content_type=ContentType.objects.get_for_model(Contact), field_type=CustomField.ENUM)
        create_evalue = CustomFieldEnumValue.objects.create
        eva00 = create_evalue(custom_field=custom_field, value='Eva-00')
        eva01 = create_evalue(custom_field=custom_field, value='Eva-01')
        eva02 = create_evalue(custom_field=custom_field, value='Eva-02')

        url  = '/creme_core/enumerable/custom/%s/json' % custom_field.id
        response = self.assertGET200(url)
        self.assertEquals([[eva00.id, eva00.value],
                           [eva01.id, eva01.value],
                           [eva02.id, eva02.value]
                          ], json.loads(response.content))
