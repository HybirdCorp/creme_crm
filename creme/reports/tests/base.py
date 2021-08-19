# -*- coding: utf-8 -*-

from datetime import datetime
from decimal import Decimal
from functools import partial
from json import dumps as json_dump
from unittest import skipIf

from django.contrib.contenttypes.models import ContentType
from django.db.models import Field as ModelField
from django.urls import reverse
from django.utils.timezone import now

from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    CustomField,
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
from creme.creme_core.tests.fake_models import (
    FakeContact,
    FakeImage,
    FakeInvoice,
    FakeInvoiceLine,
    FakeOrganisation,
)

from .. import (
    constants,
    get_report_model,
    get_rgraph_model,
    report_model_is_custom,
    rgraph_model_is_custom,
)
from ..models import Field
from .fake_models import FakeReportsDocument, FakeReportsFolder

skip_report_tests = report_model_is_custom()
skip_rgraph_tests = rgraph_model_is_custom()

Report = get_report_model()
ReportGraph = get_rgraph_model()


def skipIfCustomReport(test_func):
    return skipIf(skip_report_tests, 'Custom Report model in use')(test_func)


def skipIfCustomRGraph(test_func):
    return skipIf(skip_rgraph_tests, 'Custom ReportGraph model in use')(test_func)


class AxisFieldsMixin:
    @staticmethod
    def formfield_value_abscissa(*, abscissa, graph_type, parameter=''):
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
                'graph_type': {
                    'type_id': graph_type,
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

    def _create_simple_contacts_report(self, name='Contact report', efilter=None, user=None):
        report = Report.objects.create(
            user=user or self.user,
            name=name,
            ct=FakeContact,
            filter=efilter,
        )
        Field.objects.create(
            report=report, name='last_name', type=constants.RFT_FIELD, order=1,
        )

        return report

    def _create_contacts_report(self, name='Report #1', efilter=None, user=None):
        report = self._create_simple_contacts_report(name=name, efilter=efilter, user=user)

        create_field = partial(Field.objects.create, report=report)
        create_field(name='user',                  type=constants.RFT_FIELD,    order=2)
        create_field(name=REL_SUB_HAS,             type=constants.RFT_RELATION, order=3)
        create_field(name='get_pretty_properties', type=constants.RFT_FUNCTION, order=4)

        return report

    def _create_simple_documents_report(self, user=None):
        report = Report.objects.create(
            name='Documents report',
            user=user or self.user,
            ct=FakeReportsDocument,
        )

        create_field = partial(Field.objects.create, report=report, type=constants.RFT_FIELD)
        create_field(name='title',       order=1)
        create_field(name="description", order=2)

        return report

    def _create_simple_organisations_report(self, name='Orga report', efilter=None):
        report = Report.objects.create(
            user=self.user, name=name, ct=FakeOrganisation, filter=efilter,
        )
        Field.objects.create(report=report, name='name', type=constants.RFT_FIELD, order=1)

        return report

    def get_field_or_fail(self, report, field_name):
        try:
            return report.fields.get(name=field_name)
        except Field.DoesNotExist as e:
            self.fail(str(e))

    def _create_persons(self):
        user = self.user

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

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_kawaii', text='Kawaii',
        )
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
        user = self.user
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

    def _create_documents_rgraph(self, user=None):
        user = user or self.user
        report = self._create_simple_documents_report(user)
        return ReportGraph.objects.create(
            user=user,
            linked_report=report,
            name='Number of created documents / year',
            # abscissa_cell_value='created', abscissa_type=constants.RGT_YEAR,
            abscissa_cell_value='created',
            abscissa_type=ReportGraph.Group.YEAR,
            # ordinate_type=constants.RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )
