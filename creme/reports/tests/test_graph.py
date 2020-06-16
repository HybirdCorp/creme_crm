# -*- coding: utf-8 -*-

from decimal import Decimal
from functools import partial
from json import loads as json_load
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models.query_utils import Q
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

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
from ..constants import (
    RGA_AVG,
    RGA_COUNT,
    RGA_MAX,
    RGA_MIN,
    RGA_SUM,
    RGF_FK,
    RGF_NOLINK,
    RGF_RELATION,
    RGT_CUSTOM_DAY,
    RGT_CUSTOM_FK,
    RGT_CUSTOM_MONTH,
    RGT_CUSTOM_RANGE,
    RGT_CUSTOM_YEAR,
    RGT_DAY,
    RGT_FK,
    RGT_MONTH,
    RGT_RANGE,
    RGT_RELATION,
    RGT_YEAR,
)
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

    def _build_add_graph_url(self, report):
        return reverse('reports__create_graph', args=(report.id,))

    def _build_add_brick_url(self, rgraph):
        return reverse('reports__create_instance_brick', args=(rgraph.id,))

    def _build_edit_url(self, rgraph):
        return reverse('reports__edit_graph', args=(rgraph.id,))

    def _builf_fetch_url(self, rgraph, order='ASC', chart=None, save_settings=None):
        uri = '{}?order={}'.format(reverse('reports__fetch_graph', args=(rgraph.id,)), order)

        if chart is not None:
            uri += f'&chart={chart}'

        if save_settings is not None:
            uri += f'&save_settings={save_settings}'

        return uri

    def _build_fetchfrombrick_url(self, ibi, entity, order='ASC', chart=None, save_settings=None):
        uri = '{}?order={}'.format(
            reverse('reports__fetch_graph_from_brick', args=(ibi.id, entity.id)),
            order,
        )

        if chart is not None:
            uri += f'&chart={chart}'

        if save_settings is not None:
            uri += f'&save_settings={save_settings}'

        return uri

    def _build_graph_types_url(self, ct):
        return reverse('reports__graph_types', args=(ct.id,))

    # def _create_documents_rgraph(self, user=None):
    #     user = user or self.user
    #     report = self._create_simple_documents_report(user)
    #     return ReportGraph.objects.create(
    #         user=user, linked_report=report,
    #         name='Number of created documents / year',
    #         abscissa='created', type=RGT_YEAR,
    #         ordinate='', is_count=True,
    #     )

    # def _create_invoice_report_n_graph(self, abscissa='issuing_date', ordinate='total_no_vat__sum'):
    def _create_invoice_report_n_graph(self, abscissa='issuing_date',
                                       ordinate_type=RGA_SUM, ordinate_field='total_no_vat'):
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
            # abscissa=abscissa, type=RGT_MONTH,
            abscissa_cell_value=abscissa,
            abscissa_type=RGT_MONTH,
            # ordinate=ordinate,
            # is_count=False,
            ordinate_type=ordinate_type,
            ordinate_cell_key=f'regular_field-{ordinate_field}',
        )

    def _serialize_qfilter(self, **kwargs):
        return self.qfilter_serializer.dumps(Q(**kwargs))

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
        self.assertURL(builder({'id': 1}), FakeContact, expected_q=Q(id=1), expected_efilter_id='test-filter')

    def test_listview_URL_builder02(self):
        "Model without list-view."
        with self.assertNoException():
            builder = ListViewURLBuilder(FakeSector)

        self.assertIsNone(builder(None))
        self.assertIsNone(builder({'id': '1'}))

    def test_createview01(self):
        "RGT_FK."
        user = self.login()
        report = self._create_simple_organisations_report()
        # cf = CustomField.objects.create(content_type=report.ct,
        #                                 name='Soldiers', field_type=CustomField.INT,
        #                                )

        url = self._build_add_graph_url(report)
        context = self.assertGET200(url).context
        self.assertEqual(_('Create a graph for «{entity}»').format(entity=report),
                         context.get('title')
                        )
        self.assertEqual(ReportGraph.save_label, context.get('submit_label'))

        # with self.assertNoException():
        #     fields = context['form'].fields
        #     abscissa_choices = fields['abscissa_field'].choices
        #     aggrfields_choices = fields['aggregate_field'].choices
        #
        # self.assertEqual(2, len(abscissa_choices))
        #
        # fields_choices = abscissa_choices[0]
        # self.assertEqual(_('Fields'), fields_choices[0])
        # choices_set = {c[0] for c in fields_choices[1]}
        # self.assertIn('created', choices_set)
        # self.assertIn('sector',  choices_set)
        # self.assertNotIn('name', choices_set)  # String can not be used to group
        # self.assertNotIn('address', choices_set)  # Not enumerable
        # self.assertNotIn('image',   choices_set)  # FK to entity
        #
        # rel_choices = abscissa_choices[1]
        # self.assertEqual(_('Relationships'), rel_choices[0])
        # self.get_object_or_fail(RelationType, pk=rel_choices[1][0][0])
        #
        # self.assertEqual([(_('Fields'),        [('capital', _('Capital'))]),
        #                   (_('Custom fields'), [(cf.id,     cf.name)]),
        #                  ],
        #                  aggrfields_choices
        #                 )

        name = 'My Graph #1'
        abscissa = 'sector'
        gtype = RGT_FK
        chart = 'barchart'
        self.assertNoFormError(
            self.client.post(
                url,
                data={
                    'user': user.pk,  # TODO: report.user used instead ??
                    'name': name,

                    # 'abscissa_field':    abscissa,
                    # 'abscissa_group_by': gtype,
                    'abscissa': self.formfield_value_abscissa(
                        abscissa=FakeOrganisation._meta.get_field(abscissa),
                        graph_type=gtype,
                    ),

                    # 'is_count': True,
                    'ordinate': self.formfield_value_ordinate(aggr_id=RGA_COUNT),

                    'chart': chart,
                },
            )
        )

        rgraph = self.get_object_or_fail(ReportGraph, linked_report=report, name=name)
        self.assertEqual(user,      rgraph.user)
        # self.assertEqual(abscissa,  rgraph.abscissa)
        self.assertEqual(abscissa,  rgraph.abscissa_cell_value)
        # self.assertEqual('',        rgraph.ordinate)
        self.assertEqual(RGA_COUNT, rgraph.ordinate_type)
        self.assertEqual('',        rgraph.ordinate_cell_key)
        # self.assertEqual(gtype,     rgraph.type)
        self.assertEqual(gtype,     rgraph.abscissa_type)
        self.assertEqual(chart,     rgraph.chart)
        # self.assertIsNone(rgraph.days)
        self.assertIsNone(rgraph.abscissa_parameter)
        # self.assertIs(rgraph.is_count, True)
        self.assertIs(rgraph.asc,      True)

        hand = rgraph.hand
        self.assertEqual(_('Sector'), hand.verbose_abscissa)
        self.assertEqual(_('Count'),  hand.verbose_ordinate)
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
        self.assertIsInstance(y_asc, list)
        self.assertEqual(len(x_asc), len(y_asc))
        self.assertEqual(
            [0, '/tests/organisations?q_filter={}'.format(self._serialize_qfilter(sector=sectors[0].id))],
            y_asc[0]
        )

        # ------------------------------------------------------------
        self.assertGET200(self._builf_fetch_url(rgraph, 'DESC'))
        self.assertGET404(self._builf_fetch_url(rgraph, 'STUFF'))

    def test_createview02(self):
        "Ordinate with aggregate + RGT_DAY."
        user = self.login()
        report = self._create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        ordinate = 'capital'
        gtype = RGT_DAY

        def post(**kwargs):
            return self.client.post(
                url,
                data={
                    'user': user.id,
                    'name': name,
                    # 'abscissa_group_by': gtype,
                    'chart': 'barchart',
                    **kwargs
                },
            )

        # response = post(abscissa_field='modified')
        # self.assertEqual(200, response.status_code)
        # self.assertFormError(
        #     response, 'form', None,
        #     _("If you don't choose an ordinate field (or none available) "
        #       "you have to check 'Make a count instead of aggregate ?'"
        #     )
        #  )

        # response = post(abscissa_field='legal_form', aggregate_field=ordinate)
        response = post(
            abscissa=self.formfield_value_abscissa(
                abscissa=FakeOrganisation._meta.get_field('legal_form'),
                graph_type=gtype,
            ),
            # aggregate_field=ordinate,
            ordinate=self.formfield_value_ordinate(
                aggr_id=RGA_MAX,
                cell=EntityCellRegularField.build(FakeOrganisation, 'name'),
            ),
        )
        self.assertEqual(200, response.status_code)
        # self.assertFormError(
        #     response, 'form', 'abscissa_field',
        #     '"{}" groups are only compatible with [DateField, DateTimeField]'.format(_('By days'))
        # )
        self.assertFormError(
            response, 'form', 'abscissa',
            'This entity cell is not allowed.'
        )
        # self.assertFormError(
        #     response, 'form', 'aggregate',
        #     _('This field is required if you choose a field to aggregate.')
        # )
        self.assertFormError(
            response, 'form', 'ordinate',
            'This entity cell is not allowed.'
        )

        aggregate = RGA_MAX
        abscissa = 'created'
        # self.assertNoFormError(post(abscissa_field=abscissa,
        #                             aggregate_field=ordinate,
        #                             aggregate=aggregate,
        #                            )
        #                       )
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
        # self.assertEqual(abscissa,  rgraph.abscissa)
        # self.assertEqual(gtype, rgraph.type)
        # self.assertIsNone(rgraph.days)
        self.assertEqual(abscissa,  rgraph.abscissa_cell_value)
        self.assertEqual(gtype,     rgraph.abscissa_type)
        self.assertIsNone(rgraph.abscissa_parameter)
        # self.assertEqual(f'{ordinate}__{aggregate}', rgraph.ordinate)
        # self.assertFalse(rgraph.is_count)
        self.assertEqual(aggregate,                   rgraph.ordinate_type)
        self.assertEqual(f'regular_field-{ordinate}', rgraph.ordinate_cell_key)

        hand = rgraph.hand
        self.assertEqual(_('Creation date'), hand.verbose_abscissa)
        self.assertEqual('{} - {}'.format(_('Capital'), _('Maximum')),
                         hand.verbose_ordinate
                        )
        self.assertEqual(_('Maximum'), hand.ordinate.verbose_name)
        self.assertEqual(_('Capital'), str(hand.ordinate.cell))

    # def test_createview03(self):
    #     "'aggregate_field' empty ==> 'is_count' mandatory."
    #     user = self.login()
    #     report = self._create_simple_contacts_report()
    #     url = self._build_add_graph_url(report)
    #     response = self.assertGET200(url)
    #
    #     with self.assertNoException():
    #         fields = response.context['form'].fields
    #         fields_choices = fields['abscissa_field'].choices[0][1]
    #
    #     choices_set = {c[0] for c in fields_choices}
    #     self.assertIn('created', choices_set)
    #     self.assertIn('sector', choices_set)
    #     self.assertIn('civility', choices_set)
    #     self.assertNotIn('last_name', choices_set)
    #
    #     name = 'My Graph #1'
    #     abscissa = 'sector'
    #     self.assertNoFormError(self.client.post(
    #         url,
    #         data={
    #             'user': user.id,
    #             'name': name,
    #             'chart': 'barchart',
    #
    #             # 'abscissa_field':     abscissa,
    #             # 'abscissa_group_by':  RGT_FK,
    #
    #             # 'is_count': True, #useless
    #         },
    #     ))
    #     rgraph = self.get_object_or_fail(ReportGraph, linked_report=report, name=name)
    #     self.assertEqual(abscissa, rgraph.abscissa)
    #     self.assertEqual('',       rgraph.ordinate)
    #     self.assertTrue(rgraph.is_count)

    # def test_createview04(self):
    def test_createview03(self):
        "RGT_RELATION."
        user = self.login()
        report = self._create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        gtype = RGT_RELATION

        # def post(abscissa):
        #     return self.client.post(url,
        #                             data={'user':              user.pk,
        #                                   'name':              name,
        #                                   'abscissa_field':    abscissa,
        #                                   'abscissa_group_by': gtype,
        #                                   'is_count':          True,
        #                                   'chart':             'barchart',
        #                                  },
        #                            )

        # fname = 'staff_size'
        # response = post(fname)
        # self.assertEqual(200, response.status_code)
        # self.assertFormError(response, 'form', 'abscissa_field',
        #                      'Unknown relationship type.'
        #                     )

        rtype_id = fake_constants.FAKE_REL_OBJ_EMPLOYED_BY
        # self.assertNoFormError(post(rtype_id))
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

                # 'is_count': True,
                'ordinate': self.formfield_value_ordinate(aggr_id=RGA_COUNT),
            },
        ))

        rgraph = self.get_object_or_fail(ReportGraph, linked_report=report, name=name)
        self.assertEqual(user,      rgraph.user)
        # self.assertEqual(rtype_id,  rgraph.abscissa)
        self.assertEqual(rtype_id,  rgraph.abscissa_cell_value)
        # self.assertEqual('',        rgraph.ordinate)
        # self.assertTrue(rgraph.is_count)
        self.assertEqual(RGA_COUNT, rgraph.ordinate_type)
        self.assertEqual('',        rgraph.ordinate_cell_key)

        self.assertEqual('employs', rgraph.hand.verbose_abscissa)

    # def _aux_test_createview_with_date(self, gtype, gtype_vname):
    def _aux_test_createview_with_date(self, gtype):
        report = self._create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        ordinate = 'capital'
        aggregate = RGA_MIN

        # def post(**kwargs):
        def post(abscissa_field, **kwargs):
            return self.client.post(
                url,
                data={
                    'user': self.user.pk,
                    'name': name,
                    'chart': 'barchart',

                    # 'abscissa_group_by': gtype,
                    'abscissa': self.formfield_value_abscissa(
                        abscissa=FakeOrganisation._meta.get_field(abscissa_field),
                        graph_type=gtype,
                    ),

                    # 'aggregate_field': ordinate,
                    # 'aggregate':      'max',
                    'ordinate': self.formfield_value_ordinate(
                        aggr_id=aggregate,
                        cell=EntityCellRegularField.build(FakeOrganisation, ordinate),
                    ),

                    **kwargs
                },
            )

        response = post(abscissa_field='legal_form')
        self.assertEqual(200, response.status_code)
        # self.assertFormError(
        #     response, 'form', 'abscissa_field',
        #     f'"{gtype_vname}" groups are only compatible with [DateField, DateTimeField]'
        # )
        self.assertFormError(
            response, 'form', 'abscissa',
            'This entity cell is not allowed.'
        )

        abscissa = 'created'
        # self.assertNoFormError(post(abscissa_field=abscissa, aggregate=aggregate))
        self.assertNoFormError(post(abscissa_field=abscissa))

        rgraph = self.get_object_or_fail(ReportGraph, linked_report=report, name=name)
        self.assertEqual(self.user, rgraph.user)
        # self.assertEqual(abscissa,  rgraph.abscissa)
        self.assertEqual(abscissa,  rgraph.abscissa_cell_value)
        # self.assertEqual(f'{ordinate}__{aggregate}', rgraph.ordinate)
        # self.assertEqual(gtype, rgraph.type)
        self.assertEqual(gtype, rgraph.abscissa_type)
        # self.assertIsNone(rgraph.days)
        self.assertIsNone(rgraph.abscissa_parameter)
        # self.assertFalse(rgraph.is_count)
        self.assertEqual(aggregate,                   rgraph.ordinate_type)
        self.assertEqual(f'regular_field-{ordinate}', rgraph.ordinate_cell_key)

    # def test_createview05(self):
    def test_createview04(self):
        "RGT_MONTH."
        self.login()
        # self._aux_test_createview_with_date(RGT_MONTH, _('By months'))
        self._aux_test_createview_with_date(RGT_MONTH)

    # def test_createview06(self):
    def test_createview05(self):
        "RGT_YEAR."
        self.login()
        # self._aux_test_createview_with_date(RGT_YEAR, _('By years'))
        self._aux_test_createview_with_date(RGT_YEAR)

    # def test_createview07(self):
    def test_createview06(self):
        "RGT_RANGE."
        user = self.login()
        report = self._create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        ordinate = 'capital'
        gtype = RGT_RANGE

        # def post(**kwargs):
        def post(abscissa_field, parameter='', aggr_id=RGA_MAX, **kwargs):
            return self.client.post(
                url,
                data={
                    'user': user.id,
                    'name': name,
                    'chart': 'barchart',

                    # 'abscissa_group_by': gtype,
                    'abscissa': self.formfield_value_abscissa(
                        abscissa=FakeOrganisation._meta.get_field(abscissa_field),
                        graph_type=gtype,
                        parameter=parameter,
                    ),

                    # 'aggregate_field': ordinate,
                    # 'aggregate':       'max',
                    'ordinate': self.formfield_value_ordinate(
                        aggr_id=aggr_id,
                        cell=EntityCellRegularField.build(FakeOrganisation, ordinate),
                    ),

                    **kwargs
                },
            )

        response = post(abscissa_field='legal_form')
        self.assertEqual(200, response.status_code)
        # self.assertFormError(
        #     response, 'form', 'abscissa_field',
        #     '"{}" groups are only compatible with [DateField, DateTimeField]'.format(_('By X days'))
        # )
        self.assertFormError(
            response, 'form', 'abscissa',
            'This entity cell is not allowed.'
        )
        # self.assertFormError(
        #     response, 'form', 'days',
        #     _("You have to specify a day range if you use 'by X days'")
        # )

        aggregate = RGA_AVG
        abscissa = 'modified'
        # days = 25
        days = '25'
        # self.assertNoFormError(post(abscissa_field=abscissa, aggregate=aggregate, days=days))
        self.assertNoFormError(post(abscissa_field=abscissa, parameter=days, aggr_id=aggregate))

        rgraph = self.get_object_or_fail(ReportGraph, linked_report=report, name=name)
        self.assertEqual(user, rgraph.user)
        # self.assertEqual(gtype, rgraph.type)
        # self.assertEqual(abscissa, rgraph.abscissa)
        # self.assertEqual(days, rgraph.days)
        self.assertEqual(abscissa, rgraph.abscissa_cell_value)
        self.assertEqual(gtype,    rgraph.abscissa_type)
        self.assertEqual(days,     rgraph.abscissa_parameter)
        # self.assertEqual(f'{ordinate}__{aggregate}', rgraph.ordinate)
        # self.assertFalse(rgraph.is_count)
        self.assertEqual(aggregate,                   rgraph.ordinate_type)
        self.assertEqual(f'regular_field-{ordinate}', rgraph.ordinate_cell_key)

    # def test_createview08(self):
    def test_createview07(self):
        "RGT_CUSTOM_FK."
        user = self.login()

        create_cf = partial(CustomField.objects.create, content_type=self.ct_contact)
        cf_enum    = create_cf(name='Hair',        field_type=CustomField.ENUM)      # OK for abscissa (group by), not for ordinate (aggregate)
        # cf_dt      = create_cf(name='First fight', field_type=CustomField.DATETIME)  # idem
        # cf_int     = create_cf(name='Size (cm)',   field_type=CustomField.INT)       # INT -> not usable for abscissa , but OK for ordinate
        # cf_decimal = create_cf(name='Weight (kg)', field_type=CustomField.FLOAT)     # FLOAT -> not usable for abscissa , but OK for ordinate

        # # Bad CT
        # ct_orga = self.ct_orga
        # create_cf(content_type=ct_orga, name='Totem', field_type=CustomField.ENUM)
        # create_cf(content_type=ct_orga, name='Gold',  field_type=CustomField.INT)
        #
        # create_enum_value = partial(CustomFieldEnumValue.objects.create, custom_field=cf_enum)
        # blue = create_enum_value(value='Blue')
        # red  = create_enum_value(value='Red')
        # create_enum_value(value='Black')  # Not used
        #
        # create_contact = partial(FakeContact.objects.create, user=user)
        # ryomou  = create_contact(first_name='Ryomou',  last_name='Shimei')
        # kanu    = create_contact(first_name='Kan-u',   last_name='Unchô')
        # sonsaku = create_contact(first_name='Sonsaku', last_name='Hakuf')
        #
        # create_enum = partial(CustomFieldEnum.objects.create, custom_field=cf_enum)
        # create_enum(entity=ryomou,  value=blue)
        # create_enum(entity=kanu,    value=blue)
        # create_enum(entity=sonsaku, value=red)

        report = self._create_simple_contacts_report()
        url = self._build_add_graph_url(report)

        # response = self.assertGET200(url)
        #
        # with self.assertNoException():
        #     fields = response.context['form'].fields
        #     abs_choices = fields['abscissa_field'].choices
        #     ord_choices = fields['aggregate_field'].choices

        # self.assertEqual(3, len(abs_choices))
        #
        # cf_choice = abs_choices[2]
        # self.assertEqual(_('Custom fields'), cf_choice[0])
        # self.assertSetEqual({(cf_enum.id, cf_enum.name),
        #                      (cf_dt.id,   cf_dt.name),
        #                     },
        #                     {*cf_choice[1]}
        #                    )

        # self.assertEqual([(cf_int.id, cf_int.name), (cf_decimal.id, cf_decimal.name)],
        #                  ord_choices
        #                 )

        name = 'My Graph #1'
        gtype = RGT_CUSTOM_FK

        # def post(cf_id):
        #     return self.client.post(url, data={'user':              user.pk,
        #                                        'name':              name,
        #                                        'abscissa_field':    cf_id,
        #                                        'abscissa_group_by': gtype,
        #                                        'is_count':          True,
        #                                        'chart':             'barchart',
        #                                       },
        #                            )
        #
        # response = post(1000)
        # self.assertEqual(200, response.status_code)
        # self.assertFormError(response, 'form', 'abscissa_field',
        #                      'Unknown or invalid custom field.'
        #                     )
        #
        # self.assertNoFormError(post(cf_enum.id))

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
                'ordinate': self.formfield_value_ordinate(aggr_id=RGA_COUNT),
            },
        ))

        rgraph = self.get_object_or_fail(ReportGraph, linked_report=report, name=name)
        self.assertEqual(user,            rgraph.user)
        # self.assertEqual(str(cf_enum.id), rgraph.abscissa)
        self.assertEqual(str(cf_enum.id), rgraph.abscissa_cell_value)
        # self.assertEqual(gtype,           rgraph.type)
        self.assertEqual(gtype,           rgraph.abscissa_type)

    def _aux_test_createview_with_customdate(self, gtype):
        # create_cf = partial(CustomField.objects.create, content_type=self.ct_orga)
        # cf_dt  = create_cf(name='First victory', field_type=CustomField.DATETIME)
        # cf_int = create_cf(name='Gold',          field_type=CustomField.INT)
        cf_dt = CustomField.objects.create(
            content_type=self.ct_orga,
            name='First victory',
            field_type=CustomField.DATETIME,
        )

        report = self._create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'

        # def post(**kwargs):
        #     return self.client.post(
        #         url,
        #         data={
        #             'user':              self.user.pk,
        #             'name':              name,
        #             'abscissa_group_by': gtype,
        #             'is_count':          True,
        #             'chart':             'barchart',
        #             **kwargs
        #            },
        #     )
        #
        # response = post(abscissa_field=cf_int.id)
        # self.assertEqual(200, response.status_code)
        # self.assertFormError(response, 'form', 'abscissa_field',
        #                      'Unknown or invalid custom field.'
        #                     )
        #
        # self.assertNoFormError(post(abscissa_field=cf_dt.id))
        self.assertNoFormError(self.client.post(
            url,
            data={
                'user': self.user.pk,
                'name': name,
                'chart': 'barchart',
                'abscissa': self.formfield_value_abscissa(
                    abscissa=cf_dt,
                    graph_type=gtype,
                ),
                'ordinate': self.formfield_value_ordinate(aggr_id=RGA_COUNT),
            },
        ))

        rgraph = self.get_object_or_fail(ReportGraph, linked_report=report, name=name)
        self.assertEqual(self.user,     rgraph.user)
        # self.assertEqual(str(cf_dt.id), rgraph.abscissa)
        self.assertEqual(str(cf_dt.id), rgraph.abscissa_cell_value)
        # self.assertEqual(gtype,         rgraph.type)
        self.assertEqual(gtype,         rgraph.abscissa_type)
        self.assertEqual(RGA_COUNT,       rgraph.ordinate_type)
        self.assertEqual('',            rgraph.ordinate_cell_key)

        self.assertEqual(cf_dt.name, rgraph.hand.verbose_abscissa)

    # def test_createview09(self):
    def test_createview08(self):
        "RGT_CUSTOM_DAY."
        self.login()
        self._aux_test_createview_with_customdate(RGT_CUSTOM_DAY)

    # def test_createview10(self):
    def test_createview09(self):
        "RGT_CUSTOM_MONTH."
        self.login()
        self._aux_test_createview_with_customdate(RGT_CUSTOM_MONTH)

    # def test_createview11(self):
    def test_createview10(self):
        "RGT_CUSTOM_YEAR."
        self.login()
        self._aux_test_createview_with_customdate(RGT_CUSTOM_YEAR)

    # def test_createview12(self):
    def test_createview11(self):
        "RGT_CUSTOM_RANGE."
        user = self.login()

        create_cf = partial(CustomField.objects.create, content_type=self.ct_orga)
        cf_dt  = create_cf(name='First victory', field_type=CustomField.DATETIME)
        # cf_int = create_cf(name='Gold',          field_type=CustomField.INT)

        report = self._create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        gtype = RGT_CUSTOM_RANGE

        # def post(**kwargs):
        #     return self.client.post(
        #         url,
        #         data={'user':              user.pk,
        #               'name':              name,
        #               'abscissa_group_by': gtype,
        #               'is_count':          True,
        #               'chart':             'barchart',
        #               **kwargs
        #         },
        #     )
        #
        # response = post(abscissa_field=cf_int.id)
        # self.assertEqual(200, response.status_code)
        # self.assertFormError(response, 'form', 'abscissa_field',
        #                      'Unknown or invalid custom field.'
        #                     )
        # self.assertFormError(response, 'form', 'days',
        #                      _("You have to specify a day range if you use 'by X days'")
        #                     )

        # days = 25
        days = '25'
        # self.assertNoFormError(post(abscissa_field=cf_dt.id, days=days))
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
                'ordinate': self.formfield_value_ordinate(aggr_id=RGA_COUNT),
            },
        ))

        rgraph = self.get_object_or_fail(ReportGraph, linked_report=report, name=name)
        self.assertEqual(user,          rgraph.user)
        # self.assertEqual(str(cf_dt.id), rgraph.abscissa)
        self.assertEqual(str(cf_dt.id), rgraph.abscissa_cell_value)
        # self.assertEqual(gtype,         rgraph.type)
        self.assertEqual(gtype,         rgraph.abscissa_type)
        # self.assertEqual(days,          rgraph.days)
        self.assertEqual(days,          rgraph.abscissa_parameter)
        self.assertEqual(RGA_COUNT,     rgraph.ordinate_type)
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

        url = self._build_add_graph_url(report)
        # response = self.assertGET200(url)
        #
        # with self.assertNoException():
        #     fields = response.context['form'].fields
        #     abscissa_choices = fields['abscissa_field'].choices
        #     aggrfields_choices = fields['aggregate_field'].choices
        #
        # fields_choices = abscissa_choices[0]
        # self.assertEqual(_('Fields'), fields_choices[0])
        #
        # choices_set = {c[0] for c in fields_choices[1]}
        # self.assertIn('created', choices_set)
        # self.assertNotIn(hidden_fname1, choices_set)
        #
        # self.assertEqual([('', _('No field is usable for aggregation'))],
        #                  aggrfields_choices
        #                 )

        response = self.assertPOST200(
            url,
            data={
                'user': user.pk,
                'name': 'My Graph #1',
                'chart': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeOrganisation._meta.get_field(hidden_fname1),
                    graph_type=RGT_FK,
                ),

                # 'is_count': True,
                'ordinate': self.formfield_value_ordinate(
                    aggr_id=RGA_SUM,
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
            ordinate_type=RGA_SUM,
            ordinate_cell_key='regular_field-capital',
        )

        rgraph.abscissa_info = AbscissaInfo(
            graph_type=RGT_FK,
            cell=EntityCellRegularField.build(FakeOrganisation, 'capital'),
        )
        self.assertEqual('capital', rgraph.abscissa_cell_value)
        self.assertEqual(RGT_FK, rgraph.abscissa_type)
        self.assertIsNone(rgraph.abscissa_parameter)

        abs_info1 = rgraph.abscissa_info
        self.assertIsInstance(abs_info1, AbscissaInfo)
        self.assertEqual(RGT_FK, abs_info1.graph_type)
        self.assertIsNone(abs_info1.parameter)
        self.assertEqual('regular_field-capital', abs_info1.cell.key)

        # ---
        rgraph.abscissa_info = AbscissaInfo(
            graph_type=RGT_RANGE,
            cell=EntityCellRegularField.build(FakeOrganisation, 'created'),
            parameter='3',
        )
        self.assertEqual('created', rgraph.abscissa_cell_value)
        self.assertEqual(RGT_RANGE, rgraph.abscissa_type)
        self.assertEqual('3', rgraph.abscissa_parameter)

        abs_info2 = rgraph.abscissa_info
        self.assertEqual(RGT_RANGE, abs_info2.graph_type)
        self.assertEqual('regular_field-created', abs_info2.cell.key)
        self.assertEqual('3', abs_info2.parameter)

    def test_ordinate_info01(self):
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph(
            user=user, linked_report=report,
            name='Capital per month of creation',
        )
        aggr_id1 = RGA_MAX
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
        aggr_id2 = RGA_MIN
        rgraph.ordinate_info = OrdinateInfo(aggr_id=aggr_id2, cell=cell2)

        self.assertEqual(aggr_id2,  rgraph.ordinate_type)
        self.assertEqual(cell2.key, rgraph.ordinate_cell_key)

        ord_info2 = rgraph.ordinate_info
        self.assertEqual(aggr_id2,  ord_info2.aggr_id)
        self.assertEqual(cell2.key, ord_info2.cell.key)

        # ---
        aggr_id3 = RGA_COUNT
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
        aggr_id = RGA_MAX
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
            # abscissa='created', type=RGT_MONTH,
            abscissa_cell_value='created',
            abscissa_type=RGT_MONTH,
            # ordinate='capital__sum', is_count=False,
            ordinate_type=RGA_SUM,
            ordinate_cell_key='regular_field-capital',
        )

        url = self._build_edit_url(rgraph)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Edit a graph for «{entity}»').format(entity=report),
                         context.get('title')
                        )

        with self.assertNoException():
            fields = context['form'].fields
            abscissa_f = fields['abscissa']
            # aggregate_field_f = fields['aggregate_field']

        self.assertSetEqual({'regular_field-created'},
                            abscissa_f.not_hiddable_cell_keys
                           )
        # self.assertFalse(aggregate_field_f.help_text)

        name = 'Organisations per sector'
        abscissa = 'sector'
        gtype = RGT_FK
        self.assertNoFormError(self.client.post(
            url,
            data={
                'user': user.pk,
                'name': name,
                'chart': 'barchart',

                # 'abscissa_field':    abscissa,
                # 'abscissa_group_by': gtype,
                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeOrganisation._meta.get_field(abscissa),
                    graph_type=gtype,
                ),

                # 'is_count': True,
                'ordinate': self.formfield_value_ordinate(aggr_id=RGA_COUNT),
            },
        ))

        rgraph = self.refresh(rgraph)
        self.assertEqual(name,     rgraph.name)
        # self.assertEqual(abscissa, rgraph.abscissa)
        self.assertEqual(abscissa, rgraph.abscissa_cell_value)
        # self.assertEqual('',       rgraph.ordinate)
        self.assertEqual(RGA_COUNT,  rgraph.ordinate_type)
        # self.assertEqual(gtype,    rgraph.type)
        self.assertEqual(gtype,    rgraph.abscissa_type)
        # self.assertIsNone(rgraph.days)
        self.assertIsNone(rgraph.abscissa_parameter)
        # self.assertTrue(rgraph.is_count)

    def test_editview02(self):
        "Another ContentType."
        user = self.login()
        rgraph = self._create_invoice_report_n_graph()
        url = self._build_edit_url(rgraph)
        response = self.assertGET200(url)

        with self.assertNoException():
            # aggregate_field_f = response.context['form'].fields['aggregate_field']
            ordinate_f = response.context['form'].fields['ordinate']

        self.assertEqual(
            _('If you use a field related to money, the entities should use the same '
              'currency or the result will be wrong. Concerned fields are : {}'
             ).format('{}, {}'.format(_('Total with VAT'), _('Total without VAT'))),
            # aggregate_field_f.help_text
            ordinate_f.help_text
        )

        abscissa = 'created'
        gtype = RGT_DAY
        self.assertNoFormError(self.client.post(
            url,
            data={
                'user': user.pk,
                'name': rgraph.name,
                'chart': 'barchart',

                # 'abscissa_field':    abscissa,
                # 'abscissa_group_by': gtype,
                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeInvoice._meta.get_field(abscissa),
                    graph_type=gtype,
                ),

                # 'aggregate_field': 'total_vat',
                # 'aggregate':       'avg',
                'ordinate': self.formfield_value_ordinate(
                    aggr_id=RGA_AVG,
                    cell=EntityCellRegularField.build(FakeInvoice, 'total_vat'),
                ),
            },
        ))

        rgraph = self.refresh(rgraph)
        # self.assertEqual(abscissa,         rgraph.abscissa)
        self.assertEqual(abscissa,         rgraph.abscissa_cell_value)
        # self.assertEqual('total_vat__avg', rgraph.ordinate)
        # self.assertEqual(gtype,            rgraph.type)
        self.assertEqual(gtype,            rgraph.abscissa_type)
        # self.assertIsNone(rgraph.days)
        self.assertIsNone(rgraph.abscissa_parameter)
        # self.assertFalse(rgraph.is_count)
        self.assertEqual(RGA_AVG,                     rgraph.ordinate_type)
        self.assertEqual('regular_field-total_vat', rgraph.ordinate_cell_key)

    def test_editview03(self):
        "With FieldsConfig."
        user = self.login()
        # rgraph = self._create_invoice_report_n_graph(ordinate='total_vat__sum')
        rgraph = self._create_invoice_report_n_graph(
            ordinate_type=RGA_SUM,
            ordinate_field='total_vat',
        )

        # hidden_fname1 = 'expiration_date'
        hidden_fname = 'total_no_vat'
        FieldsConfig.objects.create(
            content_type=FakeInvoice,
            descriptions=[
                # (hidden_fname1,  {FieldsConfig.HIDDEN: True}),
                ('total_no_vat',    {FieldsConfig.HIDDEN: True}),
            ],
        )

        # response = self.assertGET200(self._build_edit_url(rgraph))
        #
        # with self.assertNoException():
        #     fields = response.context['form'].fields
        #     abscissa_choices = fields['abscissa_field'].choices
        #     aggrfields_choices = fields['aggregate_field'].choices
        #
        # fields_choices = abscissa_choices[0]
        # self.assertEqual(_('Fields'), fields_choices[0])
        #
        # choices_set = {c[0] for c in fields_choices[1]}
        # self.assertIn('created', choices_set)
        # self.assertNotIn(hidden_fname1, choices_set)
        #
        # self.assertEqual([('total_vat', _('Total with VAT'))],
        #                  aggrfields_choices
        #                 )
        response = self.assertPOST200(
            self._build_edit_url(rgraph),
            data={
                'user': user.pk,
                'name': rgraph.name,
                'chart': 'barchart',

                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeInvoice._meta.get_field('expiration_date'),
                    graph_type=RGT_MONTH,
                ),

                'ordinate': self.formfield_value_ordinate(
                    aggr_id=RGA_AVG,
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

        # url = self._build_edit_url(rgraph)
        # response = self.assertGET200(url)
        #
        # with self.assertNoException():
        #     abscissa_choices = response.context['form'].fields['abscissa_field'].choices
        #
        # fields_choices = abscissa_choices[0]
        # choices_set = {c[0] for c in fields_choices[1]}
        # self.assertIn('created', choices_set)
        # self.assertIn(hidden_fname, choices_set)

        response = self.client.post(
            self._build_edit_url(rgraph),
            data={
                'user':  rgraph.user.pk,
                'name':  rgraph.name,
                'chart': 'barchart',

                # 'abscissa_field':    hidden_fname,
                # 'abscissa_group_by': rgraph.type,
                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeInvoice._meta.get_field(hidden_fname),
                    graph_type=rgraph.abscissa_type,
                ),

                # 'aggregate_field': 'total_no_vat',
                # 'aggregate':       'sum',
                'ordinate': self.formfield_value_ordinate(
                    aggr_id=RGA_SUM,
                    cell=EntityCellRegularField.build(FakeInvoice, 'total_no_vat'),
                ),
            },
        )
        self.assertNoFormError(response)

        rgraph = self.refresh(rgraph)
        # self.assertEqual(hidden_fname, rgraph.abscissa)
        self.assertEqual(hidden_fname, rgraph.abscissa_cell_value)

        hand = rgraph.hand
        self.assertEqual(_('Expiration date'), hand.verbose_abscissa)
        self.assertEqual(_('this field should be hidden.'),
                         hand.abscissa_error
                        )

    def test_editview05(self):
        "With FieldsConfig: if fields are already selected => still proposed (ordinate)."
        self.login()
        hidden_fname = 'total_no_vat'
        # rgraph = self._create_invoice_report_n_graph(ordinate=hidden_fname + '__sum')
        rgraph = self._create_invoice_report_n_graph(
            ordinate_type=RGA_SUM,
            ordinate_field=hidden_fname,
        )

        FieldsConfig.objects.create(
            content_type=FakeInvoice,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        # response = self.assertGET200(self._build_edit_url(rgraph))
        #
        # with self.assertNoException():
        #     aggrfields_choices = response.context['form'].fields['aggregate_field'].choices
        #
        # self.assertEqual([('total_vat',    _('Total with VAT')),
        #                   ('total_no_vat', _('Total without VAT')),
        #                  ],
        #                  aggrfields_choices
        #                 )
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
            # type=RGT_CUSTOM_FK, abscissa=str(cf.id)
            abscissa_type=RGT_CUSTOM_FK,
            abscissa_cell_value=str(cf.id),
            # is_count=True,
            ordinate_type=RGA_COUNT,
        )

        response = self.assertGET200(self._build_edit_url(rgraph))

        with self.assertNoException():
            abscissa_f = response.context['form'].fields['abscissa']
            # is_count_f = response.context['form'].fields['is_count']

        # self.assertIs(is_count_f.initial, True)

        self.assertSetEqual({f'custom_field-{cf.id}'},
                            abscissa_f.not_hiddable_cell_keys
                           )

    # def test_editview06(self):
    #     "'days' field is emptied when useless"
    #     user = self.login()
    #     report = self._create_simple_organisations_report()
    #
    #     days = 15
    #     rgraph = ReportGraph.objects.create(
    #         user=user,
    #         linked_report=report,
    #         name=f'Number of orga(s) created / {days} days',
    #         abscissa='creation_date',
    #         type=RGT_RANGE, days=days,
    #         is_count=True,
    #         chart='barchart',
    #     )
    #
    #     graph_type = RGT_MONTH
    #     response = self.client.post(
    #         self._build_edit_url(rgraph),
    #         data={'user':              rgraph.user.pk,
    #               'name':              rgraph.name,
    #               'abscissa_field':    rgraph.abscissa,
    #               'abscissa_group_by': graph_type,
    #               'days':              days,  # <= should not be used
    #               'aggregate':         '',
    #               'is_count':          'on',
    #               'aggregate_field':   '',
    #               'chart':             rgraph.chart,
    #              },
    #     )
    #     self.assertNoFormError(response)
    #
    #     rgraph = self.refresh(rgraph)
    #     self.assertEqual(graph_type, rgraph.type)
    #     self.assertIsNone(rgraph.days)

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
            # abscissa='position', type=RGT_FK,
            abscissa_cell_value='position', abscissa_type=RGT_FK,
            # ordinate='', is_count=True,
            ordinate_type=RGA_COUNT,
        )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch(user)

        self.assertListEqual([*FakePosition.objects.values_list('title', flat=True)], x_asc)

        self.assertIsInstance(y_asc, list)
        self.assertEqual(len(x_asc), len(y_asc))

        fmt = lambda pk: '/tests/contacts?q_filter={}&filter=test-filter'.format(
            self._serialize_qfilter(position=pk),
        )
        self.assertEqual([1, fmt(hand.id)], y_asc[x_asc.index(hand.title)])
        self.assertEqual([2, fmt(lord.id)], y_asc[x_asc.index(lord.title)])

        # DESC ---------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC', user=user)
        self.assertListEqual([*reversed(x_asc)], x_desc)
        self.assertEqual([1, fmt(hand.id)], y_desc[x_desc.index(hand.title)])

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
            # abscissa='sector', type=RGT_FK,
            abscissa_cell_value='sector', abscissa_type=RGT_FK,
            # ordinate='capital__max', is_count=False,
            ordinate_type=RGA_MAX,
            ordinate_cell_key='regular_field-capital',
        )

        with self.assertNoException():
            # x_asc, y_asc = rgraph.fetch()
            x_asc, y_asc = rgraph.fetch(user)

        self.assertListEqual([*FakeSector.objects.values_list('title', flat=True)], x_asc)

        fmt = lambda pk: '/tests/organisations?q_filter={}&filter=test-filter'.format(
            self._serialize_qfilter(sector=pk),
        )
        index = x_asc.index
        self.assertEqual([100,  fmt(war.id)],   y_asc[index(war.title)])
        self.assertEqual([1000, fmt(trade.id)], y_asc[index(trade.title)])
        self.assertEqual([0,    fmt(peace.id)], y_asc[index(peace.title)])

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
            # abscissa='sector', type=RGT_FK,
            abscissa_cell_value='sector', abscissa_type=RGT_FK,
            # ordinate=f'{cf.id}__max', is_count=False,
            ordinate_type=RGA_MAX,
            ordinate_cell_key=f'custom_field-{cf.id}',
        )

        hand = rgraph.hand
        self.assertEqual('{} - {}'.format(cf, _('Maximum')), hand.verbose_ordinate)
        self.assertEqual(_('Maximum'), hand.ordinate.verbose_name)
        self.assertEqual(cf.name,      str(hand.ordinate.cell))

        x_asc, y_asc = rgraph.fetch(user)
        self.assertListEqual([*FakeSector.objects.values_list('title', flat=True)], x_asc)

        index = x_asc.index
        fmt = lambda pk: '/tests/organisations?q_filter={}'.format(
            self._serialize_qfilter(sector=pk),
        )
        self.assertEqual([400, fmt(war.id)],   y_asc[index(war.title)])
        self.assertEqual([500, fmt(trade.id)], y_asc[index(trade.title)])
        self.assertEqual([0,   fmt(peace.id)], y_asc[index(peace.title)])

    def test_fetch_with_fk_04(self):
        "Aggregate ordinate with invalid field."
        user = self.login()
        rgraph = ReportGraph.objects.create(
            user=user,
            linked_report=self._create_simple_organisations_report(),
            name='Max soldiers by sector',
            # abscissa='sector', type=RGT_FK,
            abscissa_cell_value='sector', abscissa_type=RGT_FK,
            # ordinate='unknown__max',  # <=====
            # is_count=False,
            ordinate_type=RGA_MAX,
            ordinate_cell_key='regular_field-unknown',  # <=====
        )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch(user)

        sectors = FakeSector.objects.all()
        self.assertEqual([s.title for s in sectors], x_asc)
        self.assertEqual(
            [0, '/tests/organisations?q_filter={}'.format(self._serialize_qfilter(sector=sectors[0].id))],
            y_asc[0]
        )
        self.assertEqual(_('the field does not exist any more.'),
                         rgraph.hand.ordinate_error
                        )

    def test_fetch_with_fk_05(self):
        "Aggregate ordinate with invalid aggregate."
        user = self.login()
        rgraph = ReportGraph.objects.create(
            user=user,
            linked_report=self._create_simple_organisations_report(),
            name='Max soldiers by sector',
            abscissa_cell_value='sector', abscissa_type=RGT_FK,
            ordinate_type='invalid',  # <=====
            ordinate_cell_key='regular_field-capital',
        )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch(user)

        sectors = FakeSector.objects.all()
        self.assertEqual([s.title for s in sectors], x_asc)
        self.assertEqual(
            [0, '/tests/organisations?q_filter={}'.format(self._serialize_qfilter(sector=sectors[0].id))],
            y_asc[0]
        )
        self.assertEqual(_('the aggregation function is invalid.'),
                         rgraph.hand.ordinate_error
                        )

    def test_fetch_with_fk_06(self):
        "Aggregate ordinate with invalid custom field."
        user = self.login()
        rgraph = ReportGraph.objects.create(
            user=user,
            linked_report=self._create_simple_organisations_report(),
            name='Max soldiers by sector',
            # abscissa='sector', type=RGT_FK,
            abscissa_cell_value='sector', abscissa_type=RGT_FK,
            # ordinate='1000__max',  # <=====
            # is_count=False,
            ordinate_type=RGA_MAX,
            ordinate_cell_key='custom_field-1000',  # <=====
        )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch(user)

        sectors = FakeSector.objects.all()
        self.assertEqual([s.title for s in sectors], x_asc)
        self.assertEqual(
            [0, '/tests/organisations?q_filter={}'.format(self._serialize_qfilter(sector=sectors[0].id))],
            y_asc[0]
        )
        # self.assertEqual(_('the custom field does not exist any more.'),
        #                  rgraph.hand.ordinate_error
        #                 )
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
            # abscissa='user', type=RGT_FK,
            abscissa_cell_value='user', abscissa_type=RGT_FK,
            # ordinate='', is_count=True,
            ordinate_type=RGA_COUNT,
        )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch(user)

        self.assertIn(str(other_user), x_asc)
        self.assertNotIn(str(user), x_asc)  # <===

    def test_fetch_with_fk_08(self):
        "Abscissa field on ContentType enumerates only entities types."
        user = self.login()

        get_ct = ContentType.objects.get_for_model
        report = Report.objects.create(user=self.user, name='Report on Reports',
                                       ct=get_ct(Report),
                                      )
        # Field.objects.create(report=report, name='name', type=RFT_FIELD, order=1)

        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Report count by CTypes',
            # abscissa='ct', type=RGT_FK,
            abscissa_cell_value='ct', abscissa_type=RGT_FK,
            # ordinate='', is_count=True,
            ordinate_type=RGA_COUNT,
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
            # abscissa='address', type=RGT_FK,
            abscissa_cell_value='address', abscissa_type=RGT_FK,
            # ordinate='', is_count=True,
            ordinate_type=RGA_COUNT,
        )

        x_asc, y_asc = rgraph.fetch(user)
        self.assertEqual([], x_asc)
        self.assertEqual([], y_asc)

        hand = rgraph.hand
        self.assertEqual(_('Billing address'), hand.verbose_abscissa)
        self.assertEqual(_('this field cannot be used as abscissa.'),
                         hand.abscissa_error
                        )

    def test_fetch_with_date_range01(self):
        "Count."
        user = self.login()
        report = self._create_simple_organisations_report()

        def create_graph(days):
            return ReportGraph.objects.create(
                user=user, linked_report=report,
                name=f'Number of organisation created / {days} day(s)',
                # abscissa='creation_date', type=RGT_RANGE, days=days,
                abscissa_cell_value='creation_date',
                abscissa_type=RGT_RANGE, abscissa_parameter=str(days),
                # is_count=True,
                ordinate_type=RGA_COUNT,
            )

        rgraph = create_graph(15)
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='Target Orga1', creation_date='2013-06-01')
        create_orga(name='Target Orga2', creation_date='2013-06-05')
        create_orga(name='Target Orga3', creation_date='2013-06-14')
        create_orga(name='Target Orga4', creation_date='2013-06-15')
        create_orga(name='Target Orga5', creation_date='2013-06-16')
        create_orga(name='Target Orga6', creation_date='2013-06-30')

        # ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch(user)
        self.assertEqual(['01/06/2013-15/06/2013', '16/06/2013-30/06/2013'],
                         x_asc
                        )

        self.assertEqual(len(y_asc), 2)
        fmt = lambda *dates: '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(creation_date__range=dates),
        )
        self.assertEqual([4, fmt('2013-06-01', '2013-06-15')], y_asc[0])
        self.assertEqual([2, fmt('2013-06-16', '2013-06-30')], y_asc[1])

        # DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(user=user, order='DESC')
        self.assertEqual(['30/06/2013-16/06/2013', '15/06/2013-01/06/2013'],
                         x_desc
                        )
        self.assertEqual([2, fmt('2013-06-16', '2013-06-30')], y_desc[0])
        self.assertEqual([4, fmt('2013-06-01', '2013-06-15')], y_desc[1])

        # Days = 1 ------------------------------------------------------------
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
            # abscissa='creation_date',type=RGT_RANGE, days=days,
            abscissa_cell_value='creation_date',
            abscissa_type=RGT_RANGE, abscissa_parameter=str(days),
            # ordinate='capital__sum', is_count=False,
            ordinate_type=RGA_SUM,
            ordinate_cell_key='regular_field-capital',
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='Orga1', creation_date='2013-06-22', capital=100)
        create_orga(name='Orga2', creation_date='2013-06-25', capital=200)
        create_orga(name='Orga3', creation_date='2013-07-5',  capital=150)
        create_orga(name='Orga4', creation_date='2013-07-5',  capital=1000, is_deleted=True)

        # ASC -----------------------------------------------------------------
        # x_asc, y_asc = rgraph.fetch()
        x_asc, y_asc = rgraph.fetch(user)
        self.assertEqual(['22/06/2013-01/07/2013', '02/07/2013-11/07/2013'],
                         x_asc
                        )
        fmt = lambda *dates: '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(creation_date__range=dates),
        )
        self.assertEqual([300, fmt('2013-06-22', '2013-07-01')], y_asc[0])
        self.assertEqual([150, fmt('2013-07-02', '2013-07-11')], y_asc[1])

        # DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC', user=user)
        self.assertEqual(['05/07/2013-26/06/2013', '25/06/2013-16/06/2013'],
                         x_desc
                        )
        self.assertEqual([150, fmt('2013-06-26', '2013-07-05')], y_desc[0])
        self.assertEqual([300, fmt('2013-06-16', '2013-06-25')], y_desc[1])

    def test_fetch_with_asymmetrical_date_range01(self):
        "Count, where the ASC values are different from the DESC ones."
        user = self.login()
        report = self._create_simple_organisations_report()

        def create_graph(days):
            return ReportGraph.objects.create(
                user=user, linked_report=report,
                name=f'Number of organisation created / {days} day(s)',
                # abscissa='creation_date', type=RGT_RANGE, days=days,
                abscissa_cell_value='creation_date',
                abscissa_type=RGT_RANGE, abscissa_parameter=str(days),
                # is_count=True,
                ordinate_type=RGA_COUNT,
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
        self.assertEqual(['21/12/2013-04/01/2014', '05/01/2014-19/01/2014'],
                         x_asc
                        )

        self.assertEqual(len(y_asc), 2)
        fmt = lambda *dates: '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(creation_date__range=[*dates]),
        )
        self.assertEqual([4, fmt('2013-12-21', '2014-01-04')], y_asc[0])
        self.assertEqual([2, fmt('2014-01-05', '2014-01-19')], y_asc[1])

        # DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(user=user, order='DESC', extra_q=None)
        self.assertEqual(['07/01/2014-24/12/2013', '23/12/2013-09/12/2013'],
                         x_desc
                        )
        self.assertEqual(len(y_desc), 2)
        self.assertEqual([5, fmt('2013-12-24', '2014-01-07')], y_desc[0])
        self.assertEqual([1, fmt('2013-12-09', '2013-12-23')], y_desc[1])

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
        invalid_days_indices = [index for index in range(len(y_one_day)) if index not in valid_days_indices]
        self.assertEqual([index for index, value in enumerate(y_one_day) if value[0] == 1], valid_days_indices)
        self.assertEqual([index for index, value in enumerate(y_one_day) if value[0] == 0], invalid_days_indices)

    def test_fetch_with_custom_date_range01(self):
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
        targaryens = create_orga(name='House Targaryen')
        lannisters = create_orga(name='House Lannister')
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

        create_cf_value(custom_field=cf2, entity=lannisters, value=create_dt(year=2013, month=11, day=6))
        create_cf_value(custom_field=cf2, entity=starks,     value=create_dt(year=2014, month=1,  day=6))

        days = 15
        rgraph = ReportGraph.objects.create(
            user=user,
            linked_report=self._create_simple_organisations_report(),
            name=f'First victory / {days} day(s)',
            # abscissa=cf.id,type=RGT_CUSTOM_RANGE, days=days,
            abscissa_cell_value=cf.id,
            abscissa_type=RGT_CUSTOM_RANGE, abscissa_parameter=str(days),
            # ordinate='', is_count=True,
            ordinate_type=RGA_COUNT,
        )

        # ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch(user)
        self.assertEqual(['21/12/2013-04/01/2014', '05/01/2014-19/01/2014'],
                         x_asc
                        )

        self.assertEqual(4, y_asc[0][0])
        self.assertURL(
            y_asc[0][1],  # base_url,
            FakeOrganisation,
            Q(customfielddatetime__custom_field=cf.id,
              customfielddatetime__value__range=['2013-12-21', '2014-01-04'],
            ),
        )

        self.assertEqual(2, y_asc[1][0])
        self.assertURL(
            y_asc[1][1],
            FakeOrganisation,
            Q(customfielddatetime__custom_field=cf.id,
              customfielddatetime__value__range=['2014-01-05', '2014-01-19'],
            ),
        )

        # DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC', user=user)
        self.assertEqual(['07/01/2014-24/12/2013', '23/12/2013-09/12/2013'],
                         x_desc
                        )

        self.assertEqual(5, y_desc[0][0])
        self.assertURL(
            y_desc[0][1],  # base_url,
            FakeOrganisation,
            Q(customfielddatetime__custom_field=cf.id,
              customfielddatetime__value__range=['2013-12-24', '2014-01-07'],
             )
        )

        self.assertEqual(1, y_desc[1][0])
        self.assertURL(
            y_desc[1][1],
            FakeOrganisation,
            Q(customfielddatetime__custom_field=cf.id,
              customfielddatetime__value__range=['2013-12-09', '2013-12-23'],
             )
        )

    def test_fetch_with_custom_date_range02(self):
        "Invalid CustomField."
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Useless name',
            # abscissa=1000,  # <====
            abscissa_cell_value=1000,  # <====
            # type=RGT_CUSTOM_RANGE, days=11,
            abscissa_type=RGT_CUSTOM_RANGE, abscissa_parameter='11',
            # ordinate='', is_count=True,
            ordinate_type=RGA_COUNT,
        )

        x_asc, y_asc = rgraph.fetch(user)
        self.assertEqual([], x_asc)
        self.assertEqual([], y_asc)

    def test_fetch_by_day01(self):
        "Aggregate."
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Average of capital by creation date (by day)',
            # abscissa='creation_date', type=RGT_DAY,
            abscissa_cell_value='creation_date',
            abscissa_type=RGT_DAY,
            # ordinate='capital__avg', is_count=False,
            ordinate_type=RGA_AVG,
            ordinate_cell_key='regular_field-capital',
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='Orga1', creation_date='2013-06-22', capital=100)
        create_orga(name='Orga2', creation_date='2013-06-22', capital=200)
        create_orga(name='Orga3', creation_date='2013-07-5',  capital=130)

        # ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch(user=user)
        self.assertEqual(['22/06/2013', '05/07/2013'], x_asc)

        self.assertEqual(150, y_asc[0][0])
        self.assertURL(y_asc[0][1],
                       FakeOrganisation,
                       Q(creation_date__day=22,
                         creation_date__month=6,
                         creation_date__year=2013,
                        )
                      )

        self.assertEqual(130, y_asc[1][0])

        # DESC ----------------------------------------------------------------
        self.assertEqual(['05/07/2013', '22/06/2013'],
                         rgraph.fetch(user=user, order='DESC')[0]
                        )

    def test_fetch_by_customday01(self):
        "Aggregate."
        user = self.login()
        create_cf_dt = partial(CustomField.objects.create,
                               content_type=self.ct_orga,
                               field_type=CustomField.DATETIME,
                              )
        cf = create_cf_dt(name='First victory')

        # This one is annoying because the values are in the same table
        # so the query must be more complex to not retrieve them
        cf2 = create_cf_dt(name='First defeat')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister', capital=100)
        baratheons = create_orga(name='House Baratheon', capital=200)
        targaryens = create_orga(name='House Targaryen', capital=130)

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
            # abscissa=cf.id, type=RGT_CUSTOM_DAY,
            abscissa_cell_value=cf.id, abscissa_type=RGT_CUSTOM_DAY,
            # ordinate='capital__avg', is_count=False,
            ordinate_type=RGA_AVG,
            ordinate_cell_key='regular_field-capital',
        )

        # ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch(user)
        self.assertEqual(['22/06/2013', '05/07/2013'], x_asc)
        self.assertEqual(150, y_asc[0][0])
        self.assertEqual(130, y_asc[1][0])

        url = y_asc[0][1]
        self.assertURL(url,
                       FakeOrganisation,
                       Q(customfielddatetime__value__day=22,
                         customfielddatetime__value__month=6,
                         customfielddatetime__value__year=2013,
                         customfielddatetime__custom_field=cf.id,
                        )
                      )

        # DESC ----------------------------------------------------------------
        self.assertEqual(['05/07/2013', '22/06/2013'],
                         rgraph.fetch(user=user, order='DESC')[0]
                        )

    def test_fetch_by_customday02(self):
        "Invalid CustomField."
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Average of capital by creation date (by day)',
            # abscissa=1000,  # <====
            abscissa_cell_value=1000,  # <====
            # type=RGT_CUSTOM_DAY,
            abscissa_type=RGT_CUSTOM_DAY,
            # ordinate='capital__avg', is_count=False,
            ordinate_type=RGA_AVG,
            ordinate_cell_key='regular_field-capital',
        )

        x_asc, y_asc = rgraph.fetch(user=user)
        self.assertEqual([], x_asc)
        self.assertEqual([], y_asc)

        hand = rgraph.hand
        self.assertEqual('??', hand.verbose_abscissa)
        self.assertEqual(_('the custom field does not exist any more.'),
                         hand.abscissa_error
                        )

    def test_fetch_by_month01(self):
        "Count."
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Number of orgas by creation date (period of 1 month)',
            # abscissa='creation_date', type=RGT_MONTH,
            abscissa_cell_value='creation_date',
            abscissa_type=RGT_MONTH,
            # ordinate='', is_count=True,
            ordinate_type=RGA_COUNT,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='Orga1', creation_date='2013-06-22')
        create_orga(name='Orga2', creation_date='2013-06-25')
        create_orga(name='Orga3', creation_date='2013-08-5')

        # ASC -----------------------------------------------------------------
        # x_asc, y_asc = rgraph.fetch()
        x_asc, y_asc = rgraph.fetch(user=user)
        self.assertEqual(['06/2013', '08/2013'], x_asc)

        self.assertEqual(2, y_asc[0][0])
        self.assertURL(y_asc[0][1],
                       FakeOrganisation,
                       Q(creation_date__month=6, creation_date__year=2013),
                      )

        self.assertEqual(1, y_asc[1][0])

        # DESC ----------------------------------------------------------------
        self.assertEqual(['08/2013', '06/2013'], rgraph.fetch(user=user, order='DESC')[0])

    def test_fetch_by_custommonth01(self):
        "Count."
        user = self.login()

        cf = CustomField.objects.create(content_type=self.ct_orga,
                                        name='First victory',
                                        field_type=CustomField.DATETIME,
                                       )
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister')
        baratheons = create_orga(name='House Baratheon')
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
            # abscissa=cf.id, type=RGT_CUSTOM_MONTH,
            abscissa_cell_value=cf.id, abscissa_type=RGT_CUSTOM_MONTH,
            # ordinate='', is_count=True,
            ordinate_type=RGA_COUNT,
        )

        x_asc, y_asc = rgraph.fetch(user=user)
        self.assertEqual(['06/2013', '08/2013'], x_asc)
        self.assertEqual(2, y_asc[0][0])

    def test_fetch_by_year01(self):
        "Count."
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Number of orgas by creation date (period of 1 year)',
            # abscissa='creation_date', type=RGT_YEAR,
            abscissa_cell_value='creation_date',
            abscissa_type=RGT_YEAR,
            # ordinate='', is_count=True,
            ordinate_type=RGA_COUNT,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='Orga1', creation_date='2013-06-22')
        create_orga(name='Orga2', creation_date='2013-07-25')
        create_orga(name='Orga3', creation_date='2014-08-5')

        # ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch(user)
        self.assertEqual(['2013', '2014'], x_asc)
        fmt = lambda year: '/tests/organisations?q_filter={}'.format(
                                self._serialize_qfilter(creation_date__year=year),
        )
        self.assertEqual([2, fmt(2013)], y_asc[0])
        self.assertEqual([1, fmt(2014)], y_asc[1])

        # DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC', user=user)
        self.assertEqual(['2014', '2013'], x_desc)
        self.assertEqual([1, fmt(2014)], y_desc[0])
        self.assertEqual([2, fmt(2013)], y_desc[1])

    def test_fetch_by_year02(self):
        "Aggregate ordinate with custom field."
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister', creation_date='2013-06-22')
        starks     = create_orga(name='House Stark',     creation_date='2013-07-25')
        baratheons = create_orga(name='House Baratheon', creation_date='2014-08-5')
        __         = create_orga(name='House Targaryen', creation_date='2015-08-5')
        tullies    = create_orga(name='House Tully',     creation_date='2016-08-5')

        cf = CustomField.objects.create(content_type=self.ct_orga,
                                        name='Vine', field_type=CustomField.FLOAT,
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
            # abscissa='creation_date', type=RGT_YEAR,
            abscissa_cell_value='creation_date',
            abscissa_type=RGT_YEAR,
            # ordinate=f'{cf.id}__sum',
            # is_count=False,
            ordinate_type=RGA_SUM,
            ordinate_cell_key=f'custom_field-{cf.id}',
        )

        x_asc, y_asc = rgraph.fetch(user)
        self.assertEqual(['2013', '2014', '2015', '2016'], x_asc)

        fmt = lambda year: '/tests/organisations?q_filter={}'.format(
                self._serialize_qfilter(creation_date__year=year),
        )
        self.assertEqual([Decimal('70.70'), fmt(2013)], y_asc[0])
        self.assertEqual([Decimal('100'),   fmt(2014)], y_asc[1])
        self.assertEqual([0,                fmt(2015)], y_asc[2])
        self.assertEqual([0,                fmt(2016)], y_asc[3])

    def test_fetch_by_year03(self):
        "Invalid field."
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Number of orgas by creation date (period of 1 year)',
            # abscissa='invalid',  # <=====
            abscissa_cell_value='invalid',  # <=====
            # type=RGT_YEAR,
            abscissa_type=RGT_YEAR,
            # ordinate='', is_count=True,
            ordinate_type=RGA_COUNT,
        )

        x_asc, y_asc = rgraph.fetch(user)
        self.assertListEqual([], x_asc)
        self.assertListEqual([], y_asc)

        hand = rgraph.hand
        self.assertEqual('??', hand.verbose_abscissa)
        self.assertEqual(_('the field does not exist any more.'),
                         hand.abscissa_error
                        )

    def test_fetch_by_customyear01(self):
        "Count"
        user = self.login()

        cf = CustomField.objects.create(content_type=self.ct_orga,
                                        name='First victory',
                                        field_type=CustomField.DATETIME,
                                       )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister')
        baratheons = create_orga(name='House Baratheon')
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
            # abscissa=cf.id, type=RGT_CUSTOM_YEAR,
            abscissa_cell_value=cf.id, abscissa_type=RGT_CUSTOM_YEAR,
            # ordinate='', is_count=True,
            ordinate_type=RGA_COUNT,
        )

        x_asc, y_asc = rgraph.fetch(user=user)
        self.assertEqual(['2013', '2014'], x_asc)
        self.assertEqual(2, y_asc[0][0])

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
            ]
        )

        create_rel = partial(Relation.objects.create, user=user, type_id=fake_constants.FAKE_REL_OBJ_EMPLOYED_BY)
        create_rel(subject_entity=lannisters, object_entity=tyrion)
        create_rel(subject_entity=starks,     object_entity=ned)
        create_rel(subject_entity=starks,     object_entity=aria)
        create_rel(subject_entity=starks,     object_entity=jon)

        report = self._create_simple_contacts_report(efilter=efilter)
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Number of employees',
            # abscissa=fake_constants.FAKE_REL_SUB_EMPLOYED_BY,
            abscissa_cell_value=fake_constants.FAKE_REL_SUB_EMPLOYED_BY,
            # type=RGT_RELATION,
            abscissa_type=RGT_RELATION,
            # ordinate='', is_count=True,
            ordinate_type=RGA_COUNT,
        )

        # ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch(user=user)
        # TODO: sort alphabetically (see comment in the code)
        # self.assertEqual([unicode(lannisters), unicode(starks)], x_asc)
        # self.assertEqual(1, y_asc[0])
        # self.assertEqual(2, y_asc[1]) #not 3, because of the filter

        self.assertEqual(2, len(x_asc))

        with self.assertNoException():
            lannisters_idx = x_asc.index(str(lannisters))
            starks_idx     = x_asc.index(str(starks))

        fmt = '/tests/contacts?q_filter={}&filter=test-filter'.format
        self.assertListEqual(
            [1, fmt(self._serialize_qfilter(pk__in=[tyrion.id]))],
            y_asc[lannisters_idx]
        )
        self.assertListEqual(
            [2, fmt(self._serialize_qfilter(pk__in=[ned.id, aria.id, jon.id]))],
            y_asc[starks_idx]
        )  # Not 3, because of the filter

        # DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC', user=user)
        self.assertEqual(x_asc, x_desc)
        self.assertEqual(y_asc, y_desc)

    def test_fetch_by_relation02(self):
        "Aggregate"
        user = self.login()
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister', capital=100)
        starks     = create_orga(name='House Stark',     capital=50)
        tullies    = create_orga(name='House Tully',     capital=40)

        create_contact = partial(FakeContact.objects.create, user=user)
        tywin = create_contact(first_name='Tywin',  last_name='Lannister')
        ned   = create_contact(first_name='Eddard', last_name='Stark')

        rtype = RelationType.create(
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
            # abscissa=rtype.id, type=RGT_RELATION,
            abscissa_cell_value=rtype.id,
            abscissa_type=RGT_RELATION,
            # ordinate='capital__sum', is_count=False,
            ordinate_type=RGA_SUM,
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
            y_asc[tywin_index]
        )
        self.assertListEqual(
            [90,  fmt(self._serialize_qfilter(pk__in=[starks.id, tullies.id]))],
            y_asc[ned_index]
        )

        # DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC', user=user)
        self.assertEqual(x_asc, x_desc)
        self.assertEqual(y_asc, y_desc)

    def test_fetch_by_relation03(self):
        "Aggregate ordinate with custom field."
        user = self.login()

        create_cf = CustomField.objects.create
        cf = create_cf(content_type=self.ct_contact,
                       name='HP', field_type=CustomField.INT,
                      )
        create_cf(content_type=self.ct_contact,
                  name='Title', field_type=CustomField.ENUM,
                 )  # Can not perform aggregates
        create_cf(content_type=self.ct_orga,
                  name='Gold', field_type=CustomField.INT,
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
            # abscissa=rtype_id, type=RGT_RELATION,
            abscissa_cell_value=rtype_id, abscissa_type=RGT_RELATION,
            # ordinate=f'{cf.id}__sum', is_count=False,
            ordinate_type=RGA_SUM,
            ordinate_cell_key=f'custom_field-{cf.id}',
        )

        x_asc, y_asc = rgraph.fetch(user)
        self.assertSetEqual({str(lannisters), str(starks)}, {*x_asc})

        index = x_asc.index
        fmt = '/tests/contacts?q_filter={}'.format
        self.assertListEqual(
            [600, fmt(self._serialize_qfilter(pk__in=[jaime.id, tyrion.id]))],
            y_asc[index(str(lannisters))]
        )
        self.assertListEqual(
            [800, fmt(self._serialize_qfilter(pk__in=[ned.id, robb.id]))],
            y_asc[index(str(starks))]
        )

    def test_fetch_by_relation04(self):
        "Invalid RelationType."
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Average of capital by creation date (by day)',
            # abscissa='invalidrtype',  # <====
            abscissa_cell_value='invalidrtype',  # <====
            # type=RGT_RELATION,
            abscissa_type=RGT_RELATION,
            # ordinate='capital__avg', is_count=False,
            ordinate_type=RGA_AVG,
            ordinate_cell_key='regular_field-capital',
        )

        x_asc, y_asc = rgraph.fetch(user)
        self.assertEqual([], x_asc)
        self.assertEqual([], y_asc)

        hand = rgraph.hand
        self.assertEqual('??', hand.verbose_abscissa)
        self.assertEqual(_('the relationship type does not exist any more.'),
                         hand.abscissa_error
                        )

    def test_fetch_with_customfk_01(self):
        user = self.login()
        report = self._create_simple_contacts_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Contacts by title',
            # abscissa=1000,  # <=========
            abscissa_cell_value=1000,  # <=========
            # type=RGT_CUSTOM_FK,
            abscissa_type=RGT_CUSTOM_FK,
            # ordinate='', is_count=True,
            ordinate_type=RGA_COUNT,
        )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch(user)

        self.assertEqual([], x_asc)
        self.assertEqual([], y_asc)

        hand = rgraph.hand
        self.assertEqual('??', hand.verbose_abscissa)
        self.assertEqual(_('the custom field does not exist any more.'),
                         hand.abscissa_error
                        )

    def test_fetch_with_customfk_02(self):
        "Count."
        user = self.login()
        cf = CustomField.objects.create(content_type=self.ct_contact,
                                        name='Title', field_type=CustomField.ENUM,
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
            # abscissa=cf.id, type=RGT_CUSTOM_FK,
            abscissa_cell_value=cf.id, abscissa_type=RGT_CUSTOM_FK,
            # ordinate='', is_count=True,
            ordinate_type=RGA_COUNT,
        )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch(user)

        self.assertEqual([hand.value, lord.value], x_asc)

        fmt = lambda val: '/tests/contacts?q_filter={}'.format(
            self._serialize_qfilter(customfieldenum__value=val),
        )
        self.assertEqual([1, fmt(hand.id)], y_asc[0])
        self.assertEqual([2, fmt(lord.id)], y_asc[1])

        # DESC ---------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC', user=user)
        self.assertListEqual([*reversed(x_asc)], x_desc)
        self.assertListEqual([*reversed(y_asc)], y_desc)

    def test_fetch_with_customfk_03(self):
        "Aggregate."
        user = self.login()
        cf = CustomField.objects.create(content_type=self.ct_orga,
                                        name='Policy',
                                        field_type=CustomField.ENUM,
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
            # abscissa=cf.id, type=RGT_CUSTOM_FK,
            abscissa_cell_value=cf.id, abscissa_type=RGT_CUSTOM_FK,
            # ordinate='capital__sum', is_count=False,
            ordinate_type=RGA_SUM,
            ordinate_cell_key='regular_field-capital',
        )

        self.assertEqual(cf.name, rgraph.hand.verbose_abscissa)

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch(user)

        self.assertEqual([fight.value, smartness.value], x_asc)

        fmt = lambda val: '/tests/organisations?q_filter={}'.format(
            self._serialize_qfilter(customfieldenum__value=val),
        )
        self.assertEqual([90,  fmt(fight.id)],     y_asc[0])
        self.assertEqual([100, fmt(smartness.id)], y_asc[1])

        # DESC ---------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC', user=user)
        self.assertListEqual([*reversed(x_asc)], x_desc)
        self.assertListEqual([*reversed(y_asc)], y_desc)

    def test_fetchgraphview_with_decimal_ordinate(self):
        "Test json encoding for Graph with Decimal in fetch_graph view."
        user = self.login()
        # rgraph = self._create_invoice_report_n_graph(ordinate='total_vat__sum')
        rgraph = self._create_invoice_report_n_graph(
            ordinate_type=RGA_SUM,
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

        # ibci = rgraph.create_instance_brick_config_item(volatile_field='linked_folder')
        # self.assertIsNotNone(ibci)
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

    def test_create_instance_brick_config_item01(self):  # DEPRECATED
        "No link."
        self.login()
        rgraph = self._create_documents_rgraph()

        ibci = rgraph.create_instance_brick_config_item()
        # self.assertEqual(f'instanceblock_reports-graph|{rgraph.id}-', ibci.brick_id)
        self.assertEqual('instanceblock_reports-graph', ibci.brick_class_id)
        # self.assertEqual('', ibci.data)
        self.assertEqual(RGF_NOLINK, ibci.get_extra_data('type'))
        self.assertIsNone(ibci.get_extra_data('value'))

        volatile = _('No volatile column')
        self.assertEqual(f'{rgraph.name} - {volatile}',
                         ReportGraphBrick(ibci).verbose_name
                        )

        # Brick verbose name should be dynamically computed
        rgraph.name = rgraph.name.upper()
        rgraph.save()
        self.assertEqual(f'{rgraph.name} - {volatile}',
                         ReportGraphBrick(ibci).verbose_name
                        )

    def test_create_instance_brick_config_item02(self):  # DEPRECATED
        "Link: regular field."
        self.login()
        rgraph = self._create_documents_rgraph()
        create_ibci = rgraph.create_instance_brick_config_item

        fk_name = 'linked_folder'
        ibci = create_ibci(volatile_field=fk_name)
        # self.assertEqual(
        #     f'instanceblock_reports-graph|{rgraph.id}-{fk_name}|{RFT_FIELD}',
        #     ibci.brick_id
        # )
        self.assertEqual(ReportGraphBrick.id_, ibci.brick_class_id)
        # self.assertEqual(f'{fk_name}|{RFT_FIELD}', ibci.data)
        self.assertEqual(RGF_FK, ibci.get_extra_data('type'))
        self.assertEqual(fk_name, ibci.get_extra_data('value'))

        self.assertIsNone(create_ibci(volatile_field='unknown'))
        self.assertIsNone(create_ibci(volatile_field='description'))  # Not FK
        self.assertIsNone(create_ibci(volatile_field='user'))  # Not FK to CremeEntity
        self.assertIsNone(create_ibci(volatile_field='folder__title'))  # Depth > 1

        self.assertEqual(
            '{} - {}' .format(
                rgraph.name,
                _('{field} (Field)').format(field=_('Folder')),
            ),
            ReportGraphBrick(ibci).verbose_name
        )

    def test_create_instance_brick_config_item03(self):  # DEPRECATED
        "Link: relation type."
        user = self.login()
        report = self._create_simple_contacts_report()
        rgraph = ReportGraph.objects.create(
            user=user,
            linked_report=report,
            name='Number of created contacts / year',
            # abscissa='created', type=RGT_YEAR,
            abscissa_cell_value='created', abscissa_type=RGT_YEAR,
            # ordinate='', is_count=True,
            ordinate_type=RGA_COUNT,
        )

        rtype = RelationType.create(
            ('reports-subject_loves', 'loves',       [FakeContact]),
            ('reports-object_loves',  'is loved by', [FakeContact]),
        )[0]

        ibci = rgraph.create_instance_brick_config_item(volatile_rtype=rtype)
        # self.assertEqual(
        #     f'instanceblock_reports-graph|{rgraph.id}-{rtype.id}|{RFT_RELATION}',
        #     ibci.brick_id
        # )
        self.assertEqual(ReportGraphBrick.id_, ibci.brick_class_id)
        # self.assertEqual(f'{rtype.id}|{RFT_RELATION}', ibci.data)
        self.assertEqual(RGF_RELATION, ibci.get_extra_data('type'))
        self.assertEqual(rtype.id,     ibci.get_extra_data('value'))

        fmt = _('{rtype} (Relationship)').format
        self.assertEqual(f'{rgraph.name} - {fmt(rtype=rtype)}',
                         ReportGraphBrick(ibci).verbose_name
                        )

        rtype.predicate = 'likes'
        rtype.save()
        self.assertEqual(f'{rgraph.name} - {fmt(rtype=rtype)}',
                         ReportGraphBrick(ibci).verbose_name
                        )

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
            context.get('title')
        )
        self.assertEqual(_('Save the block'), context.get('submit_label'))

        # ---
        # self.assertNoFormError(self.client.post(url))
        response = self.client.post(url)
        self.assertFormError(
            response, 'form', 'fetcher',
            _('This field is required.')
        )

        self.assertNoFormError(self.client.post(
            url,
            data={'fetcher': RGF_NOLINK},
        ))

        items = InstanceBrickConfigItem.objects.filter(entity=rgraph.id)
        self.assertEqual(1, len(items))

        item = items[0]
        # self.assertEqual(f'instanceblock_reports-graph|{rgraph.id}-', item.brick_id)
        self.assertEqual('instanceblock_reports-graph', item.brick_class_id)
        # self.assertEqual('', item.data)
        self.assertEqual(RGF_NOLINK, item.get_extra_data('type'))
        self.assertIsNone(item.get_extra_data('value'))
        self.assertIsNone(item.errors)

        brick_id = item.brick_id
        self.assertEqual(f'instanceblock-{item.id}', brick_id)

        title = '{} - {}'.format(rgraph.name, _('No volatile column'))
        self.assertEqual(title, ReportGraphBrick(item).verbose_name)

        brick = item.brick
        self.assertIsInstance(brick, ReportGraphBrick)
        self.assertEqual(title, brick.verbose_name)
        # self.assertEqual(item.id, brick.instance_brick_id)
        self.assertEqual(item,  brick.config_item)

        # ----------------------------------------------------------------------
        # response = self.assertPOST200(url)
        response = self.assertPOST200(
            url,
            data={'fetcher': RGF_NOLINK},
        )
        self.assertFormError(
            # response, 'form', None,
            response, 'form', 'fetcher',
            _('The instance block for «{graph}» with these parameters already exists!').format(
                graph=rgraph.name,
            )
        )

        # ----------------------------------------------------------------------
        response = self.assertGET200(reverse('reports__instance_bricks_info', args=(rgraph.id,)))
        self.assertTemplateUsed(response, 'reports/bricks/instance-bricks-info.html')
        self.assertEqual(rgraph, response.context.get('object'))
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick_id=InstanceBricksInfoBrick.id_,
        )
        vname_node = brick_node.find('.//td[@data-table-primary-column]')
        self.assertIsNotNone(vname_node)
        self.assertEqual(_('No volatile column'), vname_node.text)

        # ----------------------------------------------------------------------
        # Display on home
        BrickHomeLocation.objects.all().delete()
        # BrickHomeLocation.objects.create(brick_id=item.brick_id, order=1)
        BrickHomeLocation.objects.create(brick_id=brick_id, order=1)
        response = self.assertGET200('/')
        self.assertTemplateUsed(response, 'reports/bricks/graph.html')
        # self.get_brick_node(self.get_html_tree(response.content), item.brick_id)
        self.get_brick_node(self.get_html_tree(response.content), brick_id)

        # ----------------------------------------------------------------------
        # Display on detailview
        ct = self.ct_invoice
        BrickDetailviewLocation.objects.filter(content_type=ct).delete()
        BrickDetailviewLocation.objects.create_if_needed(
            # brick=item.brick_id,
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
        # self.get_brick_node(self.get_html_tree(response.content), item.brick_id)
        self.get_brick_node(self.get_html_tree(response.content), brick_id)

        # ----------------------------------------------------------------------
        response = self.assertGET200(self._build_fetchfrombrick_url(item, invoice, 'ASC'))

        result = response.json()
        self.assertIsInstance(result, dict)
        self.assertEqual(2, len(result))

        x_fmt = '{:02}/2014'.format  # NB: RGT_MONTH
        self.assertEqual([x_fmt(10), x_fmt(11)], result.get('x'))

        y = result.get('y')
        self.assertEqual(0, y[0][0])
        self.assertURL(y[0][1],
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
        self.assertURL(y[0][1],
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
            # choices = response.context['form'].fields['volatile_column'].choices
            choices = [*response.context['form'].fields['fetcher'].widget.choices]

        # self.assertEqual(3, len(choices))
        self.assertGreaterEqual(len(choices), 3)
        # self.assertEqual(('', pgettext('reports-volatile_choice', 'None')), choices[0])
        self.assertInChoices(
            value=f'{RGF_NOLINK}|',
            label=pgettext('reports-volatile_choice', 'None'),
            choices=choices,
        )

        fk_name = 'linked_folder'
        # folder_choice = f'fk-{fk_name}'
        folder_choice = f'{RGF_FK}|{fk_name}'
        # self.assertEqual(
        #     (_('Fields'), [(folder_choice, _('Folder'))]),
        #     choices[1]
        # )
        field_choices = self.get_choices_group_or_fail(label=_('Fields'), choices=choices)
        self.assertInChoices(
            value=folder_choice,
            label=_('Folder'),
            choices=field_choices,
        )

        # self.assertNoFormError(self.client.post(url, data={'volatile_column': folder_choice}))
        self.assertNoFormError(self.client.post(url, data={'fetcher': folder_choice}))

        items = InstanceBrickConfigItem.objects.filter(entity=rgraph.id)
        self.assertEqual(1, len(items))

        item = items[0]
        # self.assertEqual(
        #     f'instanceblock_reports-graph|{rgraph.id}-{fk_name}|{RFT_FIELD}',
        #     item.brick_id
        # )
        self.assertEqual('instanceblock_reports-graph', item.brick_class_id)
        # self.assertEqual(f'{fk_name}|{RFT_FIELD}', item.data)
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

        fetcher = ReportGraph.get_fetcher_from_instance_brick(item)
        self.assertIsNone(fetcher.error)

        x, y = fetcher.fetch_4_entity(entity=folder1, user=user)  # TODO: order

        year = doc1.created.year
        self.assertEqual([str(year)], x)
        self.assertEqual(
            [[2, reverse('reports__list_fake_documents') + '?q_filter={}'.format(self._serialize_qfilter(created__year=year))]],
            y
        )

    def test_add_graph_instance_brick_not_superuser01(self):
        self.login(is_superuser=False,
                   allowed_apps=['reports'],
                   admin_4_apps=['reports'],
                  )
        rgraph = self._create_invoice_report_n_graph()
        self.assertGET200(self._build_add_brick_url(rgraph))

    def test_add_graph_instance_brick_not_superuser02(self):
        "Admin permission needed"
        self.login(is_superuser=False,
                   allowed_apps=['reports'],
                   # admin_4_apps=['reports'],
                  )
        rgraph = self._create_invoice_report_n_graph()
        self.assertGET403(self._build_add_brick_url(rgraph))

    def test_add_graph_instance_brick02_error01(self):
        "Volatile column (RFT_FIELD): invalid field."
        user = self.login()
        rgraph = self._create_documents_rgraph()

        # We create voluntarily an invalid item
        fname = 'invalid'
        # ibci = InstanceBrickConfigItem.objects.create(
        #     entity=rgraph,
        #     brick_id=f'instanceblock_reports-graph|{rgraph.id}-{fname}|{RFT_FIELD}',
        #     data=f'{fname}|{RFT_FIELD}',
        # )
        ibci = InstanceBrickConfigItem.objects.create(
            entity=rgraph,
            brick_class_id=ReportGraphBrick.id_,
        )
        ibci.set_extra_data(key='type',  value=RGF_FK)
        ibci.set_extra_data(key='value', value=fname)

        folder = FakeReportsFolder.objects.create(user=user, title='My folder')

        # fetcher = ReportGraph.get_fetcher_from_instance_brick(ibci)
        fetcher = ReportGraphBrick(ibci).fetcher
        x, y = fetcher.fetch_4_entity(entity=folder, user=user)

        self.assertEqual([], x)
        self.assertEqual([], y)
        self.assertEqual(_('The field is invalid.'), fetcher.error)
        # self.assertEqual('??',                       fetcher.verbose_volatile_column)
        self.assertEqual('??',                       fetcher.verbose_name)

        self.assertEqual([_('The field is invalid.')], ibci.errors)

    def test_add_graph_instance_brick02_error02(self):
        "Volatile column (RFT_FIELD): field is not a FK to CremeEntity."
        user = self.login()
        rgraph = self._create_documents_rgraph()

        # We create voluntarily an invalid item
        fname = 'description'
        # ibci = InstanceBrickConfigItem.objects.create(
        #     entity=rgraph,
        #     brick_id=f'instanceblock_reports-graph|{rgraph.id}-{fname}|{RFT_FIELD}',
        #     data=f'{fname}|{RFT_FIELD}',
        # )
        ibci = InstanceBrickConfigItem(
            entity=rgraph,
            brick_class_id=ReportGraphBrick.id_,
        )
        ibci.set_extra_data(key='type',  value=RGF_FK)
        ibci.set_extra_data(key='value', value=fname)
        ibci.save()

        folder = FakeReportsFolder.objects.create(user=user, title='My folder')

        # fetcher = ReportGraph.get_fetcher_from_instance_brick(ibci)
        fetcher = ReportGraphBrick(ibci).fetcher
        x, y = fetcher.fetch_4_entity(entity=folder, user=user)

        self.assertEqual([], x)
        self.assertEqual([], y)
        self.assertEqual(_('The field is invalid (not a foreign key).'), fetcher.error)

    def test_add_graph_instance_brick02_error03(self):
        "Volatile column (RGF_FK): field is not a FK to the given Entity type."
        user = self.login()
        rgraph = self._create_documents_rgraph()

        # ibci = rgraph.create_instance_brick_config_item(volatile_field='linked_folder')
        fetcher = RegularFieldLinkedGraphFetcher(graph=rgraph, value='linked_folder')
        self.assertIsNone(fetcher.error)

        ibci = fetcher.create_brick_config_item()
        self.assertIsNotNone(ibci)

        # fetcher = ReportGraph.get_fetcher_from_instance_brick(ibci)
        x, y = fetcher.fetch_4_entity(entity=user.linked_contact, user=user)
        self.assertEqual([], x)
        self.assertEqual([], y)
        self.assertIsNone(fetcher.error)

    def test_add_graph_instance_brick03(self):
        "Volatile column (RGF_RELATION)."
        user = self.login()
        report = self._create_simple_contacts_report()
        rtype = RelationType.objects.get(pk=fake_constants.FAKE_REL_SUB_EMPLOYED_BY)
        incompatible_rtype = RelationType.create(
            ('reports-subject_related_doc', 'is related to doc',   [Report]),
            ('reports-object_related_doc',  'is linked to report', [FakeReportsDocument]),
        )[0]

        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Number of created contacts / year',
            # abscissa='created', type=RGT_YEAR,
            abscissa_cell_value='created', abscissa_type=RGT_YEAR,
            # ordinate='', is_count=True,
            ordinate_type=RGA_COUNT,
        )

        url = self._build_add_brick_url(rgraph)
        response = self.assertGET200(url)

        with self.assertNoException():
            # choices = response.context['form'].fields['volatile_column'].choices
            choices = [*response.context['form'].fields['fetcher'].widget.choices]

        # rel_group = choices[2]
        # self.assertEqual(_('Relationships'), rel_group[0])
        rel_choices = self.get_choices_group_or_fail(label=_('Relationships'), choices=choices)

        # rel_choices = frozenset((k, str(v)) for k, v in rel_group[1])
        # choice_id = f'rtype-{rtype.id}'
        choice_id = f'{RGF_RELATION}|{rtype.id}'
        self.assertInChoices(value=choice_id, label=str(rtype), choices=rel_choices)
        self.assertNotInChoices(value=f'rtype-{incompatible_rtype.id}', choices=rel_choices)

        # self.assertNoFormError(self.client.post(url, data={'volatile_column': choice_id}))
        self.assertNoFormError(self.client.post(url, data={'fetcher': choice_id}))

        items = InstanceBrickConfigItem.objects.filter(entity=rgraph.id)
        self.assertEqual(1, len(items))

        item = items[0]
        # self.assertEqual(
        #     f'instanceblock_reports-graph|{rgraph.id}-{rtype.id}|{RFT_RELATION}',
        #     item.brick_id
        # )
        self.assertEqual('instanceblock_reports-graph',
                         item.brick_class_id
                        )
        # self.assertEqual(f'{rtype.id}|{RFT_RELATION}', item.data)
        self.assertEqual(RGF_RELATION, item.get_extra_data('type'))
        self.assertEqual(rtype.id,      item.get_extra_data('value'))

        self.assertEqual('{} - {}'.format(
                            rgraph.name,
                            _('{rtype} (Relationship)').format(rtype=rtype),
                         ),
                         ReportGraphBrick(item).verbose_name
                        )

        create_contact = partial(FakeContact.objects.create, user=user)
        sonsaku = create_contact(first_name='Sonsaku', last_name='Hakufu')
        ryomou  = create_contact(first_name='Ryomou',  last_name='Shimei')
        create_contact(first_name='Kan-u', last_name='Unchô')

        nanyo = FakeOrganisation.objects.create(user=user, name='Nanyô')

        create_rel = partial(Relation.objects.create, user=user, type=rtype, object_entity=nanyo)
        create_rel(subject_entity=sonsaku)
        create_rel(subject_entity=ryomou)

        fetcher = ReportGraph.get_fetcher_from_instance_brick(item)
        self.assertIsNone(fetcher.error)

        x, y = fetcher.fetch_4_entity(entity=nanyo, user=user)

        year = sonsaku.created.year
        self.assertEqual([str(year)], x)
        self.assertEqual(
            [[2, '/tests/contacts?q_filter={}'.format(self._serialize_qfilter(created__year=year))]],
            y
        )

        # Invalid choice
        choice = 'invalid'
        # response = self.assertPOST200(url, data={'volatile_column': choice})
        response = self.assertPOST200(url, data={'fetcher': choice})
        self.assertFormError(
            # response, 'form', 'volatile_column',
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
        # ibci = InstanceBrickConfigItem.objects.create(
        #     entity=rgraph,
        #     brick_id=f'instanceblock_reports-graph|{rgraph.id}-{rtype_id}|{RFT_RELATION}',
        #     data=f'{rtype_id}|{RFT_RELATION}',
        # )
        ibci = InstanceBrickConfigItem.objects.create(
            entity=rgraph,
            brick_class_id=ReportGraphBrick.id_,
        )
        ibci.set_extra_data(key='type',  value=RGF_RELATION)
        ibci.set_extra_data(key='value', value=rtype_id)

        fetcher = ReportGraph.get_fetcher_from_instance_brick(ibci)
        x, y = fetcher.fetch_4_entity(entity=user.linked_contact, user=user)
        self.assertEqual([], x)
        self.assertEqual([], y)
        self.assertEqual(_('The relationship type is invalid.'), fetcher.error)
        # self.assertEqual('??',                                   fetcher.verbose_volatile_column)
        self.assertEqual('??',                                   fetcher.verbose_name)

    def test_get_fetcher_from_instance_brick(self):
        "Invalid type."
        self.login()
        rgraph = self._create_documents_rgraph()

        ibci = InstanceBrickConfigItem.objects.create(
            brick_class_id=ReportGraphBrick.id_,
            entity=rgraph,
        )

        # No extra data
        fetcher1 = ReportGraph.get_fetcher_from_instance_brick(ibci)
        self.assertIsInstance(fetcher1, SimpleGraphFetcher)
        msg = _('Invalid volatile link ; please contact your administrator.')
        self.assertEqual(msg, fetcher1.error)

        # Invalid type
        ibci.set_extra_data(key='type', value='invalid')
        fetcher2 = ReportGraph.get_fetcher_from_instance_brick(ibci)
        self.assertIsInstance(fetcher2, SimpleGraphFetcher)
        self.assertEqual(msg, fetcher2.error)

    def test_delete_graph_instance(self):
        "BrickDetailviewLocation instances must be deleted in cascade."
        self.login()
        rgraph = self._create_documents_rgraph()
        # ibci = rgraph.create_instance_brick_config_item()
        ibci = SimpleGraphFetcher(graph=rgraph).create_brick_config_item()

        brick_id = ibci.brick_id
        bdl = BrickDetailviewLocation.objects.create_if_needed(
            brick=brick_id,
            order=1,
            zone=BrickDetailviewLocation.RIGHT,
            model=FakeContact,
        )
        bhl = BrickHomeLocation.objects.create(brick_id=brick_id, order=1)

        rgraph.delete()
        self.assertDoesNotExist(rgraph)
        self.assertDoesNotExist(ibci)
        self.assertDoesNotExist(bdl)
        self.assertDoesNotExist(bhl)

    def test_get_available_report_graph_types01(self):
        self.login()
        url = self._build_graph_types_url(self.ct_orga)
        self.assertGET404(url)
        self.assertPOST404(url)

        response = self.assertPOST200(url, data={'record_id': 'name'})
        self.assertDictEqual(
            {'result': [{'text': _('Choose an abscissa field'), 'id': ''}]},
            response.json()
        )

        response = self.assertPOST200(url, data={'record_id': 'creation_date'})
        self.assertEqual({'result': [{'id': RGT_DAY,   'text': _('By days')},
                                     {'id': RGT_MONTH, 'text': _('By months')},
                                     {'id': RGT_YEAR,  'text': _('By years')},
                                     {'id': RGT_RANGE, 'text': _('By X days')},
                                    ],
                         },
                         response.json()
                        )

        response = self.assertPOST200(url, data={'record_id': 'sector'})
        self.assertEqual({'result': [{'id': RGT_FK, 'text': _('By values')}]},
                         response.json()
                        )

    def test_get_available_report_graph_types02(self):
        self.login()
        ct = self.ct_invoice
        url = self._build_graph_types_url(ct)

        response = self.assertPOST200(
            url, data={'record_id': fake_constants.FAKE_REL_SUB_BILL_RECEIVED},
        )
        self.assertDictEqual(
            {'result': [{'id': RGT_RELATION,
                         'text': _('By values (of related entities)'),
                        },
                       ],
            },
            response.json()
        )

        create_cf = partial(CustomField.objects.create, content_type=ct)
        cf_enum = create_cf(name='Type', field_type=CustomField.ENUM)
        response = self.assertPOST200(url, data={'record_id': cf_enum.id})
        self.assertDictEqual(
            {'result': [{'id': RGT_CUSTOM_FK,
                         'text': _('By values (of custom choices)')
                        },
                       ],
            },
            response.json()
        )

        cf_dt = create_cf(name='First payment', field_type=CustomField.DATETIME)
        response = self.assertPOST200(url, data={'record_id': cf_dt.id})
        self.assertDictEqual(
            {'result': [{'id': RGT_CUSTOM_DAY,   'text': _('By days')},
                        {'id': RGT_CUSTOM_MONTH, 'text': _('By months')},
                        {'id': RGT_CUSTOM_YEAR,  'text': _('By years')},
                        {'id': RGT_CUSTOM_RANGE, 'text': _('By X days')},
                       ],
            },
            response.json()
        )

    def bench_big_fetch_using_count(self):
        """
        Little benchmark to see how the 'group by' report queries behave with bigger datasets
        where there is a visible difference between the old "manual group by's" and the new real sql ones
        """
        from datetime import datetime
        import time

        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Number of organisation created by day',
            # abscissa='creation_date', type=RGT_RANGE, days=1,
            abscissa_cell_value='creation_date',
            abscissa_type=RGT_RANGE, abscissa_parameter='1',
            # is_count=True,
            ordinate_type=RGA_COUNT,
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
        self.assertEqual(sum((value for value, _ in y)),
                         interval_day_count * entities_per_day
                        )

    def bench_big_fetch_using_sum(self):
        """
        Little benchmark to see how the 'group by' report queries behave with bigger datasets
        where there is a visible difference between the old "manual group by's" and the new real sql ones
        """
        from datetime import datetime
        import time

        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Sum of capital by creation date (period of 1 days)',
            # abscissa='creation_date', type=RGT_RANGE, days=1,
            abscissa_cell_value='creation_date',
            abscissa_type=RGT_RANGE, abscissa_parameter='1',
            # ordinate='capital__sum', is_count=False,
            ordinate_type=RGA_SUM,
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
        self.assertEqual(sum((value for value, _ in y)),
                         interval_day_count * entities_per_day * 100
                        )

    def test_inneredit(self):
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='capital per month of creation',
            chart='barchart',
            # abscissa='created',
            # type=RGT_MONTH, is_count=False,
            # ordinate='capital__sum', is_count=False,
            abscissa_cell_value='created',
            abscissa_type=RGT_MONTH,
            # ordinate='capital__sum',
            ordinate_type=RGA_SUM,
            ordinate_cell_key='regular_field-capital',
        )

        build_url = self.build_inneredit_url
        url = build_url(rgraph, 'name')
        self.assertGET200(url)

        name = rgraph.name.title()
        response = self.client.post(url, data={'entities_lbl': [str(rgraph)],
                                               'field_value':  name,
                                              },
                                   )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(rgraph).name)

        self.assertGET(400, build_url(rgraph, 'report'))
        self.assertGET(400, build_url(rgraph, 'abscissa'))
        self.assertGET(400, build_url(rgraph, 'ordinate'))
        self.assertGET(400, build_url(rgraph, 'type'))
        self.assertGET(400, build_url(rgraph, 'days'))
        # self.assertGET(400, build_url(rgraph, 'is_count'))
        self.assertGET(400, build_url(rgraph, 'chart'))

    def test_clone_report(self):
        user = self.login()
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='capital per month of creation',
            chart='barchart',
            # type=RGT_MONTH,
            # abscissa='created',
            abscissa_cell_value='created',
            abscissa_type=RGT_MONTH,
            # ordinate='capital__sum', is_count=False,
            ordinate_type=RGA_SUM,
            ordinate_cell_key='regular_field-capital',
        )

        cloned_report = report.clone()

        rgrahes = ReportGraph.objects.filter(linked_report=cloned_report)
        self.assertEqual(1, len(rgrahes))

        cloned_rgraph = rgrahes[0]
        self.assertNotEqual(rgraph.id, cloned_rgraph.id)
        self.assertEqual(rgraph.name,  cloned_rgraph.name)

        # self.assertEqual(rgraph.abscissa, cloned_rgraph.abscissa)
        self.assertEqual(rgraph.abscissa_cell_value, cloned_rgraph.abscissa_cell_value)
        # self.assertEqual(rgraph.ordinate, cloned_rgraph.ordinate)
        # self.assertEqual(rgraph.type,     cloned_rgraph.type)
        self.assertEqual(rgraph.abscissa_type,       cloned_rgraph.abscissa_type)
        # self.assertEqual(rgraph.days,     cloned_rgraph.days)
        self.assertEqual(rgraph.abscissa_parameter,  cloned_rgraph.abscissa_parameter)

        # self.assertEqual(rgraph.is_count, cloned_rgraph.is_count)
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
        create_orga(name='O#4', user=other_user, capital=300)  # Cannot be seen => should not be used to compute aggregate

        name = 'Max capital per user'
        self.assertNoFormError(self.client.post(
            self._build_add_graph_url(report),
            data={
                'user': user.id,
                'name': name,
                'chart': 'barchart',

                # 'abscissa_field':    'user',
                # 'abscissa_group_by': RGT_FK,
                'abscissa': self.formfield_value_abscissa(
                    abscissa=FakeOrganisation._meta.get_field('user'),
                    graph_type=RGT_FK,
                ),

                # 'aggregate_field': 'capital',
                # 'aggregate':       'max',
                'ordinate': self.formfield_value_ordinate(
                    aggr_id=RGA_MAX,
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
        __   = create_doc(title='Doc#2', user=user)
        doc3 = create_doc(title='Doc#3', user=self.other_user)  # Cannot be seen => should not be used to compute aggregate
        self.assertEqual(doc1.created.year, doc3.created.year)

        rgraph = self._create_documents_rgraph()

        # ibci = rgraph.create_instance_brick_config_item(volatile_field='linked_folder')
        # self.assertIsNotNone(ibci)
        fetcher = RegularFieldLinkedGraphFetcher(graph=rgraph, value='linked_folder')
        self.assertIsNone(fetcher.error)

        ibci = fetcher.create_brick_config_item()
        response = self.assertGET200(self._build_fetchfrombrick_url(ibci, folder, 'ASC'))
        result = response.json()
        self.assertEqual([str(doc1.created.year)], result.get('x'))
        self.assertEqual(2, result.get('y')[0][0])
