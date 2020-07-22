from creme.billing import get_invoice_model
from creme.billing.exporters import (
    BillingExportEngine,
    BillingExporter,
    ExporterFlavour,
)
from creme.creme_core.models import FileRef


class NotExporter:
    pass


class OnlyInvoiceExporter(BillingExporter):
    def export(self, *, entity, user):
        return FileRef()

    def screenshots(self):
        yield 'common/images/400_200.png'


class OnlyInvoiceExportEngine(BillingExportEngine):
    id = BillingExportEngine.generate_id('billing', 'test_only_invoice')
    verbose_name = 'Only invoice'

    @property
    def flavours(self):
        yield ExporterFlavour('FR', 'fr_FR', 'basic')
        yield ExporterFlavour('FR', 'fr_FR', 'clear')
        yield ExporterFlavour('FR', 'en_EN', 'clear')
        yield ExporterFlavour('BE', 'fr_BE', 'clear')

    def exporter(self, flavour):
        if self.model != get_invoice_model():
            return None

        return OnlyInvoiceExporter(
            verbose_name='Only invoice',
            engine=self,
            flavour=flavour,
        )
