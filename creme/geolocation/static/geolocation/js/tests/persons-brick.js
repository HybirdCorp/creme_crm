/* globals google QUnitGeolocationMixin setTimeout */
(function($, QUnit) {
"use strict";

QUnit.module("creme.geolocation.persons-brick", new QUnitMixin(QUnitEventMixin,
                                                               QUnitAjaxMixin,
                                                               QUnitBrickMixin,
                                                               QUnitGeolocationMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        this.setMockBackendPOST({
            'mock/location/update': this.backend.response(200, ''),
            'mock/location/update/fail': this.backend.response(400, 'Invalid location !')
        });

        this.mockGoogleGeocoder = this.createMockGoogleGeocoder();
    },

    defaultAddresses: function() {
        return [{
            id: 'Address_A',
            selected: true,
            title: 'Address A',
            content: '319 Rue Saint-Pierre, 13005 Marseille',
            status: creme.geolocation.LocationStatus.COMPLETE,
            latitude: 43.291628,
            longitude: 5.403022
        }, {
            id: 'Address_B',
            selected: true,
            title: 'Address B',
            content: 'Place inconnue, 13005 Marseille',
            status: creme.geolocation.LocationStatus.PARTIAL,
            latitude: 43,
            longitude: 5.5
        }, {
            id: 'Address_C',
            selected: true,
            title: 'Address C',
            content: '13013 Marseille',
            status: creme.geolocation.LocationStatus.MANUAL,
            latitude: 42,
            longitude: 5
        }, {
            id: 'Address_D',
            selected: false,
            title: 'Address D',
            content: 'marseille',
            status: creme.geolocation.LocationStatus.UNDEFINED
        }];
    },

    newAddressLocation: function(data) {
        return new creme.geolocation.Location($.extend(data, {
            visible: data.selected,
            position: data.latitude ? {lat: data.latitude, lng: data.longitude} : null
        }));
    },

    renderAddressHtml: function(address) {
        return (
           '<div class="brick-geoaddress-item ${selected}" data-addressid="${id}">' +
               '<input type="checkbox" value="${id}" ${checked}/>' +
               '<div class="brick-geoaddress-label">' +
                   '<span class="brick-geoaddress-title">${title}</span>' +
                   '<span class="brick-geoaddress-content">${content}</span>' +
                '</div>' +
                '<div class="brick-geoaddress-action ${iscomplete}">' +
                    '<a class="brick-geoaddress-reset" data-addressid="${id}">Retrieve location</a>' +
                    '<span class="brick-geoaddress-position">${position}</span>' +
                    '<span class="brick-geoaddress-status">${status}</span>' +
                '</div>' +
            '</div>'
        ).template({
            id: address.id,
            selected: address.selected ? 'is-mark-visible' : '',
            checked: address.selected ? 'checked' : '',
            title: address.title || '',
            content: address.content || '',
            iscomplete: address.status === creme.geolocation.LocationStatus.COMPLETE ? ' brick-geoaddress-iscomplete' : '',
            status: creme.geolocation.locationStatusLabel(address.status),
            position: address.latitude ? '%3.6f, %3.6f'.format(address.latitude, address.longitude) : ''
        });
    },

    createPersonsBrickHtml: function(options) {
        options = $.extend({
            addresses: []
        }, options || {});

        var content = '<div class="geolocation-empty-brick">No address defined for now</div>';

        if (options.addresses) {
            content = '<div class="geolocation-brick-items">${addresses}</div>'.template({
                addresses: options.addresses.map(this.renderAddressHtml.bind(this)).join('')
            });
        }

        content += (
            '<div class="brick-geoaddress-error">${config}</div>' +
            '<div class="brick-geoaddress-canvas" style="width: 100px; height: 100px;"></div>'
        ).template({
            config: this.createBrickActionHtml({
                action: 'redirect',
                url: 'mock/apikey/config'
            })
        });

        return this.createBrickHtml($.extend({
            content: content
        }, options));
    },

    createPersonsBrick: function(options) {
        var html = this.createPersonsBrickHtml(options);

        var element = $(html).appendTo(this.qunitFixture());
        var widget = creme.widget.create(element);
        var brick = widget.brick();

        equal(true, brick.isBound());
        equal(false, brick.isLoading());

        return widget;
    },

    assertAddressItem: function(item, expected) {
        equal(1, item.size());
        equal(expected.id, item.attr('data-addressid'));
        equal(expected.selected, item.find('input[type="checkbox"]').is(':checked'));
        equal(expected.selected, item.is('.is-mark-visible'));
        equal(expected.statusLabel, item.find('.brick-geoaddress-status').text());
        equal(expected.isComplete, item.find('.brick-geoaddress-action').is('.brick-geoaddress-iscomplete'), 'is address complete');
        equal(expected.positionLabel, item.find('.brick-geoaddress-position').text());
    }
}));

