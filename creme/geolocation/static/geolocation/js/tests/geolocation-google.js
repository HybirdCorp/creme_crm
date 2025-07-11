/* globals QUnitGeolocationMixin creme_media_url */
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

    assert.equal(12, controller.options().defaultZoomValue);
    assert.equal(48, controller.options().defaultLat);
    assert.equal(2, controller.options().defaultLn);
    assert.equal(4, controller.options().defaultLargeZoom);
    assert.equal(undefined, controller.options().apiKey);
    assert.equal('3.exp', controller.options().apiVersion);

    assert.equal(true, controller.isGeocoderAllowed());

    assert.equal(false, controller.isBound());
    assert.equal(false, controller.isEnabled());

    assert.equal(false, controller.isMapEnabled());
    assert.equal(creme.geolocation.isGoogleAPIReady(), controller.isAPIReady());
    assert.equal(false, controller.isGeocoderEnabled());

    assert.equal(undefined, controller.map());
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

    assert.equal(20, controller.options().defaultZoomValue);
    assert.equal(47, controller.options().defaultLat);
    assert.equal(4, controller.options().defaultLn);
    assert.equal(5, controller.options().defaultLargeZoom);
    assert.equal('mockit!', controller.options().apiKey);
    assert.equal('3', controller.options().apiVersion);
    assert.equal(false, controller.options().allowGeocoder);

    assert.equal(false, controller.isBound());
    assert.equal(false, controller.isEnabled());
    assert.equal(false, controller.isGeocoderAllowed());

    assert.equal(false, controller.isMapEnabled());
    assert.equal(creme.geolocation.isGoogleAPIReady(), controller.isAPIReady());
    assert.equal(false, controller.isGeocoderEnabled());

    assert.equal(undefined, controller.map());
});

