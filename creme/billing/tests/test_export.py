from datetime import date
from decimal import Decimal
from functools import partial
from io import BytesIO
from json import dumps as json_dump
from pathlib import Path
from shutil import which
from unittest import skipIf
from zipfile import ZipFile

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import gettext as _

from creme.billing.bricks import BillingExportersBrick
from creme.billing.exporters import BillingExportEngineManager, ExporterFlavour
from creme.billing.exporters.latex import LatexExportEngine, LatexExporter
from creme.billing.exporters.xls import XLSExportEngine, XLSExporter
from creme.billing.models import (
    ExporterConfigItem,
    Line,
    PaymentInformation,
    SettlementTerms,
)
from creme.creme_core.gui.actions import action_registry
from creme.creme_core.models import FileRef, Vat
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.xlrd_utils import XlrdReader
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)
from creme.products import get_product_model, get_service_model
from creme.products.models import SubCategory
from creme.products.tests.base import skipIfCustomProduct, skipIfCustomService

from ..actions import BulkExportInvoiceAction, BulkExportQuoteAction
from ..forms.export import ExporterLocalisationField
from .base import (
    Address,
    CreditNote,
    Invoice,
    Organisation,
    ProductLine,
    Quote,
    SalesOrder,
    ServiceLine,
    TemplateBase,
    _BillingTestCase,
    skipIfCustomInvoice,
    skipIfCustomProductLine,
    skipIfCustomQuote,
    skipIfCustomServiceLine,
)
from .exporters.no_content_disposition import NoContentDispositionExportEngine
from .fake_exporters import OnlyInvoiceExportEngine

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


class ExporterLocalisationFieldTestCase(_BillingTestCase):
    def test_clean__empty__required(self):
        field = ExporterLocalisationField(required=True)
        msg = _('This field is required.')
        code = 'required'
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=None)
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='')

    def test_clean__empty__not_required(self):
        field = ExporterLocalisationField(required=False)

        with self.assertNoException():
            value = field.clean(None)

        self.assertIsNone(None, value)

    def test_clean__ok(self):
        manager = BillingExportEngineManager([
            'creme.billing.tests.fake_exporters.OnlyInvoiceExportEngine'
        ])
        field = ExporterLocalisationField(engine_manager=manager, model=Invoice)

        self.assertTupleEqual(
            ('FR', 'fr_FR'),
            field.clean(json_dump({
                'country': {
                    'country_code': 'FR',
                    'languages': ['fr_FR', 'en_EN'],
                },
                'language': {'language_code': 'fr_FR'},
            })),
        )
        self.assertTupleEqual(
            ('FR', 'en_EN'),
            field.clean(json_dump({
                'country': {
                    'country_code': 'FR',
                    'languages': ['fr_FR', 'en_EN'],
                },
                'language': {'language_code': 'en_EN'},
            })),
        )

    def test_clean__ok_agnostic(self):
        manager = BillingExportEngineManager([
            'creme.billing.exporters.xls.XLSExportEngine',
            'creme.billing.tests.fake_exporters.OnlyInvoiceExportEngine',
        ])
        field = ExporterLocalisationField(engine_manager=manager, model=Invoice)

        self.assertTupleEqual(
            ('FR', 'fr_FR'),
            field.clean(json_dump({
                'country': {
                    'country_code': 'FR',
                    'languages': ['fr_FR', 'en_EN'],
                },
                'language': {'language_code': 'fr_FR'},
            })),
        )
        self.assertTupleEqual(
            ('AGNOSTIC', ''),
            field.clean(json_dump({
                'country': {
                    'country_code': 'AGNOSTIC',
                    'languages': ['fr_FR', 'en_EN'],
                },
                'language': {'language_code': ''},
            })),
        )

    def test_clean__invalid_data_type_main(self):
        field = ExporterLocalisationField(required=False)
        code = 'invalidtype'
        msg = _('Invalid type')
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='"this is a string"',
        )
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='[]')

    def test_clean__invalid_format(self):
        field = ExporterLocalisationField(required=False)
        code = 'invalidformat'
        msg = _('Invalid format')
        self.assertFormfieldError(
            field=field, codes=code, messages=msg,
            value='{"country": "notadict"}',
        )
        self.assertFormfieldError(
            field=field, codes=code, messages=msg,
            value=json_dump({
                'country': {
                    'country_code': 'FR',
                    'languages': ['fr_FR', 'en_EN'],
                },
                'language': 'not a dict',
            }),
        )

    def test_clean__invalid_key_required(self):
        field = ExporterLocalisationField()
        country_msg = 'The country is required.'
        self.assertFormfieldError(
            field=field,
            value=json_dump({
                # 'country': {
                #     'country_code': 'FR',
                #     'languages': ['fr_FR', 'en_EN'],
                # },
                'language': {'language_code': 'en_EN'},
            }),
            codes='countryrequired', messages=country_msg,
        )
        self.assertFormfieldError(
            field=field,
            value=json_dump({
                'country': {
                    'country_code': '',  # <==
                    'languages': ['fr_FR', 'en_EN'],
                },
                'language': {'language_code': 'en_EN'},
            }),
            codes='countryrequired', messages=country_msg,
        )
        self.assertFormfieldError(
            field=field,
            value=json_dump({
                'country': {
                    'country_code': 'FR',
                    'languages': ['fr_FR', 'en_EN'],
                },
                # 'language': {'language_code': 'en_EN'},
            }),
            codes='languagerequired',
            messages='The language is required.',
        )

        self.assertFormfieldError(
            field=field,
            value=json_dump({
                'country': {
                    # 'country_code': 'FR',
                    'languages': ['fr_FR', 'en_EN'],
                },
                'language': {'language_code': 'en_EN'},
            }),
            codes='countryrequired', messages=country_msg,
        )
        self.assertFormfieldError(
            field=field,
            value=json_dump({
                'country': {
                    'country_code': 'FR',
                    'languages': ['fr_FR', 'en_EN'],
                },
                'language': {
                    # 'language_code': 'en_EN',
                },
            }),
            codes='invalidformat',  # TODO: 'languagerequired'
            messages=_('Invalid format'),
        )

    def test_clean__empty_country_not_required(self):
        field = ExporterLocalisationField(required=False)
        self.assertIsNone(
            field.clean(
                json_dump({
                    'country': {
                        'country_code': '',
                        'languages': [],
                    },
                    # 'language': {'language_code': 'en_EN'},
                }),
            )
        )

    def test_clean__error(self):
        manager = BillingExportEngineManager([
            'creme.billing.tests.fake_exporters.OnlyInvoiceExportEngine',
        ])
        self.assertFormfieldError(
            field=ExporterLocalisationField(engine_manager=manager, model=Invoice),
            value=json_dump({
                'country': {
                    'country_code': 'FR',
                    'languages': ['fr_FR', 'en_EN'],
                },
                'language': {
                    'language_code': 'it_IT',
                },
            }),
            messages='The couple country/language is invalid',
            codes='invalidlocalisation',
        )

    def test_initial__latex(self):
        manager = BillingExportEngineManager([
            'creme.billing.exporters.latex.LatexExportEngine',
        ])
        field = ExporterLocalisationField(engine_manager=manager, model=Invoice)

        self.assertJSONEqual(
            raw=field.from_python(('FR', 'fr_FR')),
            expected_data={
                'country': {
                    'country_code': 'FR',
                    'languages': ['fr_FR'],
                },
                'language': {
                    'language_code': 'fr_FR',
                },
            },
        )

    def test_initial__custom(self):
        manager = BillingExportEngineManager([
            'creme.billing.tests.fake_exporters.OnlyInvoiceExportEngine',
        ])
        field = ExporterLocalisationField(engine_manager=manager, model=Invoice)

        self.assertJSONEqual(
            raw=field.from_python(('FR', 'fr_FR')),
            expected_data={
                'country': {
                    'country_code': 'FR',
                    'languages': ['en_EN', 'fr_FR'],
                },
                'language': {
                    'language_code': 'fr_FR',
                },
            },
        )


