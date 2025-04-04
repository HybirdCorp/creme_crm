/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2020-2025  Hybird

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

var __googleAPIStatus = {
    NONE: 0,
    LOADING: 1,
    READY: 2,
    UNAVAILABLE: -1
};


var __googleAPI = {
    apiStatus: __googleAPIStatus.NONE
};

var __googleAPIEvents = new creme.component.EventHandler();

window.__googleAPILoaderCb = function() {
    __googleAPI.apiStatus = __googleAPIStatus.READY;
    __googleAPIEvents.trigger('google-api-ready', [$({}, __googleAPI)]);
};

window.gm_authFailure = function() {
    __googleAPI.apiStatus = __googleAPIStatus.UNAVAILABLE;
    __googleAPIEvents.trigger('google-api-error', [$({}, __googleAPI)]);
};

var googleAPIState = function() {
    return $.extend({}, __googleAPI);
};

creme.geolocation.isGoogleAPIReady = function() {
    return __googleAPI.apiStatus === __googleAPIStatus.READY;
};

var GoogleAPILoader = creme.component.Action.sub({
    _init_: function(options) {
        this._super_(creme.component.Action, '_init_', this._loadAPI, options);
    },

    /* global LANGUAGE_CODE */
    _loadAPI: function(options) {
        options = $.extend({
            language: LANGUAGE_CODE || 'en'
        }, this.options(), options);

        var self = this;

        if (__googleAPI.apiStatus === __googleAPIStatus.READY) {
            return self.done(googleAPIState());
        }

        __googleAPIEvents.on('google-api-ready', function(event, status) {
            self.done(status);
        });

        if (__googleAPI.status !== __googleAPIStatus.LOADING) {
            __googleAPI.status = __googleAPIStatus.LOADING;

            if (!options.apiKey) {
                console.warn('creme.geolocation.googleAPILoader(): empty "apiKey" is deprecated ; configure it in settings.');
            }

            var script = document.createElement('script');
            var parameters = {
                v: options.apiVersion || '3.exp',
                callback: '__googleAPILoaderCb',
                language: options.language,
                key: options.apiKey || ''
            };

            script.type = 'text/javascript';
            script.src = _.toRelativeURL('https://maps.googleapis.com/maps/api/js').searchData(parameters).toString();

            document.head.appendChild(script);
        }
    }
});

var GoogleMapShapeRegistry = creme.component.Component.sub({
    _init_: function(controller) {
        this._controller = controller;
        this._shapes = {};
    },

    all: function(query) {
        query = query || {};

        var shapes = Object.values(this._shapes);

        if (query.visible !== undefined) {
            shapes = shapes.filter(function(item) {
                return item.getVisible() === query.visible;
            });
        }

        return shapes;
    },

    register: function(id, shape) {
        Assert.not(Object.isEmpty(id), 'Shape id cannot be empty');
        Assert.not(id in this._shapes, 'Shape "${id}" is already registered', {id: id});

        this._shapes[id] = shape;

        shape.__extra = (shape.__extra || {});
        shape.__extra.id = id;

        shape.setMap(this._controller.map());

        return shape;
    },

    unregister: function(id) {
        Assert.not(Object.isEmpty(id), 'Shape id cannot be empty');
        Assert.that(id in this._shapes, 'Shape "${id}" is not registered', {id: id});

        var shape = this._shapes[id];

        delete shape.__extra.id;
        delete this._shapes[id];

        shape.setMap(null);
        return shape;
    },

    get: function(id) {
        return this._shapes[id];
    },

    update: function(id, options) {
        options = options || {};

        Assert.not(Object.isEmpty(id), 'Shape id cannot be empty');
        Assert.that(id in this._shapes, 'Shape "${id}" is not registered', {id: id});

        if (options.position) {
            var position = options.position;
            options.center = new google.maps.LatLng(position.lat, position.lng);
        }

        var shape = this.get(id);
        shape.setOptions(options);

        if (options.extraData) {
            $.extend(shape.__extra.extraData, options.extraData || {});
        }
    },

    Circle: function(options) {
        options = options || {};

        var position = options.position || {lat: 0, lng: 0};
        var shape = new google.maps.Circle({
            strokeColor: '#dea29b',
            strokeOpacity: 0.9,
            strokeWeight: 2,
            fillColor: '#dea29b',
            fillOpacity: 0.40,
            map: this._controller.map(),
            center: new google.maps.LatLng(position.lat, position.lng),
            radius: options.radius
        });

        shape.__extra = {
            extraData: $.extend({}, options.extraData)
        };

        return shape;
    }
});

