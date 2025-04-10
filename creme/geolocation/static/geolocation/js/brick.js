/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2014-2025  Hybird

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

creme.geolocation.PersonsBrick = creme.component.Component.sub({
    _init_: function(brick, options) {
        options = $.extend({
            addresses: 'script[type$="/json"].geoaddress-data:first'
        }, options || {});

        this._brick = brick;

        this.addresses(options.addresses);
        this.locationUrl(options.locationUrl);

        Assert.is(options.mapController, creme.geolocation.GeoMapController, '${value} is not a GeoMapController');

        this._controller = options.mapController;
        this._controller.on('marker-dragstop', this._onDropLocation.bind(this))
                        .on('status', this._onCanvasStatus.bind(this))
                        .on('status-enabled', this._onCanvasEnabled.bind(this));

        brick.on('state-update', this._onBrickStateUpdate.bind(this));

        // reset checkbox states (FF bug)
        this.addresses().forEach(function(location) {
            this.addressItem(location.id()).find('input[type="checkbox"]').prop('checked', location.visible());
        }.bind(this));

        brick.element().on('change', '.brick-geoaddress-item input[type="checkbox"]', this._onToggleLocation.bind(this));
        brick.element().on('click', '.brick-geoaddress-item.is-mark-visible .brick-geoaddress-reset', this._onResetLocation.bind(this));

        this._controller.bind(this.canvas());
    },

    _onBrickStateUpdate: function(event, state) {
        if (!state.collapsed) {
            this._controller.autoResize();
            this._controller.adjustMap();
        }
    },

    _onCanvasStatus: function(event, status) {
        this._brick.element().toggleClass('is-geolocation-disabled', !status);
    },

    _onCanvasEnabled: function() {
        this.addresses().filter(function(location) { return location.visible(); })
                        .forEach(function(location) {
                            this._markLocation({
                                location: location,
                                draggable: true
                            });
                        }.bind(this));
    },

    _onDropLocation: function(event, data, marker, mousevent) {
        var self = this;

        this.saveLocation({
            id: data.id,
            position: data.dragStopPosition,
            status: creme.geolocation.LocationStatus.MANUAL
        }, {
            'cancel fail': function() {
                self._controller.updateMarker(data.id, {
                    position: data.dragStartPosition
                });
            },
            done: function() {
                var location = self.address(data.id);
                location.position(data.dragStopPosition);
                location.status(creme.geolocation.LocationStatus.MANUAL);

                self._renderLocationStatus(location);
            }
        });
    },

    _markLocation: function(options) {
        options = options || {};

        var self = this;
        var location = options.location;

        return this._controller.markLocation(options, {
            done: function(event, position, status, data) {
                var hasImproved = status > location.status();

                location.position(position);
                location.status(status);
                location.visible(true);

                // when position accuracy has improved, save it !
                if (hasImproved) {
                    self.saveLocation(location);
                }

                self._renderLocationStatus(location);
                self._controller.adjustMap();
            },
            fail: function() {
                location.status(creme.geolocation.LocationStatus.UNDEFINED);

                self._renderLocationStatus(location);
                self._controller.adjustMap();
            }
        });
    },

    locationUrl: function(url) {
        return Object.property(this, '_locationUrl', url);
    },

    address: function(addressId) {
        return this._addresses[addressId];
    },

    addresses: function(addresses) {
        if (addresses === undefined) {
            return Object.values(this._addresses);
        }

        if (_.isString(addresses)) {
            var script = _.readJSONScriptText($(addresses, this._brick.element()).get(0));
            addresses = Object.isEmpty(script) ? [] : JSON.parse(script);
        }

        var data = this._addresses = {};

        for (var index in addresses) {
            var address = addresses[index];

            if (Object.isEmpty(address.id)) {
                throw new Error('PersonsBrick : empty address id');
            } else if (data[address.id] !== undefined) {
                throw new Error('PersonsBrick : address "${id}" already exists'.template(address));
            }

            // TODO : create a "visible" attribute on server side
            data[address.id] = new creme.geolocation.Location($.extend({
                visible: address.selected || address.is_billing
            }, address));
        }

        return this;
    },

    addressItem: function(address_id) {
        return $('.brick-geoaddress-item[data-addressid="' + address_id + '"]', this._brick.element());
    },

    addressItems: function() {
        return $('.brick-geoaddress-item', this._brick.element());
    },

    canvas: function() {
        return $('.brick-geoaddress-canvas', this._brick.element());
    },

    mapController: function() {
        return this._controller;
    },

    saveLocation: function(location, listeners) {
        var self = this;
        location = new creme.geolocation.Location(location);

        if (Object.isEmpty(this.locationUrl())) {
            new creme.component.Action(function() {
                this.cancel();
            }).on(listeners || {}).start();

            return this;
        }

        creme.ajax.query(this.locationUrl(), {}, {
                       id:        location.id(),
                       latitude:  location.position().lat,
                       longitude: location.position().lng,
                       geocoded:  true,
                       status:    location.status()
                   })
                  .onDone(function() {
                       self._brick.trigger('geoaddress-location-save', [location]);
                   })
                  .on(listeners || {})
                  .post();

        return this;
    },

    _renderLocationStatus: function(location) {
        var item = this.addressItem(location.id());

        item.find('.brick-geoaddress-status').text(location.statusLabel());
        item.find('.brick-geoaddress-action').toggleClass('brick-geoaddress-iscomplete', location.isComplete());
        item.find('.brick-geoaddress-position').text(location.positionLabel());
        item.find('input[type="checkbox"]').prop('checked', location.visible());
        item.toggleClass('is-mark-visible', location.visible());
    },

    _toggleLocation: function(location, visible) {
        if (this._controller.hasMarker(location.id())) {
            this._controller.toggleMarker(location.id(), visible);
            this._controller.adjustMap();
            location.visible(visible);
            this._renderLocationStatus(location);
        } else if (visible) {
            this._markLocation({
                location: location,
                draggable: true
            });
        }
    },

    _onResetLocation: function(event) {
        var id = $(event.target).attr('data-addressid');
        var location = this.address(id);

        this._markLocation({
            location: location,
            draggable: true,
            force: true
        });
    },

    _onToggleLocation: function(event) {
        var location = this.address($(event.target).val());
        this._toggleLocation(location, $(event.target).is(':checked'));
    }
});


