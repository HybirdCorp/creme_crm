/* globals QUnitGeolocationMixin */
(function($, QUnit) {
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
});

QUnit.test('creme.geolocation.LeafletMapController.bind', function(assert) {
    var controller = new creme.geolocation.LeafletMapController();
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    controller.on('status-enabled', function() {
        equal(true, controller.isBound());
        equal(true, controller.isEnabled());

        equal(true, controller.isMapEnabled());
        equal(true, controller.isGeocoderEnabled());

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

}(jQuery, QUnit));
