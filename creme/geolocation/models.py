# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2019  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#
#    GNU Affero General Public License for more details.
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from itertools import chain, groupby

from django.conf import settings
from django.db.models import (Model, FloatField, BooleanField,
    OneToOneField, CharField, SlugField, SmallIntegerField, CASCADE)
from django.db.transaction import atomic

from django.db.models.query_utils import Q
from django.template.defaultfilters import slugify
from django.utils.translation import gettext_lazy as _, pgettext_lazy

from creme.creme_core.utils import update_model_instance
from creme.creme_core.utils.chunktools import iter_as_slices

from .utils import location_bounding_box


class GeoAddress(Model):
    UNDEFINED  = 0
    MANUAL     = 1
    PARTIAL    = 2
    COMPLETE   = 3

    STATUS_LABELS = {
        UNDEFINED: _('Not localized'),
        MANUAL:    _('Manual location'),
        PARTIAL:   _('Partially matching location'),
        COMPLETE:  '',
    }

    address   = OneToOneField(settings.PERSONS_ADDRESS_MODEL, verbose_name=_('Address'),
                              primary_key=True, on_delete=CASCADE,
                             )
    latitude  = FloatField(verbose_name=_('Latitude'), null=True, blank=True)  # min_value=-90, max_value=90
    longitude = FloatField(verbose_name=_('Longitude'), null=True, blank=True)  # min_value=-180, max_value=180
    draggable = BooleanField(verbose_name=_('Is this marker draggable in maps ?'), default=True)
    geocoded  = BooleanField(verbose_name=_('Geocoded from address ?'), default=False)
    status    = SmallIntegerField(verbose_name=pgettext_lazy('geolocation', 'Status'),
                                  choices=STATUS_LABELS.items(), default=UNDEFINED,
                                 )

    creation_label = pgettext_lazy('geolocation-address', 'Create an address')

    class Meta:
        app_label = 'geolocation'
        verbose_name = pgettext_lazy('geolocation-address', 'Address')
        verbose_name_plural = pgettext_lazy('geolocation-address', 'Addresses')
        ordering = ('address_id',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._neighbours = {}

    @property
    def is_complete(self):
        return self.status == self.COMPLETE

    @classmethod
    def get_geoaddress(cls, address):
        try:
            geoaddress = address.geoaddress
        except GeoAddress.DoesNotExist:
            geoaddress = None

        if geoaddress is None:
            geoaddress = GeoAddress(address=address)

        return geoaddress

    @classmethod
    def populate_geoaddress(cls, address):
        try:
            geoaddress = address.geoaddress
        except GeoAddress.DoesNotExist:
            geoaddress = GeoAddress(address=address)
            geoaddress.set_town_position(Town.search(address))
            geoaddress.save()

        return geoaddress

    @classmethod
    def populate_geoaddresses(cls, addresses):
        for addresses in iter_as_slices(addresses, 50):
            create = []
            update = []

            # TODO: regroup queries ?
            for address in addresses:
                try:
                    geoaddress = address.geoaddress

                    if geoaddress.latitude is None:
                        update.append(geoaddress)
                except GeoAddress.DoesNotExist:
                    create.append(GeoAddress(address=address))

            towns = Town.search_all([geo.address for geo in chain(create, update)])

            for geoaddress, town in zip(chain(create, update), towns):
                geoaddress.set_town_position(town)

            GeoAddress.objects.bulk_create(create)

            # TODO: only if has changed
            # TODO: bulk_update() ?
            with atomic():
                for geoaddress in update:
                    geoaddress.save(force_update=True)

    def set_town_position(self, town):
        if town is not None:
            self.latitude = town.latitude
            self.longitude = town.longitude
            self.status = GeoAddress.PARTIAL
        else:
            self.latitude = None
            self.longitude = None
            self.status = GeoAddress.UNDEFINED

    def update(self, **kwargs):
        update_model_instance(self, **kwargs)

    def neighbours(self, distance):
        neighbours = self._neighbours.get(distance)

        if neighbours is None:
            self._neighbours[distance] = neighbours = self._get_neighbours(distance)

        return neighbours

    def _get_neighbours(self, distance):
        latitude = self.latitude
        longitude = self.longitude

        if latitude is None and longitude is None:
            return GeoAddress.objects.none()

        upper_left, lower_right = location_bounding_box(latitude, longitude, distance)

        return GeoAddress.objects.exclude(address_id=self.address.pk)\
                                 .exclude(address__object_id=self.address.object_id)\
                                 .filter(latitude__range=(upper_left[0], lower_right[0]),
                                         longitude__range=(upper_left[1], lower_right[1]))

    def __str__(self):
        return 'GeoAddress(lat={}, lon={}, status={})'.format(self.latitude, self.longitude, self.status)


class Town(Model):
    name      = CharField(_('Name of the town'), max_length=100, blank=False, null=False)
    slug      = SlugField(_('Slugified name of the town'), max_length=100, blank=False, null=False)
    zipcode   = CharField(_('Zip code'), max_length=100, blank=True)
    country   = CharField(_('Country'), max_length=40, blank=True)
    latitude  = FloatField(verbose_name=_('Latitude'))
    longitude = FloatField(verbose_name=_('Longitude'))

    creation_label = _('Create a town')

    class Meta:
        app_label = 'geolocation'
        verbose_name = _('Town')
        verbose_name_plural = _('Towns')
        ordering = ('name',)

    def __str__(self):
        return '{} {} {}'.format(self.zipcode, self.name, self.country)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @classmethod
    def search(cls, address):
        zipcode = address.zipcode
        slug = slugify(address.city) if address.city else None
        query_filter = None
        towns = Town.objects.order_by('zipcode')

        if zipcode:
            query_filter = Q(zipcode=zipcode)
        elif slug:
            query_filter = Q(slug=slug)

        if not query_filter:
            return None

        towns = list(towns.filter(query_filter))

        if len(towns) > 1 and slug:
            return next((t for t in towns if t.slug == slug), None)

        return towns[0] if len(towns) == 1 else None

    @classmethod
    def search_all(cls, addresses):
        candidates = list(Town.objects.filter(Q(zipcode__in=(a.zipcode for a in addresses if a.zipcode)) |
                                              Q(slug__in=(slugify(a.city) for a in addresses if a.city))
                                             )
                                      .order_by('zipcode')
                         )

        cities = {key: list(c) for key, c in groupby(candidates, lambda c: c.slug)}
        zipcodes = {key: list(c) for key, c in groupby(candidates, lambda c: c.zipcode)}

        get_city = cities.get
        get_zipcode = zipcodes.get

        for address in addresses:
            zipcode = address.zipcode
            slug = slugify(address.city) if address.city else None
            towns = []

            if zipcode:
                towns = get_zipcode(zipcode, [])
            elif slug:
                towns = get_city(slug, [])

            if len(towns) > 1 and slug:
                yield next((t for t in towns if t.slug == slug), None)
            else:
                yield towns[0] if len(towns) == 1 else None
