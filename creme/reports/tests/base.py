# -*- coding: utf-8 -*-

skip_report_tests = False
skip_rgraph_tests = False

try:
    from datetime import datetime
    from decimal import Decimal
    from functools import partial
    from unittest import skipIf

    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse
    from django.utils.timezone import now

    from creme.creme_core.core.entity_cell import (EntityCellRegularField,
            EntityCellFunctionField, EntityCellRelation)
    from creme.creme_core.models import (CremePropertyType, CremeProperty,
            HeaderFilter, Relation, RelationType)
    from creme.creme_core.constants import REL_SUB_HAS
    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.fake_models import (FakeContact, FakeOrganisation,
            FakeImage, FakeInvoice, FakeInvoiceLine)
    from creme.creme_core.tests.fake_constants import (
            FAKE_REL_SUB_BILL_ISSUED as REL_SUB_BILL_ISSUED,
            FAKE_REL_SUB_BILL_RECEIVED as REL_SUB_BILL_RECEIVED)

    from .fake_models import FakeReportsFolder, FakeReportsDocument

    from .. import (report_model_is_custom, rgraph_model_is_custom,
            get_report_model, get_rgraph_model)
    from ..constants import RFT_FIELD
    from ..models import Field

    skip_report_tests = report_model_is_custom()
    skip_rgraph_tests = rgraph_model_is_custom()

    Report = get_report_model()
    ReportGraph = get_rgraph_model()
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


def skipIfCustomReport(test_func):
    return skipIf(skip_report_tests, 'Custom Report model in use')(test_func)


def skipIfCustomRGraph(test_func):
    return skipIf(skip_rgraph_tests, 'Custom ReportGraph model in use')(test_func)


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

    def _create_report(self, name='Report #1', efilter=None, extra_cells=()):
        cells = [EntityCellRegularField.build(model=FakeContact, name='last_name'),
                 EntityCellRegularField.build(model=FakeContact, name='user'),
                 EntityCellRelation(model=FakeContact, rtype=RelationType.objects.get(pk=REL_SUB_HAS)),
                 EntityCellFunctionField.build(model=FakeContact, func_field_name='get_pretty_properties'),
                ]
        cells.extend(extra_cells)

        hf = HeaderFilter.create(pk='test_hf', name='name', model=FakeContact, cells_desc=cells)

        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'user':   self.user.pk,
                                          'name':   name,
                                          'ct':     ContentType.objects.get_for_model(FakeContact).id,
                                          'hf':     hf.id,
                                          'filter': efilter.id if efilter else '',
                                         }
                                   )
        self.assertNoFormError(response)

        return self.get_object_or_fail(Report, name=name)

    def _create_simple_contacts_report(self, name='Contact report', efilter=None):
        ct = ContentType.objects.get_for_model(FakeContact)
        report = Report.objects.create(user=self.user, name=name, ct=ct, filter=efilter)
        Field.objects.create(report=report, name='last_name', type=RFT_FIELD, order=1)

        return report

    def _create_simple_documents_report(self):
        report = Report.objects.create(name="Documents report", user=self.user,
                                           ct=ContentType.objects.get_for_model(FakeReportsDocument)
                                          )

        create_field = partial(Field.objects.create, report=report, type=RFT_FIELD)
        create_field(name='title',       order=1)
        create_field(name="description", order=2)

        return report

    def _create_simple_organisations_report(self, name='Orga report', efilter=None):
        ct = ContentType.objects.get_for_model(FakeOrganisation)
        report = Report.objects.create(user=self.user, name=name, ct=ct, filter=efilter)
        Field.objects.create(report=report, name='name', type=RFT_FIELD, order=1)

        return report

    def get_field_or_fail(self, report, field_name):
        try:
            return report.fields.get(name=field_name)
        except Field.DoesNotExist as e:
            self.fail(str(e))

    def _create_persons(self):
        user = self.user
        create_contact = partial(FakeContact.objects.create, user=user)
        create_contact(last_name='Langley', first_name='Asuka',  birthday=datetime(year=1981, month=7, day=25))
        rei    = create_contact(last_name='Ayanami',   first_name='Rei',    birthday=datetime(year=1981, month=3, day=26))
        misato = create_contact(last_name='Katsuragi', first_name='Misato', birthday=datetime(year=1976, month=8, day=12))

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        ptype = CremePropertyType.create(str_pk='test-prop_kawaii', text='Kawaii')
        CremeProperty.objects.create(type=ptype, creme_entity=rei)

        Relation.objects.create(user=user, type_id=REL_SUB_HAS,
                                subject_entity=misato, object_entity=nerv
                               )

    def _create_invoice(self, source, target, name="Invoice#01",
                        total_vat=Decimal("0"), issuing_date=None,
                       ):
        user = self.user
        invoice = FakeInvoice.objects.create(user=user,
                                             issuing_date=issuing_date or now().date(),
                                             name=name,
                                             total_vat=total_vat,
                                            )

        FakeInvoiceLine.objects.create(user=user, linked_invoice=invoice, item='Stuff',
                                       quantity=Decimal("1"), unit_price=total_vat,
                                      )

        create_rel = partial(Relation.objects.create, subject_entity=invoice, user=user)
        create_rel(type_id=REL_SUB_BILL_ISSUED,   object_entity=source)
        create_rel(type_id=REL_SUB_BILL_RECEIVED, object_entity=target)

        return invoice
