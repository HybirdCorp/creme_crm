from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.forms.models import ModelForm
from django.test.utils import isolate_apps, override_settings
from django.urls.base import reverse
from django.utils.translation import gettext as _
from django.utils.translation import override as override_language
from parameterized import parameterized

from creme.creme_core.core.enumerable import (
    EmptyEnumerator,
    QSEnumerator,
    enumerable_registry,
)
from creme.creme_core.forms.enumerable import (
    DEFAULT_LIMIT,
    NO_LIMIT,
    EnumerableChoice,
    EnumerableModelChoiceField,
    EnumerableSelect,
    FieldEnumerableChoiceSet,
)
from creme.creme_core.models import (
    Currency,
    FakeContact,
    FakeInvoice,
    FakeSector,
)

from ..base import CremeTestCase


# @override_settings(FORM_ENUMERABLE_LIMIT=100, ENUMERABLE_REGISTRATION_ERROR=False)
@override_settings(FORM_ENUMERABLE_LIMIT=100)
class FieldEnumerableChoiceSetTestCase(CremeTestCase):
    maxDiff = None

    @parameterized.expand([
        (None, '', DEFAULT_LIMIT),
        (None, 10, 10),
        (20, '', 20),
    ])
    def test_limit(self, limit, setting_limit, expected):
        with override_settings(FORM_ENUMERABLE_LIMIT=setting_limit):
            enumerable = FieldEnumerableChoiceSet(FakeContact._meta.get_field('user'), limit=limit)

        self.assertEqual(expected, enumerable.limit)

    def test_empty_enumerator(self):
        enumerable = FieldEnumerableChoiceSet(FakeContact._meta.get_field('first_name'))
        self.assertIsInstance(enumerable.enumerator, EmptyEnumerator)

        # with self.assertLogs(level='ERROR') as logs:
        #     choices, more = enumerable.choices()
        #
        # self.assertEqual(logs.output, [
        #     'ERROR:'
        #     'creme.creme_core.core.enumerable:'
        #     'No enumerator has been found for the field "creme_core.FakeContact.first_name". '
        #     'Please register the field or its related model in apps config '
        #     '(see register_enumerable())'
        # ])
        #
        # self.assertFalse(more)
        # self.assertEqual([], list(choices))
        #
        # groups, more = enumerable.groups()
        # self.assertFalse(more)
        # self.assertEqual([], list(groups))
        #
        # with override_settings(ENUMERABLE_REGISTRATION_ERROR=True):
        #     with self.assertRaises(NotImplementedError) as err:
        #         enumerable.choices()
        with self.assertRaises(NotImplementedError) as err:
            enumerable.choices()

        self.assertEqual(
            str(err.exception),
            'No enumerator has been found for the field "creme_core.FakeContact.first_name". '
            'HINT: Register the field or its related model in apps config '
            '(see register_enumerable())'
        )

    def test_default_url(self):
        field = FakeContact._meta.get_field('user')
        field_ctype = ContentType.objects.get_for_model(field.model)
        enumerable = FieldEnumerableChoiceSet(field)

        default_url = reverse(
            'creme_core__enumerable_choices', args=(field_ctype.id, 'user')
        )

        self.assertEqual(enumerable.url, default_url)
        self.assertEqual(enumerable.default_url, default_url)

    def test_custom_url(self):
        field = FakeContact._meta.get_field('user')
        field_ctype = ContentType.objects.get_for_model(field.model)
        enumerable = FieldEnumerableChoiceSet(field, url='new_enumerable_choices_view')

        self.assertEqual(enumerable.url, 'new_enumerable_choices_view')
        self.assertEqual(
            enumerable.default_url,
            reverse('creme_core__enumerable_choices', args=(field_ctype.id, 'user'))
        )

    def test_choices(self):
        user = self.get_root_user()
        enumerable = FieldEnumerableChoiceSet(FakeContact._meta.get_field('user'))

        choices, more = enumerable.choices()
        self.assertFalse(more)
        self.assertListEqual(
            [EnumerableChoice(user.pk, str(user)).as_dict()],
            [c.as_dict() for c in choices],
        )

    def test_choices__empty_label(self):
        user = self.get_root_user()
        enumerable = FieldEnumerableChoiceSet(
            FakeContact._meta.get_field('user'),
            empty_label='No value'
        )

        choices, more = enumerable.choices()
        self.assertFalse(more)
        self.assertListEqual(
            [
                EnumerableChoice('', 'No value').as_dict(),
                EnumerableChoice(user.pk, str(user)).as_dict(),
            ],
            [c.as_dict() for c in choices],
        )

    @parameterized.expand([
        (NO_LIMIT, False),
        (10, False),
        (3, False),
        (2, True)
    ])
    def test_choices__more(self, limit, has_more):
        fulbert = self.get_root_user()
        kirika = self.create_user(0)
        mireille = self.create_user(1)

        available_choices = [
            EnumerableChoice(fulbert.pk, str(fulbert)).as_dict(),
            EnumerableChoice(kirika.pk, str(kirika)).as_dict(),
            EnumerableChoice(mireille.pk, str(mireille)).as_dict(),
        ]

        enumerable = FieldEnumerableChoiceSet(FakeContact._meta.get_field('user'), limit=limit)
        choices, more = enumerable.choices()

        expected = available_choices if limit == NO_LIMIT else available_choices[:limit]

        self.assertListEqual(expected, [c.as_dict() for c in choices])
        self.assertEqual(more, has_more)

    def test_choices__selected(self):
        enumerable = FieldEnumerableChoiceSet(FakeContact._meta.get_field('sector'))
        farming, industry, software = FakeSector.objects.order_by('pk')[:3]
        sector_A = FakeSector.objects.create(title='Sector A')
        sector_B = FakeSector.objects.create(title='Sector B')
        sector_C = FakeSector.objects.create(title='Sector C')

        choices, more = enumerable.choices(
            selected_values=[industry.pk, sector_B.pk, software.pk]
        )
        self.assertFalse(more)
        self.assertListEqual([
            EnumerableChoice(farming.pk, str(farming)).as_dict(),
            EnumerableChoice(industry.pk, str(industry), selected=True).as_dict(),
            EnumerableChoice(software.pk, str(software), selected=True).as_dict(),
            EnumerableChoice(sector_A.pk, str(sector_A)).as_dict(),
            EnumerableChoice(sector_B.pk, str(sector_B), selected=True).as_dict(),
            EnumerableChoice(sector_C.pk, str(sector_C)).as_dict(),
        ], [c.as_dict() for c in choices])

    def test_choices__selected__outside_limit(self):
        enumerable = FieldEnumerableChoiceSet(FakeContact._meta.get_field('sector'), limit=3)

        farming, industry, software = FakeSector.objects.order_by('pk')[:3]

        FakeSector.objects.create(title='Sector A')
        FakeSector.objects.create(title='Sector B')
        sector_C = FakeSector.objects.create(title='Sector C')

        choices, more = enumerable.choices(
            selected_values=[industry.pk, sector_C.pk]
        )
        self.assertTrue(more)
        self.assertListEqual([
            EnumerableChoice(farming.pk, str(farming)).as_dict(),
            EnumerableChoice(industry.pk, str(industry), selected=True).as_dict(),
            EnumerableChoice(software.pk, str(software)).as_dict(),
            EnumerableChoice(sector_C.pk, str(sector_C), selected=True).as_dict(),
        ], [c.as_dict() for c in choices])

    def test_choices__selected__count_over_limit(self):
        enumerable = FieldEnumerableChoiceSet(FakeContact._meta.get_field('sector'), limit=3)
        _, industry, software = FakeSector.objects.order_by('pk')

        FakeSector.objects.create(title='Sector A')
        sector_B = FakeSector.objects.create(title='Sector B')
        sector_C = FakeSector.objects.create(title='Sector C')

        choices, more = enumerable.choices(
            selected_values=[industry.pk, sector_B.pk, sector_C.pk, software.pk]
        )

        self.assertTrue(more)
        self.assertListEqual([
            EnumerableChoice(industry.pk, str(industry), selected=True).as_dict(),
            EnumerableChoice(software.pk, str(software), selected=True).as_dict(),
            EnumerableChoice(sector_B.pk, str(sector_B), selected=True).as_dict(),
            EnumerableChoice(sector_C.pk, str(sector_C), selected=True).as_dict(),
        ], [c.as_dict() for c in choices])

    @override_language('en')
    def test_groups(self):
        """
        The current language of forced to english to prevent some group ordering
        issues depending on the test runner configuration
        """
        fulbert = self.get_root_user()
        kirika = self.create_user(index=0)
        mireille = self.create_user(index=1)
        chloe = self.create_user(index=2, is_active=False)

        team_A = self.create_team('ATeam', kirika, mireille)
        team_B = self.create_team('BTeam', fulbert)

        enumerable = FieldEnumerableChoiceSet(
            FakeContact._meta.get_field('user'), empty_label='No value',
        )

        groups, more = enumerable.groups()
        self.assertFalse(more)
        self.assertListEqual([
            (
                None, [
                    EnumerableChoice('', 'No value').as_dict(),
                    EnumerableChoice(fulbert.pk, str(fulbert)).as_dict(),
                    EnumerableChoice(kirika.pk, str(kirika)).as_dict(),
                    EnumerableChoice(mireille.pk, str(mireille)).as_dict(),
                ]
            ),
            (
                _('Inactive users'), [
                    EnumerableChoice(chloe.pk, str(chloe), group=_('Inactive users')).as_dict(),
                ]
            ),
            (
                _('Teams'), [
                    EnumerableChoice(team_A.pk, 'ATeam', group=_('Teams')).as_dict(),
                    EnumerableChoice(team_B.pk, 'BTeam', group=_('Teams')).as_dict(),
                ]
            ),
        ], [
            (group, [c.as_dict() for c in choices])
            for group, choices in groups
        ])

    @parameterized.expand([
        (10, False),
        (6, False),
        (2, True)
    ])
    @override_language('en')
    def test_groups__more(self, limit, has_more):
        """
        The current language of forced to english to prevent some group ordering
        issues depending on the test runner configuration.
        """
        fulbert = self.get_root_user()
        kirika = self.create_user(index=0)
        mireille = self.create_user(index=1)
        chloe = self.create_user(index=2, is_active=False)

        team_A = self.create_team('ATeam', kirika, mireille)
        team_B = self.create_team('BTeam', fulbert)

        enumerable = FieldEnumerableChoiceSet(
            FakeContact._meta.get_field('user'), limit=limit,
        )

        available_choices = [
            EnumerableChoice(fulbert.pk, str(fulbert)),
            EnumerableChoice(kirika.pk, str(kirika)),
            EnumerableChoice(mireille.pk, str(mireille)),
            EnumerableChoice(chloe.pk, str(chloe), group=_('Inactive users')),
            EnumerableChoice(team_A.pk, 'ATeam', group=_('Teams')),
            EnumerableChoice(team_B.pk, 'BTeam', group=_('Teams')),
        ]

        if limit == NO_LIMIT:
            expected = available_choices
        else:
            expected = available_choices[:limit]

        groups, more = enumerable.groups()
        self.assertListEqual(
            [
                (group, [c.as_dict() for c in choices])
                for group, choices in enumerable.group_choices(expected)
            ],
            [
                (group, [c.as_dict() for c in choices])
                for group, choices in groups
            ]
        )
        self.assertEqual(more, has_more)

    @parameterized.expand(['sector', 'civility', 'position'])
    def test_url(self, field_name):
        enumerable = FieldEnumerableChoiceSet(FakeContact._meta.get_field(field_name))

        ctype = ContentType.objects.get_for_model(FakeContact)

        self.assertEqual(
            reverse('creme_core__enumerable_choices', args=(ctype.id, field_name)),
            enumerable.url
        )

    def test_to_python(self):
        enumerable = FieldEnumerableChoiceSet(FakeContact._meta.get_field('sector'), limit=3)

        farming, industry, software = FakeSector.objects.order_by('pk')[:3]

        FakeSector.objects.create(title='Sector A')
        FakeSector.objects.create(title='Sector B')
        sector_C = FakeSector.objects.create(title='Sector C')

        self.assertEqual([
            industry, sector_C
        ], enumerable.to_python([
            industry.pk, sector_C.pk
        ]))

    def test_to_python__invalid_value(self):
        field = FakeContact._meta.get_field('sector')
        enumerable = FieldEnumerableChoiceSet(field)
        self.assertEqual([], enumerable.to_python([self.UNUSED_PK]))