var __googleMarkerIcons = {
    "circle": function() {
        return {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 5
        };
    },
    "target": function() {
        return {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 5
        };
    },
    "default": null
};

var __getGoogleMarkerIcon = function(path) {
    var icon = __googleMarkerIcons[path || 'default'];

    if (icon === undefined) {
        return {
            url: path,
            size: new google.maps.Size(25, 41),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(12, 41)
        };
    } else if (Object.isFunc(icon)) {
        return icon(path);
    } else {
        return null;
    }
};

var GoogleMapMarkerManager = creme.component.Component.sub({
    _init_: function(controller) {
        this._controller = controller;
        this._markers = {};
    },

    all: function(query) {
        query = query || {};

        var markers = Object.values(this._markers);

        if (query.visible !== undefined) {
            markers = markers.filter(function(item) {
                return item.getVisible() === query.visible;
            });
        }

        return markers;
    },

    register: function(id, marker) {
        Assert.not(Object.isEmpty(id), 'Marker id cannot be empty');
        Assert.not(id in this._markers, 'Marker "${id}" is already registered', {id: id});

        this._markers[id] = marker;

        marker.__extra = (marker.__extra || {});
        marker.__extra.id = id;

        marker.setMap(this._controller.map());
        return marker;
    },

    unregister: function(id) {
        Assert.not(Object.isEmpty(id), 'Marker id cannot be empty');
        Assert.that(id in this._markers, 'Marker "${id}" is not registered', {id: id});

        var marker = this._markers[id];
        delete marker.__extra.id;
        delete this._markers[id];

        marker.setMap(null);

        return marker;
    },

    Marker: function(options) {
        options = options || {};
        options = $.extend({
            draggable: false
        }, options);

        if (options.icon !== undefined) {
            options.icon = __getGoogleMarkerIcon(options.icon);
        }

        var marker = new google.maps.Marker(options);
        marker.__extra = {
            extraData: $.extend({}, options.extraData)
        };

        var controller = this._controller;

        google.maps.event.addListener(marker, 'click', function() {
                              controller.trigger('marker-click', [marker.__extra, marker, this]);
                          });

        if (options.draggable) {
            google.maps.event.addListener(marker, 'dragstart', function() {
                                  this.__dropData = $.extend({}, marker.__extra, {
                                      dragStartPosition: {
                                          lat: this.getPosition().lat(),
                                          lng: this.getPosition().lng()
                                      }
                                  });
                                  controller.trigger('marker-dragstart', [this.__dropData, marker, this]);
                              });

            google.maps.event.addListener(marker, 'dragend', function() {
                                  var dropData = $.extend({}, this.__dropData || {}, {
                                      dragStopPosition: {
                                          lat: this.getPosition().lat(),
                                          lng: this.getPosition().lng()
                                      }
                                  });
                                  controller.trigger('marker-dragstop', [dropData || {}, marker, this]);
                              });
        }

        return marker;
    },

    update: function(id, options) {
        options = options || {};

        Assert.not(Object.isEmpty(id), 'Marker id cannot be empty');
        Assert.that(id in this._markers, 'Marker "${id}" is not registered', {id: id});

        var marker = this.get(id);

        if (options.icon !== undefined) {
            options.icon = __getGoogleMarkerIcon(options.icon);
        }

        marker.setOptions(options);

        if (options.extraData) {
            $.extend(marker.__extra.extraData, options.extraData || {});
        }
    },

    get: function(id) {
        return this._markers[id];
    },

    getProperties: function(id) {
        var marker = this.get(id);

        if (marker) {
            return {
                id: id,
                title: marker.getTitle(),
                draggable: marker.getDraggable(),
                visible: marker.getVisible(),
                position: {
                    lat: marker.getPosition().lat(),
                    lng: marker.getPosition().lng()
                },
                extraData: (marker.__extra || {}).extraData || {}
            };
        }
    },

    toggle: function(id, state) {
        var marker = this.get(id);

        if (marker) {
            marker.setVisible(state === undefined ? !marker.getVisible() : state);
        }
    },

    toggleAll: function(state) {
        for (var key in this._markers) {
            this.toggle(key, state);
        }
    },

    getBoundBox: function() {
        var boundbox = new google.maps.LatLngBounds();

        this.all({visible: true}).forEach(function(marker) {
            boundbox.extend(marker.getPosition());
        });

        return boundbox;
    }
});