QUnit.test('creme.geolocation.GoogleMapController.bind', function(assert) {
    var controller = new creme.geolocation.GoogleMapController();
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());
    var done = assert.async();

    controller.on('status-enabled', function() {
        assert.equal(true, controller.isBound());
        assert.equal(true, controller.isEnabled());

        assert.equal(true, controller.isMapEnabled());
        assert.equal(true, controller.isAPIReady());
        assert.equal(true, controller.isGeocoderEnabled());
        done();
    });

    controller.bind(element);

    assert.equal(true, controller.isBound());
    assert.equal(false, controller.isEnabled());

    assert.equal(false, controller.isMapEnabled());
    assert.equal(creme.geolocation.isGoogleAPIReady(), controller.isAPIReady());
    assert.equal(false, controller.isGeocoderEnabled());

    assert.equal(undefined, controller.map());
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
    var done = assert.async();

    controller.on('status-enabled', function() {
        controller.unbind();
        assert.equal(false, controller.isBound());
        assert.equal(false, controller.isEnabled());

        assert.equal(false, controller.isMapEnabled());
        assert.equal(true, controller.isAPIReady());

        assert.equal(undefined, controller.map());
        done();
    });

    controller.bind(element);
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
        assert.equal(true, controller.isMapEnabled());

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
        var done = assert.async();

        query.on(listeners)
             .onComplete(function() {
                 assert.deepEqual([
                     ['done', {lat: 42, lng: 12}, creme.geolocation.LocationStatus.PARTIAL, {
                         geometry: {location: {lat: 42, lng: 12}},
                         address_components: [],
                         partial_match: true
                     }]
                 ], self.mockListenerCalls('search-done'));

                 done();
             });

        query.start();
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
        var done = assert.async();

        query.on(listeners)
             .onComplete(function() {
                 assert.deepEqual([
                     ['done', {lat: 42, lng: 12}, creme.geolocation.LocationStatus.PARTIAL, {
                         geometry: {location: {lat: 42, lng: 12}},
                         address_components: [],
                         partial_match: true
                     }]
                 ], self.mockListenerCalls('search-done'));

                 done();
             })
             .start();

        self.resetMockListenerCalls();

        var done2 = assert.async();

        // multiple matches => PARTIAL
        query = controller._searchLocationQuery('marseille 13015');
        query.on(listeners)
             .onComplete(function() {
                 assert.deepEqual([
                     ['done', {lat: 42, lng: 12}, creme.geolocation.LocationStatus.PARTIAL, {
                         geometry: {location: {lat: 42, lng: 12}},
                         address_components: [],
                         partial_match: false
                     }]
                 ], self.mockListenerCalls('search-done'));

                 done2();
             })
             .start();
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
        var done = assert.async();

        query.on(listeners)
             .onComplete(function() {
                 assert.deepEqual([
                     ['done', {lat: 43.291628, lng: 5.4030217}, creme.geolocation.LocationStatus.COMPLETE, {
                         geometry: {
                             location: {lat: 43.291628, lng: 5.4030217}
                         },
                         address_components: [],
                         partial_match: false
                     }]
                 ], self.mockListenerCalls('search-done'));

                 done();
             })
             .start();
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
        var done = assert.async();

        // single complete match => COMPLETE
        controller.markLocation({
            location: {
                owner: 'fulbert',
                id: 'Address_A',
                title: 'Address A',
                content: '319 Rue Saint-Pierre, 13005 Marseille',
                extraData: {
                    isProspect: true
                }
            },
            extraData: {
                content: 'some custom data'
            }
        }, {
            done: function(event, position, status, data) {
                assert.deepEqual({lat: 43.291628, lng: 5.4030217}, position);
                assert.deepEqual(creme.geolocation.LocationStatus.COMPLETE, status);
                assert.deepEqual({
                    geometry: {
                        location: {lat: 43.291628, lng: 5.4030217}
                    },
                    address_components: [],
                    partial_match: false
                }, data);

                var marker = controller.getMarker('Address_A');
                assert.equal(false, Object.isNone(marker), 'marker exists');
                assert.equal(true, marker.getVisible(), 'marker is visible');

                assert.equal('fulbert\n319 Rue Saint-Pierre, 13005 Marseille\n(Address A)', marker.getTitle());
                assert.deepEqual(new google.maps.LatLng({lat: 43.291628, lng: 5.4030217}), marker.getPosition());
                assert.deepEqual({
                    id: 'Address_A',
                    extraData: {
                        content: 'some custom data'
                    }
                }, marker.__extra);

                assert.deepEqual([
                    ['marker-move', marker, {
                        id: 'Address_A',
                        title: 'fulbert\n319 Rue Saint-Pierre, 13005 Marseille\n(Address A)',
                        position: {
                            lat: 43.291628,
                            lng: 5.4030217
                        },
                        location: new creme.geolocation.Location({
                            owner: 'fulbert',
                            id: 'Address_A',
                            title: 'Address A',
                            content: '319 Rue Saint-Pierre, 13005 Marseille',
                            extraData: {
                                isProspect: true
                            }
                        }),
                        draggable: false,
                        visible: true,
                        status: creme.geolocation.LocationStatus.COMPLETE,
                        extraData: {
                            content: 'some custom data'
                        },
                        searchData: data
                    }]
                ], self.mockListenerCalls('search-done'));

                done();
            }
        });
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
        assert.equal(false, Object.isNone(marker));
        assert.equal(true, marker.getVisible());
        assert.equal(1, controller.markers().length);
        assert.deepEqual({
            id: 'Address_A',
            extraData: {
                content: 'Marseille'
            }
        }, marker.__extra);

        var done = assert.async();

        // single complete match => COMPLETE
        controller.markLocation({
            location: {
                owner: 'fulbert',
                id: 'Address_A',
                content: '319 Rue Saint-Pierre, 13005 Marseille',
                extraData: {
                    isProspect: true
                }
            }
        }, {
            done: function(event, position, status, data) {
                assert.deepEqual({lat: 43.291628, lng: 5.4030217}, position);
                assert.deepEqual(creme.geolocation.LocationStatus.COMPLETE, status);
                assert.deepEqual({
                    geometry: {
                        location: {lat: 43.291628, lng: 5.4030217}
                    },
                    address_components: [],
                    partial_match: false
                }, data);

                var marker = controller.getMarker('Address_A');
                assert.equal(false, Object.isNone(marker));
                assert.equal(true, marker.getVisible());
                assert.equal(1, controller.markers().length);

                assert.equal('fulbert\n319 Rue Saint-Pierre, 13005 Marseille', marker.getTitle());
                assert.deepEqual(new google.maps.LatLng({lat: 43.291628, lng: 5.4030217}), marker.getPosition());
                assert.deepEqual({
                    id: 'Address_A',
                    extraData: {
                        content: 'Marseille'
                    }
                }, marker.__extra);

                assert.deepEqual([
                    ['marker-move', marker, {
                        id: 'Address_A',
                        title: 'fulbert\n319 Rue Saint-Pierre, 13005 Marseille',
                        position: {
                            lat: 43.291628,
                            lng: 5.4030217
                        },
                        location: new creme.geolocation.Location({
                            owner: 'fulbert',
                            id: 'Address_A',
                            content: '319 Rue Saint-Pierre, 13005 Marseille',
                            extraData: {
                                isProspect: true
                            }
                        }),
                        draggable: false,
                        visible: true,
                        status: creme.geolocation.LocationStatus.COMPLETE,
                        extraData: {
                            content: 'Marseille'
                        },
                        searchData: data
                    }]
                ], self.mockListenerCalls('search-done'));

                done();
             }
        });
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
        assert.equal(false, Object.isNone(marker));
        assert.equal(true, marker.getVisible());
        assert.equal(1, controller.markers().length);
        assert.deepEqual({
            id: 'Address_A',
            extraData: {
                content: 'Marseille'
            }
        }, marker.__extra);

        var done = assert.async();

        // single complete match => COMPLETE
        controller.markLocation({
            location: {
                owner: 'fulbert',
                id: 'Address_A',
                content: '319 Rue Saint-Pierre, 13005 Marseille',
                extraData: {
                    isProspect: true
                }
            }
        }, {
            done: function(event, position, status, data) {
                assert.deepEqual({lat: 43.291628, lng: 5.4030217}, position);
                assert.deepEqual(creme.geolocation.LocationStatus.COMPLETE, status);
                assert.deepEqual({
                    geometry: {
                        location: {lat: 43.291628, lng: 5.4030217}
                    },
                    address_components: [],
                    partial_match: false
                }, data);

                var marker = controller.getMarker('Address_A');
                assert.equal(false, Object.isNone(marker));
                assert.equal(true, marker.getVisible());
                assert.equal(1, controller.markers().length);

                assert.equal('fulbert\n319 Rue Saint-Pierre, 13005 Marseille', marker.getTitle());
                assert.deepEqual(new google.maps.LatLng({lat: 43.291628, lng: 5.4030217}), marker.getPosition());
                assert.deepEqual({
                    id: 'Address_A',
                    extraData: {
                        content: 'Marseille'
                    }
                }, marker.__extra);

                assert.deepEqual([
                    ['marker-move', marker, {
                        id: 'Address_A',
                        title: 'fulbert\n319 Rue Saint-Pierre, 13005 Marseille',
                        position: {
                            lat: 43.291628,
                            lng: 5.4030217
                        },
                        location: new creme.geolocation.Location({
                            owner: 'fulbert',
                            id: 'Address_A',
                            content: '319 Rue Saint-Pierre, 13005 Marseille',
                            extraData: {
                                isProspect: true
                            }
                        }),
                        draggable: false,
                        visible: true,
                        status: creme.geolocation.LocationStatus.COMPLETE,
                        extraData: {
                            content: 'Marseille'
                        },
                        searchData: data
                    }]
                ], self.mockListenerCalls('search-done'));

                done();
             }
        });
    });
});

