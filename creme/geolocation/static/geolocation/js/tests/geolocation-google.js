/* globals QUnitGeolocationMixin */
(function($, QUnit) {
"use strict";

QUnit.module("creme.geolocation.google", new QUnitMixin(QUnitEventMixin,
                                                        QUnitAjaxMixin,
                                                        QUnitGeolocationMixin, {
    beforeEach: function() {
        this.mockGeocoder = this.createMockGoogleGeocoder();
    }
}));

QUnit.test('creme.geolocation.GoogleMapController (init, defaults)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController();

    equal(12, controller.options().defaultZoomValue);
    equal(48, controller.options().defaultLat);
    equal(2, controller.options().defaultLn);
    equal(4, controller.options().defaultLargeZoom);
    equal(undefined, controller.options().apiKey);
    equal('3.exp', controller.options().apiVersion);

    equal(true, controller.isGeocoderAllowed());

    equal(false, controller.isBound());
    equal(false, controller.isEnabled());

    equal(false, controller.isMapEnabled());
    equal(creme.geolocation.isGoogleAPIReady(), controller.isAPIReady());
    equal(false, controller.isGeocoderEnabled());

    equal(undefined, controller.map());
});

QUnit.test('creme.geolocation.GoogleMapController (init)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        defaultZoomValue: 20,
        defaultLat: 47,
        defaultLn: 4,
        defaultLargeZoom: 5,
        apiKey: 'mockit!',
        allowGeocoder: false,
        apiVersion: '3'
    });

    equal(20, controller.options().defaultZoomValue);
    equal(47, controller.options().defaultLat);
    equal(4, controller.options().defaultLn);
    equal(5, controller.options().defaultLargeZoom);
    equal('mockit!', controller.options().apiKey);
    equal('3', controller.options().apiVersion);
    equal(false, controller.options().allowGeocoder);

    equal(false, controller.isBound());
    equal(false, controller.isEnabled());
    equal(false, controller.isGeocoderAllowed());

    equal(false, controller.isMapEnabled());
    equal(creme.geolocation.isGoogleAPIReady(), controller.isAPIReady());
    equal(false, controller.isGeocoderEnabled());

    equal(undefined, controller.map());
});

QUnit.test('creme.geolocation.GoogleMapController.bind', function(assert) {
    var controller = new creme.geolocation.GoogleMapController();
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    controller.on('status-enabled', function() {
        equal(true, controller.isBound());
        equal(true, controller.isEnabled());

        equal(true, controller.isMapEnabled());
        equal(true, controller.isAPIReady());
        equal(true, controller.isGeocoderEnabled());
        start();
    });

    controller.bind(element);

    equal(true, controller.isBound());
    equal(false, controller.isEnabled());

    equal(false, controller.isMapEnabled());
    equal(creme.geolocation.isGoogleAPIReady(), controller.isAPIReady());
    equal(false, controller.isGeocoderEnabled());

    equal(undefined, controller.map());

    stop(1);
});

QUnit.test('creme.geolocation.GoogleMapController.bind (already bound)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController();
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    controller.bind(element);

    this.assertRaises(function() {
        controller.bind(element);
    }, Error, 'Error: GeoMapController is already bound');
});

QUnit.test('creme.geolocation.GoogleMapController.unbind', function(assert) {
    var controller = new creme.geolocation.GoogleMapController();
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    controller.on('status-enabled', function() {
        controller.unbind();
        equal(false, controller.isBound());
        equal(false, controller.isEnabled());

        equal(false, controller.isMapEnabled());
        equal(true, controller.isAPIReady());

        equal(undefined, controller.map());

        start();
    });

    controller.bind(element);
    stop(1);
});

QUnit.test('creme.geolocation.GoogleMapController.unbind (not bound)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController();

    this.assertRaises(function() {
        controller.unbind();
    }, Error, 'Error: GeoMapController is not bound');
});

QUnit.test('creme.geolocation.GoogleMapController.enableMap (not bound)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController();

    this.assertRaises(function() {
        controller.enableMap();
    }, Error, 'Error: Cannot enable map of an unbound controller');
});

QUnit.test('creme.geolocation.GoogleMapController.enableMap (already enabled)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController();
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        equal(true, controller.isMapEnabled());

        this.assertRaises(function() {
            controller.enableMap();
        }, Error, 'Error: Map canvas is already enabled');
    });
});

QUnit.test('creme.geolocation.GoogleMapController.searchQuery (partial)', function(assert) {
    var self = this;
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());
    var listeners = {
        cancel: this.mockListener('search-cancel'),
        done: this.mockListener('search-done'),
        fail: this.mockListener('search-fail')
    };

    this.runTestOnGeomapReady(controller, element, function() {
        controller._geocoder = self.mockGeocoder;

        var query = controller._searchLocationQuery('marseille');
        query.on(listeners)
             .onComplete(function() {
                 deepEqual([
                     ['done', {lat: 42, lng: 12}, creme.geolocation.LocationStatus.PARTIAL, {
                         geometry: {location: {lat: 42, lng: 12}},
                         address_components: [],
                         partial_match: true
                     }]
                 ], self.mockListenerCalls('search-done'));

                 start();
             });

        query.start();
        stop(1);
    });
});

