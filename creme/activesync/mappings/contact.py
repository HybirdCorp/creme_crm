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
import os
from random import randint
import datetime
import time

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.utils import formats
from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _, ugettext

from activesync.utils import get_b64encoded_img_of_max_weight
from creme_core.models.relation import Relation, RelationType
from creme_core.utils.meta import get_field_infos, is_date_field
from creme_core.views.file_handling import handle_uploaded_file, MAXINT
from persons.models import Position, Contact, Civility, Address
from media_managers.models.image import Image
from persons.models.organisation import Organisation
from persons.constants import REL_SUB_EMPLOYED_BY

def get_encoded_contact_img(contact=None, needs_attr=False, *args, **kwargs):
    if needs_attr:
        return 'image'
    encoded_img = None
#    if contact and contact.image is not None:
    if contact:
        if contact.image is not None:
            image_path = str(contact.image.image.file)
            file_size = os.path.getsize(image_path)
            if file_size > settings.PICTURE_LIMIT_SIZE:
                encoded_img = get_b64encoded_img_of_max_weight(image_path, settings.PICTURE_LIMIT_SIZE)
            else:
                encoded_img = contact.image.get_encoded(encoding="base64")
        else:
            encoded_img = ""
    return encoded_img

def get_repr(contact=None, needs_attr=False, *args, **kwargs):
    if needs_attr:
        return ''
    return unicode(contact)

def get_organisation(contact=None, needs_attr=False, *args, **kwargs):
    if needs_attr:
        return 'organisation'

    organisation = ""

    relations = Relation.objects.filter(subject_entity=contact,
                                       type=REL_SUB_EMPLOYED_BY)

    if relations:
        organisation = unicode(relations[0].object_entity.get_real_entity())

    return organisation

