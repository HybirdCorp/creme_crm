import difflib
from json import loads as json_load
from unittest.util import safe_repr

from django.contrib.contenttypes.models import ContentType
from django.db.models.query import Q, QuerySet
from django.forms.widgets import Select
from django.test.testcases import assert_and_parse_html
from django.urls import reverse
from django.utils.html import escape
from django.utils.translation import gettext as _
from django.utils.translation import override as override_language
from django.utils.translation import pgettext

from creme.creme_core.forms.fields import RelativeDatePeriodField
from creme.creme_core.forms.widgets import (
    ActionButtonList,
    CalendarWidget,
    CremeTextarea,
    DatePeriodWidget,
    DateRangeSelect,
    DateTimeWidget,
    DurationWidget,
    DynamicSelect,
    EntityCreatorWidget,
    EntitySelector,
    RelativeDatePeriodWidget,
    UnorderedMultipleChoiceWidget,
    WidgetAction,
)
from creme.creme_core.utils import date_period, date_range
from creme.creme_core.utils.url import TemplateURLBuilder

from ..base import CremeTestCase
from ..fake_models import FakeContact


class CalendarWidgetTestCase(CremeTestCase):
    maxDiff = None

    @override_language('en')
    def test_render__en(self):
        name = 'my_calendar'
        value = self.formfield_value_date(2023, 3, 26)
        help_text = _('E.g. {}').format('2025-12-31')
        self.assertHTMLEqual(
            f'<div class="creme-datepicker">'
            f'  <div class="help-text-format">{help_text}</div>'
            f'  <input type="text" widget="ui-creme-datepicker"'
            f'         class="ui-creme-datepicker ui-creme-input ui-creme-widget widget-auto"'
            f'         format="yy-mm-dd" name="{name}" value="{value}">'
            f'</div>',
            CalendarWidget().render(name, value),
        )

    @override_language('fr')
    def test_render__fr(self):
        name = 'calendar'
        value = self.formfield_value_date(2024, 4, 27)
        help_text = _('E.g. {}').format('31/12/2025')
        self.assertHTMLEqual(
            f'<div class="creme-datepicker">'
            f'  <div class="help-text-format">{help_text}</div>'
            f'  <input type="text" widget="ui-creme-datepicker"'
            f'         class="ui-creme-datepicker ui-creme-input ui-creme-widget widget-auto"'
            f'         format="dd/mm/yy" name="{name}" value="{value}">'
            f'</div>',
            CalendarWidget().render(name, value),
        )

    def test_js_date_format(self):
        fmt = CalendarWidget.js_date_format
        self.assertEqual('yy-mm-dd', fmt('%Y-%m-%d'))
        self.assertEqual('yy/mm/dd', fmt('%Y/%m/%d'))
        self.assertEqual('dd-mm-yy', fmt('%d-%m-%Y'))
        self.assertEqual('dd,M,y',   fmt('%d,%b,%y'))
        self.assertEqual('dd,MM,y',  fmt('%d,%B,%y'))


class DateTimeWidgetTestCase(CremeTestCase):
    maxDiff = None

    @override_language('en')
    def test_render__en(self):
        name = 'my_dt'
        value = self.formfield_value_datetime(year=2023, month=3, day=26, hour=15)
        self.assertHTMLEqual(
            f'<ul class="ui-creme-widget widget-auto ui-creme-datetimepicker"'
            f'    widget="ui-creme-datetimepicker" format="yy-mm-dd">'
            f'  <input name="{name}" type="hidden" value="{value}">'
            f'  <li>{_("On")}</li>'
            f'  <li class="date">'
            f'    <input type="text" maxlength="12" title="{_("Date")}" />'
            f'  </li>'
            f'  <li>{_("at")}</li>'
            f'  <li class="hour">'
            f'    <input type="number" min="0" max="23" title="{_("Hour")}" />'
            f'  </li>'
            f'  <li>{_("h")}</li>'
            f'  <li class="minute">'
            f'    <input type="number" min="0" max="59" title="{_("Minute")}" />'
            f'  </li>'
            f'  <li></li>'
            f'  <li class="clear"><button type="button">{_("Clean")}</button></li>'
            f'  <li class="now"><button type="button">{_("Now")}</button></li>'
            f'</ul>',
            DateTimeWidget().render(name, value),
        )

    def test_js_date_format(self):
        fmt = DateTimeWidget.js_date_format
        self.assertEqual('yy-mm-dd', fmt('%Y-%m-%d'))
        self.assertEqual('dd,MM,y',  fmt('%d,%B,%y'))


class DateRangeSelectTestCase(CremeTestCase):
    maxDiff = None

    @override_language('en')
    def test_render__en(self):
        name = 'my_range'

        widget = DateRangeSelect()
        p_range = date_range.PastRange()
        widget.range_registry = date_range.DateRangeRegistry(
            p_range,
            date_range.FutureRange(),
        )

        value = p_range.name
        custom_label = pgettext('creme_core-date_range', 'Customized')
        self.assertHTMLEqual(
            f'<span class="ui-creme-daterange-selector ui-creme-widget widget-auto"'
            f'      data-format="yy-mm-dd" widget="ui-creme-daterange-selector">'
            f'  <input name="{name}" value="{value}"'
            f'         class="ui-creme-daterange-selector ui-creme-input" type="hidden">'
            f'  <select class="daterange-input range-type">'
            f'    <option value="">{custom_label}</option>'
            f'    <option value="in_past">{_("In the past")}</option>'
            f'    <option value="in_future">{_("In the future")}</option>'
            f'  </select>'
            f'  <span class="daterange-inputs">'
            f'    {_("From")}<input type="text" class="daterange-input date-start" />'
            f'    &nbsp;{_("To")}<input type="text" class="daterange-input date-end" />'
            f'  </span>'
            f'</span>',
            widget.render(name, value),
        )


