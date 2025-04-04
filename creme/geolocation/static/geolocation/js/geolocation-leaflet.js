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

/* global L creme_media_url */
(function($, leaflet) {
"use strict";

creme.geolocation = creme.geolocation || {};

function __iconMark(options) {
    return leaflet.icon(Object.assign({
        className: 'geolocation-leaflet-marker',
        iconUrl: options.iconUrl,
        iconRetinaUrl: options.iconRetinaUrl,
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [-7, -57],
        shadowUrl: options.shadowUrl,
        shadowSize: [41, 41],
        shadowAnchor: [12, 41]
    }, options || {}));
}

function __iconDefault() {
    return __iconMark({
        iconUrl: creme_media_url('geolocation/images/marker-icon.png'),
        iconRetinaUrl: creme_media_url('geolocation/images/marker-icon-2x.png'),
        shadowUrl: creme_media_url('geolocation/images/marker-shadow.png')
    });
}

var __ICONS = {
    "circle": function() {
        return leaflet.divIcon('◯');
    },
    "default": function() {
        return __iconDefault();
    },
    "target": function() {
        return __iconMark({
            iconUrl: creme_media_url('geolocation/images/marker-icon-red.png'),
            iconRetinaUrl: creme_media_url('geolocation/images/marker-icon-red-2x.png'),
            shadowUrl: creme_media_url('geolocation/images/marker-shadow.png')
        });
    }
};

function __markerDraggable(marker, state) {
    if (state === undefined) {
        return marker.dragging && marker.dragging.enabled();
    } else if (marker.dragging) {
        if (state) {
            marker.dragging.enable();
        } else {
            marker.dragging.disable();
        }
    }

    return marker;
}

function __iconMediaURL(path) {
    if (String(path || '').includes('/' + window.THEME_NAME + '/')) {
        return path;
    } else {
        return creme_media_url(path);
    }
}

function __getIcon(path, shadowPath) {
    var icon = __ICONS[path || 'default'];

    if (Object.isFunc(icon)) {
        icon = icon(path, shadowPath);
    } else if (path) {
        icon = __iconMark({
            iconUrl: __iconMediaURL(path),
            iconRetinaUrl: __iconMediaURL(path),
            shadowUrl: shadowPath ? __iconMediaURL(shadowPath) : ''
        });
    }

    return icon || __iconDefault();
}


function __markerIcon(marker, path, shadowPath) {
    if (path === undefined) {
        return marker.getIcon();
    } else {
        marker.setIcon(__getIcon(path, shadowPath));
        return marker;
    }
}


function __circleShape(options) {
    options = $.extend({
        color: '#dea29b',
        opacity: 0.9,
        weight: 2,
        fillColor: '#dea29b',
        fillOpacity: 0.40,
        radius: 1.0
    }, options || {});

    return leaflet.circle([options.position.lat, options.position.lng], options);
}

creme.geolocation.NominatimGeocoder = creme.component.Component.sub({
    _init_: function(options) {
        options = $.extend({
            url: 'https://nominatim.openstreetmap.org/search'
        }, options || {});

        this._url = options.url;
    },

    search: function(content) {
        function isPartialMatch(results) {
            return results.length > 1;
        }

        var url = this._url;

        return new creme.component.Action(function() {
            var action = this;

            creme.ajax.query(url, {}, {
                           q: content,
                           format: 'json',
                           addressdetails: 1
                       })
                      .converter(JSON.parse)
                      .onDone(function(event, data) {
                           if (Object.isEmpty(data)) {
                               action.fail(gettext("No matching location"));
                               return;
                           }

                           var result = data[0];
                           var position = {
                               lat: parseFloat(result.lat),
                               lng: parseFloat(result.lon)
                           };
                           var locationStatus = creme.geolocation.LocationStatus.COMPLETE;

                           if (isPartialMatch(data)) {
                               locationStatus = creme.geolocation.LocationStatus.PARTIAL;
                           }

                           action.done(position, locationStatus, data);
                       })
                      .onFail(function(event, data) {
                           action.fail(gettext("No matching location"));
                       })
                      .start();
        });
    }
});

creme.geolocation.LeafletMapController = creme.geolocation.GeoMapController.sub({
    _init_: function (options) {
        options = $.extend({
            defaultZoomValue: 12,
            defaultLat: 48,
            defaultLn: 2,
            defaultLargeZoom: 4,
            maxZoom: 18,
            minZoom: 1,
            tileMapUrl: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            tileMapAttribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            nominatimUrl: 'https://nominatim.openstreetmap.org/search'
        }, options || {});

        this._super_(creme.geolocation.GeoMapController, '_init_', options);

        this._options = options;
        this._markers = {};
        this._shapes = {};
    },

    _bindMap: function(element) {
        Assert.not(this.isMapEnabled(), 'Map canvas is already enabled');

        var options = this.options();

        var map = this._map = leaflet.map(this.element().get(0), {
            maxZoom: options.maxZoom,
            minZoom: options.minZoom
        });

        map.setView([options.defaultLn, options.defaultLat], options.defaultZoomValue);

        leaflet.tileLayer(options.tileMapUrl, {
            attribution: options.tileMapAttribution
        }).addTo(map);

        this.enableGeocoder();

        this.autoResize();
        this.adjustMap();
        this.isEnabled(true);
    },

    _unbindMap: function(element) {
        Assert.that(this.isMapEnabled(), 'Map canvas is disabled');

        delete this._map;

        this.element().empty();
        this.isEnabled(false);
    },

    defaultLatLng: function() {
        var options = this.options();
        return leaflet.latLng([options.defaultLat, options.defaultLn]);
    },

    options: function() {
        return $.extend({}, this._options);
    },

    geocoder: function() {
        return this._geocoder;
    },

    map: function() {
        return this._map;
    },

    isMapEnabled: function() {
        return Object.isNone(this._map) === false;
    },

    isGeocoderEnabled: function() {
        return Object.isNone(this._geocoder) === false;
    },

    enableGeocoder: function() {
        if (this.isGeocoderAllowed() && !this.isGeocoderEnabled()) {
            this._geocoder = new creme.geolocation.NominatimGeocoder({
                url: this.options().nominatimUrl
            });
        }

        return this;
    },

    adjustMap: function() {
        if (!this.isMapEnabled()) {
            return this;
        }

        var markers = this.markers({visible: true});
        var options = this.options();

        if (markers.length === 0) {
            this._map.setView(
                [options.defaultLat, options.defaultLn],
                options.defaultLargeZoom
            );
        } else if (markers.length === 1) {
            this._map.setView(markers[0].getLatLng(), options.defaultZoomValue);
        } else {
            var bounds = markers.map(function(marker) {
                return marker.getLatLng();
            });

            this._map.fitBounds(bounds);
        }

        return this;
    },

    adjustMapToShape: function(id) {
        if (!this.isMapEnabled()) {
            return this;
        }

        var options = this.options();
        var shape = this.getShape(id);

        if (shape) {
            this._map.fitBounds(shape.getBounds());
        } else {
            this._map.setView(
                [options.defaultLat, options.defaultLn],
                options.defaultLargeZoom
            );
        }

        return this;
    },

    _itemVisibility: function(item, state) {
        var visible = $(item.getElement()).is(':not(.leaflet-hidden)');

        if (state === undefined) {
            return visible;
        } else if (visible !== state) {
            $(item.getElement()).toggleClass('leaflet-hidden', !state);

            if (state) {
                item.addTo(this._map);
            } else {
                item.removeFrom(this._map);
            }
        }
    },

    _itemExtraData: function(item, data) {
        if (data === undefined) {
            return (item.__extra || {}).extraData || {};
        }

        item.__extra = $.extend(true, item.__extra || {}, {
            extraData: data
        });
    },

    _itemExtraId: function(item, id) {
        if (id === undefined) {
            return (item.__extra || {}).id;
        }

        if (id === null && item.__extra) {
            delete item.__extra.id;
        } else {
            item.__extra['id'] = id;
        }

        return item;
    },

    _itemExtraIds: function(items) {
        return items.map(function(item) {
            return item.__extra.id;
        });
    },

    _filterItems: function(items, query) {
        query = query || {};

        var visibility = this._itemVisibility.bind(this);

        if (query.visible !== undefined) {
            items = items.filter(function(item) {
                return visibility(item) === query.visible;
            });
        }

        return items;
    },

    _searchLocationQuery: function(search) {
        if (this.isGeocoderEnabled()) {
            return this._geocoder.search(search);
        }

        return this._super_(creme.geolocation.GeoMapController, '_searchLocationQuery', search);
    },

    addMarker: function(id, options) {
        Assert.that(this.isMapEnabled(), 'Map canvas is disabled');
        Assert.not(Object.isEmpty(id), 'Marker id cannot be empty');
        Assert.not(this.hasMarker(id), 'Marker "${id}" is already registered', {id: id});

        options = $.extend({
            draggable: false,
            visible: true
        }, options || {});

        var position = Object.isNone(options.position) ? this.defaultLatLng() : options.position;
        var marker = leaflet.marker([position.lat, position.lng], {
            title: options.title,
            draggable: true,
            icon: __getIcon(options.icon, options.iconShadow)
        });

        this._itemVisibility(marker, options.visible);
        this._itemExtraData(marker, options.extraData || {});
        this._itemExtraId(marker, id);

        __markerDraggable(marker, options.draggable);

        var controller = this;

        marker.on('click', function() {
            controller.trigger('marker-click', [marker.__extra, marker, this]);
        });

        marker.on('dragstart', function() {
            this.__dropData = $.extend({}, this.__extra, {
                dragStartPosition: {
                    lat: this.getLatLng().lat,
                    lng: this.getLatLng().lng
                }
            });

            controller.trigger('marker-dragstart', [this.__dropData, marker, this]);
        });

        marker.on('dragend', function() {
            var dropData = $.extend({}, this.__dropData || {}, {
                dragStopPosition: {
                    lat: this.getLatLng().lat,
                    lng: this.getLatLng().lng
                }
            });

            controller.trigger('marker-dragstop', [dropData || {}, marker, this]);
        });

        this._markers[id] = marker;
        return marker;
    },

    removeMarker: function(id) {
        Assert.that(this.isMapEnabled(), 'Map canvas is disabled');
        Assert.not(Object.isEmpty(id), 'Marker id cannot be empty');
        Assert.that(this.hasMarker(id), 'Marker "${id}" is not registered', {id: id});

        var marker = this._markers[id];

        this._itemExtraId(marker, null);
        delete this._markers[id];

        marker.remove();
        return marker;
    },

    updateMarker: function(id, options) {
        Assert.that(this.isMapEnabled(), 'Map canvas is disabled');
        Assert.not(Object.isEmpty(id), 'Marker id cannot be empty');
        Assert.that(this.hasMarker(id), 'Marker "${id}" is not registered', {id: id});

        options = options || {};

        var marker = this._markers[id];

        __markerDraggable(marker, options.draggable);
        __markerIcon(marker, options.icon, options.iconShadow);

        this._itemVisibility(marker, options.visible);
        this._itemExtraData(marker, options.extraData);

        if (options.position) {
            marker.setLatLng([options.position.lat, options.position.lng]);
        }

        return this;
    },

    getMarker: function(id) {
        return this.isMapEnabled() ? this._markers[id] : undefined;
    },

    getMarkerProperties: function(id) {
        var marker = this.getMarker(id);

        if (marker) {
            return {
                id: id,
                title: marker.options.title,
                icon: marker.getIcon(),
                draggable: __markerDraggable(marker),
                visible: this._itemVisibility(marker),
                position: {
                    lat: marker.getLatLng().lat,
                    lng: marker.getLatLng().lng
                },
                extraData: (marker.__extra || {}).extraData || {}
            };
        }
    },

    hasMarker: function(id) {
        return id in this._markers;
    },

    markers: function(query) {
        return this._filterItems(Object.values(this._markers), query);
    },

    markerIds: function(query) {
        return this._itemExtraIds(this.markers(query));
    },

    toggleMarker: function(id, state) {
        var marker = this.getMarker(id);

        if (marker) {
            this._itemVisibility(marker, state);
        }

        return this;
    },

    toggleAllMarkers: function(state) {
        for (var key in this._markers) {
            this.toggleMarker(key, state);
        }

        return this;
    },

    getShape: function(id) {
        return this.isMapEnabled() ? this._shapes[id] : undefined;
    },

    hasShape: function(id) {
        return id in this._shapes;
    },

    addShape: function(id, options) {
        Assert.that(this.isMapEnabled(), 'Map canvas is disabled');
        Assert.not(Object.isEmpty(id), 'Shape id cannot be empty');
        Assert.not(this.hasShape(id), 'Shape "${id}" is already registered', {id: id});

        options = $.extend({
            position: {lat: 0, lng: 0},
            visible: true
        }, options || {});

        var shapeType = options.shape || '';
        var shape;

        switch (shapeType.toLowerCase()) {
            case 'circle':
                shape = __circleShape(options);
                break;
            default:
                throw new Error('Shape has unknown type "${shape}"'.template({
                    shape: shapeType
                }));
        }

        this._itemVisibility(shape, options.visible);
        this._itemExtraData(shape, options.extraData || {});
        this._itemExtraId(shape, id);

        this._shapes[id] = shape;
        return shape;
    },

    removeShape: function(id) {
        Assert.that(this.isMapEnabled(), 'Map canvas is disabled');
        Assert.not(Object.isEmpty(id), 'Shape id cannot be empty');
        Assert.that(this.hasShape(id), 'Shape "${id}" is not registered', {id: id});

        var shape = this._shapes[id];

        this._itemExtraId(shape, null);
        delete this._shapes[id];

        shape.remove();
        return shape;
    },

    updateShape: function(id, options) {
        Assert.that(this.isMapEnabled(), 'Map canvas is disabled');
        Assert.not(Object.isEmpty(id), 'Shape id cannot be empty');
        Assert.that(this.hasShape(id), 'Shape "${id}" is not registered', {id: id});

        options = options || {};

        var shape = this._shapes[id];

        this._itemVisibility(shape, options.visible);
        this._itemExtraData(shape, options.extraData);

        if (options.position) {
            shape.setLatLng([options.position.lat, options.position.lng]);
        }

        if (options.radius) {
            shape.setRadius(options.radius);
        }

        return this;
    },

    shapes: function(query) {
        return this._filterItems(Object.values(this._shapes), query);
    },

    shapeIds: function(query) {
        return this._itemExtraIds(this.shapes(query));
    },

    autoResize: function() {
        if (this.isMapEnabled()) {
            this._map.invalidateSize();
        }

        return this;
    }
});

}(jQuery, L));