# TODO: split
@skipIfCustomOrganisation
class ExportTestCase(BrickTestCaseMixin, _BillingTestCase):
    @staticmethod
    def _build_conf_url(ctype):
        return reverse('billing__edit_exporter_config', args=(ctype.id,))

    @staticmethod
    def _build_export_url(entity):
        return reverse('billing__export', args=(entity.id,))

    def test_flavour(self):
        flavour1 = ExporterFlavour('FR', 'fr_FR', 'basic')
        self.assertEqual('FR',    flavour1.country)
        self.assertEqual('fr_FR', flavour1.language)
        self.assertEqual('basic', flavour1.theme)
        self.assertEqual('FR/fr_FR/basic', flavour1.as_id())

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
    def test_exporter_latex(self):
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
    def test_exporter_xls(self):
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
    def test_exporter_weasyprint(self):
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
    def test_exporter_xhtml2pdf(self):
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

    def test_exporter_manager01(self):
        "Empty."
        manager = BillingExportEngineManager([])
        self.assertFalse([*manager.engine_classes])

        self.assertIsNone(manager.engine(engine_id='billing-latex', model=Invoice))
        self.assertIsNone(manager.engine(engine_id='billing-xls', model=Invoice))

        self.assertIsNone(manager.exporter(
            engine_id='billing-latex',
            flavour_id='donotcare',
            model=Invoice,
        ))

    def test_exporter_manager02(self):
        "Pass class directly."
        manager = BillingExportEngineManager([
            'creme.billing.exporters.latex.LatexExportEngine',
            'creme.billing.exporters.xls.XLSExportEngine',
            'creme.billing.tests.fake_exporters.OnlyInvoiceExportEngine',
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
    def test_exporter_manager03(self):
        "Default argument => use settings."
        manager = BillingExportEngineManager()

        engine1 = manager.engine(engine_id=LatexExportEngine.id, model=Invoice)
        self.assertIsInstance(engine1, LatexExportEngine)
        self.assertEqual(Invoice, engine1.model)

        engine2 = manager.engine(engine_id='billing-xls', model=Quote)
        self.assertIsInstance(engine2, XLSExportEngine)
        self.assertEqual(Quote, engine2.model)

    def test_exporter_manager04(self):
        "Invalid class."
        engine = BillingExportEngineManager([
            'creme.billing.exporters.latex.LatexExportEngine',
            'creme.billing.tests.fake_exporters.NotExporter',
        ])

        with self.assertRaises(BillingExportEngineManager.InvalidEngineClass):
            [*engine.engine_classes]  # NOQA

    def test_configuration_populate(self):
        get_ct = ContentType.objects.get_for_model
        self.get_object_or_fail(
            ExporterConfigItem,
            content_type=get_ct(Invoice),
            # engine_id='',
        )
        self.get_object_or_fail(
            ExporterConfigItem,
            content_type=get_ct(Quote),
            # engine_id='',
        )
        self.get_object_or_fail(
            ExporterConfigItem,
            content_type=get_ct(SalesOrder),
            # engine_id='',
        )
        self.get_object_or_fail(
            ExporterConfigItem,
            content_type=get_ct(CreditNote),
            # engine_id='',
        )
        self.get_object_or_fail(
            ExporterConfigItem,
            content_type=get_ct(TemplateBase),
            # engine_id='',
        )

    def test_configuration_portal(self):
        self.login_as_root()

        response = self.assertGET200(
            reverse('creme_config__app_portal', args=('billing',))
        )
        self.get_brick_node(
            self.get_html_tree(response.content), brick=BillingExportersBrick,
        )

        # TODO: complete

    @skipIf(xhtml2pdf_not_installed, 'The lib "xhtml2pdf" is not installed.')
    @override_settings(BILLING_EXPORTERS=[
        'creme.billing.exporters.xhtml2pdf.Xhtml2pdfExportEngine',
        'creme.billing.exporters.xls.XLSExportEngine',
    ])
    def test_configuration_edition01(self):
        self.login_as_standard(admin_4_apps=['billing'])

        ct = ContentType.objects.get_for_model(Invoice)
        ExporterConfigItem.objects.filter(
            content_type=ct,
        ).update(
            engine_id='',
            flavour_id='',
        )

        url = self._build_conf_url(ct)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            localisation_f = response1.context['form'].fields['localisation']

        self.assertIsNone(localisation_f.initial)
        # TODO: improve

        step_key = 'exporter_config_edition_wizard-current_step'
        response2 = self.client.post(
            url,
            data={
                step_key: '0',
                '0-localisation': json_dump({
                    'country': {
                        'country_code': 'FR',
                        'languages': ['en_EN', 'fr_FR'],
                    },
                    'language': {'language_code': 'fr_FR'},
                }),
            },
        )
        self.assertNoFormError(response2)

        with self.assertNoException():
            exporter_f = response2.context['form'].fields['exporter']

        exporter_id = 'billing-xhtml2pdf|FR/fr_FR/cappuccino'
        self.assertInChoices(
            value=exporter_id,
            label='.pdf - Xhtml2pdf - Thème Cappuccino (France)',
            choices=[(str(k), v) for k, v in exporter_f.choices],
        )
        self.assertIsNone(exporter_f.initial)

        response3 = self.client.post(
            url,
            data={
                step_key: '1',
                '1-exporter': exporter_id,
            },
        )
        self.assertNoFormError(response3)

        config_item = self.get_object_or_fail(ExporterConfigItem, content_type=ct)
        self.assertEqual(Xhtml2pdfExportEngine.id, config_item.engine_id)
        self.assertEqual('FR/fr_FR/cappuccino', config_item.flavour_id)

    @skipIf(xhtml2pdf_not_installed, 'The lib "xhtml2pdf" is not installed.')
    @override_settings(BILLING_EXPORTERS=[
        'creme.billing.exporters.xhtml2pdf.Xhtml2pdfExportEngine',
    ])
    def test_configuration_edition02(self):
        "Initial values."
        self.login_as_standard(admin_4_apps=['billing'])

        ct = ContentType.objects.get_for_model(Invoice)
        ExporterConfigItem.objects.filter(
            content_type=ct,
        ).update(
            engine_id=Xhtml2pdfExportEngine.id,
            flavour_id='FR/fr_FR/cappuccino',
        )

        url = self._build_conf_url(ct)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            localisation_f = response1.context['form'].fields['localisation']

        self.assertTupleEqual(('FR', 'fr_FR'), localisation_f.initial)

        # ---
        response2 = self.client.post(
            url,
            data={
                'exporter_config_edition_wizard-current_step': '0',
                '0-localisation': json_dump({
                    'country': {
                        'country_code': 'FR',
                        # 'languages': ['fr_FR'],  # useless
                    },
                    'language': {'language_code': 'fr_FR'},
                }),
            },
        )
        self.assertNoFormError(response2)

        with self.assertNoException():
            exporter_f = response2.context['form'].fields['exporter']

        self.assertEqual('billing-xhtml2pdf|FR/fr_FR/cappuccino', exporter_f.initial)

    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.xls.XLSExportEngine'])
    def test_configuration_edition__invalid_initial01(self):
        "Invalid initial value (flavour)."
        self.login_as_root()

        ct = ContentType.objects.get_for_model(Invoice)
        ExporterConfigItem.objects.filter(
            content_type=ct,
        ).update(
            engine_id=Xhtml2pdfExportEngine.id,
            flavour_id='BROKEN/foo_FOO/invalid',
        )

        response = self.assertGET200(self._build_conf_url(ct))

        with self.assertNoException():
            localisation_f = response.context['form'].fields['localisation']

        self.assertIsNone(localisation_f.initial)

    @skipIf(xhtml2pdf_not_installed, 'The lib "xhtml2pdf" is not installed.')
    @override_settings(BILLING_EXPORTERS=[
        'creme.billing.exporters.xhtml2pdf.Xhtml2pdfExportEngine',
    ])
    def test_configuration_edition__invalid_initial02(self):
        "Invalid initial value (engine)."
        self.login_as_root()

        ct = ContentType.objects.get_for_model(Invoice)
        ExporterConfigItem.objects.filter(
            content_type=ct,
        ).update(
            engine_id='billing-invalid',
            flavour_id='BROKEN/foo_FOO/invalid',
        )

        url = self._build_conf_url(ct)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            localisation_f = response1.context['form'].fields['localisation']

        self.assertIsNone(localisation_f.initial)

        # ---
        response2 = self.client.post(
            url,
            data={
                'exporter_config_edition_wizard-current_step': '0',
                '0-localisation': json_dump({
                    'country': {
                        'country_code': 'FR',
                        'languages': ['fr_FR'],
                    },
                    'language': {'language_code': 'fr_FR'},
                }),
            },
        )
        self.assertNoFormError(response2)

        with self.assertNoException():
            exporter_f = response2.context['form'].fields['exporter']

        self.assertIsNone(exporter_f.initial)

    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.xls.XLSExportEngine'])
    def test_configuration_edition__not_allowed(self):
        "Not admin credentials."
        self.login_as_standard()  # Not admin_4_apps=['billing']

        ct = ContentType.objects.get_for_model(Invoice)
        self.assertGET403(reverse('billing__edit_exporter_config', args=(ct.id,)))

    def test_export_error__bad_ctype(self):
        user = self.login_as_root_and_get()
        orga = Organisation.objects.create(user=user, name='Laputa')
        self.assertGET404(self._build_export_url(orga))

        # TODO: test with a billing model but not managed

    @skipIfCustomQuote
    def test_export_error__empty_configuration(self):
        user = self.login_as_root_and_get()
        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]

        ExporterConfigItem.objects.filter(
            content_type=quote.entity_type,
        ).update(
            engine_id='',
            flavour_id='',
        )

        response = self.client.get(self._build_export_url(quote), follow=True)
        self.assertContains(
            response,
            _(
                'The engine is not configured; '
                'go to the configuration of the app «Billing».'
            ),
            status_code=409,
            html=True,
        )

    @skipIfCustomQuote
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.xls.XLSExportEngine'])
    def test_export_error__invalid_configuration(self):
        user = self.login_as_root_and_get()
        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]

        ExporterConfigItem.objects.filter(
            content_type=quote.entity_type,
        ).update(engine_id=LatexExportEngine.id)

        response = self.client.get(self._build_export_url(quote), follow=True)
        self.assertContains(
            response,
            _(
                'The configured exporter is invalid; '
                'go to the configuration of the app «Billing».'
            ),
            status_code=409,
            html=True,
        )

    @skipIfCustomQuote
    @override_settings(BILLING_EXPORTERS=[
        'creme.billing.tests.fake_exporters.OnlyInvoiceExportEngine',
    ])
    def test_export_error__incompatible_ctype(self):
        user = self.login_as_root_and_get()
        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]

        ExporterConfigItem.objects.filter(
            content_type=quote.entity_type,
        ).update(
            engine_id=OnlyInvoiceExportEngine.id,
            flavour_id='FR/fr_FR/basic',
        )

        response = self.client.get(self._build_export_url(quote), follow=True)
        self.assertContains(
            response,
            _(
                'The configured exporter is invalid; '
                'go to the configuration of the app «Billing».'
            ),
            status_code=409,
            html=True,
        )

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    @skipIf(latex_not_installed, '"lualatex" and "latexmk" are not installed.')
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.latex.LatexExportEngine'])
    def test_export_invoice_latex(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='My Invoice', discount=0)[0]

        ExporterConfigItem.objects.filter(
            content_type=invoice.entity_type,
        ).update(
            engine_id=LatexExportEngine.id,
            flavour_id='FR/fr_FR/clear',
        )

        create_line = partial(
            ProductLine.objects.create,
            user=user, related_document=invoice,
        )
        for price in ('10', '20'):
            create_line(on_the_fly_item=f'Fly {price}', unit_price=Decimal(price))

        existing_fileref_ids = [*FileRef.objects.values_list('id', flat=True)]

        response = self.assertGET200(self._build_export_url(invoice), follow=True)
        self.assertEqual('application/pdf', response['Content-Type'])

        fileref = self.get_alone_element(FileRef.objects.exclude(id__in=existing_fileref_ids))
        self.assertTrue(fileref.temporary)
        self.assertEqual(f"{_('Invoice')}_{invoice.id}.pdf", fileref.basename)
        self.assertEqual(user, fileref.user)
        self.assertEqual(_('Latex export for «{}»').format(invoice), fileref.description)

        fullpath = Path(fileref.filedata.path)
        self.assertTrue(fullpath.exists(), f'<{fullpath}> does not exists?!')
        self.assertEqual(Path(settings.MEDIA_ROOT, 'billing'), fullpath.parent)
        self.assertEqual(
            f'attachment; filename="{fileref.basename}"',
            response['Content-Disposition'],
        )

        # Consume stream to avoid ResourceWarning
        b''.join(response.streaming_content)

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    @skipIf(weasyprint_not_installed, 'The lib "weasyprint" is not installed.')
    @override_settings(BILLING_EXPORTERS=[
        'creme.billing.exporters.weasyprint.WeasyprintExportEngine',
    ])
    def test_export_invoice_weasyprint(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='My Invoice', discount=0)[0]

        ExporterConfigItem.objects.filter(
            content_type=invoice.entity_type,
        ).update(
            engine_id=WeasyprintExportEngine.id,
            flavour_id='FR/fr_FR/mint',
        )

        create_line = partial(
            ProductLine.objects.create,
            user=user, related_document=invoice,
        )
        for price in ('10', '20'):
            create_line(on_the_fly_item=f'Fly {price}', unit_price=Decimal(price))

        existing_fileref_ids = [*FileRef.objects.values_list('id', flat=True)]

        response = self.assertGET200(self._build_export_url(invoice), follow=True)
        self.assertEqual('application/pdf', response['Content-Type'])

        fileref = self.get_alone_element(FileRef.objects.exclude(id__in=existing_fileref_ids))
        self.assertTrue(fileref.temporary)
        self.assertEqual('{}_{}.pdf'.format(_('Invoice'), invoice.id), fileref.basename)
        self.assertEqual(user, fileref.user)
        self.assertEqual(_('Weasyprint export for «{}»').format(invoice), fileref.description)

        fullpath = Path(fileref.filedata.path)
        self.assertTrue(fullpath.exists(), f'<{fullpath}> does not exists?!')
        self.assertEqual(Path(settings.MEDIA_ROOT, 'billing'), fullpath.parent)
        self.assertEqual(
            f'attachment; filename="{fileref.basename}"',
            response['Content-Disposition'],
        )

        # Consume stream to avoid ResourceWarning
        b''.join(response.streaming_content)

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    @skipIf(xhtml2pdf_not_installed, 'The lib "xhtml2pdf" is not installed.')
    @override_settings(BILLING_EXPORTERS=[
        'creme.billing.exporters.xhtml2pdf.Xhtml2pdfExportEngine',
    ])
    def test_export_invoice_xhtml2pdf(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='My Invoice', discount=0)[0]

        ExporterConfigItem.objects.filter(
            content_type=invoice.entity_type,
        ).update(
            engine_id=Xhtml2pdfExportEngine.id,
            flavour_id='FR/fr_FR/cappuccino',
        )

        create_line = partial(
            ProductLine.objects.create,
            user=user, related_document=invoice,
        )
        for price in ('10', '20'):
            create_line(on_the_fly_item=f'Fly {price}', unit_price=Decimal(price))

        response = self.assertGET200(self._build_export_url(invoice), follow=True)
        self.assertEqual('application/pdf', response['Content-Type'])

        from pypdf import PdfReader
        with self.assertNoException():
            pdf_reader = PdfReader(BytesIO(response.content))
        self.assertEqual(1, pdf_reader.get_num_pages())
        # TODO: improve test

    @skipIfCustomAddress
    @skipIfCustomProduct
    @skipIfCustomService
    @skipIfCustomInvoice
    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.xls.XLSExportEngine'])
    def test_export_invoice_xls01(self):
        user = self.login_as_root_and_get()
        payment_type = SettlementTerms.objects.create(name='23 days')
        order_number = 'PI31416'

        # source: siret / naf / rcs / tvaintra
        invoice, source, target = self.create_invoice_n_orgas(
            user=user, name='My Invoice',
            discount=0, payment_type=payment_type.id,
            comment='Very important invoice',
            buyers_order_number=order_number,
        )

        create_addr = Address.objects.create
        source.billing_address = addr1 = create_addr(
            owner=source,
            name="Source's billing address", address='Temple of sand',
            po_box='8778', zipcode='123', city='Suna',
            department='dep1', state='Foo', country='Land of Wind',
        )
        source.siret = 'SIRET1'
        source.naf = 'NAF1'
        source.rcs = 'RCS1'
        source.tvaintra = 'TVA1'
        source.save()

        target.shipping_address = addr2 = create_addr(
            owner=target,
            name="Target's shipping address", address='Temple of trees',
            po_box='6565', zipcode='789', city='Konoha',
            department='dep2', state='Stuff', country='Land of Fire',
        )
        target.save()

        vat = Vat.objects.get_or_create(value=10)[0]

        payment_info = PaymentInformation.objects.create(
            organisation=source,
            name='RIB 1',
            bank_code='123456',
            counter_code='ABC123',
            account_number='foobarbaz',
            rib_key='31416',
            banking_domiciliation='Wonderland',
            is_default=True,
        )
        invoice.payment_info = payment_info

        invoice.billing_address = addr3 = create_addr(
            owner=invoice,
            name="Invoice's billing address", address='Temple of sea',
            po_box='4569', zipcode='456', city='Kiri',
            department='dep3', state='baz', country='Land of Water',
        )
        invoice.shipping_address = addr4 = create_addr(
            owner=invoice,
            name="Invoice's shipping address", address='Temple of cloud',
            po_box='8787', zipcode='111', city='Kumo',
            department='dep4', state='Stuff', country='Land of Lightning',
        )

        invoice.save()

        ExporterConfigItem.objects.filter(
            content_type=invoice.entity_type,
        ).update(engine_id=XLSExportEngine.id)

        subcat1, subcat2 = SubCategory.objects.all()[:2]
        currency_str = invoice.currency.local_symbol

        create_pline = partial(
            ProductLine.objects.create,
            user=user, related_document=invoice, vat_value=vat,
        )
        pline1 = create_pline(
            on_the_fly_item='Unsaved product',
            unit_price=Decimal('10'),
            quantity=Decimal('1'),
            order=2,
        )
        product = get_product_model().objects.create(
            user=user, name='Saved product',
            category=subcat1.category, sub_category=subcat1,
            unit_price=Decimal('20'),
        )
        create_pline(
            related_item=product,
            unit_price=product.unit_price,
            quantity=Decimal('2'),
            discount=Decimal('5'),
            discount_unit=Line.Discount.PERCENT,
            order=1,
        )

        create_sline = partial(
            ServiceLine.objects.create,
            user=user, related_document=invoice, vat_value=vat,
        )
        sline1 = create_sline(
            on_the_fly_item='Unsaved service',
            unit_price=Decimal('11'),
            quantity=Decimal('2'),
            discount=Decimal('6'),
            discount_unit=Line.Discount.LINE_AMOUNT,
            comment='This line is important',
        )
        service = get_service_model().objects.create(
            user=user, name='Saved service',
            category=subcat2.category, sub_category=subcat2,
            unit_price=Decimal('15'),
        )
        create_sline(
            related_item=service,
            unit_price=service.unit_price,
            quantity=Decimal('1'),
            discount=Decimal('5.5'),
            discount_unit=Line.Discount.ITEM_AMOUNT,
        )

        existing_fileref_ids = [*FileRef.objects.values_list('id', flat=True)]

        response = self.assertGET200(self._build_export_url(invoice), follow=True)
        self.assertEqual('application/vnd.ms-excel', response['Content-Type'])

        fileref = self.get_alone_element(FileRef.objects.exclude(id__in=existing_fileref_ids))
        self.assertTrue(fileref.temporary)
        self.assertEqual(f"{_('Invoice')}_{invoice.id}.xls", fileref.basename)
        self.assertEqual(user, fileref.user)
        self.assertEqual(_('Excel export for «{}»').format(invoice), fileref.description)

        full_path = Path(fileref.filedata.path)
        self.assertTrue(full_path.exists(), f'<{full_path}> does not exists?!')
        self.assertEqual(Path(settings.MEDIA_ROOT, 'billing'), full_path.parent)

        lines = iter(XlrdReader(None, file_contents=b''.join(response.streaming_content)))

        self.assertListEqual([str(source)], next(lines)[:1])
        self.assertListEqual(
            [
                addr1.address, addr1.po_box, addr1.zipcode,
                addr1.city, addr1.department, addr1.state, addr1.country,
            ],
            next(lines)[:7],
        )
        self.assertListEqual(
            [source.siret, source.naf, source.rcs, source.tvaintra],
            next(lines)[:4],
        )
        self.assertListEqual([str(target)], next(lines)[:1])
        self.assertListEqual(
            [
                addr2.address, addr2.po_box, addr2.zipcode,
                addr2.city, addr2.department, addr2.state, addr2.country,
            ],
            next(lines)[:7],
        )

        self.assertListEqual(
            [
                date_format(date(year=2010, month=9, day=7),   'DATE_FORMAT'),
                date_format(date(year=2010, month=10, day=13), 'DATE_FORMAT'),
            ],
            next(lines)[:2],
        )
        self.assertListEqual(
            [
                addr3.address, addr3.po_box, addr3.zipcode,
                addr3.city, addr3.department, addr3.state, addr3.country,
            ],
            next(lines)[:7],
        )
        self.assertListEqual(
            [
                addr4.address, addr4.po_box, addr4.zipcode,
                addr4.city, addr4.department, addr4.state, addr4.country,
            ],
            next(lines)[:7],
        )
        self.assertListEqual(
            [
                '',  # No number
                payment_type.name,
                order_number,
            ],
            next(lines)[:3],
        )
        self.assertListEqual(
            [
                payment_info.bank_code,
                payment_info.counter_code,
                payment_info.account_number,
                payment_info.rib_key,
                payment_info.banking_domiciliation,
            ],
            next(lines)[:5],
        )
        self.assertListEqual(
            [invoice.currency.name, '0.00', invoice.comment],
            next(lines)[:3],
        )
        self.assertListEqual(
            [str(invoice.total_no_vat), str(invoice.total_vat)],
            next(lines)[:2],
        )
        self.assertListEqual(
            [
                product.name,
                '2.00', '20.00',
                '5.00', '%',
                '40.00',
            ],
            next(lines)[:6],
        )
        self.assertListEqual(
            [
                pline1.on_the_fly_item,
                '1.00', '10.00',
                '0.00', '%',
                '10.00',
            ],
            next(lines)[:6],
        )
        self.assertListEqual(
            [
                sline1.on_the_fly_item, '2.00', '11.00',
                '6.00', _('{currency} per line').format(currency=currency_str),
                '22.00', '16.00', '17.60',
                sline1.comment,
            ],
            next(lines)[:9],
        )
        self.assertListEqual(
            [
                service.name, '1.00', '15.00',
                '5.50', _('{currency} per unit').format(currency=currency_str),
                '15.00', '9.50', '10.45',
                '',
            ],
            next(lines)[:9],
        )

        with self.assertRaises(StopIteration):
            next(lines)

    @skipIfCustomInvoice
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.xls.XLSExportEngine'])
    def test_export_invoice_xls02(self):
        "Number, no issuing_date, no settlement terms, no payment info, global discount..."
        user = self.login_as_root_and_get()

        invoice, source, target = self.create_invoice_n_orgas(
            user=user, name='My Invoice',
            discount=Decimal('6.3'),
            issuing_date='',
            expiration_date='',
            number='INV-0001',
        )

        # invoice.generate_number()
        # invoice.save()

        invoice = self.refresh(invoice)  # total 0 => 0.00 ...

        ExporterConfigItem.objects.filter(
            content_type=invoice.entity_type,
        ).update(engine_id=XLSExportEngine.id)

        response = self.assertGET200(self._build_export_url(invoice), follow=True)
        self.assertEqual('application/vnd.ms-excel', response['Content-Type'])

        lines = iter(XlrdReader(None, file_contents=b''.join(response.streaming_content)))

        self.assertListEqual([str(source)], next(lines)[:1])
        self.assertListEqual([''], next(lines)[:1])  # Address
        self.assertListEqual([''], next(lines)[:1])  # SIRET
        self.assertListEqual([str(target)], next(lines)[:1])
        self.assertListEqual([''], next(lines)[:1])  # Address
        self.assertListEqual(
            [
                '',  # No issuing_date
                '',  # No expiration_date
            ],
            next(lines)[:2],
        )
        self.assertListEqual([invoice.billing_address.address],  next(lines)[:1])
        self.assertListEqual([invoice.shipping_address.address], next(lines)[:1])
        self.assertListEqual(
            [
                invoice.number,
                '',  # No payment_type
                # '',  # No buyer's order number
            ],
            next(lines)[:3],
        )
        self.assertListEqual(
            [
                '',  # payment_info.bank_code,
                '',  # payment_info.counter_code,
                # '',  # payment_info.account_number,
                # '',  # payment_info.rib_key,
                # '',  # payment_info.banking_domiciliation,
            ],
            next(lines)[:5]
        )
        self.assertListEqual(
            [invoice.currency.name, '6.30'],
            next(lines)[:3],
        )
        self.assertListEqual(
            [str(invoice.total_no_vat), str(invoice.total_vat)],
            next(lines)[:2],
        )

    @skipIfCustomQuote
    @skipIfCustomServiceLine
    @skipIf(latex_not_installed, '"lualatex" and "latexmk" are not installed.')
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.latex.LatexExportEngine'])
    def test_export_quote_latex(self):
        user = self.login_as_root_and_get()
        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]

        ExporterConfigItem.objects.filter(
            content_type=quote.entity_type,
        ).update(
            engine_id='billing-latex',
            flavour_id='FR/fr_FR/clear',
        )

        create_line = partial(
            ServiceLine.objects.create,
            user=user, related_document=quote,
        )

        for price in ('10', '20'):
            create_line(on_the_fly_item='Fly ' + price, unit_price=Decimal(price))

        response = self.assertGET200(self._build_export_url(quote), follow=True)
        self.assertEqual('application/pdf', response['Content-Type'])

        # Consume stream to avoid ResourceWarning
        b''.join(response.streaming_content)

    @skipIfCustomQuote
    @skipIfCustomProductLine
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.xls.XLSExportEngine'])
    def test_export_quote_xls(self):
        user = self.login_as_root_and_get()

        quote, source, target = self.create_quote_n_orgas(
            user=user, name='My Invoice', comment='Very important quote',
        )
        vat = Vat.objects.get_or_create(value=10)[0]

        payment_info = PaymentInformation.objects.create(
            organisation=source,
            name='RIB #1',
            bank_code='B999',
            counter_code='123789-BC',
            account_number='0000',
            rib_key='42',
            banking_domiciliation='Fantasia',
            is_default=True,
        )
        quote.payment_info = payment_info
        quote.save()

        ExporterConfigItem.objects.filter(
            content_type=quote.entity_type,
        ).update(engine_id=XLSExportEngine.id)

        pline = ProductLine.objects.create(
            user=user, related_document=quote, vat_value=vat,
            on_the_fly_item='Unsaved product',
            unit_price=Decimal('10'),
            quantity=Decimal('1'),
        )

        existing_fileref_ids = [*FileRef.objects.values_list('id', flat=True)]

        response = self.assertGET200(self._build_export_url(quote), follow=True)
        self.assertEqual('application/vnd.ms-excel', response['Content-Type'])

        fileref = self.get_alone_element(FileRef.objects.exclude(id__in=existing_fileref_ids))
        self.assertEqual(f"{_('Quote')}_{quote.id}.xls", fileref.basename)

        lines = iter(XlrdReader(None, file_contents=b''.join(response.streaming_content)))

        self.assertListEqual([str(source)], next(lines)[:1])
        self.assertListEqual([''], next(lines)[:1])
        self.assertListEqual([''], next(lines)[:1])
        self.assertListEqual([str(target)], next(lines)[:1])
        self.assertListEqual([''], next(lines)[:1])
        self.assertListEqual(
            [
                date_format(date(year=2011, month=3, day=15), 'DATE_FORMAT'),
                date_format(date(year=2012, month=4, day=22), 'DATE_FORMAT'),
            ],
            next(lines)[:2],
        )
        self.assertListEqual([quote.billing_address.address],  next(lines)[:1])
        self.assertListEqual([quote.shipping_address.address], next(lines)[:1])
        self.assertListEqual(
            [
                # '0',  # No number
                '',  # No number
                '',  # No payment_type,
            ],
            next(lines)[:2],
        )
        self.assertListEqual(
            [
                payment_info.bank_code,
                payment_info.counter_code,
                payment_info.account_number,
                payment_info.rib_key,
                payment_info.banking_domiciliation,
            ],
            next(lines)[:5],
        )
        self.assertListEqual(
            [quote.currency.name, '0.00', quote.comment],
            next(lines)[:3],
        )
        self.assertListEqual(
            [str(quote.total_no_vat), str(quote.total_vat)],
            next(lines)[:2],
        )
        self.assertListEqual(
            [
                pline.on_the_fly_item,
                '1.00', '10.00',
                '0.00', '%',
                '10.00',
            ],
            next(lines)[:6],
        )

    @skipIfCustomQuote
    @skipIfCustomServiceLine
    @skipIf(weasyprint_not_installed, 'The lib "weasyprint" is not installed.')
    @override_settings(BILLING_EXPORTERS=[
        'creme.billing.exporters.weasyprint.WeasyprintExportEngine',
    ])
    def test_export_quote_weasyprint(self):
        user = self.login_as_root_and_get()
        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]

        ExporterConfigItem.objects.filter(
            content_type=quote.entity_type,
        ).update(
            engine_id=WeasyprintExportEngine.id,
            flavour_id='FR/fr_FR/mint',
        )

        create_line = partial(
            ServiceLine.objects.create,
            user=user, related_document=quote,
        )

        for price in ('10', '20'):
            create_line(on_the_fly_item='Fly ' + price, unit_price=Decimal(price))

        response = self.assertGET200(self._build_export_url(quote), follow=True)
        self.assertEqual('application/pdf', response['Content-Type'])

        # Consume stream to avoid ResourceWarning
        b''.join(response.streaming_content)

    @skipIfCustomQuote
    @skipIfCustomServiceLine
    @skipIf(xhtml2pdf_not_installed, 'The lib "xhtml2pdf" is not installed.')
    @override_settings(BILLING_EXPORTERS=[
        'creme.billing.exporters.xhtml2pdf.Xhtml2pdfExportEngine',
    ])
    def test_export_quote_xhtml2pdf(self):
        user = self.login_as_root_and_get()
        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]

        ExporterConfigItem.objects.filter(
            content_type=quote.entity_type,
        ).update(
            engine_id=Xhtml2pdfExportEngine.id,
            flavour_id='FR/fr_FR/cappuccino',
        )

        create_line = partial(
            ServiceLine.objects.create,
            user=user, related_document=quote,
        )

        for price in ('10', '20'):
            create_line(on_the_fly_item='Fly ' + price, unit_price=Decimal(price))

        response = self.assertGET200(self._build_export_url(quote), follow=True)
        self.assertEqual('application/pdf', response['Content-Type'])

    @skipIfCustomInvoice
    def test_export_credentials(self):
        "Billing entity credentials."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice, Organisation],
        )
        self.add_credentials(user.role, own=['VIEW', 'LINK', 'UNLINK'])

        invoice, source, target = self.create_invoice_n_orgas(
            user=user, name='My Invoice', discount=0,
        )
        invoice.user = self.get_root_user()
        invoice.save()

        self.assertFalse(user.has_perm_to_view(invoice))
        self.assertTrue(user.has_perm_to_view(source))
        self.assertTrue(user.has_perm_to_view(target))

        self.assertGET403(self._build_export_url(invoice))

    @skipIf(latex_not_installed, '"lualatex" and "latexmk" are not installed.')
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.latex.LatexExportEngine'])
    @skipIfCustomInvoice
    def test_export_latex_credentials01(self):
        "Source credentials."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice, Organisation],
        )
        self.add_credentials(user.role, own=['VIEW', 'LINK', 'UNLINK'])

        invoice, source, target = self.create_invoice_n_orgas(
            user=user, name='My Invoice', discount=0,
        )
        source.user = self.get_root_user()
        source.save()

        self.assertTrue(user.has_perm_to_view(invoice))
        self.assertFalse(user.has_perm_to_view(source))
        self.assertTrue(user.has_perm_to_view(target))

        ExporterConfigItem.objects.filter(
            content_type=invoice.entity_type,
        ).update(engine_id=LatexExportEngine.id)
        self.assertGET403(self._build_export_url(invoice))

    @skipIf(latex_not_installed, '"lualatex" and "latexmk" are not installed.')
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.latex.LatexExportEngine'])
    @skipIfCustomInvoice
    def test_export_latex_credentials02(self):
        "Target credentials."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice, Organisation],
        )
        self.add_credentials(user.role, own=['VIEW', 'LINK', 'UNLINK'])

        invoice, source, target = self.create_invoice_n_orgas(
            user=user, name='My Invoice', discount=0,
        )
        target.user = self.get_root_user()
        target.save()

        self.assertTrue(user.has_perm_to_view(invoice))
        self.assertTrue(user.has_perm_to_view(source))
        self.assertFalse(user.has_perm_to_view(target))

        ExporterConfigItem.objects.filter(
            content_type=invoice.entity_type,
        ).update(engine_id=LatexExportEngine.id)
        self.assertGET403(self._build_export_url(invoice))