QUnit.test('creme.geolocation.brick.PersonsBrick (google, defaults)', function(assert) {
    var self = this;
    var brick = this.createPersonsBrick({}).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;

        deepEqual([], controller.addresses());
        equal(undefined, controller.locationUrl());
        deepEqual(canvas, controller.canvas());
        deepEqual(canvas, controller.mapController().element());
        equal(0, controller.addressItems().size());

        equal(true, controller.mapController().isBound());
        equal(true, controller.mapController().isEnabled());
        equal(true, controller.mapController().isMapEnabled());
        equal(true, controller.mapController().isGeocoderEnabled());
        equal(true, controller.mapController().isAPIReady());
        equal(undefined, controller.mapController().options().apiKey);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: new creme.geolocation.GoogleMapController()
    });

    stop(1);
});

QUnit.test('creme.geolocation.brick.PersonsBrick (google, no geocoder)', function(assert) {
    var self = this;
    var brick = this.createPersonsBrick({}).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;

        deepEqual([], controller.addresses());
        equal(undefined, controller.locationUrl());
        deepEqual(canvas, controller.canvas());
        deepEqual(canvas, controller.mapController().element());
        equal(0, controller.addressItems().size());

        equal(true, controller.mapController().isBound());
        equal(true, controller.mapController().isEnabled());
        equal(true, controller.mapController().isMapEnabled());
        equal(false, controller.mapController().isGeocoderEnabled());
        equal(true, controller.mapController().isAPIReady());
        equal(undefined, controller.mapController().options().apiKey);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: new creme.geolocation.GoogleMapController({
            allowGeocoder: false
        })
    });

    stop(1);
});

QUnit.test('creme.geolocation.brick.PersonsBrick (google, no id addresses)', function(assert) {
    var addresses = [
            {content: 'unknown'}
        ];
    var brick = this.createPersonsBrick().brick();

    this.assertRaises(function() {
        return new creme.geolocation.PersonsBrick(brick, {
            mapController: new creme.geolocation.GoogleMapController(),
            addresses: addresses
        });
    }, Error, 'Error: PersonsBrick : empty address id');
});

QUnit.test('creme.geolocation.brick.PersonsBrick (google, duplicate addresses)', function(assert) {
    var addresses = [{
            id: 'Address_A',
            content: '319 Rue Saint-Pierre, 13005 Marseille'
        }, {
            id: 'Address_A',
            content: '319 Rue Saint-Pierre, 13005 Marseille'
        }];
    var brick = this.createPersonsBrick().brick();

    this.assertRaises(function() {
        return new creme.geolocation.PersonsBrick(brick, {
            mapController: new creme.geolocation.GoogleMapController(),
            addresses: addresses
        });
    }, Error, 'Error: PersonsBrick : address "Address_A" already exists');
});

QUnit.test('creme.geolocation.brick.PersonsBrick (google, addresses)', function(assert) {
    var self = this;
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        deepEqual(addresses.map(self.newAddressLocation), controller.addresses());

        deepEqual(canvas, controller.canvas());
        deepEqual(canvas, mapController.element());
        equal(4, controller.addressItems().size());

        equal(true, mapController.isMapEnabled());
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: new creme.geolocation.GoogleMapController(),
        addresses: addresses
    });

    stop(1);
});