class DatePeriodWidgetTestCase(CremeTestCase):
    @override_language('en')
    def test_render_en_no_value(self):
        name = 'date_period'
        self.assertHTMLEqual(
            f'<ul class="hbox ui-layout">'
            f' <li>'
            f'  <input class="dperiod-value" min="1" name="{name}_1" type="number">'
            f' </li>'
            f' <li>'
            f'  <div class="select-wrapper">'
            f'   <select class="dperiod-type" name="{name}_0" />'
            f'   <div class="select-arrow"/>'
            f'  </div>'
            f' </li>'
            f'</ul>',
            DatePeriodWidget().render(name=name, value=None),
        )

    @override_language('en')
    def test_render_en_list_value(self):
        widget = DatePeriodWidget()
        widget.choices = [
            (period.name, period.verbose_name) for period in [
                date_period.HoursPeriod,
                date_period.DaysPeriod,
                date_period.WeeksPeriod,
            ]
        ]
        name = 'my_date_period'
        self.assertHTMLEqual(
            f'<ul class="hbox ui-layout">'
            f' <li>'
            f'  <input class="dperiod-value" min="1" name="{name}_1" type="number" value="2">'
            f' </li>'
            f' <li>'
            f'  <div class="select-wrapper">'
            f'   <select class="dperiod-type" name="{name}_0">'
            f'    <option value="hours">Hour(s)</option>'
            f'    <option value="days">Day(s)</option>'
            f'    <option value="weeks" selected>Week(s)</option>'
            f'   </select>'
            f'   <div class="select-arrow"/>'
            f'  </div>'
            f' </li>'
            f'</ul>',
            widget.render(name=name, value=['weeks', '2']),
        )

    @override_language('fr')
    def test_render_fr(self):
        widget = DatePeriodWidget()
        widget.choices = [
            (period.name, period.verbose_name) for period in [
                date_period.HoursPeriod,
                date_period.DaysPeriod,
                date_period.WeeksPeriod,
            ]
        ]
        name = 'my_period'
        expected_html = (
            f'<ul class="hbox ui-layout">'
            f' <li>'
            f'  <input class="dperiod-value" min="1" name="{name}_1" type="number" value="1">'
            f' </li>'
            f' <li>'
            f'  <div class="select-wrapper">'
            f'   <select class="dperiod-type" name="{name}_0">'
            f'    <option value="hours">Heure(s)</option>'
            f'    <option value="days" selected>Jour(s)</option>'
            f'    <option value="weeks">Semaine(s)</option>'
            f'   </select>'
            f'   <div class="select-arrow"/>'
            f'  </div>'
            f' </li>'
            f'</ul>'
        )
        self.assertHTMLEqual(
            expected_html, widget.render(name=name, value=date_period.DaysPeriod(1)),
        )
        self.assertHTMLEqual(
            expected_html, widget.render(name=name, value={'type': 'days', 'value': 1}),
        )

    def test_value_from_datadict(self):
        self.assertListEqual(
            ['hours', '5'],
            DatePeriodWidget().value_from_datadict(
                name='offset',
                data={
                    'offset_0': 'hours',
                    'offset_1': '5',
                    'whatever': 'foo',
                },
                files={},
            ),
        )


class RelativeDatePeriodWidgetTestCase(CremeTestCase):
    @override_language('en')
    def test_render_en_no_value(self):
        name = 'date_period'
        self.maxDiff = None
        self.assertHTMLEqual(
            f'<ul class="hbox ui-layout">'
            f' <li>'
            f'  <input class="relative_dperiod-value" min="1" name="{name}_2" type="number">'
            f' </li>'
            f' <li>'
            f'  <div class="select-wrapper">'
            f'   <select class="relative_dperiod-type" name="{name}_1" />'
            f'   <div class="select-arrow" />'
            f'  </div>'
            f' </li>'
            f' <li>'
            f'  <div class="select-wrapper">'
            f'   <select class="relative_dperiod-direction" name="{name}_0" />'
            f'   <div class="select-arrow" />'
            f' </li>'
            f'</ul>',
            RelativeDatePeriodWidget().render(name=name, value=None),
        )

    @override_language('en')
    def test_render_en_list_value(self):
        widget = RelativeDatePeriodWidget()
        widget.period_choices = [
            (period.name, period.verbose_name) for period in [
                date_period.HoursPeriod,
                date_period.DaysPeriod,
                date_period.WeeksPeriod,
            ]
        ]
        widget.relative_choices = [(-1, 'Before'), (1, 'After')]
        name = 'my_offset'
        self.maxDiff = None
        self.assertHTMLEqual(
            f'<ul class="hbox ui-layout">'
            f' <li>'
            f'  <input class="relative_dperiod-value" min="1" name="{name}_2"'
            f'         type="number" value="5">'
            f' </li>'
            f' <li>'
            f'  <div class="select-wrapper">'
            f'   <select class="relative_dperiod-type" name="{name}_1">'
            f'    <option value="hours">Hour(s)</option>'
            f'    <option value="days">Day(s)</option>'
            f'    <option value="weeks" selected>Week(s)</option>'
            f'   </select>'
            f'   <div class="select-arrow"/>'
            f'  </div>'
            f' </li>'
            f' <li>'
            f'  <div class="select-wrapper">'
            f'   <select class="relative_dperiod-direction" name="{name}_0">'
            f'    <option value="-1">Before</option>'
            f'    <option value="1" selected>After</option>'
            f'   </select>'
            f'   <div class="select-arrow" />'
            f' </li>'
            f'</ul>',
            widget.render(
                name=name, value=[1, [date_period.WeeksPeriod.name, '5']],
            ),
        )

    @override_language('fr')
    def test_render_fr(self):
        widget = RelativeDatePeriodWidget()
        widget.period_choices = [
            (period.name, period.verbose_name) for period in [
                date_period.HoursPeriod,
                date_period.DaysPeriod,
                date_period.WeeksPeriod,
            ]
        ]
        widget.relative_choices = [(-1, 'Avant'), (1, 'Après')]
        name = 'my_period'
        self.maxDiff = None
        self.assertHTMLEqual(
            f'<ul class="hbox ui-layout">'
            f' <li>'
            f'  <input class="relative_dperiod-value" min="1" name="{name}_2"'
            f'         type="number" value="2">'
            f' </li>'
            f' <li>'
            f'  <div class="select-wrapper">'
            f'   <select class="relative_dperiod-type" name="{name}_1">'
            f'    <option value="hours">Heure(s)</option>'
            f'    <option value="days" selected>Jour(s)</option>'
            f'    <option value="weeks">Semaine(s)</option>'
            f'   </select>'
            f'   <div class="select-arrow"/>'
            f'  </div>'
            f' </li>'
            f' <li>'
            f'  <div class="select-wrapper">'
            f'   <select class="relative_dperiod-direction" name="{name}_0">'
            f'    <option value="-1" selected>Avant</option>'
            f'    <option value="1">Après</option>'
            f'   </select>'
            f'   <div class="select-arrow" />'
            f' </li>'
            f'</ul>',
            widget.render(
                name=name,
                value=RelativeDatePeriodField.RelativeDatePeriod(
                    sign=-1, period=date_period.DaysPeriod(2),
                ),
            ),
        )

    def test_value_from_datadict(self):
        self.assertListEqual(
            ['-1', ['hours', '5']],
            RelativeDatePeriodWidget().value_from_datadict(
                name='offset',
                data={
                    'offset_0': '-1',
                    'offset_1': 'hours',
                    'offset_2': '5',
                    'whatever': 'foo',
                },
                files={},
            ),
        )


