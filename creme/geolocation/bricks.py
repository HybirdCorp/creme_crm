# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2017  Hybird
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
from json import dumps as encode_json

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _  # ugettext

from creme.creme_core.gui.bricks import Brick
from creme.creme_core.models import EntityFilter

from creme import persons

# from .constants import DEFAULT_SEPARATING_NEIGHBOURS
from .models import GeoAddress
# from .setting_keys import NEIGHBOURHOOD_DISTANCE
from .utils import address_as_dict, get_radius  # get_setting


Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()
Address      = persons.get_address_model()


class _MapBrick(Brick):
    dependencies = (Address,)

    def get_filter_choices(self, user, *models):
        choices = []
        get_ct = ContentType.objects.get_for_model
        ctypes = [get_ct(model) for model in models]
        efilters_per_ctid = defaultdict(list)

        for efilter in EntityFilter.get_for_user(user, ctypes):
            efilters_per_ctid[efilter.entity_type_id].append(efilter)

        for ct in ctypes:
            efilters = efilters_per_ctid[ct.id]

            if efilters:
                # title = ugettext(ct.model_class()._meta.verbose_name_plural)
                title = unicode(ct.model_class()._meta.verbose_name_plural)
                choices.append((title,
                                [(ef.id, u'%s - %s' % (title, ef.name)) for ef in efilters]
                               )
                              )

        return choices

    def get_addresses_as_dict(self, entity):
        return [address_as_dict(address)
                    for address in Address.objects.filter(object_id=entity.id)
                                                  .select_related('geoaddress')
               ]


class GoogleDetailMapBrick(_MapBrick):
    id_           = Brick.generate_id('geolocation', 'detail_google_maps')
    verbose_name  = _(u'Addresses on Google Maps ®')
    # template_name = 'geolocation/templatetags/block_persons_google_map.html'
    template_name = 'geolocation/bricks/google/detail-map.html'
    target_ctypes = (Contact, Organisation)

    def detailview_display(self, context):
        entity = context['object']
        addresses = [address for address in self.get_addresses_as_dict(entity) if address.get('content')]
        return self._render(self.get_template_context(
                    context,
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, entity.pk)),
                    addresses=addresses,
                    geoaddresses=encode_json(addresses),
        ))


class GoogleFilteredMapBrick(_MapBrick):
    id_           = Brick.generate_id('geolocation', 'filtered_google_maps')
    verbose_name  = _(u'Filtered addresses on Google Maps ®')
    # template_name = 'geolocation/templatetags/block_persons_filters_google_map.html'
    template_name = 'geolocation/bricks/google/filtered-map.html'

    def home_display(self, context):
        return self._render(self.get_template_context(
                    context,
                    # update_url='/creme_core/blocks/reload/home/%s/' % self.id_,
                    update_url=reverse('creme_core__reload_home_blocks', args=(self.id_,)),
                    address_filters=self.get_filter_choices(context['user'],
                                                            Contact, Organisation,
                                                           ),
        ))


class GoogleNeighboursMapBrick(_MapBrick):
    id_           = Brick.generate_id('geolocation', 'google_whoisaround')
    dependencies  = (Address, GeoAddress,)
    verbose_name  = _(u'Neighbours on Google Maps ®')
    # template_name = 'geolocation/templatetags/block_persons_neighbours_map.html'
    template_name = 'geolocation/bricks/google/neighbours-map.html'
    target_ctypes = (Contact, Organisation)

    # Specific use case
    # Add a new ungeolocatable
    # the person bloc will show an error message
    # this bloc will show an empty select
    # edit this address with a geolocatable address
    # the person block is reloaded and the address is asynchronously geocoded
    # This block is reloaded in the same time and the address has no info yet.

    def detailview_display(self, context):
        entity = context['object']

        return self._render(self.get_template_context(
                    context,
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, entity.pk)),
                    ref_addresses=self.get_addresses_as_dict(entity),
                    address_filters=self.get_filter_choices(context['user'],
                                                            Contact, Organisation,
                                                           ),
                    # radius=get_setting(NEIGHBOURHOOD_DISTANCE,
                    #                    DEFAULT_SEPARATING_NEIGHBOURS,
                    #                   ),
                    radius=get_radius(),
                    maps_blockid=GoogleDetailMapBrick.id_,
        ))