QUnit.test('creme.geolocation.brick.PersonsBrick (google, addressItem)', function(assert) {
    var self = this;
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        mapController._geocoder = self.mockGoogleGeocoder;

        deepEqual(addresses.map(self.newAddressLocation), controller.addresses());
        equal(4, controller.addressItems().size());

        // unknown item returns empty query
        equal(0, controller.addressItem('Unknown').size());

        self.assertAddressItem(controller.addressItem('Address_A'), {
            id: 'Address_A',
            selected: true,
            statusLabel: '',
            isComplete: true,
            positionLabel: '43.291628, 5.403022'
        });
        self.assertAddressItem(controller.addressItem('Address_B'), {
            id: 'Address_B',
            selected: true,
            statusLabel: gettext("Partially matching location"),
            isComplete: false,
            positionLabel: '43.000000, 5.500000'
        });
        self.assertAddressItem(controller.addressItem('Address_C'), {
            id: 'Address_C',
            selected: true,
            statusLabel: gettext("Manual location"),
            isComplete: false,
            positionLabel: '42.000000, 5.000000'
        });
        self.assertAddressItem(controller.addressItem('Address_D'), {
            id: 'Address_D',
            selected: false,
            statusLabel: gettext("Not localized"),
            isComplete: false,
            positionLabel: ''
        });
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: new creme.geolocation.GoogleMapController(),
        addresses: addresses
    });

    stop(1);
});

QUnit.test('creme.geolocation.brick.PersonsBrick (google, markers)', function(assert) {
    var self = this;
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        mapController._geocoder = self.mockGoogleGeocoder;

        deepEqual(addresses.map(self.newAddressLocation), controller.addresses());
        equal(4, controller.addressItems().size());

        setTimeout(function() {
            equal(3, mapController.markers().length);
            this.assertGoogleMarker(mapController.getMarker('Address_A'), {
                position: {lat: 43.291628, lng: 5.403022},
                id: 'Address_A',
                title: 'Address A',
                visible: true,
                extraData: {}
            });
            this.assertGoogleMarker(mapController.getMarker('Address_B'), {
                position: {lat: 43, lng: 5.5},
                id: 'Address_B',
                title: 'Address B',
                visible: true,
                extraData: {}
            });
            this.assertGoogleMarker(mapController.getMarker('Address_C'), {
                position: {lat: 42, lng: 5},
                id: 'Address_C',
                title: 'Address C',
                visible: true,
                extraData: {}
            });

            start();
        }.bind(this), 0);

        stop(1);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: new creme.geolocation.GoogleMapController(),
        addresses: addresses
    });

    stop(1);
});

QUnit.test('creme.geolocation.brick.PersonsBrick (google, toggle mark)', function(assert) {
    var self = this;
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        mapController._geocoder = self.mockGoogleGeocoder;

        deepEqual(addresses.map(self.newAddressLocation), controller.addresses());
        equal(4, controller.addressItems().size());

        setTimeout(function() {
            equal(3, mapController.markers().length);

            this.assertGoogleMarker(mapController.getMarker('Address_A'), {
                position: {lat: 43.291628, lng: 5.403022},
                id: 'Address_A',
                title: 'Address A',
                visible: true,
                extraData: {}
            });
            this.assertAddressItem(controller.addressItem('Address_A'), {
                id: 'Address_A',
                selected: true,
                statusLabel: '',
                isComplete: true,
                positionLabel: '43.291628, 5.403022'
            });

            controller.addressItem('Address_A').find('input[type="checkbox"]').click();

            equal(3, mapController.markers().length);
            this.assertGoogleMarker(mapController.getMarker('Address_A'), {
                position: {lat: 43.291628, lng: 5.403022},
                id: 'Address_A',
                title: 'Address A',
                visible: false,
                extraData: {}
            });
            this.assertAddressItem(controller.addressItem('Address_A'), {
                id: 'Address_A',
                selected: false,
                statusLabel: '',
                isComplete: true,
                positionLabel: '43.291628, 5.403022'
            });

            controller.addressItem('Address_A').find('input[type="checkbox"]').click();

            equal(3, mapController.markers().length);
            this.assertGoogleMarker(mapController.getMarker('Address_A'), {
                position: {lat: 43.291628, lng: 5.403022},
                id: 'Address_A',
                title: 'Address A',
                visible: true,
                extraData: {}
            });
            this.assertAddressItem(controller.addressItem('Address_A'), {
                id: 'Address_A',
                selected: true,
                statusLabel: '',
                isComplete: true,
                positionLabel: '43.291628, 5.403022'
            });

            start();
        }.bind(this), 0);

        stop(1);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: new creme.geolocation.GoogleMapController(),
        addresses: addresses
    });

    stop(1);
});