class DynamicSelectTestCase(CremeTestCase):
    def test_options_list(self):
        select = DynamicSelect(options=[(1, 'A'), (2, 'B')])

        self.assertIsList(select.options)
        self.assertListEqual([(1, 'A'), (2, 'B')], select.choices)

    def test_options_queryset(self):
        user = self.get_root_user()
        FakeContact.objects.create(last_name='Doe', first_name='John', user=user)

        select = DynamicSelect(options=FakeContact.objects.values_list('id', 'last_name'))
        self.assertIsInstance(select.options, QuerySet)
        self.assertListEqual(
            [*FakeContact.objects.values_list('id', 'last_name')],
            [*select.choices],
        )

    def test_options_function(self):
        select = DynamicSelect(options=lambda: [(id, str(id)) for id in range(10)])

        self.assertTrue(callable(select.options))
        self.assertListEqual(
            [(id_, str(id_)) for id_ in range(10)],
            select.choices,
        )

    def test_options_generator(self):
        select = DynamicSelect(options=((id_, str(id_)) for id_ in range(10)))

        self.assertIsList(select.options)
        self.assertListEqual(
            [(id_, str(id_)) for id_ in range(10)],
            select.choices,
        )

    def test_render(self):
        select = DynamicSelect(options=[(1, 'A'), (2, 'B')], avoid_empty=True)
        self.assertHTMLEqual(
            '<select class="ui-creme-input ui-creme-widget widget-auto ui-creme-dselect" '
            ' name="test" url="" widget="ui-creme-dselect" data-no-empty="1">'
            '  <option value="1">A</option>'
            '  <option value="2" selected>B</option>'
            '</select>',
            select.render('test', 2)
        )

        Choice = DynamicSelect.Choice
        select = DynamicSelect(
            options=[
                (Choice(1, disabled=True, help='disabled'), 'A'),
                (Choice(2, help='item B'), 'B'),
                (Choice(3, help='item C'), 'C'),
                (Choice(4, readonly=True, help='readonly'), 'D'),
            ],
        )
        self.assertHTMLEqual(
            '<select class="ui-creme-input ui-creme-widget widget-auto ui-creme-dselect" '
            ' name="test" url="" widget="ui-creme-dselect">'
            '  <option value="1" disabled help="disabled">A</option>'
            '  <option value="2" selected help="item B">B</option>'
            '  <option value="3" help="item C">C</option>'
            '  <option value="4" readonly help="readonly">D</option>'
            '</select>',
            select.render('test', 2)
        )


class UnorderedMultipleChoiceTestCase(CremeTestCase):
    maxDiff = None

    def test_render_option_groups(self):
        select = UnorderedMultipleChoiceWidget(
            choices=[
                ('Group A', ((1, 'A'), (2, 'B'))),
                ('Group B', ((3, 'C'), (4, 'D'), (5, 'E'))),
            ],
            viewless=False,
        )
        self.assertEqual(5, select._choice_count())

        html = '''
<div class="ui-creme-widget widget-auto ui-creme-checklistselect"
     widget="ui-creme-checklistselect" selectall="3">
    <select multiple="multiple" class="ui-creme-input" name="A">
        <optgroup label="Group A">
            <option value="1">A</option>
            <option value="2">B</option>
        </optgroup>
        <optgroup label="Group B">
            <option value="3" selected>C</option>
            <option value="4" selected>D</option>
            <option value="5">E</option>
        </optgroup>
    </select>
    <span class="checklist-counter"></span>
    <div class="checklist-header">
        <a type="button" class="checklist-check-all">{check_all}</a>
        <a type="button" class="checklist-check-none">{check_none}</a>
    </div>
    <div class="checklist-body"><ul class="checklist-content"></ul></div>
</div>'''.format(
            check_all=_('Check all'),
            check_none=_('Check none'),
        )
        self.assertHTMLEqual(html, select.render('A', (3, 4,)))

    def test_render_viewless01(self):
        "Default behaviour (integer value => 40)."
        name = 'my_field'
        select = UnorderedMultipleChoiceWidget(choices=[(1, 'A'), (2, 'B')])
        self.assertEqual(2, select._choice_count())

        html = '''
<div class="ui-creme-widget widget-auto ui-creme-checklistselect" less="40"
     widget="ui-creme-checklistselect" selectall="3">
    <select multiple="multiple" class="ui-creme-input" name="{name}">
        <option value="1">A</option>
        <option value="2">B</option>
    </select>
    <span class="checklist-counter"></span>
    <div class="checklist-header">
        <a type="button" class="checklist-check-all hidden">{check_all}</a>
        <a type="button" class="checklist-check-none hidden">{check_none}</a>
    </div>
    <div class="checklist-body"><ul class="checklist-content"></ul></div>
    <div class="checklist-footer"><a class="checklist-toggle-less">{viewless_lbl}</a></div>
</div>'''.format(
            name=name,
            check_all=_('Check all'),
            check_none=_('Check none'),
            viewless_lbl=_('More'),
        )
        self.assertHTMLEqual(html, select.render(name, ()))

    def test_render_viewless02(self):
        "Let the JS chose the behaviour."
        name = 'my_field'
        select = UnorderedMultipleChoiceWidget(choices=[(1, 'A'), (2, 'B')], viewless=True)
        self.assertEqual(2, select._choice_count())

        html = '''
<div class="ui-creme-widget widget-auto ui-creme-checklistselect" less
     widget="ui-creme-checklistselect" selectall="3">
    <select multiple="multiple" class="ui-creme-input" name="{name}">
        <option value="1">A</option>
        <option value="2" selected>B</option>
    </select>
    <span class="checklist-counter"></span>
    <div class="checklist-header">
        <a type="button" class="checklist-check-all hidden">{check_all}</a>
        <a type="button" class="checklist-check-none hidden">{check_none}</a>
    </div>
    <div class="checklist-body"><ul class="checklist-content"></ul></div>
    <div class="checklist-footer"><a class="checklist-toggle-less">{viewless_lbl}</a></div>
</div>'''.format(
            name=name,
            check_all=_('Check all'),
            check_none=_('Check none'),
            viewless_lbl=_('More'),
        )
        self.assertHTMLEqual(html, select.render(name, (2,)))

    def test_render_viewless03(self):
        "Custom integer value."
        name = 'my_field'
        select = UnorderedMultipleChoiceWidget(choices=[(1, 'A'), (2, 'B')], viewless=30)
        self.assertEqual(2, select._choice_count())

        html = '''
<div class="ui-creme-widget widget-auto ui-creme-checklistselect" less="30"
     widget="ui-creme-checklistselect" selectall="3">
    <select multiple="multiple" class="ui-creme-input" name="{name}">
        <option value="1">A</option>
        <option value="2">B</option>
    </select>
    <span class="checklist-counter"></span>
    <div class="checklist-header">
        <a type="button" class="checklist-check-all hidden">{check_all}</a>
        <a type="button" class="checklist-check-none hidden">{check_none}</a>
    </div>
    <div class="checklist-body"><ul class="checklist-content"></ul></div>
    <div class="checklist-footer"><a class="checklist-toggle-less">{viewless_lbl}</a></div>
</div>'''.format(
            name=name,
            check_all=_('Check all'),
            check_none=_('Check none'),
            viewless_lbl=_('More'),
        )
        self.assertHTMLEqual(html, select.render(name, ()))

    def test_filtertype(self):
        select1 = UnorderedMultipleChoiceWidget()
        self.assertIsNone(select1.filtertype)

        select2 = UnorderedMultipleChoiceWidget(filtertype='search')
        self.assertEqual('search', select2.filtertype)

        select2.filtertype = 'filter'
        self.assertEqual('filter', select2.filtertype)

        with self.assertRaises(ValueError):
            select2.filtertype = 'invalid'

    def test_build_filtertype(self):
        select = UnorderedMultipleChoiceWidget()
        self.assertIsNone(select._build_filtertype(0))
        self.assertIsNone(select._build_filtertype(5))
        self.assertEqual('search', select._build_filtertype(10))
        self.assertEqual('search', select._build_filtertype(20))
        self.assertEqual('filter', select._build_filtertype(30))
        self.assertEqual('filter', select._build_filtertype(100))

        select = UnorderedMultipleChoiceWidget(filtertype='search')
        self.assertEqual('search', select._build_filtertype(0))
        self.assertEqual('search', select._build_filtertype(5))
        self.assertEqual('search', select._build_filtertype(10))
        self.assertEqual('search', select._build_filtertype(20))
        self.assertEqual('search', select._build_filtertype(30))
        self.assertEqual('search', select._build_filtertype(100))

    def test_render_search01(self):
        "Automatic/default behaviour."
        name = 'my_choice_field'
        select = UnorderedMultipleChoiceWidget(
            choices=[(1, 'A'), (2, 'B'), (3, 'C')], viewless=False,
        )
        self.assertEqual(10, select.MIN_SEARCH_COUNT)
        self.assertEqual(30, select.MIN_FILTER_COUNT)

        select.MIN_SEARCH_COUNT = 3

        html = '''
<div class="ui-creme-widget widget-auto ui-creme-checklistselect"
     widget="ui-creme-checklistselect" selectall="3">
    <select multiple="multiple" class="ui-creme-input" name="{name}">
        <option value="1">A</option>
        <option value="2">B</option>
        <option value="3">C</option>
    </select>
    <span class="checklist-counter"></span>
    <div class="checklist-header">
        <a type="button" class="checklist-check-all">{check_all}</a>
        <a type="button" class="checklist-check-none">{check_none}</a>
        <input type="search" class="checklist-filter" placeholder="{filter_lbl}">
    </div>
    <div class="checklist-body"><ul class="checklist-content search"></ul></div>
</div>'''.format(
            name=name,
            check_all=_('Check all'),
            check_none=_('Check none'),
            filter_lbl=pgettext('creme_core-noun', 'Search').upper(),
        )
        self.assertHTMLEqual(html, select.render(name, value=None))

    def test_render_search02(self):
        "Fixed behaviour"
        name = 'my_choice_field'
        select = UnorderedMultipleChoiceWidget(
            choices=[(1, 'A'), (2, 'B')], viewless=False, filtertype='search',
        )

        html = '''
<div class="ui-creme-widget widget-auto ui-creme-checklistselect"
     widget="ui-creme-checklistselect" selectall="3">
    <select multiple="multiple" class="ui-creme-input" name="{name}">
        <option value="1">A</option>
        <option value="2">B</option>
    </select>
    <span class="checklist-counter"></span>
    <div class="checklist-header">
        <a type="button" class="checklist-check-all hidden">{check_all}</a>
        <a type="button" class="checklist-check-none hidden">{check_none}</a>
        <input type="search" class="checklist-filter" placeholder="{filter_lbl}">
    </div>
    <div class="checklist-body"><ul class="checklist-content search"></ul></div>
</div>'''.format(
            name=name,
            check_all=_('Check all'),
            check_none=_('Check none'),
            filter_lbl=pgettext('creme_core-noun', 'Search').upper(),
        )
        self.assertHTMLEqual(html, select.render(name, value=None))

    def test_render_filter01(self):
        "Automatic/default behaviour."
        name = 'my_choice_field'
        select = UnorderedMultipleChoiceWidget(
            choices=[(1, 'A'), (2, 'B'), (3, 'C'), (4, 'D')],
            viewless=False,
        )
        self.assertEqual(10, select.MIN_SEARCH_COUNT)
        self.assertEqual(30, select.MIN_FILTER_COUNT)

        select.MIN_SEARCH_COUNT = 2
        select.MIN_FILTER_COUNT = 3

        html = '''
<div class="ui-creme-widget widget-auto ui-creme-checklistselect"
     widget="ui-creme-checklistselect" selectall="3">
    <select multiple="multiple" class="ui-creme-input" name="{name}">
        <option value="1">A</option>
        <option value="2">B</option>
        <option value="3">C</option>
        <option value="4">D</option>
    </select>
    <span class="checklist-counter"></span>
    <div class="checklist-header">
        <a type="button" class="checklist-check-all">{check_all}</a>
        <a type="button" class="checklist-check-none">{check_none}</a>
        <input type="search" class="checklist-filter" placeholder="{filter_lbl}">
    </div>
    <div class="checklist-body"><ul class="checklist-content filter"></ul></div>
</div>'''.format(
            name=name,
            check_all=_('Check all'),
            check_none=_('Check none'),
            filter_lbl=pgettext('creme_core-noun', 'Filter').upper(),
        )
        self.assertHTMLEqual(html, select.render(name, value=None))

    def test_render_filter02(self):
        "Fixed behaviour"
        name = 'my_choice_field'
        select = UnorderedMultipleChoiceWidget(
            choices=[(1, 'A'), (2, 'B')], viewless=False, filtertype='filter',
        )

        html = '''
<div class="ui-creme-widget widget-auto ui-creme-checklistselect"
     widget="ui-creme-checklistselect" selectall="3">
    <select multiple="multiple" class="ui-creme-input" name="{name}">
        <option value="1">A</option>
        <option value="2">B</option>
    </select>
    <span class="checklist-counter"></span>
    <div class="checklist-header">
        <a type="button" class="checklist-check-all hidden">{check_all}</a>
        <a type="button" class="checklist-check-none hidden">{check_none}</a>
        <input type="search" class="checklist-filter" placeholder="{filter_lbl}">
    </div>
    <div class="checklist-body"><ul class="checklist-content filter"></ul></div>
</div>'''.format(
            name=name,
            check_all=_('Check all'),
            check_none=_('Check none'),
            filter_lbl=pgettext('creme_core-noun', 'Filter').upper(),
        )
        self.assertHTMLEqual(html, select.render(name, value=None))

    def test_render_less01(self):
        name = 'my_choice_field'
        select = UnorderedMultipleChoiceWidget(
            choices=[(1, 'A'), (2, 'B'), (3, 'C')], viewless=True,
        )
        self.assertEqual(10, select.MIN_SEARCH_COUNT)
        self.assertEqual(30, select.MIN_FILTER_COUNT)

        html = '''
<div class="ui-creme-widget widget-auto ui-creme-checklistselect"
     widget="ui-creme-checklistselect" less selectall="3">
    <select multiple="multiple" class="ui-creme-input" name="{name}">
        <option value="1">A</option>
        <option value="2">B</option>
        <option value="3">C</option>
    </select>
    <span class="checklist-counter"></span>
    <div class="checklist-header">
        <a type="button" class="checklist-check-all">{check_all}</a>
        <a type="button" class="checklist-check-none">{check_none}</a>
    </div>
    <div class="checklist-body"><ul class="checklist-content"></ul></div>
    <div class="checklist-footer"><a class="checklist-toggle-less">{more_lbl}</a></div>
</div>'''.format(
            name=name,
            check_all=_('Check all'),
            check_none=_('Check none'),
            more_lbl=_('More'),
        )
        self.assertHTMLEqual(html, select.render(name, value=None))

    def test_render_empty(self):
        select = UnorderedMultipleChoiceWidget(creation_url='/add')

        self.assertFalse(select.creation_allowed)
        self.assertHTMLEqual(
            _('No choice available.'),
            select.render('field', [], {'checkall': True}),
        )

    def test_render_empty_with_creation(self):
        name = 'field_1'
        url = '/add/stuff'
        select = UnorderedMultipleChoiceWidget(
            creation_url=url, creation_allowed=True, viewless=False,
        )

        self.assertTrue(select.creation_allowed)
        html = '''
<div class="ui-creme-widget widget-auto ui-creme-checklistselect"
     widget="ui-creme-checklistselect" selectall="3">
    <select multiple="multiple" class="ui-creme-input" name="{name}">
    </select>
    <span class="checklist-counter"></span>
    <div class="checklist-header">
        <a type="button" class="checklist-check-all hidden">{check_all}</a>
        <a type="button" class="checklist-check-none hidden">{check_none}</a>
        <a type="button" class="checklist-create" href="{create_url}">{create_lbl}</a>
    </div>
    <div class="checklist-body"><ul class="checklist-content"></ul></div>
</div>'''.format(
            name=name,
            check_all=_('Check all'),
            check_none=_('Check none'),
            create_url=url,
            create_lbl=_('Create'),
        )

        self.assertHTMLEqual(html, select.render(name, (), attrs={'checkall': True}))

    def test_render_creation_not_allowed(self):
        name = 'field_1'
        select = UnorderedMultipleChoiceWidget(
            choices=[('a', '#1'), ('b', '#2')],
            creation_url='/add', creation_allowed=False,
            viewless=False,
        )

        html = '''
<div class="ui-creme-widget widget-auto ui-creme-checklistselect"
     widget="ui-creme-checklistselect" selectall="3">
    <select multiple="multiple" class="ui-creme-input" name="{name}">
        <option value="a">#1</option>
        <option value="b">#2</option>
    </select>
    <span class="checklist-counter"></span>
    <div class="checklist-header">
        <a type="button" class="checklist-check-all hidden">{check_all}</a>
        <a type="button" class="checklist-check-none hidden">{check_none}</a>
        <a type="button" class="checklist-create is-disabled">{create_lbl}</a>
    </div>
    <div class="checklist-body"><ul class="checklist-content"></ul></div>
</div>'''.format(
            name=name,
            check_all=_('Check all'),
            check_none=_('Check none'),
            create_lbl=_('Create'),
        )
        self.assertHTMLEqual(html, select.render(name, ()))

    def test_render_enhanced_options(self):
        name = 'stuffs'
        Choice = UnorderedMultipleChoiceWidget.Choice
        select = UnorderedMultipleChoiceWidget(
            choices=[
                (Choice(value=1, disabled=True, help='is disabled'), 'Choice #1'),
                (Choice(value=2),                                    'Choice #2'),
                (Choice(value=3, readonly=True, help='is readonly'), 'Choice #3'),
            ],
            viewless=False,
        )

        html = '''
<div class="ui-creme-widget widget-auto ui-creme-checklistselect"
     widget="ui-creme-checklistselect" selectall="3">
    <select multiple="multiple" class="ui-creme-input" name="{name}">
        <option value="1" disabled help="is disabled">Choice #1</option>
        <option value="2" help="">Choice #2</option>
        <option value="3" readonly help="is readonly">Choice #3</option>
    </select>
    <span class="checklist-counter"></span>
    <div class="checklist-header">
        <a type="button" class="checklist-check-all">{check_all}</a>
        <a type="button" class="checklist-check-none">{check_none}</a>
    </div>
    <div class="checklist-body"><ul class="checklist-content"></ul></div>
</div>'''.format(
            name=name,
            check_all=_('Check all'),
            check_none=_('Check none'),
        )
        self.assertHTMLEqual(html, select.render(name, ()))


