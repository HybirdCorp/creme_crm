from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.models import (
    FakeContact,
    FieldsConfig,
    InstanceBrickConfigItem,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_constants import (
    FAKE_REL_SUB_BILL_ISSUED,
    FAKE_REL_SUB_EMPLOYED_BY,
)
from creme.reports.bricks import ReportChartInstanceBrick
from creme.reports.core.chart.fetcher import (
    RegularFieldLinkedChartFetcher,
    RelationLinkedChartFetcher,
    SimpleChartFetcher,
)
from creme.reports.forms.bricks import (
    ChartFetcherField,
    ChartInstanceBrickForm,
    FetcherChoiceIterator,
)
from creme.reports.models import ReportChart
from creme.reports.tests.base import BaseReportsTestCase, Report


class ChartFetcherFieldTestCase(CremeTestCase):
    def _build_chart(self):
        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)

        return ReportChart(name='Field Test', linked_report=report)

    def test_clean__empty__not_required(self):
        with self.assertNoException():
            cleaned = ChartFetcherField(required=False).clean(None)

        self.assertIsNone(cleaned)

    def test_clean__empty__required(self):
        field = ChartFetcherField()
        self.assertTrue(field.required)
        self.assertFormfieldError(
            field=field, value=None,
            codes='required', messages=_('This field is required.'),
        )

    def test_chart_n_iterator(self):
        chart = self._build_chart()

        field = ChartFetcherField()
        self.assertIsNone(field.chart)
        self.assertEqual('|', field.choice_separator)

        choices_it1 = field.widget.choices
        self.assertIsInstance(choices_it1, FetcherChoiceIterator)
        self.assertIsNone(choices_it1.chart)
        self.assertEqual('|', choices_it1.separator)
        self.assertFalse([*choices_it1])

        # ---
        field.chart = chart
        self.assertEqual(chart, field.chart)

        choices_it2 = field.widget.choices
        self.assertEqual(chart, choices_it2.chart)

        choices = [*choices_it2]
        self.assertInChoices(
            # value=f'{constants.RGF_NOLINK}|',
            value=f'{SimpleChartFetcher.type_id}|',
            label=pgettext('reports-volatile_choice', 'None'),
            choices=choices,
        )

        fields_group = self.get_choices_group_or_fail(_('Fields'), choices)
        self.assertInChoices(
            # value=f'{constants.RGF_FK}|image',
            value=f'{RegularFieldLinkedChartFetcher.type_id}|image',
            label=_('Photograph'),
            choices=fields_group,
        )
        # self.assertNotInChoices(f'{constants.RGF_FK}|is_user', fields_group)
        self.assertNotInChoices(
            f'{RegularFieldLinkedChartFetcher.type_id}|is_user', fields_group,
        )

        relations_group = self.get_choices_group_or_fail(_('Relationships'), choices)
        self.assertInChoices(
            # value=f'{constants.RGF_RELATION}|{FAKE_REL_SUB_EMPLOYED_BY}',
            value=f'{RelationLinkedChartFetcher.type_id}|{FAKE_REL_SUB_EMPLOYED_BY}',
            label='is an employee of — employs',
            choices=relations_group,
        )
        self.assertNotInChoices(
            # f'{constants.RGF_RELATION}|{FAKE_REL_SUB_BILL_ISSUED}',
            f'{RelationLinkedChartFetcher.type_id}|{FAKE_REL_SUB_BILL_ISSUED}',
            relations_group,
        )

    def test_chart_n_iterator__hidden_field(self):
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('image', {FieldsConfig.HIDDEN: True})],
        )

        chart = self._build_chart()

        field = ChartFetcherField(chart=chart)
        choices = [*field.widget.choices]
        self.get_choices_group_or_fail(_('Relationships'), choices)

        empty_group_name = _('Fields')
        for choice in choices:
            if choice[0] == empty_group_name:
                self.fail(f'Group "{empty_group_name}" unexpectedly found.')  # pragma: no cover

    def test_clean__ok(self):
        chart = self._build_chart()

        field = ChartFetcherField(chart=chart)
        self.assertEqual(chart, field.chart)

        # No Link ---
        # fetcher1a = field.clean(value=constants.RGF_NOLINK)
        fetcher1a = field.clean(value=SimpleChartFetcher.type_id)
        self.assertIsInstance(fetcher1a, SimpleChartFetcher)
        self.assertIsNone(fetcher1a.error)

        # fetcher1b = field.clean(value=f'{constants.RGF_NOLINK}|')
        fetcher1b = field.clean(value=f'{SimpleChartFetcher.type_id}|')
        self.assertIsInstance(fetcher1b, SimpleChartFetcher)
        self.assertIsNone(fetcher1b.error)

        # FK link ---
        # fetcher2 = field.clean(value=f'{constants.RGF_FK}|image')
        fetcher2 = field.clean(value=f'{RegularFieldLinkedChartFetcher.type_id}|image')
        self.assertIsInstance(fetcher2, RegularFieldLinkedChartFetcher)
        self.assertIsNone(fetcher2.error)
        rfield = fetcher2._field
        self.assertEqual('image',     rfield.name)
        self.assertEqual(FakeContact, rfield.model)

        # Relation link ---
        fetcher3 = field.clean(
            # value=f'{constants.RGF_RELATION}|{FAKE_REL_SUB_EMPLOYED_BY}',
            value=f'{RelationLinkedChartFetcher.type_id}|{FAKE_REL_SUB_EMPLOYED_BY}',
        )
        self.assertIsInstance(fetcher3, RelationLinkedChartFetcher)
        self.assertIsNone(fetcher3.error)
        self.assertEqual(FAKE_REL_SUB_EMPLOYED_BY, fetcher3._rtype.id)

    def test_clean__error__no_link(self):
        chart = self._build_chart()
        field = ChartFetcherField(chart=chart)
        # value = f'{constants.RGF_NOLINK}|whatever'
        value = f'{SimpleChartFetcher.type_id}|whatever'
        self.assertFormfieldError(
            field=field, value=value, codes='invalid_choice',
            messages=_(
                'Select a valid choice. %(value)s is not one of the available choices.'
            ) % {'value': value},
        )

    def test_clean__error__fk(self):
        hidden_fname = 'image'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        chart = self._build_chart()
        field = ChartFetcherField(chart=chart)

        # Empty field
        code = 'invalid_choice'
        msg = _(
            'Select a valid choice. %(value)s is not one of the available choices.'
        )
        # value1 = constants.RGF_FK
        value1 = RegularFieldLinkedChartFetcher.type_id
        self.assertFormfieldError(
            field=field, value=value1,
            messages=msg % {'value': value1},
            codes=code,
        )

        # Unknown field
        # value2 = f'{constants.RGF_FK}|invalid'
        value2 = f'{RegularFieldLinkedChartFetcher.type_id}|invalid'
        self.assertFormfieldError(
            field=field, value=value2,
            messages=msg % {'value': value2},
            codes=code,
        )

        # Invalid field (not FK)
        # value3 = f'{constants.RGF_FK}|last_name'
        value3 = f'{RegularFieldLinkedChartFetcher.type_id}|last_name'
        self.assertFormfieldError(
            field=field, value=value3,
            messages=msg % {'value': value3},
            codes=code,
        )

        # Invalid field (not FK to CremeEntity)
        # value4 = f'{constants.RGF_FK}|sector'
        value4 = f'{RegularFieldLinkedChartFetcher.type_id}|sector'
        self.assertFormfieldError(
            field=field, value=value4,
            messages=msg % {'value': value4}, codes=code,
        )

        # Hidden field
        # value5 = f'{constants.RGF_FK}|{hidden_fname}'
        value5 = f'{RegularFieldLinkedChartFetcher.type_id}|{hidden_fname}'
        self.assertFormfieldError(
            field=field, value=value5,
            messages=msg % {'value': value5}, codes=code,
        )

    def test_clean__error__relation(self):
        chart = self._build_chart()
        # value = f'{constants.RGF_RELATION}|{FAKE_REL_SUB_BILL_ISSUED}'
        value = f'{RelationLinkedChartFetcher.type_id}|{FAKE_REL_SUB_BILL_ISSUED}'
        self.assertFormfieldError(
            field=ChartFetcherField(chart=chart),
            value=value,
            codes='invalid_choice',
            messages=_(
                'Select a valid choice. %(value)s is not one of the available choices.'
            ) % {'value': value},
        )

    def test_separator__chart_property(self):
        field = ChartFetcherField(choice_separator='#')
        self.assertEqual('#', field.choice_separator)

        self.assertEqual('#', field.widget.choices.separator)

        # ---
        field.chart = self._build_chart()
        choices_it = field.widget.choices
        self.assertEqual('#', choices_it.separator)

        fields_group = self.get_choices_group_or_fail(_('Fields'), [*choices_it])
        # value = f'{constants.RGF_FK}#image'
        value = f'{RegularFieldLinkedChartFetcher.type_id}#image'
        self.assertInChoices(
            value=value,
            label=_('Photograph'),
            choices=fields_group,
        )

        fetcher = field.clean(value=value)
        self.assertIsInstance(fetcher, RegularFieldLinkedChartFetcher)
        self.assertIsNone(fetcher.error)

        rfield = fetcher._field
        self.assertEqual('image',     rfield.name)
        self.assertEqual(FakeContact, rfield.model)

    def test_separator__separator_property(self):
        "Set chart then separator."
        field = ChartFetcherField(chart=self._build_chart())
        field.choice_separator = '#'
        self.assertEqual('#', field.choice_separator)
        self.assertEqual('#', field.widget.choices.separator)


