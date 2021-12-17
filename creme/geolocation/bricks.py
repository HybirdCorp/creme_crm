# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2021  Hybird
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

from collections import defaultdict

from django.contrib.contenttypes.models import ContentType
from django.utils.html import escape
from django.utils.translation import gettext_lazy as _

from creme import persons
from creme.creme_core.gui.bricks import Brick, BrickDependencies
from creme.creme_core.models import EntityFilter

from .models import GeoAddress
from .utils import (
    address_as_dict,
    get_google_api_key,
    get_openstreetmap_settings,
    get_radius,
)

Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()
Address      = persons.get_address_model()


class _MapBrick(Brick):
    dependencies: BrickDependencies = (Address,)

    @staticmethod
    # def get_filter_choices(self, user, *models):
    def get_filter_choices(user, *models):
        choices = []
        get_ct = ContentType.objects.get_for_model
        ctypes = [get_ct(model) for model in models]
        efilters_per_ctid = defaultdict(list)

        for efilter in EntityFilter.objects.filter_by_user(user)\
                                           .filter(entity_type__in=ctypes):
            efilters_per_ctid[efilter.entity_type_id].append(efilter)

        for ct in ctypes:
            efilters = efilters_per_ctid[ct.id]

            if efilters:
                title = str(ct.model_class()._meta.verbose_name_plural)
                choices.append((
                    title,
                    [(ef.id, f'{title} - {ef.name}') for ef in efilters],
                ))

        return choices

    @staticmethod
    # def get_addresses_as_dict(self, entity):
    def get_addresses_as_dict(entity):
        return [
            {
                k: (escape(v) if isinstance(v, str) else v)
                for k, v in address_as_dict(address).items()
            } for address in Address.objects
                                    .filter(object_id=entity.id)
                                    .select_related('geoaddress')
        ]

    def get_template_context(self, context: dict, **extra_kwargs) -> dict:
        return super().get_template_context(
            context,
            map_api_key=self.get_api_key(),
            **self.get_map_settings(),
            **extra_kwargs
        )

    def get_api_key(self):
        return ''

    def get_map_settings(self):
        return {}


class _DetailMapBrick(_MapBrick):
    target_ctypes = (Contact, Organisation)

    def detailview_display(self, context):
        entity = context['object']
        addresses = [
            address
            for address in self.get_addresses_as_dict(entity)
            if address.get('content')
        ]

        return self._render(self.get_template_context(
            context,
            addresses=addresses,
            geoaddresses=addresses,
        ))


class GoogleDetailMapBrick(_DetailMapBrick):
    id_ = Brick.generate_id('geolocation', 'detail_google_maps')
    verbose_name = _('Addresses on Google Maps ®')
    description = _(
        'Display the addresses of the Contact/Organisation on Google Maps ®.\n'
        'App: Geolocation'
    )
    template_name = 'geolocation/bricks/google/detail-map.html'

    def get_api_key(self):
        return get_google_api_key()


class OpenStreetMapDetailMapBrick(_DetailMapBrick):
    id_ = Brick.generate_id('geolocation', 'detail_openstreetmap')
    verbose_name = _('Addresses on OpenStreetMap ®')
    description = _(
        'Display the addresses of the Contact/Organisation on OpenStreetMap ®.\n'
        'App: Geolocation'
    )
    template_name = 'geolocation/bricks/osm/detail-map.html'

    def get_map_settings(self):
        return get_openstreetmap_settings()


class _FilteredMapBrick(_MapBrick):
    def home_display(self, context):
        return self._render(self.get_template_context(
            context,
            address_filters=self.get_filter_choices(
                context['user'], Contact, Organisation,
            ),
        ))


class GoogleFilteredMapBrick(_FilteredMapBrick):
    id_ = Brick.generate_id('geolocation', 'filtered_google_maps')
    verbose_name = _('Filtered addresses on Google Maps ®')
    description = _(
        'Display on Google Maps ® the addresses of the Contacts/Organisations '
        'corresponding to a filter.\n'
        'App: Geolocation'
    )
    template_name = 'geolocation/bricks/google/filtered-map.html'

    def get_api_key(self):
        return get_google_api_key()


class OpenStreetMapFilteredMapBrick(_FilteredMapBrick):
    id_ = Brick.generate_id('geolocation', 'filtered_openstreetmap')
    verbose_name = _('Filtered addresses on OpenStreetMap ®')
    description = _(
        'Display on OpenStreetMap ® the addresses of the Contacts/Organisations '
        'corresponding to a filter.\n'
        'App: Geolocation'
    )
    template_name = 'geolocation/bricks/osm/filtered-map.html'

    def get_map_settings(self):
        return get_openstreetmap_settings()


class _NeighboursMapBrick(_MapBrick):
    dependencies = (Address, GeoAddress,)
    target_ctypes = (Contact, Organisation)

    # Specific use case
    #  Add a new "ungeolocatable"; the person brick will show an error message
    #  This brick will show an empty <select>
    #  Edit this address with a geolocatable address ; the person brick is
    #  reloaded and the address is asynchronously geocoded
    #  This brick is reloaded in the same time and the address has no info yet.

    def detailview_display(self, context):
        entity = context['object']

        return self._render(self.get_template_context(
            context,
            ref_addresses=self.get_addresses_as_dict(entity),
            address_filters=self.get_filter_choices(
                context['user'], Contact, Organisation,
            ),
            radius=get_radius(),
            maps_blockid=self.detail_map.id_,
        ))


class GoogleNeighboursMapBrick(_NeighboursMapBrick):
    id_ = Brick.generate_id('geolocation', 'google_whoisaround')
    verbose_name = _('Neighbours on Google Maps ®')
    description = _(
        'Display on Google Maps ® the addresses of the neighbours of the Contact/Organisation. '
        'The neighbours are Contacts/Organisations and can be filtered.\n'
        'App: Geolocation'
    )
    template_name = 'geolocation/bricks/google/neighbours-map.html'
    detail_map = GoogleDetailMapBrick

    def get_api_key(self):
        return get_google_api_key()


class OpenStreetMapNeighboursMapBrick(_NeighboursMapBrick):
    id_ = Brick.generate_id('geolocation', 'openstreetmap_whoisaround')
    verbose_name = _('Neighbours on OpenStreetMap ©')
    description = _(
        'Display on OpenStreetMap ® the addresses of the neighbours of the Contact/Organisation. '
        'The neighbours are Contacts/Organisations and can be filtered.\n'
        'App: Geolocation'
    )
    template_name = 'geolocation/bricks/osm/neighbours-map.html'
    detail_map = OpenStreetMapDetailMapBrick

    def get_map_settings(self):
        return get_openstreetmap_settings()