class WidgetActionTestCase(CremeTestCase):
    def test_init01(self):
        name = 'add'
        label = 'Create a stuff'
        action = WidgetAction(name=name, label=label)
        self.assertEqual(name,  action.name)
        self.assertEqual(label, action.label)
        self.assertIsNone(action.icon)
        self.assertIs(action.enabled, True)
        self.assertDictEqual({}, action.attrs)

        self.assertDictEqual(
            {
                'name': name,
                'label': label,
                'icon': None,
                'attrs': {},
                'title': label,
            },
            action.context,
        )

    def test_init02(self):
        name = 'reset'
        label = 'Delete'
        icon = 'delete'
        url = 'https://www.stuff.org'
        action = WidgetAction(name=name, label=label, icon=icon, enabled=False, url=url)
        self.assertEqual(name,  action.name)
        self.assertEqual(label, action.label)
        self.assertEqual(icon,  action.icon)
        self.assertIs(action.enabled, False)
        self.assertDictEqual({'url': url}, action.attrs)

        self.assertDictEqual(
            {
                'name': name,
                'label': label,
                'icon': icon,
                'attrs': {
                    'disabled': True,
                    'url': url,
                },
                'title': label,
            },
            action.context,
        )

    def test_callable_enabled(self):
        action = WidgetAction(name='name', label='label', enabled=lambda: False)
        self.assertIs(action.enabled, False)

    def test_context_title(self):
        name = 'reset'
        label = 'Delete'
        title = 'Delete stuff'
        icon = 'delete'
        url = 'https://www.stuff.org'
        action = WidgetAction(name=name, label=label, icon=icon, url=url, title=title)

        self.assertDictEqual(
            {
                'name': name,
                'label': label,
                'icon': icon,
                'attrs': {
                    'url': url,
                },
                'title': title,
            },
            action.context,
        )

    def test_eq(self):
        self.assertEqual(
            WidgetAction(name='name', label='label', enabled=True),
            WidgetAction(name='name', label='label'),
        )

        url = 'https://www.stuff.org'
        self.assertEqual(
            WidgetAction(name='add', label='Create', url=url, enabled=False),
            WidgetAction(name='add', label='Create', url=url, enabled=False),
        )

        self.assertNotEqual(
            WidgetAction(name='add',    label='Add'),
            WidgetAction(name='delete', label='Add'),
        )
        self.assertNotEqual(
            WidgetAction(name='add', label='Add'),
            WidgetAction(name='add', label='Create'),
        )
        self.assertNotEqual(
            WidgetAction(name='add', label='Add', enabled=True),
            WidgetAction(name='add', label='Add', enabled=False),
        )
        self.assertNotEqual(
            WidgetAction(name='add', label='Add', icon='add'),
            WidgetAction(name='add', label='Add'),
        )
        self.assertNotEqual(
            WidgetAction(name='add', label='Add', url=url),
            WidgetAction(name='add', label='Add'),
        )


