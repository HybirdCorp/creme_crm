from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core import models
from creme.creme_core.core.entity_filter import operators
from creme.creme_core.core.entity_filter.condition_handler import (
    RegularFieldConditionHandler,
)

from ..base import CremeTestCase


class EnumerableViewsTestCase(CremeTestCase):
    @staticmethod
    def _build_choices_url(model, field_name):
        return reverse(
            'creme_core__enumerable_choices',
            args=(ContentType.objects.get_for_model(model).id, field_name),
        )

    def test_choices__invalid_limit(self):
        self.login_as_root()
        url = self._build_choices_url(models.FakeContact, 'civility')
        self.assertGET(400, f'{url}?limit=NaN')

    def test_choices__missing_only(self):
        self.login_as_root()
        mister = self.get_object_or_fail(models.FakeCivility, title='Mister')
        url = self._build_choices_url(models.FakeContact, 'civility')

        response = self.assertGET200(f'{url}?only=99999')
        self.assertListEqual([], response.json())

        response = self.assertGET200(f'{url}?only={mister.pk},99999')
        self.assertListEqual([
            {'value': mister.pk, 'label': str(mister)}
        ], response.json())

    def test_choices__fk_to_minion(self):
        "Minion is registered in creme_config."
        self.login_as_root()

        mister = self.get_object_or_fail(models.FakeCivility, title='Mister')
        miss = self.get_object_or_fail(models.FakeCivility, title='Miss')

        expected = [
            {'value': id, 'label': title}
            for id, title in models.FakeCivility.objects.values_list('id', 'title')
        ]

        url = self._build_choices_url(models.FakeContact, 'civility')
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.json()

        self.assertListEqual(expected, choices)

        # ---
        response = self.assertGET200(f'{url}?limit=2')

        with self.assertNoException():
            self.assertListEqual(expected[:2], response.json())

        # ---
        response = self.assertGET200(f'{url}?term=Mister')

        with self.assertNoException():
            choices = response.json()

        self.assertListEqual([{'value': mister.id, 'label': str(mister)}], choices)

        # ---
        response = self.assertGET200(f'{url}?only={mister.pk},{miss.pk}')

        with self.assertNoException():
            choices = response.json()

        self.assertListEqual(
            [
                {'value': miss.id, 'label': str(miss)},
                {'value': mister.id, 'label': str(mister)},
            ],
            choices,
        )

    def test_choices__m2m_to_minion(self):
        "Minion is registered in creme_config."
        self.login_as_root()
        response = self.assertGET200(self._build_choices_url(models.FakeImage, 'categories'))
        self.assertListEqual(
            [
                {'value': id, 'label': name}
                for id, name in models.FakeImageCategory.objects.values_list('id', 'name')
            ],
            response.json(),
        )

    def test_choices__limited_choices_to(self):
        self.login_as_root()

        create_lang = models.Language.objects.create
        lang1 = create_lang(name='Klingon [deprecated]')
        lang2 = create_lang(name='Namek')

        response = self.assertGET200(
            self._build_choices_url(models.FakeContact, 'languages')
        )

        ids = {t['value'] for t in response.json()}
        self.assertIn(lang2.id, ids)
        self.assertNotIn(lang1.id, ids)

    def test_choices__fk_to_entityfilter(self):
        "Model is EntityFilter."
        user = self.login_as_root_and_get()

        create_filter = models.EntityFilter.objects.smart_update_or_create
        build_cond = RegularFieldConditionHandler.build_condition
        efilter1 = create_filter(
            'test-filter01',
            name='Filter 01',
            model=models.FakeContact,
            is_custom=True,
            conditions=[
                build_cond(
                    model=models.FakeContact,
                    operator=operators.EQUALS,
                    field_name='first_name',
                    values=['Misato'],
                ),
            ],
        )
        efilter2 = create_filter(
            'test-filter02',
            name='Filter 02',
            model=models.FakeOrganisation,
            is_custom=True, user=user, is_private=True,
            conditions=[
                build_cond(
                    model=models.FakeOrganisation,
                    operator=operators.CONTAINS,
                    field_name='name',
                    values=['NERV'],
                ),
            ],
        )

        response = self.assertGET200(
            self._build_choices_url(models.FakeReport, 'efilter')
        )

        with self.assertNoException():
            choices = response.json()

        self.assertIsList(choices, min_length=2)

        first_choice = choices[0]
        self.assertIsInstance(first_choice, dict)
        self.assertIn('value', first_choice)

        def find_efilter_dict(efilter):
            return self.get_alone_element(
                c for c in choices if c['value'] == efilter.id
            )

        self.assertDictEqual(
            {
                'value': efilter1.pk,
                'label': efilter1.name,
                'help': '',
                'group': 'Test Contact',
            },
            find_efilter_dict(efilter1),
        )
        self.assertDictEqual(
            {
                'value': efilter2.pk,
                'label': efilter2.name,
                'help': _('Private ({})').format(user),
                'group': 'Test Organisation',
            },
            find_efilter_dict(efilter2),
        )

    def test_choices__entityctypefk(self):
        "Field is a EntityCTypeForeignKey."
        self.login_as_root()

        response = self.assertGET200(self._build_choices_url(models.FakeReport, 'ctype'))
        choices = response.json()
        self.assertTrue(choices)
        self.assertIsInstance(choices[0], dict)

        get_ct = ContentType.objects.get_for_model

        def find_ctype_label(model):
            ctype_id = get_ct(model).id
            choice = self.get_alone_element(t for t in choices if t['value'] == ctype_id)
            self.assertEqual(2, len(choice))
            return choice['label']

        self.assertEqual('Test Contact',      find_ctype_label(models.FakeContact))
        self.assertEqual('Test Organisation', find_ctype_label(models.FakeOrganisation))

        civ_ctid = get_ct(models.FakeCivility).id
        self.assertFalse([t for t in choices if t['value'] == civ_ctid])

    def test_choices__fk_to_entity(self):
        "Model is a CremeEntity (credentials have to be used)."
        user = self.login_as_standard()
        self.add_credentials(user.role, own=['VIEW'])

        create_img = models.FakeImage.objects.create
        img1 = create_img(name='Img #1', user=user)
        img2 = create_img(name='Img #2', user=user)
        img3 = create_img(name='Img #3', user=self.get_root_user())

        self.assertTrue(user.has_perm_to_view(img1))
        self.assertTrue(user.has_perm_to_view(img2))
        self.assertFalse(user.has_perm_to_view(img3))

        response = self.assertGET200(self._build_choices_url(models.FakeContact, 'image'))
        dict_choices = response.json()
        self.assertIsList(dict_choices, length=2)

        choices = []
        for d in dict_choices:
            self.assertIsInstance(d, dict)
            with self.assertNoException():
                choices.append((d['value'], d['label']))

        self.assertInChoices(value=img1.id, label=img1.name, choices=choices)
        self.assertInChoices(value=img2.id, label=img2.name, choices=choices)

        self.assertNotInChoices(value=img3.id, choices=choices)

    def test_choices__fk_to_role(self):
        self.login_as_root()

        role1 = self.get_regular_role()
        role2 = self.create_role(name=f'{role1.name} but better')

        response = self.assertGET200(self._build_choices_url(models.CremeUser, 'role'))

        with self.assertNoException():
            choices = response.json()

        self.assertListEqual(
            [
                {'value': role1.id, 'label': role1.name},
                {'value': role2.id, 'label': role2.name},
            ],
            choices,
        )

    def test_choices__POST(self):
        self.login_as_root()
        self.assertPOST405(self._build_choices_url(models.FakeContact, 'civility'))

    def test_choices__not_entity_model(self):
        self.login_as_root()
        self.assertContains(
            self.client.get(self._build_choices_url(models.FakeIngredient, 'group')),
            'This model is not a CremeEntity: creme.creme_core.tests.fake_models.FakeIngredient',
            status_code=409,
        )

    def test_choices__not_viewable(self):
        self.login_as_root()
        self.assertContains(
            self.client.get(self._build_choices_url(models.FakeAddress, 'entity')),
            'This field is not viewable: creme_core.FakeAddress.entity',
            status_code=409,
        )

    def test_choices__no_app_credentials(self):
        self.login_as_standard(allowed_apps=['creme_config'])
        self.assertContains(
            self.client.get(
                self._build_choices_url(models.FakeContact, 'civility'),
                headers={'X-Requested-With': 'XMLHttpRequest'},
            ),
            _('You are not allowed to access to the app: {}').format(_('Core')),
            status_code=403,
        )

    def test_choices__field_does_not_exist(self):
        self.login_as_root()
        self.assertContains(
            self.client.get(self._build_choices_url(models.FakeContact, 'unknown')),
            'This field does not exist.',
            status_code=404,
        )

    def test_custom_enum__does_not_exist(self):
        self.login_as_root()

        response = self.assertGET404(reverse('creme_core__cfield_enums', args=(666,)))
        self.assertContains(response, 'No CustomField matches the given query', status_code=404)

    def test_custom_enum(self):
        self.login_as_root()

        custom_field = models.CustomField.objects.create(
            name='Eva',
            field_type=models.CustomField.ENUM,
            content_type=models.FakeContact,
        )

        create_evalue = models.CustomFieldEnumValue.objects.create
        eva00 = create_evalue(custom_field=custom_field, value='Eva-00')
        eva01 = create_evalue(custom_field=custom_field, value='Eva-01')
        eva02 = create_evalue(custom_field=custom_field, value='Eva-02')

        response = self.assertGET200(
            reverse('creme_core__cfield_enums', args=(custom_field.id,))
        )
        self.assertListEqual(
            [
                {'value': eva00.id, 'label': eva00.value},
                {'value': eva01.id, 'label': eva01.value},
                {'value': eva02.id, 'label': eva02.value},
            ],
            response.json(),
        )
