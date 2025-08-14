from datetime import datetime
from decimal import Decimal
from functools import partial
from json import dumps as json_dump
from json import loads as json_load
from unittest import skipIf
from urllib.parse import parse_qs, urlparse

from django.contrib.contenttypes.models import ContentType
from django.db.models import Field as ModelField
from django.urls import reverse
from django.utils.timezone import now

from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    CustomField,
    FakeContact,
    FakeImage,
    FakeInvoice,
    FakeInvoiceLine,
    FakeOrganisation,
    InstanceBrickConfigItem,
    Relation,
    RelationType,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_constants import (
    FAKE_REL_SUB_BILL_ISSUED as REL_SUB_BILL_ISSUED,
)
from creme.creme_core.tests.fake_constants import (
    FAKE_REL_SUB_BILL_RECEIVED as REL_SUB_BILL_RECEIVED,
)
from creme.creme_core.utils.queries import QSerializer

# from .. import get_rgraph_model, rgraph_model_is_custom
from .. import constants, get_report_model, report_model_is_custom
# from ..constants import RGF_NOLINK
from ..core.chart.fetcher import SimpleChartFetcher
from ..models import Field, ReportChart
from .fake_models import FakeReportsDocument, FakeReportsFolder

skip_report_tests = report_model_is_custom()
# skip_rgraph_tests = rgraph_model_is_custom()

Report = get_report_model()
# ReportGraph = get_rgraph_model()


def skipIfCustomReport(test_func):
    return skipIf(skip_report_tests, 'Custom Report model in use')(test_func)


# def skipIfCustomRGraph(test_func):
#     return skipIf(skip_rgraph_tests, 'Custom ReportGraph model in use')(test_func)


class AxisFieldsMixin:
    @staticmethod
    # def formfield_value_abscissa(*, abscissa, graph_type, parameter=''):
    def formfield_value_abscissa(*, abscissa, chart_type, parameter=''):
        if isinstance(abscissa, ModelField):
            key = f'regular_field-{abscissa.name}'
        elif isinstance(abscissa, RelationType):
            key = f'relation-{abscissa.id}'
        elif isinstance(abscissa, CustomField):
            key = f'custom_field-{abscissa.id}'
        else:
            key = ''

        return json_dump(
            {
                'entity_cell': {
                    'cell_key': key,
                    'grouping_category': 'not used',
                },
                # 'graph_type': {
                'chart_type': {
                    # 'type_id': graph_type,
                    'type_id': chart_type,
                    'grouping_category': 'not used',
                },
                'parameter': parameter,
            },
            separators=(',', ':'),
        )

    @staticmethod
    def formfield_value_ordinate(*, aggr_id, cell=None):
        return json_dump(
            {
                'aggregator': {
                    'aggr_id': aggr_id,
                    'aggr_category': 'not used',
                },
                'entity_cell': {
                    'cell_key': cell.key,
                    'aggr_category': 'not used',
                } if cell else None,
            },
            separators=(',', ':'),
        )


class BaseReportsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        get_ct = ContentType.objects.get_for_model
        cls.ct_contact = get_ct(FakeContact)
        cls.ct_orga    = get_ct(FakeOrganisation)
        cls.ct_image   = get_ct(FakeImage)
        cls.ct_folder  = get_ct(FakeReportsFolder)

        cls.ADD_URL = reverse('reports__create_report')

    def assertListviewURL(self, url, model, expected_q=None, expected_efilter_id=None):
        q_serializer = QSerializer()
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

            expected_qfilter = json_load(q_serializer.dumps(expected_q))
            self.assertIsDict(qfilter, length=2)
            self.assertEqual(expected_qfilter['op'], qfilter['op'])
            # TODO: improve for nested Q...
            self.assertCountEqual(expected_qfilter['val'], qfilter['val'])

        # '&filter=' ------
        if expected_efilter_id is None:
            self.assertNotIn('filter', GET_params)
        else:
            self.assertEqual([expected_efilter_id], GET_params.pop('filter', None))

        self.assertFalse(GET_params)  # All valid parameters have been removed

    # def _create_graph_instance_brick(self, graph, fetcher=RGF_NOLINK, **kwargs):
    #     self.assertNoFormError(self.client.post(
    #         reverse('reports__create_instance_brick', args=(graph.id,)),
    #         data={'fetcher': fetcher, **kwargs}
    #     ))
    #
    #     return InstanceBrickConfigItem.objects.get(entity=graph.id)
    def _create_chart_instance_brick(self, chart, fetcher=SimpleChartFetcher, **kwargs):
        self.assertNoFormError(self.client.post(
            reverse('reports__create_instance_brick', args=(chart.id,)),
            data={'fetcher': fetcher.type_id, **kwargs},
        ))

        return self.get_object_or_fail(
            InstanceBrickConfigItem,
            entity=chart.linked_report,
            json_extra_data__chart=str(chart.uuid),
        )

    def _create_simple_contacts_report(self, *,
                                       user,
                                       name='Contact report',
                                       efilter=None,
                                       **kwargs):
        report = Report.objects.create(
            user=user,
            name=name,
            ct=FakeContact,
            filter=efilter,
            **kwargs
        )
        Field.objects.create(
            report=report, name='last_name', type=constants.RFT_FIELD, order=1,
        )

        return report

    def _create_contacts_report(self, *, user, name='Report #1', efilter=None):
        report = self._create_simple_contacts_report(name=name, efilter=efilter, user=user)

        create_field = partial(Field.objects.create, report=report)
        create_field(name='user',                  type=constants.RFT_FIELD,    order=2)
        create_field(name=REL_SUB_HAS,             type=constants.RFT_RELATION, order=3)
        create_field(name='get_pretty_properties', type=constants.RFT_FUNCTION, order=4)

        return report

    def _create_simple_documents_report(self, user):
        report = Report.objects.create(
            name='Documents report',
            user=user,
            ct=FakeReportsDocument,
        )

        create_field = partial(Field.objects.create, report=report, type=constants.RFT_FIELD)
        create_field(name='title',       order=1)
        create_field(name="description", order=2)

        return report

    def _create_simple_organisations_report(self, user, name='Orga report', efilter=None):
        report = Report.objects.create(
            user=user, name=name, ct=FakeOrganisation, filter=efilter,
        )
        Field.objects.create(report=report, name='name', type=constants.RFT_FIELD, order=1)

        return report

    def get_field_or_fail(self, report, field_name):
        try:
            return report.fields.get(name=field_name)
        except Field.DoesNotExist as e:
            self.fail(str(e))

    def _create_persons(self, user):
        create = partial(FakeContact.objects.create, user=user)
        create(
            last_name='Langley', first_name='Asuka',
            birthday=datetime(year=1981, month=7, day=25),
        )
        rei = create(
            last_name='Ayanami', first_name='Rei',
            birthday=datetime(year=1981, month=3, day=26),
        )
        misato = create(
            last_name='Katsuragi', first_name='Misato',
            birthday=datetime(year=1976, month=8, day=12),
        )

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        ptype = CremePropertyType.objects.create(text='Kawaii')
        CremeProperty.objects.create(type=ptype, creme_entity=rei)

        Relation.objects.create(
            user=user,
            subject_entity=misato,
            type_id=REL_SUB_HAS,
            object_entity=nerv,
        )

    def _create_invoice(self, source, target,
                        name='Invoice#01',
                        total_vat=Decimal('0'),
                        issuing_date=None,
                        ):
        user = source.user
        invoice = FakeInvoice.objects.create(
            user=user,
            issuing_date=issuing_date or now().date(),
            name=name,
            total_vat=total_vat,
        )

        FakeInvoiceLine.objects.create(
            user=user,
            linked_invoice=invoice,
            item='Stuff',
            quantity=Decimal('1'),
            unit_price=total_vat,
        )

        create_rel = partial(Relation.objects.create, subject_entity=invoice, user=user)
        create_rel(type_id=REL_SUB_BILL_ISSUED,   object_entity=source)
        create_rel(type_id=REL_SUB_BILL_RECEIVED, object_entity=target)

        return invoice

    # def _create_documents_rgraph(self, user):
    #     report = self._create_simple_documents_report(user=user)
    #     return ReportGraph.objects.create(
    #         user=user,
    #         linked_report=report,
    #         name='Number of created documents / year',
    #         abscissa_cell_value='created',
    #         abscissa_type=ReportGraph.Group.YEAR,
    #         ordinate_type=ReportGraph.Aggregator.COUNT,
    #     )
    def _create_documents_chart(self, user):
        report = self._create_simple_documents_report(user=user)
        return ReportChart.objects.create(
            linked_report=report,
            name='Number of created documents / year',
            abscissa_cell_value='created',
            abscissa_type=ReportChart.Group.YEAR,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

    # def _create_documents_colors_rgraph(self, report):
    #     return ReportGraph.objects.create(
    #         user=report.user,
    #         linked_report=report,
    #         name='Number of created documents / category',
    #         abscissa_cell_value='category',
    #         abscissa_type=ReportGraph.Group.FK,
    #         ordinate_type=ReportGraph.Aggregator.COUNT,
    #     )
    def _create_documents_colors_chart(self, report):
        return ReportChart.objects.create(
            linked_report=report,
            name='Number of created documents / category',
            abscissa_cell_value='category',
            abscissa_type=ReportChart.Group.FK,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

    # def _create_invoice_report_n_graph(self,
    #                                    user,
    #                                    abscissa='issuing_date',
    #                                    ordinate_type=ReportGraph.Aggregator.SUM,
    #                                    ordinate_field='total_no_vat',
    #                                    ):
    #     self.report = report = Report.objects.create(
    #         user=user,
    #         name='All invoices of the current year',
    #         ct=FakeInvoice,
    #     )
    #
    #     return ReportGraph.objects.create(
    #         user=user,
    #         linked_report=report,
    #         name='Sum of current year invoices total without taxes / month',
    #         abscissa_cell_value=abscissa,
    #         abscissa_type=ReportGraph.Group.MONTH,
    #         ordinate_type=ordinate_type,
    #         ordinate_cell_key=f'regular_field-{ordinate_field}',
    #     )
    def _create_invoice_report_n_chart(self,
                                       user,
                                       abscissa='issuing_date',
                                       ordinate_type=ReportChart.Aggregator.SUM,
                                       ordinate_field='total_no_vat',
                                       ):
        self.report = report = Report.objects.create(
            user=user, name='All invoices of the current year', ct=FakeInvoice,
        )

        # TODO: we need a helper ReportChart.objects.smart_create()?
        return ReportChart.objects.create(
            # user=user,
            linked_report=report,
            name='Sum of current year invoices total without taxes / month',
            abscissa_cell_value=abscissa,
            abscissa_type=ReportChart.Group.MONTH,
            ordinate_type=ordinate_type,
            ordinate_cell_key=f'regular_field-{ordinate_field}',
        )