class ActionButtonListTestCase(CremeTestCase):
    def setUp(self):
        super().setUp()
        self.maxDiff = None

    def test_render_empty_action_list(self):
        widget = ActionButtonList(Select(choices=[(1, 'A'), (2, 'B')]))

        html = '''
<ul class="ui-layout hbox ui-creme-widget widget-auto ui-creme-actionbuttonlist"
    widget="ui-creme-actionbuttonlist">
    <li class="delegate">
        <select name="field">
            <option value="1">A</option>
            <option value="2" selected>B</option>
        </select>
    </li>
</ul>'''
        self.assertHTMLEqual(html, widget.render('field', 2))

    def test_render_action_list(self):
        widget = ActionButtonList(Select(choices=[(1, 'A'), (2, 'B')]))
        widget.add_action('action_a', 'Action A', title='Do the action A')
        widget.add_action('action_b', 'Action B', False)

        html = '''
<ul class="ui-layout hbox ui-creme-widget widget-auto ui-creme-actionbuttonlist"
    widget="ui-creme-actionbuttonlist">
    <li class="delegate">
        <select name="field">
            <option value="1" selected>A</option>
            <option value="2">B</option>
        </select>
    </li>
    <li>
        <button class="ui-creme-actionbutton" name="action_a"
                title="Do the action A" type="button"><span>Action A</span></button>
    </li>
    <li>
        <button class="ui-creme-actionbutton" name="action_b" title="Action B"
                type="button" disabled><span>Action B</span></button>
    </li>
</ul>'''
        self.assertHTMLEqual(html, widget.render('field', 1))


class EntitySelectorTestCase(CremeTestCase):
    def setUp(self):
        super().setUp()
        self.maxDiff = None

    def test_listview_url(self):
        widget = EntitySelector()
        self.assertEqual(
            reverse('creme_core__listview_popup')
            + '?ct_id=${ctype}&selection=${selection}&q_filter=${qfilter}',
            widget.url,
        )

        widget = EntitySelector(content_type=12)
        self.assertEqual(
            reverse('creme_core__listview_popup')
            + '?ct_id=12&selection=${selection}&q_filter=${qfilter}',
            widget.url,
        )

    def test_text_url(self):
        widget = EntitySelector(content_type=12)

        self.assertEqual(
            TemplateURLBuilder(
                entity_id=(TemplateURLBuilder.Int, '${id}'),
            ).resolve('creme_core__entity_as_json'),
            widget.text_url,
        )

    def test_render(self):
        text_url = TemplateURLBuilder(
            entity_id=(TemplateURLBuilder.Int, '${id}'),
        ).resolve('creme_core__entity_as_json')

        widget = EntitySelector(content_type=12)
        name = 'field-1'
        value = '1'
        html = '''
<span class="ui-creme-widget widget-auto ui-creme-entityselector"
      widget="ui-creme-entityselector" labelURL="{text_url}" label="{label}"
      popupURL="{url}" popupSelection="single">
    <input name="{name}" type="text" value="{value}"
           class="ui-creme-input ui-creme-entityselector" />
    <button type="button">{label}</button>
</span>'''.format(
            name=name,
            value=value,
            label=_('Select…'),
            text_url=text_url,
            url=(
                reverse('creme_core__listview_popup')
                + '?ct_id=12&selection=${selection}&q_filter=${qfilter}'
            ),
        )
        self.assertHTMLEqual(html, widget.render(name, value))

    def assertDOMEqual(self, dom1, dom2, msg=None):
        if dom1 != dom2:
            standard_msg = '{} != {}'.format(
                safe_repr(dom1, True),
                safe_repr(dom2, True),
            )
            diff = ('\n' + '\n'.join(difflib.ndiff(
                str(dom1).splitlines(),
                str(dom2).splitlines(),
            )))

            self.fail(self._formatMessage(msg, self._truncateMessage(standard_msg, diff)))

    def assertQFilter(self, dom, expected_qfilter):
        for attr_name, attr_value in dom.attributes:
            if attr_name == 'qfilter':
                qfilter_attr = attr_value
                break
        else:
            self.fail('No "qfilter" attribute found !')

        self.assertEqual(expected_qfilter, json_load(qfilter_attr))

        return qfilter_attr

    def test_render_qfilter01(self):
        "Dictionary instance."
        widget = EntitySelector(content_type=12)
        name = 'field'
        value = '1'
        render_dom = assert_and_parse_html(
            self,
            widget.render('field', '1', attrs={'qfilter': {'pk__in': [12, 13]}}),
            user_msg=None,
            msg='Widget render is not valid !',
        )
        qfilter_attr = self.assertQFilter(
            render_dom,
            {'val': [['pk__in', [12, 13]]], 'op': 'AND'},
        )

        html = '''
<span class="ui-creme-widget widget-auto ui-creme-entityselector"
      widget="ui-creme-entityselector" labelURL="{text_url}" label="{label}"
      popupURL="{url}" popupSelection="single" qfilter="{q_filter}">
    <input name="{name}" type="text" value="{value}"
          class="ui-creme-input ui-creme-entityselector"/>
    <button type="button">{label}</button>
</span>'''.format(
            name=name,
            value=value,
            label=_('Select…'),
            text_url=TemplateURLBuilder(
                entity_id=(TemplateURLBuilder.Int, '${id}'),
            ).resolve('creme_core__entity_as_json'),
            url=(
                reverse('creme_core__listview_popup')
                + '?ct_id=12&selection=${selection}&q_filter=${qfilter}'
            ),
            q_filter=escape(qfilter_attr),
        )
        self.assertDOMEqual(
            assert_and_parse_html(self, html, None, 'Expected HTML is not valid !'),
            render_dom,
        )

    def test_render_qfilter02(self):
        "Q instance."
        widget = EntitySelector(content_type=13)
        name = 'my_field'
        value = '2'
        render_dom = assert_and_parse_html(
            self,
            widget.render(name, value, attrs={'qfilter': Q(name='foobar')}),
            user_msg=None,
            msg='Widget render is not valid !',
        )
        qfilter_attr = self.assertQFilter(render_dom, {'val': [['name', 'foobar']], 'op': 'AND'})
        html = '''
<span class="ui-creme-widget widget-auto ui-creme-entityselector"
      widget="ui-creme-entityselector" labelURL="{text_url}" label="{label}"
      popupURL="{url}" popupSelection="single" qfilter="{q_filter}">
    <input name="{name}" type="text" value="{value}"
           class="ui-creme-input ui-creme-entityselector"/>
    <button type="button">{label}</button>
</span>'''.format(
            name=name,
            value=value,
            label=_('Select…'),
            text_url=TemplateURLBuilder(
                entity_id=(TemplateURLBuilder.Int, '${id}'),
            ).resolve('creme_core__entity_as_json'),
            url=(
                reverse('creme_core__listview_popup')
                + '?ct_id=13&selection=${selection}&q_filter=${qfilter}'
            ),
            q_filter=escape(qfilter_attr),
        )
        self.assertDOMEqual(
            assert_and_parse_html(self, html, None, 'Expected HTML is not valid !'),
            render_dom,
        )

    def test_render_popup_options(self):
        widget = EntitySelector(content_type=12)
        html = '''
<span class="ui-creme-widget widget-auto ui-creme-entityselector" widget="ui-creme-entityselector"
          labelURL="{text_url}" label="{label}"
          popupURL="{url}" popupSelection="multiple" popupAuto>
    <input name="field" type="text" class="ui-creme-input ui-creme-entityselector" value="1"/>
    <button type="button">{label}</button>
</span>'''.format(
            label=_('Select…'),
            text_url=TemplateURLBuilder(
                entity_id=(TemplateURLBuilder.Int, '${id}'),
            ).resolve('creme_core__entity_as_json'),
            url=(
                reverse('creme_core__listview_popup')
                + '?ct_id=12&selection=${selection}&q_filter=${qfilter}'
            ),
        )
        self.assertHTMLEqual(
            html,
            widget.render('field', '1', attrs={'multiple': True, 'autoselect': True})
        )

    def test_render_is_required(self):
        widget = EntitySelector(content_type=12)
        widget.is_required = True

        html = '''
<span class="ui-creme-widget widget-auto ui-creme-entityselector" widget="ui-creme-entityselector"
          labelURL="{text_url}" label="{label}"
          popupURL="{url}" popupSelection="multiple" popupAuto>
    <input name="field" type="text" value="1"
           class="ui-creme-input ui-creme-entityselector" required />
    <button type="button">{label}</button>
</span>'''.format(
            label=_('Select…'),
            text_url=TemplateURLBuilder(
                entity_id=(TemplateURLBuilder.Int, '${id}'),
            ).resolve('creme_core__entity_as_json'),
            url=(
                reverse('creme_core__listview_popup')
                + '?ct_id=12&selection=${selection}&q_filter=${qfilter}'
            ),
        )
        self.assertHTMLEqual(
            html,
            widget.render('field', '1', attrs={'multiple': True, 'autoselect': True})
        )


