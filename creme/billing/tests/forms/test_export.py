from json import dumps as json_dump

from django.utils.translation import gettext as _

from creme.billing.exporters import BillingExportEngineManager
from creme.billing.forms.export import ExporterLocalisationField

from ..base import Invoice, _BillingTestCase


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
            'creme.billing.tests.fake_exporters.only_invoice.OnlyInvoiceExportEngine'
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
            'creme.billing.tests.fake_exporters.only_invoice.OnlyInvoiceExportEngine',
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
            'creme.billing.tests.fake_exporters.only_invoice.OnlyInvoiceExportEngine',
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
            'creme.billing.tests.fake_exporters.only_invoice.OnlyInvoiceExportEngine',
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
