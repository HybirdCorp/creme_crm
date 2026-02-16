from shutil import which
from unittest import skipIf

from django.test.utils import override_settings
from django.utils.translation import gettext as _

from creme.billing.exporters import BillingExportEngineManager, ExporterFlavour
from creme.billing.exporters.latex import LatexExportEngine, LatexExporter
from creme.billing.exporters.xls import XLSExportEngine, XLSExporter
from creme.persons.tests.base import skipIfCustomOrganisation

from .base import Invoice, Organisation, Quote, _BillingTestCase
from .fake_exporters.only_invoice import OnlyInvoiceExportEngine

latex_not_installed = which('lualatex') is None or which('latexmk') is None

try:
    import weasyprint  # NOQA
except ImportError:
    weasyprint_not_installed = True
else:
    weasyprint_not_installed = False
    from creme.billing.exporters.weasyprint import (
        WeasyprintExportEngine,
        WeasyprintExporter,
    )

try:
    import xhtml2pdf  # NOQA
except ImportError:
    xhtml2pdf_not_installed = True
else:
    xhtml2pdf_not_installed = False
    from creme.billing.exporters.xhtml2pdf import (
        Xhtml2pdfExportEngine,
        Xhtml2pdfExporter,
    )


# TODO: split
@skipIfCustomOrganisation
class ExportersTestCase(_BillingTestCase):
    def test_flavour(self):
        flavour1 = ExporterFlavour('FR', 'fr_FR', 'basic')
        self.assertEqual('FR',    flavour1.country)
        self.assertEqual('fr_FR', flavour1.language)
        self.assertEqual('basic', flavour1.theme)
        self.assertEqual('FR/fr_FR/basic', flavour1.as_id())
        self.assertEqual('ExporterFlavour("FR", "fr_FR", "basic")', repr(flavour1))

        flavour2 = ExporterFlavour.from_id('FR/fr_FR/basic')
        self.assertIsInstance(flavour2, ExporterFlavour)
        self.assertEqual('FR',    flavour2.country)
        self.assertEqual('fr_FR', flavour2.language)
        self.assertEqual('basic', flavour2.theme)
        self.assertEqual(flavour1, flavour2)

        self.assertNotEqual(
            flavour1,
            ExporterFlavour('IT', flavour1.language, flavour1.theme)
        )
        self.assertNotEqual(
            flavour1,
            ExporterFlavour(flavour1.country, 'fr_BE', flavour1.theme)
        )
        self.assertNotEqual(
            flavour1,
            ExporterFlavour(flavour1.country, flavour1.language, 'cappuccino')
        )

        flavour3 = ExporterFlavour.from_id('BE/fr_BE')
        self.assertEqual('BE',    flavour3.country)
        self.assertEqual('fr_BE', flavour3.language)
        self.assertEqual('',      flavour3.theme)

        flavour4 = ExporterFlavour.from_id('IT/it_IT/theme/with/odd/name')
        self.assertEqual('IT',    flavour4.country)
        self.assertEqual('it_IT', flavour4.language)
        self.assertEqual('theme/with/odd/name', flavour4.theme)

    @skipIf(latex_not_installed, '"lualatex" and "latexmk" are not installed.')
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.latex.LatexExportEngine'])
    def test_exporter__latex(self):
        engine1 = LatexExportEngine(Quote)
        flavour_args = ('FR', 'fr_FR', 'clear')

        flavours = [*engine1.flavours]
        self.assertIn(
            ExporterFlavour(*flavour_args),
            flavours,
        )

        exporter = engine1.exporter(
            flavour=ExporterFlavour(*flavour_args),
        )
        self.assertIsInstance(exporter, LatexExporter)
        self.assertEqual(
            '.pdf - LateX - Thème clair (France)',
            exporter.verbose_name,
        )
        self.assertIs(engine1, exporter.engine)
        self.assertEqual(
            ExporterFlavour(*flavour_args),
            exporter.flavour,
        )
        self.assertEqual('billing-latex|FR/fr_FR/clear', exporter.id)
        self.assertEqual(
            'billing/export/latex/FR/fr_FR/clear/quote.tex',
            exporter.template_path,
        )
        self.assertListEqual(
            ['billing/sample_latex.png'],
            [*exporter.screenshots],
        )

        # ---
        engine2 = LatexExportEngine(Organisation)
        self.assertFalse([*engine2.flavours])

    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.xls.XLSExportEngine'])
    def test_exporter__xls(self):
        engine = XLSExportEngine(Quote)
        self.assertListEqual(
            [ExporterFlavour(country='AGNOSTIC')], [*engine.flavours],
        )

        exporter = engine.exporter(flavour=ExporterFlavour(country='AGNOSTIC'))
        self.assertIsInstance(exporter, XLSExporter)
        self.assertEqual(_('.xls (data for template)'), exporter.verbose_name)
        self.assertIs(engine, exporter.engine)
        self.assertEqual(
            ExporterFlavour(country='AGNOSTIC'),
            exporter.flavour,
        )
        self.assertFalse([*exporter.screenshots])

    @skipIf(weasyprint_not_installed, '"weasyprint" is not installed.')
    @override_settings(BILLING_EXPORTERS=[
        'creme.billing.exporters.weasyprint.WeasyprintExportEngine',
    ])
    def test_exporter__weasyprint(self):
        engine1 = WeasyprintExportEngine(Invoice)
        flavour_args = ('FR', 'fr_FR', 'mint')

        flavours = [*engine1.flavours]
        self.assertIn(
            ExporterFlavour(*flavour_args),
            flavours,
        )

        exporter = engine1.exporter(
            flavour=ExporterFlavour(*flavour_args),
        )
        self.assertIsInstance(exporter, WeasyprintExporter)
        self.assertEqual(
            '.pdf - WeasyPrint - Thème Menthe (France)',
            exporter.verbose_name,
        )
        self.assertIs(engine1, exporter.engine)
        self.assertEqual(
            ExporterFlavour(*flavour_args),
            exporter.flavour,
        )
        self.assertEqual('billing-weasyprint|FR/fr_FR/mint', exporter.id)
        self.assertEqual(
            'billing/export/weasyprint/FR/fr_FR/mint/invoice.html',
            exporter.html_template_path,
        )
        self.assertListEqual(
            ['billing/sample_weasyprint.png'],
            [*exporter.screenshots],
        )

        # ---
        engine2 = LatexExportEngine(Organisation)
        self.assertFalse([*engine2.flavours])

    @skipIf(xhtml2pdf_not_installed, '"xhtml2pdf" is not installed.')
    @override_settings(BILLING_EXPORTERS=[
        'creme.billing.exporters.xhtml2pdf.Xhtml2pdfExportEngine']
    )
    def test_exporter__xhtml2pdf(self):
        engine1 = Xhtml2pdfExportEngine(Invoice)
        flavour_args = ('FR', 'fr_FR', 'cappuccino')

        flavours = [*engine1.flavours]
        self.assertIn(
            ExporterFlavour(*flavour_args),
            flavours,
        )

        exporter = engine1.exporter(
            flavour=ExporterFlavour(*flavour_args),
        )
        self.assertIsInstance(exporter, Xhtml2pdfExporter)
        self.assertEqual(
            '.pdf - Xhtml2pdf - Thème Cappuccino (France)',
            exporter.verbose_name,
        )
        self.assertIs(engine1, exporter.engine)
        self.assertEqual(
            ExporterFlavour(*flavour_args),
            exporter.flavour,
        )
        self.assertEqual('billing-xhtml2pdf|FR/fr_FR/cappuccino', exporter.id)
        self.assertEqual(
            'billing/export/xhtml2pdf/FR/fr_FR/cappuccino/invoice.html',
            exporter.template_path,
        )
        self.assertListEqual(
            ['billing/sample_xhtml2pdf.png'],
            [*exporter.screenshots],
        )

        # ---
        engine2 = Xhtml2pdfExportEngine(Organisation)
        self.assertFalse([*engine2.flavours])

    def test_exporter_manager__empty(self):
        manager = BillingExportEngineManager([])
        self.assertFalse([*manager.engine_classes])

        self.assertIsNone(manager.engine(engine_id='billing-latex', model=Invoice))
        self.assertIsNone(manager.engine(engine_id='billing-xls', model=Invoice))

        self.assertIsNone(manager.exporter(
            engine_id='billing-latex',
            flavour_id='donotcare',
            model=Invoice,
        ))

    def test_exporter_manager__class(self):
        "Pass class directly."
        manager = BillingExportEngineManager([
            'creme.billing.exporters.latex.LatexExportEngine',
            'creme.billing.exporters.xls.XLSExportEngine',
            'creme.billing.tests.fake_exporters.only_invoice.OnlyInvoiceExportEngine',
        ])
        self.assertCountEqual(
            [LatexExportEngine, XLSExportEngine, OnlyInvoiceExportEngine],
            [*manager.engine_classes]
        )

        # Engine ---
        engine1 = manager.engine(engine_id='billing-latex', model=Invoice)
        self.assertIsInstance(engine1, LatexExportEngine)
        self.assertEqual(Invoice, engine1.model)

        engine2 = manager.engine(engine_id=XLSExportEngine.id, model=Quote)
        self.assertIsInstance(engine2, XLSExportEngine)
        self.assertEqual(Quote, engine2.model)

        # Exporter ---
        exporter1 = manager.exporter(
            engine_id=LatexExportEngine.id,
            flavour_id='FR/fr_FR/clear',
            model=Invoice,
        )
        self.assertIsInstance(exporter1, LatexExporter)
        self.assertEqual(
            'billing/export/latex/FR/fr_FR/clear/invoice.tex',
            exporter1.template_path,
        )

        self.assertIsNone(
            manager.exporter(
                engine_id=LatexExportEngine.id,
                flavour_id='wonderland/fr_FR/clear',
                model=Invoice,
            )
        )

    @override_settings(BILLING_EXPORTERS=[
        'creme.billing.exporters.latex.LatexExportEngine',
        'creme.billing.exporters.xls.XLSExportEngine',
    ])
    def test_exporter_manager__settings(self):
        "Default argument => use settings."
        manager = BillingExportEngineManager()

        engine1 = manager.engine(engine_id=LatexExportEngine.id, model=Invoice)
        self.assertIsInstance(engine1, LatexExportEngine)
        self.assertEqual(Invoice, engine1.model)

        engine2 = manager.engine(engine_id='billing-xls', model=Quote)
        self.assertIsInstance(engine2, XLSExportEngine)
        self.assertEqual(Quote, engine2.model)

    def test_exporter_manager__invalid_class(self):
        engine = BillingExportEngineManager([
            'creme.billing.exporters.latex.LatexExportEngine',
            'creme.billing.tests.fake_exporters.NotExporter',
        ])

        with self.assertRaises(BillingExportEngineManager.InvalidEngineClass):
            [*engine.engine_classes]  # NOQA
