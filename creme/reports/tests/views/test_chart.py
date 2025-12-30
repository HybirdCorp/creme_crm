from django.db.models.query_utils import Q
from django.urls import reverse
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.models import (
    CustomField,
    EntityFilter,
    FakeContact,
    FakeEmailCampaign,
    FakeInvoice,
    FakeOrganisation,
    FakeSector,
    FieldsConfig,
    RelationType,
)
from creme.creme_core.tests import fake_constants
from creme.creme_core.tests.fake_models import FakeOpportunity
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.reports.bricks import InstanceBricksInfoBrick, ReportChartBrick
from creme.reports.core.chart import AbscissaInfo
from creme.reports.core.chart.fetcher import (
    RegularFieldLinkedChartFetcher,
    SimpleChartFetcher,
)
from creme.reports.core.chart.lv_url import ListViewURLBuilder
from creme.reports.core.chart.plot import Pie, plot_registry
from creme.reports.models import ReportChart
from creme.reports.views import chart as chart_views

from ..base import (
    AxisFieldsMixin,
    BaseReportsTestCase,
    Report,
    skipIfCustomReport,
)


@skipIfCustomReport
class ReportChartViewsTestCase(BrickTestCaseMixin,
                               AxisFieldsMixin,
                               BaseReportsTestCase):
    @staticmethod
    def _build_edit_url(chart):
        return reverse('reports__edit_chart', args=(chart.id,))

    def test_listview_URL_builder(self):
        self.login_as_root()

        builder = ListViewURLBuilder(FakeContact)
        self.assertListviewURL(builder(None), FakeContact)
        self.assertListviewURL(builder({'id': 1}), FakeContact, expected_q=Q(id=1))

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Names', FakeContact,
            is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IENDSWITH,
                    field_name='last_name', values=['Stark'],
                ),
            ],
        )

        builder = ListViewURLBuilder(FakeContact, efilter)
        self.assertListviewURL(builder(None), FakeContact, expected_efilter_id='test-filter')
        self.assertListviewURL(
            builder({'id': 1}), FakeContact,
            expected_q=Q(id=1), expected_efilter_id='test-filter',
        )

    def test_listview_URL_builder__no_listview(self):
        "Model without list-view."
        with self.assertNoException():
            builder = ListViewURLBuilder(FakeSector)

        self.assertIsNone(builder(None))
        self.assertIsNone(builder({'id': '1'}))

    def test_listview_URL_builder__common_q(self):
        self.login_as_root()

        q = Q(first_name__endswith='a')
        builder = ListViewURLBuilder(FakeContact, common_q=q)
        self.assertListviewURL(builder(None), FakeContact, expected_q=q)
        self.assertListviewURL(builder({'id': 1}), FakeContact, expected_q=q & Q(id=1))

    def test_detailview(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            linked_report=report,
            name='Capital per month of creation',
            abscissa_cell_value='created',
            abscissa_type=ReportChart.Group.MONTH,
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_cell_key='regular_field-capital',
        )

        response = self.assertGET200(chart.get_absolute_url())
        # self.assertTemplateUsed(response, 'reports/view_graph.html')
        self.assertTemplateUsed(response, 'reports/view_chart.html')

        # with self.assertNoException():
        #     chart_registry = response.context['report_charts']
        # from ..report_chart_registry import report_chart_registry
        # self.assertIs(chart_registry, report_chart_registry)
        get_ctxt = response.context.get
        self.assertEqual(chart, get_ctxt('object'))

        reloading_url = reverse('reports__reload_chart_bricks', args=(chart.id,))
        self.assertEqual(reloading_url, get_ctxt('bricks_reload_url'))

        self.get_brick_node(
            self.get_html_tree(response.content), brick=ReportChartBrick,
        )

        # Reloading ---
        brick_id = ReportChartBrick.id
        reload_response = self.assertGET200(reloading_url, data={'brick_id': brick_id})
        reload_content = reload_response.json()
        self.assertIsList(reload_content, length=1)

        sub_content = reload_content[0]
        self.assertIsList(sub_content, length=2)
        self.assertEqual(brick_id, sub_content[0])
        self.get_brick_node(self.get_html_tree(sub_content[1]), brick_id)
        # TODO: test brick content too...

        # Reloading error ---
        self.assertGET404(reloading_url, data={'brick_id': 'invalid'})

    def test_instance_bricks_info(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)
        chart1 = ReportChart.objects.create(
            linked_report=report,
            name='Capital per month of creation',
            abscissa_cell_value='created',
            abscissa_type=ReportChart.Group.MONTH,
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_cell_key='regular_field-capital',
        )
        chart2 = ReportChart.objects.create(
            linked_report=report,
            name='Number of Organisation created per month',
            abscissa_cell_value='created',
            abscissa_type=ReportChart.Group.MONTH,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        SimpleChartFetcher(chart=chart1).create_brick_config_item()
        RegularFieldLinkedChartFetcher(chart=chart1, value='image').create_brick_config_item()
        SimpleChartFetcher(chart=chart2).create_brick_config_item()

        popup_response = self.assertGET200(
            reverse('reports__instance_bricks_info', args=(chart1.id,))
        )
        brick_node1 = self.get_brick_node(
            self.get_html_tree(popup_response.content), brick=InstanceBricksInfoBrick,
        )
        self.assertBrickTitleEqual(
            brick_node=brick_node1,
            count=2, title='{count} Block', plural_title='{count} Blocks',
        )
        # TODO: improve tests for content

        # Reloading ---
        brick_id = InstanceBricksInfoBrick.id
        reload_response = self.assertGET200(
            reverse('reports__reload_chart_ibci_bricks', args=(chart1.id,)),
            data={'brick_id': brick_id},
        )
        reload_content = reload_response.json()
        self.assertIsList(reload_content, length=1)

        sub_content = reload_content[0]
        self.assertIsList(sub_content, length=2)
        self.assertEqual(brick_id, sub_content[0])

        brick_node2 = self.get_brick_node(self.get_html_tree(sub_content[1]), brick_id)
        self.assertBrickTitleEqual(
            brick_node=brick_node2,
            count=2, title='{count} Block', plural_title='{count} Blocks',
        )
        # TODO: improve tests for content

    def test_creation__FK(self):
        "Group.FK."
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)

        url = self._build_add_chart_url(report)
        context = self.assertGET200(url).context
        self.assertEqual(
            _('Create a chart for «{entity}»').format(entity=report),
            context.get('title'),
        )
        self.assertEqual(ReportChart.save_label, context.get('submit_label'))

        name = 'My Chart #1'
        abscissa = 'sector'
        chart_type = ReportChart.Group.FK
        plot_name = 'barchart'
        self.assertNoFormError(
            self.client.post(
                url,
                data={
                    # 'user': user.pk,  # todo: report.user used instead ??
                    'name': name,

                    'abscissa': self.formfield_value_abscissa(
                        abscissa=FakeOrganisation._meta.get_field(abscissa),
                        chart_type=chart_type,
                    ),

                    'ordinate': self.formfield_value_ordinate(
                        aggr_id=ReportChart.Aggregator.COUNT,
                    ),

                    'plot_name': plot_name,
                },
            )
        )

        chart = self.get_object_or_fail(ReportChart, linked_report=report, name=name)
        self.assertEqual(user,                         chart.user)
        self.assertEqual(abscissa,                     chart.abscissa_cell_value)
        self.assertEqual(ReportChart.Aggregator.COUNT, chart.ordinate_type)
        self.assertEqual('',                           chart.ordinate_cell_key)
        self.assertEqual(chart_type,                   chart.abscissa_type)
        self.assertEqual(plot_name,                    chart.plot_name)
        self.assertIsNone(chart.abscissa_parameter)
        self.assertIs(chart.asc, True)

        hand = chart.hand
        self.assertEqual(_('Sector'), hand.verbose_abscissa)
        self.assertEqual(_('Count'),  hand.ordinate.verbose_name)
        self.assertIsNone(hand.abscissa_error)
        self.assertIsNone(hand.ordinate_error)

        abs_info = chart.abscissa_info
        self.assertIsInstance(abs_info, AbscissaInfo)
        self.assertEqual(chart_type, abs_info.chart_type)
        self.assertIsNone(abs_info.parameter)
        self.assertEqual('regular_field-sector', abs_info.cell.key)

    def test_creation__DAY(self):
        "Ordinate with aggregate + Group.DAY."
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)
        url = self._build_add_chart_url(report)

        name = 'My Chart #1'
        ordinate = 'capital'
        chart_type = ReportChart.Group.DAY

        def post(**kwargs):
            return self.client.post(
                url,
                data={
                    # 'user': user.id,
                    'name': name,
                    'plot_name': 'barchart',
                    **kwargs
                },
            )

        response = post(
            abscissa=self.formfield_value_abscissa(
                abscissa=FakeOrganisation._meta.get_field('legal_form'),
                chart_type=chart_type,
            ),
            ordinate=self.formfield_value_ordinate(
                aggr_id=ReportChart.Aggregator.MAX,
                cell=EntityCellRegularField.build(FakeOrganisation, 'name'),
            ),
        )
        self.assertEqual(200, response.status_code)

        form = self.get_form_or_fail(response)
        self.assertFormError(
            form,
            field='abscissa',
            errors='This entity cell is not allowed.'
        )
        self.assertFormError(
            form,
            field='ordinate',
            errors='This entity cell is not allowed.'
        )

        # ---
        aggregate = ReportChart.Aggregator.MAX
        abscissa = 'created'
        self.assertNoFormError(post(
            abscissa=self.formfield_value_abscissa(
                abscissa=FakeOrganisation._meta.get_field(abscissa),
                chart_type=chart_type,
            ),
            ordinate=self.formfield_value_ordinate(
                aggr_id=aggregate,
                cell=EntityCellRegularField.build(FakeOrganisation, ordinate),
            ),
        ))

        chart = self.get_object_or_fail(ReportChart, linked_report=report, name=name)
        # self.assertEqual(user, chart.user)
        self.assertEqual(abscissa,   chart.abscissa_cell_value)
        self.assertEqual(chart_type, chart.abscissa_type)
        self.assertIsNone(chart.abscissa_parameter)
        self.assertEqual(aggregate,                   chart.ordinate_type)
        self.assertEqual(f'regular_field-{ordinate}', chart.ordinate_cell_key)

        hand = chart.hand
        self.assertEqual(_('Creation date'), hand.verbose_abscissa)
        self.assertEqual(_('Maximum'), hand.ordinate.verbose_name)
        self.assertEqual(_('Capital'), str(hand.ordinate.cell))

    def test_creation__CHOICES(self):
        "Group.CHOICES."
        user = self.login_as_root_and_get()
        report = Report.objects.create(user=user, name='Campaigns', ct=FakeEmailCampaign)

        name = 'My campaign graph'
        abscissa = 'type'
        self.assertNoFormError(
            self.client.post(
                self._build_add_chart_url(report),
                data={
                    # 'user': user.pk,
                    'name': name,

                    'abscissa': self.formfield_value_abscissa(
                        abscissa=FakeEmailCampaign._meta.get_field(abscissa),
                        chart_type=ReportChart.Group.CHOICES,
                    ),

                    'ordinate': self.formfield_value_ordinate(
                        aggr_id=ReportChart.Aggregator.COUNT,
                    ),

                    'plot_name': 'barchart',
                },
            )
        )

        chart = self.get_object_or_fail(ReportChart, linked_report=report, name=name)
        # self.assertEqual(user,                         chart.user)
        self.assertEqual(abscissa,                     chart.abscissa_cell_value)
        self.assertEqual(ReportChart.Aggregator.COUNT, chart.ordinate_type)
        self.assertEqual('',                           chart.ordinate_cell_key)

        self.assertEqual('Type', chart.hand.verbose_abscissa)

    def test_creation__RELATION(self):
        "Group.RELATION."
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)

        name = 'My Chart #1'
        chart_type = ReportChart.Group.RELATION
        rtype_id = fake_constants.FAKE_REL_OBJ_EMPLOYED_BY
        rtype = RelationType.objects.get(id=rtype_id)
        self.assertNoFormError(self.client.post(
            self._build_add_chart_url(report),
            data={
                # 'user': user.pk,
                'name': name,
                'plot_name': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=rtype, chart_type=chart_type,
                ),
                'ordinate': self.formfield_value_ordinate(aggr_id=ReportChart.Aggregator.COUNT),
            },
        ))

        chart = self.get_object_or_fail(ReportChart, linked_report=report, name=name)
        # self.assertEqual(user,      chart.user)
        self.assertEqual(rtype_id,                     chart.abscissa_cell_value)
        self.assertEqual(ReportChart.Aggregator.COUNT, chart.ordinate_type)
        self.assertEqual('',                           chart.ordinate_cell_key)

        self.assertEqual('employs', chart.hand.verbose_abscissa)

    @parameterized.expand([ReportChart.Group.MONTH, ReportChart.Group.YEAR])
    def test_creation__date(self, chart_type):
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)
        url = self._build_add_chart_url(report)

        name = 'My Chart #1'
        ordinate = 'capital'
        aggregate = ReportChart.Aggregator.MIN

        def post(abscissa_field, **kwargs):
            return self.client.post(
                url,
                data={
                    # 'user': user.pk,
                    'name': name,
                    'plot_name': 'barchart',

                    'abscissa': self.formfield_value_abscissa(
                        abscissa=FakeOrganisation._meta.get_field(abscissa_field),
                        chart_type=chart_type,
                    ),

                    'ordinate': self.formfield_value_ordinate(
                        aggr_id=aggregate,
                        cell=EntityCellRegularField.build(FakeOrganisation, ordinate),
                    ),

                    **kwargs
                },
            )

        response = post(abscissa_field='legal_form')
        self.assertEqual(200, response.status_code)
        self.assertFormError(
            self.get_form_or_fail(response),
            field='abscissa',
            errors='This entity cell is not allowed.'
        )

        # ---
        abscissa = 'created'
        self.assertNoFormError(post(abscissa_field=abscissa))

        chart = self.get_object_or_fail(ReportChart, linked_report=report, name=name)
        # self.assertEqual(user, rgraph.user)
        self.assertEqual(abscissa,   chart.abscissa_cell_value)
        self.assertEqual(chart_type, chart.abscissa_type)
        self.assertIsNone(chart.abscissa_parameter)
        self.assertEqual(aggregate,                   chart.ordinate_type)
        self.assertEqual(f'regular_field-{ordinate}', chart.ordinate_cell_key)

    def test_creation__RANGE(self):
        "ReportChart.Group.RANGE."
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)
        url = self._build_add_chart_url(report)

        name = 'My Chart #1'
        ordinate = 'capital'
        chart_type = ReportChart.Group.RANGE

        def post(abscissa_field, parameter='', aggr_id=ReportChart.Aggregator.MAX, **kwargs):
            return self.client.post(
                url,
                data={
                    # 'user': user.id,
                    'name': name,
                    'plot_name': 'barchart',

                    'abscissa': self.formfield_value_abscissa(
                        abscissa=FakeOrganisation._meta.get_field(abscissa_field),
                        chart_type=chart_type,
                        parameter=parameter,
                    ),
                    'ordinate': self.formfield_value_ordinate(
                        aggr_id=aggr_id,
                        cell=EntityCellRegularField.build(FakeOrganisation, ordinate),
                    ),

                    **kwargs
                },
            )

        response = post(abscissa_field='legal_form')
        self.assertEqual(200, response.status_code)
        self.assertFormError(
            self.get_form_or_fail(response),
            field='abscissa',
            errors='This entity cell is not allowed.'
        )

        # ---
        aggregate = ReportChart.Aggregator.AVG
        abscissa = 'modified'
        days = '25'
        self.assertNoFormError(post(abscissa_field=abscissa, parameter=days, aggr_id=aggregate))

        chart = self.get_object_or_fail(ReportChart, linked_report=report, name=name)
        # self.assertEqual(user, chart.user)
        self.assertEqual(abscissa,   chart.abscissa_cell_value)
        self.assertEqual(chart_type, chart.abscissa_type)
        self.assertEqual(days,       chart.abscissa_parameter)
        self.assertEqual(aggregate,                   chart.ordinate_type)
        self.assertEqual(f'regular_field-{ordinate}', chart.ordinate_cell_key)

    def test_creation__CUSTOM_FK(self):
        "ReportChart.Group.CUSTOM_FK."
        user = self.login_as_root_and_get()
        cf_enum = CustomField.objects.create(
            content_type=self.ct_contact, name='Hair', field_type=CustomField.ENUM,
        )

        report = self._create_simple_contacts_report(user=user)
        url = self._build_add_chart_url(report)

        name = 'My Chart #1'
        chart_type = ReportChart.Group.CUSTOM_FK
        self.assertNoFormError(self.client.post(
            url,
            data={
                # 'user': user.pk,
                'name': name,
                'plot_name': 'barchart',
                'abscissa': self.formfield_value_abscissa(
                    abscissa=cf_enum, chart_type=chart_type,
                ),
                'ordinate': self.formfield_value_ordinate(aggr_id=ReportChart.Aggregator.COUNT),
            },
        ))

        chart = self.get_object_or_fail(ReportChart, linked_report=report, name=name)
        # self.assertEqual(user,              chart.user)
        self.assertEqual(str(cf_enum.uuid), chart.abscissa_cell_value)
        self.assertEqual(chart_type,        chart.abscissa_type)

    @parameterized.expand([
        ReportChart.Group.CUSTOM_DAY,
        ReportChart.Group.CUSTOM_MONTH,
        ReportChart.Group.CUSTOM_YEAR,
    ])
    def test_creation__custom_datetime(self, chart_type):
        user = self.login_as_root_and_get()

        cf_dt = CustomField.objects.create(
            content_type=self.ct_orga,
            name='First victory',
            field_type=CustomField.DATETIME,
        )

        report = self._create_simple_organisations_report(user=user)
        url = self._build_add_chart_url(report)

        name = 'My Chart #1'
        self.assertNoFormError(self.client.post(
            url,
            data={
                # 'user': user.pk,
                'name': name,
                'plot_name': 'barchart',
                'abscissa': self.formfield_value_abscissa(
                    abscissa=cf_dt, chart_type=chart_type,
                ),
                'ordinate': self.formfield_value_ordinate(aggr_id=ReportChart.Aggregator.COUNT),
            },
        ))

        chart = self.get_object_or_fail(ReportChart, linked_report=report, name=name)
        # self.assertEqual(user,                         chart.user)
        self.assertEqual(str(cf_dt.uuid),              chart.abscissa_cell_value)
        self.assertEqual(chart_type,                   chart.abscissa_type)
        self.assertEqual(ReportChart.Aggregator.COUNT, chart.ordinate_type)
        self.assertEqual('',                           chart.ordinate_cell_key)

        self.assertEqual(cf_dt.name, chart.hand.verbose_abscissa)

    @parameterized.expand([
        ReportChart.Group.CUSTOM_DAY,
        ReportChart.Group.CUSTOM_MONTH,
        ReportChart.Group.CUSTOM_YEAR,
    ])
    def test_creation__custom_date(self, chart_type):
        user = self.login_as_root_and_get()

        cf_date = CustomField.objects.create(
            content_type=self.ct_orga,
            name='First victory',
            field_type=CustomField.DATE,
        )

        report = self._create_simple_organisations_report(user=user)
        url = self._build_add_chart_url(report)

        name = 'My Chart #1'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'user': user.pk,
                'name': name,
                'plot_name': 'barchart',
                'abscissa': self.formfield_value_abscissa(
                    abscissa=cf_date,
                    chart_type=chart_type,
                ),
                'ordinate': self.formfield_value_ordinate(aggr_id=ReportChart.Aggregator.COUNT),
            },
        ))

        chart = self.get_object_or_fail(ReportChart, linked_report=report, name=name)
        # self.assertEqual(user,                         chart.user)
        self.assertEqual(str(cf_date.uuid),            chart.abscissa_cell_value)
        self.assertEqual(chart_type,                   chart.abscissa_type)
        self.assertEqual(ReportChart.Aggregator.COUNT, chart.ordinate_type)
        self.assertEqual('',                           chart.ordinate_cell_key)

        self.assertEqual(cf_date.name, chart.hand.verbose_abscissa)

    def test_creation__custom_range(self):
        "ReportChart.Group.CUSTOM_RANGE."
        user = self.login_as_root_and_get()

        cf_dt = CustomField.objects.create(
            content_type=self.ct_orga, name='First victory', field_type=CustomField.DATETIME,
        )

        report = self._create_simple_organisations_report(user=user)
        url = self._build_add_chart_url(report)

        name = 'My Chart #1'
        chart_type = ReportChart.Group.CUSTOM_RANGE
        days = '25'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'user': user.pk,
                'name': name,
                'plot_name': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=cf_dt,
                    chart_type=chart_type,
                    parameter=days,
                ),
                'ordinate': self.formfield_value_ordinate(aggr_id=ReportChart.Aggregator.COUNT),
            },
        ))

        chart = self.get_object_or_fail(ReportChart, linked_report=report, name=name)
        # self.assertEqual(user,                         chart.user)
        self.assertEqual(str(cf_dt.uuid),              chart.abscissa_cell_value)
        self.assertEqual(chart_type,                   chart.abscissa_type)
        self.assertEqual(days,                         chart.abscissa_parameter)
        self.assertEqual(ReportChart.Aggregator.COUNT, chart.ordinate_type)
        self.assertEqual('',                           chart.ordinate_cell_key)

        self.assertEqual(cf_dt.name, chart.hand.verbose_abscissa)

    def test_creation__bad_related(self):
        "Not related to a Report => error."
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='House Stark')
        self.assertGET404(self._build_add_chart_url(orga))

    def test_creation__fields_config(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)

        hidden_fname1 = 'sector'
        hidden_fname2 = 'capital'
        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[
                (hidden_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )

        response = self.assertPOST200(
            self._build_add_chart_url(report),
            data={
                'user': user.pk,
                'name': 'My Chart #1',
                'plot_name': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeOrganisation._meta.get_field(hidden_fname1),
                    chart_type=ReportChart.Group.FK,
                ),
                'ordinate': self.formfield_value_ordinate(
                    aggr_id=ReportChart.Aggregator.SUM,
                    cell=EntityCellRegularField.build(FakeOrganisation, hidden_fname2),
                ),
            },
        )
        form = self.get_form_or_fail(response)
        self.assertFormError(
            form, field='abscissa', errors='This entity cell is not allowed.',
        )
        self.assertFormError(
            form, field='ordinate', errors='This entity cell is not allowed.',
        )

    def test_creation__disabled_rtype(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)

        rtype = RelationType.objects.builder(
            id='test-subject_disabled', predicate='[disabled]',
            enabled=False,  # <==
        ).symmetric(
            id='test-object_disabled', predicate='what ever',
        ).get_or_create()[0]

        response = self.assertPOST200(
            self._build_add_chart_url(report),
            data={
                'user': user.pk,
                'name': 'My Chart #1',
                'plot_name': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=rtype,
                    chart_type=ReportChart.Group.RELATION,
                ),
                'ordinate': self.formfield_value_ordinate(
                    aggr_id=ReportChart.Aggregator.COUNT,
                ),
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='abscissa',
            errors='This entity cell is not allowed.',
        )

    def test_edition(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            linked_report=report,
            name='Capital per month of creation',
            abscissa_cell_value='created',
            abscissa_type=ReportChart.Group.MONTH,
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_cell_key='regular_field-capital',
        )
        self.assertIsNone(chart.user)

        url = self._build_edit_url(chart)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(
            _('Edit a chart for «{entity}»').format(entity=report),
            context.get('title'),
        )

        with self.assertNoException():
            abscissa_f = context['form'].fields['abscissa']

        self.assertSetEqual(
            {'regular_field-created'}, abscissa_f.not_hiddable_cell_keys,
        )

        name = 'Organisations per sector'
        abscissa = 'sector'
        chart_type = ReportChart.Group.FK
        self.assertNoFormError(self.client.post(
            url,
            data={
                # 'user': ...,
                'name': name,
                'plot_name': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeOrganisation._meta.get_field(abscissa),
                    chart_type=chart_type,
                ),
                'ordinate': self.formfield_value_ordinate(aggr_id=ReportChart.Aggregator.COUNT),
            },
        ))

        chart = self.refresh(chart)
        self.assertEqual(user,                         chart.user)
        self.assertEqual(name,                         chart.name)
        self.assertEqual(abscissa,                     chart.abscissa_cell_value)
        self.assertEqual(ReportChart.Aggregator.COUNT, chart.ordinate_type)
        self.assertEqual(chart_type,                   chart.abscissa_type)
        self.assertIsNone(chart.abscissa_parameter)

    def test_edition__money_field(self):
        user = self.login_as_root_and_get()
        chart = self._create_invoice_report_n_chart(user=user)
        url = self._build_edit_url(chart)
        response = self.assertGET200(url)

        with self.assertNoException():
            ordinate_f = response.context['form'].fields['ordinate']

        self.assertEqual(
            _(
                'If you use a field related to money, the entities should use the same '
                'currency or the result will be wrong. Concerned fields are: {}'
            ).format('{}, {}'.format(_('Total with VAT'), _('Total without VAT'))),
            ordinate_f.help_text,
        )

        abscissa = 'created'
        chart_type = ReportChart.Group.DAY
        self.assertNoFormError(self.client.post(
            url,
            data={
                # 'user': user.pk,
                'name': chart.name,
                'plot_name': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeInvoice._meta.get_field(abscissa),
                    chart_type=chart_type,
                ),
                'ordinate': self.formfield_value_ordinate(
                    aggr_id=ReportChart.Aggregator.AVG,
                    cell=EntityCellRegularField.build(FakeInvoice, 'total_vat'),
                ),
            },
        ))

        chart = self.refresh(chart)
        self.assertEqual(abscissa,   chart.abscissa_cell_value)
        self.assertEqual(chart_type, chart.abscissa_type)
        self.assertIsNone(chart.abscissa_parameter)
        self.assertEqual(ReportChart.Aggregator.AVG, chart.ordinate_type)
        self.assertEqual('regular_field-total_vat',  chart.ordinate_cell_key)

    def test_edition__integer_money_field(self):
        user = self.login_as_root_and_get()
        report = Report.objects.create(
            user=user, name='All opportunities of the current year',
            ct=FakeOpportunity,
        )
        chart = ReportChart.objects.create(
            linked_report=report,
            name='Sum of current year estimated sales / month',
            abscissa_cell_value='created',
            abscissa_type=ReportChart.Group.MONTH,
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_cell_key='regular_field-estimated_sales',
        )
        response = self.assertGET200(self._build_edit_url(chart))

        with self.assertNoException():
            ordinate_f = response.context['form'].fields['ordinate']

        self.assertEqual(
            _(
                'If you use a field related to money, the entities should use the same '
                'currency or the result will be wrong. Concerned fields are: {}'
            ).format('Estimated sales'),
            ordinate_f.help_text,
        )

    def test_edition__fieldsconfig(self):
        user = self.login_as_root_and_get()
        chart = self._create_invoice_report_n_chart(
            user=user,
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_field='total_vat',
        )

        hidden_fname = 'total_no_vat'
        FieldsConfig.objects.create(
            content_type=FakeInvoice,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        response = self.assertPOST200(
            self._build_edit_url(chart),
            data={
                # 'user': user.pk,
                'name': chart.name,
                'plot_name': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeInvoice._meta.get_field('expiration_date'),
                    chart_type=ReportChart.Group.MONTH,
                ),

                'ordinate': self.formfield_value_ordinate(
                    aggr_id=ReportChart.Aggregator.AVG,
                    cell=EntityCellRegularField.build(FakeInvoice, hidden_fname),
                ),
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='ordinate',
            errors='This entity cell is not allowed.',
        )

    def test_edition__hidden_but_selected__abscissa(self):
        "With FieldsConfig: if fields are already selected => still proposed (abscissa)."
        user = self.login_as_root_and_get()
        hidden_fname = 'expiration_date'
        chart = self._create_invoice_report_n_chart(user=user, abscissa=hidden_fname)

        FieldsConfig.objects.create(
            content_type=FakeInvoice,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        response = self.client.post(
            self._build_edit_url(chart),
            data={
                # 'user':  chart.user.pk,
                'name':      chart.name,
                'plot_name': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeInvoice._meta.get_field(hidden_fname),
                    chart_type=chart.abscissa_type,
                ),
                'ordinate': self.formfield_value_ordinate(
                    aggr_id=ReportChart.Aggregator.SUM,
                    cell=EntityCellRegularField.build(FakeInvoice, 'total_no_vat'),
                ),
            },
        )
        self.assertNoFormError(response)

        chart = self.refresh(chart)
        self.assertEqual(hidden_fname, chart.abscissa_cell_value)

        hand = chart.hand
        self.assertEqual(_('Expiration date'), hand.verbose_abscissa)
        self.assertEqual(
            _('this field should be hidden.'), hand.abscissa_error,
        )

    def test_edition__hidden_but_selected__ordinate(self):
        "With FieldsConfig: if fields are already selected => still proposed (ordinate)."
        user = self.login_as_root_and_get()
        hidden_fname = 'total_no_vat'
        chart = self._create_invoice_report_n_chart(
            user=user,
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_field=hidden_fname,
        )

        FieldsConfig.objects.create(
            content_type=FakeInvoice,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        response = self.client.post(
            self._build_edit_url(chart),
            data={
                # 'user':  chart.user.pk,
                'name':      chart.name,
                'plot_name': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeInvoice._meta.get_field(chart.abscissa_cell_value),
                    chart_type=chart.abscissa_type,
                ),

                'ordinate': self.formfield_value_ordinate(
                    aggr_id=chart.ordinate_type,
                    cell=EntityCellRegularField.build(FakeInvoice, hidden_fname),
                ),
            },
        )
        self.assertNoFormError(response)

    def test_edition__custom_field(self):
        user = self.login_as_root_and_get()
        cf = CustomField.objects.create(
            content_type=self.ct_orga,
            name='Country',
            field_type=CustomField.ENUM,
        )
        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Number of clans per countries',
            abscissa_type=ReportChart.Group.CUSTOM_FK,
            abscissa_cell_value=str(cf.uuid),
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        response = self.assertGET200(self._build_edit_url(chart))
        with self.assertNoException():
            abscissa_f = response.context['form'].fields['abscissa']

        self.assertSetEqual(
            {f'custom_field-{cf.id}'}, abscissa_f.not_hiddable_cell_keys,
        )

    def test_deletion(self):
        user = self.login_as_standard(allowed_apps=['creme_core', 'reports'])
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])

        chart = self._create_documents_chart(user=user)
        ibci = SimpleChartFetcher(chart=chart).create_brick_config_item()

        url = chart.get_delete_absolute_url()
        self.assertGET405(url)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(chart)
        self.assertDoesNotExist(ibci)

    def test_deletion__not_allowed(self):
        user = self.login_as_standard(allowed_apps=['creme_core', 'reports'])
        self.add_credentials(role=user.role, own=['VIEW'])  # 'CHANGE'

        chart = self._create_documents_chart(user=user)
        self.assertPOST403(chart.get_delete_absolute_url(), follow=True)
        self.assertStillExists(chart)

    # TODO?
    # def test_inneredit(self):
    #     user = self.login()
    #     report = self._create_simple_organisations_report()
    #     chart = ReportChart.objects.create(
    #         linked_report=report,
    #         name='capital per month of creation',
    #         chart='barchart',
    #         abscissa_cell_value='created', abscissa_type=ReportChart.Group.MONTH,
    #         ordinate_type=ReportChart.Aggregator.SUM,
    #         ordinate_cell_key='regular_field-capital',
    #     )
    #
    #     build_uri = self.build_inneredit_uri
    #     field_name = 'name'
    #     uri = build_uri(chart, field_name)
    #     self.assertGET200(uri)
    #
    #     name = chart.name.title()
    #     self.assertNoFormError(self.client.post( uri, data={field_name:  name}))
    #     self.assertEqual(name, self.refresh(chart).name)
    #
    #     self.assertGET404(build_uri(chart, 'report'))
    #     self.assertGET404(build_uri(chart, 'abscissa'))
    #     self.assertGET404(build_uri(chart, 'ordinate'))
    #     self.assertGET404(build_uri(chart, 'type'))
    #     self.assertGET404(build_uri(chart, 'days'))
    #     self.assertGET404(build_uri(chart, 'chart'))


