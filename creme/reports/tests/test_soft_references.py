from functools import partial

from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.core.soft_reference import soft_reference_registry
from creme.creme_core.models import CustomField, FakeInvoice, RelationType
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_constants import FAKE_REL_SUB_BILL_ISSUED
from creme.reports.constants import (
    RFT_AGG_CUSTOM,
    RFT_CUSTOM,
    RFT_FIELD,
    RFT_RELATION,
)
from creme.reports.models import ReportChart

from .. import soft_references
from ..models import Field
from .base import Report, skipIfCustomReport


class ReportCollectorsTestCase(CremeTestCase):
    @skipIfCustomReport
    def test_collect__rtype(self):
        collector = soft_references.ReportRelationTypeRefCollector()
        self.assertEqual(RelationType, collector.model)
        self.assertEqual('reports-report-rtype', collector.id)

        rt1 = RelationType.objects.get(pk=REL_SUB_HAS)
        rt2 = RelationType.objects.get(pk=FAKE_REL_SUB_BILL_ISSUED)

        create_report = partial(
            Report.objects.create, user=self.get_root_user(), ct=FakeInvoice,
        )
        create_field = Field.objects.create

        report1 = create_report(name='Report with relation type')
        create_field(report=report1, name='name', type=RFT_FIELD,    order=1)
        create_field(report=report1, name=rt1.id, type=RFT_RELATION, order=2)

        report2 = create_report(name='Report with other relation type')
        create_field(report=report2, name='name', type=RFT_FIELD,    order=1)
        create_field(report=report2, name=rt2.id, type=RFT_RELATION, order=2)

        self.assertCountEqual([report1], collector.collect(rt1))
        self.assertCountEqual([report2], collector.collect(rt2))

    @skipIfCustomReport
    def test_collect__cfield(self):
        collector = soft_references.ReportCustomFieldTypeRefCollector()
        self.assertEqual(CustomField, collector.model)
        self.assertEqual('reports-report-cfield', collector.id)

        create_cfield = partial(CustomField.objects.create, content_type=FakeInvoice)
        cfield1 = create_cfield(name='Custom#1', field_type=CustomField.DATE)
        cfield2 = create_cfield(name='Custom#2', field_type=CustomField.INT)

        create_report = partial(
            Report.objects.create, user=self.get_root_user(), ct=FakeInvoice,
        )
        create_field = Field.objects.create

        report1 = create_report(name='Report with cfield1')
        create_field(report=report1, name='name',            type=RFT_FIELD,  order=1)
        create_field(report=report1, name=str(cfield1.uuid), type=RFT_CUSTOM, order=2)

        report2 = create_report(name='Report with cfield2')
        create_field(report=report2, name='name',            type=RFT_FIELD,  order=1)
        create_field(report=report2, name=str(cfield2.uuid), type=RFT_CUSTOM, order=2)

        report3 = create_report(name='Report with cfield1 (aggregate)')
        create_field(report=report3, name='name',                 type=RFT_FIELD,      order=1)
        create_field(report=report3, name=f'{cfield1.uuid}__avg', type=RFT_AGG_CUSTOM, order=2)

        report4 = create_report(name='Report with cfield1 (x2)')
        create_field(report=report4, name='name',                 type=RFT_FIELD,      order=1)
        create_field(report=report4, name=str(cfield1.uuid),      type=RFT_CUSTOM,     order=2)
        create_field(report=report4, name=f'{cfield1.uuid}__avg', type=RFT_AGG_CUSTOM, order=3)

        self.assertCountEqual([report1, report3, report4], collector.collect(cfield1))
        self.assertCountEqual([report2], collector.collect(cfield2))

    def test_global_registry(self):
        classes = {*soft_reference_registry.collector_classes}
        self.assertIn(soft_references.ReportRelationTypeRefCollector,    classes)
        self.assertIn(soft_references.ReportCustomFieldTypeRefCollector, classes)


class ChartCollectorsTestCase(CremeTestCase):
    @skipIfCustomReport
    def test_collect__rtype(self):
        collector = soft_references.ChartRelationTypeRefCollector()
        self.assertEqual(RelationType, collector.model)
        self.assertEqual('reports-chart-rtype', collector.id)

        rt1 = RelationType.objects.get(pk=REL_SUB_HAS)
        rt2 = RelationType.objects.get(pk=FAKE_REL_SUB_BILL_ISSUED)

        report = Report.objects.create(
            user=self.get_root_user(), ct=FakeInvoice, name='Reports with charts',
        )
        create_chart = partial(
            ReportChart.objects.create,
            linked_report=report,
            abscissa_type=ReportChart.Group.RELATION,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )
        chart1 = create_chart(name='Count things (1)', abscissa_cell_value=rt1.id)
        chart2 = create_chart(name='Count things (2)', abscissa_cell_value=rt2.id)

        self.assertCountEqual([chart1], collector.collect(rt1))
        self.assertCountEqual([chart2], collector.collect(rt2))

    @skipIfCustomReport
    def test_collect__cfield__date(self):
        collector = soft_references.ChartCustomFieldTypeRefCollector()
        self.assertEqual(CustomField, collector.model)
        self.assertEqual('reports-chart-cfield', collector.id)

        create_cfield = partial(CustomField.objects.create, content_type=FakeInvoice)
        date_cfield = create_cfield(name='Custom#1', field_type=CustomField.DATE)
        dt_cfield   = create_cfield(name='Custom#2', field_type=CustomField.DATETIME)
        enum_cfield = create_cfield(name='Custom#3', field_type=CustomField.ENUM)
        int_cfield  = create_cfield(name='Custom#4', field_type=CustomField.INT)

        report = Report.objects.create(
            user=self.get_root_user(), ct=FakeInvoice, name='Reports with charts',
        )
        create_chart = partial(
            ReportChart.objects.create,
            linked_report=report,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )
        chart1 = create_chart(
            name='Count things with date (1 - day)',
            abscissa_type=ReportChart.Group.CUSTOM_DAY,
            abscissa_cell_value=str(date_cfield.uuid),
        )
        chart2 = create_chart(
            name='Count things with date (2)',
            abscissa_type=ReportChart.Group.CUSTOM_DAY,
            abscissa_cell_value=str(dt_cfield.uuid),
        )
        chart3 = create_chart(
            name='Count things with date (1 - month)',
            abscissa_type=ReportChart.Group.CUSTOM_MONTH,
            abscissa_cell_value=str(date_cfield.uuid),
        )
        chart4 = create_chart(
            name='Count things with enum (3)',
            abscissa_type=ReportChart.Group.CUSTOM_FK,
            abscissa_cell_value=str(enum_cfield.uuid),
        )
        chart5 = create_chart(
            name='Sum things',
            abscissa_cell_value='created', abscissa_type=ReportChart.Group.YEAR,
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_cell_key=f'custom_field-{int_cfield.uuid}',
        )

        self.assertCountEqual([chart1, chart3], collector.collect(date_cfield))
        self.assertCountEqual([chart2], collector.collect(dt_cfield))
        self.assertCountEqual([chart4], collector.collect(enum_cfield))
        self.assertCountEqual([chart5], collector.collect(int_cfield))

    def test_global_registry(self):
        classes = {*soft_reference_registry.collector_classes}
        self.assertIn(soft_references.ChartRelationTypeRefCollector,    classes)
        self.assertIn(soft_references.ChartCustomFieldTypeRefCollector, classes)