creme.geolocation.GoogleMapController = creme.geolocation.GeoMapController.sub({
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

    _init_: function (options) {
        options = $.extend({
            defaultZoomValue: 12,
            defaultLat: 48,
            defaultLn: 2,
            defaultLargeZoom: 4,
            styles: this.MAPSTYLES.slice(),
            apiVersion: '3.exp'
        }, options || {});

        this._super_(creme.geolocation.GeoMapController, '_init_', options);

        this._options = options;
        this._markers = new GoogleMapMarkerManager(this);
        this._shapes = new GoogleMapShapeRegistry(this);
    },

    _unbindMap: function(element) {
        this.disableMap();
    },

    _bindMap: function() {
        var self = this;

        var _APILoadedCb = function() {
            self.enableGeocoder();

            if (self.isBound()) {
                self.enableMap();
            }
        };

        if (this.isAPIReady()) {
            setTimeout(_APILoadedCb, 0);
            return this;
        }

        new GoogleAPILoader({
                apiKey: this.apiKey
            }).on('done', function() {
                setTimeout(_APILoadedCb, 0);
                self.trigger('google-api-ready');
            }).on('fail', function() {
                console.warn('creme.geolocation.GoogleMapController(): google map API is now disabled');
                self.isEnabled(false);
                self.trigger('google-api-error');
            }).start();

        return this;
    },

    options: function() {
        return $.extend({}, this._options);
    },

    enableMap: function() {
        Assert.not(this.isMapEnabled(), 'Map canvas is already enabled');
        Assert.that(this.isBound(), 'Cannot enable map of an unbound controller');

        this._assertAPIAvailable();

        var styles = this.options().styles || this.MAPSTYLES.slice();
        var container = this.element().get(0);

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

        this.autoResize();
        this.adjustMap();
        this.isEnabled(true);

        return this;
    },

    disableMap: function() {
        this._assertMapEnabled();

        delete this._map;

        this.element().empty();
        this.isEnabled(false);

        return this;
    },

    enableGeocoder: function() {
        try {
            if (this.isGeocoderAllowed() && !this.isGeocoderEnabled()) {
                this._geocoder = new google.maps.Geocoder();
            }
        } catch (e) {
            console.warn('creme.geolocation.GoogleMapController(): unable to build google.maps.Geocoder instance', e);
        }
    },

    _assertMapEnabled: function() {
        Assert.that(this.isMapEnabled(), 'Map canvas is disabled');
    },

    _assertAPIAvailable: function() {
        Assert.that(this.isAPIReady(), 'The google API is not available');
    },

    isMapEnabled: function() {
        return Object.isNone(this._map) === false;
    },

    isAPIReady: function() {
        return __googleAPI.apiStatus === __googleAPIStatus.READY;
    },

    isGeocoderEnabled: function() {
        return Object.isNone(this._geocoder) === false;
    },

    adjustMap: function() {
        if (!this.isMapEnabled()) {
            return this;
        }

        var markerCount = this._markers.all(true).length;
        var options = this.options();

        if (markerCount === 0) {
            this._map.setCenter(new google.maps.LatLng(options.defaultLat, options.defaultLn));
            this._map.setZoom(options.defaultLargeZoom);
        } else {
            var boundbox = this._markers.getBoundBox();
            this._map.setCenter(boundbox.getCenter());

            if (markerCount === 1) {
                this._map.setZoom(options.defaultZoomValue);
            } else {
                this._map.fitBounds(boundbox);
            }
        }

        return this;
    },

    adjustMapToShape: function(id) {
        if (!this.isMapEnabled()) {
            return this;
        }

        var options = this.options();
        var shape = this._shapes.get(id);

        if (shape) {
            this._map.setCenter(shape.getCenter());
            this._map.fitBounds(shape.getBounds());
        } else {
            this._map.setCenter(new google.maps.LatLng(options.defaultLat, options.defaultLn));
            this._map.setZoom(options.defaultLargeZoom);
        }

        return this;
    },

    _searchLocationQuery: function(search) {
        var geocoder = this.geocoder();

        var isPartialMatch = function(results) {
            if (results.length > 1) {
                return true;
            }

            var match = results[0];

            if (match.partial_match === false) {
                return false;
            }

            return match.address_components.length < 7;
        };

        return new creme.component.Action(function() {
            var action = this;

            if (Object.isNone(geocoder)) {
                return this.cancel();
            }

            try {
                geocoder.geocode({address: search}, function(results, status) {
                    if (status !== google.maps.GeocoderStatus.OK) {
                        action.fail(gettext("No matching location"));
                        return;
                    }

                    var result = results[0];
                    var position = result.geometry.location;
                    var isPartial = isPartialMatch(results);
                    var locationStatus = creme.geolocation.LocationStatus.COMPLETE;

                    if (isPartial) {
                        locationStatus = creme.geolocation.LocationStatus.PARTIAL;
                    }

                    action.done(position, locationStatus, result);
                });
            } catch (e) {
                console.error(e);
                this.fail(gettext("No matching location"), e);
            }
        });
    },

    addMarker: function(id, options) {
        this._assertMapEnabled();

        var marker = this._markers.Marker(options);
        this._markers.register(id, marker);
        return marker;
    },

    removeMarker: function(id) {
        this._assertMapEnabled();
        this._markers.unregister(id);
        return this;
    },

    updateMarker: function(id, options) {
        this._assertMapEnabled();
        this._markers.update(id, options);
        return this;
    },

    hasMarker: function(id) {
        return this.isMapEnabled() && Object.isNone(this._markers.get(id)) === false;
    },

    getMarker: function(id) {
        return this.isMapEnabled() ? this._markers.get(id) : undefined;
    },

    getMarkerProperties: function(id) {
        return this.isMapEnabled() ? this._markers.getProperties(id) : undefined;
    },

    markers: function(query) {
        return this.isMapEnabled() ? this._markers.all(query) : [];
    },

    markerIds: function(query) {
        return this.markers(query).map(function(m) {
            return m.__extra.id;
        });
    },

    toggleMarker: function(id, state) {
        this._assertMapEnabled();
        this._markers.toggle(id, state);
        this.adjustMap();

        return this;
    },

    toggleAllMarkers: function(state) {
        this._assertMapEnabled();
        this._markers.toggleAll(state);
        this.adjustMap();

        return this;
    },

    addShape: function(id, options) {
        this._assertMapEnabled();
        var shape;
        var shapeType = options.shape || '';

        switch (shapeType.toLowerCase()) {
            case 'circle':
                shape = this._shapes.Circle(options); break;
            default:
                throw Error('Shape has unknown type "${shape}"'.template({
                    shape: shapeType
                }));
        }

        return this._shapes.register(id, shape);
    },

    getShape: function(id) {
        return this.isMapEnabled() ? this._shapes.get(id) : undefined;
    },

    hasShape: function(id) {
        return this.isMapEnabled() && Object.isNone(this._shapes.get(id)) === false;
    },

    updateShape: function(id, options) {
        this._assertMapEnabled();
        this._shapes.update(id, options);
        return this;
    },

    removeShape: function(id) {
        this._assertMapEnabled();
        this._shapes.unregister(id);

        return this;
    },

    shapes: function(query) {
        return this.isMapEnabled() ? this._shapes.all(query) : [];
    },

    shapeIds: function(query) {
        return this.shapes(query).map(function(s) {
            return s.__extra.id;
        });
    },

    geocoder: function() {
        return this._geocoder;
    },

    map: function() {
        return this._map;
    },

    autoResize: function() {
        if (this.isMapEnabled()) {
            google.maps.event.trigger(this._map, 'resize');
        }

        return this;
    }
});

}(jQuery));
