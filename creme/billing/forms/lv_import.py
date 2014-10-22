 # -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2014  Hybird
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

from django.utils.translation import ugettext as _

from creme.creme_core.forms.list_view_import import ImportForm4CremeEntity, EntityExtractorField
from creme.creme_core.models import Relation

from creme.persons.models import Contact, Organisation

from ..constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
from .base import copy_or_create_address


def get_import_form_builder(header_dict, choices):
    class InvoiceLVImportForm(ImportForm4CremeEntity):
        source = EntityExtractorField([(Organisation, 'name')], choices, label=_('Source organisation'))
        target = EntityExtractorField([(Organisation, 'name'), (Contact, 'last_name')],
                                      choices, label=_('Target')
                                     )

        #class Meta:
            #exclude = ('billing_address', 'shipping_address')

        def _post_instance_creation(self, instance, line):
            super(InvoiceLVImportForm, self)._post_instance_creation(instance, line)
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
            create_rel(type_id=REL_SUB_BILL_ISSUED,   object_entity=source)
            create_rel(type_id=REL_SUB_BILL_RECEIVED, object_entity=target)

            instance.billing_address  = copy_or_create_address(target.billing_address,  instance, _(u'Billing address'))
            instance.shipping_address = copy_or_create_address(target.shipping_address, instance, _(u'Shipping address'))
            instance.save()


    return InvoiceLVImportForm
