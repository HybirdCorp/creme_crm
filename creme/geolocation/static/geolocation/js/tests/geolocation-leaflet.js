/* globals QUnitGeolocationMixin creme_media_url L */
(function($, QUnit, leaflet) {
"use strict";

QUnit.module("creme.geolocation.leaflet", new QUnitMixin(QUnitEventMixin,
                                                         QUnitAjaxMixin,
                                                         QUnitGeolocationMixin, {
    beforeEach: function() {
        this.mockGeocoder = this.createMockOSMGeocoder();
    }
}));

QUnit.test('creme.geolocation.LeafletMapController (init, defaults)', function(assert) {
    var controller = new creme.geolocation.LeafletMapController();

    equal(12, controller.options().defaultZoomValue);
    equal(48, controller.options().defaultLat);
    equal(2, controller.options().defaultLn);
    equal(4, controller.options().defaultLargeZoom);
    equal(18, controller.options().maxZoom);
    equal(1, controller.options().minZoom);
    equal('https://nominatim.openstreetmap.org/search', controller.options().nominatimUrl);
    equal('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', controller.options().tileMapUrl);
    equal('&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
          controller.options().tileMapAttribution);

    equal(true, controller.isGeocoderAllowed());

    equal(false, controller.isBound());
    equal(false, controller.isEnabled());

    equal(false, controller.isMapEnabled());
    equal(false, controller.isGeocoderEnabled());

    equal(undefined, controller.map());
    equal(undefined, controller.geocoder());

    // not bound, no changes
    controller.adjustMapToShape('A');
    controller.adjustMap();
});

QUnit.test('creme.geolocation.LeafletMapController (init)', function(assert) {
    var controller = new creme.geolocation.LeafletMapController({
        defaultZoomValue: 20,
        defaultLat: 47,
        defaultLn: 4,
        defaultLargeZoom: 5,
        maxZoom: 12,
        tileMapAttribution: 'noone',
        allowGeocoder: false,
        apiVersion: '3'
    });

    equal(20, controller.options().defaultZoomValue);
    equal(47, controller.options().defaultLat);
    equal(4, controller.options().defaultLn);
    equal(5, controller.options().defaultLargeZoom);
    equal(12, controller.options().maxZoom);
    equal(1, controller.options().minZoom);
    equal('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', controller.options().tileMapUrl);
    equal('noone', controller.options().tileMapAttribution);
    equal(false, controller.options().allowGeocoder);

    equal(false, controller.isBound());
    equal(false, controller.isEnabled());
    equal(false, controller.isGeocoderAllowed());

    equal(false, controller.isMapEnabled());
    equal(false, controller.isGeocoderEnabled());

    equal(undefined, controller.map());
    equal(undefined, controller.geocoder());
});

QUnit.test('creme.geolocation.LeafletMapController.bind', function(assert) {
    var controller = new creme.geolocation.LeafletMapController();
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    controller.on('status-enabled', function() {
        equal(true, controller.isBound());
        equal(true, controller.isEnabled());

        equal(true, controller.isMapEnabled());
        equal(true, controller.isGeocoderEnabled());
        deepEqual(controller.geocoder(), new creme.geolocation.NominatimGeocoder({
            url: controller.options().nominatimUrl
        }));

        start();
    });

    setTimeout(function() {
        controller.bind(element);
    }, 0);

    stop(1);
});

QUnit.test('creme.geolocation.LeafletMapController.bind (already bound)', function(assert) {
    var controller = new creme.geolocation.LeafletMapController();
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    controller.bind(element);

    this.assertRaises(function() {
        controller.bind(element);
    }, Error, 'Error: GeoMapController is already bound');
});

QUnit.test('creme.geolocation.LeafletMapController.unbind', function(assert) {
    var controller = new creme.geolocation.LeafletMapController();
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    controller.on('status-enabled', function() {
        equal(true, controller.isBound());
        equal(true, controller.isEnabled());

        equal(true, controller.isMapEnabled());
        equal(true, controller.isGeocoderEnabled());

        controller.unbind();

        equal(false, controller.isBound());
        equal(false, controller.isEnabled());

        equal(false, controller.isMapEnabled());

        equal(undefined, controller.map());
        start();
    });

    setTimeout(function() {
        controller.bind(element);
    }, 0);

    stop(1);
});

QUnit.test('creme.geolocation.LeafletMapController.unbind (not bound)', function(assert) {
    var controller = new creme.geolocation.LeafletMapController();

    this.assertRaises(function() {
        controller.unbind();
    }, Error, 'Error: GeoMapController is not bound');
});

QUnit.parameterize('creme.geolocation.LeafletMapController.markLocation', [
    [{
        content: '319 Rue Saint-Pierre, 13005 Marseille'
    }, {
        title: 'fulbert\n319 Rue Saint-Pierre, 13005 Marseille\n(Address A)',
        iconUrl: creme_media_url('geolocation/images/marker-icon.png'),
        iconRetinaUrl: creme_media_url('geolocation/images/marker-icon-2x.png'),
        shadowUrl: creme_media_url('geolocation/images/marker-shadow.png'),
        position: {lat: 43.291628, lng: 5.4030217},
        status: creme.geolocation.LocationStatus.COMPLETE
    }],
    [{
        content: '319 Rue Saint-Pierre, 13005 Marseille',
        icon: creme_media_url('geolocation/images/marker-icon.png')
    }, {
        title: 'fulbert\n319 Rue Saint-Pierre, 13005 Marseille\n(Address A)',
        iconUrl: creme_media_url('geolocation/images/marker-icon.png'),
        iconRetinaUrl: creme_media_url('geolocation/images/marker-icon.png'),
        shadowUrl: '',
        position: {lat: 43.291628, lng: 5.4030217},
        status: creme.geolocation.LocationStatus.COMPLETE
    }],
    [{
        content: 'marseille',
        icon: 'geolocation/images/marker-icon.png'
    }, {
        title: 'fulbert\nmarseille\n(Address A)',
        iconUrl: creme_media_url('geolocation/images/marker-icon.png'),
        iconRetinaUrl: creme_media_url('geolocation/images/marker-icon.png'),
        shadowUrl: '',
        position: {lat: 42, lng: 12},
        status: creme.geolocation.LocationStatus.PARTIAL
    }]
], function(props, expected, assert) {
    var self = this;
    var controller = new creme.geolocation.LeafletMapController({
        nominatimUrl: 'mock/nominatim/search'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    controller.on('marker-move', this.mockListener('search-done'));

    this.runTestOnGeomapReady(controller, element, function() {
        controller.markLocation({
            location: {
                owner: 'fulbert',
                id: 'Address_A',
                title: 'Address A',
                content: props.content,
                icon: props.icon,
                extraData: {
                    isProspect: true
                }
            },
            extraData: {
                content: 'some custom data'
            }
        }, {
            done: function(event, position, status, data) {
                var marker = controller.getMarker('Address_A');
                var expectedIcon = leaflet.icon({
                    className: 'geolocation-leaflet-marker',
                    iconUrl: expected.iconUrl,
                    iconRetinaUrl: expected.iconRetinaUrl,
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [-7, -57],
                    shadowUrl: expected.shadowUrl,
                    shadowSize: [41, 41],
                    shadowAnchor: [12, 41]
                });

                deepEqual([
                    ['marker-move', marker, {
                        id: 'Address_A',
                        title: expected.title,
                        position: expected.position,
                        location: new creme.geolocation.Location({
                            owner: 'fulbert',
                            id: 'Address_A',
                            title: 'Address A',
                            content: props.content,
                            icon: props.icon,
                            extraData: {
                                isProspect: true
                            }
                        }),
                        icon: expectedIcon,
                        draggable: false,
                        visible: true,
                        status: expected.status,
                        extraData: {
                            content: 'some custom data'
                        },
                        searchData: data
                    }]
                ], self.mockListenerCalls('search-done'));

                deepEqual(expectedIcon, marker.getIcon());

                start();
            }
        });
    });

    stop(1);
});

QUnit.test('creme.geolocation.LeafletMapController.updateMarker', function(assert) {
    var controller = new creme.geolocation.LeafletMapController({
        nominatimUrl: 'mock/nominatim/search'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    var defaultIcon = leaflet.icon({
        className: 'geolocation-leaflet-marker',
        iconUrl: creme_media_url('geolocation/images/marker-icon.png'),
        iconRetinaUrl: creme_media_url('geolocation/images/marker-icon-2x.png'),
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [-7, -57],
        shadowUrl: creme_media_url('geolocation/images/marker-shadow.png'),
        shadowSize: [41, 41],
        shadowAnchor: [12, 41]
    });

    this.runTestOnGeomapReady(controller, element, function() {
        equal(true, controller.isEnabled());

        equal(false, controller.hasMarker('A'));
        equal(undefined, controller.getMarker('A'));

        controller.addMarker('A', {
            icon: 'default',
            position: {lat: 43, lng: 5},
            extraData: {address: 'Marseille'}
        });

        var marker = controller.getMarker('A');
        equal(true, controller.hasMarker('A'));
        equal(false, Object.isNone(marker));
        deepEqual(defaultIcon, marker.getIcon());

        controller.updateMarker('A', {
            icon: creme_media_url('geolocation/images/marker-icon.png'),
            position: {lat: 42, lng: 5.5},
            extraData: {address: 'Marseille 13006'}
        });

        var expectedIcon = leaflet.icon({
            className: 'geolocation-leaflet-marker',
            iconUrl: creme_media_url('geolocation/images/marker-icon.png'),
            iconRetinaUrl: creme_media_url('geolocation/images/marker-icon.png'),
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [-7, -57],
            shadowUrl: '',
            shadowSize: [41, 41],
            shadowAnchor: [12, 41]
        });

        marker = controller.getMarker('A');
        equal(true, controller.hasMarker('A'));
        equal(false, Object.isNone(marker));
        deepEqual({
            id: 'A',
            extraData: {address: 'Marseille 13006'}
        }, marker.__extra);
        deepEqual(expectedIcon, marker.getIcon());

        controller.updateMarker('A', {
            icon: 'circle'
        });

        marker = controller.getMarker('A');
        deepEqual({
            id: 'A',
            extraData: {address: 'Marseille 13006'}
        }, marker.__extra);
        deepEqual(leaflet.divIcon('◯'), marker.getIcon());

        controller.updateMarker('A', {
            icon: 'default'
        });

        marker = controller.getMarker('A');
        deepEqual({
            id: 'A',
            extraData: {address: 'Marseille 13006'}
        }, marker.__extra);
        deepEqual(defaultIcon, marker.getIcon());
    });
});

QUnit.test('creme.geolocation.LeafletMapController.addShape (unknown type)', function(assert) {
    var controller = new creme.geolocation.LeafletMapController();
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        this.assertRaises(function() {
            controller.addShape('A', {
                position: {lat: 43, lng: 5},
                radius: 5,
                shape: 'unknown'
            });
        }, Error, 'Error: Shape has unknown type "unknown"');
    });
});

QUnit.test('creme.geolocation.LeafletMapController.removeShape', function(assert) {
    var self = this;
    var controller = new creme.geolocation.LeafletMapController();
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        var shape = controller.addShape('A', {
            position: {lat: 43, lng: 5},
            radius: 5,
            shape: 'circle'
        });

        self.assertLeafletCircleShape(shape, {
            id: 'A',
            visible: true,
            radius: 5,
            position: {
                lat: 43, lng: 5
            }
        });

        equal(1, controller.shapes().length);
        equal(0, controller.shapes({visible: false}).length);
        deepEqual(['A'], controller.shapeIds());
        deepEqual([], controller.shapeIds({visible: false}));

        controller.removeShape('A');

        equal(undefined, controller.getShape('A'));

        equal(0, controller.shapes().length);
        equal(0, controller.shapes({visible: false}).length);
        deepEqual([], controller.shapeIds());
        deepEqual([], controller.shapeIds({visible: false}));
    });
});

}(jQuery, QUnit, L));