QUnit.test('creme.geolocation.GoogleMapController.searchQuery (partial, multiple matches)', function(assert) {
    var self = this;
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());
    var listeners = {
        cancel: this.mockListener('search-cancel'),
        done: this.mockListener('search-done'),
        fail: this.mockListener('search-fail')
    };

    this.runTestOnGeomapReady(controller, element, function() {
        controller._geocoder = self.mockGeocoder;

        // single match but partial => PARTIAL
        var query = controller._searchLocationQuery('marseille');
        query.on(listeners)
             .onComplete(function() {
                 deepEqual([
                     ['done', {lat: 42, lng: 12}, creme.geolocation.LocationStatus.PARTIAL, {
                         geometry: {location: {lat: 42, lng: 12}},
                         address_components: [],
                         partial_match: true
                     }]
                 ], self.mockListenerCalls('search-done'));

                 start();
             })
             .start();

        stop(1);
        self.resetMockListenerCalls();

        // multiple maches => PARTIAL
        query = controller._searchLocationQuery('marseille 13015');
        query.on(listeners)
             .onComplete(function() {
                 deepEqual([
                     ['done', {lat: 42, lng: 12}, creme.geolocation.LocationStatus.PARTIAL, {
                         geometry: {location: {lat: 42, lng: 12}},
                         address_components: [],
                         partial_match: false
                     }]
                 ], self.mockListenerCalls('search-done'));

                 start();
             })
             .start();

        stop(1);
    });
});

QUnit.test('creme.geolocation.GoogleMapController.searchQuery (complete)', function(assert) {
    var self = this;
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());
    var listeners = {
        cancel: this.mockListener('search-cancel'),
        done: this.mockListener('search-done'),
        fail: this.mockListener('search-fail')
    };

    this.runTestOnGeomapReady(controller, element, function() {
        controller._geocoder = self.mockGeocoder;

        // single complete match => COMPLETE
        var query = controller._searchLocationQuery('319 Rue Saint-Pierre, 13005 Marseille');
        query.on(listeners)
             .onComplete(function() {
                 deepEqual([
                     ['done', {lat: 43.291628, lng: 5.4030217}, creme.geolocation.LocationStatus.COMPLETE, {
                         geometry: {
                             location: {lat: 43.291628, lng: 5.4030217}
                         },
                         address_components: [],
                         partial_match: false
                     }]
                 ], self.mockListenerCalls('search-done'));

                 start();
             })
             .start();

        stop(1);
    });
});

QUnit.test('creme.geolocation.GoogleMapController.markLocation (add marker)', function(assert) {
    var self = this;
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    controller.on('marker-move', this.mockListener('search-done'));

    this.runTestOnGeomapReady(controller, element, function() {
        controller._geocoder = self.mockGeocoder;

        // single complete match => COMPLETE
        controller.markLocation({
            location: {
                owner: 'fulbert',
                id: 'Address_A',
                title: 'Address A',
                content: '319 Rue Saint-Pierre, 13005 Marseille'
            },
            extraData: {
                content: 'some custom data'
            }
        }, {
            done: function(event, position, status, data) {
                deepEqual({lat: 43.291628, lng: 5.4030217}, position);
                deepEqual(creme.geolocation.LocationStatus.COMPLETE, status);
                deepEqual({
                    geometry: {
                        location: {lat: 43.291628, lng: 5.4030217}
                    },
                    address_components: [],
                    partial_match: false
                }, data);

                var marker = controller.getMarker('Address_A');
                equal(false, Object.isNone(marker), 'marker exists');
                equal(true, marker.getVisible(), 'marker is visible');

                equal('fulbert\nAddress A', marker.getTitle());
                deepEqual(new google.maps.LatLng({lat: 43.291628, lng: 5.4030217}), marker.getPosition());
                deepEqual({
                    id: 'Address_A',
                    extraData: {
                        content: 'some custom data'
                    }
                }, marker.__extra);

                deepEqual([
                    ['marker-move', marker, {
                        id: 'Address_A',
                        title: 'fulbert\nAddress A',
                        position: {
                            lat: 43.291628,
                            lng: 5.4030217
                        },
                        draggable: false,
                        visible: true,
                        status: creme.geolocation.LocationStatus.COMPLETE,
                        extraData: {
                            content: 'some custom data'
                        },
                        searchData: data
                    }]
                ], self.mockListenerCalls('search-done'));

                start();
            }
        });

        stop(1);
    });
});

