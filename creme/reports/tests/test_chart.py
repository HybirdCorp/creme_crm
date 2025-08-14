from datetime import date
from decimal import Decimal
from functools import partial
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import ProtectedError
from django.db.models.query_utils import Q
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import override as override_language
from parameterized import parameterized

from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellRegularField,
)
from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    CustomField,
    CustomFieldEnum,
    CustomFieldEnumValue,
    CustomFieldInteger,
    EntityFilter,
    FakeContact,
    FakeEmailCampaign,
    FakeInvoice,
    FakeOrganisation,
    FakePosition,
    FakeSector,
    FieldsConfig,
    Relation,
    RelationType,
)
from creme.creme_core.tests import fake_constants
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.queries import QSerializer

from ..bricks import InstanceBricksInfoBrick, ReportChartBrick
from ..core.chart import AbscissaInfo, OrdinateInfo
from ..core.chart.fetcher import (
    RegularFieldLinkedChartFetcher,
    SimpleChartFetcher,
)
from ..core.chart.lv_url import ListViewURLBuilder
from ..models import ReportChart
from .base import (
    AxisFieldsMixin,
    BaseReportsTestCase,
    Report,
    skipIfCustomReport,
)
from .fake_models import FakeReportsColorCategory


@skipIfCustomReport
class ReportChartTestCase(BrickTestCaseMixin,
                          AxisFieldsMixin,
                          BaseReportsTestCase):
    @staticmethod
    def _build_add_chart_url(report):
        return reverse('reports__create_chart', args=(report.id,))

    @staticmethod
    def _build_edit_url(chart):
        return reverse('reports__edit_chart', args=(chart.id,))

    def _serialize_qfilter(self, **kwargs):
        return QSerializer().dumps(Q(**kwargs))

    def test_listview_URL_builder01(self):
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

    def test_listview_URL_builder02(self):
        "Model without list-view."
        with self.assertNoException():
            builder = ListViewURLBuilder(FakeSector)

        self.assertIsNone(builder(None))
        self.assertIsNone(builder({'id': '1'}))

    def test_listview_URL_builder03(self):
        "common_q."
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

    def test_createview__FK(self):
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

    def test_createview__DAY(self):
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

    def test_createview__CHOICES(self):
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

    def test_createview__RELATION(self):
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
    def test_createview_with_date(self, chart_type):
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

    def test_createview__RANGE(self):
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

    def test_createview__CUSTOM_FK(self):
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
    def test_createview_with_customdatetime(self, chart_type):
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
    def test_createview_with_customdate(self, chart_type):
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

    def test_createview_with_customrange(self):
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

    def test_createview__bad_related(self):
        "Not related to a Report => error."
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='House Stark')
        self.assertGET404(self._build_add_chart_url(orga))

    def test_createview__fieldsconfig(self):
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

    def test_createview__disabled_rtype(self):
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

    def test_abscissa_info(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart(
            # user=user,
            linked_report=report,
            name='Capital per month of creation',
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_cell_key='regular_field-capital',
        )

        chart.abscissa_info = AbscissaInfo(
            chart_type=ReportChart.Group.FK,
            cell=EntityCellRegularField.build(FakeOrganisation, 'capital'),
        )
        self.assertEqual('capital',            chart.abscissa_cell_value)
        self.assertEqual(ReportChart.Group.FK, chart.abscissa_type)
        self.assertIsNone(chart.abscissa_parameter)

        abs_info1 = chart.abscissa_info
        self.assertIsInstance(abs_info1, AbscissaInfo)
        self.assertEqual(ReportChart.Group.FK, abs_info1.chart_type)
        self.assertIsNone(abs_info1.parameter)
        self.assertEqual('regular_field-capital', abs_info1.cell.key)

        # ---
        chart.abscissa_info = AbscissaInfo(
            chart_type=ReportChart.Group.RANGE,
            cell=EntityCellRegularField.build(FakeOrganisation, 'created'),
            parameter='3',
        )
        self.assertEqual('created', chart.abscissa_cell_value)
        self.assertEqual(ReportChart.Group.RANGE, chart.abscissa_type)
        self.assertEqual('3', chart.abscissa_parameter)

        abs_info2 = chart.abscissa_info
        self.assertEqual(ReportChart.Group.RANGE, abs_info2.chart_type)
        self.assertEqual('regular_field-created', abs_info2.cell.key)
        self.assertEqual('3', abs_info2.parameter)

    def test_ordinate_info01(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart(
            # user=user,
            linked_report=report, name='Capital per month of creation',
        )
        aggr_id1 = ReportChart.Aggregator.MAX
        cell1 = EntityCellRegularField.build(FakeOrganisation, 'capital')
        chart.ordinate_info = OrdinateInfo(aggr_id=aggr_id1, cell=cell1)
        self.assertEqual(aggr_id1,  chart.ordinate_type)
        self.assertEqual(cell1.key, chart.ordinate_cell_key)

        ord_info1 = chart.ordinate_info
        self.assertIsInstance(ord_info1, OrdinateInfo)
        self.assertEqual(aggr_id1,  ord_info1.aggr_id)
        self.assertEqual(cell1.key, ord_info1.cell.key)

        # ---
        cfield = CustomField.objects.create(
            content_type=FakeOrganisation,
            name='Value',
            field_type=CustomField.INT,
        )
        cell2 = EntityCellCustomField(cfield)
        aggr_id2 = ReportChart.Aggregator.MIN
        chart.ordinate_info = OrdinateInfo(aggr_id=aggr_id2, cell=cell2)

        self.assertEqual(aggr_id2,  chart.ordinate_type)
        self.assertEqual(cell2.portable_key, chart.ordinate_cell_key)

        ord_info2 = chart.ordinate_info
        self.assertEqual(aggr_id2,  ord_info2.aggr_id)
        self.assertEqual(cell2.key, ord_info2.cell.key)

        # ---
        aggr_id3 = ReportChart.Aggregator.COUNT
        chart.ordinate_info = OrdinateInfo(aggr_id=aggr_id3)

        self.assertEqual(aggr_id3, chart.ordinate_type)
        self.assertEqual('',       chart.ordinate_cell_key)

        ord_info3 = chart.ordinate_info
        self.assertEqual(aggr_id3,  ord_info3.aggr_id)
        self.assertIsNone(ord_info3.cell)

    def test_ordinate_info02(self):
        "Ignore FieldSConfig."
        user = self.login_as_root_and_get()
        hidden_fname = 'capital'
        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        report = self._create_simple_organisations_report(user=user)
        cell_key = f'regular_field-{hidden_fname}'
        aggr_id = ReportChart.Aggregator.MAX
        chart = ReportChart(
            # user=user,
            linked_report=report,
            name='Max capital per month of creation',
            ordinate_type=aggr_id,
            ordinate_cell_key=cell_key,
        )

        ord_info = chart.ordinate_info
        self.assertIsInstance(ord_info, OrdinateInfo)
        self.assertEqual(aggr_id,  ord_info.aggr_id)
        self.assertEqual(cell_key, ord_info.cell.key)

    def test_editview(self):
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

    def test_editview__other_ctype(self):
        "Another ContentType."
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

    def test_editview__fieldsconfig(self):
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

    def test_editview__hidden_but_selected__abscissa(self):
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

    def test_editview__hidden_but_selected__ordinate(self):
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

    def test_editview__custom_field(self):
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

    def test_deletionview(self):
        user = self.login_as_standard(allowed_apps=['creme_core', 'reports'])
        self.add_credentials(role=user.role, own=['VIEW', 'CHANGE'])

        chart = self._create_documents_chart(user=user)
        ibci = SimpleChartFetcher(chart=chart).create_brick_config_item()

        url = chart.get_delete_absolute_url()
        self.assertGET405(url)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(chart)
        self.assertDoesNotExist(ibci)

    def test_deletionview__not_allowed(self):
        user = self.login_as_standard(allowed_apps=['creme_core', 'reports'])
        self.add_credentials(role=user.role, own=['VIEW'])  # 'CHANGE'

        chart = self._create_documents_chart(user=user)
        self.assertPOST403(chart.get_delete_absolute_url(), follow=True)
        self.assertStillExists(chart)

    def test_fetch__fk__count(self):
        user = self.login_as_root_and_get()
        create_position = FakePosition.objects.create
        hand = create_position(title='Hand of the king')
        lord = create_position(title='Lord')

        last_name = 'Stark'
        create_contact = partial(FakeContact.objects.create, user=user, last_name=last_name)
        create_contact(first_name='Eddard', position=hand)
        create_contact(first_name='Robb',   position=lord)
        create_contact(first_name='Bran',   position=lord)
        create_contact(first_name='Aria')

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Starks', FakeContact, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='last_name', values=[last_name],
                ),
            ],
        )

        report = self._create_simple_contacts_report(user=user, efilter=efilter)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Contacts by position',
            abscissa_cell_value='position', abscissa_type=ReportChart.Group.FK,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        with self.assertNoException():
            x_asc, y_asc = chart.fetch(user)
            colors = chart.fetch_colormap(user)

        # no color field in FakePosition
        self.assertDictEqual({}, colors)

        self.assertListEqual([*FakePosition.objects.values_list('title', flat=True)], x_asc)

        self.assertIsList(y_asc, length=len(x_asc))

        def fmt(pk):
            return '/tests/contacts?q_filter={q_filter}&filter={efilter_id}'.format(
                q_filter=self._serialize_qfilter(position=pk),
                efilter_id=efilter.id,
            )

        self.assertListEqual([1, fmt(hand.id)], y_asc[x_asc.index(hand.title)])
        self.assertListEqual([2, fmt(lord.id)], y_asc[x_asc.index(lord.title)])

        # DESC ----------------------------------------------------------------
        x_desc, y_desc = chart.fetch(order='DESC', user=user)
        self.assertListEqual([*reversed(x_asc)], x_desc)
        self.assertListEqual([1, fmt(hand.id)], y_desc[x_desc.index(hand.title)])

        # Extra Q --------------------------------------------------------------
        extra_q = Q(first_name__startswith='B')
        x_xtra, y_xtra = chart.fetch(user=user, extra_q=extra_q)

        lord_count, lord_url = y_xtra[x_xtra.index(lord.title)]
        self.assertEqual(1, lord_count)
        self.assertListviewURL(
            url=lord_url, model=FakeOrganisation,
            expected_q=extra_q & Q(position=lord.id),
            expected_efilter_id=efilter.id,
        )

    def test_fetch__fk__aggregate(self):
        user = self.login_as_root_and_get()

        create_sector = FakeSector.objects.create
        war   = create_sector(title='War')
        trade = create_sector(title='Trade')
        peace = create_sector(title='Peace')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='House Lannister', capital=1000, sector=trade)
        create_orga(name='House Stark',     capital=100,  sector=war)
        create_orga(name='House Targaryen', capital=10,   sector=war)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Houses', FakeOrganisation, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.ISTARTSWITH,
                    field_name='name', values=['House '],
                ),
            ],
        )

        report = self._create_simple_organisations_report(user=user, efilter=efilter)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Capital max by sector',
            abscissa_cell_value='sector', abscissa_type=ReportChart.Group.FK,
            ordinate_type=ReportChart.Aggregator.MAX,
            ordinate_cell_key='regular_field-capital',
        )

        with self.assertNoException():
            x_asc, y_asc = chart.fetch(user)

        self.assertListEqual([*FakeSector.objects.values_list('title', flat=True)], x_asc)

        def fmt(pk):
            return '/tests/organisations?q_filter={}&filter=test-filter'.format(
                self._serialize_qfilter(sector=pk),
            )

        index = x_asc.index
        self.assertListEqual([100,  fmt(war.id)],   y_asc[index(war.title)])
        self.assertListEqual([1000, fmt(trade.id)], y_asc[index(trade.title)])
        self.assertListEqual([0,    fmt(peace.id)], y_asc[index(peace.title)])

    def test_fetch__fk__aggregate__customfield(self):
        "Aggregate ordinate with custom field."
        user = self.login_as_root_and_get()

        create_sector = FakeSector.objects.create
        war   = create_sector(title='War')
        trade = create_sector(title='Trade')
        peace = create_sector(title='Peace')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister', sector=trade)
        starks     = create_orga(name='House Stark',     sector=war)
        targaryens = create_orga(name='House Targaryen', sector=war)

        cf = CustomField.objects.create(
            content_type=self.ct_orga,
            name='Soldiers',
            field_type=CustomField.INT,
        )

        create_cfval = partial(CustomFieldInteger.objects.create, custom_field=cf)
        create_cfval(entity=lannisters, value=500)
        create_cfval(entity=starks,     value=400)
        create_cfval(entity=targaryens, value=200)

        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Max soldiers by sector',
            abscissa_cell_value='sector', abscissa_type=ReportChart.Group.FK,
            ordinate_type=ReportChart.Aggregator.MAX,
            ordinate_cell_key=f'custom_field-{cf.uuid}',
        )

        hand = chart.hand
        self.assertEqual(_('Maximum'), hand.ordinate.verbose_name)
        self.assertEqual(cf.name,      str(hand.ordinate.cell))

        x_asc, y_asc = chart.fetch(user)
        self.assertListEqual([*FakeSector.objects.values_list('title', flat=True)], x_asc)

        index = x_asc.index

        def fmt(pk):
            return '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(sector=pk),
            )

        self.assertListEqual([400, fmt(war.id)],   y_asc[index(war.title)])
        self.assertListEqual([500, fmt(trade.id)], y_asc[index(trade.title)])
        self.assertListEqual([0,   fmt(peace.id)], y_asc[index(peace.title)])

    def test_fetch__fk__aggregate__invalid_field(self):
        "Aggregate ordinate with invalid field."
        user = self.login_as_root_and_get()
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=self._create_simple_organisations_report(user=user),
            name='Max soldiers by sector',
            abscissa_cell_value='sector', abscissa_type=ReportChart.Group.FK,
            ordinate_type=ReportChart.Aggregator.MAX,
            ordinate_cell_key='regular_field-unknown',  # <=====
        )

        with self.assertNoException():
            x_asc, y_asc = chart.fetch(user)

        self.assertEqual([], x_asc)
        self.assertEqual([], y_asc)
        self.assertEqual(
            _('the field does not exist any more.'), chart.hand.ordinate_error,
        )

    def test_fetch__fk__aggregate__invalid(self):
        "Aggregate ordinate with invalid aggregate."
        user = self.login_as_root_and_get()
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=self._create_simple_organisations_report(user=user),
            name='Max soldiers by sector',
            abscissa_cell_value='sector', abscissa_type=ReportChart.Group.FK,
            ordinate_type='invalid',  # <=====
            ordinate_cell_key='regular_field-capital',
        )

        with self.assertNoException():
            x_asc, y_asc = chart.fetch(user)

        self.assertEqual([], x_asc)
        self.assertEqual([], y_asc)
        self.assertEqual(
            _('the aggregation function is invalid.'), chart.hand.ordinate_error
        )

    def test_fetch__fk__aggregate__invalid_customfield(self):
        "Aggregate ordinate with invalid custom field."
        user = self.login_as_root_and_get()
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=self._create_simple_organisations_report(user=user),
            name='Max soldiers by sector',
            abscissa_cell_value='sector', abscissa_type=ReportChart.Group.FK,
            ordinate_type=ReportChart.Aggregator.MAX,
            ordinate_cell_key='custom_field-1000',  # <=====
        )

        with self.assertNoException():
            x_asc, y_asc = chart.fetch(user)

        self.assertEqual([], x_asc)
        self.assertEqual([], y_asc)
        self.assertEqual(
            _('the field does not exist any more.'),
            chart.hand.ordinate_error,
        )

    def test_fetch__fk__user(self):
        "Abscissa field on Users has a limit_choices_to which excludes staff users."
        user = self.login_as_super(is_staff=True)
        other_user = self.get_root_user()

        last_name = 'Stark'
        create_contact = partial(FakeContact.objects.create, user=other_user, last_name=last_name)
        create_contact(first_name='Sansa')
        create_contact(first_name='Bran')
        create_contact(first_name='Arya', user=user)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Starks', FakeContact, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='last_name', values=[last_name],
                ),
            ],
        )

        report = self._create_simple_contacts_report(user=user, efilter=efilter)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Contacts count by User',
            abscissa_cell_value='user', abscissa_type=ReportChart.Group.FK,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        with self.assertNoException():
            x_asc, y_asc = chart.fetch(user)

        self.assertIn(str(other_user), x_asc)
        self.assertNotIn(str(user), x_asc)  # <===

    def test_fetch__fk__content_type(self):
        "Abscissa field on ContentType enumerates only entities types."
        user = self.login_as_root_and_get()

        get_ct = ContentType.objects.get_for_model
        report = Report.objects.create(
            user=user, name='Report on Reports', ct=get_ct(Report),
        )
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Report count by CTypes',
            abscissa_cell_value='ct', abscissa_type=ReportChart.Group.FK,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        with self.assertNoException():
            x_asc, y_asc = chart.fetch(user)

        self.assertIn(str(get_ct(FakeOrganisation)), x_asc)
        self.assertNotIn(str(get_ct(FakePosition)), x_asc)  # <===

    def test_fetch__fk__invalid_field(self):
        "Invalid field (not enumerable)."
        user = self.login_as_root_and_get()
        report = self._create_simple_contacts_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Contact count per address',
            abscissa_cell_value='address', abscissa_type=ReportChart.Group.FK,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        x_asc, y_asc = chart.fetch(user)
        self.assertListEqual([], x_asc)
        self.assertListEqual([], y_asc)

        hand = chart.hand
        self.assertEqual(_('Billing address'), hand.verbose_abscissa)
        self.assertEqual(
            _('this field cannot be used as abscissa.'), hand.abscissa_error
        )

    def test_fetch_colormap_with_fk(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_documents_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Document count per category',
            abscissa_cell_value='category', abscissa_type=ReportChart.Group.FK,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        create_cat = FakeReportsColorCategory.objects.create
        cat_A = create_cat(title='Cat A')
        cat_B = create_cat(title='Cat B')
        self.assertDictEqual(
            {
                cat_A.title: f'#{cat_A.color}',
                cat_B.title: f'#{cat_B.color}',
            },
            chart.fetch_colormap(user),
        )

    def test_fetch__choices__count(self):
        user = self.login_as_root_and_get()

        create_camp = partial(FakeEmailCampaign.objects.create, user=user)
        create_camp(name='Old campaign #1', type=FakeEmailCampaign.Type.INTERNAL)
        create_camp(name='Old campaign #2', type=FakeEmailCampaign.Type.EXTERNAL)
        create_camp(name='New campaign #1', type=FakeEmailCampaign.Type.EXTERNAL)
        create_camp(name='Camp #4')

        report = Report.objects.create(user=user, name='Campaigns', ct=FakeEmailCampaign)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Campaigns by type',
            abscissa_cell_value='type', abscissa_type=ReportChart.Group.CHOICES,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        with self.assertNoException():
            x_asc, y_asc = chart.fetch(user)

        int_label = FakeEmailCampaign.Type.INTERNAL.label
        ext_label = FakeEmailCampaign.Type.EXTERNAL.label
        self.assertListEqual([int_label, ext_label], x_asc)

        self.assertIsList(y_asc, length=len(x_asc))

        def fmt(type_value):
            return '/tests/e_campaigns?q_filter={q_filter}'.format(
                q_filter=self._serialize_qfilter(type=type_value),
            )

        self.assertListEqual(
            [1, fmt(FakeEmailCampaign.Type.INTERNAL)], y_asc[x_asc.index(int_label)],
        )
        self.assertListEqual(
            [2, fmt(FakeEmailCampaign.Type.EXTERNAL)], y_asc[x_asc.index(ext_label)],
        )

        # DESC ----------------------------------------------------------------
        x_desc, y_desc = chart.fetch(order='DESC', user=user)
        self.assertListEqual([*reversed(x_asc)], x_desc)
        self.assertListEqual(
            [1, fmt(FakeEmailCampaign.Type.INTERNAL)], y_desc[x_desc.index(int_label)],
        )

        # Extra Q --------------------------------------------------------------
        extra_q = Q(name__startswith='New')
        x_xtra, y_xtra = chart.fetch(user=user, extra_q=extra_q)

        external_count, external_url = y_xtra[x_xtra.index(ext_label)]
        self.assertEqual(1, external_count)
        self.assertListviewURL(
            url=external_url, model=FakeOrganisation,
            expected_q=extra_q & Q(type=FakeEmailCampaign.Type.EXTERNAL),
        )

    def test_fetch__choices__invalid_field(self):
        "Invalid field (no choices)."
        user = self.login_as_root_and_get()
        report = self._create_simple_contacts_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Contact count per address',
            abscissa_cell_value='sector', abscissa_type=ReportChart.Group.CHOICES,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        x_asc, y_asc = chart.fetch(user)
        self.assertListEqual([], x_asc)
        self.assertListEqual([], y_asc)

        hand = chart.hand
        self.assertEqual(_('Line of business'), hand.verbose_abscissa)
        self.assertEqual(
            _('this field cannot be used as abscissa.'), hand.abscissa_error,
        )

    def test_fetch__date_range__count(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)

        def create_chart(days):
            return ReportChart.objects.create(
                # user=user,
                linked_report=report,
                name=f'Number of organisation created / {days} day(s)',
                abscissa_cell_value='creation_date',
                abscissa_type=ReportChart.Group.RANGE, abscissa_parameter=str(days),
                ordinate_type=ReportChart.Aggregator.COUNT,
            )

        chart = create_chart(15)
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='Target Orga1', creation_date=date(2013, 6,  1))
        create_orga(name='Target Orga2', creation_date=date(2013, 6,  5))
        create_orga(name='Target Orga3', creation_date=date(2013, 6, 14))
        create_orga(name='Target Orga4', creation_date=date(2013, 6, 15), capital=1000)
        create_orga(name='Target Orga5', creation_date=date(2013, 6, 16), capital=1100)
        create_orga(name='Target Orga6', creation_date=date(2013, 6, 30), capital=200)

        # ASC -----------------------------------------------------------------
        with override_language('fr'):
            x_asc, y_asc = chart.fetch(user)

        self.assertListEqual(
            ['01/06/2013-15/06/2013', '16/06/2013-30/06/2013'], x_asc,
        )

        self.assertEqual(2, len(y_asc))

        def fmt(*dates):
            return '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(creation_date__range=dates),
            )

        self.assertListEqual([4, fmt('2013-06-01', '2013-06-15')], y_asc[0])
        self.assertListEqual([2, fmt('2013-06-16', '2013-06-30')], y_asc[1])

        # DESC -----------------------------------------------------------------
        with override_language('en'):
            x_desc, y_desc = chart.fetch(user=user, order='DESC')

        self.assertListEqual(
            ['2013-06-30/2013-06-16', '2013-06-15/2013-06-01'],
            x_desc,
        )
        self.assertListEqual([2, fmt('2013-06-16', '2013-06-30')], y_desc[0])
        self.assertListEqual([4, fmt('2013-06-01', '2013-06-15')], y_desc[1])

        # Extra q --------------------------------------------------------------
        extra_q = Q(capital__gt=200)

        with override_language('fr'):
            x_xtra, y_xtra = chart.fetch(user=user, extra_q=extra_q)

        self.assertListEqual(['15/06/2013-29/06/2013'], x_xtra)

        extra_value, extra_url = y_xtra[0]
        self.assertEqual(2, extra_value)
        self.assertListviewURL(
            url=extra_url,
            model=FakeOrganisation,
            expected_q=extra_q & Q(creation_date__range=['2013-06-15', '2013-06-29']),
        )

        # Days = 1 -------------------------------------------------------------
        chart_one_day = create_chart(1)
        x_one_day, y_one_day = chart_one_day.fetch(user)
        self.assertEqual(len(y_one_day), 30)
        self.assertEqual(y_one_day[0][0],  1)
        self.assertEqual(y_one_day[1][0],  0)
        self.assertEqual(y_one_day[12][0], 0)
        self.assertEqual(y_one_day[13][0], 1)
        self.assertEqual(y_one_day[14][0], 1)
        self.assertEqual(y_one_day[15][0], 1)
        self.assertEqual(y_one_day[16][0], 0)
        self.assertEqual(y_one_day[29][0], 1)

    def test_fetch__date_range__aggregate(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)

        days = 10
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name=f'Minimum of capital by creation date (period of {days} days)',
            abscissa_cell_value='creation_date',
            abscissa_type=ReportChart.Group.RANGE, abscissa_parameter=str(days),
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_cell_key='regular_field-capital',
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='Orga1', creation_date=date(2013, 6, 22), capital=100)
        create_orga(name='Orga2', creation_date=date(2013, 6, 25), capital=200)
        create_orga(name='Orga3', creation_date=date(2013, 7,  5), capital=150)
        create_orga(name='Orga4', creation_date=date(2013, 7,  5), capital=1000, is_deleted=True)

        # ASC -----------------------------------------------------------------
        with override_language('fr'):
            x_asc, y_asc = chart.fetch(user)

        self.assertListEqual(
            ['22/06/2013-01/07/2013', '02/07/2013-11/07/2013'], x_asc,
        )

        def fmt(*dates):
            return '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(creation_date__range=dates),
            )

        self.assertListEqual([300, fmt('2013-06-22', '2013-07-01')], y_asc[0])
        self.assertListEqual([150, fmt('2013-07-02', '2013-07-11')], y_asc[1])

        # DESC ----------------------------------------------------------------
        with override_language('fr'):
            x_desc, y_desc = chart.fetch(order='DESC', user=user)

        self.assertListEqual(
            ['05/07/2013-26/06/2013', '25/06/2013-16/06/2013'], x_desc,
        )
        self.assertListEqual([150, fmt('2013-06-26', '2013-07-05')], y_desc[0])
        self.assertListEqual([300, fmt('2013-06-16', '2013-06-25')], y_desc[1])

    def test_fetch__date_range__asymmetrical(self):
        "Count, where the ASC values are different from the DESC ones."
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)

        def create_chart(days):
            return ReportChart.objects.create(
                # user=user,
                linked_report=report,
                name=f'Number of organisation created / {days} day(s)',
                abscissa_cell_value='creation_date',
                abscissa_type=ReportChart.Group.RANGE, abscissa_parameter=str(days),
                ordinate_type=ReportChart.Aggregator.COUNT,
            )

        chart = create_chart(15)
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='Target Orga1', creation_date=date(2013, 12, 21))
        create_orga(name='Target Orga2', creation_date=date(2013, 12, 26))
        create_orga(name='Target Orga3', creation_date=date(2013, 12, 31))
        create_orga(name='Target Orga4', creation_date=date(2014,  1,  3))
        create_orga(name='Target Orga5', creation_date=date(2014,  1,  5))
        create_orga(name='Target Orga6', creation_date=date(2014,  1,  7))

        # ASC -----------------------------------------------------------------
        with override_language('fr'):
            x_asc, y_asc = chart.fetch(user)

        self.assertListEqual(
            ['21/12/2013-04/01/2014', '05/01/2014-19/01/2014'], x_asc,
        )

        self.assertEqual(2, len(y_asc))

        def fmt(*dates):
            return '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(creation_date__range=[*dates]),
            )

        self.assertListEqual([4, fmt('2013-12-21', '2014-01-04')], y_asc[0])
        self.assertListEqual([2, fmt('2014-01-05', '2014-01-19')], y_asc[1])

        # DESC ----------------------------------------------------------------
        with override_language('fr'):
            x_desc, y_desc = chart.fetch(user=user, order='DESC', extra_q=None)

        self.assertListEqual(
            ['07/01/2014-24/12/2013', '23/12/2013-09/12/2013'], x_desc,
        )
        self.assertEqual(2, len(y_desc))
        self.assertListEqual([5, fmt('2013-12-24', '2014-01-07')], y_desc[0])
        self.assertListEqual([1, fmt('2013-12-09', '2013-12-23')], y_desc[1])

        # Days = 1 ------------------------------------------------------------
        chart_one_day = create_chart(1)
        x_one_day, y_one_day = chart_one_day.fetch(user)
        self.assertEqual(len(y_one_day), 18)
        self.assertEqual(y_one_day[0][0],  1)
        self.assertEqual(y_one_day[1][0],  0)
        self.assertEqual(y_one_day[4][0],  0)
        self.assertEqual(y_one_day[5][0],  1)
        self.assertEqual(y_one_day[6][0],  0)
        self.assertEqual(y_one_day[10][0], 1)
        self.assertEqual(y_one_day[13][0], 1)
        self.assertEqual(y_one_day[15][0], 1)
        self.assertEqual(y_one_day[17][0], 1)

        valid_days_indices = [0, 5, 10, 13, 15, 17]
        invalid_days_indices = [
            index for index in range(len(y_one_day)) if index not in valid_days_indices
        ]
        self.assertListEqual(
            [index for index, value in enumerate(y_one_day) if value[0] == 1],
            valid_days_indices,
        )
        self.assertListEqual(
            [index for index, value in enumerate(y_one_day) if value[0] == 0],
            invalid_days_indices,
        )

    def test_fetch__custom_date_range(self):
        user = self.login_as_root_and_get()

        cf = CustomField.objects.create(
            content_type=self.ct_orga, field_type=CustomField.DATE, name='First victory',
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        targaryens = create_orga(name='House Targaryen', capital=100)
        lannisters = create_orga(name='House Lannister', capital=1000)
        starks     = create_orga(name='House Stark')
        baratheons = create_orga(name='House Baratheon')
        tullies    = create_orga(name='House Tully')
        arryns     = create_orga(name='House Arryn')

        create_cf_value = partial(cf.value_class.objects.create, custom_field=cf)
        create_cf_value(entity=targaryens, value=date(year=2013, month=12, day=21))
        create_cf_value(entity=lannisters, value=date(year=2013, month=12, day=26))
        create_cf_value(entity=starks,     value=date(year=2013, month=12, day=31))
        create_cf_value(entity=baratheons, value=date(year=2014, month=1,  day=3))
        create_cf_value(entity=tullies,    value=date(year=2014, month=1,  day=5))
        create_cf_value(entity=arryns,     value=date(year=2014, month=1,  day=7))

        days = 15
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=self._create_simple_organisations_report(user=user),
            name=f'First victory / {days} day(s)',
            abscissa_cell_value=str(cf.uuid),
            abscissa_type=ReportChart.Group.CUSTOM_RANGE, abscissa_parameter=str(days),
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        with override_language('fr'):
            x_asc, y_asc = chart.fetch(user)

        self.assertListEqual(
            ['21/12/2013-04/01/2014', '05/01/2014-19/01/2014'], x_asc,
        )

        self.assertEqual(4, y_asc[0][0])
        self.assertListviewURL(
            url=y_asc[0][1],
            model=FakeOrganisation,
            expected_q=Q(
                customfielddate__custom_field=cf.id,
                customfielddate__value__range=['2013-12-21', '2014-01-04'],
            ),
        )

        self.assertEqual(2, y_asc[1][0])
        self.assertListviewURL(
            url=y_asc[1][1],
            model=FakeOrganisation,
            expected_q=Q(
                customfielddate__custom_field=cf.id,
                customfielddate__value__range=['2014-01-05', '2014-01-19'],
            ),
        )

    def test_fetch__custom_datetime_range(self):
        user = self.login_as_root_and_get()

        create_cf = partial(
            CustomField.objects.create,
            content_type=self.ct_orga,
            field_type=CustomField.DATETIME,
        )
        cf = create_cf(name='First victory')

        # This one is annoying because the values are in the same table,
        # so the query must be more complex to not retrieve them.
        cf2 = create_cf(name='First defeat')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        targaryens = create_orga(name='House Targaryen', capital=100)
        lannisters = create_orga(name='House Lannister', capital=1000)
        starks     = create_orga(name='House Stark')
        baratheons = create_orga(name='House Baratheon')
        tullies    = create_orga(name='House Tully')
        arryns     = create_orga(name='House Arryn')

        create_cf_value = partial(cf.value_class.objects.create, custom_field=cf)
        create_dt = partial(self.create_datetime, utc=True)
        create_cf_value(entity=targaryens, value=create_dt(year=2013, month=12, day=21))
        create_cf_value(entity=lannisters, value=create_dt(year=2013, month=12, day=26))
        create_cf_value(entity=starks,     value=create_dt(year=2013, month=12, day=31))
        create_cf_value(entity=baratheons, value=create_dt(year=2014, month=1,  day=3))
        create_cf_value(entity=tullies,    value=create_dt(year=2014, month=1,  day=5))
        create_cf_value(entity=arryns,     value=create_dt(year=2014, month=1,  day=7))

        create_cf_value(
            custom_field=cf2, entity=lannisters, value=create_dt(year=2013, month=11, day=6),
        )
        create_cf_value(
            custom_field=cf2, entity=starks, value=create_dt(year=2014, month=1, day=6),
        )

        days = 15
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=self._create_simple_organisations_report(user=user),
            name=f'First victory / {days} day(s)',
            abscissa_cell_value=str(cf.uuid),
            abscissa_type=ReportChart.Group.CUSTOM_RANGE, abscissa_parameter=str(days),
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        # ASC -----------------------------------------------------------------
        with override_language('fr'):
            x_asc, y_asc = chart.fetch(user)

        self.assertListEqual(
            ['21/12/2013-04/01/2014', '05/01/2014-19/01/2014'], x_asc,
        )

        self.assertEqual(4, y_asc[0][0])
        self.assertListviewURL(
            url=y_asc[0][1],
            model=FakeOrganisation,
            expected_q=Q(
                customfielddatetime__custom_field=cf.id,
                customfielddatetime__value__range=[
                    '2013-12-21T00:00:00.000000Z',
                    '2014-01-04T00:00:00.000000Z',
                ],
            ),
        )

        self.assertEqual(2, y_asc[1][0])
        self.assertListviewURL(
            url=y_asc[1][1],
            model=FakeOrganisation,
            expected_q=Q(
                customfielddatetime__custom_field=cf.id,
                customfielddatetime__value__range=[
                    '2014-01-05T00:00:00.000000Z',
                    '2014-01-19T00:00:00.000000Z',
                ],
            ),
        )

        # DESC ----------------------------------------------------------------
        with override_language('fr'):
            x_desc, y_desc = chart.fetch(order='DESC', user=user)

        self.assertListEqual(
            ['07/01/2014-24/12/2013', '23/12/2013-09/12/2013'], x_desc,
        )

        self.assertEqual(5, y_desc[0][0])
        self.assertListviewURL(
            url=y_desc[0][1],
            model=FakeOrganisation,
            expected_q=Q(
                customfielddatetime__custom_field=cf.id,
                customfielddatetime__value__range=[
                    '2013-12-24T00:00:00.000000Z',
                    '2014-01-07T00:00:00.000000Z',
                ],
            ),
        )

        self.assertEqual(1, y_desc[1][0])
        self.assertListviewURL(
            url=y_desc[1][1],
            model=FakeOrganisation,
            expected_q=Q(
                customfielddatetime__custom_field=cf.id,
                customfielddatetime__value__range=[
                    '2013-12-09T00:00:00.000000Z',
                    '2013-12-23T00:00:00.000000Z',
                ],
            ),
        )

        # Extra Q --------------------------------------------------------------
        extra_q = Q(capital__gt=500)

        with override_language('fr'):
            x_xtra, y_xtra = chart.fetch(user=user, extra_q=extra_q)

        self.assertListEqual(['26/12/2013-09/01/2014'], x_xtra)

        extra_value, extra_url = y_xtra[0]
        self.assertEqual(1, extra_value)
        self.assertListviewURL(
            url=extra_url,
            model=FakeOrganisation,
            expected_q=extra_q & Q(
                customfielddatetime__custom_field=cf.id,
                customfielddatetime__value__range=[
                    '2013-12-26T00:00:00.000000Z',
                    '2014-01-09T00:00:00.000000Z',
                ],
            ),
        )

    def test_fetch__custom_date_range__error(self):
        "Invalid CustomField."
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Useless name',
            abscissa_cell_value=str(uuid4()),  # <====
            abscissa_type=ReportChart.Group.CUSTOM_RANGE, abscissa_parameter='11',
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        x_asc, y_asc = chart.fetch(user)
        self.assertListEqual([], x_asc)
        self.assertListEqual([], y_asc)

    def test_fetch__day(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Average of capital by creation date (by day)',
            abscissa_cell_value='creation_date',
            abscissa_type=ReportChart.Group.DAY,
            ordinate_type=ReportChart.Aggregator.AVG,
            ordinate_cell_key='regular_field-capital',
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='House Stark',     creation_date=date(2013, 6, 22), capital=100)
        create_orga(name='House Lannister', creation_date=date(2013, 6, 22), capital=200)
        create_orga(name='Wildlings',       creation_date=date(2013, 7, 5),  capital=130)

        # ASC ------------------------------------------------------------------
        with override_language('fr'):
            x_asc, y_asc = chart.fetch(user=user)

        self.assertListEqual(['22/06/2013', '05/07/2013'], x_asc)

        self.assertEqual(150, y_asc[0][0])
        self.assertListviewURL(
            y_asc[0][1],
            FakeOrganisation,
            Q(
                creation_date__day=22,
                creation_date__month=6,
                creation_date__year=2013,
            ),
        )

        self.assertEqual(130, y_asc[1][0])

        # DESC -----------------------------------------------------------------
        with override_language('en'):
            self.assertListEqual(
                ['2013-07-05', '2013-06-22'],
                chart.fetch(user=user, order='DESC')[0],
            )

        # Extra Q --------------------------------------------------------------
        with override_language('fr'):
            x_xtra, y_xtra = chart.fetch(user=user, extra_q=Q(name__startswith='House'))

        self.assertListEqual(['22/06/2013'], x_xtra)

        self.assertEqual(150, y_xtra[0][0])
        self.assertListviewURL(
            y_xtra[0][1],
            FakeOrganisation,
            Q(
                name__startswith='House',
                creation_date__day=22,
                creation_date__month=6,
                creation_date__year=2013,
            ),
        )

    def test_fetch__customday_date(self):
        "Aggregate + DATE."
        user = self.login_as_root_and_get()
        cf = CustomField.objects.create(
            name='First victory', content_type=self.ct_orga, field_type=CustomField.DATE,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister', capital=100, description='Westeros')
        baratheons = create_orga(name='House Baratheon', capital=200, description='Westeros')
        targaryens = create_orga(name='House Targaryen', capital=130, description='Essos')

        create_cf_value = partial(cf.value_class.objects.create, custom_field=cf)
        create_date = partial(date, year=2013)
        create_cf_value(entity=lannisters, value=create_date(month=6, day=22))
        create_cf_value(entity=baratheons, value=create_date(month=6, day=22))
        create_cf_value(entity=targaryens, value=create_date(month=7, day=5))

        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Average of capital by 1rst victory (by day)',
            abscissa_cell_value=str(cf.uuid), abscissa_type=ReportChart.Group.CUSTOM_DAY,
            ordinate_type=ReportChart.Aggregator.AVG,
            ordinate_cell_key='regular_field-capital',
        )

        with override_language('fr'):
            x_asc, y_asc = chart.fetch(user)

        self.assertListEqual(['22/06/2013', '05/07/2013'], x_asc)
        self.assertEqual(150, y_asc[0][0])
        self.assertEqual(130, y_asc[1][0])

        url = y_asc[0][1]
        expected_q = Q(
            customfielddate__value__day=22,
            customfielddate__value__month=6,
            customfielddate__value__year=2013,
            customfielddate__custom_field=cf.id,
        )
        self.assertListviewURL(url=url, model=FakeOrganisation, expected_q=expected_q)

    def test_fetch__customday__datetime(self):
        "Aggregate + DATETIME."
        user = self.login_as_root_and_get()
        create_cf_dt = partial(
            CustomField.objects.create,
            content_type=self.ct_orga, field_type=CustomField.DATETIME,
        )
        cf = create_cf_dt(name='First victory')

        # This one is annoying because the values are in the same table
        # so the query must be more complex to not retrieve them
        cf2 = create_cf_dt(name='First defeat')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister', capital=100, description='Westeros')
        baratheons = create_orga(name='House Baratheon', capital=200, description='Westeros')
        targaryens = create_orga(name='House Targaryen', capital=130, description='Essos')

        create_cf_value = partial(cf.value_class.objects.create, custom_field=cf)
        create_dt = partial(self.create_datetime, utc=True, year=2013)
        create_cf_value(entity=lannisters, value=create_dt(month=6, day=22))
        create_cf_value(entity=baratheons, value=create_dt(month=6, day=22))
        create_cf_value(entity=targaryens, value=create_dt(month=7, day=5))

        create_cf_value(custom_field=cf2, entity=lannisters, value=create_dt(month=7, day=6))
        create_cf_value(custom_field=cf2, entity=lannisters, value=create_dt(month=7, day=5))

        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Average of capital by 1rst victory (by day)',
            abscissa_cell_value=str(cf.uuid), abscissa_type=ReportChart.Group.CUSTOM_DAY,
            ordinate_type=ReportChart.Aggregator.AVG,
            ordinate_cell_key='regular_field-capital',
        )

        # ASC -----------------------------------------------------------------
        with override_language('fr'):
            x_asc, y_asc = chart.fetch(user)

        self.assertListEqual(['22/06/2013', '05/07/2013'], x_asc)
        self.assertEqual(150, y_asc[0][0])
        self.assertEqual(130, y_asc[1][0])

        url = y_asc[0][1]
        expected_q = Q(
            customfielddatetime__value__day=22,
            customfielddatetime__value__month=6,
            customfielddatetime__value__year=2013,
            customfielddatetime__custom_field=cf.id,
        )
        self.assertListviewURL(url=url, model=FakeOrganisation, expected_q=expected_q)

        # DESC ----------------------------------------------------------------
        with override_language('fr'):
            self.assertListEqual(
                ['05/07/2013', '22/06/2013'],
                chart.fetch(user=user, order='DESC')[0],
            )

        # ASC -----------------------------------------------------------------
        extra_q = Q(description='Westeros')

        with override_language('en'):
            x_xtra, y_xtra = chart.fetch(user=user, extra_q=extra_q)

        self.assertListEqual(['2013-06-22'], x_xtra)

        xtra_value, xtra_url = y_xtra[0]
        self.assertEqual(150, xtra_value)
        self.assertListviewURL(
            url=xtra_url,
            model=FakeOrganisation,
            expected_q=extra_q & expected_q,
        )

    def test_fetch__customday__error(self):
        "Invalid CustomField."
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Average of capital by creation date (by day)',
            abscissa_cell_value=str(uuid4()),  # <====
            abscissa_type=ReportChart.Group.CUSTOM_DAY,
            ordinate_type=ReportChart.Aggregator.AVG,
            ordinate_cell_key='regular_field-capital',
        )

        x_asc, y_asc = chart.fetch(user=user)
        self.assertListEqual([], x_asc)
        self.assertListEqual([], y_asc)

        hand = chart.hand
        self.assertEqual('??', hand.verbose_abscissa)
        self.assertEqual(
            _('the custom field does not exist any more.'), hand.abscissa_error,
        )

    def test_fetch__month(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Number of orgas by creation date (period of 1 month)',
            abscissa_cell_value='creation_date', abscissa_type=ReportChart.Group.MONTH,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='Orga1', creation_date=date(2013, 6, 22))
        create_orga(name='Orga2', creation_date=date(2013, 6, 25))
        create_orga(name='Orga3', creation_date=date(2013, 8, 5))

        # ASC -----------------------------------------------------------------
        with override_language('fr'):
            x_asc, y_asc = chart.fetch(user=user)

        self.assertEqual(['06/2013', '08/2013'], x_asc)

        self.assertEqual(2, y_asc[0][0])
        self.assertListviewURL(
            y_asc[0][1],
            FakeOrganisation,
            Q(creation_date__month=6, creation_date__year=2013),
        )

        self.assertEqual(1, y_asc[1][0])

        # DESC ----------------------------------------------------------------
        with override_language('en'):
            self.assertListEqual(
                ['2013-08', '2013-06'],
                chart.fetch(user=user, order='DESC')[0],
            )

    def test_fetch__custommonth_date(self):
        "Count."
        user = self.login_as_root_and_get()

        cf = CustomField.objects.create(
            content_type=self.ct_orga, name='First victory', field_type=CustomField.DATE,
        )
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister', capital=1000)
        baratheons = create_orga(name='House Baratheon', capital=100)
        targaryens = create_orga(name='House Targaryen')

        create_cf_value = partial(cf.value_class.objects.create, custom_field=cf)
        create_date = partial(date, year=2013)
        create_cf_value(entity=lannisters, value=create_date(month=6, day=22))
        create_cf_value(entity=baratheons, value=create_date(month=6, day=25))
        create_cf_value(entity=targaryens, value=create_date(month=8, day=5))

        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Number of houses by 1rst victory (period of 1 month)',
            abscissa_cell_value=str(cf.uuid), abscissa_type=ReportChart.Group.CUSTOM_MONTH,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        with override_language('fr'):
            x_asc, y_asc = chart.fetch(user=user)

        self.assertListEqual(['06/2013', '08/2013'], x_asc)

        value0, url0 = y_asc[0]
        self.assertEqual(2, value0)

        expected_q = Q(
            customfielddate__custom_field=cf.id,
            customfielddate__value__month=6,
            customfielddate__value__year=2013,
        )
        self.assertListviewURL(
            url=url0,
            model=FakeOrganisation,
            expected_q=expected_q,
        )

    def test_fetch__custommonth_datetime(self):
        user = self.login_as_root_and_get()

        cf = CustomField.objects.create(
            content_type=self.ct_orga, name='First victory', field_type=CustomField.DATETIME,
        )
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister', capital=1000)
        baratheons = create_orga(name='House Baratheon', capital=100)
        targaryens = create_orga(name='House Targaryen')

        create_cf_value = partial(cf.value_class.objects.create, custom_field=cf)
        create_dt = partial(self.create_datetime, utc=True, year=2013)
        create_cf_value(entity=lannisters, value=create_dt(month=6, day=22))
        create_cf_value(entity=baratheons, value=create_dt(month=6, day=25))
        create_cf_value(entity=targaryens, value=create_dt(month=8, day=5))

        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Number of houses by 1rst victory (period of 1 month)',
            abscissa_cell_value=str(cf.uuid), abscissa_type=ReportChart.Group.CUSTOM_MONTH,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        with override_language('fr'):
            x_asc, y_asc = chart.fetch(user=user)

        self.assertListEqual(['06/2013', '08/2013'], x_asc)

        value0, url0 = y_asc[0]
        self.assertEqual(2, value0)

        expected_q = Q(
            customfielddatetime__custom_field=cf.id,
            customfielddatetime__value__month=6,
            customfielddatetime__value__year=2013,
        )
        self.assertListviewURL(
            url=url0,
            model=FakeOrganisation,
            expected_q=expected_q,
        )

        # Extra Q --------------------------------------------------------------
        extra_q = Q(capital__gt=200)

        with override_language('en'):
            x_xtra, y_xtra = chart.fetch(user=user, extra_q=extra_q)

        self.assertListEqual(['2013-06'], x_xtra)

        extra_value, extra_url = y_xtra[0]
        self.assertEqual(1, extra_value)
        self.assertListviewURL(
            url=extra_url,
            model=FakeOrganisation,
            expected_q=extra_q & expected_q,
        )

    def test_fetch__year__count(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Number of orgas by creation date (period of 1 year)',
            abscissa_cell_value='creation_date', abscissa_type=ReportChart.Group.YEAR,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='Orga1', creation_date=date(2013, 6, 22))
        create_orga(name='Orga2', creation_date=date(2013, 7, 25))
        create_orga(name='Orga3', creation_date=date(2014, 8,  5))

        # ASC -----------------------------------------------------------------
        with override_language('en'):
            x_asc, y_asc = chart.fetch(user)

        self.assertEqual(['2013', '2014'], x_asc)

        def fmt(year):
            return '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(creation_date__year=year),
            )

        self.assertListEqual([2, fmt(2013)], y_asc[0])
        self.assertListEqual([1, fmt(2014)], y_asc[1])

        # DESC ----------------------------------------------------------------
        with override_language('en'):
            x_desc, y_desc = chart.fetch(order='DESC', user=user)

        self.assertListEqual(['2014', '2013'], x_desc)
        self.assertListEqual([1, fmt(2014)], y_desc[0])
        self.assertListEqual([2, fmt(2013)], y_desc[1])

    def test_fetch__year__custom_field(self):
        "Aggregate ordinate with custom field."
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister', creation_date=date(2013, 6, 22))
        starks     = create_orga(name='House Stark',     creation_date=date(2013, 7, 25))
        baratheons = create_orga(name='House Baratheon', creation_date=date(2014, 8,  5))
        tullies    = create_orga(name='House Tully',     creation_date=date(2016, 8,  5))
        create_orga(name='House Targaryen', creation_date=date(2015, 8, 5))

        cf = CustomField.objects.create(
            content_type=self.ct_orga, name='Vine', field_type=CustomField.FLOAT,
        )

        create_cfval = partial(cf.value_class.objects.create, custom_field=cf)
        create_cfval(entity=lannisters, value='20.2')
        create_cfval(entity=starks,     value='50.5')
        create_cfval(entity=baratheons, value='100.0')
        create_cfval(entity=tullies,    value='0.0')

        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Sum of vine by creation date (period of 1 year)',
            abscissa_cell_value='creation_date', abscissa_type=ReportChart.Group.YEAR,
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_cell_key=f'custom_field-{cf.uuid}',
        )

        x_asc, y_asc = chart.fetch(user)
        self.assertListEqual(['2013', '2014', '2016'], x_asc)

        def fmt(year):
            return '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(creation_date__year=year),
            )

        self.assertListEqual([Decimal('70.70'), fmt(2013)], y_asc[0])
        self.assertListEqual([Decimal('100'),   fmt(2014)], y_asc[1])
        self.assertListEqual([0,                fmt(2016)], y_asc[2])

    def test_fetch__year__invalid_field(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Number of orgas by creation date (period of 1 year)',
            abscissa_cell_value='invalid',  # <=====
            abscissa_type=ReportChart.Group.YEAR,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        x_asc, y_asc = chart.fetch(user)
        self.assertListEqual([], x_asc)
        self.assertListEqual([], y_asc)

        hand = chart.hand
        self.assertEqual('??', hand.verbose_abscissa)
        self.assertEqual(_('the field does not exist any more.'), hand.abscissa_error)

    def test_fetch__year__customfields_dictinct(self):
        "Entity type with several CustomFields with the same type (bugfix)."
        user = self.login_as_root_and_get()

        create_cf = partial(
            CustomField.objects.create,
            content_type=self.ct_orga, field_type=CustomField.INT,
        )
        cf1 = create_cf(name='Gold')
        cf2 = create_cf(name='Famous swords')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(
            name='House Lannister', creation_date=date(year=2013, month=6, day=22),
        )
        starks = create_orga(
            name='House Stark',     creation_date=date(year=2013, month=7, day=25),
        )
        baratheons = create_orga(
            name='House Baratheon', creation_date=date(year=2014, month=8, day=5),
        )
        targaryens = create_orga(
            name='House Targaryen', creation_date=date(year=2015, month=9, day=6),
        )

        create_cf_value1 = partial(cf1.value_class.objects.create, custom_field=cf1)
        create_cf_value1(entity=lannisters, value=1000)
        create_cf_value1(entity=starks,     value=100)
        create_cf_value1(entity=baratheons, value=500)

        create_cf_value2 = partial(cf2.value_class.objects.create, custom_field=cf2)
        create_cf_value2(entity=lannisters, value=3)
        create_cf_value2(entity=starks,     value=12)
        create_cf_value2(entity=targaryens, value=1)

        report = self._create_simple_organisations_report(user=user)
        chart1 = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Sum of gold by creation date (period of 1 year)',
            abscissa_cell_value='creation_date', abscissa_type=ReportChart.Group.YEAR,
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_cell_key=f'custom_field-{cf1.uuid}',
        )

        x_asc1, y_asc1 = chart1.fetch(user)
        self.assertListEqual(['2013', '2014'], x_asc1)

        def fmt(year):
            return '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(creation_date__year=year),
            )

        self.assertListEqual([1100, fmt(2013)], y_asc1[0])
        self.assertListEqual([500,  fmt(2014)], y_asc1[1])

        # ---
        chart2 = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Average of gold by creation date (period of 1 year)',
            abscissa_cell_value='creation_date', abscissa_type=ReportChart.Group.YEAR,
            ordinate_type=ReportChart.Aggregator.AVG,
            ordinate_cell_key=f'custom_field-{cf2.uuid}',
        )

        x_asc2, y_asc2 = chart2.fetch(user)
        self.assertListEqual(['2013', '2015'], x_asc2)
        self.assertListEqual([Decimal('7.5'), fmt(2013)], y_asc2[0])
        self.assertListEqual([1,              fmt(2015)], y_asc2[1])

    def test_fetch__cutomfields_on_x_n_y(self):
        "Graphs with CustomFields on abscissa & ordinate."
        user = self.login_as_root_and_get()

        create_cf = partial(CustomField.objects.create, content_type=self.ct_orga)
        cf_x = create_cf(name='Birthday', field_type=CustomField.DATETIME)
        cf_y = create_cf(name='Gold',     field_type=CustomField.INT)

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister')
        starks     = create_orga(name='House Stark')
        baratheons = create_orga(name='House Baratheon')
        targaryens = create_orga(name='House Targaryen')

        create_dt = partial(self.create_datetime, utc=True)
        create_cf_value_x = partial(cf_x.value_class.objects.create, custom_field=cf_x)
        create_cf_value_x(entity=lannisters, value=create_dt(year=2013, month=6, day=22))
        create_cf_value_x(entity=starks,     value=create_dt(year=2013, month=7, day=25))
        create_cf_value_x(entity=baratheons, value=create_dt(year=2014, month=8, day=5))
        create_cf_value_x(entity=targaryens, value=create_dt(year=2015, month=9, day=12))

        create_cf_value_y = partial(cf_y.value_class.objects.create, custom_field=cf_y)
        create_cf_value_y(entity=lannisters, value=1000)
        create_cf_value_y(entity=starks,     value=100)
        create_cf_value_y(entity=baratheons, value=500)

        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Sum of gold by birthday (period of 1 year)',
            abscissa_cell_value=str(cf_x.uuid), abscissa_type=ReportChart.Group.CUSTOM_YEAR,
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_cell_key=f'custom_field-{cf_y.uuid}',
        )

        x_asc, y_asc = chart.fetch(user)
        self.assertListEqual(['2013', '2014'], x_asc)

        def fmt(year):
            return '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(
                    customfielddatetime__custom_field=cf_x.id,
                    customfielddatetime__value__year=year,
                ),
            )

        self.assertListEqual([1100, fmt(2013)], y_asc[0])
        self.assertListEqual([500,  fmt(2014)], y_asc[1])

    def test_fetch__customyear__date(self):
        user = self.login_as_root_and_get()

        cf = CustomField.objects.create(
            content_type=self.ct_orga, name='First victory', field_type=CustomField.DATE,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister', capital=1000)
        baratheons = create_orga(name='House Baratheon', capital=100)
        targaryens = create_orga(name='House Targaryen')

        create_cf_value = partial(cf.value_class.objects.create, custom_field=cf)
        create_cf_value(entity=lannisters, value=date(year=2013, month=6, day=22))
        create_cf_value(entity=baratheons, value=date(year=2013, month=7, day=25))
        create_cf_value(entity=targaryens, value=date(year=2014, month=8, day=5))

        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Number of house by 1rst victory (period of 1 year)',
            abscissa_cell_value=str(cf.uuid), abscissa_type=ReportChart.Group.CUSTOM_YEAR,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        with override_language('en'):
            x_asc, y_asc = chart.fetch(user=user)

        self.assertListEqual(['2013', '2014'], x_asc)

        value0, url0 = y_asc[0]
        self.assertEqual(2, value0)

        expected_q = Q(
            customfielddate__custom_field=cf.id,
            customfielddate__value__year=2013,
        )
        self.assertListviewURL(url=url0, model=FakeOrganisation, expected_q=expected_q)

    def test_fetch__customyear__datetime(self):
        user = self.login_as_root_and_get()

        cf = CustomField.objects.create(
            content_type=self.ct_orga, name='First victory', field_type=CustomField.DATETIME,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister', capital=1000)
        baratheons = create_orga(name='House Baratheon', capital=100)
        targaryens = create_orga(name='House Targaryen')

        create_cf_value = partial(cf.value_class.objects.create, custom_field=cf)
        create_dt = partial(self.create_datetime, utc=True)
        create_cf_value(entity=lannisters, value=create_dt(year=2013, month=6, day=22))
        create_cf_value(entity=baratheons, value=create_dt(year=2013, month=7, day=25))
        create_cf_value(entity=targaryens, value=create_dt(year=2014, month=8, day=5))

        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Number of house by 1rst victory (period of 1 year)',
            abscissa_cell_value=str(cf.uuid), abscissa_type=ReportChart.Group.CUSTOM_YEAR,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        # with self.settings(USE_L10N=False, DATE_INPUT_FORMATS=['%Y/%m/%d']):
        with override_language('fr'):
            x_asc, y_asc = chart.fetch(user=user)

        self.assertListEqual(['2013', '2014'], x_asc)

        value0, url0 = y_asc[0]
        self.assertEqual(2, value0)

        expected_q = Q(
            customfielddatetime__custom_field=cf.id,
            customfielddatetime__value__year=2013,
        )
        self.assertListviewURL(
            url=url0,
            model=FakeOrganisation,
            expected_q=expected_q,
        )

        # Extra q --------------------------------------------------------------
        extra_q = Q(capital__gt=200)

        with override_language('en'):
            x_xtra, y_xtra = chart.fetch(user=user, extra_q=extra_q)

        self.assertListEqual(['2013'], x_xtra)

        extra_value, extra_url = y_xtra[0]
        self.assertEqual(1, extra_value)
        self.assertListviewURL(
            url=extra_url,
            model=FakeOrganisation,
            expected_q=extra_q & expected_q,
        )

    def test_fetch__relation__count(self):
        user = self.login_as_root_and_get()
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister')
        starks     = create_orga(name='House Stark')

        create_contact = partial(FakeContact.objects.create, user=user)
        tyrion = create_contact(first_name='Tyrion', last_name='Lannister')
        ned    = create_contact(first_name='Eddard', last_name='Stark')
        aria   = create_contact(first_name='Aria',   last_name='Stark')
        jon    = create_contact(first_name='Jon',    last_name='Snow')

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Not bastard', FakeContact, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator=operators.IEQUALS,
                    values=[tyrion.last_name, ned.last_name],
                ),
            ],
        )

        rtype_id = fake_constants.FAKE_REL_SUB_EMPLOYED_BY
        create_rel = partial(
            Relation.objects.create,
            user=user, type_id=rtype_id,
        )
        create_rel(subject_entity=tyrion, object_entity=lannisters)
        create_rel(subject_entity=ned,    object_entity=starks)
        create_rel(subject_entity=aria,   object_entity=starks)
        create_rel(subject_entity=jon,    object_entity=starks)

        report = self._create_simple_contacts_report(user=user, efilter=efilter)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Number of employees',
            abscissa_cell_value=rtype_id,
            abscissa_type=ReportChart.Group.RELATION,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        # ASC -----------------------------------------------------------------
        x_asc, y_asc = chart.fetch(user=user)
        self.assertEqual([str(lannisters), str(starks)], x_asc)

        fmt = '/tests/contacts?q_filter={}&filter=test-filter'.format
        self.assertListEqual(
            [
                1,
                fmt(self._serialize_qfilter(
                    relations__type_id=rtype_id, relations__object_entity_id=lannisters.id,
                ))
            ],
            y_asc[0],
        )
        self.assertListEqual(
            [
                2,
                fmt(self._serialize_qfilter(
                    relations__type_id=rtype_id, relations__object_entity_id=starks.id,
                ))
            ],
            y_asc[1],
        )  # Not 3, because of the filter

        # DESC ----------------------------------------------------------------
        x_desc, y_desc = chart.fetch(order='DESC', user=user)
        self.assertEqual(x_asc, x_desc)
        self.assertEqual(y_asc, y_desc)

        # extra Q --------------------------------------------------------------
        extra_q = Q(first_name__startswith='Ar')
        x_xtra, y_xtra = chart.fetch(user=user, extra_q=extra_q)

        xtra_value, xtra_url = y_xtra[x_xtra.index(str(starks))]
        self.assertEqual(1, xtra_value)
        self.assertListviewURL(
            url=xtra_url,
            model=FakeContact,
            expected_q=extra_q & Q(
                relations__type_id=rtype_id, relations__object_entity_id=starks.id,
            ),
            expected_efilter_id=efilter.id,
        )

    def test_fetch__relation__aggregate(self):
        user = self.login_as_root_and_get()
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister', capital=100)
        starks     = create_orga(name='House Stark',     capital=50)
        tullies    = create_orga(name='House Tully',     capital=40)

        create_contact = partial(FakeContact.objects.create, user=user)
        tywin = create_contact(first_name='Tywin',  last_name='Lannister')
        ned   = create_contact(first_name='Eddard', last_name='Stark')

        rtype = RelationType.objects.builder(
            id='reports-subject_obeys', predicate='obeys to', models=[FakeOrganisation],
        ).symmetric(
            id='reports-object_commands', predicate='commands', models=[FakeContact],
        ).get_or_create()[0]

        create_rel = partial(Relation.objects.create, user=user, type=rtype)
        create_rel(subject_entity=lannisters, object_entity=tywin)
        create_rel(subject_entity=starks,     object_entity=ned)
        create_rel(subject_entity=tullies,    object_entity=ned)

        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Capital by lords',
            abscissa_cell_value=rtype.id,
            abscissa_type=ReportChart.Group.RELATION,
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_cell_key='regular_field-capital',
        )

        # ASC -----------------------------------------------------------------
        x_asc, y_asc = chart.fetch(user)
        self.assertEqual([str(ned), str(tywin)], x_asc)

        fmt = '/tests/organisations?q_filter={}'.format
        self.assertListEqual(
            [
                100,
                fmt(self._serialize_qfilter(
                    relations__type_id=rtype.id, relations__object_entity_id=tywin.id,
                ))
            ],
            y_asc[1],
        )
        self.assertListEqual(
            [
                90,
                fmt(self._serialize_qfilter(
                    relations__type_id=rtype.id, relations__object_entity_id=ned.id,
                ))
            ],
            y_asc[0],
        )

        # DESC ----------------------------------------------------------------
        x_desc, y_desc = chart.fetch(order='DESC', user=user)
        self.assertEqual(x_asc, x_desc)
        self.assertEqual(y_asc, y_desc)

    def test_fetch__relation__customfield(self):
        "Aggregate ordinate with custom field."
        user = self.login_as_root_and_get()

        create_cf = CustomField.objects.create
        cf = create_cf(
            content_type=self.ct_contact, name='HP', field_type=CustomField.INT,
        )
        create_cf(
            content_type=self.ct_contact, name='Title', field_type=CustomField.ENUM,
        )  # Can not perform aggregates
        create_cf(
            content_type=self.ct_orga, name='Gold', field_type=CustomField.INT,
        )  # Bad CT

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister')
        starks     = create_orga(name='House Stark')

        create_contact = partial(FakeContact.objects.create, user=user)
        ned    = create_contact(first_name='Eddard', last_name='Stark')
        robb   = create_contact(first_name='Robb',   last_name='Stark')
        jaime  = create_contact(first_name='Jaime',  last_name='Lannister')
        tyrion = create_contact(first_name='Tyrion', last_name='Lannister')

        rtype_id = fake_constants.FAKE_REL_SUB_EMPLOYED_BY
        create_rel = partial(Relation.objects.create, user=user, type_id=rtype_id)
        create_rel(subject_entity=ned,    object_entity=starks)
        create_rel(subject_entity=robb,   object_entity=starks)
        create_rel(subject_entity=jaime,  object_entity=lannisters)
        create_rel(subject_entity=tyrion, object_entity=lannisters)

        create_cfval = partial(CustomFieldInteger.objects.create, custom_field=cf)
        create_cfval(entity=ned,    value=500)
        create_cfval(entity=robb,   value=300)
        create_cfval(entity=jaime,  value=400)
        create_cfval(entity=tyrion, value=200)

        report = self._create_simple_contacts_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Contacts HP by house',
            abscissa_cell_value=rtype_id, abscissa_type=ReportChart.Group.RELATION,
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_cell_key=f'custom_field-{cf.uuid}',
        )

        x_asc, y_asc = chart.fetch(user)
        self.assertListEqual([str(lannisters), str(starks)], x_asc)

        fmt = '/tests/contacts?q_filter={}'.format
        self.assertListEqual(
            [
                600,
                fmt(self._serialize_qfilter(
                    relations__type_id=rtype_id, relations__object_entity_id=lannisters.id,
                ))
            ],
            y_asc[0],  # lannisters
        )
        self.assertListEqual(
            [
                800,
                fmt(self._serialize_qfilter(
                    relations__type_id=rtype_id, relations__object_entity_id=starks.id,
                ))
            ],
            y_asc[1],
        )

    def test_fetch__relation__invalid_rtype(self):
        "Invalid RelationType."
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Average of capital by creation date (by day)',
            abscissa_cell_value='invalidrtype',  # <====
            abscissa_type=ReportChart.Group.RELATION,
            ordinate_type=ReportChart.Aggregator.AVG,
            ordinate_cell_key='regular_field-capital',
        )

        x_asc, y_asc = chart.fetch(user)
        self.assertListEqual([], x_asc)
        self.assertListEqual([], y_asc)

        hand = chart.hand
        self.assertEqual('??', hand.verbose_abscissa)
        self.assertEqual(
            _('the relationship type does not exist any more.'), hand.abscissa_error,
        )

    def test_fetch__customfk__error(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_contacts_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Contacts by title',
            abscissa_cell_value=str(uuid4()),  # <=========
            abscissa_type=ReportChart.Group.CUSTOM_FK,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        with self.assertNoException():
            x_asc, y_asc = chart.fetch(user)

        self.assertListEqual([], x_asc)
        self.assertListEqual([], y_asc)

        hand = chart.hand
        self.assertEqual('??', hand.verbose_abscissa)
        self.assertEqual(
            _('the custom field does not exist any more.'), hand.abscissa_error,
        )

    def test_fetch__customfk__count(self):
        user = self.login_as_root_and_get()
        cf = CustomField.objects.create(
            content_type=self.ct_contact, name='Title', field_type=CustomField.ENUM,
        )
        create_enum_value = partial(CustomFieldEnumValue.objects.create, custom_field=cf)
        hand = create_enum_value(value='Hand')
        lord = create_enum_value(value='Lord')

        create_contact = partial(FakeContact.objects.create, user=user, last_name='Stark')
        ned  = create_contact(first_name='Eddard')
        robb = create_contact(first_name='Robb')
        bran = create_contact(first_name='Bran')
        create_contact(first_name='Aria')

        create_enum = partial(CustomFieldEnum.objects.create, custom_field=cf)
        create_enum(entity=ned,  value=hand)
        create_enum(entity=robb, value=lord)
        create_enum(entity=bran, value=lord)

        report = self._create_simple_contacts_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Contacts by title',
            abscissa_cell_value=str(cf.uuid), abscissa_type=ReportChart.Group.CUSTOM_FK,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        with self.assertNoException():
            x_asc, y_asc = chart.fetch(user)

        self.assertListEqual([hand.value, lord.value], x_asc)

        def fmt(val):
            return '/tests/contacts?q_filter={}'.format(
                self._serialize_qfilter(customfieldenum__value=val),
            )

        self.assertListEqual([1, fmt(hand.id)], y_asc[0])
        self.assertListEqual([2, fmt(lord.id)], y_asc[1])

        # DESC -----------------------------------------------------------------
        x_desc, y_desc = chart.fetch(order='DESC', user=user)
        self.assertListEqual([*reversed(x_asc)], x_desc)
        self.assertListEqual([*reversed(y_asc)], y_desc)

        # Extra Q --------------------------------------------------------------
        extra_q = Q(first_name__startswith='B')
        x_xtra, y_xtra = chart.fetch(user=user, extra_q=extra_q)
        self.assertListEqual([hand.value, lord.value], x_xtra)

        extra_value, extra_url = y_xtra[1]
        self.assertEqual(1, extra_value)
        self.assertListviewURL(
            url=extra_url,
            model=FakeContact,
            expected_q=extra_q & Q(customfieldenum__value=lord.id),
        )

    def test_fetch__customfk__aggregate(self):
        user = self.login_as_root_and_get()
        cf = CustomField.objects.create(
            content_type=self.ct_orga, name='Policy', field_type=CustomField.ENUM,
        )
        create_enum_value = partial(CustomFieldEnumValue.objects.create, custom_field=cf)
        fight     = create_enum_value(value='Fight')
        smartness = create_enum_value(value='Smartness')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        starks     = create_orga(name='Starks',     capital=30)
        baratheons = create_orga(name='Baratheon',  capital=60)
        lannisters = create_orga(name='Lannisters', capital=100)

        create_enum = partial(CustomFieldEnum.objects.create, custom_field=cf)
        create_enum(entity=starks,     value=fight)
        create_enum(entity=baratheons, value=fight)
        create_enum(entity=lannisters, value=smartness)

        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Capital by policy',
            abscissa_cell_value=str(cf.uuid), abscissa_type=ReportChart.Group.CUSTOM_FK,
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_cell_key='regular_field-capital',
        )

        self.assertEqual(cf.name, chart.hand.verbose_abscissa)

        with self.assertNoException():
            x_asc, y_asc = chart.fetch(user)

        self.assertEqual([fight.value, smartness.value], x_asc)

        def fmt(val):
            return '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(customfieldenum__value=val),
            )

        self.assertListEqual([90,  fmt(fight.id)],     y_asc[0])
        self.assertListEqual([100, fmt(smartness.id)], y_asc[1])

        # DESC ---------------------------------------------------------------
        x_desc, y_desc = chart.fetch(order='DESC', user=user)
        self.assertListEqual([*reversed(x_asc)], x_desc)
        self.assertListEqual([*reversed(y_asc)], y_desc)

    def test_fetch__customfk__distinct(self):
        """Entity type with several CustomFields with the same type
        + custom-field ENUM for aggregation (bugfix).
        """
        user = self.login_as_root_and_get()

        create_cf = partial(CustomField.objects.create, content_type=self.ct_orga)
        cf_int1 = create_cf(name='Gold',          field_type=CustomField.INT)
        cf_int2 = create_cf(name='Famous swords', field_type=CustomField.INT)
        cf_enum = create_cf(name='Army type',     field_type=CustomField.ENUM)

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister')
        starks     = create_orga(name='House Stark')
        baratheons = create_orga(name='House Baratheon')
        targaryens = create_orga(name='House Targaryen')

        create_cf_value1 = partial(cf_int1.value_class.objects.create, custom_field=cf_int1)
        create_cf_value1(entity=lannisters, value=1000)
        create_cf_value1(entity=starks,     value=100)
        create_cf_value1(entity=baratheons, value=500)

        create_cf_value2 = partial(cf_int2.value_class.objects.create, custom_field=cf_int2)
        create_cf_value2(entity=lannisters, value=3)
        create_cf_value2(entity=starks,     value=12)
        create_cf_value2(entity=targaryens, value=1)

        create_enum_value = partial(CustomFieldEnumValue.objects.create, custom_field=cf_enum)
        soldiers = create_enum_value(value='Soldiers')
        knights = create_enum_value(value='Knights')
        dragons = create_enum_value(value='Dragons')

        create_enum = partial(CustomFieldEnum.objects.create, custom_field=cf_enum)
        create_enum(entity=starks,     value=soldiers)
        create_enum(entity=lannisters, value=soldiers)
        create_enum(entity=baratheons, value=knights)
        create_enum(entity=targaryens, value=dragons)

        report = self._create_simple_organisations_report(user=user)
        chart1 = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Sum of gold by type',
            abscissa_cell_value=str(cf_enum.uuid), abscissa_type=ReportChart.Group.CUSTOM_FK,
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_cell_key=f'custom_field-{cf_int1.uuid}',
        )

        x_asc1, y_asc1 = chart1.fetch(user)
        self.assertListEqual([soldiers.value, knights.value, dragons.value], x_asc1)

        def fmt(enum_value):
            return '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(
                    # customfieldenum__custom_field=cf_enum.id, ??
                    customfieldenum__value=enum_value.id,
                ),
            )

        self.assertListEqual([1100, fmt(soldiers)], y_asc1[0])
        self.assertListEqual([500,  fmt(knights)],  y_asc1[1])

        # ---
        chart2 = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Average of gold by type',
            abscissa_cell_value=str(cf_enum.uuid), abscissa_type=ReportChart.Group.CUSTOM_FK,
            ordinate_type=ReportChart.Aggregator.AVG,
            ordinate_cell_key=f'custom_field-{cf_int2.uuid}',
        )

        x_asc2, y_asc2 = chart2.fetch(user)
        self.assertListEqual([soldiers.value, knights.value, dragons.value], x_asc2)
        self.assertListEqual([Decimal('7.5'), fmt(soldiers)], y_asc2[0])
        self.assertListEqual([0,              fmt(knights)],  y_asc2[1])
        self.assertListEqual([1,              fmt(dragons)],  y_asc2[2])

    def test_delete_chart_instance(self):
        "No related Brick location."
        user = self.login_as_root_and_get()

        chart1 = self._create_documents_chart(user=user)
        chart2 = self._create_documents_chart(user=user)

        ibci1 = SimpleChartFetcher(chart=chart1).create_brick_config_item()
        ibci2 = SimpleChartFetcher(chart=chart2).create_brick_config_item()

        chart1.delete()
        self.assertDoesNotExist(chart1)
        self.assertDoesNotExist(ibci1)
        self.assertStillExists(chart2)
        self.assertStillExists(ibci2)

    def test_delete_chart_instance__used(self):
        "There are Brick locations => cannot delete."
        user = self.login_as_root_and_get()
        chart = self._create_documents_chart(user=user)
        ibci = SimpleChartFetcher(chart=chart).create_brick_config_item()

        brick_id = ibci.brick_id
        bdl = BrickDetailviewLocation.objects.create_if_needed(
            brick=brick_id,
            order=1,
            zone=BrickDetailviewLocation.RIGHT,
            model=FakeContact,
        )
        bhl = BrickHomeLocation.objects.create(brick_id=brick_id, order=1)

        with self.assertRaises(ProtectedError):
            chart.delete()

        self.assertStillExists(chart)
        self.assertStillExists(ibci)
        self.assertStillExists(bdl)
        self.assertStillExists(bhl)

    def bench_big_fetch_using_count(self):
        """
        Little benchmark to see how the 'group by' report queries behave with
        bigger data-sets where there is a visible difference between the old
        "manual group by's" and the new real sql ones.
        """
        import time
        from datetime import datetime

        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Number of organisation created by day',
            abscissa_cell_value='creation_date',
            abscissa_type=ReportChart.Group.RANGE, abscissa_parameter='1',
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        interval_day_count = 300
        entities_per_day = 5
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        for i in range(1, interval_day_count + 1):
            creation = datetime.strptime(f'{i} 2014', '%j %Y').strftime('%Y-%m-%d')
            for _j in range(entities_per_day):
                create_orga(name='Target Orga', creation_date=creation)

        start = time.clock()

        x, y = chart.fetch()

        print('Fetch took', 1000 * (time.clock() - start), 'ms')

        self.assertEqual(len(x), interval_day_count)
        self.assertEqual(len(y), interval_day_count)
        self.assertEqual(
            sum(value for value, _ in y),
            interval_day_count * entities_per_day,
        )

    def bench_big_fetch_using_sum(self):
        """
        Little benchmark to see how the 'group by' report queries behave with
        bigger data-sets where there is a visible difference between the old
        "manual group by's" and the new real sql ones.
        """
        import time
        from datetime import datetime

        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Sum of capital by creation date (period of 1 days)',
            abscissa_cell_value='creation_date',
            abscissa_type=ReportChart.Group.RANGE, abscissa_parameter='1',
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_cell_key='regular_field-capital',
        )

        interval_day_count = 300
        entities_per_day = 5
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        for i in range(1, interval_day_count + 1):
            creation = datetime.strptime(f'{i} 2014', '%j %Y').strftime('%Y-%m-%d')
            for _j in range(entities_per_day):
                create_orga(name='Target Orga', creation_date=creation, capital=100)

        start = time.clock()

        x, y = chart.fetch()

        print('Fetch took', 1000 * (time.clock() - start), 'ms')

        self.assertEqual(len(x), interval_day_count)
        self.assertEqual(len(y), interval_day_count)
        self.assertEqual(
            sum(value for value, _ in y),
            interval_day_count * entities_per_day * 100
        )

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

    def test_clone_report(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_organisations_report(user=user)
        chart = ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='capital per month of creation',
            plot_name='barchart',
            abscissa_cell_value='created', abscissa_type=ReportChart.Group.MONTH,
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_cell_key='regular_field-capital',
        )

        cloned_report = self.clone(report)
        cloned_chart = self.get_alone_element(
            ReportChart.objects.filter(linked_report=cloned_report)
        )
        self.assertNotEqual(chart.id, cloned_chart.id)
        self.assertEqual(chart.name,  cloned_chart.name)

        self.assertEqual(user, cloned_chart.user)

        self.assertEqual(chart.abscissa_cell_value, cloned_chart.abscissa_cell_value)
        self.assertEqual(chart.abscissa_type,       cloned_chart.abscissa_type)
        self.assertEqual(chart.abscissa_parameter,  cloned_chart.abscissa_parameter)

        self.assertEqual(chart.ordinate_type,     cloned_chart.ordinate_type)
        self.assertEqual(chart.ordinate_cell_key, cloned_chart.ordinate_cell_key)

        self.assertEqual(chart.plot_name, cloned_chart.plot_name)

    # def test_clone_report__method(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #     report = self._create_simple_organisations_report(user=user)
    #     rgraph = ReportChart.objects.create(
    #         user=user, linked_report=report,
    #         name='capital per month of creation',
    #         chart='barchart',
    #         abscissa_cell_value='created', abscissa_type=ReportChart.Group.MONTH,
    #         ordinate_type=ReportChart.Aggregator.SUM,
    #         ordinate_cell_key='regular_field-capital',
    #     )
    #
    #     cloned_report = report.clone()
    #
    #     cloned_rgraph = self.get_alone_element(
    #         ReportChart.objects.filter(linked_report=cloned_report)
    #     )
    #     self.assertNotEqual(rgraph.id, cloned_rgraph.id)
    #     self.assertEqual(rgraph.name,  cloned_rgraph.name)
    #
    #     self.assertEqual(rgraph.abscissa_cell_value, cloned_rgraph.abscissa_cell_value)
    #     self.assertEqual(rgraph.abscissa_type,       cloned_rgraph.abscissa_type)
    #     self.assertEqual(rgraph.abscissa_parameter,  cloned_rgraph.abscissa_parameter)
    #
    #     self.assertEqual(rgraph.ordinate_type,     cloned_rgraph.ordinate_type)
    #     self.assertEqual(rgraph.ordinate_cell_key, cloned_rgraph.ordinate_cell_key)
    #
    #     self.assertEqual(rgraph.chart, cloned_rgraph.chart)

    def test_credentials(self):
        "Filter retrieved entities with permission."
        user = self.login_as_standard(allowed_apps=['creme_core', 'reports'])
        self.add_credentials(user.role, own=['VIEW', 'CHANGE'])

        other_user = self.get_root_user()
        report = self._create_simple_organisations_report(user=user)

        create_orga = FakeOrganisation.objects.create
        create_orga(name='O#1', user=user)
        create_orga(name='O#2', user=user, capital=100)
        create_orga(name='O#3', user=user, capital=200)
        # Cannot be seen => should not be used to compute aggregate
        create_orga(name='O#4', user=other_user, capital=300)

        name = 'Max capital per user'
        self.assertNoFormError(self.client.post(
            self._build_add_chart_url(report),
            data={
                'user': user.id,
                'name': name,
                'plot_name': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeOrganisation._meta.get_field('user'),
                    chart_type=ReportChart.Group.FK,
                ),
                'ordinate': self.formfield_value_ordinate(
                    aggr_id=ReportChart.Aggregator.MAX,
                    cell=EntityCellRegularField.build(FakeOrganisation, 'capital'),
                ),
            })
        )
        chart = self.get_object_or_fail(ReportChart, linked_report=report, name=name)
        x_data, y_data = chart.fetch(order='ASC', user=user)

        users = sorted(get_user_model().objects.all(), key=str)
        self.assertListEqual([str(u) for u in users], x_data)

        def get_user_index(user_id):
            index = next((i for i, u in enumerate(users) if user_id == u.id), None)
            self.assertIsNotNone(index)
            return index

        self.assertEqual(200, y_data[get_user_index(user.id)][0])
        self.assertEqual(0,   y_data[get_user_index(other_user.id)][0])  # Not 300
