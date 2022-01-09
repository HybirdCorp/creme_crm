# -*- coding: utf-8 -*-

from datetime import date
from decimal import Decimal
from functools import partial
from json import loads as json_load
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import ProtectedError
from django.db.models.query_utils import Q
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext
from parameterized import parameterized

from creme.creme_core.auth.entity_credentials import EntityCredentials
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
    FakeInvoice,
    FakeOrganisation,
    FakePosition,
    FakeSector,
    FieldsConfig,
    InstanceBrickConfigItem,
    Relation,
    RelationType,
    SetCredentials,
)
from creme.creme_core.tests import fake_constants
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.queries import QSerializer

from ..bricks import InstanceBricksInfoBrick, ReportGraphBrick
# from ..constants import (
#     RGA_AVG,
#     RGA_COUNT,
#     RGA_MAX,
#     RGA_MIN,
#     RGA_SUM,
#     RGF_FK,
#     RGF_NOLINK,
#     RGF_RELATION,
#     RGT_CUSTOM_DAY,
#     RGT_CUSTOM_FK,
#     RGT_CUSTOM_MONTH,
#     RGT_CUSTOM_RANGE,
#     RGT_CUSTOM_YEAR,
#     RGT_DAY,
#     RGT_FK,
#     RGT_MONTH,
#     RGT_RANGE,
#     RGT_RELATION,
#     RGT_YEAR,
# )
from ..constants import RGF_FK, RGF_NOLINK, RGF_RELATION
from ..core.graph import AbscissaInfo, ListViewURLBuilder, OrdinateInfo
from ..core.graph.fetcher import (
    RegularFieldLinkedGraphFetcher,
    SimpleGraphFetcher,
)
from .base import (
    AxisFieldsMixin,
    BaseReportsTestCase,
    Report,
    ReportGraph,
    skipIfCustomReport,
    skipIfCustomRGraph,
)
from .fake_models import FakeReportsDocument, FakeReportsFolder