QUnit.test('creme.geolocation.GoogleMapController.markLocation (no api key)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController();
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        var done = assert.async();

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
                assert.equal(gettext("No matching location"), message);
                assert.equal(0, controller.markers().length);

                done();
            }
        });
    });
});

QUnit.test('creme.geolocation.GoogleMapController.addMarker', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        assert.equal(false, controller.hasMarker('A'));
        assert.equal(undefined, controller.getMarker('A'));

        controller.addMarker('A', {
            icon: 'circle',
            position: {lat: 43, lng: 5},
            extraData: {address: 'Marseille'}
        });

        var marker = controller.getMarker('A');
        assert.equal(true, controller.hasMarker('A'));
        assert.equal(false, Object.isNone(marker));
        assert.equal(1, controller.markers().length);
        assert.equal(0, controller.markers({visible: false}).length);
        assert.deepEqual(['A'], controller.markerIds());
        assert.deepEqual([], controller.markerIds({visible: false}));

        assert.deepEqual({
            path: google.maps.SymbolPath.CIRCLE,
            scale: 5
        }, marker.getIcon());
        assert.equal(true, marker.getVisible());
        assert.deepEqual(new google.maps.LatLng({lat: 43, lng: 5}), marker.getPosition());
        assert.deepEqual({
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
        assert.equal(false, controller.hasMarker('A'));
        assert.equal(undefined, controller.getMarker('A'));

        controller.addMarker('A', {
            position: {lat: 43, lng: 5},
            extraData: {address: 'Marseille'}
        });

        var marker = controller.getMarker('A');
        assert.equal(true, controller.hasMarker('A'));
        assert.equal(false, Object.isNone(marker));

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

        controller.removeMarker('A');

        assert.equal(false, controller.hasMarker('A'));
        assert.equal(undefined, controller.getMarker('A'));
    });
});