QUnit.test('creme.geolocation.GoogleMapController.markLocation (update marker)', function(assert) {
    var self = this;
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    controller.on('marker-move', this.mockListener('search-done'));

    this.runTestOnGeomapReady(controller, element, function() {
        controller._geocoder = self.mockGeocoder;

        controller.addMarker('Address_A', {
            icon: 'default',
            position: {lat: 43, lng: 5},
            extraData: {
                content: 'Marseille'
            }
        });

        var marker = controller.getMarker('Address_A');
        equal(false, Object.isNone(marker));
        equal(true, marker.getVisible());
        equal(1, controller.markers().length);
        deepEqual({
            id: 'Address_A',
            extraData: {
                content: 'Marseille'
            }
        }, marker.__extra);

        // single complete match => COMPLETE
        controller.markLocation({
            location: {
                owner: 'fulbert',
                id: 'Address_A',
                content: '319 Rue Saint-Pierre, 13005 Marseille'
            }
        }, {
            done: function(event, position, status, data) {
                deepEqual({lat: 43.291628, lng: 5.4030217}, position);
                deepEqual(creme.geolocation.LocationStatus.COMPLETE, status);
                deepEqual({
                    geometry: {
                        location: {lat: 43.291628, lng: 5.4030217}
                    },
                    address_components: [],
                    partial_match: false
                }, data);

                var marker = controller.getMarker('Address_A');
                equal(false, Object.isNone(marker));
                equal(true, marker.getVisible());
                equal(1, controller.markers().length);

                equal('fulbert\n319 Rue Saint-Pierre, 13005 Marseille', marker.getTitle());
                deepEqual(new google.maps.LatLng({lat: 43.291628, lng: 5.4030217}), marker.getPosition());
                deepEqual({
                    id: 'Address_A',
                    extraData: {
                        content: 'Marseille'
                    }
                }, marker.__extra);

                deepEqual([
                    ['marker-move', marker, {
                        id: 'Address_A',
                        title: 'fulbert\n319 Rue Saint-Pierre, 13005 Marseille',
                        position: {
                            lat: 43.291628,
                            lng: 5.4030217
                        },
                        draggable: false,
                        visible: true,
                        status: creme.geolocation.LocationStatus.COMPLETE,
                        extraData: {
                            content: 'Marseille'
                        },
                        searchData: data
                    }]
                ], self.mockListenerCalls('search-done'));

                start();
             }
        });

        stop(1);
    });
});

QUnit.test('creme.geolocation.GoogleMapController.markLocation (address has previous position)', function(assert) {
    var self = this;
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    controller.on('marker-move', this.mockListener('search-done'));

    this.runTestOnGeomapReady(controller, element, function() {
        controller._geocoder = self.mockGeocoder;

        controller.addMarker('Address_A', {
            icon: 'default',
            position: {lat: 43, lng: 5},
            extraData: {
                content: 'Marseille'
            }
        });

        var marker = controller.getMarker('Address_A');
        equal(false, Object.isNone(marker));
        equal(true, marker.getVisible());
        equal(1, controller.markers().length);
        deepEqual({
            id: 'Address_A',
            extraData: {
                content: 'Marseille'
            }
        }, marker.__extra);

        // single complete match => COMPLETE
        controller.markLocation({
            location: {
                owner: 'fulbert',
                id: 'Address_A',
                content: '319 Rue Saint-Pierre, 13005 Marseille'
            }
        }, {
            done: function(event, position, status, data) {
                deepEqual({lat: 43.291628, lng: 5.4030217}, position);
                deepEqual(creme.geolocation.LocationStatus.COMPLETE, status);
                deepEqual({
                    geometry: {
                        location: {lat: 43.291628, lng: 5.4030217}
                    },
                    address_components: [],
                    partial_match: false
                }, data);

                var marker = controller.getMarker('Address_A');
                equal(false, Object.isNone(marker));
                equal(true, marker.getVisible());
                equal(1, controller.markers().length);

                equal('fulbert\n319 Rue Saint-Pierre, 13005 Marseille', marker.getTitle());
                deepEqual(new google.maps.LatLng({lat: 43.291628, lng: 5.4030217}), marker.getPosition());
                deepEqual({
                    id: 'Address_A',
                    extraData: {
                        content: 'Marseille'
                    }
                }, marker.__extra);

                deepEqual([
                    ['marker-move', marker, {
                        id: 'Address_A',
                        title: 'fulbert\n319 Rue Saint-Pierre, 13005 Marseille',
                        position: {
                            lat: 43.291628,
                            lng: 5.4030217
                        },
                        draggable: false,
                        visible: true,
                        status: creme.geolocation.LocationStatus.COMPLETE,
                        extraData: {
                            content: 'Marseille'
                        },
                        searchData: data
                    }]
                ], self.mockListenerCalls('search-done'));

                start();
             }
        });

        stop(1);
    });
});

