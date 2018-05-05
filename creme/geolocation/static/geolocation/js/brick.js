/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2014-2018  Hybird

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*******************************************************************************/

(function($) {
"use strict";

creme.geolocation = creme.geolocation || {};

//creme.geolocation.PersonsBlock = creme.component.Component.sub({
creme.geolocation.PersonsBrick = creme.component.Component.sub({
    STATUS_LABELS: {
        0: gettext("Not localized"),
        1: gettext("Manual location"),
        2: gettext("Partially matching location"),
        3: ''
    },

    _init_: function(brick, options) {
        options = $.extend({
            addresses: []
        }, options || {});

        var self = this;

        this._brick = brick;
        this._addresses = options.addresses;

        var controller = this._controller = new creme.geolocation.GoogleMapController(options);

        controller.on('save-location', this._onSaveLocation.bind(this))
                  .on('api-status', this._onAPIStatus.bind(this))
                  .on('map-status', this._onCanvasStatus.bind(this));

        brick.on('state-update', this._onBrickStateUpdate.bind(this));

        this.addressItems().each(function() {
            var checkbox = $('input[type="checkbox"]', this);
//            var resetbutton = $('.block-geoaddress-reset', this);
            var resetbutton = $('.brick-geoaddress-reset', this);

            resetbutton.click(self._onRefreshLocation.bind(self));
            checkbox.change(self._onToggleLocation.bind(self));

            // initialize map with current checkbox state.
            self._toggleLocation(checkbox.val(), checkbox.is(':checked'));
        });

        controller.loadAPI({
                       apiKey: options.apiKey,
                       container: this.canvas()
                   });
    },

    _onBrickStateUpdate: function(event, state) {
        if (!state.collapsed) {
            this._controller.resize();
            this._controller.adjustMap();
        }
    },

    _onAPIStatus: function(event, status) {
        this._brick.element().toggleClass('is-geolocation-disabled', !status);
    },

    _onCanvasStatus: function(event, status) {
        if (status) {
            this._addresses.forEach(this._geocodeAddress.bind(this));
        }
    },

    _onSaveLocation: function(event, address, marker, status) {
        this._showPosition(address.id, marker);
        this._showStatus(address.id, status);
        this._brick.trigger('geoaddress-location', [address, marker]);
    },

    _geocodeAddress: function(address) {
        var self = this;
        var controller = this._controller;

        if (controller.isAddressLocated(address)) {
            controller.marker_manager.Marker({
                address: address,
                draggable: true,
                visible: false
            });
        } else {
            controller.findLocation(address, {
                draggable: true,
                done: function(marker) {
                    controller.marker_manager.hideAll();
                },
                fail: function(data) {
                    self._showStatus(address.id, data);
                }
            });
        }
    },

    addressItem: function(address_id) {
//        return $('.block-geoaddress-item[data-addressid="' + address_id + '"]', this._brick.element());
        return $('.brick-geoaddress-item[data-addressid="' + address_id + '"]', this._brick.element());
    },

    addressItems: function() {
//        return $('.block-geoaddress-item', this._brick.element());
        return $('.brick-geoaddress-item', this._brick.element());
    },

    canvas: function() {
//        return $('.block-geoaddress-canvas', this._brick.element());
        return $('.brick-geoaddress-canvas', this._brick.element());
    },

    _showStatus: function(address_id, status) {
        var item = this.addressItem(address_id);
        var is_complete = (status === creme.geolocation.LocationStatus.COMPLETE);

//        item.find('.block-geoaddress-status').html(this.STATUS_LABELS[status]);
        item.find('.brick-geoaddress-status').html(this.STATUS_LABELS[status]);
//        item.find('.block-geoaddress-action').toggleClass('block-geoaddress-iscomplete', is_complete);
        item.find('.brick-geoaddress-action').toggleClass('brick-geoaddress-iscomplete', is_complete);
    },

    _showPosition: function(address_id, marker) {
        var content = '';

        if (!Object.isEmpty(marker)) {
            content = '%3.6f, %3.6f'.format(marker.position.lat(),
                                            marker.position.lng());
        }

        // result.formatted_address
//        this.addressItem(address_id).find('.block-geoaddress-position').html(content);
        this.addressItem(address_id).find('.brick-geoaddress-position').html(content);
    },

    _toggleLocation: function(address_id, status) {
        this._controller.marker_manager.toggle(address_id, status);
        this.addressItem(address_id).toggleClass('item-selected', status);
    },

    _onRefreshLocation: function(event) {
        var self       = this;
        var controller = this._controller;

        var address_id = parseInt($(event.target).attr('data-addressid'));
        var marker     = controller.getMarker(address_id);

        if (marker) {
            this._controller.findLocation(marker.address, {
                                 done: function(marker, result, status) {
                                     controller.adjustMap();
                                 },
                                 fail: function(status) {
                                     self._showPosition(address_id);
                                     self._showStatus(address_id, status);
                                 }
                             });
        }
    },

    _onToggleLocation: function(event) {
        this._toggleLocation($(event.target).val(), $(event.target).is(':checked'));
    }
});


//creme.geolocation.AddressesBlock = creme.component.Component.sub({
creme.geolocation.AddressesBrick = creme.component.Component.sub({
    _init_: function(brick, options) {
        options = options || {};

//        if (!options.addressesUrl) {
//            console.warn('creme.geolocation.AddressesBlock(): hard-coded "addressesUrl" is deprecated ; give it as the second parameter.');
//        }

        this._brick = brick;
//        this._addressesUrl = options.addressesUrl || '/geolocation/get_addresses/';
        this._addressesUrl = options.addressesUrl;

        var controller = this._controller = new creme.geolocation.GoogleMapController(options);
        controller.on('api-status', this._onAPIStatus.bind(this))
                  .on('map-status', this._onCanvasStatus.bind(this));

        brick.on('state-update', this._onBrickStateUpdate.bind(this));

        controller.loadAPI({
                       apiKey: options.apiKey,
                       container: this.canvas()
                   });
    },

    _onBrickStateUpdate: function(event, state) {
        if (!state.collapsed) {
            this._controller.resize();
            this._controller.adjustMap();
        }
    },

    _onAPIStatus: function(event, status) {
        this._brick.element().toggleClass('is-geolocation-disabled', !status);
    },

    _onCanvasStatus: function(event, status) {
        if (status) {
//            var filterSelector = this._filterSelector = $('.block-geoaddress-filter', this._brick.element());
            var filterSelector = this._filterSelector = $('.brick-geoaddress-filter', this._brick.element());
            filterSelector.change(this._onFilterChange.bind(this));
            this._updateFilter(filterSelector.val());
        }
    },

    _queryAddresses: function(filter, listeners) {
        var self = this;
        var controller = this._controller;
        var updateAddress = this._updateAddress.bind(this);
        var url = this._addressesUrl;

        creme.ajax.query(url, {}, {id: filter})
                  .converter(JSON.parse)
                  .onDone(function(event, data) {
                      data.addresses.forEach(updateAddress);
                      controller.adjustMap();
                      self._showCount(data.addresses.length);
                   })
                  .onFail(function() {
                      controller.adjustMap();
                      self._showCount(0);
                  })
                  .on(listeners || {}).get();
    },

    _updateAddress: function(address) {
        var controller = this._controller;
        var marker = controller.marker_manager.get(address.id);

        if (!marker) {
            if (controller.isAddressLocated(address)) {
                controller.marker_manager.Marker({
                    address:   address,
                    draggable: false,
                    redirect:  address.url
                });
            }
        } else {
            marker.setVisible(true);
        }
    },

    _onFilterChange: function(event) {
        var controller = this._controller;
        var filter = $(event.target).val();

        controller.marker_manager.hideAll();

        this._updateFilter(filter, {
                 fail: function() {
                     $(event.target).val('');
                 }
             });
    },

    _updateFilter: function(filter, listeners) {
        if (filter) {
            this._queryAddresses(filter, listeners);
        } else {
            this._controller.adjustMap();
            this._showCount(0);
        }
    },

    _showCount: function(count) {
        var content = !count ? gettext('No address from') : ngettext('%0$d address from', '%0$d addresses from', count).format(count);
//        $('.block-geoaddress-counter', this._brick.element()).html(content);
        $('.brick-geoaddress-counter', this._brick.element()).html(content);
    },

    canvas: function() {
//        return $('.block-geoaddress-canvas', this._brick.element());
        return $('.brick-geoaddress-canvas', this._brick.element());
    }
});


//creme.geolocation.PersonsNeighborhoodBlock = creme.component.Component.sub({
creme.geolocation.PersonsNeighborhoodBrick = creme.component.Component.sub({
    _init_: function(brick, options) {
        options = options || {};

//        if (!options.neighboursUrl) {
//            console.warn('creme.geolocation.PersonsNeighborhoodBlock(): hard-coded "neighboursUrl" is deprecated');
//        }

        this._radius = options.radius || 1;
        this._brick = brick;
//        this._neighboursUrl = options.neighboursUrl || '/geolocation/get_neighbours/';
        this._neighboursUrl = options.neighboursUrl;

        var controller = this._controller = new creme.geolocation.GoogleMapController(options);
        controller.on('api-status', this._onAPIStatus.bind(this))
                  .on('map-status', this._onCanvasStatus.bind(this));

        brick.on('state-update', this._onBrickStateUpdate.bind(this));

        controller.loadAPI({
                       apiKey: options.apiKey,
                       container: this.canvas()
                   });
    },

    _onBrickStateUpdate: function(event, state) {
        if (!state.collapsed) {
            this._controller.resize();
            this._controller.shape_manager.adjustMap('NeighbourhoodCircle');
        }
    },

    _onAPIStatus: function(event, status) {
        this._brick.element().toggleClass('is-geolocation-disabled', !status);
    },

    _onCanvasStatus: function(event, status) {
        if (status) {
            var container = this._brick.element();

//            this._sourceSelector = $('.block-geoaddress-source', container).change(this._onChange.bind(this));
            this._sourceSelector = $('.brick-geoaddress-source', container).change(this._onChange.bind(this));
//            this._filterSelector = $('.block-geoaddress-filter', container).change(this._onChange.bind(this));
            this._filterSelector = $('.brick-geoaddress-filter', container).change(this._onChange.bind(this));
            this._onChange();
        }
    },

    _queryNeighbours: function(address, filter) {
        if (!address) {
            this._controller.adjustMap();
            return;
        }

        var updateNeighbours = this._updateNeighbours.bind(this);
        var parameters = {
            address_id: address,
            filter_id: filter
        };

        var url = this._neighboursUrl + '?' + $.param(parameters);

        creme.ajax.query(url)
                  .converter(JSON.parse)
                  .onDone(function(event, data) {
                       updateNeighbours(data.source_address, data.addresses);
                   })
                  .onFail(function() {
                       updateNeighbours(address, []);
                   })
                  .get();
    },

    _clearNeighbours: function() {
        var controller = this._controller;
        controller.marker_manager.hideAll();

        if (controller.shape_manager.get('NeighbourhoodCircle')) {
            controller.shape_manager.unregister('NeighbourhoodCircle');
        }
    },

    /* global google */
    _updateMarker: function(address, options) {
        if (Object.isNone(address)) {
            return;
        }

        var controller = this._controller;
        var marker = controller.marker_manager.get(address.id);

        if (controller.isAddressLocated(address)) {
            if (marker) {
                marker.setPosition(new google.maps.LatLng(address.latitude, address.longitude));
            } else {
                options = $.extend({
                    address: address,
                    draggable: false
                }, options || {});

                marker = controller.marker_manager.Marker(options);
            }

            marker.setVisible(true);
        }

        return marker;
    },

    /* global google */
    _updateNeighbours: function(source, addresses) {
        this._clearNeighbours();

        var controller = this._controller;
        var sourceMarker = this._updateMarker(source, {
                                                  icon: {
                                                      path: google.maps.SymbolPath.CIRCLE,
                                                      scale: 5
                                                  }
                                              });

        if (!sourceMarker) {
            return this;
        }

        controller.shape_manager.register('NeighbourhoodCircle',
            new google.maps.Circle({
                strokeColor: '#dea29b',
                strokeOpacity: 0.9,
                strokeWeight: 2,
                fillColor: '#dea29b',
                fillOpacity: 0.40,
                map: controller.map(),
                center: sourceMarker.position,
                radius: this._radius
        }));

        this._showCount(addresses.length);

        var addressMarker = this._updateMarker.bind(this);

        addresses.forEach(function(address) {
            addressMarker(address, {redirect: address.url});
        });

        controller.shape_manager.adjustMap('NeighbourhoodCircle');
    },

    sourcePosition: function(address, position) {
        var mark = this._controller.getMarker(address.id);

        if (mark) {
            mark.setPosition(position);

            if (this._sourceSelector.val() === '' + address.id) {
                this._queryNeighbours(this._sourceSelector.val(), this._filterSelector.val());
            }
        }
    },

    _onChange: function(event) {
        this._queryNeighbours(this._sourceSelector.val(), this._filterSelector.val());
    },

    _showCount: function(count) {
        var counter = !count ? gettext('None of') : ngettext('%0$d of', '%0$d of', count).format(count);
//        $('.block-geoaddress-counter', this._brick.element()).html(counter);
        $('.brick-geoaddress-counter', this._brick.element()).html(counter);
    },

    canvas: function() {
//        return $('.block-geoaddress-canvas', this._brick.element());
        return $('.brick-geoaddress-canvas', this._brick.element());
    }
});

}(jQuery));