CREME_CONTACT_MAPPING = {
    'Contacts:':
    {
        'civility__title'         : 'Title',
        'first_name'              : 'FirstName',
        'last_name'               : 'LastName',
        'skype'                   : 'Home2PhoneNumber',
        'phone'                   : 'HomePhoneNumber',
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
        get_organisation          : 'CompanyName',
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

if not settings.IS_ZPUSH:
    CREME_CONTACT_MAPPING['AirSyncBase:'].update({'description': 'Body'})

### Contact helpers
def create_or_update_organisation(contact, d, user, history=None):
    organisation = d.pop('organisation', None)

    if organisation is not None:
        try:
            org = Organisation.objects.get(name__iexact=organisation, user=user)
        except Organisation.DoesNotExist:
            org = Organisation.objects.create(name=organisation, user=user)
            if history is not None:
                history.changes = [(_(u"Contact's organisation created"), org)]
        except Organisation.MultipleObjectsReturned:
            org = Organisation.objects.filter(name__iexact=organisation, user=user)[0]

        Relation.objects.get_or_create(subject_entity=contact,
                                       type=RelationType.objects.get(pk=REL_SUB_EMPLOYED_BY),
                                       object_entity=org,
                                       user=user)


def create_or_update_address(contact, prefix, data, history=None):
    dpop_ = data.pop
    address = getattr(contact, '%s_address' % prefix)#if exception happens means model change

    city            = dpop_('%s_address__city'    % prefix, None)
    state           = dpop_('%s_address__state'   % prefix, None)
    country         = dpop_('%s_address__country' % prefix, None)
    po_box          = dpop_('%s_address__po_box'  % prefix, None)
    address_content = dpop_('%s_address__address' % prefix, None)

    changes = []

    if address is not None:

        if city:
            address.city = city
            changes.append(('%s_address__city'    % prefix, city))

        if state:
            address.state = state
            changes.append(('%s_address__state'   % prefix, state))

        if country:
            address.country = country
            changes.append(('%s_address__country' % prefix, country))

        if po_box:
            address.po_box = po_box
            changes.append(('%s_address__po_box'  % prefix, po_box))

        if address_content:
            address.address = address_content
            changes.append(('%s_address__address' % prefix, address_content))

        address.save()
    elif any([city, state, country, po_box, address_content]):
        c_address = Address(city=city,
                    state=state,
                    country=country,
                    po_box=po_box,
                    address=address_content)

        c_address.content_type = ContentType.objects.get_for_model(Contact)
        c_address.object_id = contact.id
        c_address.save()
        setattr(contact, '%s_address' % prefix, c_address)
        changes.append(('%s_address' % prefix, c_address))

    if history is not None:
        history.changes = changes


def create_or_update_civility(contact, d, history=None):
    civility_title = d.pop('civility__title', None)
    if civility_title is not None:
        old_civility = contact.civility
        contact.civility = Civility.objects.get_or_create(title=civility_title)[0]

        if history is not None and contact.civility != old_civility:
            history.changes = [('civility__title', contact.civility)]


#TODO: Rename create_or_update_position
def create_or_update_function(contact, d, history=None):
    position_title = d.pop('position__title', None)
    if position_title is not None:
        old_position = contact.position
        contact.position = Position.objects.get_or_create(title=position_title)[0]

        if history is not None and contact.position != old_position:
            history.changes = [('position__title', contact.position)]


def create_image_from_b64(contact, d, user):
    image_b64 = d.pop('image', None)
    if image_b64 is not None:
        if contact.image is not None:
            img_entity = contact.image
            img_entity.image.delete()#Deleting the old file
        else:
            img_entity = Image()

        image_format = Image.get_image_format(image_b64)
        img_entity.image = handle_uploaded_file(ContentFile(base64.decodestring(image_b64)), path=['upload','images'], name='file_%08x.%s' % (randint(0, MAXINT), image_format))
        img_entity.user = user
        img_entity.save()
        contact.image = img_entity
###
def _format_data(model_or_entity, data):
    for field_name, value in data.iteritems():
        field_class, field_value = get_field_infos(model_or_entity, field_name)
        if field_class is not None and issubclass(field_class, (models.DateTimeField, models.DateField)):
            datetime_formatted = False
            for format in formats.get_format('DATETIME_INPUT_FORMATS'):
                try:
                    data[field_name] = datetime.datetime(*time.strptime(value, format)[:6])
                    datetime_formatted = True
                except ValueError:
                    continue

            if not datetime_formatted:
                data[field_name] = None
        elif isinstance(value, basestring):
            data[field_name] = value
#            data[field_name] = value.decode('utf-8')


def save_contact(data, user, *args, **kwargs):
    """Save a contact from a populated data dict
        @Returns : A saved contact instance
    """
    c = Contact()
    ct_contact = ContentType.objects.get_for_model(Contact)
    pop_ = data.pop

    pop_('', None)

    create_or_update_civility(c, data)
    create_or_update_function(c, data)

    #TODO:Use create_or_update_address
    b_address = Address(city=pop_('billing_address__city', None),
                        state=pop_('billing_address__state', None),
                        country=pop_('billing_address__country', None),
                        po_box=pop_('billing_address__po_box', None),
                        address=pop_('billing_address__address', None))
    c.billing_address  = b_address

    #TODO:Use create_or_update_address
    s_address = Address(city=pop_('shipping_address__city', None),
                        state=pop_('shipping_address__state', None),
                        country=pop_('shipping_address__country', None),
                        po_box=pop_('shipping_address__po_box', None),
                        address=pop_('shipping_address__address', None))
    c.shipping_address = s_address

    create_image_from_b64(c, data, user)

    c.user = user

    _format_data(c, data)

    c.__dict__.update(data)
    c.save()

    create_or_update_organisation(c, data, user)

    b_address.content_type = ct_contact
    b_address.object_id = c.id
    b_address.save()

    s_address.content_type = ct_contact
    s_address.object_id = c.id
    s_address.save()

    return c

def update_contact(contact, data, user, history, *args, **kwargs):
    """Update a contact instance from a updated data dict
        @Returns : A saved contact instance
    """
    pop_ = data.pop
    pop_('', None)

    create_or_update_civility(contact, data, history)
    create_or_update_function(contact, data, history)

    create_or_update_address(contact, 'billing',  data, history)
    create_or_update_address(contact, 'shipping', data, history)

    create_image_from_b64(contact, data, contact.user)

    create_or_update_organisation(contact, data, user, history)

    _format_data(contact, data)

    write_simple_history(history, data)

    contact.__dict__.update(data)#TODO: setattr better ?
    contact.save()

    history.save()
    return contact

def write_simple_history(history, data):
    changes = []
    for ns, fields in CREME_CONTACT_MAPPING.iteritems():
        for creme_field in fields.iterkeys():
            updated = data.get(creme_field)
            if updated is not None:
                changes.append((creme_field, updated.encode('utf-8')))#Adding changes to the history
            #else tell the attr was emptied?

    history.changes = changes

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

def pre_serialize_contact(value, c_field, xml_field, f_class, entity):
    return value