creme.geolocation.AddressesBrick = creme.component.Component.sub({
    _init_: function(brick, options) {
        options = options || {};

        this._brick = brick;
        this._addresses = [];

        this.addressesUrl(options.addressesUrl);

        Assert.is(options.mapController, creme.geolocation.GeoMapController, '${value} is not a GeoMapController');

        this._controller = options.mapController;
        this._controller.on('status', this._onCanvasStatus.bind(this))
                        .on('status-enabled', this._onCanvasEnabled.bind(this))
                        .on('marker-click', this._onMarkerClick.bind(this));

        brick.on('state-update', this._onBrickStateUpdate.bind(this));
        brick.element().on('change', '.brick-geoaddress-filter', this._onFilterChange.bind(this));

        this._controller.bind(this.canvas());
    },

    canvas: function() {
        return $('.brick-geoaddress-canvas', this._brick.element());
    },

    filterSelector: function() {
        return $('.brick-geoaddress-filter', this._brick.element());
    },

    counterItem: function() {
        return $('.brick-geoaddress-counter', this._brick.element());
    },

    addressesUrl: function(url) {
        return Object.property(this, '_addressesUrl', url);
    },

    addresses: function() {
        return this._addresses;
    },

    address: function(id) {
        var res = this._addresses.filter(function(n) {
            return n.id() === id;
        });

        return res.length > 0 ? res[0] : undefined;
    },

    mapController: function() {
        return this._controller;
    },

    _onBrickStateUpdate: function(event, state) {
        if (!state.collapsed) {
            this._controller.autoResize();
            this._controller.adjustMap();
        }
    },

    _onCanvasStatus: function(event, status) {
        this._brick.element().toggleClass('is-geolocation-disabled', !status);
    },

    _onCanvasEnabled: function(event) {
        this._queryAddresses(this._brick.element().find('.brick-geoaddress-filter').val());
    },

    _queryAddresses: function(filter, listeners) {
        var self = this;
        var query;

        if (Object.isEmpty(filter)) {
            query = new creme.component.Action(function() {
                this.fail();
            });
        } else {
            query = creme.ajax.query(this.addressesUrl(), {}, {id: filter})
                              .converter(JSON.parse);
        }

        query.onDone(function(event, data) {
                  self._onUpdateAddresses(data.addresses);
              })
             .onFail(function() {
                  self._onUpdateAddresses([]);
              })
             .on(listeners || {});

        return query.start();
    },

    _onUpdateAddresses: function(addresses) {
        addresses = addresses || [];
        var controller = this._controller;

        controller.toggleAllMarkers(false);

        this._addresses = addresses.map(function(address) {
            var location = new creme.geolocation.Location(Object.assign({
                position: address.latitude ? {
                    lat: address.latitude,
                    lng: address.longitude
                } : null
            }, address || {}));

            if (location.hasPosition()) {
                controller.updateOrAddMarker(location.id(), {
                    title: location.markerLabel(),
                    position: location.position(),
                    visible: true,
                    draggable: false,
                    icon: location.icon(),
                    iconShadow: location.iconShadow(),
                    extraData: location.extraData() || {}
                });
            }

            return location;
        });

        controller.adjustMap();
        this._renderCount(controller.markers({visible: true}).length);
    },

    _onMarkerClick: function(event, data) {
        var location = this.address(data.id);

        if (location && !Object.isEmpty(location.url())) {
            creme.utils.goTo(location.url());
        }
    },

    _onFilterChange: function(event) {
        var filter = $(event.target);

        this._queryAddresses(filter.val(), {
             fail: function() {
                 filter.val('');
             }
         });
    },

    _renderCount: function(count) {
        var content = count > 0 ? ngettext('%0$d address from', '%0$d addresses from', count).format(count) : gettext('No address from');
        $('.brick-geoaddress-counter', this._brick.element()).html(content);
    }
});


