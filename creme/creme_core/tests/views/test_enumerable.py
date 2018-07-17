# -*- coding: utf-8 -*-
try:
    # import json

    from django.contrib.auth import get_user_model
    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse
    from django.utils.translation import ugettext as _

    from .base import ViewsTestCase
    from ..fake_models import FakeContact, FakeCivility
    from creme.creme_core.models import (CustomField, CustomFieldEnumValue,
            EntityFilter, EntityFilterCondition)
    from creme.creme_core.utils.unicode_collation import collator
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class EnumerableViewsTestCase(ViewsTestCase):
    def _build_enum_url(self, model):
        return reverse('creme_core__list_enumerable', args=(ContentType.objects.get_for_model(model).id,))

    def test_model_not_registered(self):
        self.login()

        url = self._build_enum_url(FakeContact)
        response = self.assertGET404(url)
        self.assertContains(response, 'Content type is not registered in config', status_code=404)

    def test_model_app_not_allowed(self):
        user = self.login(is_superuser=False, allowed_apps=('documents',))  # not 'creme_core'

        self.assertFalse(user.has_perm(ContentType.objects.get_for_model(FakeCivility).app_label))

        url = self._build_enum_url(FakeCivility)
        response = self.assertGET404(url)
        self.assertContains(response, "You are not allowed to access to the app 'creme_core'", status_code=404)

    def test_contenttype_not_exists(self):
        self.login()

        url = reverse('creme_core__list_enumerable', args=(1045,))
        response = self.assertGET404(url)
        self.assertContains(response, 'No content type with this id', status_code=404)

    def test_model_enumerable(self):
        self.login()

        self.assertTrue(self.user.has_perm(ContentType.objects.get_for_model(FakeCivility).app_label))

        url = self._build_enum_url(FakeCivility)
        response = self.assertGET200(url)
        self.assertEqual([[c.id, str(c)] for c in FakeCivility.objects.all()], response.json())

    def test_model_user(self):
        self.login()

        User = get_user_model()
        url = self._build_enum_url(User)
        response = self.assertGET200(url)
        self.assertEqual([[c.id, str(c)] for c in User.objects.all()], response.json())

    def test_model_entityfilter(self):
        self.maxDiff = None
        user = self.login()

        # Create at least one filter
        create_filter = EntityFilter.create
        efilter = create_filter('test-filter01', 'Filter 01', FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.EQUALS,
                                                                    name='first_name', values=['Misato'],
                                                                   ),
                               ])

        efilter_private = create_filter('test-filter02', 'Filter 02', FakeContact, is_custom=True,
                                        user=user, is_private=True,
                                       )
        efilter_private.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                            operator=EntityFilterCondition.EQUALS,
                                                                            name='first_name', values=['Misato'],
                                                                           ),
                                       ])

        response = self.assertGET200(self._build_enum_url(EntityFilter))
        sort_key = collator.sort_key
        self.assertEqual(sorted([{'value': f.id,
                                  'label': f.name,
                                  'group': str(f.entity_type),
                                  'help':  str(f.entity_type) + (u' ({})'.format(f.user) if f.is_private else ''),
                                 } for f in EntityFilter.objects.all()
                                ],
                                key=lambda e: sort_key(e['group'] + e['label'])
                               ),
                         response.json()
                        )

    def test_userfilter_list(self):
        self.login()

        response = self.assertGET200(reverse('creme_core__efilter_user_choices'))
        self.assertEqual([['__currentuser__', _(u'Current user')]] +
                         [[u.id, str(u)] for u in get_user_model().objects.all()],
                         response.json()
                        )

    def test_custom_enum_not_exists(self):
        self.login()

        response = self.assertGET404(reverse('creme_core__cfield_enums', args=(666,)))
        self.assertContains(response, 'No CustomField matches the given query', status_code=404)

    def test_custom_enum(self):
        self.login()

        custom_field = CustomField.objects.create(name='Eva', field_type=CustomField.ENUM,
                                                  content_type=ContentType.objects.get_for_model(FakeContact),
                                                 )

        create_evalue = CustomFieldEnumValue.objects.create
        eva00 = create_evalue(custom_field=custom_field, value='Eva-00')
        eva01 = create_evalue(custom_field=custom_field, value='Eva-01')
        eva02 = create_evalue(custom_field=custom_field, value='Eva-02')

        response = self.assertGET200(reverse('creme_core__cfield_enums', args=(custom_field.id,)))
        self.assertEqual([[eva00.id, eva00.value],
                          [eva01.id, eva01.value],
                          [eva02.id, eva02.value]
                         ],
                         response.json()
                        )
