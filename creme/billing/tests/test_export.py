# -*- coding: utf-8 -*-

from datetime import date
from decimal import Decimal
from functools import partial
from json import dumps as json_dump
from os.path import dirname, exists, join
from shutil import which
from unittest import skipIf

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
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import FileRef, SetCredentials, Vat
from creme.creme_core.tests.forms.base import FieldTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.xlrd_utils import XlrdReader
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)
from creme.products import get_product_model, get_service_model
from creme.products.models import SubCategory
from creme.products.tests.base import skipIfCustomProduct, skipIfCustomService

# from .. import constants
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
from .fake_exporters import OnlyInvoiceExportEngine

pdflatex_not_installed = which('pdflatex') is None

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


class ExporterLocalisationFieldTestCase(FieldTestCase):
    def test_clean_empty_required(self):
        clean = ExporterLocalisationField(required=True).clean
        self.assertFieldValidationError(ExporterLocalisationField, 'required', clean, None)
        self.assertFieldValidationError(ExporterLocalisationField, 'required', clean, '')

    def test_clean_empty_not_required(self):
        field = ExporterLocalisationField(required=False)

        with self.assertNoException():
            value = field.clean(None)

        self.assertIsNone(None, value)

    def test_clean01(self):
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

    def test_ok_agnostic(self):
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

    def test_clean_invalid_data_type_main(self):
        clean = ExporterLocalisationField(required=False).clean
        self.assertFieldValidationError(
            ExporterLocalisationField, 'invalidtype', clean, '"this is a string"',
        )
        self.assertFieldValidationError(
            ExporterLocalisationField, 'invalidtype', clean, '[]',
        )

    def test_clean_invalid_format(self):
        field = ExporterLocalisationField(required=False)
        self.assertFieldValidationError(
            ExporterLocalisationField,
            'invalidformat',
            field.clean,
            '{"country": "notadict"}',
        )
        self.assertFieldValidationError(
            ExporterLocalisationField,
            'invalidformat',
            field.clean,
            json_dump({
                'country': {
                    'country_code': 'FR',
                    'languages': ['fr_FR', 'en_EN'],
                },
                'language': 'not a dict',
            }),
        )

    def test_clean_invalid_key_required(self):
        field = ExporterLocalisationField()
        self.assertFieldValidationError(
            ExporterLocalisationField,
            'countryrequired',
            field.clean,
            json_dump({
                # 'country': {
                #     'country_code': 'FR',
                #     'languages': ['fr_FR', 'en_EN'],
                # },
                'language': {'language_code': 'en_EN'},
            }),
        )
        self.assertFieldValidationError(
            ExporterLocalisationField,
            'countryrequired',
            field.clean,
            json_dump({
                'country': {
                    'country_code': '',  # <==
                    'languages': ['fr_FR', 'en_EN'],
                },
                'language': {'language_code': 'en_EN'},
            }),
        )
        self.assertFieldValidationError(
            ExporterLocalisationField,
            'languagerequired',
            field.clean,
            json_dump({
                'country': {
                    'country_code': 'FR',
                    'languages': ['fr_FR', 'en_EN'],
                },
                # 'language': {'language_code': 'en_EN'},
            }),
        )

        self.assertFieldValidationError(
            ExporterLocalisationField,
            'countryrequired',
            field.clean,
            json_dump({
                'country': {
                    # 'country_code': 'FR',
                    'languages': ['fr_FR', 'en_EN'],
                },
                'language': {'language_code': 'en_EN'},
            }),
        )
        self.assertFieldValidationError(
            ExporterLocalisationField,
            # 'languagerequired',  TODO
            'invalidformat',
            field.clean,
            json_dump({
                'country': {
                    'country_code': 'FR',
                    'languages': ['fr_FR', 'en_EN'],
                },
                'language': {
                    # 'language_code': 'en_EN',
                },
            }),
        )

    def test_clean_empty_country_not_required(self):
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

    def test_clean_error(self):
        manager = BillingExportEngineManager([
            'creme.billing.tests.fake_exporters.OnlyInvoiceExportEngine',
        ])
        field = ExporterLocalisationField(engine_manager=manager, model=Invoice)
        self.assertFieldValidationError(
            ExporterLocalisationField,
            'invalidlocalisation',
            field.clean,
            json_dump({
                'country': {
                    'country_code': 'FR',
                    'languages': ['fr_FR', 'en_EN'],
                },
                'language': {
                    'language_code': 'it_IT',
                },
            }),
        )

    def test_initial01(self):
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

    def test_initial02(self):
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

    @skipIf(pdflatex_not_installed, '"pdflatex" is not installed.')
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
        self.login()

        response = self.assertGET200(
            reverse('creme_config__app_portal', args=('billing',))
        )
        self.get_brick_node(
            self.get_html_tree(response.content), BillingExportersBrick.id_,
        )

        # TODO: complete

    @skipIf(xhtml2pdf_not_installed, 'The lib "xhtml2pdf" is not installed.')
    @override_settings(BILLING_EXPORTERS=[
        'creme.billing.exporters.xhtml2pdf.Xhtml2pdfExportEngine',
        'creme.billing.exporters.xls.XLSExportEngine',
    ])
    def test_configuration_edition01(self):
        self.login(is_superuser=False, admin_4_apps=['billing'])

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
        self.login(is_superuser=False, admin_4_apps=['billing'])

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
    def test_configuration_edition03(self):
        "Invalid initial value."
        self.login()

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

    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.xls.XLSExportEngine'])
    def test_configuration_edition04(self):
        "Not admin credentials."
        self.login(is_superuser=False)  # Not admin_4_apps=['billing']

        ct = ContentType.objects.get_for_model(Invoice)
        self.assertGET403(reverse('billing__edit_exporter_config', args=(ct.id,)))

    def test_export_error01(self):
        "Bad CT."
        user = self.login()
        orga = Organisation.objects.create(user=user, name='Laputa')
        self.assertGET404(self._build_export_url(orga))

        # TODO: test with a billing model but not managed

    @skipIfCustomQuote
    def test_export_error02(self):
        "Empty configuration."
        self.login()
        quote = self.create_quote_n_orgas('My Quote')[0]

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
                'The engine is not configured ; '
                'go to the configuration of the app «Billing».'
            ),
            status_code=409,
            html=True,
        )

    @skipIfCustomQuote
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.xls.XLSExportEngine'])
    def test_export_error03(self):
        "Invalid configuration."
        self.login()
        quote = self.create_quote_n_orgas('My Quote')[0]

        ExporterConfigItem.objects.filter(
            content_type=quote.entity_type,
        ).update(engine_id=LatexExportEngine.id)

        response = self.client.get(self._build_export_url(quote), follow=True)
        self.assertContains(
            response,
            _(
                'The configured exporter is invalid ; '
                'go to the configuration of the app «Billing».'
            ),
            status_code=409,
            html=True,
        )

    @skipIfCustomQuote
    @override_settings(BILLING_EXPORTERS=[
        'creme.billing.tests.fake_exporters.OnlyInvoiceExportEngine',
    ])
    def test_export_error04(self):
        "Incompatible CT."
        self.login()
        quote = self.create_quote_n_orgas('My Quote')[0]

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
                'The configured exporter is invalid ; '
                'go to the configuration of the app «Billing».'
            ),
            status_code=409,
            html=True,
        )

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    @skipIf(pdflatex_not_installed, '"pdflatex" is not installed.')
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.latex.LatexExportEngine'])
    def test_export_invoice_latex(self):
        user = self.login()
        invoice = self.create_invoice_n_orgas('My Invoice', discount=0)[0]

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

        filerefs = FileRef.objects.exclude(id__in=existing_fileref_ids)
        self.assertEqual(1, len(filerefs))

        fileref = filerefs[0]
        self.assertTrue(fileref.temporary)
        self.assertEqual(f"{_('Invoice')}_{invoice.id}.pdf", fileref.basename)
        self.assertEqual(user, fileref.user)

        fullpath = fileref.filedata.path
        self.assertTrue(exists(fullpath), f'<{fullpath}> does not exists?!')
        # self.assertEqual(join(settings.MEDIA_ROOT, 'upload', 'billing'), dirname(fullpath))
        self.assertEqual(join(settings.MEDIA_ROOT, 'billing'), dirname(fullpath))
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
        user = self.login()
        invoice = self.create_invoice_n_orgas('My Invoice', discount=0)[0]

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

        filerefs = FileRef.objects.exclude(id__in=existing_fileref_ids)
        self.assertEqual(1, len(filerefs))

        fileref = filerefs[0]
        self.assertTrue(fileref.temporary)
        self.assertEqual('{}_{}.pdf'.format(_('Invoice'), invoice.id), fileref.basename)
        self.assertEqual(user, fileref.user)

        fullpath = fileref.filedata.path
        self.assertTrue(exists(fullpath), f'<{fullpath}> does not exists?!')
        # self.assertEqual(join(settings.MEDIA_ROOT, 'upload', 'billing'), dirname(fullpath))
        self.assertEqual(join(settings.MEDIA_ROOT, 'billing'), dirname(fullpath))
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
        user = self.login()
        invoice = self.create_invoice_n_orgas('My Invoice', discount=0)[0]

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

    @skipIfCustomAddress
    @skipIfCustomProduct
    @skipIfCustomService
    @skipIfCustomInvoice
    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.xls.XLSExportEngine'])
    def test_export_invoice_xls01(self):
        user = self.login()
        payment_type = SettlementTerms.objects.create(name='23 days')
        order_number = 'PI31416'

        # source: siret / naf / rcs / tvaintra
        invoice, source, target = self.create_invoice_n_orgas(
            'My Invoice',
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
            # discount_unit=constants.DISCOUNT_PERCENT,
            discount_unit=Line.Discount.PERCENT,
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
            # discount_unit=constants.DISCOUNT_LINE_AMOUNT,
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
            # discount_unit=constants.DISCOUNT_ITEM_AMOUNT,
            discount_unit=Line.Discount.ITEM_AMOUNT,
        )

        existing_fileref_ids = [*FileRef.objects.values_list('id', flat=True)]

        response = self.assertGET200(self._build_export_url(invoice), follow=True)
        self.assertEqual('application/vnd.ms-excel', response['Content-Type'])

        filerefs = FileRef.objects.exclude(id__in=existing_fileref_ids)
        self.assertEqual(1, len(filerefs))

        fileref = filerefs[0]
        self.assertTrue(fileref.temporary)
        self.assertEqual(f"{_('Invoice')}_{invoice.id}.xls", fileref.basename)
        self.assertEqual(user, fileref.user)

        full_path = fileref.filedata.path
        self.assertTrue(exists(full_path), f'<{full_path}> does not exists?!')
        self.assertEqual(
            # join(settings.MEDIA_ROOT, 'upload', 'billing'),
            join(settings.MEDIA_ROOT, 'billing'),
            dirname(full_path),
        )

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
                pline1.on_the_fly_item,
                '1.00', '10.00',
                '0.00', '%',
                '10.00',
            ],
            next(lines)[:6],
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
        self.login()

        invoice, source, target = self.create_invoice_n_orgas(
            'My Invoice',
            discount=Decimal('6.3'),
            issuing_date='',
            expiration_date='',
        )

        invoice.generate_number()
        invoice.save()

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
    @skipIf(pdflatex_not_installed, '"pdflatex" is not installed.')
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.latex.LatexExportEngine'])
    def test_export_quote_latex(self):
        user = self.login()
        quote = self.create_quote_n_orgas('My Quote')[0]

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
        user = self.login()
        # payment_type = SettlementTerms.objects.create(name='23 days')

        quote, source, target = self.create_quote_n_orgas(
            'My Invoice',
            # discount=0, payment_type=payment_type.id,
            comment='Very important quote',
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

        filerefs = FileRef.objects.exclude(id__in=existing_fileref_ids)
        self.assertEqual(1, len(filerefs))
        self.assertEqual(f"{_('Quote')}_{quote.id}.xls", filerefs[0].basename)

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
                '0',  # No number
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
        user = self.login()
        quote = self.create_quote_n_orgas('My Quote')[0]

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
        user = self.login()
        quote = self.create_quote_n_orgas('My Quote')[0]

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
        user = self.login(
            is_superuser=False, allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice, Organisation],
        )

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK | EntityCredentials.UNLINK,
            set_type=SetCredentials.ESET_OWN,
        )

        invoice, source, target = self.create_invoice_n_orgas('My Invoice', discount=0)
        invoice.user = self.other_user
        invoice.save()

        self.assertFalse(user.has_perm_to_view(invoice))
        self.assertTrue(user.has_perm_to_view(source))
        self.assertTrue(user.has_perm_to_view(target))

        self.assertGET403(self._build_export_url(invoice))

    @skipIf(pdflatex_not_installed, '"pdflatex" is not installed.')
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.latex.LatexExportEngine'])
    @skipIfCustomInvoice
    def test_export_latex_credentials01(self):
        "Source credentials."
        user = self.login(
            is_superuser=False, allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice, Organisation],
        )

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK | EntityCredentials.UNLINK,
            set_type=SetCredentials.ESET_OWN,
        )

        invoice, source, target = self.create_invoice_n_orgas('My Invoice', discount=0)
        source.user = self.other_user
        source.save()

        self.assertTrue(user.has_perm_to_view(invoice))
        self.assertFalse(user.has_perm_to_view(source))
        self.assertTrue(user.has_perm_to_view(target))

        ExporterConfigItem.objects.filter(
            content_type=invoice.entity_type,
        ).update(engine_id=LatexExportEngine.id)
        self.assertGET403(self._build_export_url(invoice))

    @skipIf(pdflatex_not_installed, '"pdflatex" is not installed.')
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.latex.LatexExportEngine'])
    @skipIfCustomInvoice
    def test_export_latex_credentials02(self):
        "Target credentials."
        user = self.login(
            is_superuser=False, allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice, Organisation],
        )

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK | EntityCredentials.UNLINK,
            set_type=SetCredentials.ESET_OWN,
        )

        invoice, source, target = self.create_invoice_n_orgas('My Invoice', discount=0)
        target.user = self.other_user
        target.save()

        self.assertTrue(user.has_perm_to_view(invoice))
        self.assertTrue(user.has_perm_to_view(source))
        self.assertFalse(user.has_perm_to_view(target))

        ExporterConfigItem.objects.filter(
            content_type=invoice.entity_type,
        ).update(engine_id=LatexExportEngine.id)
        self.assertGET403(self._build_export_url(invoice))
