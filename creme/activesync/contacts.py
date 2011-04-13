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
import base64
from random import randint

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile

from activesync.config import IS_ZPUSH
from creme_core.utils.meta import get_field_infos
from creme_core.views.file_handling import handle_uploaded_file, MAXINT
from persons.models import Position, Contact, Civility, Address
from media_managers.models.image import Image

def get_encoded_contact_img(contact=None, needs_attr=False, *args, **kwargs):
    if needs_attr:
        return 'image'
    encoded_img = None
    if contact and contact.image is not None:
        encoded_img = contact.image.get_encoded(encoding="base64")
    return encoded_img

def get_repr(contact=None, needs_attr=False, *args, **kwargs):
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
        'position__title'         : 'JobTitle',
#        'sector__sector_name'     : None,
        'email'                   : 'Email1Address',
        'url_site'                : 'WebPage',
        'billing_address__city'   : 'BusinessCity',
        'billing_address__state'  : 'BusinessState',
        'billing_address__country': 'BusinessCountry',
        'billing_address__po_box' : 'BusinessPostalCode',
        'billing_address__address': 'BusinessStreet',
        'shipping_address__city'   : 'OtherCity',
        'shipping_address__state'  : 'OtherState',
        'shipping_address__country': 'OtherCountry',
        'shipping_address__po_box' : 'OtherPostalCode',
        'shipping_address__address': 'OtherStreet',
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


### Contact helpers
def create_or_update_address(contact, prefix, d):
    dpop_ = d.pop
    address = getattr(contact, '%s_address' % prefix)#if exception happens means model change
    if address is not None:
        city = dpop_('%s_address__city' % prefix, None)
        if city:
            address.city = city

        state = dpop_('%s_address__state' % prefix, None)
        if state:
            address.state = state

        country = dpop_('%s_address__country' % prefix, None)
        if country:
            address.country = country

        po_box = dpop_('%s_address__po_box' % prefix, None)
        if po_box:
            address.po_box = po_box

        _address = dpop_('%s_address__address' % prefix, None)
        if _address:
            address.address = _address

        address.save()
    else:
        c_address = Address(city=dpop_('%s_address__city' % prefix, None),
                    state=dpop_('%s_address__state' % prefix, None),
                    country=dpop_('%s_address__country' % prefix, None),
                    po_box=dpop_('%s_address__po_box' % prefix, None),
                    address=dpop_('%s_address__address' % prefix, None))
        c_address.content_type = ContentType.objects.get_for_model(Contact)
        c_address.object_id = contact.id
        c_address.save()
        setattr(contact, '%s_address' % prefix, c_address)

def create_or_update_civility(contact, d):
    civility_name = d.pop('civility__civility_name', None)
    if civility_name is not None:
        contact.civility = Civility.objects.get_or_create(civility_name=civility_name)[0]

def create_or_update_function(contact, d):
    position_title = d.pop('position__title', None)
    if position_title is not None:
        contact.function = Position.objects.get_or_create(title=position_title)[0]

def create_image_from_b64(contact, d, user):
    image_b64 = d.pop('image', None)
    if image_b64 is not None:
        image_format = Image.get_image_format(image_b64)
        i = Image()
        i.image = handle_uploaded_file(ContentFile(base64.decodestring(image_b64)), path=['upload','images'], name='file_%08x.%s' % (randint(0, MAXINT), image_format))
        i.user = user
        i.save()
        contact.image = i
###

def save_contact(data, user):
    """Save a contact from a populated data dict
        @Returns : A saved contact instance
    """
    c = Contact()
    ct_contact = ContentType.objects.get_for_model(Contact)
    pop_ = data.pop
    
    pop_('', None)

    create_or_update_civility(c, data)
    create_or_update_function(c, data)

    b_address = Address(city=pop_('billing_address__city', None),
                        state=pop_('billing_address__state', None),
                        country=pop_('billing_address__country', None),
                        po_box=pop_('billing_address__po_box', None),
                        address=pop_('billing_address__address', None))
    c.billing_address  = b_address

    s_address = Address(city=pop_('shipping_address__city', None),
                        state=pop_('shipping_address__state', None),
                        country=pop_('shipping_address__country', None),
                        po_box=pop_('shipping_address__po_box', None),
                        address=pop_('shipping_address__address', None))
    c.shipping_address = s_address

    create_image_from_b64(c, data, user)
        
    c.user = user
    c.__dict__.update(data)
    c.save()

    b_address.content_type = ct_contact
    b_address.object_id = c.id
    b_address.save()

    s_address.content_type = ct_contact
    s_address.object_id = c.id
    s_address.save()
    
    return c

def update_contact(contact, data, user):
    """Update a contact instance from a updated data dict
        @Returns : A saved contact instance
    """
    pop_ = data.pop
    pop_('', None)
    
    create_or_update_civility(contact, data)
    create_or_update_function(contact, data)

    create_or_update_address(contact, 'billing',  data)
    create_or_update_address(contact, 'shipping', data)

    create_image_from_b64(contact, data, contact.user)

    contact.__dict__.update(data)
    contact.save()
    return contact

def serialize_contact(contact, namespaces):
    """Serialize a contact in xml respecting namespaces prefixes
       TODO/NB: Need to send an empty value when the contact hasn't a value ?
       TODO: Add the possibility to subset contact fields ?
    """
    xml = []
    xml_append = xml.append
    for ns, values in CREME_CONTACT_MAPPING.iteritems():
        prefix = namespaces.get(ns)
        for c_field, xml_field in values.iteritems():
            value = None
            if callable(c_field):
                value = c_field(contact)
            else:
                f_class, value = get_field_infos(contact, c_field)

            if value:
                xml_append("<%(prefix)s%(tag)s>%(value)s</%(prefix)s%(tag)s>" %
                           {
                            'prefix': '%s:' % prefix if prefix else '',
                            'tag': xml_field,
                            'value': value #Problems with unicode
                            }
                           )
    return "".join(xml)      