QUnit.test('creme.geolocation.GoogleMapController.markLocation (no api key)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController();
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        // single complete match => COMPLETE
        controller.markLocation({
            location: {
                owner: 'fulbert',
                id: 'Address_B',
                title: 'Address B',
                content: '319 Rue Saint-Pierre, 13005 Marseille'
            }
        }, {
            fail: function(event, message) {
                equal(gettext("No matching location"), message);
                equal(0, controller.markers().length);

                start();
            }
        });

        stop(1);
    });
});

QUnit.test('creme.geolocation.GoogleMapController.addMarker', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        equal(false, controller.hasMarker('A'));
        equal(undefined, controller.getMarker('A'));

        controller.addMarker('A', {
            icon: 'circle',
            position: {lat: 43, lng: 5},
            extraData: {address: 'Marseille'}
        });

        var marker = controller.getMarker('A');
        equal(true, controller.hasMarker('A'));
        equal(false, Object.isNone(marker));
        equal(1, controller.markers().length);
        equal(0, controller.markers({visible: false}).length);
        deepEqual(['A'], controller.markerIds());
        deepEqual([], controller.markerIds({visible: false}));

        deepEqual({
            path: google.maps.SymbolPath.CIRCLE,
            scale: 5
        }, marker.getIcon());
        equal(true, marker.getVisible());
        deepEqual(new google.maps.LatLng({lat: 43, lng: 5}), marker.getPosition());
        deepEqual({
            id: 'A',
            extraData: {address: 'Marseille'}
        }, marker.__extra);
    });
});

QUnit.test('creme.geolocation.GoogleMapController.addMarker (already exists)', function(assert) {
    var self = this;
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        equal(false, controller.hasMarker('A'));
        equal(undefined, controller.getMarker('A'));

        controller.addMarker('A', {
            position: {lat: 43, lng: 5},
            extraData: {address: 'Marseille'}
        });

        var marker = controller.getMarker('A');
        equal(true, controller.hasMarker('A'));
        equal(false, Object.isNone(marker));

        self.assertRaises(function() {
            controller.addMarker('A', {
                icon: 'default',
                position: {lat: 43, lng: 5},
                extraData: {address: 'Marseille'}
            });
        }, Error, 'Error: Marker "A" is already registered');
    });
});

QUnit.test('creme.geolocation.GoogleMapController.addMarker (empty id)', function(assert) {
    var self = this;
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        self.assertRaises(function() {
            controller.addMarker(undefined, {
                icon: 'default'
            });
        }, Error, 'Error: Marker id cannot be empty');

        self.assertRaises(function() {
            controller.addMarker(null, {
                icon: 'default'
            });
        }, Error, 'Error: Marker id cannot be empty');

        self.assertRaises(function() {
            controller.addMarker('', {
                icon: 'default'
            });
        }, Error, 'Error: Marker id cannot be empty');
    });
});

QUnit.test('creme.geolocation.GoogleMapController.removeMarker', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
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

        controller.removeMarker('A');

        equal(false, controller.hasMarker('A'));
        equal(undefined, controller.getMarker('A'));
    });
});

QUnit.test('creme.geolocation.GoogleMapController.removeMarker (not exists)', function(assert) {
    var self = this;
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        equal(false, controller.hasMarker('A'));
        equal(undefined, controller.getMarker('A'));

        self.assertRaises(function() {
            controller.removeMarker(undefined);
        }, Error, 'Error: Marker id cannot be empty');

        self.assertRaises(function() {
            controller.removeMarker(null);
        }, Error, 'Error: Marker id cannot be empty');

        self.assertRaises(function() {
            controller.removeMarker('');
        }, Error, 'Error: Marker id cannot be empty');

        self.assertRaises(function() {
            controller.removeMarker('A');
        }, Error, 'Error: Marker "A" is not registered');
    });
});

QUnit.test('creme.geolocation.GoogleMapController.updateMarker', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

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
        equal(null, marker.getIcon());

        controller.updateMarker('A', {
            icon: 'cross',
            position: {lat: 42, lng: 5.5},
            extraData: {address: 'Marseille 13006'}
        });

        marker = controller.getMarker('A');
        equal(true, controller.hasMarker('A'));
        equal(false, Object.isNone(marker));
        equal(true, marker.getVisible());
        deepEqual(new google.maps.LatLng({lat: 42, lng: 5.5}), marker.getPosition());
        deepEqual({
            id: 'A',
            extraData: {address: 'Marseille 13006'}
        }, marker.__extra);
        equal('cross', marker.getIcon());

        controller.updateMarker('A', {
            icon: 'circle'
        });

        marker = controller.getMarker('A');
        equal(true, marker.getVisible());
        deepEqual(new google.maps.LatLng({lat: 42, lng: 5.5}), marker.getPosition());
        deepEqual({
            id: 'A',
            extraData: {address: 'Marseille 13006'}
        }, marker.__extra);
        deepEqual({
            path: google.maps.SymbolPath.CIRCLE,
            scale: 5
        }, marker.getIcon());

        controller.updateMarker('A', {
            icon: 'default'
        });

        marker = controller.getMarker('A');
        equal(true, marker.getVisible());
        deepEqual(new google.maps.LatLng({lat: 42, lng: 5.5}), marker.getPosition());
        deepEqual({
            id: 'A',
            extraData: {address: 'Marseille 13006'}
        }, marker.__extra);
        deepEqual(null, marker.getIcon());
    });
});

