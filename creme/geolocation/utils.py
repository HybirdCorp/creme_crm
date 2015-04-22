# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2015  Hybird
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

from math import cos, radians

from django.contrib.contenttypes.models import ContentType
from django.db.models.query_utils import Q
from django.utils.translation import ugettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.setting_key import SettingKey
from creme.creme_core.models import SettingValue

from creme.persons import get_address_model
#from creme.persons.models import Address


def address_as_dict(address):
    from .models import GeoAddress

    title      = address_title(address)
    content    = unicode(address)
    owner      = address.owner
    address_id = address.id

    geoaddress = GeoAddress.get_geoaddress(address)

    is_billing  = owner.billing_address_id == address_id
    is_shipping = owner.shipping_address_id == address_id

    return {
            'id':           address_id,
            'content':      content,
            'owner':        unicode(owner),
            'title':        title,
            'is_billing':   is_billing,
            'is_shipping':  is_shipping,
            'is_complete':  geoaddress.is_complete,
            'status':       geoaddress.status,
            'status_label': geoaddress.get_status_display(),
            'latitude':     geoaddress.latitude,
            'longitude':    geoaddress.longitude,
            'draggable':    geoaddress.draggable,
            'geocoded':     geoaddress.geocoded,
            'url':          owner.get_absolute_url(),
           }

def address_title(address):
    if address.name:
        return address.name

    if address.owner.billing_address_id == address.id:
        return _('Billing address')

    if address.owner.shipping_address_id == address.id:
        return _('Shipping address')

    return ''

def addresses_from_persons(queryset, user):
    entities = EntityCredentials.filter(user, queryset.filter(is_deleted=False))
#    addresses = Address.objects.filter(content_type_id=ContentType.objects.get_for_model(queryset.model).id)
    addresses = get_address_model().objects.filter(content_type_id=ContentType.objects.get_for_model(queryset.model).id)

    # get address ids which owner has billing or shipping or both
    billing_shipping_ids = entities.filter(Q(billing_address__isnull=False) | Q(shipping_address__isnull=False))\
                                   .values_list('pk', 'billing_address', 'shipping_address')
    billing_shipping_ids = {owner: billing or shipping for owner, billing, shipping in billing_shipping_ids}

    # get address ids which owner without billing nor shipping
    address_ids = {owner: pk for owner, pk in
                        addresses.filter(object_id__in=entities.filter(billing_address__isnull=True,
                                                                  shipping_address__isnull=True,
                                                                 )
                                                               .values_list('pk', flat=True)
                                        )
                                 .order_by('-pk')
                                 .values_list('object_id', 'pk')
                  }

    # merge ids
    address_ids.update(billing_shipping_ids)
    return addresses.filter(pk__in=address_ids.itervalues()) # TODO: select_related('geoaddress') ??

# TODO : move it to creme_core
def get_setting(key, default=None):
    try:
        if isinstance(key, SettingKey):
            key = key.id

        return SettingValue.objects.get(key_id=key).value
    except SettingValue.DoesNotExist:
        return default

def location_bounding_box(latitude, longitude, distance):
    # latitude:  1 deg ~ 110.54 km
    # longitude: 1 deg ~ 111.32 km ⋅ cos(latitude)
    offset_latitude = distance / 110540.0
    offset_longitude = distance / (111320.0 * cos(radians(latitude)))

    return ((latitude - offset_latitude, longitude - offset_longitude),
            (latitude + offset_latitude, longitude + offset_longitude))
