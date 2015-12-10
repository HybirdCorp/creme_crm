/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2014-2015  Hybird

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


creme.geolocation = creme.geolocation || {};

__googleAPI_loader_status = false;
__googleAPI_loader_callbacks = [];

initialize = function() {
    __googleAPI_loader_status = 'done';

    var callbacks = __googleAPI_loader_callbacks.splice(0, __googleAPI_loader_callbacks.length);

    callbacks.forEach(function(callback) {
        try {
            callback();
        } catch(e) {
            console.warn(e);
        }
    });
}

creme.geolocation.ready = function(callback) {
    $(document).ready(function() {
        if (window['google'] !== undefined || __googleAPI_loader_status === 'done') {
            return callback();
        }

        __googleAPI_loader_callbacks.push(callback);

        if (!__googleAPI_loader_status)
        {
            __googleAPI_loader_status = 'loading';
            var script = document.createElement('script');

            script.type = 'text/javascript';
            script.src = 'https://maps.googleapis.com/maps/api/js?v=3.exp&language=fr&callback=initialize';

            document.body.appendChild(script);
        }
    });
};

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
                         {hue: "#94c6db"},
                         {weight: 2}
                    ]
                },
                {
                    featureType: "road",
                    elementType: "geometry",
                    stylers: [
                      { visibility: "simplified" }
                    ]
                }
            ]
        }
    ],

    _init_: function (map_container)
    {
        this.defaultZoomValue = 12;
        this.defaultLat = 48;
        this.defaultLn = 2;
        this.defaultLargeZoom = 4;

        this._events = new creme.component.EventHandler();

        this.geocoder = new google.maps.Geocoder();
        this.marker_manager = new creme.geolocation.GoogleMapMarkerManager(this);
        this.shape_manager = new creme.geolocation.GoogleMapShapeRegistry(this);

        var mapStyleIds = this.MAPSTYLES.map(function(style) {return style.id})
                                        .concat(google.maps.MapTypeId.SATELLITE);

        var map = this.map = new google.maps.Map(map_container, {
                                                     zoom: this.defaultZoomValue,
                                                     mapTypeControlOptions: {
                                                         mapTypeIds: mapStyleIds
                                                     }
                                                 });

        this.MAPSTYLES.forEach(function(style) {
            map.mapTypes.set(style.id, new google.maps.StyledMapType(style.style, {name: style.label}));
        });

        map.setMapTypeId(mapStyleIds[0]);

        this.adjustMap();
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

    adjustMap: function()
    {
        var n_markers = this.marker_manager.count(true);

        if (n_markers == 0) {
            var default_location = new google.maps.LatLng(this.defaultLat, this.defaultLn);
            this.map.setCenter(default_location);
            this.map.setZoom(this.defaultLargeZoom);
        } else {
            var boundbox = this.marker_manager.getBoundBox();
            this.map.setCenter(boundbox.getCenter());
            if (n_markers == 1) {
                this.map.setZoom(this.defaultZoomValue);
            } else {
                this.map.fitBounds(boundbox);
            }
        }
    },

    _isPartialMatch: function(results)
    {
        if (results.length > 1)
            return true;

        var match = results[0]

        if (match.partial_match === false)
            return false;

        return match.address_components.length < 7;
    },

    geocode: function(options)
    {
        var marker_manager = this.marker_manager;
        var saveLocation = this.saveLocation.bind(this);
        var isPartialMatch = this._isPartialMatch.bind(this);

        this.geocoder.geocode(options.data, function(results, status) {
            var address = options.address;

            if (status === google.maps.GeocoderStatus.OK)
            {
                var marker   = marker_manager.get(address.id);
                var result   = results[0];

                var position = result.geometry.location;
                var isPartial = isPartialMatch(results);
                var location_status = creme.geolocation.LocationStatus.COMPLETE;

                if (isPartial) {
                    location_status = creme.geolocation.LocationStatus.PARTIAL;
                }

                if (!marker) {
                    var marker = marker_manager.Marker({
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
    },

    saveLocation: function (marker, options, geocoded, status)
    {
        var self = this;

        creme.ajax.query('/geolocation/set_address_info/%s'.format(options.address.id), {}, {
                             latitude:  marker.position.lat(),
                             longitude: marker.position.lng(),
                             geocoded:  geocoded,
                             status:    status
                         })
                  .onFail(function() {
                              marker.setPosition(options.initial_position);
                          })
                  .onDone(function() {
                              self._events.trigger('save-location', [options.address, marker, status])
                          })
                  .post();
    },

    findLocation: function (address, options)
    {
        this.geocode({
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

    isAddressLocated: function(address) {
        return address && !Object.isNone(address.latitude) && !Object.isNone(address.longitude);
    },

    resize: function() {
        google.maps.event.trigger(this.map, 'resize');
    }
});

creme.geolocation.GoogleMapShapeRegistry = creme.component.Component.sub({
    _init_: function (controller) {
        this._controller = controller;
        this._shapes = {};
    },

    register: function(shape_id, shape) {
        if (shape_id in this._shapes){
            throw new Error('Shape "' + shape_id + '" is already registered');
        }
        this._shapes[shape_id] = shape;
    },

    unregister: function(shape_id) {
        if (shape_id in this._shapes){
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
        var shape = this.get(shape_id);
        this._controller.map.setCenter(shape.getCenter());
        this._controller.map.fitBounds(shape.getBounds());
    }
});

creme.geolocation.GoogleMapMarkerManager = creme.component.Component.sub({
    _init_: function (controller) {
        this._controller = controller;
        this._markers = {};
    },

    markers: function(visible) {
        var markers = Object.values(this._markers);

        if (visible === undefined)
            return markers;

        return markers.filter(function(item) {return item.getVisible() === visible});
    },

    count: function(visible) {
        return this.markers(visible).length;
    },

    register: function(marker) {
        var id = marker.address.id
        if (id in this._markers){
            throw new Error('marker "' + id + '" is already registered');
        }
        this._markers[id] = marker;
    },

    Marker: function (options)
    {
        var options = $.extend({
                            map:       this._controller.map,
                            draggable: false,
                        }, options || {});

        var address = options.address;

        options.position = options.position || new google.maps.LatLng(address.latitude, address.longitude);
        options.title = '%s\n%s'.format(address.owner, address.title || address.content)

        var marker = new google.maps.Marker(options);
        this.register(marker);

        if (options.redirect)
        {
            google.maps.event.addListener(marker, 'click', function() {
                                  creme.utils.goTo(options.redirect);
                              });
        }

        if (options.draggable)
        {
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

    toggle: function(id, state)
    {
        var marker = this.get(id);

        if (marker) {
            marker.setVisible(state === undefined ? !marker.getVisible() : state);
            this._controller.adjustMap();
        }
    },

    hideAll: function() {
        for (key in this._markers) {
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

