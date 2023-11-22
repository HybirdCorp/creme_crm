/* globals QUnitGeolocationMixin */
(function($, QUnit) {
"use strict";

QUnit.module("creme.geolocation", new QUnitMixin(QUnitEventMixin,
                                                 QUnitAjaxMixin,
                                                 QUnitGeolocationMixin, {
}));

QUnit.test('creme.geolocation.Location (defaults)', function() {
    var location = new creme.geolocation.Location();
    equal(undefined, location.id());
    equal('', location.content());
    equal('', location.title());
    equal(undefined, location.owner());
    equal(undefined, location.url());

    equal(false, location.visible());
    equal(null, location.position());
    equal(false, location.hasPosition());

    equal(creme.geolocation.LocationStatus.UNDEFINED, location.status());
    equal(false, location.isComplete());
    equal(false, location.isPartial());
    equal(false, location.isManual());

    equal(gettext("Not localized"), location.statusLabel());
    equal('', location.positionLabel());
    equal('', location.markerLabel());
});

QUnit.test('creme.geolocation.Location (getters)', function() {
    var location = new creme.geolocation.Location({
        id: 'A',
        content: '319 Rue Saint-Pierre, 13005 Marseille',
        title: 'Address A',
        owner: 'joe',
        url: 'mock/address/Address_A',
        visible: true,
        status: creme.geolocation.LocationStatus.PARTIAL,
        position: {lat: 43.45581, lng: 5.544}
    });

    equal('A', location.id());
    equal('319 Rue Saint-Pierre, 13005 Marseille', location.content());
    equal('Address A', location.title());
    equal('joe', location.owner());
    equal('mock/address/Address_A', location.url());

    equal(true, location.visible());
    deepEqual({lat: 43.45581, lng: 5.544}, location.position());
    equal(true, location.hasPosition());

    equal(creme.geolocation.LocationStatus.PARTIAL, location.status());
    equal(false, location.isComplete());
    equal(true, location.isPartial());
    equal(false, location.isManual());

    equal(gettext("Partially matching location"), location.statusLabel());
    equal('43.455810, 5.544000', location.positionLabel());
    equal('joe\n319 Rue Saint-Pierre, 13005 Marseille\n(Address A)', location.markerLabel());
});

QUnit.test('creme.geolocation.Location (copy)', function() {
    var location = new creme.geolocation.Location({
        id: 'A',
        content: '319 Rue Saint-Pierre, 13005 Marseille',
        title: 'Address A',
        owner: 'joe',
        url: 'mock/address/Address_A',
        status: creme.geolocation.LocationStatus.COMPLETE,
        position: {lat: 43, lng: 5}
    });

    var copy = new creme.geolocation.Location(location);

    deepEqual(copy, location);
});

QUnit.test('creme.geolocation.Location (position)', function() {
    var location = new creme.geolocation.Location({
        position: {lat: 43, lng: 5}
    });

    equal(true, location.hasPosition());
    deepEqual({lat: 43, lng: 5}, location.position());

    location = new creme.geolocation.Location({
        latitude: 42, longitude: 6
    });

    equal(true, location.hasPosition());
    deepEqual({lat: 42, lng: 6}, location.position());

    location = new creme.geolocation.Location({
        latitude: 42,
        longitude: 6,
        position: {lat: 43, lng: 5}
    });

    equal(true, location.hasPosition());
    deepEqual({lat: 42, lng: 6}, location.position());
});

QUnit.test('creme.geolocation.Location (status)', function() {
    var location = new creme.geolocation.Location({
        status: creme.geolocation.LocationStatus.COMPLETE
    });

    equal(creme.geolocation.LocationStatus.COMPLETE, location.status());
    equal(true, location.isComplete());
    equal(false, location.isPartial());
    equal(false, location.isManual());
    equal('', location.statusLabel());

    location = new creme.geolocation.Location({
        status: creme.geolocation.LocationStatus.PARTIAL
    });

    equal(creme.geolocation.LocationStatus.PARTIAL, location.status());
    equal(false, location.isComplete());
    equal(true, location.isPartial());
    equal(false, location.isManual());
    equal(gettext("Partially matching location"), location.statusLabel());

    location.status(creme.geolocation.LocationStatus.MANUAL);

    equal(creme.geolocation.LocationStatus.MANUAL, location.status());
    equal(false, location.isComplete());
    equal(false, location.isPartial());
    equal(true, location.isManual());
    equal(gettext("Manual location"), location.statusLabel());
});

QUnit.test('creme.geolocation.GeoMapController (base class)', function(assert) {
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());
    var controller = new creme.geolocation.GeoMapController();

    equal(controller.element(), undefined);
    equal(controller.isBound(), false);
    equal(controller.isGeocoderAllowed(), true);
    equal(controller.isMapEnabled(), false);
    equal(controller.isGeocoderEnabled(), false);

    this.assertRaises(function() {
        controller.bind(element);
    }, Error, "Error: Not implemented");

    this.assertRaises(function() {
        controller.unbind(element);
    }, Error, "Error: Not implemented");

    this.assertRaises(function() {
        controller.addMarker('a', {});
    }, Error, "Error: Not implemented");

    equal(controller.hasMarker('a'), false);
    deepEqual(controller, controller.removeMarker('a'));
    deepEqual(controller, controller.removeAllMarkers());
    deepEqual(controller, controller.updateMarker('a', {}));
    deepEqual(controller, controller.toggleMarker('a', {}));
    deepEqual(controller, controller.toggleAllMarkers('a', {}));

    this.assertRaises(function() {
        controller.getMarker('a');
    }, Error, "Error: Not implemented");

    this.assertRaises(function() {
        controller.getMarkerProperties('a');
    }, Error, "Error: Not implemented");

    deepEqual(controller.markers(), []);
    deepEqual(controller.markerIds(), []);

    this.assertRaises(function() {
        controller.addShape('a', {});
    }, Error, "Error: Not implemented");

    this.assertRaises(function() {
        controller.getShape('a');
    }, Error, "Error: Not implemented");

    equal(controller.hasShape('a'), false);
    deepEqual(controller, controller.removeShape('a'));
    deepEqual(controller, controller.removeAllShapes());
    deepEqual(controller, controller.updateShape('a', {}));

    deepEqual(controller.shapes(), []);
    deepEqual(controller.shapeIds(), []);

    deepEqual(controller, controller.autoResize());

    this.assertRaises(function() {
        controller.adjustMap('a');
    }, Error, "Error: Not implemented");

    this.assertRaises(function() {
        controller.adjustMapToShape('a');
    }, Error, "Error: Not implemented");
});

QUnit.parameterize('creme.geolocation.GeoMapController (events)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(controller, assert) {
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        controller.trigger('any', {a: 12});

        deepEqual(this.mockListenerCalls('any'), []);
        deepEqual(this.mockListenerJQueryCalls('geomap-any'), []);

        var listener = this.mockListener('any');
        element.on('geomap-any', this.mockListener('geomap-any'));
        controller.on('any', listener);

        controller.trigger('any', {a: 12});

        deepEqual(this.mockListenerCalls('any'), [['any', {a: 12}]]);
        deepEqual(this.mockListenerJQueryCalls('geomap-any'), [
            ['geomap-any', [controller, {a: 12}]]
        ]);

        controller.off('any', listener);

        controller.trigger('any', {b: 7});

        deepEqual(this.mockListenerCalls('any'), [['any', {a: 12}]]);
        deepEqual(this.mockListenerJQueryCalls('geomap-any'), [
            ['geomap-any', [controller, {a: 12}]],
            ['geomap-any', [controller, {b: 7}]]
        ]);

        controller.one('any', listener);
        controller.trigger('any', {c: 8});
        controller.trigger('any', {d: 9});

        deepEqual(this.mockListenerCalls('any'), [
            ['any', {a: 12}],
            ['any', {c: 8}]
        ]);
    });
});

QUnit.parametrize('creme.geolocation.GeoMapController.enableGeocoder (not allowed)', [
    [new creme.geolocation.GoogleMapController({
        allowGeocoder: false
    })],
    [new creme.geolocation.LeafletMapController({
        allowGeocoder: false
    })]
], function(controller, assert) {
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        equal(false, controller.isGeocoderAllowed());
        equal(false, controller.isGeocoderEnabled());

        controller.enableGeocoder();

        equal(false, controller.isGeocoderEnabled());
    });
});

QUnit.parametrize('creme.geolocation.GeoMapController.enableGeocoder (already enabled)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(controller, assert) {
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        equal(true, controller.isGeocoderAllowed());
        equal(true, controller.isGeocoderEnabled());

        // do nothing
        controller.enableGeocoder();
    });
});

}(jQuery, QUnit));