@skipIfCustomReport
@skipIfCustomRGraph
class ReportGraphTestCase(BrickTestCaseMixin,
                          AxisFieldsMixin,
                          BaseReportsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ct_invoice = ContentType.objects.get_for_model(FakeInvoice)
        cls.qfilter_serializer = QSerializer()

    def assertURL(self, url, model, expected_q=None, expected_efilter_id=None):
        parsed_url = urlparse(url)
        self.assertTrue(model.get_lv_absolute_url(), parsed_url.path)

        GET_params = parse_qs(parsed_url.query)

        # '?q_filter=' ------
        if expected_q is None:
            self.assertNotIn('q_filter', GET_params)
        else:
            qfilters = GET_params.pop('q_filter', ())
            self.assertEqual(1, len(qfilters))

            with self.assertNoException():
                qfilter = json_load(qfilters[0])

            expected_qfilter = json_load(self.qfilter_serializer.dumps(expected_q))
            self.assertIsInstance(qfilter, dict)
            self.assertEqual(2, len(qfilter))
            self.assertEqual(expected_qfilter['op'], qfilter['op'])
            # TODO: improve for nested Q...
            self.assertCountEqual(expected_qfilter['val'], qfilter['val'])

        # '&filter=' ------
        if expected_efilter_id is None:
            self.assertNotIn('filter', GET_params)
        else:
            self.assertEqual([expected_efilter_id], GET_params.pop('filter', None))

        self.assertFalse(GET_params)  # All valid parameters have been removed

    @staticmethod
    def _build_add_graph_url(report):
        return reverse('reports__create_graph', args=(report.id,))

    @staticmethod
    def _build_add_brick_url(rgraph):
        return reverse('reports__create_instance_brick', args=(rgraph.id,))

    @staticmethod
    def _build_edit_url(rgraph):
        return reverse('reports__edit_graph', args=(rgraph.id,))

    @staticmethod
    def _builf_fetch_url(rgraph, order='ASC', chart=None, save_settings=None):
        uri = '{}?order={}'.format(reverse('reports__fetch_graph', args=(rgraph.id,)), order)

        if chart is not None:
            uri += f'&chart={chart}'

        if save_settings is not None:
            uri += f'&save_settings={save_settings}'

        return uri

    @staticmethod
    def _build_fetchfrombrick_url(ibi, entity, order='ASC', chart=None, save_settings=None):
        uri = '{}?order={}'.format(
            reverse('reports__fetch_graph_from_brick', args=(ibi.id, entity.id)),
            order,
        )

        if chart is not None:
            uri += f'&chart={chart}'

        if save_settings is not None:
            uri += f'&save_settings={save_settings}'

        return uri

    # @staticmethod
    # def _build_graph_types_url(ct):
    #     return reverse('reports__graph_types', args=(ct.id,))

    def _create_invoice_report_n_graph(self, abscissa='issuing_date',
                                       # ordinate_type=RGA_SUM,
                                       ordinate_type=ReportGraph.Aggregator.SUM,
                                       ordinate_field='total_no_vat'):
        self.report = report = Report.objects.create(
            user=self.user,
            name='All invoices of the current year',
            ct=self.ct_invoice,
        )

        # TODO: we need a helper ReportGraph.create() ??
        return ReportGraph.objects.create(
            user=self.user,
            linked_report=report,
            name='Sum of current year invoices total without taxes / month',
            abscissa_cell_value=abscissa,
            # abscissa_type=RGT_MONTH,
            abscissa_type=ReportGraph.Group.MONTH,
            ordinate_type=ordinate_type,
            ordinate_cell_key=f'regular_field-{ordinate_field}',
        )

    # TODO: uncomment with ordered dict
    # def _serialize_qfilter(self, **kwargs):
    #     return self.qfilter_serializer.dumps(Q(**kwargs))
    def _serialize_qfilter(self, *qs, **kwargs):
        q = Q()
        for q_object in qs:
            q &= q_object

        if kwargs:
            q &= Q(**kwargs)

        return self.qfilter_serializer.dumps(q)

    def test_listview_URL_builder01(self):
        self.login()

        builder = ListViewURLBuilder(FakeContact)
        self.assertURL(builder(None), FakeContact)
        self.assertURL(builder({'id': 1}), FakeContact, expected_q=Q(id=1))

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Names', FakeContact, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IENDSWITH,
                    field_name='last_name', values=['Stark'],
                ),
            ],
        )

        builder = ListViewURLBuilder(FakeContact, efilter)
        self.assertURL(builder(None), FakeContact, expected_efilter_id='test-filter')
        self.assertURL(
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
        self.login()

        q = Q(first_name__endswith='a')
        builder = ListViewURLBuilder(FakeContact, common_q=q)
        self.assertURL(builder(None), FakeContact, expected_q=q)
        self.assertURL(builder({'id': 1}), FakeContact, expected_q=q & Q(id=1))

    def test_createview01(self):
        "Group.FK."
        user = self.login()
        report = self._create_simple_organisations_report()

        url = self._build_add_graph_url(report)
        context = self.assertGET200(url).context
        self.assertEqual(
            _('Create a graph for «{entity}»').format(entity=report),
            context.get('title'),
        )
        self.assertEqual(ReportGraph.save_label, context.get('submit_label'))

        name = 'My Graph #1'
        abscissa = 'sector'
        # gtype = RGT_FK
        gtype = ReportGraph.Group.FK
        chart = 'barchart'
        self.assertNoFormError(
            self.client.post(
                url,
                data={
                    'user': user.pk,  # TODO: report.user used instead ??
                    'name': name,

                    'abscissa': self.formfield_value_abscissa(
                        abscissa=FakeOrganisation._meta.get_field(abscissa),
                        graph_type=gtype,
                    ),

                    # 'ordinate': self.formfield_value_ordinate(aggr_id=RGA_COUNT),
                    'ordinate': self.formfield_value_ordinate(
                        aggr_id=ReportGraph.Aggregator.COUNT,
                    ),

                    'chart': chart,
                },
            )
        )

        rgraph = self.get_object_or_fail(ReportGraph, linked_report=report, name=name)
        self.assertEqual(user,      rgraph.user)
        self.assertEqual(abscissa,  rgraph.abscissa_cell_value)
        # self.assertEqual(RGA_COUNT, rgraph.ordinate_type)
        self.assertEqual(ReportGraph.Aggregator.COUNT, rgraph.ordinate_type)
        self.assertEqual('',        rgraph.ordinate_cell_key)
        self.assertEqual(gtype,     rgraph.abscissa_type)
        self.assertEqual(chart,     rgraph.chart)
        self.assertIsNone(rgraph.abscissa_parameter)
        self.assertIs(rgraph.asc,      True)

        hand = rgraph.hand
        self.assertEqual(_('Sector'), hand.verbose_abscissa)
        # self.assertEqual(_('Count'),  hand.verbose_ordinate)
        self.assertEqual(_('Count'),  hand.ordinate.verbose_name)
        self.assertIsNone(hand.abscissa_error)
        self.assertIsNone(hand.ordinate_error)

        abs_info = rgraph.abscissa_info
        self.assertIsInstance(abs_info, AbscissaInfo)
        self.assertEqual(gtype, abs_info.graph_type)
        self.assertIsNone(abs_info.parameter)
        self.assertEqual('regular_field-sector', abs_info.cell.key)

        # ------------------------------------------------------------
        response = self.assertGET200(rgraph.get_absolute_url())
        self.assertTemplateUsed(response, 'reports/view_graph.html')

        with self.assertNoException():
            chart_registry = response.context['report_charts']

        from ..report_chart_registry import report_chart_registry
        self.assertIs(chart_registry, report_chart_registry)

        # ------------------------------------------------------------
        response = self.assertGET200(self._builf_fetch_url(rgraph, 'ASC'))
        data = response.json()

        self.assertIsInstance(data, dict)
        self.assertEqual(2, len(data))

        sectors = FakeSector.objects.all()
        x_asc = data.get('x')
        self.assertEqual([s.title for s in sectors], x_asc)

        y_asc = data.get('y')
        self.assertIsList(y_asc, length=len(x_asc))
        self.assertListEqual(
            [
                0,
                '/tests/organisations?q_filter={}'.format(
                    self._serialize_qfilter(sector=sectors[0].id),
                ),
            ],
            y_asc[0],
        )

        # ------------------------------------------------------------
        self.assertGET200(self._builf_fetch_url(rgraph, 'DESC'))
        self.assertGET404(self._builf_fetch_url(rgraph, 'STUFF'))

    def test_createview02(self):
        "Ordinate with aggregate + Group.DAY."
        user = self.login()
        report = self._create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        ordinate = 'capital'
        # gtype = RGT_DAY
        gtype = ReportGraph.Group.DAY

        def post(**kwargs):
            return self.client.post(
                url,
                data={
                    'user': user.id,
                    'name': name,
                    'chart': 'barchart',
                    **kwargs
                },
            )

        response = post(
            abscissa=self.formfield_value_abscissa(
                abscissa=FakeOrganisation._meta.get_field('legal_form'),
                graph_type=gtype,
            ),
            ordinate=self.formfield_value_ordinate(
                # aggr_id=RGA_MAX,
                aggr_id=ReportGraph.Aggregator.MAX,
                cell=EntityCellRegularField.build(FakeOrganisation, 'name'),
            ),
        )
        self.assertEqual(200, response.status_code)
        self.assertFormError(
            response, 'form', 'abscissa',
            'This entity cell is not allowed.'
        )
        self.assertFormError(
            response, 'form', 'ordinate',
            'This entity cell is not allowed.'
        )

        # aggregate = RGA_MAX
        aggregate = ReportGraph.Aggregator.MAX
        abscissa = 'created'
        self.assertNoFormError(post(
            abscissa=self.formfield_value_abscissa(
                abscissa=FakeOrganisation._meta.get_field(abscissa),
                graph_type=gtype,
            ),
            ordinate=self.formfield_value_ordinate(
                aggr_id=aggregate,
                cell=EntityCellRegularField.build(FakeOrganisation, ordinate),
            ),
        ))

        rgraph = self.get_object_or_fail(ReportGraph, linked_report=report, name=name)
        self.assertEqual(user,      rgraph.user)
        self.assertEqual(abscissa,  rgraph.abscissa_cell_value)
        self.assertEqual(gtype,     rgraph.abscissa_type)
        self.assertIsNone(rgraph.abscissa_parameter)
        self.assertEqual(aggregate,                   rgraph.ordinate_type)
        self.assertEqual(f'regular_field-{ordinate}', rgraph.ordinate_cell_key)

        hand = rgraph.hand
        self.assertEqual(_('Creation date'), hand.verbose_abscissa)
        # self.assertEqual(
        #     f"{_('Capital')} - {_('Maximum')}",
        #     hand.verbose_ordinate
        # )
        self.assertEqual(_('Maximum'), hand.ordinate.verbose_name)
        self.assertEqual(_('Capital'), str(hand.ordinate.cell))

    def test_createview_with_relation(self):
        "Group.RELATION."
        user = self.login()
        report = self._create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        # gtype = RGT_RELATION
        gtype = ReportGraph.Group.RELATION

        rtype_id = fake_constants.FAKE_REL_OBJ_EMPLOYED_BY
        rtype = RelationType.objects.get(id=rtype_id)
        self.assertNoFormError(self.client.post(
            url,
            data={
                'user': user.pk,
                'name': name,
                'chart': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=rtype,
                    graph_type=gtype,
                ),

                # 'ordinate': self.formfield_value_ordinate(aggr_id=RGA_COUNT),
                'ordinate': self.formfield_value_ordinate(aggr_id=ReportGraph.Aggregator.COUNT),
            },
        ))

        rgraph = self.get_object_or_fail(ReportGraph, linked_report=report, name=name)
        self.assertEqual(user,      rgraph.user)
        self.assertEqual(rtype_id,  rgraph.abscissa_cell_value)
        # self.assertEqual(RGA_COUNT, rgraph.ordinate_type)
        self.assertEqual(ReportGraph.Aggregator.COUNT, rgraph.ordinate_type)
        self.assertEqual('',        rgraph.ordinate_cell_key)

        self.assertEqual('employs', rgraph.hand.verbose_abscissa)

    @parameterized.expand([
        # (RGT_MONTH,),
        (ReportGraph.Group.MONTH,),
        # (RGT_YEAR,),
        (ReportGraph.Group.YEAR,),
    ])
    def test_createview_with_date(self, gtype):
        user = self.login()
        report = self._create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        ordinate = 'capital'
        # aggregate = RGA_MIN
        aggregate = ReportGraph.Aggregator.MIN

        def post(abscissa_field, **kwargs):
            return self.client.post(
                url,
                data={
                    'user': self.user.pk,
                    'name': name,
                    'chart': 'barchart',

                    'abscissa': self.formfield_value_abscissa(
                        abscissa=FakeOrganisation._meta.get_field(abscissa_field),
                        graph_type=gtype,
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
            response, 'form', 'abscissa',
            'This entity cell is not allowed.'
        )

        abscissa = 'created'
        self.assertNoFormError(post(abscissa_field=abscissa))

        rgraph = self.get_object_or_fail(ReportGraph, linked_report=report, name=name)
        self.assertEqual(user, rgraph.user)
        self.assertEqual(abscissa,  rgraph.abscissa_cell_value)
        self.assertEqual(gtype, rgraph.abscissa_type)
        self.assertIsNone(rgraph.abscissa_parameter)
        self.assertEqual(aggregate,                   rgraph.ordinate_type)
        self.assertEqual(f'regular_field-{ordinate}', rgraph.ordinate_cell_key)

    def test_createview_with_range(self):
        "ReportGraph.Group.RANGE."
        user = self.login()
        report = self._create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        ordinate = 'capital'
        # gtype = RGT_RANGE
        gtype = ReportGraph.Group.RANGE

        # def post(abscissa_field, parameter='', aggr_id=RGA_MAX, **kwargs):
        def post(abscissa_field, parameter='', aggr_id=ReportGraph.Aggregator.MAX, **kwargs):
            return self.client.post(
                url,
                data={
                    'user': user.id,
                    'name': name,
                    'chart': 'barchart',

                    'abscissa': self.formfield_value_abscissa(
                        abscissa=FakeOrganisation._meta.get_field(abscissa_field),
                        graph_type=gtype,
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
            response, 'form', 'abscissa',
            'This entity cell is not allowed.'
        )

        # aggregate = RGA_AVG
        aggregate = ReportGraph.Aggregator.AVG
        abscissa = 'modified'
        days = '25'
        self.assertNoFormError(post(abscissa_field=abscissa, parameter=days, aggr_id=aggregate))

        rgraph = self.get_object_or_fail(ReportGraph, linked_report=report, name=name)
        self.assertEqual(user, rgraph.user)
        self.assertEqual(abscissa, rgraph.abscissa_cell_value)
        self.assertEqual(gtype,    rgraph.abscissa_type)
        self.assertEqual(days,     rgraph.abscissa_parameter)
        self.assertEqual(aggregate,                   rgraph.ordinate_type)
        self.assertEqual(f'regular_field-{ordinate}', rgraph.ordinate_cell_key)

    def test_createview_with_customfk(self):
        "ReportGraph.Group.CUSTOM_FK."
        user = self.login()
        cf_enum = CustomField.objects.create(
            content_type=self.ct_contact, name='Hair', field_type=CustomField.ENUM,
        )

        report = self._create_simple_contacts_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        # gtype = RGT_CUSTOM_FK
        gtype = ReportGraph.Group.CUSTOM_FK

        self.assertNoFormError(self.client.post(
            url,
            data={
                'user': user.pk,
                'name': name,
                'chart': 'barchart',
                'abscissa': self.formfield_value_abscissa(
                    abscissa=cf_enum,
                    graph_type=gtype,
                ),
                # 'ordinate': self.formfield_value_ordinate(aggr_id=RGA_COUNT),
                'ordinate': self.formfield_value_ordinate(aggr_id=ReportGraph.Aggregator.COUNT),
            },
        ))

        rgraph = self.get_object_or_fail(ReportGraph, linked_report=report, name=name)
        self.assertEqual(user,            rgraph.user)
        self.assertEqual(str(cf_enum.id), rgraph.abscissa_cell_value)
        self.assertEqual(gtype,           rgraph.abscissa_type)

    @parameterized.expand([
        # (RGT_CUSTOM_DAY,),
        # (RGT_CUSTOM_MONTH,),
        # (RGT_CUSTOM_YEAR,),
        (ReportGraph.Group.CUSTOM_DAY,),
        (ReportGraph.Group.CUSTOM_MONTH,),
        (ReportGraph.Group.CUSTOM_YEAR,),
    ])
    def test_createview_with_customdatetime(self, gtype):
        user = self.login()

        cf_dt = CustomField.objects.create(
            content_type=self.ct_orga,
            name='First victory',
            field_type=CustomField.DATETIME,
        )

        report = self._create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'user': user.pk,
                'name': name,
                'chart': 'barchart',
                'abscissa': self.formfield_value_abscissa(
                    abscissa=cf_dt,
                    graph_type=gtype,
                ),
                # 'ordinate': self.formfield_value_ordinate(aggr_id=RGA_COUNT),
                'ordinate': self.formfield_value_ordinate(aggr_id=ReportGraph.Aggregator.COUNT),
            },
        ))

        rgraph = self.get_object_or_fail(ReportGraph, linked_report=report, name=name)
        self.assertEqual(user,          rgraph.user)
        self.assertEqual(str(cf_dt.id), rgraph.abscissa_cell_value)
        self.assertEqual(gtype,         rgraph.abscissa_type)
        # self.assertEqual(RGA_COUNT,     rgraph.ordinate_type)
        self.assertEqual(ReportGraph.Aggregator.COUNT, rgraph.ordinate_type)
        self.assertEqual('',            rgraph.ordinate_cell_key)

        self.assertEqual(cf_dt.name, rgraph.hand.verbose_abscissa)

    @parameterized.expand([
        (ReportGraph.Group.CUSTOM_DAY,),
        (ReportGraph.Group.CUSTOM_MONTH,),
        (ReportGraph.Group.CUSTOM_YEAR,),
    ])
    # def test_createview_with_customdate(self):
    def test_createview_with_customdate(self, gtype):
        user = self.login()

        cf_date = CustomField.objects.create(
            content_type=self.ct_orga,
            name='First victory',
            field_type=CustomField.DATE,
        )

        report = self._create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'user': user.pk,
                'name': name,
                'chart': 'barchart',
                'abscissa': self.formfield_value_abscissa(
                    abscissa=cf_date,
                    graph_type=gtype,
                ),
                'ordinate': self.formfield_value_ordinate(aggr_id=ReportGraph.Aggregator.COUNT),
            },
        ))

        rgraph = self.get_object_or_fail(ReportGraph, linked_report=report, name=name)
        self.assertEqual(user,                         rgraph.user)
        self.assertEqual(str(cf_date.id),              rgraph.abscissa_cell_value)
        self.assertEqual(gtype,                        rgraph.abscissa_type)
        self.assertEqual(ReportGraph.Aggregator.COUNT, rgraph.ordinate_type)
        self.assertEqual('',                           rgraph.ordinate_cell_key)

        self.assertEqual(cf_date.name, rgraph.hand.verbose_abscissa)

    def test_createview_with_customrange(self):
        "ReportGraph.Group.CUSTOM_RANGE."
        user = self.login()

        cf_dt = CustomField.objects.create(
            content_type=self.ct_orga, name='First victory', field_type=CustomField.DATETIME,
        )

        report = self._create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        # gtype = RGT_CUSTOM_RANGE
        gtype = ReportGraph.Group.CUSTOM_RANGE

        days = '25'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'user': self.user.pk,
                'name': name,
                'chart': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=cf_dt,
                    graph_type=gtype,
                    parameter=days,
                ),
                # 'ordinate': self.formfield_value_ordinate(aggr_id=RGA_COUNT),
                'ordinate': self.formfield_value_ordinate(aggr_id=ReportGraph.Aggregator.COUNT),
            },
        ))

        rgraph = self.get_object_or_fail(ReportGraph, linked_report=report, name=name)
        self.assertEqual(user,          rgraph.user)
        self.assertEqual(str(cf_dt.id), rgraph.abscissa_cell_value)
        self.assertEqual(gtype,         rgraph.abscissa_type)
        self.assertEqual(days,          rgraph.abscissa_parameter)
        # self.assertEqual(RGA_COUNT,     rgraph.ordinate_type)
        self.assertEqual(ReportGraph.Aggregator.COUNT, rgraph.ordinate_type)
        self.assertEqual('',            rgraph.ordinate_cell_key)

        self.assertEqual(cf_dt.name, rgraph.hand.verbose_abscissa)

    def test_createview_bad_related(self):
        "Not related to a Report => error."
        user = self.login()
        orga = FakeOrganisation.objects.create(user=user, name='House Stark')
        self.assertGET404(self._build_add_graph_url(orga))

    def test_createview_fieldsconfig(self):
        user = self.login()
        report = self._create_simple_organisations_report()

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
            self._build_add_graph_url(report),
            data={
                'user': user.pk,
                'name': 'My Graph #1',
                'chart': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeOrganisation._meta.get_field(hidden_fname1),
                    # graph_type=RGT_FK,
                    graph_type=ReportGraph.Group.FK,
                ),
                'ordinate': self.formfield_value_ordinate(
                    # aggr_id=RGA_SUM,
                    aggr_id=ReportGraph.Aggregator.SUM,
                    cell=EntityCellRegularField.build(FakeOrganisation, hidden_fname2),
                ),
            },
        )
        self.assertFormError(
            response, 'form', 'abscissa',
            'This entity cell is not allowed.'
        )
        self.assertFormError(
            response, 'form', 'ordinate',
            'This entity cell is not allowed.'
        )

    def test_abscissa_info(self):
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph(
            user=user, linked_report=report,
            name='Capital per month of creation',
            # ordinate_type=RGA_SUM,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key='regular_field-capital',
        )

        rgraph.abscissa_info = AbscissaInfo(
            # graph_type=RGT_FK,
            graph_type=ReportGraph.Group.FK,
            cell=EntityCellRegularField.build(FakeOrganisation, 'capital'),
        )
        self.assertEqual('capital',            rgraph.abscissa_cell_value)
        # self.assertEqual(RGT_FK, rgraph.abscissa_type)
        self.assertEqual(ReportGraph.Group.FK, rgraph.abscissa_type)
        self.assertIsNone(rgraph.abscissa_parameter)

        abs_info1 = rgraph.abscissa_info
        self.assertIsInstance(abs_info1, AbscissaInfo)
        # self.assertEqual(RGT_FK, abs_info1.graph_type)
        self.assertEqual(ReportGraph.Group.FK, abs_info1.graph_type)
        self.assertIsNone(abs_info1.parameter)
        self.assertEqual('regular_field-capital', abs_info1.cell.key)

        # ---
        rgraph.abscissa_info = AbscissaInfo(
            # graph_type=RGT_RANGE,
            graph_type=ReportGraph.Group.RANGE,
            cell=EntityCellRegularField.build(FakeOrganisation, 'created'),
            parameter='3',
        )
        self.assertEqual('created', rgraph.abscissa_cell_value)
        # self.assertEqual(RGT_RANGE, rgraph.abscissa_type)
        self.assertEqual(ReportGraph.Group.RANGE, rgraph.abscissa_type)
        self.assertEqual('3', rgraph.abscissa_parameter)

        abs_info2 = rgraph.abscissa_info
        # self.assertEqual(RGT_RANGE, abs_info2.graph_type)
        self.assertEqual(ReportGraph.Group.RANGE, abs_info2.graph_type)
        self.assertEqual('regular_field-created', abs_info2.cell.key)
        self.assertEqual('3', abs_info2.parameter)

    def test_ordinate_info01(self):
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph(
            user=user, linked_report=report,
            name='Capital per month of creation',
        )
        # aggr_id1 = RGA_MAX
        aggr_id1 = ReportGraph.Aggregator.MAX
        cell1 = EntityCellRegularField.build(FakeOrganisation, 'capital')
        rgraph.ordinate_info = OrdinateInfo(aggr_id=aggr_id1, cell=cell1)
        self.assertEqual(aggr_id1,  rgraph.ordinate_type)
        self.assertEqual(cell1.key, rgraph.ordinate_cell_key)

        ord_info1 = rgraph.ordinate_info
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
        # aggr_id2 = RGA_MIN
        aggr_id2 = ReportGraph.Aggregator.MIN
        rgraph.ordinate_info = OrdinateInfo(aggr_id=aggr_id2, cell=cell2)

        self.assertEqual(aggr_id2,  rgraph.ordinate_type)
        self.assertEqual(cell2.key, rgraph.ordinate_cell_key)

        ord_info2 = rgraph.ordinate_info
        self.assertEqual(aggr_id2,  ord_info2.aggr_id)
        self.assertEqual(cell2.key, ord_info2.cell.key)

        # ---
        # aggr_id3 = RGA_COUNT
        aggr_id3 = ReportGraph.Aggregator.COUNT
        rgraph.ordinate_info = OrdinateInfo(aggr_id=aggr_id3)

        self.assertEqual(aggr_id3, rgraph.ordinate_type)
        self.assertEqual('',       rgraph.ordinate_cell_key)

        ord_info3 = rgraph.ordinate_info
        self.assertEqual(aggr_id3,  ord_info3.aggr_id)
        self.assertIsNone(ord_info3.cell)

    def test_ordinate_info02(self):
        "Ignore FieldSConfig."
        user = self.login()
        hidden_fname = 'capital'
        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        report = self._create_simple_organisations_report()
        cell_key = f'regular_field-{hidden_fname}'
        # aggr_id = RGA_MAX
        aggr_id = ReportGraph.Aggregator.MAX
        rgraph = ReportGraph(
            user=user, linked_report=report,
            name='Max capital per month of creation',
            ordinate_type=aggr_id,
            ordinate_cell_key=cell_key,
        )

        ord_info = rgraph.ordinate_info
        self.assertIsInstance(ord_info, OrdinateInfo)
        self.assertEqual(aggr_id,  ord_info.aggr_id)
        self.assertEqual(cell_key, ord_info.cell.key)

    def test_editview01(self):
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Capital per month of creation',
            abscissa_cell_value='created',
            # abscissa_type=RGT_MONTH,
            abscissa_type=ReportGraph.Group.MONTH,
            # ordinate_type=RGA_SUM,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key='regular_field-capital',
        )

        url = self._build_edit_url(rgraph)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(
            _('Edit a graph for «{entity}»').format(entity=report),
            context.get('title'),
        )

        with self.assertNoException():
            abscissa_f = context['form'].fields['abscissa']

        self.assertSetEqual(
            {'regular_field-created'}, abscissa_f.not_hiddable_cell_keys,
        )

        name = 'Organisations per sector'
        abscissa = 'sector'
        # gtype = RGT_FK
        gtype = ReportGraph.Group.FK
        self.assertNoFormError(self.client.post(
            url,
            data={
                'user': user.pk,
                'name': name,
                'chart': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeOrganisation._meta.get_field(abscissa),
                    graph_type=gtype,
                ),
                # 'ordinate': self.formfield_value_ordinate(aggr_id=RGA_COUNT),
                'ordinate': self.formfield_value_ordinate(aggr_id=ReportGraph.Aggregator.COUNT),
            },
        ))

        rgraph = self.refresh(rgraph)
        self.assertEqual(name,     rgraph.name)
        self.assertEqual(abscissa, rgraph.abscissa_cell_value)
        # self.assertEqual(RGA_COUNT,  rgraph.ordinate_type)
        self.assertEqual(ReportGraph.Aggregator.COUNT, rgraph.ordinate_type)
        self.assertEqual(gtype,    rgraph.abscissa_type)
        self.assertIsNone(rgraph.abscissa_parameter)

    def test_editview02(self):
        "Another ContentType."
        user = self.login()
        rgraph = self._create_invoice_report_n_graph()
        url = self._build_edit_url(rgraph)
        response = self.assertGET200(url)

        with self.assertNoException():
            ordinate_f = response.context['form'].fields['ordinate']

        self.assertEqual(
            _(
                'If you use a field related to money, the entities should use the same '
                'currency or the result will be wrong. Concerned fields are : {}'
            ).format('{}, {}'.format(_('Total with VAT'), _('Total without VAT'))),
            ordinate_f.help_text
        )

        abscissa = 'created'
        # gtype = RGT_DAY
        gtype = ReportGraph.Group.DAY
        self.assertNoFormError(self.client.post(
            url,
            data={
                'user': user.pk,
                'name': rgraph.name,
                'chart': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeInvoice._meta.get_field(abscissa),
                    graph_type=gtype,
                ),
                'ordinate': self.formfield_value_ordinate(
                    # aggr_id=RGA_AVG,
                    aggr_id=ReportGraph.Aggregator.AVG,
                    cell=EntityCellRegularField.build(FakeInvoice, 'total_vat'),
                ),
            },
        ))

        rgraph = self.refresh(rgraph)
        self.assertEqual(abscissa, rgraph.abscissa_cell_value)
        self.assertEqual(gtype,    rgraph.abscissa_type)
        self.assertIsNone(rgraph.abscissa_parameter)
        # self.assertEqual(RGA_AVG,                   rgraph.ordinate_type)
        self.assertEqual(ReportGraph.Aggregator.AVG, rgraph.ordinate_type)
        self.assertEqual('regular_field-total_vat',  rgraph.ordinate_cell_key)

    def test_editview03(self):
        "With FieldsConfig."
        user = self.login()
        rgraph = self._create_invoice_report_n_graph(
            # ordinate_type=RGA_SUM,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_field='total_vat',
        )

        hidden_fname = 'total_no_vat'
        FieldsConfig.objects.create(
            content_type=FakeInvoice,
            descriptions=[
                (hidden_fname, {FieldsConfig.HIDDEN: True}),
            ],
        )

        response = self.assertPOST200(
            self._build_edit_url(rgraph),
            data={
                'user': user.pk,
                'name': rgraph.name,
                'chart': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeInvoice._meta.get_field('expiration_date'),
                    # graph_type=RGT_MONTH,
                    graph_type=ReportGraph.Group.MONTH,
                ),

                'ordinate': self.formfield_value_ordinate(
                    # aggr_id=RGA_AVG,
                    aggr_id=ReportGraph.Aggregator.AVG,
                    cell=EntityCellRegularField.build(FakeInvoice, hidden_fname),
                ),
            },
        )
        self.assertFormError(
            response, 'form', 'ordinate',
            'This entity cell is not allowed.'
        )

    def test_editview04(self):
        "With FieldsConfig: if fields are already selected => still proposed (abscissa)."
        self.login()
        hidden_fname = 'expiration_date'
        rgraph = self._create_invoice_report_n_graph(abscissa=hidden_fname)

        FieldsConfig.objects.create(
            content_type=FakeInvoice,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        response = self.client.post(
            self._build_edit_url(rgraph),
            data={
                'user':  rgraph.user.pk,
                'name':  rgraph.name,
                'chart': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeInvoice._meta.get_field(hidden_fname),
                    graph_type=rgraph.abscissa_type,
                ),
                'ordinate': self.formfield_value_ordinate(
                    # aggr_id=RGA_SUM,
                    aggr_id=ReportGraph.Aggregator.SUM,
                    cell=EntityCellRegularField.build(FakeInvoice, 'total_no_vat'),
                ),
            },
        )
        self.assertNoFormError(response)

        rgraph = self.refresh(rgraph)
        self.assertEqual(hidden_fname, rgraph.abscissa_cell_value)

        hand = rgraph.hand
        self.assertEqual(_('Expiration date'), hand.verbose_abscissa)
        self.assertEqual(
            _('this field should be hidden.'), hand.abscissa_error,
        )

    def test_editview05(self):
        "With FieldsConfig: if fields are already selected => still proposed (ordinate)."
        self.login()
        hidden_fname = 'total_no_vat'
        rgraph = self._create_invoice_report_n_graph(
            # ordinate_type=RGA_SUM,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_field=hidden_fname,
        )

        FieldsConfig.objects.create(
            content_type=FakeInvoice,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        response = self.client.post(
            self._build_edit_url(rgraph),
            data={
                'user':  rgraph.user.pk,
                'name':  rgraph.name,
                'chart': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeInvoice._meta.get_field(rgraph.abscissa_cell_value),
                    graph_type=rgraph.abscissa_type,
                ),

                'ordinate': self.formfield_value_ordinate(
                    aggr_id=rgraph.ordinate_type,
                    cell=EntityCellRegularField.build(FakeInvoice, hidden_fname),
                ),
            },
        )
        self.assertNoFormError(response)

    def test_editview06(self):
        "Custom field."
        user = self.login()
        cf = CustomField.objects.create(
            content_type=self.ct_orga,
            name='Country',
            field_type=CustomField.ENUM,
        )

        report = self._create_simple_organisations_report()

        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Number of clans per countries',
            # abscissa_type=RGT_CUSTOM_FK,
            abscissa_type=ReportGraph.Group.CUSTOM_FK,
            abscissa_cell_value=str(cf.id),
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        response = self.assertGET200(self._build_edit_url(rgraph))

        with self.assertNoException():
            abscissa_f = response.context['form'].fields['abscissa']

        self.assertSetEqual(
            {f'custom_field-{cf.id}'}, abscissa_f.not_hiddable_cell_keys,
        )

    def test_fetch_with_fk_01(self):
        "Count."
        user = self.login()
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

        report = self._create_simple_contacts_report(efilter=efilter)
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Contacts by position',
            # abscissa_cell_value='position', abscissa_type=RGT_FK,
            abscissa_cell_value='position', abscissa_type=ReportGraph.Group.FK,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch(user)

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
        x_desc, y_desc = rgraph.fetch(order='DESC', user=user)
        self.assertListEqual([*reversed(x_asc)], x_desc)
        self.assertListEqual([1, fmt(hand.id)], y_desc[x_desc.index(hand.title)])

        # Extra Q --------------------------------------------------------------
        extra_q = Q(first_name__startswith='B')
        x_xtra, y_xtra = rgraph.fetch(user=user, extra_q=extra_q)

        lord_count, lord_url = y_xtra[x_asc.index(lord.title)]
        self.assertEqual(1, lord_count)
        self.assertURL(
            url=lord_url, model=FakeOrganisation,
            expected_q=extra_q & Q(position=lord.id),
            expected_efilter_id=efilter.id,
        )

    def test_fetch_with_fk_02(self):
        "Aggregate."
        user = self.login()

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

        report = self._create_simple_organisations_report(efilter=efilter)
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Capital max by sector',
            # abscissa_cell_value='sector', abscissa_type=RGT_FK,
            abscissa_cell_value='sector', abscissa_type=ReportGraph.Group.FK,
            # ordinate_type=RGA_MAX,
            ordinate_type=ReportGraph.Aggregator.MAX,
            ordinate_cell_key='regular_field-capital',
        )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch(user)

        self.assertListEqual([*FakeSector.objects.values_list('title', flat=True)], x_asc)

        def fmt(pk):
            return '/tests/organisations?q_filter={}&filter=test-filter'.format(
                self._serialize_qfilter(sector=pk),
            )

        index = x_asc.index
        self.assertListEqual([100,  fmt(war.id)],   y_asc[index(war.title)])
        self.assertListEqual([1000, fmt(trade.id)], y_asc[index(trade.title)])
        self.assertListEqual([0,    fmt(peace.id)], y_asc[index(peace.title)])

    def test_fetch_with_fk_03(self):
        "Aggregate ordinate with custom field."
        user = self.login()

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

        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Max soldiers by sector',
            # abscissa_cell_value='sector', abscissa_type=RGT_FK,
            abscissa_cell_value='sector', abscissa_type=ReportGraph.Group.FK,
            # ordinate_type=RGA_MAX,
            ordinate_type=ReportGraph.Aggregator.MAX,
            ordinate_cell_key=f'custom_field-{cf.id}',
        )

        hand = rgraph.hand
        # self.assertEqual('{} - {}'.format(cf, _('Maximum')), hand.verbose_ordinate)
        self.assertEqual(_('Maximum'), hand.ordinate.verbose_name)
        self.assertEqual(cf.name,      str(hand.ordinate.cell))

        x_asc, y_asc = rgraph.fetch(user)
        self.assertListEqual([*FakeSector.objects.values_list('title', flat=True)], x_asc)

        index = x_asc.index

        def fmt(pk):
            return '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(sector=pk),
            )

        self.assertListEqual([400, fmt(war.id)],   y_asc[index(war.title)])
        self.assertListEqual([500, fmt(trade.id)], y_asc[index(trade.title)])
        self.assertListEqual([0,   fmt(peace.id)], y_asc[index(peace.title)])

    def test_fetch_with_fk_04(self):
        "Aggregate ordinate with invalid field."
        user = self.login()
        rgraph = ReportGraph.objects.create(
            user=user,
            linked_report=self._create_simple_organisations_report(),
            name='Max soldiers by sector',
            # abscissa_cell_value='sector', abscissa_type=RGT_FK,
            abscissa_cell_value='sector', abscissa_type=ReportGraph.Group.FK,
            # ordinate_type=RGA_MAX,
            ordinate_type=ReportGraph.Aggregator.MAX,
            ordinate_cell_key='regular_field-unknown',  # <=====
        )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch(user)

        sectors = FakeSector.objects.all()
        self.assertEqual([s.title for s in sectors], x_asc)
        self.assertListEqual(
            [
                0,
                '/tests/organisations?q_filter={}'.format(
                    self._serialize_qfilter(sector=sectors[0].id),
                ),
            ],
            y_asc[0]
        )
        self.assertEqual(
            _('the field does not exist any more.'), rgraph.hand.ordinate_error,
        )

    def test_fetch_with_fk_05(self):
        "Aggregate ordinate with invalid aggregate."
        user = self.login()
        rgraph = ReportGraph.objects.create(
            user=user,
            linked_report=self._create_simple_organisations_report(),
            name='Max soldiers by sector',
            # abscissa_cell_value='sector', abscissa_type=RGT_FK,
            abscissa_cell_value='sector', abscissa_type=ReportGraph.Group.FK,
            ordinate_type='invalid',  # <=====
            ordinate_cell_key='regular_field-capital',
        )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch(user)

        sectors = FakeSector.objects.all()
        self.assertEqual([s.title for s in sectors], x_asc)
        self.assertListEqual(
            [
                0,
                '/tests/organisations?q_filter={}'.format(
                    self._serialize_qfilter(sector=sectors[0].id),
                ),
            ],
            y_asc[0]
        )
        self.assertEqual(
            _('the aggregation function is invalid.'), rgraph.hand.ordinate_error
        )

    def test_fetch_with_fk_06(self):
        "Aggregate ordinate with invalid custom field."
        user = self.login()
        rgraph = ReportGraph.objects.create(
            user=user,
            linked_report=self._create_simple_organisations_report(),
            name='Max soldiers by sector',
            # abscissa_cell_value='sector', abscissa_type=RGT_FK,
            abscissa_cell_value='sector', abscissa_type=ReportGraph.Group.FK,
            # ordinate_type=RGA_MAX,
            ordinate_type=ReportGraph.Aggregator.MAX,
            ordinate_cell_key='custom_field-1000',  # <=====
        )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch(user)

        sectors = FakeSector.objects.all()
        self.assertListEqual([s.title for s in sectors], x_asc)
        self.assertListEqual(
            [
                0,
                '/tests/organisations?q_filter={}'.format(
                    self._serialize_qfilter(sector=sectors[0].id),
                ),
            ],
            y_asc[0]
        )
        self.assertEqual(
            _('the field does not exist any more.'),
            rgraph.hand.ordinate_error
        )

    def test_fetch_with_fk_07(self):
        "Abscissa field on Users has a limit_choices_to which excludes staff users."
        user = self.login(is_staff=True)
        other_user = self.other_user

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

        report = self._create_simple_contacts_report(efilter=efilter)
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Contacts count by User',
            # abscissa_cell_value='user', abscissa_type=RGT_FK,
            abscissa_cell_value='user', abscissa_type=ReportGraph.Group.FK,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch(user)

        self.assertIn(str(other_user), x_asc)
        self.assertNotIn(str(user), x_asc)  # <===

    def test_fetch_with_fk_08(self):
        "Abscissa field on ContentType enumerates only entities types."
        user = self.login()

        get_ct = ContentType.objects.get_for_model
        report = Report.objects.create(
            user=self.user, name='Report on Reports', ct=get_ct(Report),
        )

        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Report count by CTypes',
            # abscissa_cell_value='ct', abscissa_type=RGT_FK,
            abscissa_cell_value='ct', abscissa_type=ReportGraph.Group.FK,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch(user)

        self.assertIn(str(get_ct(FakeOrganisation)), x_asc)
        self.assertNotIn(str(get_ct(FakePosition)), x_asc)  # <===

    def test_fetch_with_fk_09(self):
        "Invalid field (not enumerable)."
        user = self.login()
        report = self._create_simple_contacts_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Contact count per address',
            # abscissa_cell_value='address', abscissa_type=RGT_FK,
            abscissa_cell_value='address', abscissa_type=ReportGraph.Group.FK,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        x_asc, y_asc = rgraph.fetch(user)
        self.assertListEqual([], x_asc)
        self.assertListEqual([], y_asc)

        hand = rgraph.hand
        self.assertEqual(_('Billing address'), hand.verbose_abscissa)
        self.assertEqual(
            _('this field cannot be used as abscissa.'), hand.abscissa_error
        )

    def test_fetch_with_date_range01(self):
        "Count."
        user = self.login()
        report = self._create_simple_organisations_report()

        def create_graph(days):
            return ReportGraph.objects.create(
                user=user, linked_report=report,
                name=f'Number of organisation created / {days} day(s)',
                abscissa_cell_value='creation_date',
                # abscissa_type=RGT_RANGE, abscissa_parameter=str(days),
                abscissa_type=ReportGraph.Group.RANGE, abscissa_parameter=str(days),
                # ordinate_type=RGA_COUNT,
                ordinate_type=ReportGraph.Aggregator.COUNT,
            )

        rgraph = create_graph(15)
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='Target Orga1', creation_date='2013-06-01')
        create_orga(name='Target Orga2', creation_date='2013-06-05')
        create_orga(name='Target Orga3', creation_date='2013-06-14')
        create_orga(name='Target Orga4', creation_date='2013-06-15', capital=1000)
        create_orga(name='Target Orga5', creation_date='2013-06-16', capital=1100)
        create_orga(name='Target Orga6', creation_date='2013-06-30', capital=200)

        # ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch(user)
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
        x_desc, y_desc = rgraph.fetch(user=user, order='DESC')
        self.assertListEqual(
            ['30/06/2013-16/06/2013', '15/06/2013-01/06/2013'], x_desc,
        )
        self.assertListEqual([2, fmt('2013-06-16', '2013-06-30')], y_desc[0])
        self.assertListEqual([4, fmt('2013-06-01', '2013-06-15')], y_desc[1])

        # Extra q --------------------------------------------------------------
        extra_q = Q(capital__gt=200)
        x_xtra, y_xtra = rgraph.fetch(user=user, extra_q=extra_q)
        self.assertListEqual(
            ['15/06/2013-29/06/2013'], x_xtra,
        )

        extra_value, extra_url = y_xtra[0]
        self.assertEqual(2, extra_value)
        self.assertURL(
            url=extra_url,
            model=FakeOrganisation,
            expected_q=extra_q & Q(creation_date__range=['2013-06-15', '2013-06-29']),
        )

        # Days = 1 -------------------------------------------------------------
        rgraph_one_day = create_graph(1)
        x_one_day, y_one_day = rgraph_one_day.fetch(user)
        self.assertEqual(len(y_one_day), 30)
        self.assertEqual(y_one_day[0][0],  1)
        self.assertEqual(y_one_day[1][0],  0)
        self.assertEqual(y_one_day[12][0], 0)
        self.assertEqual(y_one_day[13][0], 1)
        self.assertEqual(y_one_day[14][0], 1)
        self.assertEqual(y_one_day[15][0], 1)
        self.assertEqual(y_one_day[16][0], 0)
        self.assertEqual(y_one_day[29][0], 1)

    def test_fetch_with_date_range02(self):
        "Aggregate."
        user = self.login()
        report = self._create_simple_organisations_report()

        days = 10
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name=f'Minimum of capital by creation date (period of {days} days)',
            abscissa_cell_value='creation_date',
            # abscissa_type=RGT_RANGE, abscissa_parameter=str(days),
            abscissa_type=ReportGraph.Group.RANGE, abscissa_parameter=str(days),
            # ordinate_type=RGA_SUM,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key='regular_field-capital',
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='Orga1', creation_date='2013-06-22', capital=100)
        create_orga(name='Orga2', creation_date='2013-06-25', capital=200)
        create_orga(name='Orga3', creation_date='2013-07-5',  capital=150)
        create_orga(name='Orga4', creation_date='2013-07-5',  capital=1000, is_deleted=True)

        # ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch(user)
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
        x_desc, y_desc = rgraph.fetch(order='DESC', user=user)
        self.assertListEqual(
            ['05/07/2013-26/06/2013', '25/06/2013-16/06/2013'], x_desc,
        )
        self.assertListEqual([150, fmt('2013-06-26', '2013-07-05')], y_desc[0])
        self.assertListEqual([300, fmt('2013-06-16', '2013-06-25')], y_desc[1])

    def test_fetch_with_asymmetrical_date_range01(self):
        "Count, where the ASC values are different from the DESC ones."
        user = self.login()
        report = self._create_simple_organisations_report()

        def create_graph(days):
            return ReportGraph.objects.create(
                user=user, linked_report=report,
                name=f'Number of organisation created / {days} day(s)',
                abscissa_cell_value='creation_date',
                # abscissa_type=RGT_RANGE, abscissa_parameter=str(days),
                abscissa_type=ReportGraph.Group.RANGE, abscissa_parameter=str(days),
                # ordinate_type=RGA_COUNT,
                ordinate_type=ReportGraph.Aggregator.COUNT,
            )

        rgraph = create_graph(15)
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='Target Orga1', creation_date='2013-12-21')
        create_orga(name='Target Orga2', creation_date='2013-12-26')
        create_orga(name='Target Orga3', creation_date='2013-12-31')
        create_orga(name='Target Orga4', creation_date='2014-01-03')
        create_orga(name='Target Orga5', creation_date='2014-01-05')
        create_orga(name='Target Orga6', creation_date='2014-01-07')

        # ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch(user)
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
        x_desc, y_desc = rgraph.fetch(user=user, order='DESC', extra_q=None)
        self.assertListEqual(
            ['07/01/2014-24/12/2013', '23/12/2013-09/12/2013'], x_desc,
        )
        self.assertEqual(2, len(y_desc))
        self.assertListEqual([5, fmt('2013-12-24', '2014-01-07')], y_desc[0])
        self.assertListEqual([1, fmt('2013-12-09', '2013-12-23')], y_desc[1])

        # Days = 1 ------------------------------------------------------------
        rgraph_one_day = create_graph(1)
        x_one_day, y_one_day = rgraph_one_day.fetch(user)
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

    def test_fetch_with_custom_date_range(self):
        "Count."
        user = self.login()

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
        rgraph = ReportGraph.objects.create(
            user=user,
            linked_report=self._create_simple_organisations_report(),
            name=f'First victory / {days} day(s)',
            abscissa_cell_value=cf.id,
            abscissa_type=ReportGraph.Group.CUSTOM_RANGE, abscissa_parameter=str(days),
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        x_asc, y_asc = rgraph.fetch(user)
        self.assertListEqual(
            ['21/12/2013-04/01/2014', '05/01/2014-19/01/2014'], x_asc,
        )

        self.assertEqual(4, y_asc[0][0])
        self.assertURL(
            url=y_asc[0][1],
            model=FakeOrganisation,
            expected_q=Q(
                customfielddate__custom_field=cf.id,
                customfielddate__value__range=['2013-12-21', '2014-01-04'],
            ),
        )

        self.assertEqual(2, y_asc[1][0])
        self.assertURL(
            url=y_asc[1][1],
            model=FakeOrganisation,
            expected_q=Q(
                customfielddate__custom_field=cf.id,
                customfielddate__value__range=['2014-01-05', '2014-01-19'],
            ),
        )

    def test_fetch_with_custom_datetime_range(self):
        "Count."
        user = self.login()

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
        rgraph = ReportGraph.objects.create(
            user=user,
            linked_report=self._create_simple_organisations_report(),
            name=f'First victory / {days} day(s)',
            abscissa_cell_value=cf.id,
            # abscissa_type=RGT_CUSTOM_RANGE, abscissa_parameter=str(days),
            abscissa_type=ReportGraph.Group.CUSTOM_RANGE, abscissa_parameter=str(days),
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        # ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch(user)
        self.assertListEqual(
            ['21/12/2013-04/01/2014', '05/01/2014-19/01/2014'], x_asc,
        )

        self.assertEqual(4, y_asc[0][0])
        self.assertURL(
            url=y_asc[0][1],
            model=FakeOrganisation,
            expected_q=Q(
                customfielddatetime__custom_field=cf.id,
                customfielddatetime__value__range=['2013-12-21', '2014-01-04'],
            ),
        )

        self.assertEqual(2, y_asc[1][0])
        self.assertURL(
            url=y_asc[1][1],
            model=FakeOrganisation,
            expected_q=Q(
                customfielddatetime__custom_field=cf.id,
                customfielddatetime__value__range=['2014-01-05', '2014-01-19'],
            ),
        )

        # DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC', user=user)
        self.assertListEqual(
            ['07/01/2014-24/12/2013', '23/12/2013-09/12/2013'], x_desc,
        )

        self.assertEqual(5, y_desc[0][0])
        self.assertURL(
            url=y_desc[0][1],
            model=FakeOrganisation,
            expected_q=Q(
                customfielddatetime__custom_field=cf.id,
                customfielddatetime__value__range=['2013-12-24', '2014-01-07'],
            ),
        )

        self.assertEqual(1, y_desc[1][0])
        self.assertURL(
            url=y_desc[1][1],
            model=FakeOrganisation,
            expected_q=Q(
                customfielddatetime__custom_field=cf.id,
                customfielddatetime__value__range=['2013-12-09', '2013-12-23'],
            ),
        )

        # Extra Q --------------------------------------------------------------
        extra_q = Q(capital__gt=500)
        x_xtra, y_xtra = rgraph.fetch(user=user, extra_q=extra_q)
        self.assertListEqual(['26/12/2013-09/01/2014'], x_xtra)

        extra_value, extra_url = y_xtra[0]
        self.assertEqual(1, extra_value)
        self.assertURL(
            url=extra_url,
            model=FakeOrganisation,
            expected_q=extra_q & Q(
                customfielddatetime__custom_field=cf.id,
                customfielddatetime__value__range=['2013-12-26', '2014-01-09'],
            ),
        )

    def test_fetch_with_custom_date_range_error(self):
        "Invalid CustomField."
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Useless name',
            abscissa_cell_value=1000,  # <====
            # abscissa_type=RGT_CUSTOM_RANGE, abscissa_parameter='11',
            abscissa_type=ReportGraph.Group.CUSTOM_RANGE, abscissa_parameter='11',
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        x_asc, y_asc = rgraph.fetch(user)
        self.assertListEqual([], x_asc)
        self.assertListEqual([], y_asc)

    def test_fetch_by_day(self):
        "Aggregate."
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Average of capital by creation date (by day)',
            abscissa_cell_value='creation_date',
            # abscissa_type=RGT_DAY,
            abscissa_type=ReportGraph.Group.DAY,
            # ordinate_type=RGA_AVG,
            ordinate_type=ReportGraph.Aggregator.AVG,
            ordinate_cell_key='regular_field-capital',
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='House Stark',     creation_date='2013-06-22', capital=100)
        create_orga(name='House Lannister', creation_date='2013-06-22', capital=200)
        create_orga(name='Wildlings',       creation_date='2013-07-5',  capital=130)

        # ASC ------------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch(user=user)
        self.assertListEqual(['22/06/2013', '05/07/2013'], x_asc)

        self.assertEqual(150, y_asc[0][0])
        self.assertURL(
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
        self.assertListEqual(
            ['05/07/2013', '22/06/2013'], rgraph.fetch(user=user, order='DESC')[0],
        )

        # Extra Q --------------------------------------------------------------
        x_xtra, y_xtra = rgraph.fetch(user=user, extra_q=Q(name__startswith='House'))
        self.assertListEqual(['22/06/2013'], x_xtra)

        self.assertEqual(150, y_xtra[0][0])
        self.assertURL(
            y_xtra[0][1],
            FakeOrganisation,
            Q(
                name__startswith='House',
                creation_date__day=22,
                creation_date__month=6,
                creation_date__year=2013,
            ),
        )

    def test_fetch_by_customday_date(self):
        "Aggregate + DATE."
        user = self.login()
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

        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Average of capital by 1rst victory (by day)',
            abscissa_cell_value=cf.id, abscissa_type=ReportGraph.Group.CUSTOM_DAY,
            ordinate_type=ReportGraph.Aggregator.AVG,
            ordinate_cell_key='regular_field-capital',
        )

        x_asc, y_asc = rgraph.fetch(user)
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
        self.assertURL(url=url, model=FakeOrganisation, expected_q=expected_q)

    def test_fetch_by_customday_datetime(self):
        "Aggregate + DATETIME."
        user = self.login()
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

        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Average of capital by 1rst victory (by day)',
            # abscissa_cell_value=cf.id, abscissa_type=RGT_CUSTOM_DAY,
            abscissa_cell_value=cf.id, abscissa_type=ReportGraph.Group.CUSTOM_DAY,
            # ordinate_type=RGA_AVG,
            ordinate_type=ReportGraph.Aggregator.AVG,
            ordinate_cell_key='regular_field-capital',
        )

        # ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch(user)
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
        self.assertURL(url=url, model=FakeOrganisation, expected_q=expected_q)

        # DESC ----------------------------------------------------------------
        self.assertListEqual(
            ['05/07/2013', '22/06/2013'], rgraph.fetch(user=user, order='DESC')[0],
        )

        # ASC -----------------------------------------------------------------
        extra_q = Q(description='Westeros')
        x_xtra, y_xtra = rgraph.fetch(user=user, extra_q=extra_q)
        self.assertListEqual(['22/06/2013'], x_xtra)

        xtra_value, xtra_url = y_xtra[0]
        self.assertEqual(150, xtra_value)
        self.assertURL(
            url=xtra_url,
            model=FakeOrganisation,
            expected_q=extra_q & expected_q,
        )

    def test_fetch_by_customday_error(self):
        "Invalid CustomField."
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Average of capital by creation date (by day)',
            abscissa_cell_value=1000,  # <====
            # abscissa_type=RGT_CUSTOM_DAY,
            abscissa_type=ReportGraph.Group.CUSTOM_DAY,
            # ordinate_type=RGA_AVG,
            ordinate_type=ReportGraph.Aggregator.AVG,
            ordinate_cell_key='regular_field-capital',
        )

        x_asc, y_asc = rgraph.fetch(user=user)
        self.assertListEqual([], x_asc)
        self.assertListEqual([], y_asc)

        hand = rgraph.hand
        self.assertEqual('??', hand.verbose_abscissa)
        self.assertEqual(
            _('the custom field does not exist any more.'), hand.abscissa_error,
        )

    def test_fetch_by_month01(self):
        "Count."
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Number of orgas by creation date (period of 1 month)',
            # abscissa_cell_value='creation_date', abscissa_type=RGT_MONTH,
            abscissa_cell_value='creation_date', abscissa_type=ReportGraph.Group.MONTH,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='Orga1', creation_date='2013-06-22')
        create_orga(name='Orga2', creation_date='2013-06-25')
        create_orga(name='Orga3', creation_date='2013-08-5')

        # ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch(user=user)
        self.assertEqual(['06/2013', '08/2013'], x_asc)

        self.assertEqual(2, y_asc[0][0])
        self.assertURL(
            y_asc[0][1],
            FakeOrganisation,
            Q(creation_date__month=6, creation_date__year=2013),
        )

        self.assertEqual(1, y_asc[1][0])

        # DESC ----------------------------------------------------------------
        self.assertListEqual(
            ['08/2013', '06/2013'], rgraph.fetch(user=user, order='DESC')[0],
        )

    def test_fetch_by_custommonth_date(self):
        "Count."
        user = self.login()

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

        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Number of houses by 1rst victory (period of 1 month)',
            abscissa_cell_value=cf.id, abscissa_type=ReportGraph.Group.CUSTOM_MONTH,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        x_asc, y_asc = rgraph.fetch(user=user)
        self.assertListEqual(['06/2013', '08/2013'], x_asc)

        value0, url0 = y_asc[0]
        self.assertEqual(2, value0)

        expected_q = Q(
            customfielddate__custom_field=cf.id,
            customfielddate__value__month=6,
            customfielddate__value__year=2013,
        )
        self.assertURL(
            url=url0,
            model=FakeOrganisation,
            expected_q=expected_q,
        )

    def test_fetch_by_custommonth_datetime(self):
        "Count."
        user = self.login()

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

        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Number of houses by 1rst victory (period of 1 month)',
            # abscissa_cell_value=cf.id, abscissa_type=RGT_CUSTOM_MONTH,
            abscissa_cell_value=cf.id, abscissa_type=ReportGraph.Group.CUSTOM_MONTH,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        x_asc, y_asc = rgraph.fetch(user=user)
        self.assertListEqual(['06/2013', '08/2013'], x_asc)

        value0, url0 = y_asc[0]
        self.assertEqual(2, value0)

        expected_q = Q(
            customfielddatetime__custom_field=cf.id,
            customfielddatetime__value__month=6,
            customfielddatetime__value__year=2013,
        )
        self.assertURL(
            url=url0,
            model=FakeOrganisation,
            expected_q=expected_q,
        )

        # Extra Q --------------------------------------------------------------
        extra_q = Q(capital__gt=200)
        x_xtra, y_xtra = rgraph.fetch(user=user, extra_q=extra_q)
        self.assertListEqual(['06/2013'], x_xtra)

        extra_value, extra_url = y_xtra[0]
        self.assertEqual(1, extra_value)
        self.assertURL(
            url=extra_url,
            model=FakeOrganisation,
            expected_q=extra_q & expected_q,
        )

    def test_fetch_by_year01(self):
        "Count."
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Number of orgas by creation date (period of 1 year)',
            # abscissa_cell_value='creation_date', abscissa_type=RGT_YEAR,
            abscissa_cell_value='creation_date', abscissa_type=ReportGraph.Group.YEAR,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='Orga1', creation_date='2013-06-22')
        create_orga(name='Orga2', creation_date='2013-07-25')
        create_orga(name='Orga3', creation_date='2014-08-5')

        # ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch(user)
        self.assertEqual(['2013', '2014'], x_asc)

        def fmt(year):
            return '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(creation_date__year=year),
            )

        self.assertListEqual([2, fmt(2013)], y_asc[0])
        self.assertListEqual([1, fmt(2014)], y_asc[1])

        # DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC', user=user)
        self.assertListEqual(['2014', '2013'], x_desc)
        self.assertListEqual([1, fmt(2014)], y_desc[0])
        self.assertListEqual([2, fmt(2013)], y_desc[1])

    def test_fetch_by_year02(self):
        "Aggregate ordinate with custom field."
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister', creation_date='2013-06-22')
        starks     = create_orga(name='House Stark',     creation_date='2013-07-25')
        baratheons = create_orga(name='House Baratheon', creation_date='2014-08-5')
        tullies    = create_orga(name='House Tully',     creation_date='2016-08-5')
        create_orga(name='House Targaryen', creation_date='2015-08-5')

        cf = CustomField.objects.create(
            content_type=self.ct_orga, name='Vine', field_type=CustomField.FLOAT,
        )

        create_cfval = partial(cf.value_class.objects.create, custom_field=cf)
        create_cfval(entity=lannisters, value='20.2')
        create_cfval(entity=starks,     value='50.5')
        create_cfval(entity=baratheons, value='100.0')
        create_cfval(entity=tullies,    value='0.0')

        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Sum of vine by creation date (period of 1 year)',
            # abscissa_cell_value='creation_date', abscissa_type=RGT_YEAR,
            abscissa_cell_value='creation_date', abscissa_type=ReportGraph.Group.YEAR,
            # ordinate_type=RGA_SUM,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key=f'custom_field-{cf.id}',
        )

        x_asc, y_asc = rgraph.fetch(user)
        # self.assertListEqual(['2013', '2014', '2015', '2016'], x_asc)
        self.assertListEqual(['2013', '2014', '2016'], x_asc)

        def fmt(year):
            return '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(creation_date__year=year),
            )

        self.assertListEqual([Decimal('70.70'), fmt(2013)], y_asc[0])
        self.assertListEqual([Decimal('100'),   fmt(2014)], y_asc[1])
        # self.assertListEqual([0,                fmt(2015)], y_asc[2])
        # self.assertListEqual([0,                fmt(2016)], y_asc[3])
        self.assertListEqual([0,                fmt(2016)], y_asc[2])

    def test_fetch_by_year03(self):
        "Invalid field."
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Number of orgas by creation date (period of 1 year)',
            abscissa_cell_value='invalid',  # <=====
            # abscissa_type=RGT_YEAR,
            abscissa_type=ReportGraph.Group.YEAR,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        x_asc, y_asc = rgraph.fetch(user)
        self.assertListEqual([], x_asc)
        self.assertListEqual([], y_asc)

        hand = rgraph.hand
        self.assertEqual('??', hand.verbose_abscissa)
        self.assertEqual(_('the field does not exist any more.'), hand.abscissa_error)

    def test_fetch_by_year04(self):
        "Entity type with several CustomFields with the same type (bugfix)."
        user = self.login()

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

        report = self._create_simple_organisations_report()
        rgraph1 = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Sum of gold by creation date (period of 1 year)',
            abscissa_cell_value='creation_date', abscissa_type=ReportGraph.Group.YEAR,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key=f'custom_field-{cf1.id}',
        )

        x_asc1, y_asc1 = rgraph1.fetch(user)
        # self.assertListEqual(['2013', '2014', '2015'], x_asc1)
        self.assertListEqual(['2013', '2014'], x_asc1)

        def fmt(year):
            return '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(creation_date__year=year),
            )

        self.assertListEqual([1100, fmt(2013)], y_asc1[0])
        self.assertListEqual([500,  fmt(2014)], y_asc1[1])

        # ---
        rgraph2 = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Average of gold by creation date (period of 1 year)',
            abscissa_cell_value='creation_date', abscissa_type=ReportGraph.Group.YEAR,
            ordinate_type=ReportGraph.Aggregator.AVG,
            ordinate_cell_key=f'custom_field-{cf2.id}',
        )

        x_asc2, y_asc2 = rgraph2.fetch(user)
        # self.assertListEqual(['2013', '2014', '2015'], x_asc2)
        self.assertListEqual(['2013', '2015'], x_asc2)
        self.assertListEqual([Decimal('7.5'), fmt(2013)], y_asc2[0])
        self.assertListEqual([1,              fmt(2015)], y_asc2[1])

    def test_fetch_with_cutomfields_on_x_n_y(self):
        "Graphs with CustomFields on abscissa & ordinate."
        user = self.login()

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

        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Sum of gold by birthday (period of 1 year)',
            abscissa_cell_value=cf_x.id, abscissa_type=ReportGraph.Group.CUSTOM_YEAR,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key=f'custom_field-{cf_y.id}',
        )

        x_asc, y_asc = rgraph.fetch(user)
        # self.assertListEqual(['2013', '2014', '2015'], x_asc)
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
        # self.assertListEqual([0,    fmt(2015)], y_asc[2])

    def test_fetch_by_customyear_date(self):
        "Count."
        user = self.login()

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

        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Number of house by 1rst victory (period of 1 year)',
            abscissa_cell_value=cf.id, abscissa_type=ReportGraph.Group.CUSTOM_YEAR,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        x_asc, y_asc = rgraph.fetch(user=user)
        self.assertListEqual(['2013', '2014'], x_asc)

        value0, url0 = y_asc[0]
        self.assertEqual(2, value0)

        expected_q = Q(
            customfielddate__custom_field=cf.id,
            customfielddate__value__year=2013,
        )
        self.assertURL(url=url0, model=FakeOrganisation, expected_q=expected_q)

    def test_fetch_by_customyear_datetime(self):
        "Count."
        user = self.login()

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

        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Number of house by 1rst victory (period of 1 year)',
            # abscissa_cell_value=cf.id, abscissa_type=RGT_CUSTOM_YEAR,
            abscissa_cell_value=cf.id, abscissa_type=ReportGraph.Group.CUSTOM_YEAR,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        x_asc, y_asc = rgraph.fetch(user=user)
        self.assertListEqual(['2013', '2014'], x_asc)

        value0, url0 = y_asc[0]
        self.assertEqual(2, value0)

        expected_q = Q(
            customfielddatetime__custom_field=cf.id,
            customfielddatetime__value__year=2013,
        )
        self.assertURL(
            url=url0,
            model=FakeOrganisation,
            expected_q=expected_q,
        )

        # Extra q --------------------------------------------------------------
        extra_q = Q(capital__gt=200)
        x_xtra, y_xtra = rgraph.fetch(user=user, extra_q=extra_q)
        self.assertListEqual(['2013'], x_xtra)

        extra_value, extra_url = y_xtra[0]
        self.assertEqual(1, extra_value)
        self.assertURL(
            url=extra_url,
            model=FakeOrganisation,
            expected_q=extra_q & expected_q,
        )

    def test_fetch_by_relation01(self):
        "Count"
        user = self.login()
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

        create_rel = partial(
            Relation.objects.create,
            user=user, type_id=fake_constants.FAKE_REL_OBJ_EMPLOYED_BY,
        )
        create_rel(subject_entity=lannisters, object_entity=tyrion)
        create_rel(subject_entity=starks,     object_entity=ned)
        create_rel(subject_entity=starks,     object_entity=aria)
        create_rel(subject_entity=starks,     object_entity=jon)

        report = self._create_simple_contacts_report(efilter=efilter)
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Number of employees',
            abscissa_cell_value=fake_constants.FAKE_REL_SUB_EMPLOYED_BY,
            # abscissa_type=RGT_RELATION,
            abscissa_type=ReportGraph.Group.RELATION,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        # ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch(user=user)
        # TODO: sort alphabetically (see comment in the code)
        # self.assertEqual([str(lannisters), str(starks)], x_asc)
        # self.assertEqual(1, y_asc[0])
        # self.assertEqual(2, y_asc[1]) #not 3, because of the filter

        self.assertEqual(2, len(x_asc))

        with self.assertNoException():
            lannisters_idx = x_asc.index(str(lannisters))
            starks_idx     = x_asc.index(str(starks))

        fmt = '/tests/contacts?q_filter={}&filter=test-filter'.format
        self.assertListEqual(
            [1, fmt(self._serialize_qfilter(pk__in=[tyrion.id]))],
            y_asc[lannisters_idx],
        )
        self.assertListEqual(
            [2, fmt(self._serialize_qfilter(pk__in=[ned.id, aria.id, jon.id]))],
            y_asc[starks_idx],
        )  # Not 3, because of the filter

        # DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC', user=user)
        self.assertEqual(x_asc, x_desc)
        self.assertEqual(y_asc, y_desc)

        # extra Q --------------------------------------------------------------
        extra_q = Q(first_name__startswith='Ar')
        x_xtra, y_xtra = rgraph.fetch(user=user, extra_q=extra_q)

        xtra_value, xtra_url = y_xtra[x_xtra.index(str(starks))]
        self.assertEqual(1, xtra_value)
        self.assertURL(
            url=xtra_url,
            model=FakeContact,
            expected_q=extra_q & Q(pk__in=[ned.id, aria.id, jon.id]),
            expected_efilter_id=efilter.id,
        )

    def test_fetch_by_relation02(self):
        "Aggregate."
        user = self.login()
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister', capital=100)
        starks     = create_orga(name='House Stark',     capital=50)
        tullies    = create_orga(name='House Tully',     capital=40)

        create_contact = partial(FakeContact.objects.create, user=user)
        tywin = create_contact(first_name='Tywin',  last_name='Lannister')
        ned   = create_contact(first_name='Eddard', last_name='Stark')

        rtype = RelationType.objects.smart_update_or_create(
            ('reports-subject_obeys',   'obeys to', [FakeOrganisation]),
            ('reports-object_commands', 'commands', [FakeContact]),
        )[0]

        create_rel = partial(Relation.objects.create, user=user, type=rtype)
        create_rel(subject_entity=lannisters, object_entity=tywin)
        create_rel(subject_entity=starks,     object_entity=ned)
        create_rel(subject_entity=tullies,    object_entity=ned)

        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Capital by lords',
            abscissa_cell_value=rtype.id,
            # abscissa_type=RGT_RELATION,
            abscissa_type=ReportGraph.Group.RELATION,
            # ordinate_type=RGA_SUM,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key='regular_field-capital',
        )

        # ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch(user)
        self.assertEqual(2, len(x_asc))

        ned_index = x_asc.index(str(ned))
        self.assertNotEqual(-1,  ned_index)

        tywin_index = x_asc.index(str(tywin))
        self.assertNotEqual(-1,  tywin_index)

        fmt = '/tests/organisations?q_filter={}'.format
        self.assertListEqual(
            [100, fmt(self._serialize_qfilter(pk__in=[lannisters.pk]))],
            y_asc[tywin_index],
        )
        self.assertListEqual(
            [90,  fmt(self._serialize_qfilter(pk__in=[starks.id, tullies.id]))],
            y_asc[ned_index],
        )

        # DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC', user=user)
        self.assertEqual(x_asc, x_desc)
        self.assertEqual(y_asc, y_desc)

    def test_fetch_by_relation03(self):
        "Aggregate ordinate with custom field."
        user = self.login()

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

        report = self._create_simple_contacts_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Contacts HP by house',
            # abscissa_cell_value=rtype_id, abscissa_type=RGT_RELATION,
            abscissa_cell_value=rtype_id, abscissa_type=ReportGraph.Group.RELATION,
            # ordinate_type=RGA_SUM,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key=f'custom_field-{cf.id}',
        )

        x_asc, y_asc = rgraph.fetch(user)
        self.assertSetEqual({str(lannisters), str(starks)}, {*x_asc})

        index = x_asc.index
        fmt = '/tests/contacts?q_filter={}'.format
        self.assertListEqual(
            [600, fmt(self._serialize_qfilter(pk__in=[jaime.id, tyrion.id]))],
            y_asc[index(str(lannisters))],
        )
        self.assertListEqual(
            [800, fmt(self._serialize_qfilter(pk__in=[ned.id, robb.id]))],
            y_asc[index(str(starks))],
        )

    def test_fetch_by_relation04(self):
        "Invalid RelationType."
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Average of capital by creation date (by day)',
            abscissa_cell_value='invalidrtype',  # <====
            # abscissa_type=RGT_RELATION,
            abscissa_type=ReportGraph.Group.RELATION,
            # ordinate_type=RGA_AVG,
            ordinate_type=ReportGraph.Aggregator.AVG,
            ordinate_cell_key='regular_field-capital',
        )

        x_asc, y_asc = rgraph.fetch(user)
        self.assertListEqual([], x_asc)
        self.assertListEqual([], y_asc)

        hand = rgraph.hand
        self.assertEqual('??', hand.verbose_abscissa)
        self.assertEqual(
            _('the relationship type does not exist any more.'), hand.abscissa_error,
        )

    def test_fetch_with_customfk_01(self):
        user = self.login()
        report = self._create_simple_contacts_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Contacts by title',
            abscissa_cell_value=1000,  # <=========
            # abscissa_type=RGT_CUSTOM_FK,
            abscissa_type=ReportGraph.Group.CUSTOM_FK,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch(user)

        self.assertListEqual([], x_asc)
        self.assertListEqual([], y_asc)

        hand = rgraph.hand
        self.assertEqual('??', hand.verbose_abscissa)
        self.assertEqual(
            _('the custom field does not exist any more.'), hand.abscissa_error,
        )

    def test_fetch_with_customfk_02(self):
        "Count."
        user = self.login()
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

        report = self._create_simple_contacts_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Contacts by title',
            # abscissa_cell_value=cf.id, abscissa_type=RGT_CUSTOM_FK,
            abscissa_cell_value=cf.id, abscissa_type=ReportGraph.Group.CUSTOM_FK,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch(user)

        self.assertListEqual([hand.value, lord.value], x_asc)

        def fmt(val):
            return '/tests/contacts?q_filter={}'.format(
                self._serialize_qfilter(customfieldenum__value=val),
            )

        self.assertListEqual([1, fmt(hand.id)], y_asc[0])
        self.assertListEqual([2, fmt(lord.id)], y_asc[1])

        # DESC -----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC', user=user)
        self.assertListEqual([*reversed(x_asc)], x_desc)
        self.assertListEqual([*reversed(y_asc)], y_desc)

        # Extra Q --------------------------------------------------------------
        extra_q = Q(first_name__startswith='B')
        x_xtra, y_xtra = rgraph.fetch(user=user, extra_q=extra_q)
        self.assertListEqual([hand.value, lord.value], x_xtra)

        extra_value, extra_url = y_xtra[1]
        self.assertEqual(1, extra_value)
        self.assertURL(
            url=extra_url,
            model=FakeContact,
            expected_q=extra_q & Q(customfieldenum__value=lord.id),
        )

    def test_fetch_with_customfk_03(self):
        "Aggregate."
        user = self.login()
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

        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Capital by policy',
            # abscissa_cell_value=cf.id, abscissa_type=RGT_CUSTOM_FK,
            abscissa_cell_value=cf.id, abscissa_type=ReportGraph.Group.CUSTOM_FK,
            # ordinate_type=RGA_SUM,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key='regular_field-capital',
        )

        self.assertEqual(cf.name, rgraph.hand.verbose_abscissa)

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch(user)

        self.assertEqual([fight.value, smartness.value], x_asc)

        def fmt(val):
            return '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(customfieldenum__value=val),
            )

        self.assertListEqual([90,  fmt(fight.id)],     y_asc[0])
        self.assertListEqual([100, fmt(smartness.id)], y_asc[1])

        # DESC ---------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC', user=user)
        self.assertListEqual([*reversed(x_asc)], x_desc)
        self.assertListEqual([*reversed(y_asc)], y_desc)

    def test_fetch_with_customfk_04(self):
        """Entity type with several CustomFields with the same type
        + custom-field ENUM for aggregation (bugfix).
        """
        user = self.login()

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

        report = self._create_simple_organisations_report()
        rgraph1 = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Sum of gold by type',
            abscissa_cell_value=str(cf_enum.id), abscissa_type=ReportGraph.Group.CUSTOM_FK,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key=f'custom_field-{cf_int1.id}',
        )

        x_asc1, y_asc1 = rgraph1.fetch(user)
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
        rgraph2 = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Average of gold by type',
            abscissa_cell_value=str(cf_enum.id), abscissa_type=ReportGraph.Group.CUSTOM_FK,
            ordinate_type=ReportGraph.Aggregator.AVG,
            ordinate_cell_key=f'custom_field-{cf_int2.id}',
        )

        x_asc2, y_asc2 = rgraph2.fetch(user)
        self.assertListEqual([soldiers.value, knights.value, dragons.value], x_asc2)
        self.assertListEqual([Decimal('7.5'), fmt(soldiers)], y_asc2[0])
        self.assertListEqual([0,              fmt(knights)],  y_asc2[1])
        self.assertListEqual([1,              fmt(dragons)],  y_asc2[2])

    def test_fetchgraphview_with_decimal_ordinate(self):
        "Test json encoding for Graph with Decimal in fetch_graph view."
        user = self.login()
        # rgraph = self._create_invoice_report_n_graph(ordinate='total_vat__sum')
        rgraph = self._create_invoice_report_n_graph(
            # ordinate_type=RGA_SUM,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_field='total_vat',
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='BullFrog')
        orga2 = create_orga(name='Maxis')
        self._create_invoice(orga1, orga2, issuing_date='2015-10-16', total_vat=Decimal('1212.12'))
        self._create_invoice(orga1, orga2, issuing_date='2015-10-03', total_vat=Decimal('33.24'))

        self.assertGET200(self._builf_fetch_url(rgraph, 'ASC'))

    def test_fetchgraphview_save_settings01(self):
        self.login()
        rgraph = self._create_documents_rgraph()

        chart1 = 'piechart'
        url = self._builf_fetch_url
        self.assertGET200(url(rgraph, 'ASC', chart=chart1))
        rgraph = self.refresh(rgraph)
        self.assertIsNone(rgraph.chart)
        self.assertTrue(rgraph.asc)

        self.assertGET200(url(rgraph, 'ASC', chart=chart1, save_settings='false'))
        self.assertIsNone(self.refresh(rgraph).chart)

        self.assertGET404(url(rgraph, 'ASC', chart=chart1, save_settings='invalid'))
        self.assertIsNone(self.refresh(rgraph).chart)

        self.assertGET404(url(rgraph, 'ASC', chart='invalid', save_settings='true'))
        self.assertIsNone(self.refresh(rgraph).chart)

        self.assertGET200(url(rgraph, 'ASC', chart=chart1, save_settings='true'))
        rgraph = self.refresh(rgraph)
        self.assertEqual(chart1, rgraph.chart)
        self.assertTrue(rgraph.asc)

        chart2 = 'tubechart'
        self.assertGET200(url(rgraph, 'DESC', chart=chart2, save_settings='true'))
        rgraph = self.refresh(rgraph)
        self.assertEqual(chart2, rgraph.chart)
        self.assertFalse(rgraph.asc)

        self.assertGET200(url(rgraph, 'ASC', save_settings='true'))
        rgraph = self.refresh(rgraph)
        self.assertEqual(chart2, rgraph.chart)
        self.assertTrue(rgraph.asc)

    def test_fetchgraphview_save_settings02(self):
        "Not super-user."
        user = self.login(is_superuser=False, allowed_apps=['creme_core', 'reports'])
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE,
            set_type=SetCredentials.ESET_OWN,
        )

        rgraph1 = self._create_documents_rgraph(user=self.other_user)
        self.assertFalse(user.has_perm_to_view(rgraph1))

        chart = 'piechart'
        url = self._builf_fetch_url
        self.assertGET200(url(rgraph1, 'ASC', chart=chart, save_settings='true'))
        self.assertIsNone(self.refresh(rgraph1).chart)

        # --
        rgraph2 = self._create_documents_rgraph(user=user)
        self.assertTrue(user.has_perm_to_change(rgraph2))
        self.assertGET200(url(rgraph2, 'ASC', chart=chart, save_settings='true'))
        self.assertEqual(chart, self.refresh(rgraph2).chart)

    def test_fetchfrombrick_save_settings(self):
        user = self.login()
        folder = FakeReportsFolder.objects.create(title='my Folder', user=user)
        rgraph = self._create_documents_rgraph()

        fetcher = RegularFieldLinkedGraphFetcher(graph=rgraph, value='linked_folder')
        self.assertIsNone(fetcher.error)

        ibci = fetcher.create_brick_config_item()

        chart = 'piechart'
        url = self._build_fetchfrombrick_url
        self.assertGET200(url(ibci, folder, 'ASC', chart=chart))
        rgraph = self.refresh(rgraph)
        self.assertIsNone(rgraph.chart)
        self.assertTrue(rgraph.asc)

        self.assertGET200(url(ibci, folder, 'ASC', chart=chart, save_settings='false'))
        self.assertIsNone(self.refresh(rgraph).chart)

        self.assertGET404(url(ibci, folder, 'ASC', chart=chart, save_settings='invalid'))
        self.assertIsNone(self.refresh(rgraph).chart)

        self.assertGET404(url(ibci, folder, 'ASC', chart='invalid', save_settings='true'))
        self.assertIsNone(self.refresh(rgraph).chart)

        self.assertGET200(url(ibci, folder, 'ASC', chart=chart, save_settings='true'))
        rgraph = self.refresh(rgraph)
        self.assertEqual(chart, rgraph.chart)
        self.assertTrue(rgraph.asc)

        self.assertGET200(url(ibci, folder, 'DESC', save_settings='true'))
        rgraph = self.refresh(rgraph)
        self.assertEqual(chart, rgraph.chart)
        self.assertFalse(rgraph.asc)

    # def test_create_instance_brick_config_item01(self):  # DEPRECATED
    #     "No link."
    #     self.login()
    #     rgraph = self._create_documents_rgraph()
    #
    #     ibci = rgraph.create_instance_brick_config_item()
    #     self.assertEqual('instanceblock_reports-graph', ibci.brick_class_id)
    #     self.assertEqual(RGF_NOLINK, ibci.get_extra_data('type'))
    #     self.assertIsNone(ibci.get_extra_data('value'))
    #
    #     volatile = _('No volatile column')
    #     self.assertEqual(
    #         f'{rgraph.name} - {volatile}', ReportGraphBrick(ibci).verbose_name
    #     )
    #
    #     # Brick verbose name should be dynamically computed
    #     rgraph.name = rgraph.name.upper()
    #     rgraph.save()
    #     self.assertEqual(
    #         f'{rgraph.name} - {volatile}', ReportGraphBrick(ibci).verbose_name
    #     )

    # def test_create_instance_brick_config_item02(self):  # DEPRECATED
    #     "Link: regular field."
    #     self.login()
    #     rgraph = self._create_documents_rgraph()
    #     create_ibci = rgraph.create_instance_brick_config_item
    #
    #     fk_name = 'linked_folder'
    #     ibci = create_ibci(volatile_field=fk_name)
    #     self.assertEqual(ReportGraphBrick.id_, ibci.brick_class_id)
    #     self.assertEqual(RGF_FK, ibci.get_extra_data('type'))
    #     self.assertEqual(fk_name, ibci.get_extra_data('value'))
    #
    #     self.assertIsNone(create_ibci(volatile_field='unknown'))
    #     self.assertIsNone(create_ibci(volatile_field='description'))  # Not FK
    #     self.assertIsNone(create_ibci(volatile_field='user'))  # Not FK to CremeEntity
    #     self.assertIsNone(create_ibci(volatile_field='folder__title'))  # Depth > 1
    #
    #     self.assertEqual(
    #         '{} - {}' .format(
    #             rgraph.name,
    #             _('{field} (Field)').format(field=_('Folder')),
    #         ),
    #         ReportGraphBrick(ibci).verbose_name
    #     )

    # def test_create_instance_brick_config_item03(self):  # DEPRECATED
    #     "Link: relation type."
    #     user = self.login()
    #     report = self._create_simple_contacts_report()
    #     rgraph = ReportGraph.objects.create(
    #         user=user,
    #         linked_report=report,
    #         name='Number of created contacts / year',
    #         abscissa_cell_value='created', abscissa_type=RGT_YEAR,
    #         ordinate_type=RGA_COUNT,
    #     )
    #
    #     rtype = RelationType.create(
    #         ('reports-subject_loves', 'loves',       [FakeContact]),
    #         ('reports-object_loves',  'is loved by', [FakeContact]),
    #     )[0]
    #
    #     ibci = rgraph.create_instance_brick_config_item(volatile_rtype=rtype)
    #     self.assertEqual(ReportGraphBrick.id_, ibci.brick_class_id)
    #     self.assertEqual(RGF_RELATION, ibci.get_extra_data('type'))
    #     self.assertEqual(rtype.id,     ibci.get_extra_data('value'))
    #
    #     fmt = _('{rtype} (Relationship)').format
    #     self.assertEqual(
    #         f'{rgraph.name} - {fmt(rtype=rtype)}', ReportGraphBrick(ibci).verbose_name,
    #     )
    #
    #     rtype.predicate = 'likes'
    #     rtype.save()
    #     self.assertEqual(
    #         f'{rgraph.name} - {fmt(rtype=rtype)}', ReportGraphBrick(ibci).verbose_name,
    #     )

    def test_add_graph_instance_brick01(self):
        user = self.login()
        rgraph = self._create_invoice_report_n_graph()
        self.assertFalse(
            InstanceBrickConfigItem.objects.filter(entity=rgraph.id).exists()
        )

        url = self._build_add_brick_url(rgraph)
        response = self.assertGET200(url)
        self.assertTemplateUsed(
            response,
            'creme_core/generics/blockform/add-popup.html',
        )

        context = response.context
        self.assertEqual(
            _('Create an instance block for «{entity}»').format(entity=rgraph),
            context.get('title'),
        )
        self.assertEqual(_('Save the block'), context.get('submit_label'))

        # ---
        response = self.client.post(url)
        self.assertFormError(
            response, 'form', 'fetcher',
            _('This field is required.'),
        )

        self.assertNoFormError(self.client.post(
            url,
            data={'fetcher': RGF_NOLINK},
        ))

        items = InstanceBrickConfigItem.objects.filter(entity=rgraph.id)
        self.assertEqual(1, len(items))

        item = items[0]
        self.assertEqual('instanceblock_reports-graph', item.brick_class_id)
        self.assertEqual(RGF_NOLINK, item.get_extra_data('type'))
        self.assertIsNone(item.get_extra_data('value'))
        self.assertIsNone(item.brick.errors)

        brick_id = item.brick_id
        self.assertEqual(f'instanceblock-{item.id}', brick_id)

        title = '{} - {}'.format(rgraph.name, _('No volatile column'))
        self.assertEqual(title, ReportGraphBrick(item).verbose_name)

        brick = item.brick
        self.assertIsInstance(brick, ReportGraphBrick)
        self.assertEqual(item,  brick.config_item)
        self.assertEqual(title, brick.verbose_name)
        self.assertEqual(
            _(
                'This block displays the graph «{graph}», contained by the report «{report}».\n'
                'App: Reports'
            ).format(graph=rgraph.name, report=rgraph.linked_report.name),
            brick.description,
        )

        # ----------------------------------------------------------------------
        response = self.assertPOST200(
            url,
            data={'fetcher': RGF_NOLINK},
        )
        self.assertFormError(
            response, 'form', 'fetcher',
            _('The instance block for «{graph}» with these parameters already exists!').format(
                graph=rgraph.name,
            ),
        )

        # ----------------------------------------------------------------------
        response = self.assertGET200(reverse('reports__instance_bricks_info', args=(rgraph.id,)))
        self.assertTemplateUsed(response, 'reports/bricks/instance-bricks-info.html')
        self.assertEqual(rgraph, response.context.get('object'))
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick_id=InstanceBricksInfoBrick.id_,
        )
        vname_node = self.get_html_node_or_fail(brick_node, './/td[@data-table-primary-column]')
        self.assertEqual(_('No volatile column'), vname_node.text)

        # ----------------------------------------------------------------------
        # Display on home
        BrickHomeLocation.objects.all().delete()
        BrickHomeLocation.objects.create(brick_id=brick_id, order=1)
        response = self.assertGET200('/')
        self.assertTemplateUsed(response, 'reports/bricks/graph.html')
        self.get_brick_node(self.get_html_tree(response.content), brick_id)

        # ----------------------------------------------------------------------
        # Display on detailview
        ct = self.ct_invoice
        BrickDetailviewLocation.objects.filter(content_type=ct).delete()
        BrickDetailviewLocation.objects.create_if_needed(
            brick=brick_id,
            order=1,
            zone=BrickDetailviewLocation.RIGHT, model=FakeInvoice,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='BullFrog')
        orga2 = create_orga(name='Maxis')
        orga3 = create_orga(name='Bitmap brothers')

        invoice = self._create_invoice(orga1, orga2, issuing_date='2014-10-16')
        self._create_invoice(orga1, orga3, issuing_date='2014-11-03')

        response = self.assertGET200(invoice.get_absolute_url())
        self.assertTemplateUsed(response, 'reports/bricks/graph.html')
        self.get_brick_node(self.get_html_tree(response.content), brick_id)

        # ----------------------------------------------------------------------
        response = self.assertGET200(self._build_fetchfrombrick_url(item, invoice, 'ASC'))

        result = response.json()
        self.assertIsInstance(result, dict)
        self.assertEqual(2, len(result))

        x_fmt = '{:02}/2014'.format  # NB: ReportGraph.Group.MONTH
        self.assertEqual([x_fmt(10), x_fmt(11)], result.get('x'))

        y = result.get('y')
        self.assertEqual(0, y[0][0])
        self.assertURL(
            y[0][1],
            FakeInvoice,
            Q(issuing_date__month=10, issuing_date__year=2014),
        )

        response = self.assertGET200(self._build_fetchfrombrick_url(item, invoice, 'ASC'))
        self.assertEqual(result, response.json())

        # ----------------------------------------------------------------------
        response = self.assertGET200(self._build_fetchfrombrick_url(item, invoice, 'DESC'))
        result = response.json()
        self.assertEqual([x_fmt(11), x_fmt(10)], result.get('x'))

        y = result.get('y')
        self.assertEqual(0, y[0][0])
        self.assertURL(
            y[0][1],
            FakeInvoice,
            Q(issuing_date__month=11, issuing_date__year=2014),
        )

        # ----------------------------------------------------------------------
        self.assertGET404(self._build_fetchfrombrick_url(item, invoice, 'FOOBAR'))

    def test_add_graph_instance_brick02(self):
        "Volatile column (RGF_FK)."
        user = self.login()
        rgraph = self._create_documents_rgraph()

        url = self._build_add_brick_url(rgraph)
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = [*response.context['form'].fields['fetcher'].widget.choices]

        self.assertGreaterEqual(len(choices), 3)
        self.assertInChoices(
            value=f'{RGF_NOLINK}|',
            label=pgettext('reports-volatile_choice', 'None'),
            choices=choices,
        )

        fk_name = 'linked_folder'
        folder_choice = f'{RGF_FK}|{fk_name}'
        field_choices = self.get_choices_group_or_fail(label=_('Fields'), choices=choices)
        self.assertInChoices(
            value=folder_choice,
            label=_('Folder'),
            choices=field_choices,
        )

        self.assertNoFormError(self.client.post(url, data={'fetcher': folder_choice}))

        items = InstanceBrickConfigItem.objects.filter(entity=rgraph.id)
        self.assertEqual(1, len(items))

        item = items[0]
        self.assertEqual('instanceblock_reports-graph', item.brick_class_id)
        self.assertEqual(RGF_FK, item.get_extra_data('type'))
        self.assertEqual(fk_name, item.get_extra_data('value'))

        title = '{} - {}'.format(rgraph.name, _('{field} (Field)').format(field=_('Folder')))
        self.assertEqual(title, ReportGraphBrick(item).verbose_name)
        self.assertEqual(title, str(item))

        # Display on detailview
        create_folder = partial(FakeReportsFolder.objects.create, user=user)
        folder1 = create_folder(title='Internal')
        folder2 = create_folder(title='External')

        create_doc = partial(FakeReportsDocument.objects.create, user=user)
        doc1 = create_doc(title='Doc#1.1', linked_folder=folder1)
        create_doc(title='Doc#1.2', linked_folder=folder1)
        create_doc(title='Doc#2',   linked_folder=folder2)

        ct = folder1.entity_type
        BrickDetailviewLocation.objects.filter(content_type=ct).delete()
        BrickDetailviewLocation.objects.create_if_needed(
            brick=item.brick_id,
            order=1,
            zone=BrickDetailviewLocation.RIGHT, model=FakeReportsFolder,
        )

        response = self.assertGET200(folder1.get_absolute_url())
        self.assertTemplateUsed(response, 'reports/bricks/graph.html')

        # fetcher = ReportGraph.get_fetcher_from_instance_brick(item)
        fetcher = ReportGraphBrick(item).fetcher
        self.assertIsNone(fetcher.error)

        x, y = fetcher.fetch_4_entity(entity=folder1, user=user)  # TODO: order

        year = doc1.created.year
        self.assertListEqual([str(year)], x)
        qfilter = Q(linked_folder=folder1.id) & Q(created__year=year)
        self.assertListEqual(
            [[
                2,
                reverse('reports__list_fake_documents')
                + f'?q_filter={self._serialize_qfilter(qfilter)}',
            ]],
            y,
        )

    def test_add_graph_instance_brick_not_superuser01(self):
        apps = ['reports']
        self.login(is_superuser=False, allowed_apps=apps, admin_4_apps=apps)
        rgraph = self._create_invoice_report_n_graph()
        self.assertGET200(self._build_add_brick_url(rgraph))

    def test_add_graph_instance_brick_not_superuser02(self):
        "Admin permission needed"
        self.login(
            is_superuser=False, allowed_apps=['reports'],  # admin_4_apps=['reports'],
        )
        rgraph = self._create_invoice_report_n_graph()
        self.assertGET403(self._build_add_brick_url(rgraph))

    def test_add_graph_instance_brick02_error01(self):
        "Volatile column (RFT_FIELD): invalid field."
        user = self.login()
        rgraph = self._create_documents_rgraph()

        # We create voluntarily an invalid item
        fname = 'invalid'
        ibci = InstanceBrickConfigItem.objects.create(
            entity=rgraph,
            brick_class_id=ReportGraphBrick.id_,
        )
        ibci.set_extra_data(key='type',  value=RGF_FK)
        ibci.set_extra_data(key='value', value=fname)

        folder = FakeReportsFolder.objects.create(user=user, title='My folder')

        fetcher = ReportGraphBrick(ibci).fetcher
        x, y = fetcher.fetch_4_entity(entity=folder, user=user)

        self.assertEqual([], x)
        self.assertEqual([], y)
        self.assertEqual(_('The field is invalid.'), fetcher.error)
        self.assertEqual('??',                       fetcher.verbose_name)

        self.assertEqual([_('The field is invalid.')], ibci.brick.errors)

    def test_add_graph_instance_brick02_error02(self):
        "Volatile column (RFT_FIELD): field is not a FK to CremeEntity."
        user = self.login()
        rgraph = self._create_documents_rgraph()

        # We create voluntarily an invalid item
        fname = 'description'
        ibci = InstanceBrickConfigItem(
            entity=rgraph,
            brick_class_id=ReportGraphBrick.id_,
        )
        ibci.set_extra_data(key='type',  value=RGF_FK)
        ibci.set_extra_data(key='value', value=fname)
        ibci.save()

        folder = FakeReportsFolder.objects.create(user=user, title='My folder')

        fetcher = ReportGraphBrick(ibci).fetcher
        x, y = fetcher.fetch_4_entity(entity=folder, user=user)

        self.assertEqual([], x)
        self.assertEqual([], y)
        self.assertEqual(_('The field is invalid (not a foreign key).'), fetcher.error)

    def test_add_graph_instance_brick02_error03(self):
        "Volatile column (RGF_FK): field is not a FK to the given Entity type."
        user = self.login()
        rgraph = self._create_documents_rgraph()

        fetcher = RegularFieldLinkedGraphFetcher(graph=rgraph, value='linked_folder')
        self.assertIsNone(fetcher.error)

        ibci = fetcher.create_brick_config_item()
        self.assertIsNotNone(ibci)

        x, y = fetcher.fetch_4_entity(entity=user.linked_contact, user=user)
        self.assertListEqual([], x)
        self.assertListEqual([], y)
        self.assertIsNone(fetcher.error)

    def test_add_graph_instance_brick03(self):
        "Volatile column (RGF_RELATION)."
        user = self.login()
        report = self._create_simple_contacts_report()
        rtype = RelationType.objects.get(pk=fake_constants.FAKE_REL_SUB_EMPLOYED_BY)
        incompatible_rtype = RelationType.objects.smart_update_or_create(
            ('reports-subject_related_doc', 'is related to doc',   [Report]),
            ('reports-object_related_doc',  'is linked to report', [FakeReportsDocument]),
        )[0]

        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Number of created contacts / year',
            # abscissa_cell_value='created', abscissa_type=RGT_YEAR,
            abscissa_cell_value='created', abscissa_type=ReportGraph.Group.YEAR,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        url = self._build_add_brick_url(rgraph)
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = [*response.context['form'].fields['fetcher'].widget.choices]

        rel_choices = self.get_choices_group_or_fail(label=_('Relationships'), choices=choices)

        choice_id = f'{RGF_RELATION}|{rtype.id}'
        self.assertInChoices(value=choice_id, label=str(rtype), choices=rel_choices)
        self.assertNotInChoices(value=f'rtype-{incompatible_rtype.id}', choices=rel_choices)

        self.assertNoFormError(self.client.post(url, data={'fetcher': choice_id}))

        items = InstanceBrickConfigItem.objects.filter(entity=rgraph.id)
        self.assertEqual(1, len(items))

        item = items[0]
        self.assertEqual('instanceblock_reports-graph', item.brick_class_id)
        self.assertEqual(RGF_RELATION, item.get_extra_data('type'))
        self.assertEqual(rtype.id,     item.get_extra_data('value'))

        self.assertEqual(
            '{} - {}'.format(
                rgraph.name,
                _('{rtype} (Relationship)').format(rtype=rtype),
            ),
            ReportGraphBrick(item).verbose_name,
        )

        create_contact = partial(FakeContact.objects.create, user=user)
        sonsaku = create_contact(first_name='Sonsaku', last_name='Hakufu')
        ryomou  = create_contact(first_name='Ryomou',  last_name='Shimei')
        create_contact(first_name='Kan-u', last_name='Unchô')

        nanyo = FakeOrganisation.objects.create(user=user, name='Nanyô')

        create_rel = partial(Relation.objects.create, user=user, type=rtype, object_entity=nanyo)
        create_rel(subject_entity=sonsaku)
        create_rel(subject_entity=ryomou)

        # fetcher = ReportGraph.get_fetcher_from_instance_brick(item)
        fetcher = ReportGraphBrick(item).fetcher
        self.assertIsNone(fetcher.error)

        x, y = fetcher.fetch_4_entity(entity=nanyo, user=user)

        year = sonsaku.created.year
        self.assertListEqual([str(year)], x)

        qfilter = (
            Q(relations__object_entity=nanyo.id)
            & Q(relations__type=rtype)
            & Q(created__year=year)
        )
        self.assertListEqual(
            [[
                2,
                f'/tests/contacts?q_filter={self._serialize_qfilter(qfilter)}',
            ]],
            y,
        )

        # Invalid choice
        choice = 'invalid'
        response = self.assertPOST200(url, data={'fetcher': choice})
        self.assertFormError(
            response, 'form', 'fetcher',
            _('Select a valid choice. %(value)s is not one of the available choices.') % {
                'value': choice,
            },
        )

    def test_add_graph_instance_brick03_error(self):
        "Volatile column (RFT_RELATION): invalid relation type."
        user = self.login()
        rgraph = self._create_documents_rgraph()

        # We create voluntarily an invalid item
        rtype_id = 'invalid'
        ibci = InstanceBrickConfigItem.objects.create(
            entity=rgraph,
            brick_class_id=ReportGraphBrick.id_,
        )
        ibci.set_extra_data(key='type',  value=RGF_RELATION)
        ibci.set_extra_data(key='value', value=rtype_id)

        # fetcher = ReportGraph.get_fetcher_from_instance_brick(ibci)
        fetcher = ReportGraphBrick(ibci).fetcher
        x, y = fetcher.fetch_4_entity(entity=user.linked_contact, user=user)
        self.assertListEqual([], x)
        self.assertListEqual([], y)
        self.assertEqual(_('The relationship type is invalid.'), fetcher.error)
        self.assertEqual('??',                                   fetcher.verbose_name)

    def test_get_fetcher_from_instance_brick(self):
        "Invalid type."
        self.login()
        rgraph = self._create_documents_rgraph()

        ibci = InstanceBrickConfigItem.objects.create(
            brick_class_id=ReportGraphBrick.id_, entity=rgraph,
        )

        # No extra data
        # fetcher1 = ReportGraph.get_fetcher_from_instance_brick(ibci)
        fetcher1 = ReportGraphBrick(ibci).fetcher
        self.assertIsInstance(fetcher1, SimpleGraphFetcher)
        msg = _('Invalid volatile link ; please contact your administrator.')
        self.assertEqual(msg, fetcher1.error)

        # Invalid type
        ibci.set_extra_data(key='type', value='invalid')
        # fetcher2 = ReportGraph.get_fetcher_from_instance_brick(ibci)
        fetcher2 = ReportGraphBrick(ibci).fetcher
        self.assertIsInstance(fetcher2, SimpleGraphFetcher)
        self.assertEqual(msg, fetcher2.error)

    def test_delete_graph_instance01(self):
        "No related Brick location."
        self.login()
        rgraph = self._create_documents_rgraph()
        ibci = SimpleGraphFetcher(graph=rgraph).create_brick_config_item()

        rgraph.delete()
        self.assertDoesNotExist(rgraph)
        self.assertDoesNotExist(ibci)

    def test_delete_graph_instance02(self):
        "There are Brick locations => cannot delete."
        self.login()
        rgraph = self._create_documents_rgraph()
        ibci = SimpleGraphFetcher(graph=rgraph).create_brick_config_item()

        brick_id = ibci.brick_id
        bdl = BrickDetailviewLocation.objects.create_if_needed(
            brick=brick_id,
            order=1,
            zone=BrickDetailviewLocation.RIGHT,
            model=FakeContact,
        )
        bhl = BrickHomeLocation.objects.create(brick_id=brick_id, order=1)

        with self.assertRaises(ProtectedError):
            rgraph.delete()

        self.assertStillExists(rgraph)
        self.assertStillExists(ibci)
        self.assertStillExists(bdl)
        self.assertStillExists(bhl)

    # def test_get_available_report_graph_types01(self):
    #     self.login()
    #     url = self._build_graph_types_url(self.ct_orga)
    #     self.assertGET404(url)
    #     self.assertPOST404(url)
    #
    #     response = self.assertPOST200(url, data={'record_id': 'name'})
    #     self.assertDictEqual(
    #         {'result': [{'text': _('Choose an abscissa field'), 'id': ''}]},
    #         response.json(),
    #     )
    #
    #     response = self.assertPOST200(url, data={'record_id': 'creation_date'})
    #     self.assertDictEqual(
    #         {
    #             'result': [
    #                 {'id': RGT_DAY,   'text': _('By days')},
    #                 {'id': RGT_MONTH, 'text': _('By months')},
    #                 {'id': RGT_YEAR,  'text': _('By years')},
    #                 {'id': RGT_RANGE, 'text': _('By X days')},
    #             ],
    #         },
    #         response.json(),
    #     )
    #
    #     response = self.assertPOST200(url, data={'record_id': 'sector'})
    #     self.assertDictEqual(
    #         {'result': [{'id': RGT_FK, 'text': _('By values')}]}, response.json()
    #     )
    #
    # def test_get_available_report_graph_types02(self):
    #     self.login()
    #     ct = self.ct_invoice
    #     url = self._build_graph_types_url(ct)
    #
    #     response = self.assertPOST200(
    #         url, data={'record_id': fake_constants.FAKE_REL_SUB_BILL_RECEIVED},
    #     )
    #     self.assertDictEqual(
    #         {
    #             'result': [{
    #                 'id': RGT_RELATION,
    #                 'text': _('By values (of related entities)'),
    #             }],
    #         },
    #         response.json(),
    #     )
    #
    #     create_cf = partial(CustomField.objects.create, content_type=ct)
    #     cf_enum = create_cf(name='Type', field_type=CustomField.ENUM)
    #     response = self.assertPOST200(url, data={'record_id': cf_enum.id})
    #     self.assertDictEqual(
    #         {
    #             'result': [{
    #                 'id': RGT_CUSTOM_FK,
    #                 'text': _('By values (of custom choices)')
    #             }],
    #         },
    #         response.json(),
    #     )
    #
    #     cf_dt = create_cf(name='First payment', field_type=CustomField.DATETIME)
    #     response = self.assertPOST200(url, data={'record_id': cf_dt.id})
    #     self.assertDictEqual(
    #         {
    #             'result': [
    #                 {'id': RGT_CUSTOM_DAY,   'text': _('By days')},
    #                 {'id': RGT_CUSTOM_MONTH, 'text': _('By months')},
    #                 {'id': RGT_CUSTOM_YEAR,  'text': _('By years')},
    #                 {'id': RGT_CUSTOM_RANGE, 'text': _('By X days')},
    #             ],
    #         },
    #         response.json(),
    #     )

    def bench_big_fetch_using_count(self):
        """
        Little benchmark to see how the 'group by' report queries behave with
        bigger data-sets where there is a visible difference between the old
         "manual group by's" and the new real sql ones.
        """
        import time
        from datetime import datetime

        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Number of organisation created by day',
            abscissa_cell_value='creation_date',
            # abscissa_type=RGT_RANGE, abscissa_parameter='1',
            abscissa_type=ReportGraph.Group.RANGE, abscissa_parameter='1',
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        interval_day_count = 300
        entities_per_day = 5
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        for i in range(1, interval_day_count + 1):
            creation = datetime.strptime(f'{i} 2014', '%j %Y').strftime('%Y-%m-%d')
            for _j in range(entities_per_day):
                create_orga(name='Target Orga', creation_date=creation)

        start = time.clock()

        x, y = rgraph.fetch()

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

        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Sum of capital by creation date (period of 1 days)',
            abscissa_cell_value='creation_date',
            # abscissa_type=RGT_RANGE, abscissa_parameter='1',
            abscissa_type=ReportGraph.Group.RANGE, abscissa_parameter='1',
            # ordinate_type=RGA_SUM,
            ordinate_type=ReportGraph.Aggregator.SUM,
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

        x, y = rgraph.fetch()

        print('Fetch took', 1000 * (time.clock() - start), 'ms')

        self.assertEqual(len(x), interval_day_count)
        self.assertEqual(len(y), interval_day_count)
        self.assertEqual(
            sum(value for value, _ in y),
            interval_day_count * entities_per_day * 100
        )

    def test_inneredit(self):
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='capital per month of creation',
            chart='barchart',
            # abscissa_cell_value='created', abscissa_type=RGT_MONTH,
            abscissa_cell_value='created', abscissa_type=ReportGraph.Group.MONTH,
            # ordinate_type=RGA_SUM,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key='regular_field-capital',
        )

        build_url = self.build_inneredit_url
        url = build_url(rgraph, 'name')
        self.assertGET200(url)

        name = rgraph.name.title()
        response = self.client.post(
            url, data={'entities_lbl': [str(rgraph)], 'field_value':  name},
        )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(rgraph).name)

        self.assertGET(400, build_url(rgraph, 'report'))
        self.assertGET(400, build_url(rgraph, 'abscissa'))
        self.assertGET(400, build_url(rgraph, 'ordinate'))
        self.assertGET(400, build_url(rgraph, 'type'))
        self.assertGET(400, build_url(rgraph, 'days'))
        self.assertGET(400, build_url(rgraph, 'chart'))

    def test_clone_report(self):
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='capital per month of creation',
            chart='barchart',
            # abscissa_cell_value='created', abscissa_type=RGT_MONTH,
            abscissa_cell_value='created', abscissa_type=ReportGraph.Group.MONTH,
            # ordinate_type=RGA_SUM,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key='regular_field-capital',
        )

        cloned_report = report.clone()

        rgrahes = ReportGraph.objects.filter(linked_report=cloned_report)
        self.assertEqual(1, len(rgrahes))

        cloned_rgraph = rgrahes[0]
        self.assertNotEqual(rgraph.id, cloned_rgraph.id)
        self.assertEqual(rgraph.name,  cloned_rgraph.name)

        self.assertEqual(rgraph.abscissa_cell_value, cloned_rgraph.abscissa_cell_value)
        self.assertEqual(rgraph.abscissa_type,       cloned_rgraph.abscissa_type)
        self.assertEqual(rgraph.abscissa_parameter,  cloned_rgraph.abscissa_parameter)

        self.assertEqual(rgraph.ordinate_type,     cloned_rgraph.ordinate_type)
        self.assertEqual(rgraph.ordinate_cell_key, cloned_rgraph.ordinate_cell_key)

        self.assertEqual(rgraph.chart, cloned_rgraph.chart)

    def test_credentials01(self):
        "Filter retrieved entities with permission."
        user = self.login(is_superuser=False, allowed_apps=['creme_core', 'reports'])
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE,
            set_type=SetCredentials.ESET_OWN,
        )

        other_user = self.other_user
        report = self._create_simple_organisations_report()

        create_orga = FakeOrganisation.objects.create
        create_orga(name='O#1', user=user)
        create_orga(name='O#2', user=user, capital=100)
        create_orga(name='O#3', user=user, capital=200)
        # Cannot be seen => should not be used to compute aggregate
        create_orga(name='O#4', user=other_user, capital=300)

        name = 'Max capital per user'
        self.assertNoFormError(self.client.post(
            self._build_add_graph_url(report),
            data={
                'user': user.id,
                'name': name,
                'chart': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeOrganisation._meta.get_field('user'),
                    # graph_type=RGT_FK,
                    graph_type=ReportGraph.Group.FK,
                ),
                'ordinate': self.formfield_value_ordinate(
                    # aggr_id=RGA_MAX,
                    aggr_id=ReportGraph.Aggregator.MAX,
                    cell=EntityCellRegularField.build(FakeOrganisation, 'capital'),
                ),
            })
        )
        rgraph = self.get_object_or_fail(ReportGraph, linked_report=report, name=name)

        response = self.assertGET200(self._builf_fetch_url(rgraph, 'ASC'))
        data = response.json()
        users = sorted(get_user_model().objects.all(), key=str)
        self.assertListEqual([str(u) for u in users], data.get('x'))

        y_data = data.get('y')

        def get_user_index(user_id):
            index = next((i for i, u in enumerate(users) if user_id == u.id), None)
            self.assertIsNotNone(index)
            return index

        self.assertEqual(200, y_data[get_user_index(user.id)][0])
        self.assertEqual(0,   y_data[get_user_index(other_user.id)][0])  # Not 300

    def test_credentials02(self):
        "Filter retrieved entities with permission (brick + regular field version)."
        user = self.login(is_superuser=False, allowed_apps=['creme_core', 'reports'])
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE,
            set_type=SetCredentials.ESET_OWN,
        )

        folder = FakeReportsFolder.objects.create(title='my Folder', user=user)

        create_doc = partial(FakeReportsDocument.objects.create, linked_folder=folder)
        doc1 = create_doc(title='Doc#1', user=user)
        create_doc(title='Doc#2', user=user)
        # Cannot be seen => should not be used to compute aggregate
        doc3 = create_doc(title='Doc#3', user=self.other_user)
        self.assertEqual(doc1.created.year, doc3.created.year)

        rgraph = self._create_documents_rgraph()
        fetcher = RegularFieldLinkedGraphFetcher(graph=rgraph, value='linked_folder')
        self.assertIsNone(fetcher.error)

        ibci = fetcher.create_brick_config_item()
        response = self.assertGET200(self._build_fetchfrombrick_url(ibci, folder, 'ASC'))

        result = response.json()
        self.assertListEqual([str(doc1.created.year)], result.get('x'))
        self.assertEqual(2, result.get('y')[0][0])
