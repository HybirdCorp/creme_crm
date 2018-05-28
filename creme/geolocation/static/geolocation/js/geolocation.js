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

/* TODO: rename google-geolocation ?? */

var __googleAPILoadStatus = {
    NONE: 0,
    RUNNING: 1,
    LOADED: 2
};


var __googleAPI = {
    loadStatus: __googleAPILoadStatus.NONE,
    available: false
};

var __googleAPIEvents = new creme.component.EventHandler();

window.__googleAPILoaderCb = function() {
    __googleAPI.loadStatus = __googleAPILoadStatus.LOADED;
    __googleAPI.available = true;
    __googleAPIEvents.trigger('google-api-loaded', [$({}, __googleAPI)]);
};

window.gm_authFailure = function() {
    __googleAPI.available = false;
    __googleAPIEvents.trigger('google-api-error', [$({}, __googleAPI)]);
};

creme.geolocation.googleAPIState = function() {
    return $.extend({}, __googleAPI);
};

creme.geolocation.GoogleAPILoader = creme.component.Action.sub({
    _init_: function(options) {
        this._super_(creme.component.Action, '_init_', this._loadAPI, options);
    },

    /* global LANGUAGE_CODE */
    _loadAPI: function(options) {
        options = $.extend({
            language: LANGUAGE_CODE || 'en'
        }, this.options(), options);

        var self = this;

        if (__googleAPI.loadStatus === __googleAPILoadStatus.LOADED) {
            return self.done($({}, __googleAPI));
        }

        __googleAPIEvents.on('google-api-loaded', function(event, status) {
            self.done(status);
        });

        if (__googleAPI.status !== __googleAPILoadStatus.RUNNING) {
            __googleAPI.status = __googleAPILoadStatus.RUNNING;

            if (!options.apiKey) {
                console.warn('creme.geolocation.googleAPILoader(): empty "apiKey" is deprecated ; configure it in settings.');
            }

            var script = document.createElement('script');
            var parameters = {
                v: '3.exp',
                callback: '__googleAPILoaderCb',
                language: options.language,
                key: options.apiKey || ''
            };

            script.type = 'text/javascript';
            script.src = 'https://maps.googleapis.com/maps/api/js?' + $.param(parameters);

            document.head.appendChild(script);
        }
    }
});

creme.geolocation.LocationStatus = {
    UNDEFINED: 0,
    MANUAL:    1,
    PARTIAL:   2,
    COMPLETE:  3
};

