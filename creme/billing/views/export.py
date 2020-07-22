# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from creme import billing
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import FileRef
from creme.creme_core.views.generic import CremeModelEditionWizardPopup, base

from ..exporters import BillingExportEngineManager
from ..forms import export as export_forms
from ..models import ExporterConfigItem

logger = logging.getLogger(__name__)
# TEMPLATE_PATHS = {
#     billing.get_invoice_model():       'billing/templates/invoice.tex',
#     billing.get_credit_note_model():   'billing/templates/billings.tex',
#     billing.get_quote_model():         'billing/templates/billings.tex',
#     billing.get_sales_order_model():   'billing/templates/billings.tex',
#     billing.get_template_base_model(): 'billing/templates/billings.tex',
# }


class ExporterConfigEditionWizard(base.EntityCTypeRelatedMixin,
                                  CremeModelEditionWizardPopup):
    model = ExporterConfigItem
    permissions = 'billing.can_admin'

    slug_field = 'content_type'
    slug_url_kwarg = 'ct_id'

    form_list = [
        export_forms.ExporterLocalisationStep,
        export_forms.ExporterThemeStep,
    ]

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step=step)
        kwargs['engine_manager'] = BillingExportEngineManager()
        kwargs['model'] = self.get_ctype().model_class()

        if step == '1':
            kwargs['localisation'] = self.get_cleaned_data_for_step('0')['localisation']

        return kwargs


# @auth_dec.login_required
# @auth_dec.permission_required('billing')
# def export_as_pdf(request, base_id):
#     entity = get_object_or_404(CremeEntity, pk=base_id).get_real_entity()
#
#     has_perm = request.user.has_perm_to_view_or_die
#     has_perm(entity)
#
#     template_path = TEMPLATE_PATHS.get(entity.__class__)
#     if template_path is None:
#         raise ConflictError('This type of entity cannot be exported as pdf')
#
#     source = entity.get_source().get_real_entity()
#     has_perm(source)
#
#     target = entity.get_target().get_real_entity()
#     has_perm(target)
#
#     document_name = str(entity._meta.verbose_name)
#
#     template = loader.get_template(template_path)
#     context = {
#         'plines':        entity.get_lines(billing.get_product_line_model()),
#         'slines':        entity.get_lines(billing.get_service_line_model()),
#         'source':        source,
#         'target':        target,
#         'object':        entity,
#         'document_name': document_name,
#     }
#
#     basename = secure_filename('{}_{}'.format(document_name, entity.id))
#     tmp_dir_path = mkdtemp(prefix='creme_billing_latex')
#     latex_file_path = path.join(tmp_dir_path, '{}.tex'.format(basename))
#
#     # NB: we precise the encoding or it oddly crashes on some systems...
#     with open(latex_file_path, 'w', encoding='utf-8') as f:
#         f.write(smart_str(template.render(context)))
#
#     # NB: return code seems always 1 even when there is no error...
#     subprocess.call(['pdflatex',
#                      '-interaction=batchmode',
#                      '-output-directory', tmp_dir_path,
#                      latex_file_path,
#                     ]
#                    )
#
#     pdf_basename = '{}.pdf'.format(basename)
#     temp_pdf_file_path = path.join(tmp_dir_path, pdf_basename)
#
#     if not path.exists(temp_pdf_file_path):
#         logger.critical('It seems the PDF generation has failed. '
#                         'The temporary directory has not been removed, '
#                         'so you can inspect the *.log file in "%s"', tmp_dir_path
#                        )
#         raise ConflictError(
#             _('The generation of the PDF file has failed ; please contact your administrator.')
#         )
#
#     final_path = FileCreator(dir_path=path.join(settings.MEDIA_ROOT, 'upload', 'billing'),
#                              name=pdf_basename,
#                             ).create()
#     copy(temp_pdf_file_path, final_path)
#
#     rmtree(tmp_dir_path)
#
#     fileref = FileRef.objects.create(# user=request.user,
#                                      filedata='upload/billing/' + path.basename(final_path),
#                                      basename=pdf_basename,
#                                     )
#
#     return HttpResponseRedirect(reverse('creme_core__dl_file',
#                                         args=(fileref.filedata,),
#                                        )
#                                )
class Export(base.EntityRelatedMixin, base.CheckedView):
    permissions = 'billing'
    entity_classes = [
        billing.get_invoice_model(),
        billing.get_credit_note_model(),
        billing.get_quote_model(),
        billing.get_sales_order_model(),
        billing.get_template_base_model(),
    ]

    def check_related_entity_permissions(self, entity, user):
        has_perm = user.has_perm_to_view_or_die
        has_perm(entity)
        has_perm(entity.source)
        has_perm(entity.target)

    def get(self, request, *args, **kwargs):
        entity = self.get_related_entity()
        config_item = get_object_or_404(
            ExporterConfigItem,
            content_type=entity.entity_type,
        )

        engine_id = config_item.engine_id
        if not engine_id:
            raise ConflictError(_(
                'The engine is not configured ; '
                'go to the configuration of the app «Billing».'
            ))

        exporter = BillingExportEngineManager().exporter(
            engine_id=engine_id,
            flavour_id=config_item.flavour_id,
            model=type(entity),
        )

        if exporter is None:
            raise ConflictError(_(
                'The configured exporter is invalid ; '
                'go to the configuration of the app «Billing».'
            ))

        export_result = exporter.export(
            entity=entity, user=request.user,
        )

        if isinstance(export_result, HttpResponse):
            return export_result

        assert export_result, FileRef

        return HttpResponseRedirect(export_result.get_download_absolute_url())
