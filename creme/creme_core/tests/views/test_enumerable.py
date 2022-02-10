# -*- coding: utf-8 -*-

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core import models
from creme.creme_core.core.entity_filter import operators
from creme.creme_core.core.entity_filter.condition_handler import (
    RegularFieldConditionHandler,
)

from .base import ViewsTestCase


class EnumerableViewsTestCase(ViewsTestCase):
    @staticmethod
    def _build_choices_url(model, field_name):
        return reverse(
            'creme_core__enumerable_choices',
            args=(ContentType.objects.get_for_model(model).id, field_name),
        )

    def test_choices_success_fk(self):
        self.login()
        response = self.assertGET200(self._build_choices_url(models.FakeContact, 'civility'))

        with self.assertNoException():
            choices = response.json()

        self.assertListEqual(
            [
                {'value': id, 'label': title}
                for id, title in models.FakeCivility.objects.values_list('id', 'title')
            ],
            choices,
        )

    def test_choices_success_m2m(self):
        self.login()
        response = self.assertGET200(self._build_choices_url(models.FakeImage, 'categories'))
        self.assertListEqual(
            [
                {'value': id, 'label': name}
                for id, name in models.FakeImageCategory.objects.values_list('id', 'name')
            ],
            response.json(),
        )

    def test_choices_success_limited_choices_to(self):
        self.login()

        create_lang = models.Language.objects.create
        lang1 = create_lang(name='Klingon [deprecated]')
        lang2 = create_lang(name='Namek')

        response = self.assertGET200(
            self._build_choices_url(models.FakeContact, 'languages')
        )

        ids = {t['value'] for t in response.json()}
        self.assertIn(lang2.id, ids)
        self.assertNotIn(lang1.id, ids)

    def test_choices_success_specific_printer01(self):
        "Model is EntityFilter."
        user = self.login()

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
            efilter_as_dicts = [c for c in choices if c['value'] == efilter.id]
            self.assertEqual(1, len(efilter_as_dicts))
            return efilter_as_dicts[0]

        self.assertDictEqual(
            {
                'value': efilter1.pk,
                'label': efilter1.name,
                'help': '',
                'group': 'Test Contact',
            },
            find_efilter_dict(efilter1)
        )
        self.assertDictEqual(
            {
                'value': efilter2.pk,
                'label': efilter2.name,
                'help': _('Private ({})').format(user),
                'group': 'Test Organisation',
            },
            find_efilter_dict(efilter2)
        )

    def test_choices_success_specific_printer02(self):
        "Field is a EntityCTypeForeignKey."
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
        self.assertContains(
            self.client.get(self._build_choices_url(models.FakeAddress, 'entity')),
            'This model is not a CremeEntity: creme.creme_core.tests.fake_models.FakeAddress',
            status_code=409,
        )

    def test_choices_no_app_credentials(self):
        self.login(is_superuser=False, allowed_apps=['creme_config'])
        self.assertContains(
            self.client.get(
                self._build_choices_url(models.FakeContact, 'civility'),
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            ),
            _('You are not allowed to access to the app: {}').format(_('Core')),
            status_code=403,
        )

    def test_choices_field_does_not_exist(self):
        self.login()
        self.assertContains(
            self.client.get(self._build_choices_url(models.FakeContact, 'unknown')),
            'This field does not exist.',
            status_code=404,
        )

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

        response = self.assertGET200(
            reverse('creme_core__cfield_enums', args=(custom_field.id,))
        )
        self.assertListEqual(
            [
                [eva00.id, eva00.value],
                [eva01.id, eva01.value],
                [eva02.id, eva02.value],
            ],
            response.json(),
        )