QUnit.test('creme.geolocation.GoogleMapController.updateMarker (not exists)', function(assert) {
    var self = this;
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        equal(true, controller.isEnabled());

        equal(false, controller.hasMarker('A'));
        equal(undefined, controller.getMarker('A'));

        self.assertRaises(function() {
            controller.updateMarker(undefined);
        }, Error, 'Error: Marker id cannot be empty');

        self.assertRaises(function() {
            controller.updateMarker(null);
        }, Error, 'Error: Marker id cannot be empty');

        self.assertRaises(function() {
            controller.updateMarker('');
        }, Error, 'Error: Marker id cannot be empty');

        self.assertRaises(function() {
            controller.updateMarker('A');
        }, Error, 'Error: Marker "A" is not registered');
    });
});

QUnit.test('creme.geolocation.GoogleMapController.toggleMarker', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
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
        equal(true, marker.getVisible());
        equal(1, controller.markers().length);
        equal(0, controller.markers({visible: false}).length);

        controller.toggleMarker('A');

        marker = controller.getMarker('A');
        equal(false, marker.getVisible());
        equal(1, controller.markers().length);
        equal(1, controller.markers({visible: false}).length);

        controller.toggleMarker('A');

        marker = controller.getMarker('A');
        equal(true, marker.getVisible());
        equal(1, controller.markers().length);
        equal(0, controller.markers({visible: false}).length);

        controller.toggleMarker('A', true);

        marker = controller.getMarker('A');
        equal(true, marker.getVisible());
        equal(1, controller.markers().length);
        equal(0, controller.markers({visible: false}).length);
    });
});

QUnit.test('creme.geolocation.GoogleMapController.toggleAllMarkers', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        equal(false, controller.hasMarker('A'));
        equal(undefined, controller.getMarker('A'));

        controller.addMarker('A', {
            icon: 'default',
            position: {lat: 43, lng: 5},
            extraData: {address: 'Marseille'}
        });

        controller.addMarker('B', {
            icon: 'default',
            position: {lat: 43, lng: 5.5},
            extraData: {address: 'Marseille 13006'}
        });

        equal(2, controller.markers().length);
        equal(0, controller.markers({visible: false}).length);
        deepEqual(['A', 'B'], controller.markerIds());
        deepEqual([], controller.markerIds({visible: false}));

        controller.toggleAllMarkers();

        equal(2, controller.markers().length);
        equal(2, controller.markers({visible: false}).length);
        deepEqual(['A', 'B'], controller.markerIds());
        deepEqual(['A', 'B'], controller.markerIds({visible: false}));

        controller.toggleAllMarkers();

        equal(2, controller.markers().length);
        equal(0, controller.markers({visible: false}).length);
        deepEqual(['A', 'B'], controller.markerIds());
        deepEqual([], controller.markerIds({visible: false}));

        controller.toggleAllMarkers(true);

        equal(2, controller.markers().length);
        equal(0, controller.markers({visible: false}).length);
        deepEqual(['A', 'B'], controller.markerIds());
        deepEqual([], controller.markerIds({visible: false}));

        controller.toggleAllMarkers(false);

        equal(2, controller.markers().length);
        equal(2, controller.markers({visible: false}).length);
        deepEqual(['A', 'B'], controller.markerIds());
        deepEqual(['A', 'B'], controller.markerIds({visible: false}));
    });
});

