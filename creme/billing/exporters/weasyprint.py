# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020-2021  Hybird
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
from os import path

from django.conf import settings
from django.template.loader import get_template
from django.utils.translation import override
from django.views.generic.base import ContextMixin
from weasyprint import CSS, HTML

from creme import billing
from creme.creme_core.models import FileRef
from creme.creme_core.utils import l10n
from creme.creme_core.utils.file_handling import FileCreator
from creme.creme_core.utils.secure_filename import secure_filename

from . import base

logger = logging.getLogger(__name__)


class WeasyprintExporter(ContextMixin, base.BillingExporter):
    def __init__(self, *, html_template_path, css_template_path, screenshots, **kwargs):
        super().__init__(**kwargs)
        self.html_template_path = html_template_path
        self.css_template_path = css_template_path
        self._screenshots = [*screenshots]

    def export(self, entity, user):
        html_template = get_template(self.html_template_path)
        css_template = get_template(self.css_template_path)
        context = self.get_context_data(object=entity)

        with override(language=self.flavour.language):
            html_content = html_template.render(context)
            css_content = css_template.render(context)

        # NB: before creating file to raise error as soon a possible
        #     & avoid junk files.
        html = HTML(string=html_content)
        css = CSS(string=css_content)

        basename = secure_filename(f'{entity._meta.verbose_name}_{entity.id}.pdf')
        final_path = FileCreator(
            # dir_path=path.join(settings.MEDIA_ROOT, 'upload', 'billing'),
            dir_path=path.join(settings.MEDIA_ROOT, 'billing'),
            name=basename,
        ).create()

        # NB: we create the FileRef instance as soon as possible to get the
        #     smallest duration when a crash causes a file which have to be
        #     removed by hand (not cleaned by the Cleaner job).
        file_ref = FileRef.objects.create(
            user=user,
            # filedata=f'upload/billing/{path.basename(final_path)}',
            filedata=f'billing/{path.basename(final_path)}',
            basename=basename,
        )

        # TODO ?
        # from weasyprint.fonts import FontConfiguration
        # font_config = FontConfiguration()
        html.write_pdf(
            final_path,
            stylesheets=[css],
            # TODO: ???
            # font_config=font_config
        )

        return file_ref

    @property
    def screenshots(self):
        yield from self._screenshots


# TODO: factorise with LatexTheme ?
class WeasyprintTheme:
    def __init__(self, *, verbose_name, templates, css, screenshots):
        self.verbose_name = verbose_name
        self.templates = templates
        self.css = css
        self.screenshots = screenshots


class WeasyprintExportEngine(base.BillingExportEngine):
    id = base.BillingExportEngine.generate_id('billing', 'weasyprint')

    FLAVOURS_INFO = {
        l10n.FR: {
            'fr_FR': {
                'mint': WeasyprintTheme(
                    verbose_name='.pdf - WeasyPrint - Thème Menthe (France)',
                    # TODO: attribute "directory" ?
                    templates={
                        billing.get_invoice_model():
                            'billing/export/weasyprint/FR/fr_FR/mint/invoice.html',
                        billing.get_credit_note_model():
                            'billing/export/weasyprint/FR/fr_FR/mint/credit_note.html',
                        billing.get_quote_model():
                            'billing/export/weasyprint/FR/fr_FR/mint/quote.html',
                        billing.get_sales_order_model():
                            'billing/export/weasyprint/FR/fr_FR/mint/sales_order.html',
                        billing.get_template_base_model():
                            'billing/export/weasyprint/FR/fr_FR/mint/template.html',
                    },
                    css='billing/export/weasyprint/FR/fr_FR/mint/mint.css',
                    # TODO: by ContentType ?
                    screenshots=['billing/sample_weasyprint.png'],
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
        # TODO: factorise with LateX ?
        try:
            theme = self.FLAVOURS_INFO[flavour.country][flavour.language][flavour.theme]
            template_path = theme.templates[self.model]
        except KeyError as e:
            logger.warning('WeasyprintExportEngine.exporter(): invalid data [%s].', e)
            return None

        return WeasyprintExporter(
            verbose_name=theme.verbose_name,
            engine=self,
            flavour=flavour,
            html_template_path=template_path,
            css_template_path=theme.css,
            screenshots=theme.screenshots,
        )
