################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020-2025  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

import logging

from django.http import HttpResponse
from django.template.loader import get_template
from django.utils.translation import gettext as _
from django.utils.translation import override
from django.views.generic.base import ContextMixin
from xhtml2pdf import pisa

from creme import billing
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.utils import l10n

from . import base

logger = logging.getLogger(__name__)


class Xhtml2pdfExporter(ContextMixin, base.BillingExporter):
    def __init__(self, *, template_path, screenshots, **kwargs):
        super().__init__(**kwargs)
        self.template_path = template_path
        self._screenshots = [*screenshots]

    def export(self, entity, user):
        template = get_template(self.template_path)

        with override(language=self.flavour.language):
            html = template.render(self.get_context_data(object=entity))

        response = HttpResponse(headers={
            'Content-Type': 'application/pdf',
            'Content-Disposition': (
                f'attachment; filename="{entity._meta.verbose_name}_{entity.id}.pdf"'
            ),
        })

        pisa_status = pisa.CreatePDF(
            html, dest=response,
            # TODO ? see https://xhtml2pdf.readthedocs.io/en/latest/usage.html#using-xhtml2pdf-in-django  # NOQA
            # link_callback=link_callback,
        )

        if pisa_status.err:
            # TODO: test ; use pisa_status.log ?
            raise ConflictError(
                _('An error happened while generating the PDF file.')
            )

        return response

    @property
    def screenshots(self):
        yield from self._screenshots


# TODO: factorise with LatexTheme ?
class Xhtml2pdfTheme:
    def __init__(self, *, verbose_name, templates, screenshots):
        self.verbose_name = verbose_name
        # self.description = description  # TODO ?
        self.templates = templates
        self.screenshots = screenshots


# TODO: factorise with LateX/WeasyPrint ?
class Xhtml2pdfExportEngine(base.BillingExportEngine):
    id = base.BillingExportEngine.generate_id('billing', 'xhtml2pdf')

    FLAVOURS_INFO = {
        l10n.FR: {
            'fr_FR': {
                'cappuccino': Xhtml2pdfTheme(
                    verbose_name='.pdf - Xhtml2pdf - Thème Cappuccino (France)',
                    # description='...',  # TODO ?
                    # TODO: attribute "directory" ?
                    templates={
                        billing.get_invoice_model():
                            'billing/export/xhtml2pdf/FR/fr_FR/cappuccino/invoice.html',
                        billing.get_credit_note_model():
                            'billing/export/xhtml2pdf/FR/fr_FR/cappuccino/credit_note.html',
                        billing.get_quote_model():
                            'billing/export/xhtml2pdf/FR/fr_FR/cappuccino/quote.html',
                        billing.get_sales_order_model():
                            'billing/export/xhtml2pdf/FR/fr_FR/cappuccino/sales_order.html',
                        billing.get_template_base_model():
                            'billing/export/xhtml2pdf/FR/fr_FR/cappuccino/template.html',
                    },
                    # TODO: by ContentType ?
                    screenshots=['billing/sample_xhtml2pdf.png'],
                ),
            },
        },
    }

    @property
    def flavours(self):
        model = self.model

        for country, languages in self.FLAVOURS_INFO.items():
            for language, themes in languages.items():
                for theme_id, theme_info in themes.items():
                    if model in theme_info.templates:
                        yield base.ExporterFlavour(country, language, theme_id)

    def exporter(self, flavour):
        try:
            theme = self.FLAVOURS_INFO[flavour.country][flavour.language][flavour.theme]
            template_path = theme.templates[self.model]
        except KeyError as e:
            logger.warning('Xhtml2pdfExportEngine.exporter(): invalid data [%s].', e)
            return None

        return Xhtml2pdfExporter(
            verbose_name=theme.verbose_name,
            engine=self,
            flavour=flavour,
            template_path=template_path,
            screenshots=theme.screenshots,
        )