class ChartInstanceBrickFormTestCase(BaseReportsTestCase):
    def test_init_n_clean(self):
        user = self.get_root_user()
        chart = self._create_documents_chart(user)

        form1 = ChartInstanceBrickForm(user=user, chart=chart)

        fetcher_f = form1.fields.get('fetcher')
        self.assertIsInstance(fetcher_f, ChartFetcherField)
        self.assertEqual(chart, fetcher_f.chart)

        fk_name = 'linked_folder'
        form2 = ChartInstanceBrickForm(
            user=user, chart=chart,
            # data={'fetcher': f'{constants.RGF_FK}|{fk_name}'},
            data={'fetcher': f'{RegularFieldLinkedChartFetcher.type_id}|{fk_name}'},
        )
        self.assertTrue(form2.is_valid())

        ibci = form2.save()
        self.assertIsInstance(ibci, InstanceBrickConfigItem)
        self.assertEqual(chart.linked_report_id, ibci.entity_id)
        # self.assertEqual(constants.RGF_FK, ibci.get_extra_data('type'))
        self.assertEqual(RegularFieldLinkedChartFetcher.type_id, ibci.get_extra_data('type'))
        self.assertEqual(fk_name, ibci.get_extra_data('value'))
        self.assertUUIDEqual(chart.uuid, ibci.get_extra_data('chart'))

    def test_uniqueness(self):
        user = self.get_root_user()
        chart = self._create_documents_chart(user)

        fk_name = 'linked_folder'
        RegularFieldLinkedChartFetcher(
            chart=chart, value=fk_name,
        ).create_brick_config_item(
            brick_class=ReportChartInstanceBrick,
        )

        form1 = ChartInstanceBrickForm(
            user=user, chart=chart,
            # data={'fetcher': f'{constants.RGF_FK}|{fk_name}'},
            data={'fetcher': f'{RegularFieldLinkedChartFetcher.type_id}|{fk_name}'},
        )
        self.assertFormInstanceErrors(
            form1,
            (
                'fetcher',
                _(
                    'The instance block for «{chart}» with these parameters'
                    ' already exists!'
                ).format(chart=chart),
            ),
        )

        form2 = ChartInstanceBrickForm(
            # user=user, chart=chart, data={'fetcher': constants.RGF_NOLINK},
            user=user, chart=chart, data={'fetcher': SimpleChartFetcher.type_id},
        )
        self.assertTrue(form2.is_valid())

    def test_uniqueness__not_same_chart(self):
        user = self.get_root_user()
        chart1 = self._create_documents_chart(user)
        chart2 = self._create_documents_chart(user)

        fk_name = 'linked_folder'
        RegularFieldLinkedChartFetcher(
            chart=chart2,  # Not same chart => collision
            value=fk_name,
        ).create_brick_config_item(
            brick_class=ReportChartInstanceBrick
        )

        form = ChartInstanceBrickForm(
            user=user, chart=chart1,
            # data={'fetcher': f'{constants.RGF_FK}|{fk_name}'},
            data={'fetcher': f'{RegularFieldLinkedChartFetcher.type_id}|{fk_name}'},
        )
        self.assertTrue(form.is_valid())

    def test_uniqueness__not_same_brick_class(self):
        user = self.get_root_user()
        chart = self._create_documents_chart(user)

        class OtherReportChartBrick(ReportChartInstanceBrick):
            id = ReportChartInstanceBrick.generate_id('reports', 'other_chart')

        fk_name = 'linked_folder'
        RegularFieldLinkedChartFetcher(
            chart=chart, value=fk_name,
        ).create_brick_config_item(
            brick_class=OtherReportChartBrick,
        )

        form = ChartInstanceBrickForm(
            user=user, chart=chart,
            # data={'fetcher': f'{constants.RGF_FK}|{fk_name}'},
            data={'fetcher': f'{RegularFieldLinkedChartFetcher.type_id}|{fk_name}'},
        )
        self.assertTrue(form.is_valid())