QUnit.test('creme.geolocation.brick.PersonsBrick (google, add mark)', function(assert) {
    var self = this;
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        mapController._geocoder = self.mockGoogleGeocoder;

        deepEqual(addresses.map(self.newAddressLocation), controller.addresses());
        equal(4, controller.addressItems().size());

        setTimeout(function() {
            equal(3, mapController.markers().length);
            equal(undefined, mapController.getMarker('Address_D'));

            controller.addressItem('Address_D').find('input[type="checkbox"]').click();

            setTimeout(function() {
                equal(4, mapController.markers().length);
                this.assertAddressItem(controller.addressItem('Address_D'), {
                    id: 'Address_D',
                    selected: true,
                    statusLabel: gettext("Partially matching location"),
                    isComplete: false,
                    positionLabel: '42.000000, 12.000000'
                });
                this.assertGoogleMarker(mapController.getMarker('Address_D'), {
                    position: {lat: 42, lng: 12},
                    id: 'Address_D',
                    title: 'Address D',
                    visible: true,
                    extraData: {}
                });

                deepEqual([
                    ['POST', {
                        id: 'Address_D',
                        latitude:  42,
                        longitude: 12,
                        geocoded:  true,
                        status:    creme.geolocation.LocationStatus.PARTIAL
                    }]
                ], this.mockBackendUrlCalls('mock/location/update'));

                controller.addressItem('Address_D').find('input[type="checkbox"]').click();

                this.assertAddressItem(controller.addressItem('Address_D'), {
                    id: 'Address_D',
                    selected: false,
                    statusLabel: gettext("Partially matching location"),
                    isComplete: false,
                    positionLabel: '42.000000, 12.000000'
                });
                this.assertGoogleMarker(mapController.getMarker('Address_D'), {
                    position: {lat: 42, lng: 12},
                    id: 'Address_D',
                    title: 'Address D',
                    visible: false,
                    extraData: {}
                });

                start();
            }.bind(this), 0);
        }.bind(this), 0);

        stop(1);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: new creme.geolocation.GoogleMapController(),
        addresses: addresses,
        locationUrl: '/mock/location/update'
    });

    stop(1);
});

QUnit.test('creme.geolocation.brick.PersonsBrick (google, move mark, save)', function(assert) {
    var self = this;
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        setTimeout(function() {
            var marker = mapController.getMarker('Address_A');
            equal(false, Object.isNone(marker));

            google.maps.event.trigger(marker, 'dragstart');
            marker.setPosition({lat: 42, lng: 5.5});
            google.maps.event.trigger(marker, 'dragend');

            deepEqual([
                ['POST', {
                    id: 'Address_A',
                    latitude:  42,
                    longitude: 5.5,
                    geocoded:  true,
                    status:    creme.geolocation.LocationStatus.MANUAL
                }]
            ], this.mockBackendUrlCalls('mock/location/update'));

            deepEqual(new google.maps.LatLng({lat: 42, lng: 5.5}), marker.getPosition());

            this.assertAddressItem(controller.addressItem('Address_A'), {
                id: 'Address_A',
                selected: true,
                statusLabel: gettext("Manual location"),
                isComplete: false,
                positionLabel: '42.000000, 5.500000'
            });
            this.assertGoogleMarker(mapController.getMarker('Address_A'), {
                position: {lat: 42, lng: 12},
                id: 'Address_A',
                title: 'Address A',
                visible: true,
                extraData: {}
            });

        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: new creme.geolocation.GoogleMapController(),
        addresses: addresses,
        locationUrl: '/mock/location/update'
    });

    stop(1);
});

QUnit.test('creme.geolocation.brick.PersonsBrick (google, move mark, save failed)', function(assert) {
    var self = this;
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        setTimeout(function() {
            var marker = mapController.getMarker('Address_A');
            equal(false, Object.isNone(marker));

            google.maps.event.trigger(marker, 'dragstart');
            marker.setPosition({lat: 42, lng: 5.5});
            google.maps.event.trigger(marker, 'dragend');

            deepEqual([
                ['POST', {
                    id: 'Address_A',
                    latitude:  42,
                    longitude: 5.5,
                    geocoded:  true,
                    status:    creme.geolocation.LocationStatus.MANUAL
                }]
            ], this.mockBackendUrlCalls('mock/location/update/fail'));

            // Rollback to previous position
            deepEqual(new google.maps.LatLng({lat: 43.291628, lng: 5.403022}), marker.getPosition());
        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: new creme.geolocation.GoogleMapController(),
        addresses: addresses,
        locationUrl: '/mock/location/update/fail'
    });

    stop(1);
});