creme.geolocation.GoogleMapController = creme.component.Component.sub({
    MAPSTYLES: [
        {
            id: 'creme',
            label: gettext('Map'),
            style: [
                {
                    stylers: [
                         {hue: '#94c6db'},
                         {weight: 2}
                    ]
                },
                {
                    featureType: 'road',
                    elementType: 'geometry',
                    stylers: [
                      { visibility: 'simplified' }
                    ]
                }
            ]
        }
    ],

    /* global google setTimeout */
    _init_: function (options) {
        this.defaultZoomValue = 12;
        this.defaultLat = 48;
        this.defaultLn = 2;
        this.defaultLargeZoom = 4;

        this._infoUrl = options.infoUrl;
        this._events = new creme.component.EventHandler();

        this.marker_manager = new creme.geolocation.GoogleMapMarkerManager(this);
        this.shape_manager = new creme.geolocation.GoogleMapShapeRegistry(this);
    },

    /* global google */
    loadAPI: function(options, listeners) {
        options = options || {};

        var events = this._events;
        var _APILoadedCb = function() {
            var status = false;

            try {
                if (Object.isNone(this.geocoder)) {
                    this.geocoder = new google.maps.Geocoder();
                }

                status = true;
            } catch (e) {
                console.warn('creme.geolocation.GoogleMapController(): unable to build google.maps.Geocoder instance', e);
            }

            if (status && !Object.isNone(options.container)) {
                this.enableMap(options.container, options.styles);
            }
        }.bind(this);

        events.one(listeners || {});

        if (this.isAPILoaded()) {
            setTimeout(_APILoadedCb, 200);
            return this;
        }

        __googleAPIEvents.on('google-api-error', function(event, status) {
            console.warn('creme.geolocation.GoogleMapController(): google map API is now disabled');
            events.trigger('api-status', [false]);
        });

        new creme.geolocation.GoogleAPILoader({
                                  apiKey: options.apiKey
                              }).on('done', function() {
                                  setTimeout(_APILoadedCb, 200);
                              }).on('fail', function() {
                                  events.trigger('api-status', [false]);
                              }).start();

        return this;
    },

    enableMap: function(container, styles) {
        if (this.isMapEnabled()) {
            return this;
        }

        styles = styles || this.MAPSTYLES.slice();
        container = (container instanceof jQuery) ? container.get(0) : container;

        var styleIds = styles.map(function(style) {
                                  return style.id;
                              })
                             .concat(google.maps.MapTypeId.SATELLITE);

        var map = this._map = new google.maps.Map(container, {
            zoom: this.defaultZoomValue,
            mapTypeControlOptions: {
                mapTypeIds: styleIds
            }
        });

        styles.forEach(function(style) {
            map.mapTypes.set(style.id, new google.maps.StyledMapType(style.style, { name: style.label }));
        });

        map.setMapTypeId(styleIds[0]);

        this._mapContainer = container;

        this.resize();
        this.adjustMap();
        this._events.trigger('map-status', [true]);
        return this;
    },

    disableMap: function() {
        if (!this.isMapEnabled()) {
            return this;
        }

        delete this._map;

        this._mapContainer.empty();
        this._mapContainer = undefined;

        this._events.trigger('map-status', [false]);
        return this;
    },

    assertAPIAvailable: function() {
        if (!this.isAPIAvailable()) {
            throw new Error('The google API is not available');
        }
    },

    isMapEnabled: function() {
        return Object.isNone(this._map) === false;
    },

    isAPILoaded: function() {
        return __googleAPI.loadStatus === __googleAPILoadStatus.LOADED;
    },

    isAPIAvailable: function() {
        return __googleAPI.available;
    },

    on: function(event, listener, decorator) {
        this._events.on(event, listener, decorator);
        return this;
    },

    off: function(event, listener) {
        this._events.off(event, listener);
        return this;
    },

    one: function(event, listener) {
        this._events.one(event, listener);
        return this;
    },

    adjustMap: function() {
        if (!this.isMapEnabled()) {
            return this;
        }

        var n_markers = this.marker_manager.count(true);

        if (n_markers === 0) {
            var default_location = new google.maps.LatLng(this.defaultLat, this.defaultLn);
            this._map.setCenter(default_location);
            this._map.setZoom(this.defaultLargeZoom);
        } else {
            var boundbox = this.marker_manager.getBoundBox();
            this._map.setCenter(boundbox.getCenter());

            if (n_markers === 1) {
                this._map.setZoom(this.defaultZoomValue);
            } else {
                this._map.fitBounds(boundbox);
            }
        }

        return this;
    },

    adjustMapToShape: function(shape) {
        if (!this.isMapEnabled()) {
            return this;
        }

        this._map.setCenter(shape.getCenter());
        this._map.fitBounds(shape.getBounds());
    },

    _isPartialMatch: function(results) {
        if (results.length > 1) {
            return true;
        }

        var match = results[0];

        if (match.partial_match === false) {
            return false;
        }

        return match.address_components.length < 7;
    },

    geocode: function(options) {
        var marker_manager = this.marker_manager;
        var saveLocation = this.saveLocation.bind(this);
        var isPartialMatch = this._isPartialMatch.bind(this);

        this.geocoder.geocode(options.data, function(results, status) {
            var address = options.address;

            if (status === google.maps.GeocoderStatus.OK) {
                var marker   = marker_manager.get(address.id);
                var result   = results[0];

                var position = result.geometry.location;
                var isPartial = isPartialMatch(results);
                var location_status = creme.geolocation.LocationStatus.COMPLETE;

                if (isPartial) {
                    location_status = creme.geolocation.LocationStatus.PARTIAL;
                }

                if (!marker) {
                    marker = marker_manager.Marker({
                        address:   address,
                        draggable: options.draggable,
                        position:  position
                    });
                } else {
                    marker.setPosition(position);
                }

                saveLocation(marker, {
                                 address: address,
                                 initial_position: options.initial_position
                             }, true, location_status);

                if (Object.isFunc(options.callback)) {
                    options.callback(marker, result, location_status);
                }
            } else {
                if (Object.isFunc(options.fail)) {
                    options.fail(gettext("No matching location"));
                }
            }
        });

        return this;
    },

    saveLocation: function(marker, options, geocoded, status) {
        var self = this;

        creme.ajax.query(this._infoUrl, {}, {
                             id:        options.address.id,
                             latitude:  marker.position.lat(),
                             longitude: marker.position.lng(),
                             geocoded:  geocoded,
                             status:    status
                         })
                  .onFail(function() {
                              marker.setPosition(options.initial_position);
                          })
                  .onDone(function() {
                              self._events.trigger('save-location', [options.address, marker, status]);
                          })
                  .post();

        return this;
    },

    findLocation: function(address, options) {
        return this.geocode({
            address:   address,
            draggable: options.draggable,
            data:      {address: address.content},
            fail:      options.fail,
            callback:  options.done
        });
    },

    getMarker: function(id) {
        return this.marker_manager.get(id);
    },

    map: function() {
        return this._map;
    },

    isAddressLocated: function(address) {
        return address && !Object.isNone(address.latitude) && !Object.isNone(address.longitude);
    },

    resize: function() {
        google.maps.event.trigger(this._map, 'resize');
        return this;
    }
});

