# -*- coding: utf-8 -*-

from decimal import Decimal
from functools import partial

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.formats import get_format, number_format
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.enumerable import QSEnumerator, _EnumerableRegistry
from creme.creme_core.forms import listview as lv_form
from creme.creme_core.gui.listview import ListViewSearchFieldRegistry
# from creme.creme_core.tests.fake_constants import (
#     FAKE_AMOUNT_UNIT,
#     FAKE_PERCENT_UNIT,
# )
from creme.creme_core.models import (
    CremeUser,
    CustomField,
    CustomFieldEnumValue,
    FakeActivity,
    FakeActivityType,
    FakeContact,
    FakeImage,
    FakeImageCategory,
    FakeInvoiceLine,
    FakeOrganisation,
    FakeSector,
    Relation,
    RelationType,
)

from ..base import CremeTestCase


class SearchWidgetsTestCase(CremeTestCase):
    def test_textwidget(self):
        widget = lv_form.TextLVSWidget()
        name = 'foobar'
        get_value = partial(widget.value_from_datadict, name=name, files=None)
        self.assertIsNone(get_value(data={}))

        value = 'baz'
        self.assertEqual('baz', get_value(data={name: value}))

        self.assertHTMLEqual(
            f'<input class="lv-state-field" name="{name}" '
            f'type="text" data-lv-search-widget="text" value="{value}" />',
            widget.render(name=name, value=value),
        )

    def test_booleanwidget01(self):
        widget = lv_form.BooleanLVSWidget()
        self.assertIs(widget.null, False)
        name = 'foo'
        get_value = partial(widget.value_from_datadict, name=name, files=None)
        self.assertEqual(None,  get_value(data={}))
        self.assertEqual(None,  get_value(data={name: ''}))
        self.assertEqual(None,  get_value(data={name: 'NULL'}))
        self.assertEqual(True,  get_value(data={name: '1'}))
        self.assertEqual(False, get_value(data={name: '0'}))

        self.assertHTMLEqual(
            '<select class="lv-state-field" data-lv-search-widget="select" name="{name}">'
            ' <option value="">{all}</option>'
            ' <option value="1" selected>{yes}</option>'
            ' <option value="0">{no}</option>'
            '</select>'.format(
                name=name,
                all=pgettext('creme_core-filter', 'All'),
                yes=_('Yes'),
                no=_('No'),
            ),
            widget.render(name=name, value='1'),
        )

    def test_booleanwidget02(self):
        widget1 = lv_form.BooleanLVSWidget(null=False)
        self.assertFalse(widget1.null)

        widget2 = lv_form.BooleanLVSWidget(null=True)
        self.assertTrue(widget2.null)
        name = 'foobar'
        get_value = partial(widget2.value_from_datadict, name=name, files=None)
        self.assertEqual(None,   get_value(data={}))
        self.assertEqual('NULL', get_value(data={name: 'NULL'}))
        self.assertEqual(True,   get_value(data={name: '1'}))
        self.assertEqual(False,  get_value(data={name: '0'}))

        self.assertHTMLEqual(
            '<select class="lv-state-field" data-lv-search-widget="select" name="{name}">'
            ' <option value="">{all}</option>'
            ' <option value="NULL" selected>{null}</option>'
            ' <option value="1">{yes}</option>'
            ' <option value="0">{no}</option>'
            '</select>'.format(
                name=name,
                all=pgettext('creme_core-filter', 'All'),
                null=_('N/A'),
                yes=_('Yes'),
                no=_('No'),
            ),
            widget2.render(name=name, value='NULL'),
        )

    def test_selectwidget01(self):
        "No choice."
        widget = lv_form.SelectLVSWidget()
        name = 'foo'
        get_value = partial(widget.value_from_datadict, name=name, files=None)
        self.assertEqual(None, get_value(data={}))

        value = 'bar'
        self.assertEqual(value, get_value(data={name: value}))

        self.assertEqual((), widget.choices)

        self.assertHTMLEqual(
            f'<select class="lv-state-field" data-lv-search-widget="select" '
            f'name="{name}"></select>',
            widget.render(name=name, value=value),
        )

    def test_selectwidget02(self):
        "With choice."
        choices = [
            {'value': '',  'label': 'All'},
            {'value': '1', 'label': 'one'},
            {'value': '2', 'label': 'two'},
            {'value': '3', 'label': 'three'},
        ]
        widget = lv_form.SelectLVSWidget(choices=choices)
        self.assertEqual(choices, widget.choices)

        name = 'foo'
        self.assertHTMLEqual(
            f'<select class="lv-state-field" data-lv-search-widget="select" name="{name}">'
            '  <option value="">All</option>'
            '  <option value="1">one</option>'
            '  <option value="2" selected>two</option>'
            '  <option value="3">three</option>'
            '</select>',
            widget.render(name=name, value='2'),
        )

    def test_selectwidget03(self):
        "With groups & NULL."
        choices = [
            {'value': '',     'label': 'All'},
            {'value': 'NULL', 'label': 'Nothing'},

            {'group': 'Numbers', 'value': '1', 'label': 'one'},
            {'group': 'Numbers', 'value': '2', 'label': 'two'},

            {'group': 'Letters', 'value': 'a', 'label': 'A'},
            {'group': 'Letters', 'value': 'b', 'label': 'B'},
        ]
        widget = lv_form.SelectLVSWidget(choices=choices)
        self.assertEqual(choices, widget.choices)

        name = 'foob'
        self.assertHTMLEqual(
            f'<select class="lv-state-field" data-lv-search-widget="select" name="{name}">'
            '   <option value="">All</option>'
            '   <option value="NULL" class="search-nullfk">Nothing</option>'
            '   <optgroup label="Numbers">'
            '       <option value="1">one</option>'
            '       <option value="2">two</option>'
            '   </optgroup>'
            '   <optgroup label="Letters">'
            '        <option value="a" selected>A</option>'
            '       <option value="b">B</option>'
            '   </optgroup>'
            '</select>',
            widget.render(name=name, value='a'),
        )

    def test_daterangewidget(self):
        widget = lv_form.DateRangeLVSWidget()
        get_value = partial(widget.value_from_datadict, files=None)
        self.assertListEqual(['', ''], get_value(data={}, name='foobar'))
        self.assertListEqual(['baz', ''], get_value(name='foobar', data={'foobar-start': 'baz'}))
        self.assertListEqual(['', 'bar'], get_value(name='foo',    data={'foo-end': 'bar'}))
        self.assertListEqual(
            ['yipee', 'kay'],
            get_value(
                name='foob',
                data={
                    'foob-start': 'yipee',
                    'foob-end':   'kay',
                },
            ),
        )

        name = 'search-birthday'
        self.assertHTMLEqual(
            '<div class="lv-search-daterange" data-lv-search-widget="daterange">'
            ' <div class="date-start">'
            '    <label for="id_birth-start">{start_label}</label>'
            '    <input class="lv-state-field"'
            '           data-format="{format}" id="id_birth-start" name="{name}-start" '
            '           value="12-02-2019" />'
            ' </div>'
            ' <div class="date-end">'
            '   <label for="id_birth-end">{end_label}</label>'
            '   <input class="lv-state-field"'
            '          data-format="{format}" id="id_birth-end" name="{name}-end" '
            '          value="14-02-2019" />'
            ' </div>'
            '</div>'.format(
                name=name,
                start_label=_('Start'),
                end_label=_('End'),
                format=settings.DATE_FORMAT_JS.get(settings.DATE_FORMAT),
            ),
            widget.render(
                name=name,
                value=['12-02-2019', '14-02-2019'],
                attrs={'id': 'id_birth'},
            ),
        )


class SearchFieldsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.create_user()

    def test_regular_charfield01(self):
        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')
        field = lv_form.RegularCharField(cell=cell, user=self.user)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=''))

        value = 'baz'
        self.assertEqual(Q(name__icontains=value), to_python(value=value))

    def test_regular_charfield02(self):
        cell = EntityCellRegularField.build(model=FakeOrganisation, name='sector__title')
        field = lv_form.RegularCharField(cell=cell, user=self.user)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=''))

        value = 'foo'
        self.assertEqual(Q(sector__title__icontains=value), to_python(value=value))

    def test_regular_booleanfield01(self):
        cell = EntityCellRegularField.build(model=FakeContact, name='is_a_nerd')
        field = lv_form.RegularBooleanField(cell=cell, user=self.user)

        to_python = field.to_python
        self.assertEqual(Q(),                to_python(value=None))
        self.assertEqual(Q(is_a_nerd=True),  to_python(value=True))
        self.assertEqual(Q(is_a_nerd=False), to_python(value=False))
        self.assertEqual(Q(),                to_python(value='NULL'))

        self.assertFalse(field.null)
        self.assertFalse(field.widget.null)

    def test_regular_booleanfield02(self):
        "Nullable."
        cell = EntityCellRegularField.build(model=FakeContact, name='loves_comics')
        field = lv_form.RegularBooleanField(cell=cell, user=self.user)

        to_python = field.to_python
        self.assertEqual(Q(),                   to_python(value=None))
        self.assertEqual(Q(loves_comics=True),  to_python(value=True))
        self.assertEqual(Q(loves_comics=False), to_python(value=False))
        self.assertEqual(Q(loves_comics=None),  to_python(value='NULL'))

        self.assertTrue(field.null)
        self.assertTrue(field.widget.null)

    def test_regular_integerfield(self):
        cell = EntityCellRegularField.build(model=FakeOrganisation, name='capital')
        field = lv_form.RegularIntegerField(cell=cell, user=self.user)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=None))
        self.assertEqual(Q(), to_python(value=''))
        self.assertEqual(Q(), to_python(value='notatint'))
        self.assertEqual(Q(), to_python(value='>notatint'))
        self.assertEqual(Q(), to_python(value='<notatint'))
        self.assertEqual(Q(), to_python(value='>=notatint'))
        self.assertEqual(Q(), to_python(value='<=notatint'))
        self.assertEqual(Q(), to_python(value='#100'))

        self.assertEqual(Q(capital__exact=100), to_python(value='100'))
        self.assertEqual(Q(capital__exact=100), to_python(value=' 100 '))
        self.assertEqual(Q(capital__exact=100), to_python(value=' = 100 '))
        self.assertEqual(Q(capital__exact=-100), to_python(value='-100'))

        self.assertEqual(Q(capital__gt=1000), to_python(value='>1000'))
        self.assertEqual(Q(capital__gt=1000), to_python(value=' > 1000 '))

        self.assertEqual(Q(capital__lt=250), to_python(value='<250'))
        self.assertEqual(Q(capital__lt=250), to_python(value=' < 250 '))

        self.assertEqual(Q(capital__gte=123), to_python(value='>=123'))
        self.assertEqual(Q(capital__lte=25),  to_python(value='<=25'))

        self.assertEqual(
            Q(capital__gte=100, capital__lt=200),
            to_python(value='>=100; <200'),
        )
        self.assertEqual(
            Q(capital__gte=100),
            to_python(value='>=100; <notanint'),
        )

    def test_regular_positiveintegerfield(self):
        cell = EntityCellRegularField.build(model=FakeOrganisation, name='capital')
        field = lv_form.RegularPositiveIntegerField(cell=cell, user=self.user)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=None))
        self.assertEqual(Q(), to_python(value=''))
        self.assertEqual(Q(), to_python(value='notatint'))
        self.assertEqual(Q(), to_python(value='>notatint'))
        self.assertEqual(Q(), to_python(value='<notatint'))
        self.assertEqual(Q(), to_python(value='>=notatint'))
        self.assertEqual(Q(), to_python(value='<=notatint'))
        self.assertEqual(Q(), to_python(value='#100'))

        self.assertEqual(Q(capital__exact=100), to_python(value='100'))
        self.assertEqual(Q(capital__exact=100), to_python(value=' 100 '))
        self.assertEqual(Q(capital__exact=100), to_python(value=' = 100 '))

        self.assertEqual(Q(capital__gt=1000), to_python(value='>1000'))
        self.assertEqual(Q(capital__gt=1000), to_python(value=' > 1000 '))

        self.assertEqual(Q(capital__lt=250), to_python(value='<250'))

        self.assertEqual(Q(capital__gte=123), to_python(value='>=123'))
        self.assertEqual(Q(capital__lte=25),  to_python(value='<=25'))

        self.assertEqual(
            Q(capital__gte=100, capital__lt=200),
            to_python(value='>=100; <200'),
        )
        self.assertEqual(
            Q(capital__gte=100),
            to_python(value='>=100; <notanint')
        )

    def test_regular_decimalfield(self):
        cell = EntityCellRegularField.build(model=FakeInvoiceLine, name='discount')
        field = lv_form.RegularDecimalField(cell=cell, user=self.user)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=None))
        self.assertEqual(Q(), to_python(value=''))
        self.assertEqual(Q(), to_python(value='notadecimal'))
        self.assertEqual(Q(), to_python(value='>notadecimal'))
        self.assertEqual(Q(), to_python(value='<notadecimal'))
        self.assertEqual(Q(), to_python(value='>=notadecimal'))
        self.assertEqual(Q(), to_python(value='<=notadecimal'))
        self.assertEqual(Q(), to_python(value='#100'))

        self.assertEqual(Q(discount__exact=Decimal('100')), to_python(value='100'))
        self.assertEqual(Q(discount__exact=Decimal('100')), to_python(value=' 100 '))
        self.assertEqual(Q(discount__exact=Decimal('100')), to_python(value=' = 100 '))
        self.assertEqual(Q(discount__exact=Decimal('-100')), to_python(value='-100'))

        self.assertEqual(Q(discount__gt=Decimal('1000')), to_python(value='>1000'))
        self.assertEqual(Q(discount__gt=Decimal('1000')), to_python(value=' > 1000 '))

        self.assertEqual(Q(discount__lt=Decimal('250')), to_python(value='<250'))

        self.assertEqual(Q(discount__gte=Decimal('123')), to_python(value='>=123'))
        self.assertEqual(Q(discount__lte=Decimal('25')),  to_python(value='<=25'))

        self.assertEqual(
            Q(discount__gte=Decimal('100'), discount__lt=Decimal('200')),
            to_python(value='>=100; <200'),
        )
        self.assertEqual(
            Q(discount__gte=Decimal('100')),
            to_python(value='>=100; <notanint'),
        )

        # With decimal part ---
        # TODO: fix when 'settings.USE_L10N = True' is set by default
        dec_sep = get_format('DECIMAL_SEPARATOR', use_l10n=True)
        self.assertEqual(Q(), to_python(value=dec_sep))
        self.assertEqual(
            Q(discount__exact=Decimal('10.5')),
            to_python(value=number_format(Decimal('10.5'), use_l10n=True)),
        )
        # No whole part
        self.assertEqual(
            Q(discount__exact=Decimal('0.5')), to_python(value=dec_sep + '5'),
        )

    def test_regular_floatfield(self):
        cell = EntityCellRegularField.build(model=FakeInvoiceLine, name='discount')
        field = lv_form.RegularFloatField(cell=cell, user=self.user)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=None))
        self.assertEqual(Q(), to_python(value=''))
        self.assertEqual(Q(), to_python(value='notafloat'))
        self.assertEqual(Q(), to_python(value='>notafloat'))

        # No EQUAL
        self.assertEqual(Q(), to_python(value='100'))
        self.assertEqual(Q(), to_python(value='=100'))

        self.assertEqual(Q(discount__gt=1000.0), to_python(value='>1000'))
        self.assertEqual(Q(discount__lt=25.0), to_python(value='<25'))

        self.assertEqual(Q(discount__gte=123.0), to_python(value='>=123'))
        self.assertEqual(Q(discount__lte=25.0), to_python(value='<=25'))

        # TODO: fix when 'settings.USE_L10N = True' is set by default
        self.assertEqual(
            Q(discount__gt=10.5),
            to_python(value='>' + number_format(10.5, use_l10n=True)),
        )

    def test_regular_datefield(self):
        cell = EntityCellRegularField.build(model=FakeContact, name='created')
        field = lv_form.RegularDateField(cell=cell, user=self.user)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=['', '']))

        dt = self.create_datetime
        self.assertEqual(
            Q(created__range=(
                dt(day=22, month=2, year=2019),
                dt(day=28, month=2, year=2019, hour=23, minute=59, second=59),
            )),
            to_python(value=['22-02-2019', '28-02-2019']),
        )
        self.assertEqual(
            Q(created__gte=dt(day=21, month=2, year=2019)),
            to_python(value=['21-02-2019', '']),
        )
        self.assertEqual(
            Q(created__lte=dt(day=25, month=2, year=2019, hour=23, minute=59, second=59)),
            to_python(value=['', '25-02-2019']),
        )

        # Invalid dates
        self.assertEqual(Q(), to_python(value=['abc', 'def']))
        self.assertEqual(
            Q(created__gte=dt(day=22, month=2, year=2019)),
            to_python(value=['22-02-2019', 'zblu']),
        )
        self.assertEqual(
            Q(created__lte=dt(day=26, month=2, year=2019, hour=23, minute=59, second=59)),
            to_python(value=['123', '26-02-2019']),
        )

    def test_regular_choicefield(self):
        cell = EntityCellRegularField.build(model=FakeInvoiceLine, name='discount_unit')

        field = lv_form.RegularChoiceField(cell=cell, user=self.user)  # TODO: choices=... ?
        Discount = FakeInvoiceLine.Discount
        expected_choices = [
            {'value': '',                'label': pgettext('creme_core-filter', 'All')},
            {'value': lv_form.NULL,      'label': _('* is empty *')},
            # {'value': FAKE_PERCENT_UNIT, 'label': _('Percent')},
            # {'value': FAKE_AMOUNT_UNIT,  'label': _('Amount')},
            {'value': Discount.PERCENT.value, 'label': _('Percent')},
            {'value': Discount.AMOUNT.value,  'label': _('Amount')},
        ]

        self.assertEqual(expected_choices, field.choices)
        self.assertEqual(expected_choices, field.widget.choices)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=None))
        self.assertEqual(Q(), to_python(value=''))
        self.assertEqual(Q(), to_python(value='unknown'))

        self.assertEqual(
            # Q(discount_unit=FAKE_PERCENT_UNIT),
            Q(discount_unit=Discount.PERCENT.value),
            # to_python(value=str(FAKE_PERCENT_UNIT))
            to_python(value=str(Discount.PERCENT.value))
        )
        self.assertEqual(
            # Q(discount_unit=FAKE_AMOUNT_UNIT),
            Q(discount_unit=Discount.AMOUNT.value),
            # to_python(value=str(FAKE_AMOUNT_UNIT))
            to_python(value=str(Discount.AMOUNT.value))
        )

        self.assertEqual(Q(discount_unit__isnull=True), to_python(value=lv_form.NULL))

    def test_regular_relatedfield01(self):
        "Nullable FK."
        cell = EntityCellRegularField.build(model=FakeOrganisation, name='sector')
        field = lv_form.RegularRelatedField(cell=cell, user=self.user)

        expected_choices = [
            {'value': '',           'label': pgettext('creme_core-filter', 'All')},
            {'value': lv_form.NULL, 'label': _('* is empty *')},
            *(
                {'value': pk, 'label': title}
                for pk, title in FakeSector.objects.values_list('id', 'title')
            ),
        ]
        self.assertEqual(expected_choices, field.choices)

        widget = field.widget
        self.assertIsInstance(widget, lv_form.SelectLVSWidget)
        self.assertEqual(expected_choices, widget.choices)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=''))
        self.assertEqual(Q(), to_python(value=None))
        self.assertEqual(Q(), to_python(value=0))

        value = FakeSector.objects.first().id
        self.assertEqual(Q(sector=value), to_python(value=str(value)))

        # NULL
        self.assertEqual(Q(sector__isnull=True), to_python(value=lv_form.NULL))

        # Invalid id
        self.assertEqual(Q(), to_python(value=self.UNUSED_PK))

    def test_regular_relatedfield02(self):
        "Not nullable FK."
        cell = EntityCellRegularField.build(model=FakeActivity, name='type')
        field = lv_form.RegularRelatedField(cell=cell, user=self.user)
        self.assertListEqual(
            [
                {'value': '', 'label': pgettext('creme_core-filter', 'All')},
                *(
                    {'value': pk, 'label': name}
                    for pk, name in FakeActivityType.objects.values_list('id', 'name')
                ),
            ],
            field.choices,
        )

    def test_regular_relatedfield03(self):
        "ManyToMany."
        cell = EntityCellRegularField.build(model=FakeImage, name='categories')
        field = lv_form.RegularRelatedField(cell=cell, user=self.user)

        self.assertListEqual(
            [
                {'value': '',           'label': pgettext('creme_core-filter', 'All')},
                {'value': lv_form.NULL, 'label': _('* is empty *')},
                *(
                    {'value': pk, 'label': name}
                    for pk, name in FakeImageCategory.objects.values_list('id', 'name')
                )
            ],
            field.choices,
        )

    def test_regular_relatedfield04(self):
        "limit_choices_to"
        # NB: limit_choices_to = lambda: ~Q(title='[INVALID]')
        cell = EntityCellRegularField.build(model=FakeContact, name='sector')
        expected_choices = [
            {'value': '',           'label': pgettext('creme_core-filter', 'All')},
            {'value': lv_form.NULL, 'label': _('* is empty *')},
            *(
                {'value': pk, 'label': title}
                for pk, title in FakeSector.objects.values_list('id', 'title')
            ),
        ]

        FakeSector.objects.create(title='[INVALID]')  # Excluded

        field = lv_form.RegularRelatedField(cell=cell, user=self.user)
        self.assertEqual(expected_choices, field.choices)

    def test_regular_relatedfield05(self):
        "Enumerator registry."
        cell = EntityCellRegularField.build(model=FakeOrganisation, name='sector')

        create_sector = FakeSector.objects.create
        s1 = create_sector(title='Sector #1')
        create_sector(title='Sector #2')

        class FakeSectorEnumerator(QSEnumerator):
            def _queryset(this):
                return FakeSector.objects.exclude(id=s1.id)

        enum_registry = _EnumerableRegistry()
        enum_registry.register_related_model(FakeSector, FakeSectorEnumerator)

        field = lv_form.RegularRelatedField(
            cell=cell, user=self.user,
            enumerable_registry=enum_registry,
        )
        self.assertListEqual(
            [
                {'value': '',           'label': pgettext('creme_core-filter', 'All')},
                {'value': lv_form.NULL, 'label': _('* is empty *')},
                *(
                    {'value': pk, 'label': title}
                    for pk, title in FakeSector.objects
                                               .exclude(id=s1.id)
                                               .values_list('id', 'title')
                )
            ],
            field.choices,
        )

    def test_regular_relatedfield06(self):
        "Not enumerable FK."
        cell = EntityCellRegularField.build(model=FakeContact, name='address')
        expected_choices = [
            {'value': '',           'label': pgettext('creme_core-filter', 'All')},
            {'value': lv_form.NULL, 'label': _('* is empty *')},
        ]

        field = lv_form.RegularRelatedField(cell=cell, user=self.user)
        self.assertEqual(expected_choices, field.choices)

    def test_regular_relatedfield07(self):
        "Field has a null_label."
        cell = EntityCellRegularField.build(model=FakeContact, name='is_user')
        expected_choices = [
            {'value': '',           'label': pgettext('creme_core-filter', 'All')},
            {'value': lv_form.NULL, 'label': '* {} *'.format(pgettext('persons-is_user', 'None'))},
        ]

        field = lv_form.RegularRelatedField(cell=cell, user=self.user)
        self.assertEqual(expected_choices, field.choices)

    def test_entity_relatedfield(self):
        cell = EntityCellRegularField.build(model=FakeInvoiceLine, name='linked_invoice')
        field = lv_form.EntityRelatedField(cell=cell, user=self.user)
        self.assertIsInstance(field.widget, lv_form.TextLVSWidget)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=''))
        self.assertEqual(Q(), to_python(value=None))

        value = 'foobar2000'
        self.assertEqual(
            Q(linked_invoice__header_filter_search_field__icontains=value),
            to_python(value=value),
        )

        # TODO: NULL (future field/widget) (needs a nullable FK)
        # self.assertEqual(Q(linked_invoice__isnull=True), to_python(value=...lv_form.NULL...))

    def test_custom_charfield(self):
        cfield = CustomField.objects.create(
            name='Special attack', field_type=CustomField.STR, content_type=FakeContact,
        )

        create_contact = partial(FakeContact.objects.create, user=self.user)
        ryu     = create_contact(first_name='Ryu',     last_name='??')
        ken     = create_contact(first_name='Ken',     last_name='Masters')
        zangief = create_contact(first_name='Zangief', last_name='??')
        create_contact(first_name='Blanka',  last_name='??')

        def set_cfvalue(cfield, entity, value):
            cfield.value_class(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(cfield, ryu,     'Hadoken')
        set_cfvalue(cfield, ken,     'Shoryuken')
        set_cfvalue(cfield, zangief, 'Piledriver')

        cell = EntityCellCustomField(cfield)

        field = lv_form.CustomCharField(cell=cell, user=self.user)
        self.assertIsInstance(field.widget, lv_form.TextLVSWidget)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=''))
        self.assertEqual(Q(), to_python(value=None))

        # ---
        q = to_python(value='ken')
        self.assertIsInstance(q, Q)
        self.assertFalse(q.negated)

        children = q.children
        self.assertEqual(1, len(children))
        k, v = children[0]
        self.assertEqual('pk__in', k)
        self.assertSetEqual({ryu.id, ken.id}, {*v})

    def test_custom_booleanfield(self):
        cfield = CustomField.objects.create(
            name='Shoto', field_type=CustomField.BOOL, content_type=FakeContact,
        )

        create_contact = partial(FakeContact.objects.create, user=self.user)
        ryu     = create_contact(first_name='Ryu',     last_name='??')
        ken     = create_contact(first_name='Ken',     last_name='Masters')
        zangief = create_contact(first_name='Zangief', last_name='??')
        create_contact(first_name='Blanka',  last_name='??')

        def set_cfvalue(cfield, entity, value):
            cfield.value_class(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(cfield, ryu,     True)
        set_cfvalue(cfield, ken,     True)
        set_cfvalue(cfield, zangief, False)

        cell = EntityCellCustomField(cfield)

        field = lv_form.CustomBooleanField(cell=cell, user=self.user)
        self.assertIsInstance(field.widget, lv_form.BooleanLVSWidget)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=None))

        # ---
        q_true = to_python(value=True)
        self.assertIsInstance(q_true, Q)
        self.assertFalse(q_true.negated)

        children = q_true.children
        self.assertEqual(1, len(children))
        k, v = children[0]
        self.assertEqual('pk__in', k)
        self.assertSetEqual({ryu.id, ken.id}, {*v})

        # ---
        q_false = to_python(value=False)
        k, v = q_false.children[0]
        self.assertEqual('pk__in', k)
        self.assertListEqual([zangief.id], [*v])

    def test_custom_integerfield(self):
        cfield = CustomField.objects.create(
            name='HP', field_type=CustomField.INT, content_type=FakeContact,
        )

        create_contact = partial(FakeContact.objects.create, user=self.user)
        ken     = create_contact(first_name='Ken',     last_name='Masters')
        chunli  = create_contact(first_name='Chun-Li', last_name='')
        zangief = create_contact(first_name='Zangief', last_name='??')
        create_contact(first_name='Blanka',  last_name='??')

        def set_cfvalue(cfield, entity, value):
            cfield.value_class(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(cfield, ken,     100)
        set_cfvalue(cfield, chunli,  90)
        set_cfvalue(cfield, zangief, 120)

        cell = EntityCellCustomField(cfield)
        field = lv_form.CustomIntegerField(cell=cell, user=self.user)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=None))
        self.assertEqual(Q(), to_python(value=''))
        self.assertEqual(Q(), to_python(value='notatint'))
        self.assertEqual(Q(), to_python(value='>notatint'))
        self.assertEqual(Q(), to_python(value='<notatint'))
        self.assertEqual(Q(), to_python(value='>=notatint'))
        self.assertEqual(Q(), to_python(value='<=notatint'))
        self.assertEqual(Q(), to_python(value='#100'))

        # EQUAL ---
        q_equal = to_python(value=' 100 ')
        self.assertIsInstance(q_equal, Q)
        self.assertFalse(q_equal.negated)

        equal_children = q_equal.children
        self.assertEqual(1, len(equal_children))
        equal_k, equal_v = equal_children[0]
        self.assertEqual('pk__in', equal_k)
        self.assertListEqual([ken.id], [*equal_v])

        self.assertQEqual(q_equal, to_python(value=' = 100 '))

        # GT ---
        q_gt = to_python(value=' > 100 ')
        gt_k, gt_v = q_gt.children[0]
        self.assertEqual('pk__in', gt_k)
        self.assertListEqual([zangief.id], [*gt_v])

        # LT ---
        q_lt = to_python(value=' < 100 ')
        lt_k, lt_v = q_lt.children[0]
        self.assertEqual('pk__in', lt_k)
        self.assertListEqual([chunli.id], [*lt_v])

        # GTE ---
        q_gte = to_python(value=' >= 100 ')
        __, gte_v = q_gte.children[0]
        self.assertSetEqual({ken.id, zangief.id}, {*gte_v})

        # LTE ---
        q_lte = to_python(value=' <= 100 ')
        __, lte_v = q_lte.children[0]
        self.assertSetEqual({ken.id, chunli.id}, {*lte_v})

        # RANGE ---
        q_range = to_python(value=' >90 ; <= 110 ')
        __, range_v = q_range.children[0]
        self.assertListEqual([ken.id], [*range_v])

    def test_custom_decimalfield(self):
        cfield = CustomField.objects.create(
            name='HP', field_type=CustomField.FLOAT, content_type=FakeContact,
        )

        create_contact = partial(FakeContact.objects.create, user=self.user)
        ken     = create_contact(first_name='Ken',     last_name='Masters')
        chunli  = create_contact(first_name='Chun-Li', last_name='')
        zangief = create_contact(first_name='Zangief', last_name='??')
        create_contact(first_name='Blanka',  last_name='??')

        def set_cfvalue(cfield, entity, value):
            cfield.value_class(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(cfield, ken,     '100')
        set_cfvalue(cfield, chunli,  '90')
        set_cfvalue(cfield, zangief, '120.5')

        cell = EntityCellCustomField(cfield)
        field = lv_form.CustomDecimalField(cell=cell, user=self.user)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=None))
        self.assertEqual(Q(), to_python(value=''))
        self.assertEqual(Q(), to_python(value='notadecimal'))
        self.assertEqual(Q(), to_python(value='>notadecimal'))
        self.assertEqual(Q(), to_python(value='<notadecimal'))
        self.assertEqual(Q(), to_python(value='>=notadecimal'))
        self.assertEqual(Q(), to_python(value='<=notadecimal'))
        self.assertEqual(Q(), to_python(value='#100'))

        # EQUAL ---
        q_equal = to_python(value=' 100 ')
        self.assertIsInstance(q_equal, Q)
        self.assertFalse(q_equal.negated)

        equal_children = q_equal.children
        self.assertEqual(1, len(equal_children))
        equal_k, equal_v = equal_children[0]
        self.assertEqual('pk__in', equal_k)
        self.assertListEqual([ken.id], [*equal_v])

        self.assertQEqual(q_equal, to_python(value=' = 100 '))

        # GT ---
        q_gt = to_python(value=' > 100 ')
        gt_k, gt_v = q_gt.children[0]
        self.assertEqual('pk__in', gt_k)
        self.assertListEqual([zangief.id], [*gt_v])

        # LT ---
        q_lt = to_python(value=' < 100 ')
        lt_k, lt_v = q_lt.children[0]
        self.assertEqual('pk__in', lt_k)
        self.assertListEqual([chunli.id], [*lt_v])

        # GTE ---
        q_gte = to_python(value=' >= 100 ')
        __, gte_v = q_gte.children[0]
        self.assertSetEqual({ken.id, zangief.id}, {*gte_v})

        # LTE ---
        q_lte = to_python(value=' <= 100 ')
        __, lte_v = q_lte.children[0]
        self.assertSetEqual({ken.id, chunli.id}, {*lte_v})

        # RANGE ---
        q_range = to_python(value=' >90 ; <= 110 ')
        __, range_v = q_range.children[0]
        self.assertListEqual([ken.id], [*range_v])

        # With decimal part ---
        # TODO: fix when 'settings.USE_L10N = True' is set by default
        q_sep = to_python(value=number_format(Decimal('120.5'), use_l10n=True))
        __, sep_v = q_sep.children[0]
        self.assertListEqual([zangief.id], [*sep_v])

    def test_custom_datefield(self):
        cfield = CustomField.objects.create(
            name='Party', field_type=CustomField.DATETIME, content_type=FakeContact,
        )

        create_contact = partial(FakeContact.objects.create, user=self.user)
        ryu     = create_contact(first_name='Ryu',     last_name='??')
        ken     = create_contact(first_name='Ken',     last_name='Masters')
        zangief = create_contact(first_name='Zangief', last_name='??')
        blanka  = create_contact(first_name='Blanka',  last_name='??')
        create_contact(first_name='Chun Li', last_name='??')

        def set_cfvalue(cfield, entity, value):
            cfield.value_class(custom_field=cfield, entity=entity).set_value_n_save(value)

        create_dt = self.create_datetime
        set_cfvalue(cfield, ryu,     create_dt(year=2019, month=2, day=12))
        set_cfvalue(cfield, ken,     create_dt(year=2019, month=2, day=27))
        set_cfvalue(cfield, zangief, create_dt(year=2019, month=1, day=27))
        set_cfvalue(cfield, blanka,  create_dt(year=2019, month=3, day=5))

        cell = EntityCellCustomField(cfield)

        field = lv_form.CustomDatetimeField(cell=cell, user=self.user)

        to_python = field.to_python
        # self.assertEqual(Q(), to_python(value=None))  TODO ?
        # self.assertEqual(Q(), to_python(value=''))
        self.assertEqual(Q(), to_python(value=['', '']))

        # ---
        q_range = to_python(value=['01-02-2019', '28-02-2019'])
        self.assertIsInstance(q_range, Q)
        self.assertFalse(q_range.negated)

        children = q_range.children
        self.assertEqual(1, len(children))
        k, v = children[0]
        self.assertEqual('pk__in', k)
        self.assertSetEqual({ryu.id, ken.id}, {*v})

        # ---
        q_start = to_python(value=['01-02-2019', ''])
        k, v = q_start.children[0]
        self.assertEqual('pk__in', k)
        self.assertSetEqual({ryu.id, ken.id, blanka.id}, {*v})

        q_end = to_python(value=['', '01-03-2019'])
        k, v = q_end.children[0]
        self.assertEqual('pk__in', k)
        self.assertSetEqual({ryu.id, ken.id, zangief.id}, {*v})

        # Invalid dates ---------------------------
        self.assertEqual(Q(), to_python(value=['abc', 'def']))

        k, v = to_python(value=['01-02-2019', 'zblu']).children[0]
        self.assertEqual('pk__in', k)
        self.assertSetEqual({ryu.id, ken.id, blanka.id}, {*v})

        v = to_python(value=['123', '28-02-2019']).children[0][1]
        self.assertSetEqual({ryu.id, ken.id, zangief.id}, {*v})

    def test_custom_enumfield(self):
        cfield = CustomField.objects.create(
            name='Attack', field_type=CustomField.ENUM, content_type=FakeContact,
        )

        create_evalue = CustomFieldEnumValue.objects.create
        punch  = create_evalue(custom_field=cfield, value='Punch')
        kick   = create_evalue(custom_field=cfield, value='Kick')
        hold   = create_evalue(custom_field=cfield, value='Hold')

        create_contact = partial(FakeContact.objects.create, user=self.user)
        ryu     = create_contact(first_name='Ryu',     last_name='??')
        ken     = create_contact(first_name='Ken',     last_name='Masters')
        zangief = create_contact(first_name='Zangief', last_name='??')
        create_contact(first_name='Blanka',  last_name='??')
        create_contact(first_name='Chun Li', last_name='??')

        klass = cfield.value_class

        def set_cfvalue(entity, evalue):
            klass(custom_field=cfield, entity=entity).set_value_n_save(evalue.id)

        set_cfvalue(ryu,     kick)
        set_cfvalue(ken,     kick)
        set_cfvalue(zangief, hold)

        cell = EntityCellCustomField(cfield)

        field = lv_form.CustomChoiceField(cell=cell, user=self.user)
        self.assertIsInstance(field.widget, lv_form.SelectLVSWidget)

        expected_choices = [
            {'value': '',           'label': pgettext('creme_core-filter', 'All')},
            {'value': lv_form.NULL, 'label': _('* is empty *')},
            {'value': punch.id,     'label': punch.value},
            {'value': kick.id,      'label': kick.value},
            {'value': hold.id,      'label': hold.value},
        ]
        self.assertEqual(expected_choices, field.choices)
        self.assertEqual(expected_choices, field.widget.choices)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=None))
        self.assertEqual(Q(), to_python(value=''))

        # ---
        q_kick = to_python(value=str(kick.id))
        self.assertIsInstance(q_kick, Q)
        self.assertFalse(q_kick.negated)

        children = q_kick.children
        self.assertEqual(1, len(children))
        k, v = children[0]
        self.assertEqual('pk__in', k)
        self.assertSetEqual({ryu.id, ken.id}, {*v})

        # ---
        q_hold = to_python(value=str(hold.id))
        k, v = q_hold.children[0]
        self.assertEqual('pk__in', k)
        self.assertListEqual([zangief.id], [*v])

        # ---
        q_null = to_python(value=lv_form.NULL)
        self.assertIsInstance(q_null, Q)
        self.assertTrue(q_null.negated)

        children = q_null.children
        self.assertEqual(1, len(children))
        k, v = children[0]
        self.assertEqual('pk__in', k)
        self.assertSetEqual({ryu.id, ken.id, zangief.id}, {*v})

    def test_custom_multienumfield(self):
        cfield = CustomField.objects.create(
            name='Attack', field_type=CustomField.MULTI_ENUM, content_type=FakeContact,
        )

        create_evalue = CustomFieldEnumValue.objects.create
        punch = create_evalue(custom_field=cfield, value='Punch')
        kick  = create_evalue(custom_field=cfield, value='Kick')
        hold  = create_evalue(custom_field=cfield, value='Hold')

        create_contact = partial(FakeContact.objects.create, user=self.user)
        ryu     = create_contact(first_name='Ryu',     last_name='??')
        ken     = create_contact(first_name='Ken',     last_name='Masters')
        zangief = create_contact(first_name='Zangief', last_name='??')
        create_contact(first_name='Blanka',  last_name='??')
        create_contact(first_name='Chun Li', last_name='??')

        klass = cfield.value_class

        def set_cfvalue(entity, *evalues):
            klass(custom_field=cfield, entity=entity).set_value_n_save(evalues)

        set_cfvalue(ryu,     kick, hold)
        set_cfvalue(ken,     kick)
        set_cfvalue(zangief, hold)

        cell = EntityCellCustomField(cfield)

        field = lv_form.CustomChoiceField(cell=cell, user=self.user)
        self.assertIsInstance(field.widget, lv_form.SelectLVSWidget)

        expected_choices = [
            {'value': '',           'label': pgettext('creme_core-filter', 'All')},
            {'value': lv_form.NULL, 'label': _('* is empty *')},
            {'value': punch.id,     'label': punch.value},
            {'value': kick.id,      'label': kick.value},
            {'value': hold.id,      'label': hold.value},
        ]
        self.assertEqual(expected_choices, field.choices)
        self.assertEqual(expected_choices, field.widget.choices)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=None))
        self.assertEqual(Q(), to_python(value=''))

        # ---
        q_kick = to_python(value=str(kick.id))
        self.assertIsInstance(q_kick, Q)
        self.assertFalse(q_kick.negated)

        children = q_kick.children
        self.assertEqual(1, len(children))
        k, v = children[0]
        self.assertEqual('pk__in', k)
        self.assertSetEqual({ryu.id, ken.id}, {*v})

        # ---
        q_hold = to_python(value=str(hold.id))
        k, v = q_hold.children[0]
        self.assertEqual('pk__in', k)
        self.assertSetEqual({ryu.id, zangief.id}, {*v})

        # ---
        q_null = to_python(value=lv_form.NULL)
        self.assertIsInstance(q_null, Q)
        self.assertTrue(q_null.negated)

        children = q_null.children
        self.assertEqual(1, len(children))
        k, v = children[0]
        self.assertEqual('pk__in', k)
        self.assertSetEqual({ryu.id, ken.id, zangief.id}, {*v})

    def test_relationfield(self):
        user = self.user
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_trains', 'trains'),
            ('test-object_trains',  'trained by'),
        )[1]

        create_contact = partial(FakeContact.objects.create, user=user)
        ryu   = create_contact(first_name='Ryu',   last_name='??')
        ken   = create_contact(first_name='Ken',   last_name='Masters')
        guile = create_contact(first_name='Guile', last_name='??')
        create_contact(first_name='Blanka',  last_name='??')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        dojo = create_orga(name="Gouken's Dojo")
        army = create_orga(name='US Army')

        create_rel = partial(Relation.objects.create, user=user, type=rtype)
        create_rel(subject_entity=ryu, object_entity=dojo)
        create_rel(subject_entity=ken, object_entity=dojo)
        create_rel(subject_entity=guile, object_entity=army)

        cell = EntityCellRelation(model=FakeContact, rtype=rtype)

        field = lv_form.RelationField(cell=cell, user=self.user)
        self.assertIsInstance(field.widget, lv_form.TextLVSWidget)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=''))

        # ---
        q = to_python(value='dojo')
        self.assertIsInstance(q, Q)
        self.assertFalse(q.negated)

        children = q.children
        self.assertEqual(1, len(children))
        k, v = children[0]
        self.assertEqual('pk__in', k)
        self.assertSetEqual({ryu.id, ken.id}, {*v})

    def test_propertiesfield(self):
        from creme.creme_core.core.entity_cell import EntityCellFunctionField
        from creme.creme_core.function_fields import PropertiesField
        from creme.creme_core.models import CremePropertyType

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ct_orga = ContentType.objects.get_for_model(FakeOrganisation)
        ptype1 = create_ptype(str_pk='test-cool', text='is cool')
        ptype2 = create_ptype(
            str_pk='test-beautiful', text='is beautiful',
            subject_ctypes=[ct_orga, FakeContact],
        )
        ptype3 = create_ptype(
            str_pk='test-is_a_trust', text='is a trust', subject_ctypes=[ct_orga],
        )

        funfield = PropertiesField()
        cell = EntityCellFunctionField(model=FakeContact, func_field=funfield)

        field_class = PropertiesField.search_field_builder
        self.assertIsNotNone(field_class)

        field = field_class(cell=cell, user=self.user)
        choices = field.choices
        self.assertGreaterEqual(len(choices), 2)
        self.assertDictEqual(
            {'value': '', 'label': pgettext('creme_core-filter', 'All')},
            choices[0],
        )
        self.assertDictEqual(
            {'value': lv_form.NULL, 'label': _('* no property *')},
            choices[1],
        )
        self.assertIn({'value': ptype1.id, 'label': str(ptype1)}, choices)
        self.assertIn({'value': ptype2.id, 'label': str(ptype2)}, choices)
        self.assertNotIn({'value': ptype3.id, 'label': str(ptype3)}, choices)

        widget = field.widget
        self.assertIsInstance(widget, lv_form.SelectLVSWidget)
        self.assertEqual(field.choices, field.widget.choices)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=None))
        self.assertEqual(Q(), to_python(value=''))
        self.assertEqual(Q(), to_python(value='invalid'))

        self.assertEqual(Q(properties__type=ptype1.id), to_python(value=ptype1.id))
        self.assertEqual(Q(properties__isnull=True),    to_python(value=lv_form.NULL))


class SearchFormTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = CremeUser(
            username='yui', email='kawa.yui@kimengumi.jp',
            first_name='Yui', last_name='Kawa',
        )

    def test_search_form01(self):
        "Empty data."
        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        fname_cell = build_cell(name='first_name')
        birth_cell = build_cell(name='birthday')

        form = lv_form.ListViewSearchForm(
            field_registry=ListViewSearchFieldRegistry(),
            cells=[fname_cell, birth_cell],
            data={},
            user=self.user,
        )

        fields = form.fields
        self.assertIsInstance(fields, dict)
        self.assertEqual(2, len(fields))
        self.assertIsInstance(fields.get(fname_cell.key), lv_form.RegularCharField)
        self.assertIsInstance(fields.get(birth_cell.key), lv_form.RegularDateField)

        form.full_clean()

        self.assertEqual(Q(), form.search_q)

        self.assertHTMLEqual(  # NB: not "required"
            '<input class="lv-state-field" data-lv-search-widget="text" '
            '       id="id_search-{key}" name="search-{key}" type="text" />'.format(
                key=fname_cell.key,
            ),
            str(form[fname_cell.key]),
        )

        self.assertDictEqual({}, form.filtered_data)

    def test_search_form02(self):
        "Some data."
        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        fname_cell = build_cell(name='first_name')
        lname_cell = build_cell(name='last_name')
        nerd_cell  = build_cell(name='is_a_nerd')
        birth_cell = build_cell(name='birthday')

        data = {
            f'search-{fname_cell.key}': 'yui',
            f'search-{nerd_cell.key}': '1',
            f'search-{birth_cell.key}-start': '25-02-2019',
        }
        form = lv_form.ListViewSearchForm(
            field_registry=ListViewSearchFieldRegistry(),
            cells=[fname_cell, lname_cell, nerd_cell, birth_cell],
            data={
                **data,
                'i_m_not_used': 'neither_do_i',  # <= not in filtered_data
            },
            user=self.user,
        )
        form.full_clean()

        self.assertEqual(
            Q(first_name__icontains='yui')
            & Q(is_a_nerd=True)
            & Q(birthday__gte=self.create_datetime(day=25, month=2, year=2019)),
            form.search_q,
        )

        self.assertIn('value="yui"',        str(form[fname_cell.key]))
        self.assertIn('value="1" selected', str(form[nerd_cell.key]))
        self.assertIn('value="25-02-2019"', str(form[birth_cell.key]))

        self.assertNotIn('value="', str(form[lname_cell.key]))

        self.assertEqual(data, form.filtered_data)