QUnit.test('creme.geolocation.GoogleMapController.removeMarker (not exists)', function(assert) {
    var self = this;
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        assert.equal(false, controller.hasMarker('A'));
        assert.equal(undefined, controller.getMarker('A'));

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
        assert.equal(null, marker.getIcon());

        controller.updateMarker('A', {
            icon: creme_media_url('geolocation/images/marker-icon.png'),
            position: {lat: 42, lng: 5.5},
            extraData: {address: 'Marseille 13006'}
        });

        marker = controller.getMarker('A');
        assert.equal(true, controller.hasMarker('A'));
        assert.equal(false, Object.isNone(marker));
        assert.equal(true, marker.getVisible());
        assert.deepEqual(new google.maps.LatLng({lat: 42, lng: 5.5}), marker.getPosition());
        assert.deepEqual({
            id: 'A',
            extraData: {address: 'Marseille 13006'}
        }, marker.__extra);
        assert.deepEqual({
            url: creme_media_url('geolocation/images/marker-icon.png'),
            size: new google.maps.Size(25, 41),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(12, 41)
        }, marker.getIcon());

        controller.updateMarker('A', {
            icon: 'circle'
        });

        marker = controller.getMarker('A');
        assert.equal(true, marker.getVisible());
        assert.deepEqual(new google.maps.LatLng({lat: 42, lng: 5.5}), marker.getPosition());
        assert.deepEqual({
            id: 'A',
            extraData: {address: 'Marseille 13006'}
        }, marker.__extra);
        assert.deepEqual({
            path: google.maps.SymbolPath.CIRCLE,
            scale: 5
        }, marker.getIcon());

        controller.updateMarker('A', {
            icon: 'default'
        });

        marker = controller.getMarker('A');
        assert.equal(true, marker.getVisible());
        assert.deepEqual(new google.maps.LatLng({lat: 42, lng: 5.5}), marker.getPosition());
        assert.deepEqual({
            id: 'A',
            extraData: {address: 'Marseille 13006'}
        }, marker.__extra);
        assert.deepEqual(null, marker.getIcon());
    });
});

