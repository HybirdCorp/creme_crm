# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2021  Hybird
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

from django.forms.fields import BooleanField
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme import persons
from creme.creme_core.forms.mass_import import (
    EntityExtractorField,
    ImportForm4CremeEntity,
)
from creme.creme_core.utils import update_model_instance

from ..utils import copy_or_create_address

Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()


def _copy_or_update_address(source, dest, attr_name, addr_name):
    change = True

    source_addr = getattr(source, attr_name, None)
    dest_addr   = getattr(dest,   attr_name, None)

    if dest_addr is None:  # Should not happen
        setattr(dest, attr_name, copy_or_create_address(source_addr, source, addr_name))
    elif source_addr is None:
        # Should we empty the fields of the Address ?
        pass
    else:
        change = update_model_instance(dest_addr, **dict(source_addr.info_fields))

    return change


def get_import_form_builder(header_dict, choices):
    class InvoiceMassImportForm(ImportForm4CremeEntity):
        source = EntityExtractorField(
            models_info=[(Organisation, 'name')],
            choices=choices,
            label=pgettext_lazy('billing', 'Source organisation'),
        )
        target = EntityExtractorField(
            models_info=[
                (Organisation, 'name'),
                (Contact, 'last_name'),
            ],
            choices=choices, label=pgettext_lazy('billing', 'Target'),
        )

        override_billing_addr = BooleanField(
            label=_('Update the billing address'), required=False,
            help_text=_('In update mode, update the billing address from the target.'),
        )
        override_shipping_addr = BooleanField(
            label=_('Update the shipping address'), required=False,
            help_text=_('In update mode, update the shipping address from the target.'),
        )

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            model = self._meta.model
            if model.generate_number_in_create:
                self.fields['number'].help_text = _(
                    'If you chose an organisation managed by Creme as source organisation, '
                    'a number will be automatically generated for created «{}».'
                ).format(model._meta.verbose_name_plural)

        def _pre_instance_save(self, instance, line):
            cdata = self.cleaned_data
            append_error = self.append_error
            user = self.user

            for prop_name in ('source', 'target'):
                entity, err_msg = cdata[prop_name].extract_value(line, user)
                setattr(instance, prop_name, entity)

                # Error is really appended if 'err_msg' is not empty
                append_error(err_msg)

        def _post_instance_creation(self, instance, line, updated):
            super()._post_instance_creation(instance, line, updated)

            if updated:
                cdata = self.cleaned_data
                target = instance.target
                b_change = s_change = False

                if cdata['override_billing_addr']:
                    b_change = _copy_or_update_address(
                        target, instance, 'billing_address', _('Billing address'),
                    )

                if cdata['override_shipping_addr']:
                    s_change = _copy_or_update_address(
                        target, instance, 'shipping_address', _('Shipping address'),
                    )

                if b_change or s_change:
                    instance.save()

    return InvoiceMassImportForm
