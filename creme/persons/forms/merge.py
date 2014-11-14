# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from itertools import chain

from django.utils.translation import ugettext as _

from creme.creme_core.forms.merge import MergeEntitiesBaseForm, mergefield_factory

from ..models import Address, Contact


_FIELD_NAMES = Address._INFO_FIELD_NAMES #TODO: use introspection to get editable fields ??
_BILL_PREFIX = 'billaddr_'
_SHIP_PREFIX = 'shipaddr_'


class _PersonMergeForm(MergeEntitiesBaseForm):
    def __init__(self, entity1, entity2, *args, **kwargs):
        if isinstance(entity1, Contact): #TODO: create a ContactMergeForm ?
            if entity2.is_user:
                if entity1.is_user:
                    raise self.CanNotMergeError(_('Can not merge 2 Contacts which represent some users.'))

                entity1, entity2 = entity2, entity1

        super(_PersonMergeForm, self).__init__(entity1, entity2, *args, **kwargs)

    def _build_initial_address_dict(self, address, initial, prefix):
        getter = (lambda fname: '') if address is None else \
                    lambda fname: getattr(address, fname)

        for fname in _FIELD_NAMES:
            initial[prefix + fname] = getter(fname)

    def _build_initial_dict(self, entity):
        initial = super(_PersonMergeForm, self)._build_initial_dict(entity)

        build = self._build_initial_address_dict
        build(entity.billing_address,  initial, _BILL_PREFIX)
        build(entity.shipping_address, initial, _SHIP_PREFIX)

        return initial

    def _save_address(self, entity1, entity2, attr_name, cleaned_data, prefix):
        address = getattr(entity1, attr_name)
        was_none = False

        if address is None:
            address = getattr(entity2, attr_name) or Address()
            address.owner = entity1
            was_none = True

        for fname in _FIELD_NAMES:
            setattr(address, fname, cleaned_data[prefix + fname])

        if address:
            address.save()
            setattr(entity1, attr_name, address)
            return was_none, ()

        if not was_none:
            setattr(entity1, attr_name, None)
            return True, [address] if address.pk else ()

        return True, ()

    def _post_entity1_update(self, entity1, entity2, cleaned_data):
        super(_PersonMergeForm, self)._post_entity1_update(entity1, entity2, cleaned_data)
        save_address = self._save_address

        must_save1, to_del1 = save_address(entity1, entity2, 'billing_address',  cleaned_data, _BILL_PREFIX)
        must_save2, to_del2 = save_address(entity1, entity2, 'shipping_address', cleaned_data, _SHIP_PREFIX)

        if must_save1 or must_save2:
            entity1.save()

        for address in chain(to_del1, to_del2):
            address.delete()

#TODO: can we build the form once instead of build it each time ??
#TODO: factorise with csv_import.py ?
def get_merge_form_builder():
    get_field_by_name = Address._meta.get_field_by_name
    attrs = {}
    billing_address_fnames = []
    shipping_address_fnames = []

    for field_name in _FIELD_NAMES:
        field = get_field_by_name(field_name)[0]

        form_fieldname = _BILL_PREFIX + field_name
        attrs[form_fieldname] = mergefield_factory(field)
        billing_address_fnames.append(form_fieldname)

        form_fieldname = _SHIP_PREFIX + field_name
        attrs[form_fieldname] = mergefield_factory(field)
        shipping_address_fnames.append(form_fieldname)

    attrs['blocks'] = MergeEntitiesBaseForm.blocks.new(
                            ('billing_address',  _(u'Billing address'),  billing_address_fnames),
                            ('shipping_address', _(u'Shipping address'), shipping_address_fnames),
                        )

    return type('PersonMergeForm', (_PersonMergeForm,), attrs)
