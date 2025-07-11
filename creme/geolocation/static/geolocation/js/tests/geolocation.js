/* globals QUnitGeolocationMixin */
(function($, QUnit) {
"use strict";

QUnit.module("creme.geolocation", new QUnitMixin(QUnitEventMixin,
                                                 QUnitAjaxMixin,
                                                 QUnitGeolocationMixin, {
}));

QUnit.test('creme.geolocation.Location (defaults)', function(assert) {
    var location = new creme.geolocation.Location();
    assert.equal(undefined, location.id());
    assert.equal('', location.content());
    assert.equal('', location.title());
    assert.equal(undefined, location.owner());
    assert.equal(undefined, location.url());

    assert.equal(false, location.visible());
    assert.equal(null, location.position());
    assert.equal(false, location.hasPosition());

    assert.equal(creme.geolocation.LocationStatus.UNDEFINED, location.status());
    assert.equal(false, location.isComplete());
    assert.equal(false, location.isPartial());
    assert.equal(false, location.isManual());

    assert.equal(gettext("Not localized"), location.statusLabel());
    assert.equal('', location.positionLabel());
    assert.equal('', location.markerLabel());
});

QUnit.test('creme.geolocation.Location (getters)', function(assert) {
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

    assert.equal('A', location.id());
    assert.equal('319 Rue Saint-Pierre, 13005 Marseille', location.content());
    assert.equal('Address A', location.title());
    assert.equal('joe', location.owner());
    assert.equal('mock/address/Address_A', location.url());

    assert.equal(true, location.visible());
    assert.deepEqual({lat: 43.45581, lng: 5.544}, location.position());
    assert.equal(true, location.hasPosition());

    assert.equal(creme.geolocation.LocationStatus.PARTIAL, location.status());
    assert.equal(false, location.isComplete());
    assert.equal(true, location.isPartial());
    assert.equal(false, location.isManual());

    assert.equal(gettext("Partially matching location"), location.statusLabel());
    assert.equal('43.455810, 5.544000', location.positionLabel());
    assert.equal('joe\n319 Rue Saint-Pierre, 13005 Marseille\n(Address A)', location.markerLabel());
});

QUnit.test('creme.geolocation.Location (copy)', function(assert) {
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

    assert.deepEqual(copy, location);
});

QUnit.test('creme.geolocation.Location (position)', function(assert) {
    var location = new creme.geolocation.Location({
        position: {lat: 43, lng: 5}
    });

    assert.equal(true, location.hasPosition());
    assert.deepEqual({lat: 43, lng: 5}, location.position());

    location = new creme.geolocation.Location({
        latitude: 42, longitude: 6
    });

    assert.equal(true, location.hasPosition());
    assert.deepEqual({lat: 42, lng: 6}, location.position());

    location = new creme.geolocation.Location({
        latitude: 42,
        longitude: 6,
        position: {lat: 43, lng: 5}
    });

    assert.equal(true, location.hasPosition());
    assert.deepEqual({lat: 42, lng: 6}, location.position());
});

QUnit.test('creme.geolocation.Location (status)', function(assert) {
    var location = new creme.geolocation.Location({
        status: creme.geolocation.LocationStatus.COMPLETE
    });

    assert.equal(creme.geolocation.LocationStatus.COMPLETE, location.status());
    assert.equal(true, location.isComplete());
    assert.equal(false, location.isPartial());
    assert.equal(false, location.isManual());
    assert.equal('', location.statusLabel());

    location = new creme.geolocation.Location({
        status: creme.geolocation.LocationStatus.PARTIAL
    });

    assert.equal(creme.geolocation.LocationStatus.PARTIAL, location.status());
    assert.equal(false, location.isComplete());
    assert.equal(true, location.isPartial());
    assert.equal(false, location.isManual());
    assert.equal(gettext("Partially matching location"), location.statusLabel());

    location.status(creme.geolocation.LocationStatus.MANUAL);

    assert.equal(creme.geolocation.LocationStatus.MANUAL, location.status());
    assert.equal(false, location.isComplete());
    assert.equal(false, location.isPartial());
    assert.equal(true, location.isManual());
    assert.equal(gettext("Manual location"), location.statusLabel());
});

QUnit.test('creme.geolocation.GeoMapController (base class)', function(assert) {
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());
    var controller = new creme.geolocation.GeoMapController();

    assert.equal(controller.element(), undefined);
    assert.equal(controller.isBound(), false);
    assert.equal(controller.isGeocoderAllowed(), true);
    assert.equal(controller.isMapEnabled(), false);
    assert.equal(controller.isGeocoderEnabled(), false);

    this.assertRaises(function() {
        controller.bind(element);
    }, Error, "Error: Not implemented");

    this.assertRaises(function() {
        controller.unbind(element);
    }, Error, "Error: Not implemented");

    this.assertRaises(function() {
        controller.addMarker('a', {});
    }, Error, "Error: Not implemented");

    assert.equal(controller.hasMarker('a'), false);
    assert.deepEqual(controller, controller.removeMarker('a'));
    assert.deepEqual(controller, controller.removeAllMarkers());
    assert.deepEqual(controller, controller.updateMarker('a', {}));
    assert.deepEqual(controller, controller.toggleMarker('a', {}));
    assert.deepEqual(controller, controller.toggleAllMarkers('a', {}));

    this.assertRaises(function() {
        controller.getMarker('a');
    }, Error, "Error: Not implemented");

    this.assertRaises(function() {
        controller.getMarkerProperties('a');
    }, Error, "Error: Not implemented");

    assert.deepEqual(controller.markers(), []);
    assert.deepEqual(controller.markerIds(), []);

    this.assertRaises(function() {
        controller.addShape('a', {});
    }, Error, "Error: Not implemented");

    this.assertRaises(function() {
        controller.getShape('a');
    }, Error, "Error: Not implemented");

    assert.equal(controller.hasShape('a'), false);
    assert.deepEqual(controller, controller.removeShape('a'));
    assert.deepEqual(controller, controller.removeAllShapes());
    assert.deepEqual(controller, controller.updateShape('a', {}));

    assert.deepEqual(controller.shapes(), []);
    assert.deepEqual(controller.shapeIds(), []);

    assert.deepEqual(controller, controller.autoResize());

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

        assert.deepEqual(this.mockListenerCalls('any'), []);
        assert.deepEqual(this.mockListenerJQueryCalls('geomap-any'), []);

        var listener = this.mockListener('any');
        element.on('geomap-any', this.mockListener('geomap-any'));
        controller.on('any', listener);

        controller.trigger('any', {a: 12});

        assert.deepEqual(this.mockListenerCalls('any'), [['any', {a: 12}]]);
        assert.deepEqual(this.mockListenerJQueryCalls('geomap-any'), [
            ['geomap-any', [controller, {a: 12}]]
        ]);

        controller.off('any', listener);

        controller.trigger('any', {b: 7});

        assert.deepEqual(this.mockListenerCalls('any'), [['any', {a: 12}]]);
        assert.deepEqual(this.mockListenerJQueryCalls('geomap-any'), [
            ['geomap-any', [controller, {a: 12}]],
            ['geomap-any', [controller, {b: 7}]]
        ]);

        controller.one('any', listener);
        controller.trigger('any', {c: 8});
        controller.trigger('any', {d: 9});

        assert.deepEqual(this.mockListenerCalls('any'), [
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
        assert.equal(false, controller.isGeocoderAllowed());
        assert.equal(false, controller.isGeocoderEnabled());

        controller.enableGeocoder();

        assert.equal(false, controller.isGeocoderEnabled());
    });
});

QUnit.parametrize('creme.geolocation.GeoMapController.enableGeocoder (already enabled)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(controller, assert) {
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        assert.equal(true, controller.isGeocoderAllowed());
        assert.equal(true, controller.isGeocoderEnabled());

        // do nothing
        controller.enableGeocoder();
    });
});

}(jQuery, QUnit));