QUnit.test('creme.geolocation.GoogleMapController.replaceMarkers', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        equal(false, controller.hasMarker('A'));
        equal(undefined, controller.getMarker('A'));

        controller.addMarker('A', {
            icon: 'default',
            position: {lat: 43, lng: 5},
            extraData: {address: 'Marseille'}
        });

        equal(true, controller.hasMarker('A'));

        this.assertGoogleMarker(controller.getMarker('A'), {
            position: {lat: 42, lng: 5.5},
            id: 'A',
            title: undefined,
            visible: true,
            extraData: {
                address: 'Marseille'
            }
        });

        controller.replaceMarkers([{
            id: 'A',
            title: 'Address A',
            icon: 'circle',
            position: {lat: 42, lng: 5.5}
        }, {
            id: 'B',
            position: {lat: 43, lng: 5},
            extraData: {
                address: 'Marseille 13006'
            },
            visible: false
        }]);

        equal(2, controller.markers().length);
        equal(1, controller.markers({visible: false}).length);
        deepEqual(['A', 'B'], controller.markerIds());
        deepEqual(['B'], controller.markerIds({visible: false}));

        this.assertGoogleMarker(controller.getMarker('A'), {
            position: {lat: 42, lng: 5.5},
            id: 'A',
            title: 'Address A',
            visible: true,
            extraData: {
                address: 'Marseille'
            }
        });

        this.assertGoogleMarker(controller.getMarker('B'), {
            position: {lat: 43, lng: 5},
            id: 'B',
            title: undefined,
            visible: false,
            extraData: {
                address: 'Marseille 13006'
            }
        });

        controller.replaceMarkers([{
            id: 'C',
            title: 'Address C',
            position: {lat: 42.75, lng: 5.2},
            visible: true,
            extraData: {
                url: 'mock/address/C'
            }
        }]);

        equal(1, controller.markers().length);
        equal(0, controller.markers({visible: false}).length);
        deepEqual(['C'], controller.markerIds());
        deepEqual([], controller.markerIds({visible: false}));

        this.assertGoogleMarker(controller.getMarker('C'), {
            id: 'C',
            title: 'Address C',
            position: {lat: 42.75, lng: 5.2},
            visible: true,
            extraData: {
                url: 'mock/address/C'
            }
        });

        controller.replaceMarkers([]);

        equal(0, controller.markers().length);
        equal(0, controller.markers({visible: false}).length);
        deepEqual([], controller.markerIds());
        deepEqual([], controller.markerIds({visible: false}));
    });
});

QUnit.test('creme.geolocation.GoogleMapController (marker-click)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    controller.on('marker-click', this.mockListener('marker-click'));

    this.runTestOnGeomapReady(controller, element, function() {
        equal(true, controller.isEnabled());

        equal(false, controller.hasMarker('A'));
        equal(undefined, controller.getMarker('A'));

        var marker = controller.addMarker('A', {
            icon: 'default',
            position: {lat: 43, lng: 5},
            extraData: {address: 'Marseille'}
        });

        deepEqual([], this.mockListenerCalls('marker-click'));

        google.maps.event.trigger(marker, 'click');

        deepEqual([
            ['marker-click', {id: 'A', extraData: {address: 'Marseille'}}]
        ], this.mockListenerCalls('marker-click').map(function(e) {
            return [e[0], e[1]];
        }));
    });
});

QUnit.test('creme.geolocation.GoogleMapController (drag-n-drop)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    controller.on('marker-dragstart', this.mockListener('marker-dragstart'));
    controller.on('marker-dragstop', this.mockListener('marker-dragstop'));

    this.runTestOnGeomapReady(controller, element, function() {
        equal(true, controller.isEnabled());

        equal(false, controller.hasMarker('A'));
        equal(undefined, controller.getMarker('A'));

        var marker = controller.addMarker('A', {
            draggable: true,
            icon: 'default',
            position: {lat: 43, lng: 5},
            extraData: {address: 'Marseille'}
        });

        deepEqual([], this.mockListenerCalls('marker-dragstart'));
        deepEqual([], this.mockListenerCalls('marker-dragstop'));

        google.maps.event.trigger(marker, 'dragstart');

        deepEqual([
            ['marker-dragstart', {
                id: 'A',
                extraData: {address: 'Marseille'},
                dragStartPosition: {lat: 43, lng: 5}
            }]
        ], this.mockListenerCalls('marker-dragstart').map(function(e) {
            return [e[0], e[1]];
        }));
        deepEqual([], this.mockListenerCalls('marker-dragstop'));

        marker.setPosition({lat: 42, lng: 5.5});
        google.maps.event.trigger(marker, 'dragend');

        deepEqual([
            ['marker-dragstart', {
                id: 'A',
                extraData: {address: 'Marseille'},
                dragStartPosition: {lat: 43, lng: 5}
            }]
        ], this.mockListenerCalls('marker-dragstart').map(function(e) {
            return [e[0], e[1]];
        }));
        deepEqual([
            ['marker-dragstop', {
                id: 'A',
                extraData: {address: 'Marseille'},
                dragStartPosition: {lat: 43, lng: 5},
                dragStopPosition: {lat: 42, lng: 5.5}
            }]
        ], this.mockListenerCalls('marker-dragstop').map(function(e) {
            return [e[0], e[1]];
        }));
    });
});