QUnit.test('creme.geolocation.GoogleMapController.updateMarker (not exists)', function(assert) {
    var self = this;
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        assert.equal(true, controller.isEnabled());

        assert.equal(false, controller.hasMarker('A'));
        assert.equal(undefined, controller.getMarker('A'));

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
        assert.equal(true, marker.getVisible());
        assert.equal(1, controller.markers().length);
        assert.equal(0, controller.markers({visible: false}).length);

        controller.toggleMarker('A');

        marker = controller.getMarker('A');
        assert.equal(false, marker.getVisible());
        assert.equal(1, controller.markers().length);
        assert.equal(1, controller.markers({visible: false}).length);

        controller.toggleMarker('A');

        marker = controller.getMarker('A');
        assert.equal(true, marker.getVisible());
        assert.equal(1, controller.markers().length);
        assert.equal(0, controller.markers({visible: false}).length);

        controller.toggleMarker('A', true);

        marker = controller.getMarker('A');
        assert.equal(true, marker.getVisible());
        assert.equal(1, controller.markers().length);
        assert.equal(0, controller.markers({visible: false}).length);
    });
});

QUnit.test('creme.geolocation.GoogleMapController.toggleAllMarkers', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        assert.equal(false, controller.hasMarker('A'));
        assert.equal(undefined, controller.getMarker('A'));

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

        assert.equal(2, controller.markers().length);
        assert.equal(0, controller.markers({visible: false}).length);
        assert.deepEqual(['A', 'B'], controller.markerIds());
        assert.deepEqual([], controller.markerIds({visible: false}));

        controller.toggleAllMarkers();

        assert.equal(2, controller.markers().length);
        assert.equal(2, controller.markers({visible: false}).length);
        assert.deepEqual(['A', 'B'], controller.markerIds());
        assert.deepEqual(['A', 'B'], controller.markerIds({visible: false}));

        controller.toggleAllMarkers();

        assert.equal(2, controller.markers().length);
        assert.equal(0, controller.markers({visible: false}).length);
        assert.deepEqual(['A', 'B'], controller.markerIds());
        assert.deepEqual([], controller.markerIds({visible: false}));

        controller.toggleAllMarkers(true);

        assert.equal(2, controller.markers().length);
        assert.equal(0, controller.markers({visible: false}).length);
        assert.deepEqual(['A', 'B'], controller.markerIds());
        assert.deepEqual([], controller.markerIds({visible: false}));

        controller.toggleAllMarkers(false);

        assert.equal(2, controller.markers().length);
        assert.equal(2, controller.markers({visible: false}).length);
        assert.deepEqual(['A', 'B'], controller.markerIds());
        assert.deepEqual(['A', 'B'], controller.markerIds({visible: false}));
    });
});

QUnit.test('creme.geolocation.GoogleMapController.replaceMarkers', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        assert.equal(false, controller.hasMarker('A'));
        assert.equal(undefined, controller.getMarker('A'));

        controller.addMarker('A', {
            icon: 'default',
            position: {lat: 43, lng: 5},
            extraData: {address: 'Marseille'}
        });

        assert.equal(true, controller.hasMarker('A'));

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

        assert.equal(2, controller.markers().length);
        assert.equal(1, controller.markers({visible: false}).length);
        assert.deepEqual(['A', 'B'], controller.markerIds());
        assert.deepEqual(['B'], controller.markerIds({visible: false}));

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

        assert.equal(1, controller.markers().length);
        assert.equal(0, controller.markers({visible: false}).length);
        assert.deepEqual(['C'], controller.markerIds());
        assert.deepEqual([], controller.markerIds({visible: false}));

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

        assert.equal(0, controller.markers().length);
        assert.equal(0, controller.markers({visible: false}).length);
        assert.deepEqual([], controller.markerIds());
        assert.deepEqual([], controller.markerIds({visible: false}));
    });
});