creme.geolocation.PersonsNeighborhoodBrick = creme.component.Component.sub({
    _init_: function(brick, options) {
        options = options || {};

        this._brick = brick;
        this._origin = null;
        this._neighbours = [];

        this.radius(options.radius || 1);
        this.neighboursUrl(options.neighboursUrl);

        Assert.is(options.mapController, creme.geolocation.GeoMapController, '${value} is not a GeoMapController');

        this._controller = options.mapController;
        this._controller.on('status', this._onCanvasStatus.bind(this))
                        .on('status-enabled', this._onUpdateNeighbours.bind(this))
                        .on('marker-click', this._onMarkerClick.bind(this));

        brick.on('state-update', this._onBrickStateUpdate.bind(this));

        this._brick.element().on('change', '.brick-geoaddress-origin', this._onUpdateNeighbours.bind(this));
        this._brick.element().on('change', '.brick-geoaddress-filter', this._onUpdateNeighbours.bind(this));
        $(document).on('brick-geoaddress-location-save', '.geolocation-detail-brick', this._onMoveLocation.bind(this));

        this._controller.bind(this.canvas());
    },

    neighboursUrl: function(url) {
        return Object.property(this, '_neighboursUrl', url);
    },

    radius: function(radius) {
        return Object.property(this, '_radius', radius);
    },

    mapController: function() {
        return this._controller;
    },

    _onBrickStateUpdate: function(event, state) {
        if (!state.collapsed) {
            this._controller.autoResize();
            this._controller.adjustMapToShape('NeighbourhoodCircle');
        }
    },

    _onCanvasStatus: function(event, status) {
        this._brick.element().toggleClass('is-geolocation-disabled', !status);
    },

    _onUpdateNeighbours: function() {
        this._queryNeighboursOf({
            originId: this.originSelector().val(),
            filterId: this.filterSelector().val()
        });
    },

    _queryNeighboursOf: function(options, listeners) {
        options = options || {};

        var markNeighbours = this.markNeighbours.bind(this);
        var query;

        if (Object.isEmpty(options.originId)) {
            query = new creme.component.Action(function() {
                this.fail();
            });
        } else {
            query = creme.ajax.query(this.neighboursUrl(), {}, {
                                   address_id: options.originId,
                                   filter_id: options.filterId
                               })
                              .converter(JSON.parse);
        }

        query.onDone(function(event, data) {
                  markNeighbours({
                      originId: options.originId,
                      origin: new creme.geolocation.Location(data.source_address),
                      neighbours: data.addresses.map(function(address) {
                          return new creme.geolocation.Location(address);
                      })
                  });
              })
             .onFail(function() {
                  markNeighbours({
                      originId: options.originId,
                      origin: null,
                      neighbours: []
                  });
              })
             .on(listeners || []);

        return query.start();
    },

    markNeighbours: function(options) {
        options = options || {};

        var controller = this._controller;
        var origin = this._origin = options.origin || null;
        var neighbours = this._neighbours = options.neighbours || [];

        controller.toggleAllMarkers(false);

        if (Object.isNone(origin)) {
            controller.removeAllMarkers();
            controller.removeAllShapes();
        } else {
            controller.updateOrAddShape('NeighbourhoodCircle', {
                position: origin.position(),
                radius: this.radius(),
                shape: 'circle'
            });

            controller.replaceMarkers(neighbours.map(function(location) {
                return {
                    id: location.id(),
                    title: location.markerLabel(),
                    position: location.position(),
                    draggable: false,
                    visible: true,
                    icon: location.icon(),
                    iconShadow: location.iconShadow(),
                    extraData: location.extraData()
                };
            }));

            controller.updateOrAddMarker(origin.id(), {
                title: origin.markerLabel(),
                position: origin.position(),
                draggable: false,
                icon: origin.icon() || 'target',
                iconShadow: origin.iconShadow(),
                extraData: origin.extraData() || {}
            });

            controller.adjustMapToShape('NeighbourhoodCircle');
        }

        this._renderCount(neighbours.length);
    },

    _onMoveLocation: function(event, brick, location) {
        this._onUpdateNeighbours();
    },

    _onMarkerClick: function(event, data) {
        var location = this.neighbour(data.id);

        if (location && !Object.isEmpty(location.url())) {
            creme.utils.goTo(location.url());
        }
    },

    canvas: function() {
        return $('.brick-geoaddress-canvas', this._brick.element());
    },

    originSelector: function() {
        return $('.brick-geoaddress-origin', this._brick.element());
    },

    filterSelector: function() {
        return $('.brick-geoaddress-filter', this._brick.element());
    },

    neighbours: function() {
        return this._neighbours;
    },

    neighbour: function(id) {
        var res = this._neighbours.filter(function(n) {
            return n.id() === id;
        });

        return res.length > 0 ? res[0] : undefined;
    },

    origin: function() {
        return this._origin;
    },

    counterItem: function() {
        return $('.brick-geoaddress-counter', this._brick.element());
    },

    _renderCount: function(count) {
        var content = count > 0 ? ngettext('%0$d of', '%0$d of', count).format(count) : gettext('None of');
        this.counterItem().text(content);
    }
});

}(jQuery));
