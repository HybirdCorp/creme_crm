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

window.QUnitGeolocationMixin = {
    createMockGoogleGeocoder: function(responses) {
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

    assertGoogleMarker: function(marker, expected) {
        equal(false, Object.isNone(marker));

        if (Object.isNone(marker) === false) {
            equal(expected.visible, marker.getVisible(), 'is marker visible');
            equal(expected.title, marker.getTitle(), 'marker title');
            deepEqual(new google.maps.LatLng(expected.position), marker.getPosition());
            deepEqual({
                id: expected.id,
                extraData: expected.extraData || {}
            }, marker.__extra);
        }
    },

    assertGoogleShape: function(shape, expected) {
        equal(false, Object.isNone(shape));

        if (Object.isNone(shape) === false) {
            equal(expected.visible, shape.getVisible(), 'is shape visible');
            equal(expected.radius, shape.getRadius(), 'shape radius');
            deepEqual(new google.maps.LatLng(expected.position), shape.getCenter());
            deepEqual({
                id: expected.id,
                extraData: expected.extraData || {}
            }, shape.__extra);
        }
    }
};

}(jQuery));
