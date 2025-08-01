################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
#    Copyright (C) 2025 Patrick Baus <patrick.baus@quantum-electronic-devices.de>
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
import subprocess
from os import path
from shutil import copy, rmtree
from tempfile import mkdtemp

from django.conf import settings
from django.template import loader
from django.utils.encoding import smart_str
from django.utils.translation import gettext as _
from django.utils.translation import override
from django.views.generic.base import ContextMixin

from creme import billing
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import FileRef
from creme.creme_core.utils import l10n
from creme.creme_core.utils.file_handling import FileCreator
from creme.creme_core.utils.secure_filename import secure_filename

from . import base

logger = logging.getLogger(__name__)


class LatexExporter(ContextMixin, base.BillingExporter):
    def __init__(self, *, template_path, screenshots, **kwargs):
        super().__init__(**kwargs)
        self.template_path = template_path
        self._screenshots = [*screenshots]

    def generate_pdf(self, *, content, dir_path, basename):
        latex_file_path = path.join(dir_path, f'{basename}.tex')
        log_file_path   = path.join(dir_path, f'{basename}.main.log')

        # NB: we specify the encoding, or it oddly crashes on some systems...
        with open(latex_file_path, 'w', encoding='utf-8') as f:
            f.write(smart_str(content))

        # NB: return code seems always 1 even when there is no error...
        with open(log_file_path, 'wb') as log_file:
            subprocess.call(
                [
                    'latexmk',
                    '-lualatex',
                    '-cd',  # TODO: <f'-output-directory={dir_path}'> ?
                    latex_file_path,
                ],
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )

        pdf_basename = f'{basename}.pdf'
        temp_pdf_file_path = path.join(dir_path, pdf_basename)

        if not path.exists(temp_pdf_file_path):
            logger.critical(
                'It seems the PDF generation has failed. '
                'The temporary directory has not been removed, '
                'so you can inspect the log file "%s"',
                log_file.name,
            )
            if settings.TESTS_ON:
                print('latexmk errors ##########')
                with open(log_file_path, 'r') as log_file:
                    for line in log_file.readlines():
                        print(line)
                print('latexmk errors [end] ##########')

            # TODO: use a better exception class ?
            raise ConflictError(_(
                'The generation of the PDF file has failed; '
                'please contact your administrator.'
            ))

        final_path = FileCreator(
            dir_path=path.join(settings.MEDIA_ROOT, 'billing'),
            name=pdf_basename,
        ).create()
        copy(temp_pdf_file_path, final_path)

        return final_path, pdf_basename

    def export(self, entity, user):
        template = loader.get_template(self.template_path)
        context = self.get_context_data(object=entity)
        tmp_dir_path = mkdtemp(prefix='creme_billing_latex')

        with override(language=self.flavour.language):
            content = template.render(context)

        final_path, pdf_basename = self.generate_pdf(
            content=content,
            dir_path=tmp_dir_path,
            basename=secure_filename(f'{entity._meta.verbose_name}_{entity.id}'),
        )

        # TODO: context manager which can avoid file cleaning on exception ?
        rmtree(tmp_dir_path)

        return FileRef.objects.create(
            user=user,
            filedata='billing/' + path.basename(final_path),
            basename=pdf_basename,
            description=_('Latex export for «{}»').format(entity),
        )

    @property
    def screenshots(self):
        yield from self._screenshots


class LatexTheme:
    def __init__(self, *, verbose_name, templates, screenshots):
        self.verbose_name = verbose_name
        self.templates = templates
        self.screenshots = screenshots


class LatexExportEngine(base.BillingExportEngine):
    id = base.BillingExportEngine.generate_id('billing', 'latex')

    FLAVOURS_INFO = {
        l10n.FR: {
            'fr_FR': {
                # Ubuntu packages needed to render correctly this theme
                #  - texlive-latex-recommended
                #  - texlive-fonts-extra
                #  - texlive-lang-french
                #  - texlive-latex-extra
                'clear': LatexTheme(
                    verbose_name='.pdf - LateX - Thème clair (France)',
                    templates={
                        billing.get_invoice_model():
                            'billing/export/latex/FR/fr_FR/clear/invoice.tex',
                        billing.get_credit_note_model():
                            'billing/export/latex/FR/fr_FR/clear/credit_note.tex',
                        billing.get_quote_model():
                            'billing/export/latex/FR/fr_FR/clear/quote.tex',
                        billing.get_sales_order_model():
                            'billing/export/latex/FR/fr_FR/clear/sales_order.tex',
                        billing.get_template_base_model():
                            'billing/export/latex/FR/fr_FR/clear/template.tex',
                    },
                    # TODO: by ContentType ?
                    screenshots=['billing/sample_latex.png'],
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
            logger.warning('LatexExportEngine.exporter(): invalid data [%s].', e)
            return None

        return LatexExporter(
            verbose_name=theme.verbose_name,
            engine=self,
            flavour=flavour,
            template_path=template_path,
            screenshots=theme.screenshots,
        )