@override_settings(FORM_ENUMERABLE_LIMIT=100)
class EnumerableSelectTestCase(CremeTestCase):
    maxDiff = None

    def test_render_no_url(self):
        farming, industry, software = FakeSector.objects.order_by('pk')[:3]
        sector_A = FakeSector.objects.create(title='Sector A')
        sector_B = FakeSector.objects.create(title='Sector B')
        sector_C = FakeSector.objects.create(title='Sector C')

        enumerable = FieldEnumerableChoiceSet(FakeContact._meta.get_field('sector'))
        widget = EnumerableSelect(enumerable)

        self.assertHTMLEqual(
            f'''
            <select class="ui-creme-input ui-creme-widget ui-creme-dselect widget-auto is-enum"
                    widget="ui-creme-dselect"
                    name="testfield" autocomplete
                    data-allow-clear="true">
                <option value="{farming.pk}">Farming</option>
                <option selected value="{industry.pk}">Industry</option>
                <option value="{software.pk}">Software</option>
                <option value="{sector_A.pk}">Sector A</option>
                <option value="{sector_B.pk}">Sector B</option>
                <option value="{sector_C.pk}">Sector C</option>
            </select>
            ''',
            widget.render('testfield', value=industry.pk),
        )

    def test_render_url(self):
        farming, industry, software = FakeSector.objects.order_by('pk')[:3]

        enumerable = FieldEnumerableChoiceSet(FakeContact._meta.get_field('sector'))
        widget = EnumerableSelect(enumerable)
        widget.create_url = url = reverse(
            'creme_config__create_instance_from_widget', args=('creme_core', 'fake_sector'),
        )

        self.assertHTMLEqual(
            f'''
            <select class="ui-creme-input ui-creme-widget ui-creme-dselect widget-auto is-enum"
                    widget="ui-creme-dselect"
                    name="testfield" autocomplete
                    data-create-url="{url}"
                    data-allow-clear="true">
                <option value="{farming.pk}">Farming</option>
                <option selected value="{industry.pk}">Industry</option>
                <option value="{software.pk}">Software</option>
            </select>
            ''',
            widget.render('testfield', value=industry.pk),
        )

    def test_render__more(self):
        farming, industry, software = FakeSector.objects.order_by('pk')[:3]
        sector_A = FakeSector.objects.create(title='Sector A')
        FakeSector.objects.create(title='Sector B')
        FakeSector.objects.create(title='Sector C')

        enumerable = FieldEnumerableChoiceSet(FakeContact._meta.get_field('sector'), limit=4)
        widget = EnumerableSelect(enumerable)

        self.assertHTMLEqual(
            f'''
            <select class="ui-creme-input ui-creme-widget ui-creme-dselect widget-auto is-enum"
                    widget="ui-creme-dselect"
                    name="testfield" autocomplete
                    data-allow-clear="true"
                    data-enum-url="{enumerable.url}"
                    data-enum-limit="{enumerable.limit}"
                    data-enum-cache="true"
                    data-enum-debounce="300">
                <option value="{farming.pk}">Farming</option>
                <option selected value="{industry.pk}">Industry</option>
                <option value="{software.pk}">Software</option>
                <option value="{sector_A.pk}">Sector A</option>
            </select>
            ''',
            widget.render('testfield', value=industry.pk),
        )

    def test_render__more_custom_attrs(self):
        farming, industry, software = FakeSector.objects.order_by('pk')[:3]

        enumerable = FieldEnumerableChoiceSet(FakeContact._meta.get_field('sector'), limit=2)
        widget = EnumerableSelect(enumerable, attrs={
            'data-enum-cache': 'false',
            'data-enum-debounce': 500,
        })

        self.assertHTMLEqual(
            f'''
            <select class="ui-creme-input ui-creme-widget ui-creme-dselect widget-auto is-enum"
                    widget="ui-creme-dselect"
                    name="testfield" autocomplete
                    data-allow-clear="true"
                    data-enum-url="{enumerable.url}"
                    data-enum-limit="{enumerable.limit}"
                    data-enum-cache="false"
                    data-enum-debounce="500">
                <option value="{farming.pk}">Farming</option>
                <option selected value="{industry.pk}">Industry</option>
            </select>
            ''',
            widget.render('testfield', value=industry.pk),
        )


