from json import dumps as json_dump
from unittest import skipIf

from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.urls import reverse

from creme.billing.bricks import BillingExportersBrick
from creme.billing.models import ExporterConfigItem
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from ..base import Invoice, _BillingTestCase

try:
    import xhtml2pdf  # NOQA
except ImportError:
    xhtml2pdf_not_installed = True
else:
    xhtml2pdf_not_installed = False
    from creme.billing.exporters.xhtml2pdf import Xhtml2pdfExportEngine


class ExporterConfigItemTestCase(BrickTestCaseMixin, _BillingTestCase):
    @staticmethod
    def _build_conf_url(ctype):
        return reverse('billing__edit_exporter_config', args=(ctype.id,))

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
    def test_configuration_edition(self):
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
    def test_configuration_edition__initial_values(self):
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
    def test_configuration_edition__invalid_initial__flavour(self):
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
    def test_configuration_edition__invalid_initial__engine(self):
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