QUnit.test('creme.geolocation.GoogleMapController.addShape (circle)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        equal(false, controller.hasShape('A'));
        equal(undefined, controller.getShape('A'));
        equal(0, controller.shapes().length);
        equal(0, controller.shapes({visible: false}).length);
        equal(0, controller.shapeIds().length);
        equal(0, controller.shapeIds({visible: false}).length);


        var shape = controller.addShape('A', {
            position: {lat: 43, lng: 5},
            radius: 5,
            shape: 'circle',
            extraData: {
                url: 'mock/shape'
            }
        });

        equal(false, Object.isNone(shape));
        equal(true, shape.getVisible());
        equal(5, shape.getRadius());
        deepEqual(new google.maps.LatLng({lat: 43, lng: 5}), shape.getCenter());
        deepEqual({
            id: 'A',
            extraData: {
                url: 'mock/shape'
            }
        }, shape.__extra);

        equal(1, controller.shapes().length);
        equal(0, controller.shapes({visible: false}).length);

        deepEqual(['A'], controller.shapeIds());
        deepEqual([], controller.shapeIds({visible: false}));
    });
});

QUnit.test('creme.geolocation.GoogleMapController.addShape (unknown type)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        equal(false, controller.hasShape('A'));
        equal(undefined, controller.getShape('A'));
        equal(0, controller.shapes().length);
        equal(0, controller.shapes({visible: false}).length);
        equal(0, controller.shapeIds().length);
        equal(0, controller.shapeIds({visible: false}).length);

        this.assertRaises(function() {
            controller.addShape('A', {
                position: {lat: 52, lng: 6},
                radius: 10,
                shape: 'cloud'
            });
        }, Error, 'Error: Shape has unknown type "cloud"');

        equal(false, controller.hasShape('A'));
        equal(undefined, controller.getShape('A'));
        equal(0, controller.shapes().length);
        equal(0, controller.shapes({visible: false}).length);
    });
});

QUnit.test('creme.geolocation.GoogleMapController.addShape (empty id)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        equal(false, controller.hasShape('A'));
        equal(undefined, controller.getShape('A'));
        equal(0, controller.shapes().length);
        equal(0, controller.shapes({visible: false}).length);
        equal(0, controller.shapeIds().length);
        equal(0, controller.shapeIds({visible: false}).length);

        this.assertRaises(function() {
            controller.addShape(undefined, {
                shape: 'circle'
            });
        }, Error, 'Error: Shape id cannot be empty');

        this.assertRaises(function() {
            controller.addShape(null, {
                shape: 'circle'
            });
        }, Error, 'Error: Shape id cannot be empty');

        this.assertRaises(function() {
            controller.addShape('', {
                shape: 'circle'
            });
        }, Error, 'Error: Shape id cannot be empty');

        equal(false, controller.hasShape('A'));
        equal(undefined, controller.getShape('A'));
        equal(0, controller.shapes().length);
        equal(0, controller.shapes({visible: false}).length);
    });
});


QUnit.test('creme.geolocation.GoogleMapController.addShape (already exists)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        equal(false, controller.hasShape('A'));
        equal(undefined, controller.getShape('A'));
        equal(0, controller.shapes().length);
        equal(0, controller.shapes({visible: false}).length);

        var shape = controller.addShape('A', {
            position: {lat: 43, lng: 5},
            radius: 5,
            shape: 'circle'
        });

        equal(false, Object.isNone(shape));
        equal(true, shape.getVisible());
        equal(5, shape.getRadius());
        deepEqual(new google.maps.LatLng({lat: 43, lng: 5}), shape.getCenter());

        equal(1, controller.shapes().length);
        equal(0, controller.shapes({visible: false}).length);

        deepEqual(['A'], controller.shapeIds());
        deepEqual([], controller.shapeIds({visible: false}));

        this.assertRaises(function() {
            controller.addShape('A', {
                position: {lat: 52, lng: 6},
                radius: 10,
                shape: 'circle'
            });
        }, Error, 'Error: Shape "A" is already registered');
    });
});

QUnit.test('creme.geolocation.GoogleMapController.updateShape', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        var shape = controller.addShape('A', {
            position: {lat: 43, lng: 5},
            radius: 5,
            shape: 'circle'
        });

        equal(false, Object.isNone(shape));
        equal(true, shape.getVisible());
        equal(5, shape.getRadius());
        deepEqual(new google.maps.LatLng({lat: 43, lng: 5}), shape.getCenter());

        equal(1, controller.shapes().length);
        equal(0, controller.shapes({visible: false}).length);

        controller.updateShape('A', {
            position: {lat: 43.5, lng: 5.53},
            radius: 2,
            extraData: {
                address: 'Marseille'
            }
        });

        shape = controller.getShape('A');
        equal(true, shape.getVisible());
        equal(2, shape.getRadius());
        deepEqual(new google.maps.LatLng({lat: 43.5, lng: 5.53}), shape.getCenter());
        deepEqual({
            address: 'Marseille'
        }, shape.__extra.extraData);

        equal(1, controller.shapes().length);
        equal(0, controller.shapes({visible: false}).length);
    });
});

