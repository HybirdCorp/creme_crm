/* globals QUnitGeolocationMixin */
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
        equal(1, item.length);
        equal(expected.id, item.attr('data-addressid'));
        equal(expected.selected, item.find('input[type="checkbox"]').is(':checked'));
        equal(expected.selected, item.is('.is-mark-visible'));
        equal(expected.statusLabel, item.find('.brick-geoaddress-status').text());
        equal(expected.isComplete, item.find('.brick-geoaddress-action').is('.brick-geoaddress-iscomplete'), 'is address complete');
        equal(expected.positionLabel, item.find('.brick-geoaddress-position').text());
    }
}));

QUnit.parametrize('creme.geolocation.brick.PersonsBrick (defaults)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var self = this;
    var brick = this.createPersonsBrick({}).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;

        deepEqual([], controller.addresses());
        equal(undefined, controller.locationUrl());
        deepEqual(canvas.get(), controller.canvas().get());
        deepEqual(canvas.get(), controller.mapController().element().get());
        equal(0, controller.addressItems().length);

        equal(true, controller.mapController().isBound());
        equal(true, controller.mapController().isEnabled());
        equal(true, controller.mapController().isMapEnabled());
        equal(true, controller.mapController().isGeocoderEnabled());

        // google maps specific
        if (mapController instanceof creme.geolocation.GoogleMapController) {
            equal(true, controller.mapController().isAPIReady());
            equal(undefined, controller.mapController().options().apiKey);
        }
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: mapController
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.PersonsBrick (no geocoder)', [
    [new creme.geolocation.GoogleMapController({
        allowGeocoder: false
    })],
    [new creme.geolocation.LeafletMapController({
        allowGeocoder: false
    })]
], function(mapController, assert) {
    var self = this;
    var brick = this.createPersonsBrick({}).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;

        deepEqual([], controller.addresses());
        equal(undefined, controller.locationUrl());
        deepEqual(canvas.get(), controller.canvas().get());
        deepEqual(canvas.get(), controller.mapController().element().get());
        equal(0, controller.addressItems().length);

        equal(true, controller.mapController().isBound());
        equal(true, controller.mapController().isEnabled());
        equal(true, controller.mapController().isMapEnabled());
        equal(false, controller.mapController().isGeocoderEnabled());

        // google maps specific
        if (mapController instanceof creme.geolocation.GoogleMapController) {
            equal(true, controller.mapController().isAPIReady());
            equal(undefined, controller.mapController().options().apiKey);
        }
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: mapController
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.PersonsBrick (no id addresses)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var addresses = [
            {content: 'unknown'}
        ];
    var brick = this.createPersonsBrick().brick();

    this.assertRaises(function() {
        return new creme.geolocation.PersonsBrick(brick, {
            mapController: mapController,
            addresses: addresses
        });
    }, Error, 'Error: PersonsBrick : empty address id');
});

QUnit.parametrize('creme.geolocation.brick.PersonsBrick (duplicate addresses)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
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
            mapController: mapController,
            addresses: addresses
        });
    }, Error, 'Error: PersonsBrick : address "Address_A" already exists');
});

