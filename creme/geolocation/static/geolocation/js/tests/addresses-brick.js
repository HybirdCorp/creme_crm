/* globals QUnitGeolocationMixin */
(function($, QUnit) {
"use strict";

QUnit.module("creme.geolocation.addresses-brick", new QUnitMixin(QUnitEventMixin,
                                                                 QUnitAjaxMixin,
                                                                 QUnitBrickMixin,
                                                                 QUnitGeolocationMixin, {
    beforeEach: function() {
        var self = this;
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        this.setMockBackendGET({
            'mock/addresses': function(url, data, options) {
                return backend.responseJSON(200, {
                    addresses: self.defaultAddresses().filter(function(a) {
                        return data.id && (a.group || '').indexOf(data.id) !== -1;
                    })
                });
            },
            'mock/addresses/fail': backend.response(400, 'Invalid addresses')
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
            longitude: 5.403022,
            url: 'mock/address/Address_A',
            group: 'A1'
        }, {
            id: 'Address_B',
            selected: true,
            title: 'Address B',
            content: 'Place inconnue, 13005 Marseille',
            status: creme.geolocation.LocationStatus.PARTIAL,
            latitude: 43,
            longitude: 5.5,
            url: 'mock/address/Address_B',
            group: 'A1 A2'
        }, {
            id: 'Address_C',
            selected: true,
            title: 'Address C',
            content: '13013 Marseille',
            status: creme.geolocation.LocationStatus.MANUAL,
            latitude: 42,
            longitude: 5,
            url: 'mock/address/Address_C',
            group: 'A1 B1 B2'
        }, {
            id: 'Address_D',
            selected: false,
            title: 'Address D',
            content: 'marseille',
            status: creme.geolocation.LocationStatus.UNDEFINED,
            url: 'mock/address/Address_D',
            group: 'A1 B2'
        }];
    },

    renderAddressFilterGroupHtml: function(group) {
        group = group || {};

        return (
           '<optgroup label="${group}">${choices}</optgroup>'
        ).template({
            group: group.name,
            choices: (group.items || []).map(function(item) {
                return '<option value="${value}">${label}</option>'.template(item);
            }).join('')
        });
    },

    createAddressesBrickHtml: function(options) {
        options = $.extend({
            filters: []
        }, options || {});

        var content = (
            '<div class="geolocation-brick-header">' +
                '<span class="brick-geoaddress-counter">No address from</span>' +
                '<select class="brick-geoaddress-filter">${filters}</select>' +
            '</div>' +
            '<div class="brick-geoaddress-error">${config}</div>' +
            '<div class="brick-geoaddress-canvas" style="width: 100px; height: 100px;"></div>'
        ).template({
            filters: options.filters.map(this.renderAddressFilterGroupHtml.bind(this)).join(''),
            config: this.createBrickActionHtml({
                action: 'redirect',
                url: 'mock/apikey/config'
            })
        });

        return this.createBrickHtml($.extend({
            content: content
        }, options));
    },

    createAddressesBrick: function(options) {
        var html = this.createAddressesBrickHtml(options);

        var element = $(html).appendTo(this.qunitFixture());
        var widget = creme.widget.create(element);
        var brick = widget.brick();

        this.assert.equal(true, brick.isBound());
        this.assert.equal(false, brick.isLoading());

        return widget;
    }
}));

QUnit.parametrize('creme.geolocation.brick.AddressesBrick (defaults)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var self = this;
    var brick = this.createAddressesBrick({}).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');
    var filter = brick.element().find('.brick-geoaddress-filter');
    var counter = brick.element().find('.brick-geoaddress-counter');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;

        assert.deepEqual(canvas.get(), controller.canvas().get());
        assert.deepEqual(filter.get(), controller.filterSelector().get());
        assert.deepEqual(counter.get(), controller.counterItem().get());
        assert.equal(undefined, controller.addressesUrl());
        assert.deepEqual([], controller.addresses());

        assert.deepEqual(canvas.get(), controller.mapController().element().get());
        assert.equal(true, controller.mapController().isBound());
        assert.equal(true, controller.mapController().isEnabled());
        assert.equal(true, controller.mapController().isMapEnabled());
        assert.equal(true, controller.mapController().isGeocoderEnabled());

        /* google maps specific */
        if (mapController instanceof creme.geolocation.GoogleMapController) {
            assert.equal(true, controller.mapController().isAPIReady());
            assert.equal(undefined, controller.mapController().options().apiKey);
        }

        var done = assert.async();

        setTimeout(function() {
            assert.equal(null, brick.element().find('.brick-geoaddress-filter').val());
            assert.equal(gettext('No address from'), brick.element().find('.brick-geoaddress-counter').text());
            assert.equal(0, controller.mapController().markers().length);

            done();
        }, 0);
    });

    this.controller = new creme.geolocation.AddressesBrick(brick, {
        mapController: mapController
    });
});

