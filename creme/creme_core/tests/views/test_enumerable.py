# -*- coding: utf-8 -*-
try:
    # from django.contrib.auth import get_user_model
    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse
    from django.utils.translation import gettext as _

    from .base import ViewsTestCase
    from creme.creme_core import models
    # from creme.creme_core.utils.unicode_collation import collator
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class EnumerableViewsTestCase(ViewsTestCase):
    # def _build_enum_url(self, model):
    #     return reverse('creme_core__list_enumerable', args=(ContentType.objects.get_for_model(model).id,))

    def _build_choices_url(self, model, field_name):
        return reverse('creme_core__enumerable_choices',
                       args=(ContentType.objects.get_for_model(model).id, field_name),
                      )

    # def test_list_enum_model_not_registered(self):
    #     self.login()
    #
    #     url = self._build_enum_url(models.FakeContact)
    #     response = self.assertGET404(url)
    #     self.assertContains(response, 'Content type is not registered in config', status_code=404)
    #
    # def test_list_enum_model_app_not_allowed(self):
    #     user = self.login(is_superuser=False, allowed_apps=('documents',))  # not 'creme_core'
    #
    #     self.assertFalse(user.has_perm(ContentType.objects.get_for_model(models.FakeCivility).app_label))
    #
    #     url = self._build_enum_url(models.FakeCivility)
    #     response = self.assertGET404(url)
    #     self.assertContains(response, "You are not allowed to access to the app 'creme_core'", status_code=404)
    #
    # def test_list_enum_contenttype_not_exists(self):
    #     self.login()
    #
    #     url = reverse('creme_core__list_enumerable', args=(1045,))
    #     response = self.assertGET404(url)
    #     self.assertContains(response, 'No content type with this id', status_code=404)
    #
    # def test_list_enum_model_enumerable(self):
    #     self.login()
    #
    #     self.assertTrue(self.user.has_perm(ContentType.objects.get_for_model(models.FakeCivility).app_label))
    #
    #     url = self._build_enum_url(models.FakeCivility)
    #     response = self.assertGET200(url)
    #     self.assertEqual([[c.id, str(c)] for c in models.FakeCivility.objects.all()], response.json())
    #
    # def test_list_enum_model_user(self):
    #     self.login()
    #
    #     User = get_user_model()
    #     url = self._build_enum_url(User)
    #     response = self.assertGET200(url)
    #     self.assertEqual([[c.id, str(c)] for c in User.objects.all()], response.json())
    #
    # def test_list_enum_model_contenttype(self):
    #     self.login()
    #
    #     url = self._build_enum_url(ContentType)
    #     response = self.assertGET200(url)
    #
    #     with self.assertNoException():
    #         choices = dict(response.json())
    #
    #     get_ct = ContentType.objects.get_for_model
    #     self.assertEqual(choices.get(get_ct(models.FakeContact).id),      str(models.FakeContact._meta.verbose_name))
    #     self.assertEqual(choices.get(get_ct(models.FakeOrganisation).id), str(models.FakeOrganisation._meta.verbose_name))
    #     self.assertIsNone(choices.get(get_ct(models.FakeCivility).id))
    #
    # def test_model_entityfilter(self):
    #     self.maxDiff = None
    #     user = self.login()
    #
    #     # Create at least one filter
    #     create_filter = models.EntityFilter.create
    #     efilter = create_filter('test-filter01', 'Filter 01', models.FakeContact, is_custom=True)
    #     efilter.set_conditions([models.EntityFilterCondition.build_4_field(
    #                                     model=models.FakeContact,
    #                                     operator=models.EntityFilterCondition.EQUALS,
    #                                     name='first_name', values=['Misato'],
    #                                ),
    #                            ])
    #
    #     efilter_private = create_filter('test-filter02', 'Filter 02', models.FakeContact, is_custom=True,
    #                                     user=user, is_private=True,
    #                                    )
    #     efilter_private.set_conditions([models.EntityFilterCondition.build_4_field(
    #                                         model=models.FakeContact,
    #                                         operator=models.EntityFilterCondition.EQUALS,
    #                                         name='first_name', values=['Misato'],
    #                                       ),
    #                                    ])
    #
    #     response = self.assertGET200(self._build_enum_url(models.EntityFilter))
    #     sort_key = collator.sort_key
    #     self.assertEqual(sorted([{'value': f.id,
    #                               'label': f.name,
    #                               'group': str(f.entity_type),
    #                               'help':  _('Private ({})').format(f.user) if f.is_private else '',
    #                              } for f in models.EntityFilter.objects.all()
    #                             ],
    #                             key=lambda e: sort_key(e['group'] + e['label'])
    #                            ),
    #                      response.json()
    #                     )

    def test_choices_success_fk(self):
        self.login()
        response = self.assertGET200(self._build_choices_url(models.FakeContact, 'civility'))

        with self.assertNoException():
            choices = response.json()

        self.assertEqual([{'value': id, 'label': title}
                              for id, title in models.FakeCivility.objects.values_list('id', 'title')
                         ],
                         choices
                        )

    def test_choices_success_m2m(self):
        self.login()
        response = self.assertGET200(self._build_choices_url(models.FakeImage, 'categories'))
        self.assertEqual([{'value': id, 'label': name}
                              for id, name in models.FakeImageCategory.objects.values_list('id', 'name')
                         ],
                         response.json()
                        )

    def test_choices_success_limited_choices_to(self):
        self.login()

        create_lang = models.Language.objects.create
        lang1 = create_lang(name='Klingon [deprecated]')
        lang2 = create_lang(name='Namek')

        response = self.assertGET200(self._build_choices_url(models.FakeContact, 'languages'))

        ids = {t['value'] for t in response.json()}
        self.assertIn(lang2.id, ids)
        self.assertNotIn(lang1.id, ids)

    def test_choices_success_specific_printer01(self):
        "Model is EntityFilter"
        user = self.login()

        create_filter = models.EntityFilter.create
        build_cond = models.EntityFilterCondition.build_4_field
        efilter1 = create_filter('test-filter01',
                                 name='Filter 01',
                                 model=models.FakeContact,
                                 is_custom=True,
                                 conditions=[build_cond(
                                                model=models.FakeContact,
                                                operator=models.EntityFilterCondition.EQUALS,
                                                name='first_name', values=['Misato'],
                                             ),
                                            ],
                                 )
        efilter2 = create_filter('test-filter02',
                                 name='Filter 02',
                                 model=models.FakeOrganisation,
                                 is_custom=True, user=user, is_private=True,
                                 conditions=[build_cond(
                                                 model=models.FakeOrganisation,
                                                 operator=models.EntityFilterCondition.CONTAINS,
                                                 name='name', values=['NERV'],
                                              ),
                                            ]
                                 )

        response = self.assertGET200(self._build_choices_url(models.FakeReport, 'efilter'))

        with self.assertNoException():
            choices = response.json()

        self.assertIsInstance(choices, list)
        self.assertGreaterEqual(len(choices), 2)

        first_choice = choices[0]
        self.assertIsInstance(first_choice, dict)
        self.assertIn('value', first_choice)

        def find_efilter_dict(efilter):
            efilter_as_dicts = [c for c in choices if c['value'] == efilter.id]
            self.assertEqual(1, len(efilter_as_dicts))
            return efilter_as_dicts[0]

        self.assertEqual({'value': efilter1.pk,
                          'label': efilter1.name,
                          'help': '',
                          'group': 'Test Contact',
                         },
                         find_efilter_dict(efilter1)
                        )
        self.assertEqual({'value': efilter2.pk,
                          'label': efilter2.name,
                          'help': _('Private ({})').format(user),
                          'group': 'Test Organisation',
                         },
                         find_efilter_dict(efilter2)
                        )

    def test_choices_success_specific_printer02(self):
        "Field is a EntityCTypeForeignKey"
        self.login()

        response = self.assertGET200(self._build_choices_url(models.FakeReport, 'ctype'))
        choices = response.json()
        self.assertTrue(choices)
        self.assertIsInstance(choices[0], dict)

        get_ct = ContentType.objects.get_for_model

        def find_ctype_label(model):
            ctype_id = get_ct(model).id
            ctype_as_lists = [t for t in choices if t['value'] == ctype_id]
            self.assertEqual(1, len(ctype_as_lists))
            choice = ctype_as_lists[0]
            self.assertEqual(2, len(choice))
            return choice['label']

        self.assertEqual('Test Contact',      find_ctype_label(models.FakeContact))
        self.assertEqual('Test Organisation', find_ctype_label(models.FakeOrganisation))

        civ_ctid = get_ct(models.FakeCivility).id
        self.assertFalse([t for t in choices if t['value'] == civ_ctid])

    def test_choices_POST(self):
        self.login()
        self.assertPOST405(self._build_choices_url(models.FakeContact, 'civility'))

    def test_choices_not_entity_model(self):
        self.login()
        response = self.assertGET409(self._build_choices_url(models.FakeAddress, 'entity'))
        self.assertIn('This model is not a CremeEntity: creme.creme_core.tests.fake_models.FakeAddress',
                      response.content.decode()
                     )

    def test_choices_no_app_credentials(self):
        self.login(is_superuser=False, allowed_apps=['creme_config'])
        response = self.assertGET403(self._build_choices_url(models.FakeContact, 'civility'),
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                                    )
        self.assertIn(_('You are not allowed to access to the app: {}').format(_('Core')),
                      response.content.decode()
                     )

    def test_choices_field_does_not_exist(self):
        self.login()
        response = self.assertGET404(self._build_choices_url(models.FakeContact, 'unknown'))
        self.assertIn('This field does not exist.', response.content.decode())

    # def test_userfilter_list(self):
    #     self.login()
    #
    #     response = self.assertGET200(reverse('creme_core__efilter_user_choices'))
    #     self.assertEqual([['__currentuser__', _('Current user')]] +
    #                      [[u.id, str(u)] for u in get_user_model().objects.all()],
    #                      response.json()
    #                     )

    def test_custom_enum_not_exists(self):
        self.login()

        response = self.assertGET404(reverse('creme_core__cfield_enums', args=(666,)))
        self.assertContains(response, 'No CustomField matches the given query', status_code=404)

    def test_custom_enum(self):
        self.login()

        custom_field = models.CustomField.objects.create(
            name='Eva',
            field_type=models.CustomField.ENUM,
            content_type=models.FakeContact,
        )

        create_evalue = models.CustomFieldEnumValue.objects.create
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
