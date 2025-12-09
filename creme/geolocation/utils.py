################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2025  Hybird
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

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models.query_utils import Q
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import SettingValue
from creme.persons import get_address_model

from . import constants, setting_keys
from .registry import geomarker_icon_registry


def address_as_dict(address):
    from .models import GeoAddress

    title      = address_title(address)
    content    = str(address)
    owner      = address.owner
    address_id = address.id
    owner_icon = geomarker_icon_registry.icon_for_instance(owner).url

    geoaddress = GeoAddress.get_geoaddress(address)

    # NB: we use gettattr() to accept custom person model without
    # billing_address/shipping_address attribute.
    is_billing  = getattr(owner, 'billing_address_id', None) == address_id
    is_shipping = getattr(owner, 'shipping_address_id', None) == address_id

    return {
        'id':           address_id,
        'content':      content,
        'owner':        str(owner),
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
        'icon':         owner_icon if use_entity_icon() else None
    }


def address_title(address):
    if address.name:
        return address.name

    address_id = address.id

    # See above
    if getattr(address.owner, 'billing_address_id', None) == address_id:
        return _('Billing address')

    if getattr(address.owner, 'shipping_address_id', None) == address_id:
        return _('Shipping address')

    return ''


def addresses_from_persons(queryset, user):
    entities = EntityCredentials.filter(user, queryset.filter(is_deleted=False))
    addresses = get_address_model().objects.filter(
        content_type=ContentType.objects.get_for_model(queryset.model),
    )

    # get address ids which owner has billing or shipping or both
    billing_shipping_ids = {
        owner: billing or shipping
        for owner, billing, shipping in entities.filter(
            Q(billing_address__isnull=False) | Q(shipping_address__isnull=False)
        ).values_list('pk', 'billing_address', 'shipping_address')
    }

    # get address ids which owner without billing nor shipping
    address_ids = {
        owner: pk
        for owner, pk in addresses.filter(
            object_id__in=entities.filter(
                billing_address__isnull=True,
                shipping_address__isnull=True,
            ).values_list('pk', flat=True),
        ).order_by('-pk').values_list('object_id', 'pk')
    }

    # merge ids
    address_ids.update(billing_shipping_ids)

    return addresses.filter(pk__in=address_ids.values())  # TODO: select_related('geoaddress') ??


def get_radius():
    return SettingValue.objects.value_4_key(
        setting_keys.neighbourhood_distance_key,
        default=constants.DEFAULT_SEPARATING_NEIGHBOURS,
    )


def get_google_api_key():
    # return SettingValue.objects.value_4_key(setting_keys.google_api_key, default='') or ''
    return SettingValue.objects.value_4_key(setting_keys.google_api_key, default='')


def use_entity_icon():
    return SettingValue.objects.value_4_key(setting_keys.use_entity_icon_key, default=False)


def get_openstreetmap_settings():
    return {
        'nominatim_url': settings.GEOLOCATION_OSM_NOMINATIM_URL,
        'tilemap_url': settings.GEOLOCATION_OSM_TILEMAP_URL,
        'copyright_url': settings.GEOLOCATION_OSM_COPYRIGHT_URL,
        'copyright_title': settings.GEOLOCATION_OSM_COPYRIGHT_TITLE,
    }


def location_bounding_box(latitude, longitude, distance):
    # latitude:  1 deg ~ 110.54 km
    # longitude: 1 deg ~ 111.32 km ⋅ cos(latitude)
    offset_latitude = distance / 110540.0
    offset_longitude = distance / (111320.0 * cos(radians(latitude)))

    return (
        (latitude - offset_latitude, longitude - offset_longitude),
        (latitude + offset_latitude, longitude + offset_longitude),
    )