QUnit.test('creme.geolocation.brick.PersonsBrick (google, move mark, no url)', function(assert) {
    var self = this;
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        setTimeout(function() {
            var marker = mapController.getMarker('Address_A');
            equal(false, Object.isNone(marker));

            google.maps.event.trigger(marker, 'dragstart');
            marker.setPosition({lat: 42, lng: 5.5});
            google.maps.event.trigger(marker, 'dragend');

            deepEqual([], this.mockBackendUrlCalls());

            // Rollback to previous position
            deepEqual(new google.maps.LatLng({lat: 43.291628, lng: 5.403022}), marker.getPosition());
            start();
        }.bind(this), 0);

        stop(1);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: new creme.geolocation.GoogleMapController(),
        addresses: addresses
    });

    stop(1);
});

QUnit.test('creme.geolocation.brick.PersonsBrick (google, reset, no geolocation)', function(assert) {
    var self = this;
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        setTimeout(function() {
            var marker = mapController.getMarker('Address_C');

            controller.addressItem('Address_C').find('.brick-geoaddress-reset').click();
            deepEqual([], this.mockBackendUrlCalls());

            this.assertGoogleMarker(mapController.getMarker('Address_C'), {
                position: {lat: 42, lng: 5},
                id: 'Address_C',
                title: 'Address C',
                visible: true,
                extraData: {}
            });

            this.assertAddressItem(controller.addressItem('Address_C'), {
                id: 'Address_C',
                selected: true,
                statusLabel: gettext("Manual location"),
                isComplete: false,
                positionLabel: '42.000000, 5.000000'
            });

            var address = controller.address('Address_C');
            deepEqual({lat: 42, lng: 5}, address.position());
            equal(false, address.isComplete());
            equal(true, address.visible());
            equal(creme.geolocation.LocationStatus.MANUAL, address.status());

            // Rollback to previous position
            deepEqual(new google.maps.LatLng({lat: 43, lng: 5.5}), marker.getPosition());
            start();
        }.bind(this), 50);

        stop(1);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: new creme.geolocation.GoogleMapController({
            allowGeocoder: false
        }),
        addresses: addresses,
        locationUrl: '/mock/location/update'
    });

    stop(1);
});

QUnit.test('creme.geolocation.brick.PersonsBrick (google, reset, not found)', function(assert) {
    var self = this;
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    brick.element().on('brick-geoaddress-location-save', this.mockListener('location-save'));

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        mapController._geocoder = self.mockGoogleGeocoder;

        setTimeout(function() {
            controller.addressItem('Address_B').find('.brick-geoaddress-reset').click();

            setTimeout(function() {
                deepEqual([], this.mockBackendUrlCalls());
                deepEqual([], this.mockListenerJQueryCalls('location-save'));

                this.assertGoogleMarker(mapController.getMarker('Address_B'), {
                    position: {lat: 43, lng: 5.5},
                    id: 'Address_B',
                    title: 'Address B',
                    visible: true,
                    extraData: {}
                });

                this.assertAddressItem(controller.addressItem('Address_B'), {
                    id: 'Address_B',
                    selected: true,
                    statusLabel: gettext("Not localized"),
                    isComplete: false,
                    positionLabel: '43.000000, 5.500000'
                });

                var address = controller.address('Address_B');
                deepEqual({lat: 43, lng: 5.5}, address.position());
                equal(false, address.isComplete());
                equal(true, address.visible());
                equal(creme.geolocation.LocationStatus.UNDEFINED, address.status());

                start();
            }.bind(this), 50);
        }.bind(this), 50);

        stop(1);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: new creme.geolocation.GoogleMapController(),
        addresses: addresses,
        locationUrl: '/mock/location/update'
    });

    stop(1);
});