QUnit.test('creme.geolocation.GoogleMapController (marker-click)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    controller.on('marker-click', this.mockListener('marker-click'));

    this.runTestOnGeomapReady(controller, element, function() {
        assert.equal(true, controller.isEnabled());

        assert.equal(false, controller.hasMarker('A'));
        assert.equal(undefined, controller.getMarker('A'));

        var marker = controller.addMarker('A', {
            icon: 'default',
            position: {lat: 43, lng: 5},
            extraData: {address: 'Marseille'}
        });

        assert.deepEqual([], this.mockListenerCalls('marker-click'));

        google.maps.event.trigger(marker, 'click');

        assert.deepEqual([
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
        assert.equal(true, controller.isEnabled());

        assert.equal(false, controller.hasMarker('A'));
        assert.equal(undefined, controller.getMarker('A'));

        var marker = controller.addMarker('A', {
            draggable: true,
            icon: 'default',
            position: {lat: 43, lng: 5},
            extraData: {address: 'Marseille'}
        });

        assert.deepEqual([], this.mockListenerCalls('marker-dragstart'));
        assert.deepEqual([], this.mockListenerCalls('marker-dragstop'));

        google.maps.event.trigger(marker, 'dragstart');

        assert.deepEqual([
            ['marker-dragstart', {
                id: 'A',
                extraData: {address: 'Marseille'},
                dragStartPosition: {lat: 43, lng: 5}
            }]
        ], this.mockListenerCalls('marker-dragstart').map(function(e) {
            return [e[0], e[1]];
        }));
        assert.deepEqual([], this.mockListenerCalls('marker-dragstop'));

        marker.setPosition({lat: 42, lng: 5.5});
        google.maps.event.trigger(marker, 'dragend');

        assert.deepEqual([
            ['marker-dragstart', {
                id: 'A',
                extraData: {address: 'Marseille'},
                dragStartPosition: {lat: 43, lng: 5}
            }]
        ], this.mockListenerCalls('marker-dragstart').map(function(e) {
            return [e[0], e[1]];
        }));
        assert.deepEqual([
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
        assert.equal(false, controller.hasShape('A'));
        assert.equal(undefined, controller.getShape('A'));
        assert.equal(0, controller.shapes().length);
        assert.equal(0, controller.shapes({visible: false}).length);
        assert.equal(0, controller.shapeIds().length);
        assert.equal(0, controller.shapeIds({visible: false}).length);


        var shape = controller.addShape('A', {
            position: {lat: 43, lng: 5},
            radius: 5,
            shape: 'circle',
            extraData: {
                url: 'mock/shape'
            }
        });

        assert.equal(false, Object.isNone(shape));
        assert.equal(true, shape.getVisible());
        assert.equal(5, shape.getRadius());
        assert.deepEqual(new google.maps.LatLng({lat: 43, lng: 5}), shape.getCenter());
        assert.deepEqual({
            id: 'A',
            extraData: {
                url: 'mock/shape'
            }
        }, shape.__extra);

        assert.equal(1, controller.shapes().length);
        assert.equal(0, controller.shapes({visible: false}).length);

        assert.deepEqual(['A'], controller.shapeIds());
        assert.deepEqual([], controller.shapeIds({visible: false}));
    });
});

QUnit.test('creme.geolocation.GoogleMapController.addShape (unknown type)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        assert.equal(false, controller.hasShape('A'));
        assert.equal(undefined, controller.getShape('A'));
        assert.equal(0, controller.shapes().length);
        assert.equal(0, controller.shapes({visible: false}).length);
        assert.equal(0, controller.shapeIds().length);
        assert.equal(0, controller.shapeIds({visible: false}).length);

        this.assertRaises(function() {
            controller.addShape('A', {
                position: {lat: 52, lng: 6},
                radius: 10,
                shape: 'cloud'
            });
        }, Error, 'Error: Shape has unknown type "cloud"');

        assert.equal(false, controller.hasShape('A'));
        assert.equal(undefined, controller.getShape('A'));
        assert.equal(0, controller.shapes().length);
        assert.equal(0, controller.shapes({visible: false}).length);
    });
});