class EntityCreatorWidgetTestCase(CremeTestCase):
    maxDiff = None

    @staticmethod
    def _build_reset_action(enabled=True, value=''):
        return WidgetAction(
            name='reset',
            label=_('Clear'),
            enabled=enabled,
            icon='delete',

            action='reset',
            title=_('Clear'),
            value=value,
        )

    @staticmethod
    def _build_create_action(label, title, url='', enabled=True):
        return WidgetAction(
            name='create',
            label=label,
            enabled=enabled,
            icon='add',

            title=title,
            popupUrl=url,
        )

    def test_is_disabled(self):
        widget = EntityCreatorWidget(FakeContact)
        self.assertFalse(widget._is_disabled({}))
        self.assertFalse(widget._is_disabled(None))
        self.assertTrue(widget._is_disabled({'readonly': True}))
        self.assertTrue(widget._is_disabled({'disabled': True}))

    def test_actions(self):
        creation_url = reverse(
            'creme_core__quick_form',
            args=(ContentType.objects.get_for_model(FakeContact).id,),
        )
        widget = EntityCreatorWidget(
            model=FakeContact, creation_url=creation_url, creation_allowed=True,
        )
        widget._build_actions(FakeContact, {})

        self.assertListEqual(
            [
                self._build_reset_action(),
                self._build_create_action(FakeContact.creation_label, _('Create'), creation_url),
            ],
            widget.actions,
        )

    def test_actions_creation_url_empty(self):
        widget = EntityCreatorWidget(FakeContact, creation_url='', creation_allowed=True)
        widget._build_actions(FakeContact, {})

        self.assertListEqual([self._build_reset_action()], widget.actions)

    def test_actions_creation_not_allowed(self):
        creation_url = reverse(
            'creme_core__quick_form',
            args=(ContentType.objects.get_for_model(FakeContact).id,),
        )
        widget = EntityCreatorWidget(
            FakeContact, creation_url=creation_url, creation_allowed=False,
        )
        widget._build_actions(FakeContact, {})

        self.assertListEqual(
            [
                self._build_reset_action(),
                self._build_create_action(
                    FakeContact.creation_label, _("Can't create"), creation_url,
                    enabled=False,
                ),
            ],
            widget.actions,
        )

    def test_actions_required(self):
        creation_url = reverse(
            'creme_core__quick_form',
            args=(ContentType.objects.get_for_model(FakeContact).id,),
        )
        widget = EntityCreatorWidget(
            FakeContact, creation_url=creation_url, creation_allowed=True,
        )
        widget.is_required = True
        widget._build_actions(FakeContact, {})

        self.assertListEqual(
            [self._build_create_action(FakeContact.creation_label, _('Create'), creation_url)],
            widget.actions,
        )

    def test_actions_disabled(self):
        creation_url = reverse(
            'creme_core__quick_form',
            args=(ContentType.objects.get_for_model(FakeContact).id,),
        )
        widget = EntityCreatorWidget(FakeContact, creation_url=creation_url, creation_allowed=True)
        widget._build_actions(FakeContact, {})

        self.assertListEqual(
            [
                self._build_reset_action(),
                self._build_create_action(FakeContact.creation_label, _('Create'), creation_url),
            ],
            widget.actions,
        )

        widget._build_actions(FakeContact, {'readonly': True})
        self.assertListEqual([], widget.actions)

        widget._build_actions(FakeContact, {'disabled': True})
        self.assertListEqual([], widget.actions)

    def test_render_no_model(self):
        widget = EntityCreatorWidget()
        html = '''
<ul class="hbox ui-creme-widget ui-layout widget-auto ui-creme-actionbuttonlist"
    widget="ui-creme-actionbuttonlist">
    <li class="delegate">
        <input name="field" style="display:none;" type="text" />
        <span>Model is not set</span>
    </li>
</ul>'''
        self.assertHTMLEqual(html, widget.render('field', ''))

    def test_render_empty_value(self):
        "Empty."
        ct_id = ContentType.objects.get_for_model(FakeContact).id
        creation_url = reverse('creme_core__quick_form', args=(ct_id,))
        widget = EntityCreatorWidget(
            FakeContact, creation_url=creation_url, creation_allowed=False,
        )
        self.assertIsNone(widget.creation_label)

        reset_label = _('Clear')
        create_label = FakeContact.creation_label
        html = '''
<ul class="hbox ui-creme-widget ui-layout widget-auto ui-creme-actionbuttonlist"
    widget="ui-creme-actionbuttonlist">
    <li class="delegate">
        <span class="ui-creme-widget ui-creme-entityselector" widget="ui-creme-entityselector"
              labelURL="{select_label_url}" label="{select_label}"
              popupURL="{select_url}" popupSelection="single">
            <input name="field" type="text" class="ui-creme-input ui-creme-entityselector"/>
            <button type="button">{select_label}</button>
        </span>
    </li>
    <li>
        <button class="ui-creme-actionbutton with-icon" action="reset" name="reset"
                title="{reset_label}" type="button" value="">
            {reset_icon}<span>{reset_label}</span>
        </button>
    </li>
    <li>
        <button class="ui-creme-actionbutton with-icon" name="create"
                title="{create_title}" type="button" disabled popupUrl="{create_url}">
            {create_icon}<span>{create_label}</span>
        </button>
    </li>
</ul>'''.format(
            select_label=_('Select…'),
            select_label_url=EntitySelector(content_type=ct_id).text_url,
            select_url=EntitySelector(content_type=ct_id).url,

            reset_label=reset_label,
            reset_icon=self.get_icon('delete', size='form-widget', label=reset_label).render(),

            create_title=_("Can't create"),
            create_label=create_label,
            create_url=creation_url,
            create_icon=self.get_icon('add', size='form-widget', label=create_label).render(),
        )
        self.assertHTMLEqual(html, widget.render('field', ''))

    def test_render_initial(self):
        "Initialized, creation_label."
        user = self.get_root_user()
        contact = FakeContact.objects.create(last_name='Doe', first_name='John', user=user)
        ct_id = contact.entity_type_id

        creation_url = reverse('creme_core__quick_form', args=(ct_id,))
        creation_label = 'Create a agent'
        widget = EntityCreatorWidget(
            FakeContact,
            creation_url=creation_url,
            creation_allowed=False,
            creation_label=creation_label,
        )
        self.assertEqual(creation_label, widget.creation_label)

        widget.from_python = lambda value: value.id
        reset_label = _('Clear')
        html = '''
<ul class="hbox ui-creme-widget ui-layout widget-auto ui-creme-actionbuttonlist"
    widget="ui-creme-actionbuttonlist">
    <li class="delegate">
        <span class="ui-creme-widget ui-creme-entityselector" widget="ui-creme-entityselector"
              labelURL="{select_label_url}" label="{select_label}"
              popupURL="{select_url}" popupSelection="single">
            <input name="field" type="text" value="{value}"
                   class="ui-creme-input ui-creme-entityselector"/>
            <button type="button">{select_label}</button>
        </span>
    </li>
    <li>
        <button class="ui-creme-actionbutton with-icon" action="reset" name="reset"
                title="{reset_label}" type="button" value="">
            {reset_icon}<span>{reset_label}</span>
        </button>
    </li>
    <li>
        <button class="ui-creme-actionbutton with-icon" name="create"
                title="{create_title}" type="button" disabled popupUrl="{create_url}">
            {create_icon}<span>{create_label}</span>
        </button>
    </li>
</ul>'''.format(
            select_label=_('Select…'),
            select_label_url=EntitySelector(content_type=ct_id).text_url,
            select_url=EntitySelector(content_type=ct_id).url,

            reset_label=reset_label,
            reset_icon=self.get_icon('delete', size='form-widget', label=reset_label).render(),

            create_title=_("Can't create"),
            create_label=creation_label,
            create_url=creation_url,
            create_icon=self.get_icon('add', size='form-widget', label=creation_label).render(),

            value=contact.id,
        )
        self.assertHTMLEqual(html, widget.render('field', value=contact))