@skipIfCustomReport
# class GraphFetchSettingsTestCase(BaseReportsTestCase):
class ChartFetchSettingsUpdateTestCase(BaseReportsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # TODO: use a fake registry instead.
        # report_chart_registry.register(
        #     ReportPieChart(name='fakepie', label='Fake Pie')
        # )
        plot_registry.register(
            Pie(name='fakepie', label='Fake Pie'),
        )

    def test_update_settings__missing_id(self):
        self.login_as_root()
        self.assertPOST404(
            # path=reverse('reports__update_graph_fetch_settings', args=(self.UNUSED_PK,)),
            path=reverse('reports__update_chart_fetch_settings', args=(self.UNUSED_PK,)),
            # data={'chart': 'fakepie'},
            data={'plot': 'fakepie'},
        )

    def test_update_settings__not_allowed(self):
        """Edition on reports is needed to update the settings."""
        user = self.login_as_standard(allowed_apps=['reports'])
        self.add_credentials(user.role, own=['VIEW'])  # 'CHANGE'

        # graph = self._create_documents_rgraph(user=self.get_root_user())
        chart = self._create_documents_chart(user=self.get_root_user())
        # self.assertEqual(graph.asc, True)
        self.assertEqual(chart.asc, True)
        # self.assertEqual(graph.chart, None)
        self.assertEqual(chart.plot_name, None)

        # with self.assertLogs(graph_views.logger, level='WARNING') as logs:
        with self.assertLogs(chart_views.logger, level='WARNING') as logs:
            response = self.assertPOST200(
                # path=reverse('reports__update_graph_fetch_settings', args=(graph.pk,)),
                path=reverse('reports__update_chart_fetch_settings', args=(chart.id,)),
                # data={'sort': 'DESC', 'chart': 'fakepie'},
                data={'sort': 'DESC', 'plot': 'fakepie'},
            )

        # self.assertJSONEqual(response.content, {'sort': 'ASC', 'chart': None})
        self.assertJSONEqual(response.content, {'sort': 'ASC', 'plot': None})
        self.assertEqual([
            # f'WARNING:creme.reports.views.graph:The ReportGraph id="{graph.id}" '
            f'WARNING:creme.reports.views.chart:The ReportChart id="{chart.id}" '
            'cannot be edited, so the settings are not saved.'
        ], logs.output)

    @parameterized.expand([
        # ({}, 'Chart value is missing'),
        ({}, 'Plot name is missing'),
        # ({"sort": "ASC"}, 'Chart value is missing'),
        ({'sort': 'ASC'}, 'Plot name is missing'),
        # ({"chart": "unknown", "sort": "ASC"}, (
        ({'plot': 'unknown', 'sort': 'ASC'}, (
            # 'Chart value must be in '
            # f'{[c[0] for c in report_chart_registry] + ["fakepie"]} '
            # '(value=unknown)'
            'Plot name must be in '
            f'{[plot.name for plot in plot_registry] + ["fakepie"]} '
            '(given name="unknown")'
        )),
        # ({"chart": "fakepie", "sort": "unknown"}, (
        ({'plot': 'fakepie', 'sort': 'unknown'}, (
            'Order value must be ASC or DESC (value=unknown)'
        )),
    ])
    def test_update_settings__invalid_argument(self, data, expected):
        user = self.login_as_root_and_get()
        chart = self._create_documents_chart(user=user)

        response = self.assertPOST(
            400,
            path=reverse('reports__update_chart_fetch_settings', args=(chart.pk,)),
            data=data,
        )
        self.assertEqual(response.text, expected)

    def test_update_settings(self):
        user = self.login_as_root_and_get()

        chart = self._create_documents_chart(user=user)
        self.assertEqual(chart.asc, True)
        self.assertEqual(chart.plot_name, None)

        plot = 'fakepie'
        data = {'sort': 'DESC', 'plot': plot}
        response = self.assertPOST200(
            path=reverse('reports__update_chart_fetch_settings', args=(chart.id,)),
            data=data
        )
        self.assertJSONEqual(response.content, data)

        chart.refresh_from_db()
        self.assertEqual(chart.asc, False)
        self.assertEqual(chart.plot_name, plot)

    # # DEPRECATED
    # def test_update_instance_settings__missing_id(self):
    #     user = self.login_as_root_and_get()
    #
    #     url_name = 'reports__update_graph_fetch_settings_for_instance'
    #     UNUSED_PK = self.UNUSED_PK
    #     self.assertPOST404(
    #         path=reverse(url_name, args=(UNUSED_PK, UNUSED_PK)),
    #         data={'chart': 'fakepie'},
    #     )
    #
    #     entity = FakeOrganisation.objects.create(user=user, name='Acme')
    #     graph = self._create_documents_rgraph(user=user)
    #     self.assertPOST404(
    #         # path=reverse(url_name, args=(UNUSED_PK, graph.pk)),
    #         path=reverse(url_name, args=(UNUSED_PK, entity.id)),
    #         data={'chart': 'fakepie'},
    #     )
    #
    #     config = self._create_graph_instance_brick(graph)
    #     self.assertPOST404(
    #         path=reverse(url_name, args=(config.pk, UNUSED_PK)),
    #         data={'chart': 'fakepie'},
    #     )
    #
    # # DEPRECATED
    # @parameterized.expand([
    #     ({}, 'Chart value is missing'),
    #     ({"sort": "ASC"}, 'Chart value is missing'),
    #     ({"chart": "unknown", "sort": "ASC"}, (
    #         'Chart value must be in '
    #         f'{[c[0] for c in report_chart_registry] + ["fakepie"]} '
    #         '(value=unknown)'
    #     )),
    #     ({"chart": "fakepie", "sort": "unknown"}, (
    #         'Order value must be ASC or DESC (value=unknown)'
    #     )),
    # ])
    # def test_update_instance_settings__invalid_argument(self, data, expected):
    #     user = self.login_as_root_and_get()
    #     graph = self._create_documents_rgraph(user=user)
    #     ibci = self._create_graph_instance_brick(graph)
    #     entity = FakeOrganisation.objects.create(user=user, name='Acme')
    #
    #     response = self.assertPOST(
    #         400,
    #         path=reverse(
    #             'reports__update_graph_fetch_settings_for_instance',
    #             args=(ibci.id, entity.id),
    #         ),
    #         data=data,
    #     )
    #     self.assertEqual(response.text, expected)
    #
    # def test_update_instance_settings(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #     graph = self._create_documents_rgraph(user=user)
    #     ibci = self._create_graph_instance_brick(graph)
    #     entity = FakeOrganisation.objects.create(user=user, name='Acme')
    #
    #     self.assertEqual(graph.asc, True)
    #     self.assertEqual(graph.chart, None)
    #
    #     data = {'sort': 'DESC', 'chart': 'fakepie'}
    #     response = self.assertPOST200(
    #         path=reverse(
    #             'reports__update_graph_fetch_settings_for_instance',
    #             args=(ibci.pk, entity.id),
    #         ),
    #         data=data,
    #     )
    #     self.assertJSONEqual(response.content, data)
    #
    #     graph.refresh_from_db()
    #     self.assertEqual(graph.asc, False)
    #     self.assertEqual(graph.chart, 'fakepie')
