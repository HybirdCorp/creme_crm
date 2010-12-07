# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from activesync.config import IS_ZPUSH
from creme_core.utils.meta import get_field_infos

def get_encoded_contact_img(contact, needs_attr=False):
    if needs_attr:
        return 'image'
    encoded_img = None
    if contact.image is not None:
        encoded_img = contact.image.get_encoded(encoding="base64")
    return encoded_img

def get_repr(contact, needs_attr=False):
    if needs_attr:
        return ''
    return unicode(contact)

CREME_CONTACT_MAPPING = {
    'Contacts:':
    {
        'civility__civility_name' : 'Title',
        'first_name'              : 'FirstName',
        'last_name'               : 'LastName',
        'skype'                   : 'Home2PhoneNumber',
        'landline'                : 'HomePhoneNumber',
        'mobile'                  : 'MobilePhoneNumber',
        'function__function_name' : 'JobTitle',
#        'sector__sector_name'     : None,
        'email'                   : 'Email1Address',
        'url_site'                : 'WebPage',
        'billing_adress__city'    : 'BusinessCity',
        'billing_adress__state'   : 'BusinessState',
        'billing_adress__country' : 'BusinessCountry',
        'billing_adress__po_box'  : 'BusinessPostalCode',
        'billing_adress__address' : 'BusinessStreet',
        'shipping_adress__city'   : 'OtherCity',
        'shipping_adress__state'  : 'OtherState',
        'shipping_adress__country': 'OtherCountry',
        'shipping_adress__po_box' : 'OtherPostalCode',
        'shipping_adress__address': 'OtherStreet',
        'birthday'                : 'Birthday',
        get_encoded_contact_img   : 'Picture',#'image'
#        ''                        : 'CompanyName',
        get_repr                  : 'FileAs',
    },
    'AirSyncBase:':
    {
#        'description': 'Body',#Not implemented in z-push
    },
#    'Contacts2:':
#    {
##        'id': 'CustomerId',#Not really usefull
#    }

}

if not IS_ZPUSH:
    CREME_CONTACT_MAPPING['AirSyncBase:'].update({'description': 'Body'})

def serialize_contact(contact, namespaces):
    """Serialize a contact in xml respecting namespaces prefixes
       TODO/NB: Need to send an empty value when the contact hasn't a value ?
       TODO: Add the possibility to subset contact fields ?
    """
    xml = []
    for ns, values in CREME_CONTACT_MAPPING.iteritems():
        prefix = namespaces.get(ns)
        for c_field, xml_field in values.iteritems():
            value = None
            if callable(c_field):
                value = c_field(contact)
            else:
                f_class, value = get_field_infos(contact, c_field)

            if value:
                xml.append("<%(prefix)s%(tag)s>%(value)s</%(prefix)s%(tag)s>" %
                           {
                            'prefix': '%s:' % prefix if prefix else '',
                            'tag': xml_field,
                            'value': value #Problems with unicode
                            }
                           )
    return "".join(xml)