class CremeTextareaTestCase(CremeTestCase):
    def test_render01(self):
        widget = CremeTextarea()
        self.assertHTMLEqual(
            '''
<textarea cols="40" rows="3" name="field"
          class="ui-creme-autosizedarea ui-creme-widget widget-auto"
          widget="ui-creme-autosizedarea">''',
            widget.render('field', value=''),
        )

    def test_render02(self):
        "row & cols."
        widget = CremeTextarea(attrs={'rows': 4, 'cols': 80})
        self.assertHTMLEqual(
            '''
<textarea cols="80" rows="4" name="my_field"
          class="ui-creme-autosizedarea ui-creme-widget widget-auto"
          widget="ui-creme-autosizedarea">''',
            widget.render('my_field', value=''),
        )

    def test_render03(self):
        "Extra class."
        widget = CremeTextarea(attrs={'class': 'my_extra_class'})
        self.assertHTMLEqual(
            '''
<textarea cols="40" rows="3" name="field"
          class="my_extra_class ui-creme-autosizedarea ui-creme-widget widget-auto"
          widget="ui-creme-autosizedarea">''',
            widget.render('field', value=''),
        )


class DurationWidgetTestCase(CremeTestCase):
    @override_language('fr')
    def test_render_fr(self):
        name = 'my_duration'
        self.assertHTMLEqual(
            f'<span>'
            f' <input min="0" name="{name}_0" type="number">Heure(s)'
            f' <input min="0" name="{name}_1" type="number">Minute(s)'
            f' <input min="0" name="{name}_2" type="number">Seconde(s)'
            f'</span>',
            DurationWidget().render(name=name, value=''),
        )

    @override_language('en')
    def test_render_en_string_value(self):
        name = 'duration'
        self.assertHTMLEqual(
            f'<span>'
            f' <input min="0" name="{name}_0" type="number" value="0">Hour(s)'
            f' <input min="0" name="{name}_1" type="number" value="15">Minute(s)'
            f' <input min="0" name="{name}_2" type="number" value="00">Second(s)'
            f'</span>',
            DurationWidget().render(name=name, value='0:15:00'),
        )