creme.geolocation.GoogleMapShapeRegistry = creme.component.Component.sub({
    _init_: function(controller) {
        this._controller = controller;
        this._shapes = {};
    },

    register: function(shape_id, shape) {
        if (shape_id in this._shapes) {
            throw new Error('Shape "' + shape_id + '" is already registered');
        }
        this._shapes[shape_id] = shape;
    },

    unregister: function(shape_id) {
        if (shape_id in this._shapes) {
            this._shapes[shape_id].setMap(null);
            delete this._shapes[shape_id];
        } else {
            throw new Error('Shape "' + shape_id + '" not registered');
        }
    },

    get: function(shape_id) {
        if (shape_id in this._shapes) {
            return this._shapes[shape_id];
        } else {
            return false;
        }
    },

    adjustMap: function(shape_id) {
        this._controller.adjustMapToShape(this.get(shape_id));
        return this;
    }
});

creme.geolocation.GoogleMapMarkerManager = creme.component.Component.sub({
    _init_: function(controller) {
        this._controller = controller;
        this._markers = {};
    },

    markers: function(visible) {
        var markers = Object.values(this._markers);

        if (visible === undefined) {
            return markers;
        }

        return markers.filter(function(item) {
            return item.getVisible() === visible;
        });
    },

    count: function(visible) {
        return this.markers(visible).length;
    },

    register: function(marker) {
        var id = marker.address.id;

        if (id in this._markers) {
            throw new Error('marker "' + id + '" is already registered');
        }

        this._markers[id] = marker;
    },

    Marker: function(options) {
        options = $.extend({
            map:       this._controller.map(),
            draggable: false
        }, options || {});

        var address = options.address;

        options.position = options.position || new google.maps.LatLng(address.latitude, address.longitude);
        options.title = '%s\n%s'.format(address.owner, address.title || address.content);

        var marker = new google.maps.Marker(options);
        this.register(marker);

        if (options.redirect) {
            google.maps.event.addListener(marker, 'click', function() {
                                  creme.utils.goTo(options.redirect);
                              });
        }

        if (options.draggable) {
            var saveLocation = this._controller.saveLocation.bind(this._controller);

            google.maps.event.addListener(marker, 'dragstart', function() {
                                  options.initial_position = this.getPosition();
                              });

            google.maps.event.addListener(marker, 'dragend', function() {
                                  saveLocation(marker, options, true, creme.geolocation.LocationStatus.MANUAL);
                              });
        }

        return marker;
    },

    get: function(id) {
        return this._markers[id];
    },

    show: function(id) {
        this.toggle(id, true);
    },

    hide: function(id) {
        this.toggle(id, false);
    },

    toggle: function(id, state) {
        var marker = this.get(id);

        if (marker) {
            marker.setVisible(state === undefined ? !marker.getVisible() : state);
            this._controller.adjustMap();
        }
    },

    hideAll: function() {
        for (var key in this._markers) {
            this._markers[key].setVisible(false);
        }
    },

    getBoundBox: function() {
        var boundbox = new google.maps.LatLngBounds();

        this.markers(true).forEach(function(marker) {
            boundbox.extend(marker.getPosition());
        });

        return boundbox;
    }
});

}(jQuery));
