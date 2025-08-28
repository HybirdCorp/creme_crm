################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2025  Hybird
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

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.urls.base import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme import billing
from creme.billing.core.number_generation import number_generator_registry
from creme.billing.models import NumberGeneratorItem
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui import actions

Invoice = billing.get_invoice_model()
Quote   = billing.get_quote_model()


class _ExportAction(actions.UIAction):
    type = 'redirect'

    label = _('Download')
    icon = 'download'
    help_text = _('Download as PDF')

    @property
    def url(self):
        return reverse('billing__export', args=(self.instance.id,))

    @property
    def is_enabled(self):
        return self.user.has_perm_to_view(self.instance)


class ExportInvoiceAction(_ExportAction):
    id = _ExportAction.generate_id('billing', 'export_invoice')
    model = Invoice


class ExportQuoteAction(_ExportAction):
    id = _ExportAction.generate_id('billing', 'export_quote')
    model = Quote


# ------------------------------------------------------------------------------
class _BulkExportAction(actions.BulkEntityAction):
    # id = actions.BulkEntityAction.generate_id('billing', ...)
    # model = ...

    # TODO: improve action system (<type = 'redirect'> ?)
    type = 'billing-bulk-export'
    url_name = 'billing__bulk_export'

    label = _('Download as zipped PDF')
    icon = 'download'

    bulk_max_count = settings.BILLING_BULK_EXPORT_LIMIT

    @property
    def url(self):
        return reverse(
            self.url_name,
            args=(ContentType.objects.get_for_model(self.model).id,),
        )


class BulkExportInvoiceAction(_BulkExportAction):
    id = _BulkExportAction.generate_id('billing', 'export_invoice')
    model = Invoice


class BulkExportQuoteAction(_BulkExportAction):
    id = _BulkExportAction.generate_id('billing', 'export_quote')
    model = Quote


# ------------------------------------------------------------------------------
class _GenerateNumberAction(actions.UIAction):
    # id = UIAction.generate_id('billing', ....)
    type = 'billing-number'
    # model = ...

    label = _('Generate the number')
    icon = 'invoice'

    generator_registry = number_generator_registry

    @property
    def url(self):
        return reverse('billing__generate_number', args=(self.instance.id,))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        entity = self.instance
        # NB: entity.source is prefetched by the listviews (see views.base.BaseList)
        item = NumberGeneratorItem.objects.get_for_instance(entity)
        if item is None:
            self.is_enabled = False
            self.help_text = _(
                'This entity cannot generate a number (see configuration of the app Billing)'
            )
        else:
            try:
                self.generator_registry[item].check_permissions(
                    user=self.user, entity=entity,
                )
            except (PermissionDenied, ConflictError) as e:
                self.is_enabled = False
                self.help_text = e.args[0]

    def _get_options(self):
        return {
            'confirm': gettext('Do you really want to generate a number?'),
        }


class GenerateInvoiceNumberAction(_GenerateNumberAction):
    id = _GenerateNumberAction.generate_id('billing', 'invoice_number')
    model = Invoice


class GenerateCreditNoteNumberAction(_GenerateNumberAction):
    id = _GenerateNumberAction.generate_id('billing', 'creditnote_number')
    model = billing.get_credit_note_model()