QUnit.parametrize('creme.geolocation.brick.PersonsBrick (addresses)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
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

        deepEqual(canvas.get(), controller.canvas().get());
        deepEqual(canvas.get(), mapController.element().get());
        equal(4, controller.addressItems().length);

        equal(true, mapController.isMapEnabled());
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: mapController,
        addresses: addresses
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.PersonsBrick (addressItem)', [
    [new creme.geolocation.GoogleMapController(), 'mockGoogleGeocoder'],
    [new creme.geolocation.LeafletMapController(), 'mockOSMGeocoder']
], function(mapController, geocoderName, assert) {
    var self = this;
    var geocoder = this[geocoderName];
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        mapController._geocoder = geocoder;

        deepEqual(addresses.map(self.newAddressLocation), controller.addresses());
        equal(4, controller.addressItems().length);

        // unknown item returns empty query
        equal(0, controller.addressItem('Unknown').length);

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
        mapController: mapController,
        addresses: addresses
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.PersonsBrick (markers)', [
    [new creme.geolocation.GoogleMapController(), 'mockGoogleGeocoder'],
    [new creme.geolocation.LeafletMapController(), 'mockOSMGeocoder']
], function(mapController, geocoderName, assert) {
    var self = this;
    var geocoder = this[geocoderName];
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        mapController._geocoder = geocoder;

        deepEqual(addresses.map(self.newAddressLocation), controller.addresses());
        equal(4, controller.addressItems().length);

        setTimeout(function() {
            equal(3, mapController.markers().length);
            this.assertMarkerProperties(mapController.getMarkerProperties('Address_A'), {
                position: {lat: 43.291628, lng: 5.403022},
                id: 'Address_A',
                title: '319 Rue Saint-Pierre, 13005 Marseille\n(Address A)',
                visible: true,
                extraData: {}
            });
            this.assertMarkerProperties(mapController.getMarkerProperties('Address_B'), {
                position: {lat: 43, lng: 5.5},
                id: 'Address_B',
                title: 'Place inconnue, 13005 Marseille\n(Address B)',
                visible: true,
                extraData: {}
            });
            this.assertMarkerProperties(mapController.getMarkerProperties('Address_C'), {
                position: {lat: 42, lng: 5},
                id: 'Address_C',
                title: '13013 Marseille\n(Address C)',
                visible: true,
                extraData: {}
            });

            start();
        }.bind(this), 0);

        stop(1);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: mapController,
        addresses: addresses
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.PersonsBrick (toggle mark)', [
    [new creme.geolocation.GoogleMapController(), 'mockGoogleGeocoder'],
    [new creme.geolocation.LeafletMapController(), 'mockOSMGeocoder']
], function(mapController, geocoderName, assert) {
    var self = this;
    var geocoder = this[geocoderName];
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        mapController._geocoder = geocoder;

        deepEqual(addresses.map(self.newAddressLocation), controller.addresses());
        equal(4, controller.addressItems().length);

        setTimeout(function() {
            equal(3, mapController.markers().length);

            this.assertMarkerProperties(mapController.getMarkerProperties('Address_A'), {
                position: {lat: 43.291628, lng: 5.403022},
                id: 'Address_A',
                title: '319 Rue Saint-Pierre, 13005 Marseille\n(Address A)',
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

            controller.addressItem('Address_A').find('input[type="checkbox"]').trigger('click');

            equal(3, mapController.markers().length);
            this.assertMarkerProperties(mapController.getMarkerProperties('Address_A'), {
                position: {lat: 43.291628, lng: 5.403022},
                id: 'Address_A',
                title: '319 Rue Saint-Pierre, 13005 Marseille\n(Address A)',
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

            controller.addressItem('Address_A').find('input[type="checkbox"]').trigger('click');

            equal(3, mapController.markers().length);
            this.assertMarkerProperties(mapController.getMarkerProperties('Address_A'), {
                position: {lat: 43.291628, lng: 5.403022},
                id: 'Address_A',
                title: '319 Rue Saint-Pierre, 13005 Marseille\n(Address A)',
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

QUnit.parametrize('creme.geolocation.brick.PersonsBrick (add mark)', [
    [new creme.geolocation.GoogleMapController(), 'mockGoogleGeocoder'],
    [new creme.geolocation.LeafletMapController(), 'mockOSMGeocoder']
], function(mapController, geocoderName, assert) {
    var self = this;
    var geocoder = this[geocoderName];
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        mapController._geocoder = geocoder;

        deepEqual(addresses.map(self.newAddressLocation), controller.addresses());
        equal(4, controller.addressItems().length);

        setTimeout(function() {
            equal(3, mapController.markers().length);
            equal(undefined, mapController.getMarker('Address_D'));

            controller.addressItem('Address_D').find('input[type="checkbox"]').trigger('click');

            setTimeout(function() {
                equal(4, mapController.markers().length);
                this.assertAddressItem(controller.addressItem('Address_D'), {
                    id: 'Address_D',
                    selected: true,
                    statusLabel: gettext("Partially matching location"),
                    isComplete: false,
                    positionLabel: '42.000000, 12.000000'
                });
                this.assertMarkerProperties(mapController.getMarkerProperties('Address_D'), {
                    position: {lat: 42, lng: 12},
                    id: 'Address_D',
                    title: 'marseille\n(Address D)',
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

                controller.addressItem('Address_D').find('input[type="checkbox"]').trigger('click');

                this.assertAddressItem(controller.addressItem('Address_D'), {
                    id: 'Address_D',
                    selected: false,
                    statusLabel: gettext("Partially matching location"),
                    isComplete: false,
                    positionLabel: '42.000000, 12.000000'
                });
                this.assertMarkerProperties(mapController.getMarkerProperties('Address_D'), {
                    position: {lat: 42, lng: 12},
                    id: 'Address_D',
                    title: 'marseille\n(Address D)',
                    visible: false,
                    extraData: {}
                });

                start();
            }.bind(this), 100);
        }.bind(this), 0);

        stop(1);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: mapController,
        addresses: addresses,
        locationUrl: '/mock/location/update'
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.PersonsBrick (move mark, save)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
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

            this.triggerMarkerDragNDrop(marker, {lat: 42, lng: 5.5});

            deepEqual([
                ['POST', {
                    id: 'Address_A',
                    latitude:  42,
                    longitude: 5.5,
                    geocoded:  true,
                    status:    creme.geolocation.LocationStatus.MANUAL
                }]
            ], this.mockBackendUrlCalls('mock/location/update'));

            this.assertAddressItem(controller.addressItem('Address_A'), {
                id: 'Address_A',
                selected: true,
                statusLabel: gettext("Manual location"),
                isComplete: false,
                positionLabel: '42.000000, 5.500000'
            });
            this.assertMarkerProperties(mapController.getMarkerProperties('Address_A'), {
                position: {lat: 42, lng: 5.5},
                id: 'Address_A',
                title: '319 Rue Saint-Pierre, 13005 Marseille\n(Address A)',
                visible: true,
                extraData: {}
            });

        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: mapController,
        addresses: addresses,
        locationUrl: '/mock/location/update'
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.PersonsBrick (move mark, save failed)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
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

            this.triggerMarkerDragNDrop(marker, {lat: 42, lng: 5.5});

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
            this.assertMarkerProperties(mapController.getMarkerProperties('Address_A'), {
                position: {lat: 43.291628, lng: 5.403022},
                id: 'Address_A',
                title: '319 Rue Saint-Pierre, 13005 Marseille\n(Address A)',
                visible: true,
                extraData: {}
            });
        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: mapController,
        addresses: addresses,
        locationUrl: '/mock/location/update/fail'
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.PersonsBrick (move mark, no url)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
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

            this.triggerMarkerDragNDrop(marker, {lat: 42, lng: 5.5});

            deepEqual([], this.mockBackendUrlCalls());

            // Rollback to previous position
            this.assertMarkerProperties(mapController.getMarkerProperties('Address_A'), {
                position: {lat: 43.291628, lng: 5.403022},
                id: 'Address_A',
                title: '319 Rue Saint-Pierre, 13005 Marseille\n(Address A)',
                visible: true,
                extraData: {}
            });

            start();
        }.bind(this), 0);

        stop(1);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: mapController,
        addresses: addresses
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.PersonsBrick (reset, no geolocation)', [
    [new creme.geolocation.GoogleMapController({
        allowGeocoder: false
    })],
    [new creme.geolocation.LeafletMapController({
        allowGeocoder: false
    })]
], function(mapController, assert) {
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
            this.assertMarkerProperties(mapController.getMarkerProperties('Address_C'), {
                position: {lat: 42, lng: 5},
                id: 'Address_C',
                title: '13013 Marseille\n(Address C)',
                visible: true,
                extraData: {}
            });

            controller.addressItem('Address_C').find('.brick-geoaddress-reset').trigger('click');
            deepEqual([], this.mockBackendUrlCalls());

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
            this.assertMarkerProperties(mapController.getMarkerProperties('Address_C'), {
                position: {lat: 42, lng: 5},
                id: 'Address_C',
                title: '13013 Marseille\n(Address C)',
                visible: true,
                extraData: {}
            });

            start();
        }.bind(this), 50);

        stop(1);
    });

    this.controller = new creme.geolocation.PersonsBrick(brick, {
        mapController: mapController,
        addresses: addresses,
        locationUrl: '/mock/location/update'
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.PersonsBrick (reset, not found)', [
    [new creme.geolocation.GoogleMapController(), 'mockGoogleGeocoder'],
    [new creme.geolocation.LeafletMapController(), 'mockOSMGeocoder']
], function(mapController, geocoderName, assert) {
    var self = this;
    var geocoder = this[geocoderName];
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    brick.element().on('brick-geoaddress-location-save', this.mockListener('location-save'));

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        mapController._geocoder = geocoder;

        setTimeout(function() {
            this.assertMarkerProperties(mapController.getMarkerProperties('Address_B'), {
                position: {lat: 43, lng: 5.5},
                id: 'Address_B',
                title: 'Place inconnue, 13005 Marseille\n(Address B)',
                visible: true,
                extraData: {}
            });

            controller.addressItem('Address_B').find('.brick-geoaddress-reset').trigger('click');

            setTimeout(function() {
                deepEqual([], this.mockBackendUrlCalls('mock/location/update'));
                deepEqual([], this.mockListenerJQueryCalls('location-save'));

                this.assertMarkerProperties(mapController.getMarkerProperties('Address_B'), {
                    position: {lat: 43, lng: 5.5},
                    id: 'Address_B',
                    title: 'Place inconnue, 13005 Marseille\n(Address B)',
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
        mapController: mapController,
        addresses: addresses,
        locationUrl: '/mock/location/update'
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.PersonsBrick (reset, not visible)', [
    [new creme.geolocation.GoogleMapController(), 'mockGoogleGeocoder'],
    [new creme.geolocation.LeafletMapController(), 'mockOSMGeocoder']
], function(mapController, geocoderName, assert) {
    var self = this;
    var geocoder = this[geocoderName];
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    brick.element().on('brick-geoaddress-location-save', this.mockListener('location-save'));

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        mapController._geocoder = geocoder;

        setTimeout(function() {
            controller.addressItem('Address_B').find('input[type="checkbox"]').trigger('click');

            this.assertMarkerProperties(mapController.getMarkerProperties('Address_B'), {
                position: {lat: 43, lng: 5.5},
                id: 'Address_B',
                title: 'Place inconnue, 13005 Marseille\n(Address B)',
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
            controller.addressItem('Address_B').find('.brick-geoaddress-reset').trigger('click');

            setTimeout(function() {
                deepEqual([], this.mockBackendUrlCalls('mock/location/update'));
                deepEqual([], this.mockListenerJQueryCalls('location-save'));

                this.assertMarkerProperties(mapController.getMarkerProperties('Address_B'), {
                    position: {lat: 43, lng: 5.5},
                    id: 'Address_B',
                    title: 'Place inconnue, 13005 Marseille\n(Address B)',
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
        mapController: mapController,
        addresses: addresses,
        locationUrl: '/mock/location/update'
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.PersonsBrick (reset, improve accuracy)', [
    [new creme.geolocation.GoogleMapController(), 'mockGoogleGeocoder'],
    [new creme.geolocation.LeafletMapController(), 'mockOSMGeocoder']
], function(mapController, geocoderName, assert) {
    var self = this;
    var geocoder = this[geocoderName];
    var addresses = this.defaultAddresses();
    var brick = this.createPersonsBrick({
        addresses: addresses
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    brick.element().on('brick-geoaddress-location-save', this.mockListener('location-save'));

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;
        var mapController = controller.mapController();

        mapController._geocoder = geocoder;

        setTimeout(function() {
            this.assertMarkerProperties(mapController.getMarkerProperties('Address_C'), {
                position: {lat: 42, lng: 5},
                id: 'Address_C',
                title: '13013 Marseille\n(Address C)',
                visible: true,
                extraData: {}
            });

            controller.addressItem('Address_C').find('.brick-geoaddress-reset').trigger('click');

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

                this.assertMarkerProperties(mapController.getMarkerProperties('Address_C'), {
                    position: {lat: 43.178801, lng: 4.5048807},
                    id: 'Address_C',
                    title: '13013 Marseille\n(Address C)',
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
        mapController: mapController,
        addresses: addresses,
        locationUrl: '/mock/location/update'
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.PersonsBrick (collapse state)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
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
        mapController: mapController,
        addresses: addresses
    });

    this.autoResizeFaker = this.fakeMethod({
        instance: this.controller.mapController(),
        method: 'autoResize',
        follow: true
    });

    this.adjustMapFaker = this.fakeMethod({
        instance: this.controller.mapController(),
        method: 'adjustMap',
        follow: true
    });

    stop(1);
});

}(jQuery, QUnit));
