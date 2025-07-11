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

    assert.equal(12, controller.options().defaultZoomValue);
    assert.equal(48, controller.options().defaultLat);
    assert.equal(2, controller.options().defaultLn);
    assert.equal(4, controller.options().defaultLargeZoom);
    assert.equal(18, controller.options().maxZoom);
    assert.equal(1, controller.options().minZoom);
    assert.equal('https://nominatim.openstreetmap.org/search', controller.options().nominatimUrl);
    assert.equal('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', controller.options().tileMapUrl);
    assert.equal('&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
          controller.options().tileMapAttribution);

    assert.equal(true, controller.isGeocoderAllowed());

    assert.equal(false, controller.isBound());
    assert.equal(false, controller.isEnabled());

    assert.equal(false, controller.isMapEnabled());
    assert.equal(false, controller.isGeocoderEnabled());

    assert.equal(undefined, controller.map());
    assert.equal(undefined, controller.geocoder());

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

    assert.equal(20, controller.options().defaultZoomValue);
    assert.equal(47, controller.options().defaultLat);
    assert.equal(4, controller.options().defaultLn);
    assert.equal(5, controller.options().defaultLargeZoom);
    assert.equal(12, controller.options().maxZoom);
    assert.equal(1, controller.options().minZoom);
    assert.equal('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', controller.options().tileMapUrl);
    assert.equal('noone', controller.options().tileMapAttribution);
    assert.equal(false, controller.options().allowGeocoder);

    assert.equal(false, controller.isBound());
    assert.equal(false, controller.isEnabled());
    assert.equal(false, controller.isGeocoderAllowed());

    assert.equal(false, controller.isMapEnabled());
    assert.equal(false, controller.isGeocoderEnabled());

    assert.equal(undefined, controller.map());
    assert.equal(undefined, controller.geocoder());
});

QUnit.test('creme.geolocation.LeafletMapController.bind', function(assert) {
    var controller = new creme.geolocation.LeafletMapController();
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());
    var done = assert.async();

    controller.on('status-enabled', function() {
        assert.equal(true, controller.isBound());
        assert.equal(true, controller.isEnabled());

        assert.equal(true, controller.isMapEnabled());
        assert.equal(true, controller.isGeocoderEnabled());
        assert.deepEqual(controller.geocoder(), new creme.geolocation.NominatimGeocoder({
            url: controller.options().nominatimUrl
        }));
        done();
    });

    setTimeout(function() {
        controller.bind(element);
    }, 0);
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
    var done = assert.async();

    controller.on('status-enabled', function() {
        assert.equal(true, controller.isBound());
        assert.equal(true, controller.isEnabled());

        assert.equal(true, controller.isMapEnabled());
        assert.equal(true, controller.isGeocoderEnabled());

        controller.unbind();

        assert.equal(false, controller.isBound());
        assert.equal(false, controller.isEnabled());

        assert.equal(false, controller.isMapEnabled());

        assert.equal(undefined, controller.map());
        done();
    });

    setTimeout(function() {
        controller.bind(element);
    }, 0);
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

    assert.timeout(500);
    var done = assert.async();

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

                assert.deepEqual([
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

                assert.deepEqual(expectedIcon, marker.getIcon());

                done();
            }
        });
    });
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
        assert.equal(true, controller.isEnabled());

        assert.equal(false, controller.hasMarker('A'));
        assert.equal(undefined, controller.getMarker('A'));

        controller.addMarker('A', {
            icon: 'default',
            position: {lat: 43, lng: 5},
            extraData: {address: 'Marseille'}
        });

        var marker = controller.getMarker('A');
        assert.equal(true, controller.hasMarker('A'));
        assert.equal(false, Object.isNone(marker));
        assert.deepEqual(defaultIcon, marker.getIcon());

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
        assert.equal(true, controller.hasMarker('A'));
        assert.equal(false, Object.isNone(marker));
        assert.deepEqual({
            id: 'A',
            extraData: {address: 'Marseille 13006'}
        }, marker.__extra);
        assert.deepEqual(expectedIcon, marker.getIcon());

        controller.updateMarker('A', {
            icon: 'circle'
        });

        marker = controller.getMarker('A');
        assert.deepEqual({
            id: 'A',
            extraData: {address: 'Marseille 13006'}
        }, marker.__extra);
        assert.deepEqual(leaflet.divIcon('◯'), marker.getIcon());

        controller.updateMarker('A', {
            icon: 'default'
        });

        marker = controller.getMarker('A');
        assert.deepEqual({
            id: 'A',
            extraData: {address: 'Marseille 13006'}
        }, marker.__extra);
        assert.deepEqual(defaultIcon, marker.getIcon());
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

        assert.equal(1, controller.shapes().length);
        assert.equal(0, controller.shapes({visible: false}).length);
        assert.deepEqual(['A'], controller.shapeIds());
        assert.deepEqual([], controller.shapeIds({visible: false}));

        controller.removeShape('A');

        assert.equal(undefined, controller.getShape('A'));

        assert.equal(0, controller.shapes().length);
        assert.equal(0, controller.shapes({visible: false}).length);
        assert.deepEqual([], controller.shapeIds());
        assert.deepEqual([], controller.shapeIds({visible: false}));
    });
});

}(jQuery, QUnit, L));
