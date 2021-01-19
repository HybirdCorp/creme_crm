# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