@skipIfCustomOrganisation
class BulkExportTestCase(_BillingTestCase):
    @staticmethod
    def _build_url(model):
        return reverse(
            'billing__bulk_export',
            args=(ContentType.objects.get_for_model(model).id,),
        )

    @skipIfCustomInvoice
    @skipIf(xhtml2pdf_not_installed, 'The lib "xhtml2pdf" is not installed.')
    @override_settings(
        BILLING_EXPORTERS=['creme.billing.exporters.xhtml2pdf.Xhtml2pdfExportEngine'],
        BILLING_BULK_EXPORT_LIMIT=50,
    )
    def test_invoice__xhtml2pdf(self):
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice, Organisation],
        )
        self.add_credentials(user.role, own=['VIEW', 'LINK'])
        source, target = self.create_orgas(user=user)

        existing_file_ref_ids = [*FileRef.objects.values_list('id', flat=True)]

        create_invoice = partial(self.create_invoice, user=user, source=source, target=target)
        invoice1 = create_invoice(name='Invoice #1')
        invoice2 = create_invoice(name='Invoice #2')

        ExporterConfigItem.objects.filter(
            content_type=invoice1.entity_type,
        ).update(
            engine_id=Xhtml2pdfExportEngine.id,
            flavour_id='FR/fr_FR/cappuccino',
        )

        response = self.assertGET200(
            self._build_url(Invoice),
            follow=True,
            data={'id': [invoice1.id, invoice2.id]},
        )
        self.assertEqual('application/zip', response['Content-Type'])

        with self.assertNoException():
            zip_file = ZipFile(BytesIO(b''.join(response.streaming_content)))

        name1 = f'{_("Invoice")}_{invoice1.id}.pdf'
        self.assertCountEqual(
            [name1, f'{_("Invoice")}_{invoice2.id}.pdf'],
            zip_file.namelist(),
        )

        from pypdf import PdfReader
        with self.assertNoException():
            with zip_file.open(name1) as pdf_file1:
                pdf_reader1 = PdfReader(pdf_file1)
                num_pages1 = pdf_reader1.get_num_pages()
        self.assertEqual(1, num_pages1)
        # TODO complete pdf test

        file_ref = self.get_alone_element(
            FileRef.objects.exclude(id__in=existing_file_ref_ids)
        )
        self.assertEqual(user, file_ref.user)
        self.assertEqual(f'{_("Invoices")}_X2.zip', file_ref.basename)
        self.assertEqual(
            _('Bulk export of {count} {model}').format(count=2, model=_('Invoices')),
            file_ref.description,
        )

    @skipIfCustomQuote
    @override_settings(
        BILLING_EXPORTERS=['creme.billing.exporters.xls.XLSExportEngine'],
        BILLING_BULK_EXPORT_LIMIT=50,
    )
    def test_quote__xls(self):
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Quote, Organisation],
        )
        self.add_credentials(user.role, own=['VIEW', 'LINK'])
        source, target = self.create_orgas(user=user)

        existing_file_ref_ids = [*FileRef.objects.values_list('id', flat=True)]

        create_quote = partial(self.create_quote, user=user, source=source, target=target)
        quote1 = create_quote(name='Quote #1')
        quote2 = create_quote(name='Quote #2')
        quote3 = create_quote(name='Quote #3')

        ExporterConfigItem.objects.filter(
            content_type=quote1.entity_type,
        ).update(engine_id=XLSExportEngine.id)

        response = self.assertGET200(
            self._build_url(Quote),
            follow=True,
            data={'id': [quote1.id, quote2.id, quote3.id]},
        )
        self.assertEqual('application/zip', response['Content-Type'])

        with self.assertNoException():
            zip_file = ZipFile(BytesIO(b''.join(response.streaming_content)))

        name1 = f'{_("Quote")}_{quote1.id}.xls'
        self.assertCountEqual(
            [name1, f'{_("Quote")}_{quote2.id}.xls', f'{_("Quote")}_{quote3.id}.xls'],
            zip_file.namelist(),
        )

        with self.assertNoException():
            with zip_file.open(name1) as xls_file1:
                xl_reader = XlrdReader(None, file_contents=xls_file1.read())

        self.assertEqual(12, xl_reader.sheet.nrows)
        # TODO: improve tests for content

        file_ref = self.get_alone_element(
            FileRef.objects.exclude(id__in=existing_file_ref_ids)
        )
        self.assertEqual(user, file_ref.user)
        self.assertEqual(f'{_("Quotes")}_X3.zip', file_ref.basename)
        self.assertEqual(
            _('Bulk export of {count} {model}').format(count=3, model=_('Quotes')),
            file_ref.description,
        )

    @skipIfCustomQuote
    @override_settings(
        BILLING_EXPORTERS=[
            'creme.billing.tests.exporters.no_content_disposition.NoContentDispositionExportEngine'
        ],
        BILLING_BULK_EXPORT_LIMIT=50,
    )
    def test_warning__backend_no_content_disposition(self):
        user = self.login_as_root_and_get()
        source, target = self.create_orgas(user=user)

        create_quote = partial(self.create_quote, user=user, source=source, target=target)
        quote1 = create_quote(name='Quote #1')
        quote2 = create_quote(name='Quote #2')

        ExporterConfigItem.objects.filter(
            content_type=quote1.entity_type,
        ).update(engine_id=NoContentDispositionExportEngine.id)

        with self.assertLogs(level='CRITICAL') as logs_manager:
            response = self.assertGET200(
                self._build_url(Quote),
                follow=True,
                data={'id': [quote1.id, quote2.id]},
            )
        self.assertIn(
            'The export backend response has no Content-Disposition',
            logs_manager.output[0],
        )

        with self.assertNoException():
            zip_file = ZipFile(BytesIO(b''.join(response.streaming_content)))

        self.assertCountEqual(
            [f'{_("Quote")}_{quote1.id}', f'{_("Quote")}_{quote2.id}'],
            zip_file.namelist(),
        )

    @override_settings(BILLING_BULK_EXPORT_LIMIT=5)
    def test_error__list(self):
        self.login_as_root()
        url = self._build_url(Invoice)

        # Empty ---
        response1 = self.client.get(
            url, follow=True,  # data={'id': [...]},
        )
        self.assertContains(response1, 'The list of IDs is empty', status_code=409)

        # Too long ---
        response2 = self.client.get(
            url, follow=True, data={'id': [12, 13, 14, 15, 16, 17]},
        )
        self.assertContains(
            response2,
            'The length of the ID list cannot be greater than 5',
            status_code=409,
        )

        # Bad type ---
        response3 = self.client.get(
            url, follow=True, data={'id': [12, 'not_int', 14]},
        )
        self.assertContains(response3, 'Some IDs are invalid', status_code=409)

    def test_error__app_perms(self):
        user = self.login_as_standard(allowed_apps=['persons'])  # 'billing'
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        response = self.client.get(
            self._build_url(Invoice), follow=True, data={'id': [12, 14]},
        )
        self.assertContains(
            response,
            _('You are not allowed to access to the app: {}').format(_('Billing')),
            status_code=403, html=True,
        )

    @skipIfCustomInvoice
    @override_settings(BILLING_BULK_EXPORT_LIMIT=50)
    def test_error__view_perms(self):
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice, Organisation],
        )
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        source, target = self.create_orgas(user=user)

        create_invoice = partial(self.create_invoice, user=user, source=source, target=target)
        invoice1 = create_invoice(name='Invoice #1')
        invoice2 = create_invoice(name='Invoice #2')

        invoice2.user = self.get_root_user()
        invoice2.save()

        response = self.client.get(
            self._build_url(Invoice),
            follow=True, data={'id': [invoice1.id, invoice2.id]},
        )
        self.assertContains(
            response,
            _('Some entities are invalid or not viewable'),
            status_code=403,
        )

    @skipIfCustomInvoice
    @override_settings(
        # BILLING_EXPORTERS=['creme.billing.exporters.xhtml2pdf.Xhtml2pdfExportEngine'],
        BILLING_BULK_EXPORT_LIMIT=50,
    )
    def test_error__empty_configuration(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice')[0]

        ExporterConfigItem.objects.filter(
            content_type=invoice.entity_type,
        ).update(
            engine_id='',
            flavour_id='',
        )

        response = self.client.get(
            self._build_url(Invoice), follow=True, data={'id': [invoice.id]},
        )
        self.assertContains(
            response,
            _(
                'The engine is not configured; '
                'go to the configuration of the app «Billing».'
            ),
            status_code=409,
            html=True,
        )

    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.xls.XLSExportEngine'])
    def test_error__invalid_configuration(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice')[0]

        ExporterConfigItem.objects.filter(
            content_type=invoice.entity_type,
        ).update(engine_id=LatexExportEngine.id)

        response = self.client.get(
            self._build_url(Invoice), follow=True, data={'id': [invoice.id]},
        )
        self.assertContains(
            response,
            _(
                'The configured exporter is invalid; '
                'go to the configuration of the app «Billing».'
            ),
            status_code=409,
            html=True,
        )

    def test_error__not_billing_entity(self):
        user = self.login_as_root_and_get()
        contact = user.linked_contact
        model = type(contact)

        response = self.client.get(
            self._build_url(model), follow=True, data={'id': [contact.id]},
        )
        self.assertContains(
            response, 'This model is not allowed:', status_code=409,
        )

    def test_action_invoice(self):
        self.assertIn(
            BulkExportInvoiceAction,
            action_registry.bulk_action_classes(model=Invoice),
        )

        self.assertEqual('billing-export_invoice', BulkExportInvoiceAction.id)
        self.assertEqual(Invoice, BulkExportInvoiceAction.model)
        self.assertEqual(1,       BulkExportInvoiceAction.bulk_min_count)
        self.assertEqual(
            settings.BILLING_BULK_EXPORT_LIMIT,
            BulkExportInvoiceAction.bulk_max_count,
        )

        self.assertEqual(_('Download as zipped PDF'), BulkExportInvoiceAction.label)
        self.assertEqual(
            self._build_url(Invoice),
            BulkExportInvoiceAction(user=self.get_root_user()).url,
        )

    def test_action_quote(self):
        self.assertIn(
            BulkExportQuoteAction,
            action_registry.bulk_action_classes(model=Quote),
        )

        self.assertEqual('billing-export_quote', BulkExportQuoteAction.id)
        self.assertEqual(Quote, BulkExportQuoteAction.model)
        self.assertEqual(
            settings.BILLING_BULK_EXPORT_LIMIT,
            BulkExportQuoteAction.bulk_max_count,
        )
        self.assertEqual(
            self._build_url(Quote),
            BulkExportQuoteAction(user=self.get_root_user()).url,
        )
