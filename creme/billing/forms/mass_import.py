# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2016  Hybird
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

from functools import partial

from django.forms.fields import BooleanField
from django.utils.translation import ugettext as _

from creme.creme_core.forms.mass_import import ImportForm4CremeEntity, EntityExtractorField
from creme.creme_core.models import Relation
from creme.creme_core.utils import find_first, update_model_instance

from creme.persons import get_contact_model, get_organisation_model

from ..constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
from .base import copy_or_create_address


Contact      = get_contact_model()
Organisation = get_organisation_model()


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
        source = EntityExtractorField([(Organisation, 'name')], choices, label=_('Source organisation'))
        target = EntityExtractorField([(Organisation, 'name'), (Contact, 'last_name')],
                                      choices, label=_('Target'),
                                     )

        override_billing_addr  = BooleanField(label=_('Update the billing address'), required=False,
                                              help_text=_('In update mode, update the billing address from the target.')
                                             )
        override_shipping_addr = BooleanField(label=_('Update the shipping address'), required=False,
                                              help_text=_('In update mode, update the shipping address from the target.')
                                             )

        def _post_instance_creation(self, instance, line, updated):
            super(InvoiceMassImportForm, self)._post_instance_creation(instance, line, updated)
            cdata = self.cleaned_data
            user = self.user

            append_error = self.append_error
            source, err_msg = cdata['source'].extract_value(line, user)
            append_error(line, err_msg, instance)

            target, err_msg  = cdata['target'].extract_value(line, user)
            append_error(line, err_msg, instance)
 
            create_rel = partial(Relation.objects.create, subject_entity=instance,
                                 user=instance.user,
                                )

            # TODO: move this intelligence in models.Base.save() (see regular Forms)
            if not updated:
                create_rel(type_id=REL_SUB_BILL_ISSUED,   object_entity=source)
                create_rel(type_id=REL_SUB_BILL_RECEIVED, object_entity=target)

                instance.billing_address  = copy_or_create_address(target.billing_address,  instance, _(u'Billing address'))
                instance.shipping_address = copy_or_create_address(target.shipping_address, instance, _(u'Shipping address'))
                instance.save()
            else:  # Update mode
                relations = Relation.objects.filter(subject_entity=instance.pk,
                                                    type__in=(REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED)
                                                   )

                issued_relation   = find_first(relations, (lambda r: r.type_id == REL_SUB_BILL_ISSUED), None)
                received_relation = find_first(relations, (lambda r: r.type_id == REL_SUB_BILL_RECEIVED), None)

                assert issued_relation is not None
                assert received_relation is not None

                if issued_relation.object_entity_id != source:
                    issued_relation.delete()
                    create_rel(type_id=REL_SUB_BILL_ISSUED, object_entity=source)

                if received_relation.object_entity_id != target:
                    received_relation.delete()
                    create_rel(type_id=REL_SUB_BILL_RECEIVED, object_entity=target)

                b_change = s_change = False

                if cdata['override_billing_addr']:
                    b_change = _copy_or_update_address(
                            target, instance, 'billing_address', _(u'Billing address'),
                        )

                if cdata['override_shipping_addr']:
                    s_change = _copy_or_update_address(
                            target, instance, 'shipping_address', _(u'Shipping address'),
                        )

                if b_change or s_change:
                    instance.save()

    return InvoiceMassImportForm