QUnit.test('creme.geolocation.brick.PersonsBrick (google, reset, not visible)', function(assert) {
    var self = this;
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    brick.element().on('brick-geoaddress-location-save', this.mockListener('location-save'));

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        mapController._geocoder = self.mockGoogleGeocoder;

        setTimeout(function() {
            controller.addressItem('Address_B').find('input[type="checkbox"]').click();

            this.assertGoogleMarker(mapController.getMarker('Address_B'), {
                position: {lat: 43, lng: 5.5},
                id: 'Address_B',
                title: 'Address B',
                visible: false,
                extraData: {}
            });
            this.assertAddressItem(controller.addressItem('Address_B'), {
                id: 'Address_B',
                selected: false,
                statusLabel: gettext("Partially matching location"),
                isComplete: false,
                positionLabel: '43.000000, 5.500000'
            });

            // hidden address, do nothing
            controller.addressItem('Address_B').find('.brick-geoaddress-reset').click();

            setTimeout(function() {
                deepEqual([], this.mockBackendUrlCalls());
                deepEqual([], this.mockListenerJQueryCalls('location-save'));

                this.assertGoogleMarker(mapController.getMarker('Address_B'), {
                    position: {lat: 43, lng: 5.5},
                    id: 'Address_B',
                    title: 'Address B',
                    visible: false,
                    extraData: {}
                });
                this.assertAddressItem(controller.addressItem('Address_B'), {
                    id: 'Address_B',
                    selected: false,
                    statusLabel: gettext("Partially matching location"),
                    isComplete: false,
                    positionLabel: '43.000000, 5.500000'
                });

                start();
            }.bind(this), 50);
        }.bind(this), 50);

        stop(1);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: new creme.geolocation.GoogleMapController(),
        addresses: addresses,
        locationUrl: '/mock/location/update'
    });

    stop(1);
});

QUnit.test('creme.geolocation.brick.PersonsBrick (google, reset, improve accuracy)', function(assert) {
    var self = this;
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    brick.element().on('brick-geoaddress-location-save', this.mockListener('location-save'));

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        mapController._geocoder = self.mockGoogleGeocoder;

        setTimeout(function() {
            controller.addressItem('Address_C').find('.brick-geoaddress-reset').click();

            setTimeout(function() {
                deepEqual([
                    ['POST', {
                        id: 'Address_C',
                        latitude:  43.178801,
                        longitude: 4.5048807,
                        geocoded:  true,
                        status:    creme.geolocation.LocationStatus.COMPLETE
                    }]
                ], this.mockBackendUrlCalls('mock/location/update'));
                deepEqual([
                    ['brick-geoaddress-location-save', [brick, controller.address('Address_C')]]
                ], this.mockListenerJQueryCalls('location-save'));

                this.assertGoogleMarker(mapController.getMarker('Address_C'), {
                    position: {lat: 43.178801, lng: 4.5048807},
                    id: 'Address_C',
                    title: 'Address C',
                    visible: true,
                    extraData: {}
                });

                this.assertAddressItem(controller.addressItem('Address_C'), {
                    id: 'Address_C',
                    selected: true,
                    statusLabel: '',
                    isComplete: true,
                    positionLabel: '43.178801, 4.504881'
                });

                var address = controller.address('Address_C');
                deepEqual({lat: 43.178801, lng: 4.5048807}, address.position());
                equal(creme.geolocation.LocationStatus.COMPLETE, address.status());
                equal(true, address.isComplete());
                equal(true, address.visible());

                start();
            }.bind(this), 50);
        }.bind(this), 50);

        stop(1);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: new creme.geolocation.GoogleMapController(),
        addresses: addresses,
        locationUrl: '/mock/location/update'
    });

    stop(1);
});

QUnit.test('creme.geolocation.brick.PersonsBrick (google, collapse state)', function(assert) {
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        setTimeout(function() {
            this.autoResizeFaker.reset();
            this.adjustMapFaker.reset();

            equal(0, this.autoResizeFaker.count());
            equal(0, this.adjustMapFaker.count());

            brick.setState({
                collapsed: true
            });

            equal(0, this.autoResizeFaker.count());
            equal(0, this.adjustMapFaker.count());

            brick.setState({
                collapsed: false
            });

            equal(1, this.autoResizeFaker.count());
            equal(1, this.adjustMapFaker.count());

            start();
        }.bind(this), 0);

        stop(1);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: new creme.geolocation.GoogleMapController(),
        addresses: addresses
    });

    this.autoResizeFaker = this.fakeMethod(this.controller.mapController(), 'autoResize', true);
    this.adjustMapFaker = this.fakeMethod(this.controller.mapController(), 'adjustMap', true);

    stop(1);
});

}(jQuery, QUnit));