QUnit.test('creme.geolocation.GoogleMapController.addShape (empty id)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        assert.equal(false, controller.hasShape('A'));
        assert.equal(undefined, controller.getShape('A'));
        assert.equal(0, controller.shapes().length);
        assert.equal(0, controller.shapes({visible: false}).length);
        assert.equal(0, controller.shapeIds().length);
        assert.equal(0, controller.shapeIds({visible: false}).length);

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

        assert.equal(false, controller.hasShape('A'));
        assert.equal(undefined, controller.getShape('A'));
        assert.equal(0, controller.shapes().length);
        assert.equal(0, controller.shapes({visible: false}).length);
    });
});


QUnit.test('creme.geolocation.GoogleMapController.addShape (already exists)', function(assert) {
    var controller = new creme.geolocation.GoogleMapController({
        apiKey: 'thisisanapikey'
    });
    var element = $(this.createMapHtml()).appendTo(this.qunitFixture());

    this.runTestOnGeomapReady(controller, element, function() {
        assert.equal(false, controller.hasShape('A'));
        assert.equal(undefined, controller.getShape('A'));
        assert.equal(0, controller.shapes().length);
        assert.equal(0, controller.shapes({visible: false}).length);

        var shape = controller.addShape('A', {
            position: {lat: 43, lng: 5},
            radius: 5,
            shape: 'circle'
        });

        assert.equal(false, Object.isNone(shape));
        assert.equal(true, shape.getVisible());
        assert.equal(5, shape.getRadius());
        assert.deepEqual(new google.maps.LatLng({lat: 43, lng: 5}), shape.getCenter());

        assert.equal(1, controller.shapes().length);
        assert.equal(0, controller.shapes({visible: false}).length);

        assert.deepEqual(['A'], controller.shapeIds());
        assert.deepEqual([], controller.shapeIds({visible: false}));

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

        assert.equal(false, Object.isNone(shape));
        assert.equal(true, shape.getVisible());
        assert.equal(5, shape.getRadius());
        assert.deepEqual(new google.maps.LatLng({lat: 43, lng: 5}), shape.getCenter());

        assert.equal(1, controller.shapes().length);
        assert.equal(0, controller.shapes({visible: false}).length);

        controller.updateShape('A', {
            position: {lat: 43.5, lng: 5.53},
            radius: 2,
            extraData: {
                address: 'Marseille'
            }
        });

        shape = controller.getShape('A');
        assert.equal(true, shape.getVisible());
        assert.equal(2, shape.getRadius());
        assert.deepEqual(new google.maps.LatLng({lat: 43.5, lng: 5.53}), shape.getCenter());
        assert.deepEqual({
            address: 'Marseille'
        }, shape.__extra.extraData);

        assert.equal(1, controller.shapes().length);
        assert.equal(0, controller.shapes({visible: false}).length);
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

        assert.equal(false, Object.isNone(shape));
        assert.equal(true, shape.getVisible());
        assert.equal(5, shape.getRadius());
        assert.deepEqual(new google.maps.LatLng({lat: 43, lng: 5}), shape.getCenter());

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
        assert.deepEqual(
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
        assert.deepEqual(marker.getPosition(), controller.map().getCenter());
        assert.equal(controller.options().defaultZoomValue, controller.map().getZoom());
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
        assert.deepEqual(bounds.getCenter(), controller.map().getCenter());

        // 1 visible marker, center map on it
        controller.toggleMarker('A', false);
        controller.toggleMarker('B', false);

        assert.deepEqual(markerC.getPosition(), controller.map().getCenter());

        controller.toggleMarker('A', true);
        controller.toggleMarker('B', false);
        controller.toggleMarker('C', false);

        assert.deepEqual(markerA.getPosition(), controller.map().getCenter());

        // no visible marker, center on default
        controller.toggleMarker('A', false);

        assert.equal(0, controller.markers({visible: true}).length);

        assert.deepEqual(
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
        assert.deepEqual(shape.getCenter(), controller.map().getCenter());
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
        assert.deepEqual(
            new google.maps.LatLng(controller.options().defaultLat, controller.options().defaultLng),
            controller.map().getCenter()
        );
    });
});

}(jQuery, QUnit));