QUnit.test('creme.geolocation.GoogleMapController.updateShape (not exists)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        this.assertRaises(function() {
            controller.updateShape(undefined, {
                radius: 10
            });
        }, Error, 'Error: Shape id cannot be empty');

        this.assertRaises(function() {
            controller.updateShape(null, {
                radius: 10
            });
        }, Error, 'Error: Shape id cannot be empty');

        this.assertRaises(function() {
            controller.updateShape('', {
                radius: 10
            });
        }, Error, 'Error: Shape id cannot be empty');

        this.assertRaises(function() {
            controller.updateShape('A', {
                position: {lat: 43.5, lng: 5.53},
                radius: 2
            });
        }, Error, 'Error: Shape "A" is not registered');
    });
});

QUnit.test('creme.geolocation.GoogleMapController.removeShape', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        var shape = controller.addShape('A', {
            position: {lat: 43, lng: 5},
            radius: 5,
            shape: 'circle'
        });

        equal(false, Object.isNone(shape));
        equal(true, shape.getVisible());
        equal(5, shape.getRadius());
        deepEqual(new google.maps.LatLng({lat: 43, lng: 5}), shape.getCenter());

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

QUnit.test('creme.geolocation.GoogleMapController.removeShape (not exists)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        this.assertRaises(function() {
            controller.removeShape(undefined);
        }, Error, 'Error: Shape id cannot be empty');

        this.assertRaises(function() {
            controller.removeShape(null);
        }, Error, 'Error: Shape id cannot be empty');

        this.assertRaises(function() {
            controller.removeShape('');
        }, Error, 'Error: Shape id cannot be empty');

        this.assertRaises(function() {
            controller.removeShape('A');
        }, Error, 'Error: Shape "A" is not registered');
    });
});

QUnit.test('creme.geolocation.GoogleMapController.adjustMap (no marker)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    // not bound, no changes
    controller.adjustMap();

    this.runTestOnGeomapReady(controller, element, function() {
        controller.adjustMap();

        // no markers, centers on defaults
        deepEqual(
            new google.maps.LatLng(controller.options().defaultLat, controller.options().defaultLng),
            controller.map().getCenter()
        );
    });
});

QUnit.test('creme.geolocation.GoogleMapController.adjustMap (single marker)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        var marker = controller.addMarker('A', {
            position: {lat: 43, lng: 5}
        });

        controller.adjustMap();

        // 1 marker, center map on it
        deepEqual(marker.getPosition(), controller.map().getCenter());
        equal(controller.options().defaultZoomValue, controller.map().getZoom());
    });
});

QUnit.test('creme.geolocation.GoogleMapController.adjustMap (multiple markers)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        var markerA = controller.addMarker('A', {
            position: {lat: 43, lng: 5}
        });
        var markerB = controller.addMarker('B', {
            position: {lat: 40, lng: 3}
        });
        var markerC = controller.addMarker('C', {
            position: {lat: 50, lng: 6}
        });

        controller.adjustMap();

        var bounds = new google.maps.LatLngBounds();
        bounds.extend(markerA.getPosition());
        bounds.extend(markerB.getPosition());
        bounds.extend(markerC.getPosition());

        // 3 visible markers, center map on them
        deepEqual(bounds.getCenter(), controller.map().getCenter());

        // 1 visible marker, center map on it
        controller.toggleMarker('A', false);
        controller.toggleMarker('B', false);

        deepEqual(markerC.getPosition(), controller.map().getCenter());

        controller.toggleMarker('A', true);
        controller.toggleMarker('B', false);
        controller.toggleMarker('C', false);

        deepEqual(markerA.getPosition(), controller.map().getCenter());

        // no visible marker, center on default
        controller.toggleMarker('A', false);

        equal(0, controller.markers({visible: true}).length);

        deepEqual(
            new google.maps.LatLng(controller.options().defaultLat, controller.options().defaultLng),
            controller.map().getCenter()
        );
    });
});

QUnit.test('creme.geolocation.GoogleMapController.adjustMapToShape', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    // not bound, no changes
    controller.adjustMapToShape('A');

    this.runTestOnGeomapReady(controller, element, function() {
        var shape = controller.addShape('A', {
            position: {lat: 43, lng: 5},
            radius: 5,
            shape: 'circle'
        });

        controller.adjustMapToShape('A');

        // center map on shape
        deepEqual(shape.getCenter(), controller.map().getCenter());
    });
});

QUnit.test('creme.geolocation.GoogleMapController.adjustMapToShape (not exists)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        controller.adjustMapToShape('A');

        // no shape, remains on map defaults
        deepEqual(
            new google.maps.LatLng(controller.options().defaultLat, controller.options().defaultLng),
            controller.map().getCenter()
        );
    });
});

}(jQuery, QUnit));
