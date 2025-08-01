################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2025  Hybird
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

from io import StringIO

from django import template
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import FieldsConfig
from creme.persons import get_organisation_model
from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES

register = template.Library()


# TODO: a code per country ?
@register.filter
def persons_pretty_address(address):
    is_field_hidden = FieldsConfig.objects.get_for_model(address.__class__).is_fieldname_hidden

    with StringIO() as sio:
        write = sio.write

        addr = '' if is_field_hidden('address') else address.address
        if addr:
            write(addr)

        po_box = '' if is_field_hidden('po_box') else address.po_box
        if po_box:
            if sio.tell():
                write('\n')

            write(po_box)

        zipcode = '' if is_field_hidden('zipcode') else address.zipcode
        city    = '' if is_field_hidden('city')    else address.city
        if zipcode or city:
            if sio.tell():
                write('\n')

            if not zipcode:
                write(city)
            elif not city:
                write(zipcode)
            else:
                write(zipcode)
                write(' ')
                write(city)

        return sio.getvalue()


@register.filter
def persons_pretty_contact(contact):
    civ = contact.civility
    last_name = contact.last_name.upper()

    if civ and civ.shortcut:
        return _('{civility} {first_name} {last_name}').format(
            civility=civ.shortcut,
            first_name=contact.first_name,
            last_name=last_name,
        )

    if contact.first_name:
        return _('{first_name} {last_name}').format(
            first_name=contact.first_name,
            last_name=last_name,
        )

    return last_name or ''


# NB: only used in opportunities?
@register.simple_tag
def persons_contact_first_employer(contact, user):
    info = {}
    managed_ids = []
    employing_ids = []

    for rtype_id, orga_id in contact.relations.filter(
        type__in=(REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES),
    ).values_list('type', 'object_entity'):
        if rtype_id == REL_SUB_MANAGES:
            managed_ids.append(orga_id)
        else:
            employing_ids.append(orga_id)

    if managed_ids:
        orga = EntityCredentials.filter(
            user,
            get_organisation_model().objects.filter(id__in=managed_ids, is_deleted=False),
        ).first()

        if orga:
            info['organisation'] = orga
            info['as_manager'] = True

    if not info and employing_ids:
        orga = EntityCredentials.filter(
            user,
            get_organisation_model().objects.filter(id__in=employing_ids, is_deleted=False),
        ).first()

        if orga:
            info['organisation'] = orga
            info['as_manager'] = False

    return info


@register.simple_tag
def persons_addresses_formblock_fields(form, address_fks, zip_fields=True):
    if not address_fks:
        return None

    meta = []
    grouped_fields = []

    # NB: we expect that AddressesGroup injects corresponding fields in the
    #     same order (e.g. "city" as first for billing & shipping, then "zipcode"...)
    for fk in address_fks:
        prefix = f'{fk.name}-'

        meta.append({
            'title': fk.verbose_name,
            'prefix': fk.name,  # NB: JQuery |= filter already adds a hyphen
        })
        grouped_fields.append(
            [field for field in form if field.name.startswith(prefix)]
        )

    return {
        'grouped_meta': meta,
        'grouped_fields': [*zip(*grouped_fields)] if zip_fields else grouped_fields,
    }