QUnit.parametrize('creme.geolocation.brick.AddressesBrick (load addresses, no filter)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var brick = this.createAddressesBrick({}).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = this.controller;
        var done = assert.async();

        assert.equal('mock/addresses', controller.addressesUrl());

        setTimeout(function() {
            assert.deepEqual([], this.mockBackendUrlCalls('mock/addresses'));

            assert.equal(null, brick.element().find('.brick-geoaddress-filter').val());
            assert.equal(gettext('No address from'), brick.element().find('.brick-geoaddress-counter').text());
            assert.equal(0, controller.mapController().markers().length);

            done();
        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.AddressesBrick(brick, {
        mapController: mapController,
        addressesUrl: 'mock/addresses'
    });
});

QUnit.parametrize('creme.geolocation.brick.AddressesBrick (load addresses)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var brick = this.createAddressesBrick({
        filters: [
            {
                name: 'Group A',
                items: [
                    {value: 'A1', label: 'Contact A1'},
                    {value: 'A2', label: 'Contact A2'}
                ]
            }, {
                name: 'Group B',
                items: [
                    {value: 'B1', label: 'Orga A1'}
                ]
            }
        ]
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');
    var addresses = this.defaultAddresses();

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = this.controller;

        assert.equal('mock/addresses', controller.addressesUrl());
        var done = assert.async();

        setTimeout(function() {
            assert.deepEqual([
                ['mock/addresses', 'GET', {id: 'A1'}]
            ], this.mockBackendUrlCalls());

            assert.equal('A1', brick.element().find('.brick-geoaddress-filter').val());
            assert.equal(
                ngettext('%0$d address from', '%0$d addresses from', 3).format(3),
                brick.element().find('.brick-geoaddress-counter').text()
            );
            assert.equal(3, controller.mapController().markers().length);

            assert.deepEqual([
                new creme.geolocation.Location(addresses[0]),
                new creme.geolocation.Location(addresses[1]),
                new creme.geolocation.Location(addresses[2]),
                new creme.geolocation.Location(addresses[3])
            ], controller.addresses());

            done();
        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.AddressesBrick(brick, {
        mapController: mapController,
        addressesUrl: 'mock/addresses'
    });
});

QUnit.parametrize('creme.geolocation.brick.AddressesBrick (load addresses, fail)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var brick = this.createAddressesBrick({
        filters: [
            {
                name: 'Group A',
                items: [
                    {value: 'A1', label: 'Contact A1'},
                    {value: 'A2', label: 'Contact A2'}
                ]
            }, {
                name: 'Group B',
                items: [
                    {value: 'B1', label: 'Orga A1'}
                ]
            }
        ]
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');
    var filter = brick.element().find('.brick-geoaddress-filter');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = this.controller;

        assert.equal('A1', filter.val());
        assert.equal('mock/addresses/fail', controller.addressesUrl());

        setTimeout(function() {
            assert.deepEqual([
                ['mock/addresses/fail', 'GET', {id: 'A1'}]
            ], this.mockBackendUrlCalls());

            assert.equal('A1', filter.val());
            assert.equal(gettext('No address from'), brick.element().find('.brick-geoaddress-counter').text());
            assert.equal(0, controller.mapController().markers().length);
        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.AddressesBrick(brick, {
        mapController: mapController,
        addressesUrl: 'mock/addresses/fail'
    });
});

QUnit.parametrize('creme.geolocation.brick.AddressesBrick (google, click, redirect)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var brick = this.createAddressesBrick({
        filters: [
            {
                name: 'Group A',
                items: [
                    {value: 'A1', label: 'Contact A1'},
                    {value: 'A2', label: 'Contact A2'}
                ]
            }, {
                name: 'Group B',
                items: [
                    {value: 'B1', label: 'Orga A1'}
                ]
            }
        ]
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = this.controller;

        controller.mapController().on('marker-click', this.mockListener('marker-click'));

        assert.equal('mock/addresses', controller.addressesUrl());
        var done = assert.async();

        setTimeout(function() {
            assert.deepEqual([
                ['mock/addresses', 'GET', {id: 'A1'}]
            ], this.mockBackendUrlCalls());
            assert.deepEqual([], this.mockRedirectCalls());
            assert.deepEqual([], this.mockListenerCalls('marker-click'));

            assert.equal('A1', brick.element().find('.brick-geoaddress-filter').val());
            assert.equal(
                ngettext('%0$d address from', '%0$d addresses from', 3).format(3),
                brick.element().find('.brick-geoaddress-counter').text()
            );
            assert.equal(3, controller.mapController().markers().length);

            /* google maps specific */
            if (mapController instanceof creme.geolocation.GoogleMapController) {
                assert.equal(true, controller.mapController().isAPIReady());
                assert.equal(undefined, controller.mapController().options().apiKey);
            }

            this.triggerMarkerClick(controller.mapController().getMarker('Address_C'));

            setTimeout(function() {
                assert.deepEqual([
                    'mock/address/Address_C'
                ], this.mockRedirectCalls());
                assert.deepEqual([
                    ['marker-click', {
                        id: 'Address_C',
                        extraData: {}
                    }]
                ], this.mockListenerCalls('marker-click').map(function(e) {
                    return [e[0], e[1]];
                }));

                done();
            }.bind(this), 0);
        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.AddressesBrick(brick, {
        mapController: mapController,
        addressesUrl: 'mock/addresses'
    });
});


QUnit.parametrize('creme.geolocation.brick.AddressesBrick (update filter)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var brick = this.createAddressesBrick({
        filters: [
            {
                name: 'Group A',
                items: [
                    {value: 'A1', label: 'Contact A1'},
                    {value: 'A2', label: 'Contact A2'}
                ]
            }, {
                name: 'Group B',
                items: [
                    {value: 'B1', label: 'Orga A1'}
                ]
            }
        ]
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');
    var filter = brick.element().find('.brick-geoaddress-filter');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = this.controller;
        var mapController = controller.mapController();

        assert.equal('A1', filter.val());
        assert.equal('mock/addresses', controller.addressesUrl());

        var done = assert.async();

        setTimeout(function() {
            assert.deepEqual([
                ['mock/addresses', 'GET', {id: 'A1'}]
            ], this.mockBackendUrlCalls());

            assert.equal(
                ngettext('%0$d address from', '%0$d addresses from', 3).format(3),
                brick.element().find('.brick-geoaddress-counter').text()
             );
            assert.equal(3, mapController.markers().length);

            filter.val('B1').trigger('change');

            setTimeout(function() {
                assert.deepEqual([
                    ['mock/addresses', 'GET', {id: 'A1'}],
                    ['mock/addresses', 'GET', {id: 'B1'}]
                ], this.mockBackendUrlCalls());

                assert.equal('B1', filter.val());
                assert.equal(gettext('%0$d address from').format(1), brick.element().find('.brick-geoaddress-counter').text());
                assert.equal(1, mapController.markers({visible: true}).length);

                this.assertMarkerProperties(mapController.getMarkerProperties('Address_C'), {
                    position: {lat: 42, lng: 5},
                    id: 'Address_C',
                    title: '13013 Marseille\n(Address C)',
                    visible: true,
                    extraData: {}
                });

                done();
            }.bind(this), 0);
        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.AddressesBrick(brick, {
        mapController: new creme.geolocation.GoogleMapController(),
        addressesUrl: 'mock/addresses'
    });
});

QUnit.parametrize('creme.geolocation.brick.AddressesBrick (update filter, fail)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var brick = this.createAddressesBrick({
        filters: [
            {
                name: 'Group A',
                items: [
                    {value: 'A1', label: 'Contact A1'},
                    {value: 'A2', label: 'Contact A2'}
                ]
            }, {
                name: 'Group B',
                items: [
                    {value: 'B1', label: 'Orga A1'}
                ]
            }
        ]
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');
    var filter = brick.element().find('.brick-geoaddress-filter');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = this.controller;
        var mapController = controller.mapController();
        var done = assert.async();

        assert.equal('A1', filter.val());
        assert.equal('mock/addresses', controller.addressesUrl());

        setTimeout(function() {
            assert.deepEqual([
                ['mock/addresses', 'GET', {id: 'A1'}]
            ], this.mockBackendUrlCalls());

            assert.equal(
                ngettext('%0$d address from', '%0$d addresses from', 3).format(3),
                brick.element().find('.brick-geoaddress-counter').text()
             );
            assert.equal(3, mapController.markers().length);

            controller.addressesUrl('mock/addresses/fail');

            filter.val('B1').trigger('change');

            setTimeout(function() {
                assert.deepEqual([
                    ['mock/addresses', 'GET', {id: 'A1'}],
                    ['mock/addresses/fail', 'GET', {id: 'B1'}]
                ], this.mockBackendUrlCalls());

                assert.equal(null, filter.val());
                assert.equal(gettext('No address from'), brick.element().find('.brick-geoaddress-counter').text());
                assert.equal(0, mapController.markers({visible: true}).length);

                done();
            }.bind(this), 0);

        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.AddressesBrick(brick, {
        mapController: mapController,
        addressesUrl: 'mock/addresses'
    });
});

QUnit.parametrize('creme.geolocation.brick.AddressesBrick (collapse state)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var brick = this.createAddressesBrick().brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var done = assert.async();

        setTimeout(function() {
            this.autoResizeFaker.reset();
            this.adjustMapFaker.reset();

            assert.equal(0, this.autoResizeFaker.count());
            assert.equal(0, this.adjustMapFaker.count());

            brick.setState({
                collapsed: true
            });

            assert.equal(0, this.autoResizeFaker.count());
            assert.equal(0, this.adjustMapFaker.count());

            brick.setState({
                collapsed: false
            });

            assert.equal(1, this.autoResizeFaker.count());
            assert.equal(1, this.adjustMapFaker.count());

            done();
        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.AddressesBrick(brick, {
        mapController: mapController,
        addressesUrl: 'mock/addresses'
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
});

}(jQuery, QUnit));
