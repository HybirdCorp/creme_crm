################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
import re
from os import path
from os import remove as delete_file
from zipfile import ZipFile

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from creme import billing
from creme.creme_core.auth import EntityCredentials
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import FileRef
from creme.creme_core.utils.file_handling import FileCreator
from creme.creme_core.utils.secure_filename import secure_filename
from creme.creme_core.utils.translation import smart_model_verbose_name
from creme.creme_core.views.generic import CremeModelEditionWizardPopup, base

from ..exporters import BillingExportEngineManager
from ..forms import export as export_forms
from ..models import ExporterConfigItem

logger = logging.getLogger(__name__)


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


class ExporterMixin:
    def get_exporter(self, entity_ctype):
        config_item = get_object_or_404(
            ExporterConfigItem, content_type=entity_ctype,
        )

        engine_id = config_item.engine_id
        if not engine_id:
            raise ConflictError(_(
                'The engine is not configured; '
                'go to the configuration of the app «Billing».'
            ))

        exporter = BillingExportEngineManager().exporter(
            engine_id=engine_id,
            flavour_id=config_item.flavour_id,
            model=entity_ctype.model_class(),
        )
        if exporter is None:
            raise ConflictError(_(
                'The configured exporter is invalid; '
                'go to the configuration of the app «Billing».'
            ))

        return exporter


class Export(base.EntityRelatedMixin, ExporterMixin, base.CheckedView):
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
        exporter = self.get_exporter(entity_ctype=entity.entity_type)
        export_result = exporter.export(entity=entity, user=request.user)

        if isinstance(export_result, HttpResponse):
            return export_result

        assert isinstance(export_result, FileRef)
        return HttpResponseRedirect(export_result.get_download_absolute_url())


class BulkExport(base.EntityCTypeRelatedMixin, ExporterMixin, base.CheckedView):
    permissions = 'billing'
    allowed_models = [
        billing.get_invoice_model(),
        billing.get_credit_note_model(),
        billing.get_quote_model(),
        billing.get_sales_order_model(),
        billing.get_template_base_model(),
    ]

    def get_ids(self, request):
        raw_ids = request.GET.getlist('id')
        if not raw_ids:
            raise ConflictError('The list of IDs is empty')
        if len(raw_ids) > settings.BILLING_BULK_EXPORT_LIMIT:
            raise ConflictError(
                f'The length of the ID list cannot be greater than '
                f'{settings.BILLING_BULK_EXPORT_LIMIT}'
            )
        try:
            cleaned_ids = {int(i) for i in raw_ids}
        except ValueError as e:
            raise ConflictError('Some IDs are invalid: {e}') from e

        return cleaned_ids

    def get(self, request, *args, **kwargs):
        ids = self.get_ids(request)
        ctype = self.get_ctype()
        model = ctype.model_class()
        user = request.user

        entities = EntityCredentials.filter(
            user=user, queryset=model.objects.filter(id__in=ids),
        )
        if len(entities) != len(ids):
            raise PermissionDenied(_('Some entities are invalid or not viewable'))

        exporter = self.get_exporter(entity_ctype=ctype)

        count = len(entities)
        # TODO: add date in the file name?
        basename = secure_filename(f'{model._meta.verbose_name_plural}_X{count}.zip')
        final_path = FileCreator(
            dir_path=path.join(settings.MEDIA_ROOT, 'billing'),
            name=basename,
        ).create()

        # NB: we create the FileRef instance as soon as possible to get the
        #     smallest duration when a crash causes a file which have to be
        #     removed by hand (not cleaned by the Cleaner job).
        file_ref = FileRef.objects.create(
            user=user,
            filedata=f'billing/{path.basename(final_path)}',
            basename=basename,
            description=_('Bulk export of {count} {model}').format(
                count=count,
                model=smart_model_verbose_name(model=model, count=count),
            ),
        )
        tmp_file_refs = []
        disp_re = re.compile('attachment; filename="(?P<name>.+)"')

        with ZipFile(final_path, 'w') as archive:
            for entity in entities:
                export_result = exporter.export(entity=entity, user=user)

                if isinstance(export_result, HttpResponse):
                    file_name_match = disp_re.match(export_result.get('Content-Disposition', ''))
                    if file_name_match is None:
                        logger.critical('The export backend response has no Content-Disposition')
                        archive_name = f'{entity._meta.verbose_name}_{entity.id}'
                    else:
                        archive_name = file_name_match['name']

                    archive.writestr(archive_name, data=export_result.content)
                else:
                    assert isinstance(export_result, FileRef)

                    archive.write(
                        filename=export_result.filedata.path,
                        arcname=export_result.basename,
                    )
                    tmp_file_refs.append(export_result)

        for tmp_file_ref in tmp_file_refs:
            # TODO: test file deletion
            full_path = tmp_file_ref.filedata.path
            if path.exists(full_path):
                try:
                    delete_file(full_path)
                except Exception as e:
                    logger.warning('Cannot find the temporary file %s (%s)', full_path, e)

            tmp_file_ref.delete()

        return HttpResponseRedirect(file_ref.get_download_absolute_url())
