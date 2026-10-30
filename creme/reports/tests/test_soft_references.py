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
