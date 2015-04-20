# -*- coding: utf-8 -*-
try:
    import json

    from django.contrib.auth import get_user_model
    from django.contrib.contenttypes.models import ContentType
    from django.utils.translation import ugettext as _

    from .base import ViewsTestCase
    from ..fake_models import FakeContact as Contact, FakeCivility as Civility
    from creme.creme_core.models import (CustomField, CustomFieldEnumValue,
            EntityFilter, EntityFilterCondition)
    from creme.creme_core.utils.unicode_collation import collator

#    from creme.persons.models import Contact, Civility
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('EnumerableViewsTestCase', )

class EnumerableViewsTestCase(ViewsTestCase):
#    @classmethod
#    def setUpClass(cls):
#        ViewsTestCase.setUpClass()
##        cls.populate('creme_config')
#        cls.autodiscover()

    def _build_enum_url(self, model):
        return '/creme_core/enumerable/%s/json' % ContentType.objects.get_for_model(model).id

    def test_model_not_registered(self):
        self.login()

        url = self._build_enum_url(Contact)
        response = self.assertGET404(url)
        self.assertContains(response, 'Content type is not registered in config', status_code=404)

    def test_model_app_not_allowed(self):
#        self.login(is_superuser=False)
        user = self.login(is_superuser=False, allowed_apps=('documents',)) # not 'creme_core'

        self.assertFalse(user.has_perm(ContentType.objects.get_for_model(Civility).app_label))

        url = self._build_enum_url(Civility)
        response = self.assertGET404(url)
#        self.assertContains(response, "You are not allowed to access to the app 'persons'", status_code=404)
        self.assertContains(response, "You are not allowed to access to the app 'creme_core'", status_code=404)

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

        User = get_user_model()
        url = self._build_enum_url(User)
        response = self.assertGET200(url)
        self.assertEqual([[c.id, unicode(c)] for c in User.objects.all()], json.loads(response.content))

    def test_model_entityfilter(self):
        self.login()

        sort_key = collator.sort_key
        key = lambda e: sort_key(e[2] + e[1])

        # create at least one filter
        efilter = EntityFilter.create('test-filter01', 'Filter 01', Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.EQUALS,
                                                                    name='first_name', values=['Misato']
                                                                   )
                               ])

        efilter_private = EntityFilter.create('test-filter02', 'Filter 02', Contact, user=self.user, is_custom=True, is_private=True)
        efilter_private.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                            operator=EntityFilterCondition.EQUALS,
                                                                            name='first_name', values=['Misato']
                                                                            )
                               ])

        url = self._build_enum_url(EntityFilter)
        response = self.assertGET200(url)
        self.assertEqual(sorted([[f.id,
                                  '%s [%s]%s' % (f.name, unicode(f.entity_type), (' (%s)' % unicode(f.user) if f.is_private else '')),
                                  unicode(f.entity_type)
                                 ] for f in EntityFilter.objects.all()
                                ],
                                key=key
                               ),
                         json.loads(response.content)
                        )

    def test_userfilter_list(self):
        self.login()

        response = self.assertGET200('/creme_core/enumerable/userfilter/json')
        self.assertEqual([['__currentuser__', _('Current user')]] +
                         [[u.id, unicode(u)] for u in get_user_model().objects.all()],
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
                          ],
                          json.loads(response.content))