@override_settings(FORM_ENUMERABLE_LIMIT=100)
class EnumerableModelChoiceFieldTestCase(CremeTestCase):
    maxDiff = None

    def test_default(self):
        farming, industry, software = FakeSector.objects.order_by('pk')[:3]
        field = EnumerableModelChoiceField(FakeContact, 'sector')

        self.assertEqual('---------', field.empty_label)
        self.assertIsNone(field.initial)
        self.assertIsNone(field.user)

        self.assertIsInstance(field.widget, EnumerableSelect)
        self.assertListEqual([], field.widget.choices)

        expected = [
            EnumerableChoice('', '---------').as_dict(),
            EnumerableChoice(farming.pk, str(farming)).as_dict(),
            EnumerableChoice(industry.pk, str(industry)).as_dict(),
            EnumerableChoice(software.pk, str(software)).as_dict(),
        ]

        self.assertListEqual(expected, [c.as_dict() for c in field.choices])

    def test_initial(self):
        farming, industry, software = FakeSector.objects.order_by('pk')[:3]
        field = EnumerableModelChoiceField(
            FakeContact, 'sector', empty_label='No value...', initial=industry.pk
        )

        self.assertIsNone(field.empty_label)
        self.assertEqual(industry.pk, field.initial)
        self.assertIsNone(field.user)

        self.assertIsInstance(field.widget, EnumerableSelect)
        self.assertListEqual([], field.widget.choices)

        expected = [
            EnumerableChoice(farming.pk, str(farming)).as_dict(),
            EnumerableChoice(industry.pk, str(industry)).as_dict(),
            EnumerableChoice(software.pk, str(software)).as_dict(),
        ]

        self.assertListEqual(expected, [c.as_dict() for c in field.choices])

    def test_initial_from_model_default(self):
        class FakeInvoiceForm(ModelForm):
            class Meta:
                model = FakeInvoice
                fields = ('currency',)

        form = FakeInvoiceForm()
        field = EnumerableModelChoiceField(
            FakeInvoice, 'currency', empty_label='No value…',
        )
        boundfield = field.get_bound_field(form, 'currency')

        default_currency = Currency.objects.default()

        self.assertIsNone(field.empty_label)
        self.assertIsNone(field.user)
        self.assertEqual(FakeInvoice._meta.get_field('currency')._get_default, field.initial)
        self.assertEqual(default_currency.pk, boundfield.initial)

        other_currency = Currency.objects.exclude(id=default_currency.pk)[0]
        field = EnumerableModelChoiceField(
            FakeInvoice, 'currency', empty_label='No value…', initial=other_currency.pk,
        )
        boundfield = field.get_bound_field(form, 'currency')

        self.assertIsNone(field.empty_label)
        self.assertIsNone(field.user)
        self.assertEqual(other_currency.pk, field.initial)
        self.assertEqual(other_currency.pk, boundfield.initial)

    # Feature of django test tools that allows to declare some models inside a test.
    # see (https://docs.djangoproject.com/en/5.2/topics/testing/tools/#isolating-apps)
    @isolate_apps("creme.creme_core.tests.forms")
    def test_initial_from_model_default__callable(self):
        farming, industry, software = FakeSector.objects.order_by('pk')[:3]

        def get_default_sector():
            return FakeSector.objects.filter(title='default').first()

        class FakeEnumerableModel(models.Model):
            sector = models.ForeignKey(
                FakeSector, verbose_name=_('Line of business'),
                null=True, blank=True,
                on_delete=models.SET_NULL,
                default=get_default_sector,
            )

        class FakeEnumerableForm(ModelForm):
            class Meta:
                model = FakeEnumerableModel
                fields = ('sector',)

        enumerable_registry.register_related_model(FakeSector, QSEnumerator)

        form = FakeEnumerableForm()
        field = form.fields['sector']
        boundfield = field.get_bound_field(form, 'sector')

        self.assertTrue(isinstance(field, EnumerableModelChoiceField))
        self.assertTrue(field.show_hidden_initial)
        self.assertEqual(field.initial, get_default_sector)
        self.assertListEqual([
            EnumerableChoice('', field.empty_label).as_dict(),
            EnumerableChoice(farming.pk, str(farming)).as_dict(),
            EnumerableChoice(industry.pk, str(industry)).as_dict(),
            EnumerableChoice(software.pk, str(software)).as_dict(),
        ], [c.as_dict() for c in field.choices])

        self.assertIsInstance(field.widget, EnumerableSelect)
        self.assertEqual(boundfield.initial, None)

        default = FakeSector.objects.create(title='default')

        form = FakeEnumerableForm()
        field = form.fields['sector']
        boundfield = field.get_bound_field(form, 'sector')

        self.assertListEqual([
            EnumerableChoice('', field.empty_label).as_dict(),
            EnumerableChoice(farming.pk, str(farming)).as_dict(),
            EnumerableChoice(industry.pk, str(industry)).as_dict(),
            EnumerableChoice(software.pk, str(software)).as_dict(),
            EnumerableChoice(default.pk, str(default)).as_dict(),
        ], [c.as_dict() for c in field.choices])

        self.assertEqual(boundfield.initial, default)

    def test_clean_value(self):
        farming = FakeSector.objects.order_by('pk').first()
        field = EnumerableModelChoiceField(FakeContact, 'sector', required=False)

        self.assertIsNone(field.to_python(''))
        self.assertEqual(farming, field.to_python(farming.pk))

    @override_settings(FORM_ENUMERABLE_LIMIT=2)
    def test_clean_value__outside_limit(self):
        farming, industry, software = FakeSector.objects.order_by('pk')[:3]
        field = EnumerableModelChoiceField(FakeContact, 'sector', required=False)

        expected = [
            EnumerableChoice('', '---------').as_dict(),
            EnumerableChoice(farming.pk, str(farming)).as_dict(),
            EnumerableChoice(industry.pk, str(industry)).as_dict(),
        ]

        self.assertListEqual(expected, [c.as_dict() for c in field.choices])
        self.assertIsNone(field.to_python(''))
        self.assertEqual(software, field.to_python(software.pk))

    def test_invalid_value(self):
        field = EnumerableModelChoiceField(FakeContact, 'sector')

        with self.assertRaises(ValidationError):
            field.to_python('unknown')
