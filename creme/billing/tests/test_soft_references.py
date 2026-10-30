from functools import partial

from creme.billing.models import (
    CreditNoteStatus,
    InvoiceStatus,
    QuoteStatus,
    SalesOrderStatus,
)
from creme.creme_core.core.soft_reference import soft_reference_registry
from creme.creme_core.models import MinionModel
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_models import FakeSector
from creme.persons.tests.base import skipIfCustomOrganisation

from ..models import CreditNote, Invoice, Quote, SalesOrder, TemplateBase
from ..soft_references import TemplateBaseStatusRefCollector
from .base import Organisation


class TemplateBaseStatusRefCollectorTestCase(CremeTestCase):
    @staticmethod
    def _create_templatebase(*, user, model, index, status, emitter, receiver):
        return TemplateBase.objects.create(
            user=user, ct=model, name=f'Template #{index}',
            status_uuid=status.uuid,
            source=emitter, target=receiver,
        )

    @skipIfCustomOrganisation
    def test_collect(self):
        collector = TemplateBaseStatusRefCollector()
        self.assertEqual(MinionModel, collector.model)
        self.assertEqual('billing-template-status', collector.id)

        invoice_status = InvoiceStatus.objects.create(name='OK')
        other_invoice_status = InvoiceStatus.objects.first()

        quote_status = QuoteStatus.objects.create(name='OK', uuid=invoice_status.uuid)
        order_status = SalesOrderStatus.objects.create(name='OK')
        cnote_status = CreditNoteStatus.objects.create(name='OK')

        user = self.get_root_user()
        create_orga = partial(Organisation.objects.create, user=user)
        emitter = create_orga(name='Source')
        receiver = create_orga(name='Target')

        create_tpl = partial(
            self._create_templatebase, user=user, emitter=emitter, receiver=receiver,
        )
        invoice_tpl = create_tpl(index=1, model=Invoice, status=invoice_status)
        create_tpl(index=2, model=Invoice, status=other_invoice_status)
        quote_tpl = create_tpl(index=3, model=Quote, status=quote_status)
        order_tpl = create_tpl(index=3, model=SalesOrder, status=order_status)
        cnote_tpl = create_tpl(index=3, model=CreditNote, status=cnote_status)

        self.assertCountEqual([invoice_tpl], collector.collect(invoice_status))
        self.assertCountEqual([quote_tpl],   collector.collect(quote_status))
        self.assertCountEqual([order_tpl],   collector.collect(order_status))
        self.assertCountEqual([cnote_tpl],   collector.collect(cnote_status))

        # Not billing model ---
        sector = FakeSector.objects.create(title='Ignore me')
        with self.assertNoException():
            [*collector.collect(sector)]  # NOQA

    def test_global_registry(self):
        self.assertIn(
            TemplateBaseStatusRefCollector,
            soft_reference_registry.collector_classes,
        )
