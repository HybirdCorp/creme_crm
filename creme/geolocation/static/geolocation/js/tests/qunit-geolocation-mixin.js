(function($) {
"use strict";

var MockGoogleGeocoder = creme.component.Component.sub({
    _init_: function() {
        this.responses = {};
    },

    mockUpdateResponses: function(reponses) {
        $.extend(true, this.responses, reponses || {});
    },

    mockPartialResponse: function(position) {
        return {
            geometry: {
                location: position
            },
            partial_match: true,
            address_components: []
        };
    },

    mockResponse: function(position) {
        return {
            geometry: {
                location: position
            },
            partial_match: false,
            address_components: []
        };
    },

    geocode: function(data, cb) {
        data = data || {};

        var response = this.responses[data.address];
        var status = google.maps.GeocoderStatus.OK;

        if (Object.isNone(response)) {
            status = google.maps.GeocoderStatus.ZERO_RESULT;
            response = [];
        }

        cb(response, status);
    }
});

var MockNominatimGeocoder = creme.component.Component.sub({
    _init_: function() {
        this.responses = {};
    },

    mockUpdateResponses: function(reponses) {
        $.extend(true, this.responses, reponses || {});
    },

    mockPartialResponse: function(position) {
        return {
            position: position,
            status: creme.geolocation.LocationStatus.PARTIAL
        };
    },

    mockResponse: function(position) {
        return {
            position: position,
            status: creme.geolocation.LocationStatus.COMPLETE
        };
    },

    search: function(content) {
        var self = this;

        return new creme.component.Action(function() {
            var candidates = self.responses[content] || [];

            if (Object.isEmpty(candidates)) {
                this.fail('No location');
            } else {
                this.done(candidates[0].position, candidates[0].status, candidates);
            }
        });
    }
});

window.QUnitGeolocationMixin = {
    beforeEach: function() {
        var backend = this.backend;
        var nominatimResponses = this._mockNominatimResponses = {
            'marseille': [
                {lat: "42", lon: "12"},
                {lat: "42", lon: "5.5"}
            ],
            'marseille 13015': [
                {lat: "42", lon: "12"},
                {lat: "42", lon: "12.5"}
            ],
            '13013 Marseille': [
                {lat: "43.178801", lon: "4.5048807"}
            ],
            '319 Rue Saint-Pierre, 13005 Marseille': [
                {lat: "43.291628", lon: "5.4030217"}
            ]
        };

        this.setMockBackendGET({
            'mock/nominatim/search': function(url, data, options) {
                return backend.responseJSON(200, nominatimResponses[data.q] || []);
            }
        });

        this.mockGoogleGeocoder = this.createMockGoogleGeocoder();
        this.mockOSMGeocoder = this.createMockOSMGeocoder();
    },

    setMockNominatimResponses: function(responses) {
        this._mockNominatimResponses = $.extend(this._mockNominatimResponses || {}, responses);
    },

    createMockOSMGeocoder: function() {
        var geocoder = new MockNominatimGeocoder();

        geocoder.mockUpdateResponses({
            'marseille': [
                geocoder.mockPartialResponse({lat: 42, lng: 12})
            ],
            'marseille 13015': [
                geocoder.mockResponse({lat: 42, lng: 12}),
                geocoder.mockResponse({lat: 42, lng: 12.5})
            ],
            '13013 Marseille': [
                geocoder.mockResponse({lat: 43.178801, lng: 4.5048807})
            ],
            '319 Rue Saint-Pierre, 13005 Marseille': [
                geocoder.mockResponse({lat: 43.291628, lng: 5.4030217})
            ]
        });

        return geocoder;
    },

    createMockGoogleGeocoder: function() {
        var geocoder = new MockGoogleGeocoder();

        geocoder.mockUpdateResponses({
            'marseille': [
                geocoder.mockPartialResponse({lat: 42, lng: 12})
            ],
            'marseille 13015': [
                geocoder.mockResponse({lat: 42, lng: 12}),
                geocoder.mockResponse({lat: 42, lng: 12.5})
            ],
            '13013 Marseille': [
                geocoder.mockResponse({lat: 43.178801, lng: 4.5048807})
            ],
            '319 Rue Saint-Pierre, 13005 Marseille': [
                geocoder.mockResponse({lat: 43.291628, lng: 5.4030217})
            ]
        });

        return geocoder;
    },

    createMapHtml: function(options) {
        options = $.extend({
            width: 100,
            height: 100
        }, options || options);

        return '<div style="width: ${width}px; height: ${height}px;"></div>'.format(options);
    },

    triggerMarkerClick: function(marker) {
        if (marker instanceof google.maps.Marker) {
            google.maps.event.trigger(marker, 'click');
        } else {
            marker.fire('click');
        }
    },

    triggerMarkerDragNDrop: function(marker, position) {
        if (marker instanceof google.maps.Marker) {
            google.maps.event.trigger(marker, 'dragstart');
            marker.setPosition(position);
            google.maps.event.trigger(marker, 'dragend');
        } else {
            marker.fire('dragstart');
            marker.setLatLng([position.lat, position.lng]);
            marker.fire('dragend');
        }
    },

    assertMarkerProperties: function(marker, expected) {
        this.assert.equal(false, Object.isNone(marker));

        if (Object.isNone(marker) === false) {
            this.assert.equal(expected.visible, marker.visible, 'is marker visible');
            this.assert.equal(expected.title, marker.title, 'marker title');
            this.assert.equal(expected.id, marker.id);
            this.assert.deepEqual(expected.position, marker.position);
            this.assert.deepEqual(expected.extraData, marker.extraData || {});
        }
    },

    assertCircleShape: function(shape, expected) {
        if (shape instanceof google.maps.Circle) {
            this.assertGoogleCircleShape(shape, expected);
        } else {
            this.assertLeafletCircleShape(shape, expected);
        }
    },

    assertLeafletCircleShape: function(shape, expected) {
        this.assert.equal(false, Object.isNone(shape));

        if (Object.isNone(shape) === false) {
            this.assert.equal(expected.visible, $(shape.getElement()).is(':not(.leaflet-hidden)'), 'is shape visible');
            this.assert.equal(expected.radius, shape.getRadius());
            this.assert.deepEqual(expected.position, {
                lat: shape.getLatLng().lat,
                lng: shape.getLatLng().lng
            });
            this.assert.deepEqual({
                id: expected.id,
                extraData: expected.extraData || {}
            }, shape.__extra);
        }
    },

    assertGoogleMarker: function(marker, expected) {
        this.assert.equal(false, Object.isNone(marker));

        if (Object.isNone(marker) === false) {
            this.assert.equal(expected.visible, marker.getVisible(), 'is marker visible');
            this.assert.equal(expected.title, marker.getTitle(), 'marker title');
            this.assert.deepEqual(new google.maps.LatLng(expected.position), marker.getPosition());
            this.assert.deepEqual({
                id: expected.id,
                extraData: expected.extraData || {}
            }, marker.__extra);
        }
    },

    assertGoogleCircleShape: function(shape, expected) {
        this.assert.equal(false, Object.isNone(shape));

        if (Object.isNone(shape) === false) {
            this.assert.equal(expected.visible, shape.getVisible(), 'is shape visible');
            this.assert.equal(expected.radius, shape.getRadius(), 'shape radius');
            this.assert.deepEqual(new google.maps.LatLng(expected.position), shape.getCenter());
            this.assert.deepEqual({
                id: expected.id,
                extraData: expected.extraData || {}
            }, shape.__extra);
        }
    },

    runTestOnGeomapReady: function(controller, element, callback) {
        this.bindTestOn(controller, 'status-enabled', callback, [controller]);
        controller.bind(element);
    }
};

}(jQuery));
