/* globals QUnitGeolocationMixin */
(function($, QUnit) {
"use strict";

QUnit.module("creme.geolocation.neighborhood-brick", new QUnitMixin(QUnitEventMixin,
                                                                    QUnitAjaxMixin,
                                                                    QUnitBrickMixin,
                                                                    QUnitGeolocationMixin, {
    beforeEach: function() {
        var self = this;
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        this._mockNeighbourAddresses = self.defaultAddressesAsDict();

        this.setMockBackendGET({
            'mock/neighbours': function(url, data, options) {
                var addresses = self._mockNeighbourAddresses;

                if (Object.isEmpty(data.address_id)) {
                    return backend.response(400, 'Invalid address id');
                }

                if (data.filter_id === 'empty') {
                    return backend.responseJSON(200, {
                        source_address: addresses[data.address_id],
                        addresses: []
                    });
                }

                return backend.responseJSON(200, {
                    source_address: addresses[data.address_id],
                    addresses: Object.values(addresses).filter(function(a) {
                        return (a.neighbours || '').indexOf(data.address_id) !== -1;
                    })
                });
            },
            'mock/neighbours/fail': backend.response(400, 'Invalid addresses')
        });
    },

    mockNeighbourAddresses: function() {
        return this._mockNeighbourAddresses;
    },

    defaultAddressesAsDict: function() {
        var data = {};

        this.defaultAddresses().forEach(function(a) {
            data[a.id] = a;
        });

        return data;
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
            neighbours: 'Address_C Address_D'
        }, {
            id: 'Address_B',
            selected: true,
            title: 'Address B',
            content: 'Place inconnue, 13005 Marseille',
            status: creme.geolocation.LocationStatus.PARTIAL,
            latitude: 43,
            longitude: 5.5,
            url: 'mock/address/Address_B',
            neighbours: 'Address_C'
        }, {
            id: 'Address_C',
            selected: true,
            title: 'Address C',
            content: '13013 Marseille',
            status: creme.geolocation.LocationStatus.MANUAL,
            latitude: 42,
            longitude: 5,
            url: 'mock/address/Address_C',
            neighbours: 'Address_A Address_B Address_D'
        }, {
            id: 'Address_D',
            selected: false,
            title: 'Address D',
            content: 'marseille',
            status: creme.geolocation.LocationStatus.UNDEFINED,
            url: 'mock/address/Address_D',
            neighbours: 'Address_A Address_C'
        }];
    },

    renderOptionHtml: function(item) {
        return '<option value="${value}">${label}</option>'.template(item);
    },

    renderAddressFilterGroupHtml: function(group) {
        group = group || {};

        return (
           '<optgroup label="${group}">${choices}</optgroup>'
        ).template({
            group: group.name,
            choices: (group.items || []).map(this.renderOptionHtml.bind(this)).join('')
        });
    },

    createNeighboursBrickHtml: function(options) {
        options = $.extend({
            filters: [],
            origins: []
        }, options || {});

        var filters = [{
            value: '', label: 'All the contacts and organisations'
        }].concat(options.filters);

        var origins = Object.isEmpty(options.origins) ? [{
            value: '', label: 'No geolocated address for now'
        }] : options.origins;

        var content = (
            '<div class="geolocation-brick-header">' +
                '<span class="brick-geoaddress-counter">None of</span>' +
                '<select class="brick-geoaddress-filter">${filters}</select>' +
                ' around <select class="brick-geoaddress-origin">${origins}</select>' +
                ' within a radius of ${radius}.' +
            '</div>' +
            '<div class="brick-geoaddress-error">${config}</div>' +
            '<div class="brick-geoaddress-canvas" style="width: 100px; height: 100px;"></div>'
        ).template({
            filters: filters.map(this.renderAddressFilterGroupHtml.bind(this)).join(''),
            origins: origins.map(this.renderOptionHtml.bind(this)).join(''),
            radius: options.radius || 0,
            config: this.createBrickActionHtml({
                action: 'redirect',
                url: 'mock/apikey/config'
            })
        });

        return this.createBrickHtml($.extend({
            content: content,
            classes: ['geolocation-brick']
        }, options));
    },

    createNeighboursBrick: function(options) {
        var html = this.createNeighboursBrickHtml(options);

        var element = $(html).appendTo(this.qunitFixture());
        var widget = creme.widget.create(element);
        var brick = widget.brick();

        this.assert.equal(true, brick.isBound());
        this.assert.equal(false, brick.isLoading());

        return widget;
    },

    fakeBrickLocationSave: function(controller, address) {
        controller._onMoveLocation($.Event(), {}, address);
    }
}));

QUnit.parametrize('creme.geolocation.brick.NeighborhoodBrick (defaults)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var self = this;
    var brick = this.createNeighboursBrick({}).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');
    var filter = brick.element().find('.brick-geoaddress-filter');
    var origin = brick.element().find('.brick-geoaddress-origin');
    var counter = brick.element().find('.brick-geoaddress-counter');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = self.controller;

        assert.deepEqual(canvas.get(), controller.canvas().get());
        assert.deepEqual(filter.get(), controller.filterSelector().get());
        assert.deepEqual(origin.get(), controller.originSelector().get());

        assert.deepEqual(counter.get(), controller.counterItem().get());

        assert.equal(undefined, controller.neighboursUrl());
        assert.equal(null, controller.origin());
        assert.deepEqual([], controller.neighbours());

        assert.deepEqual(canvas.get(), controller.mapController().element().get());

        assert.equal(true, controller.mapController().isBound());
        assert.equal(true, controller.mapController().isEnabled());
        assert.equal(true, controller.mapController().isMapEnabled());
        assert.equal(true, controller.mapController().isGeocoderEnabled());

        // google maps specific
        if (mapController instanceof creme.geolocation.GoogleMapController) {
            assert.equal(true, controller.mapController().isAPIReady());
            assert.equal(undefined, controller.mapController().options().apiKey);
        }

        var done = assert.async();

        setTimeout(function() {
            assert.equal(null, brick.element().find('.brick-geoaddress-filter').val());
            assert.equal(gettext('None of'), brick.element().find('.brick-geoaddress-counter').text());
            assert.equal(0, controller.mapController().markers().length);
            assert.equal(0, controller.mapController().shapes().length);

            done();
        }, 0);
    });

    this.controller = new creme.geolocation.PersonsNeighborhoodBrick(brick, {
        mapController: mapController
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.NeighborhoodBrick (no origin, no filter)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var brick = this.createNeighboursBrick({}).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = this.controller;

        assert.equal('mock/neighbours', controller.neighboursUrl());

        var done = assert.async();

        setTimeout(function() {
            assert.deepEqual([], this.mockBackendUrlCalls());

            assert.equal(null, controller.filterSelector().val());
            assert.equal('', controller.originSelector().val());

            assert.equal(null, controller.origin());
            assert.deepEqual([], controller.neighbours());

            assert.equal(gettext('None of'), brick.element().find('.brick-geoaddress-counter').text());
            assert.equal(0, controller.mapController().markers().length);
            assert.equal(0, controller.mapController().shapes().length);

            done();
        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.PersonsNeighborhoodBrick(brick, {
        mapController: mapController,
        neighboursUrl: 'mock/neighbours'
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.NeighborhoodBrick (no filter)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var brick = this.createNeighboursBrick({
        origins: [
            {value: 'Address_A', label: 'Address A'},
            {value: 'Address_B', label: 'Address B'}
        ]
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');
    var addresses = this.defaultAddressesAsDict();

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = this.controller;

        assert.equal('mock/neighbours', controller.neighboursUrl());
        var done = assert.async();

        setTimeout(function() {
            assert.deepEqual([
                ['mock/neighbours', 'GET', {
                    address_id: 'Address_A',
                    filter_id: null
                }]
            ], this.mockBackendUrlCalls());

            assert.equal(null, controller.filterSelector().val());
            assert.equal('Address_A', controller.originSelector().val());

            assert.deepEqual(new creme.geolocation.Location(addresses['Address_A']), controller.origin());
            assert.deepEqual([
                new creme.geolocation.Location(addresses['Address_C']),
                new creme.geolocation.Location(addresses['Address_D'])
            ], controller.neighbours());

            assert.equal(ngettext('%0$d of', '%0$d of', 2).format(2),
                  brick.element().find('.brick-geoaddress-counter').text());
            assert.equal(3, controller.mapController().markers().length);
            assert.equal(1, controller.mapController().shapes().length);

            done();
        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.PersonsNeighborhoodBrick(brick, {
        mapController: mapController,
        neighboursUrl: 'mock/neighbours'
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.NeighborhoodBrick (filter)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var brick = this.createNeighboursBrick({
        origins: [
            {value: 'Address_A', label: 'Address A'},
            {value: 'Address_B', label: 'Address B'}
        ],
        filters: {
            name: 'Group A',
            items: [
                {value: 'A1', label: 'Filter A1'},
                {value: 'empty', label: 'Empty'}
            ]
        }
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');
    var addresses = this.defaultAddressesAsDict();

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = this.controller;
        var done = assert.async();

        assert.equal('mock/neighbours', controller.neighboursUrl());

        setTimeout(function() {
            assert.deepEqual([
                ['mock/neighbours', 'GET', {
                    address_id: 'Address_A',
                    filter_id: 'A1'
                }]
            ], this.mockBackendUrlCalls());

            assert.equal('A1', controller.filterSelector().val());
            assert.equal('Address_A', controller.originSelector().val());

            assert.deepEqual(new creme.geolocation.Location(addresses['Address_A']), controller.origin());
            assert.deepEqual([
                new creme.geolocation.Location(addresses['Address_C']),
                new creme.geolocation.Location(addresses['Address_D'])
            ], controller.neighbours());

            assert.equal(ngettext('%0$d of', '%0$d of', 2).format(2),
                  brick.element().find('.brick-geoaddress-counter').text());
            assert.equal(3, controller.mapController().markers().length);
            assert.equal(1, controller.mapController().shapes().length);

            brick.element().find('.brick-geoaddress-filter').val('empty').trigger('change');

            setTimeout(function() {
                assert.deepEqual([
                    ['mock/neighbours', 'GET', {
                        address_id: 'Address_A',
                        filter_id: 'A1'
                    }],
                    ['mock/neighbours', 'GET', {
                        address_id: 'Address_A',
                        filter_id: 'empty'
                    }]
                ], this.mockBackendUrlCalls());

                assert.deepEqual(new creme.geolocation.Location(addresses['Address_A']), controller.origin());
                assert.deepEqual([], controller.neighbours());

                assert.equal(gettext('None of'), brick.element().find('.brick-geoaddress-counter').text());
                assert.equal(1, controller.mapController().markers().length);
                assert.equal(1, controller.mapController().shapes().length);

                done();
            }.bind(this), 0);
        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.PersonsNeighborhoodBrick(brick, {
        mapController: mapController,
        neighboursUrl: 'mock/neighbours'
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.NeighborhoodBrick (origin change)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var brick = this.createNeighboursBrick({
        origins: [
            {value: 'Address_A', label: 'Address A'},
            {value: 'Address_B', label: 'Address B'}
        ],
        filters: {
            name: 'Group A',
            items: [
                {value: 'A1', label: 'Filter A1'},
                {value: 'empty', label: 'Empty'}
            ]
        }
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');
    var addresses = this.defaultAddressesAsDict();

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = this.controller;
        var done = assert.async();

        assert.equal('mock/neighbours', controller.neighboursUrl());

        setTimeout(function() {
            assert.deepEqual([
                ['mock/neighbours', 'GET', {
                    address_id: 'Address_A',
                    filter_id: 'A1'
                }]
            ], this.mockBackendUrlCalls());

            this.assertCircleShape(controller.mapController().shapes()[0], {
                visible: true,
                radius: 1,
                position: {lat: 43.291628, lng: 5.403022},
                id: 'NeighbourhoodCircle'
            });

            brick.element().find('.brick-geoaddress-origin').val('Address_B').trigger('change');

            setTimeout(function() {
                assert.deepEqual([
                    ['mock/neighbours', 'GET', {
                        address_id: 'Address_A',
                        filter_id: 'A1'
                    }],
                    ['mock/neighbours', 'GET', {
                        address_id: 'Address_B',
                        filter_id: 'A1'
                    }]
                ], this.mockBackendUrlCalls());

                assert.equal('A1', controller.filterSelector().val());
                assert.equal('Address_B', controller.originSelector().val());

                assert.deepEqual(new creme.geolocation.Location(addresses['Address_B']), controller.origin());
                assert.deepEqual([
                    new creme.geolocation.Location(addresses['Address_C'])
                ], controller.neighbours());

                assert.equal(ngettext('%0$d of', '%0$d of', 1).format(1),
                      brick.element().find('.brick-geoaddress-counter').text());
                assert.equal(2, controller.mapController().markers().length);
                assert.equal(1, controller.mapController().shapes().length);

                this.assertCircleShape(controller.mapController().shapes()[0], {
                    visible: true,
                    radius: 1,
                    position: {lat: 43.0, lng: 5.5},
                    id: 'NeighbourhoodCircle'
                });
                done();
            }.bind(this), 0);
        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.PersonsNeighborhoodBrick(brick, {
        mapController: mapController,
        neighboursUrl: 'mock/neighbours'
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.NeighborhoodBrick (origin move)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var brick = this.createNeighboursBrick({
        origins: [
            {value: 'Address_A', label: 'Address A'}
        ],
        filters: {
            name: 'Group A',
            items: [
                {value: 'A1', label: 'Filter A1'},
                {value: 'empty', label: 'Empty'}
            ]
        }
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');
    var addresses = this.mockNeighbourAddresses();

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = this.controller;
        var done = assert.async();

        assert.equal('mock/neighbours', controller.neighboursUrl());

        setTimeout(function() {
            assert.deepEqual([
                ['mock/neighbours', 'GET', {
                    address_id: 'Address_A',
                    filter_id: 'A1'
                }]
            ], this.mockBackendUrlCalls());

            assert.equal('A1', controller.filterSelector().val());
            assert.equal('Address_A', controller.originSelector().val());

            assert.deepEqual(new creme.geolocation.Location(addresses['Address_A']), controller.origin());
            assert.deepEqual([
                new creme.geolocation.Location(addresses['Address_C']),
                new creme.geolocation.Location(addresses['Address_D'])
            ], controller.neighbours());

            assert.equal(ngettext('%0$d of', '%0$d of', 2).format(2),
                  brick.element().find('.brick-geoaddress-counter').text());
            assert.equal(3, controller.mapController().markers().length);
            assert.equal(1, controller.mapController().shapes().length);

            assert.equal(true, brick.element().is('.geolocation-brick'));

            // Update the origin Address_A & trigger the save event
            $.extend(addresses['Address_A'], {
                latitude: 47.887799,
                longitude: 6.077844,
                status: creme.geolocation.LocationStatus.COMPLETE
            });
            var newAddress_A = new creme.geolocation.Location(addresses['Address_A']);

            this.fakeBrickLocationSave(controller, newAddress_A);

            setTimeout(function() {
                assert.deepEqual([
                    ['mock/neighbours', 'GET', {
                        address_id: 'Address_A',
                        filter_id: 'A1'
                    }],
                    // Address A has moved and implies a NEW neighbour request
                    ['mock/neighbours', 'GET', {
                        address_id: 'Address_A',
                        filter_id: 'A1'
                    }]
                ], this.mockBackendUrlCalls());

                assert.equal('A1', controller.filterSelector().val());
                assert.equal('Address_A', controller.originSelector().val());

                assert.deepEqual(newAddress_A, controller.origin());
                assert.deepEqual([
                    new creme.geolocation.Location(addresses['Address_C']),
                    new creme.geolocation.Location(addresses['Address_D'])
                ], controller.neighbours());

                assert.equal(ngettext('%0$d of', '%0$d of', 2).format(2),
                      brick.element().find('.brick-geoaddress-counter').text());
                assert.equal(3, controller.mapController().markers().length);
                assert.equal(1, controller.mapController().shapes().length);

                done();
            }.bind(this), 0);
        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.PersonsNeighborhoodBrick(brick, {
        mapController: mapController,
        neighboursUrl: 'mock/neighbours'
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.NeighborhoodBrick (neighbour move)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var brick = this.createNeighboursBrick({
        origins: [
            {value: 'Address_A', label: 'Address A'}
        ],
        filters: {
            name: 'Group A',
            items: [
                {value: 'A1', label: 'Filter A1'},
                {value: 'empty', label: 'Empty'}
            ]
        }
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');
    var addresses = this.mockNeighbourAddresses();

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = this.controller;
        var done = assert.async();

        assert.equal('mock/neighbours', controller.neighboursUrl());

        setTimeout(function() {
            assert.equal('A1', controller.filterSelector().val());
            assert.equal('Address_A', controller.originSelector().val());

            assert.deepEqual(new creme.geolocation.Location(addresses['Address_A']), controller.origin());
            assert.deepEqual([
                new creme.geolocation.Location(addresses['Address_C']),
                new creme.geolocation.Location(addresses['Address_D'])
            ], controller.neighbours());

            assert.equal(ngettext('%0$d of', '%0$d of', 2).format(2),
                  brick.element().find('.brick-geoaddress-counter').text());
            assert.equal(3, controller.mapController().markers().length);
            assert.equal(1, controller.mapController().shapes().length);

            assert.equal(true, brick.element().is('.geolocation-brick'));

            assert.deepEqual([
                ['mock/neighbours', 'GET', {
                    address_id: 'Address_A',
                    filter_id: 'A1'
                }]
            ], this.mockBackendUrlCalls());

            // Update Address_C in mock neighbours list & trigger the save event
            $.extend(addresses['Address_C'], {
                latitude: 47.887799,
                longitude: 6.077844,
                status: creme.geolocation.LocationStatus.COMPLETE
            });
            var newAddress_C = new creme.geolocation.Location(addresses['Address_C']);

            this.fakeBrickLocationSave(controller, newAddress_C);

            setTimeout(function() {
                assert.deepEqual([
                    ['mock/neighbours', 'GET', {
                        address_id: 'Address_A',
                        filter_id: 'A1'
                    }],
                    // Address C has moved and implies a NEW neighbour request
                    ['mock/neighbours', 'GET', {
                        address_id: 'Address_A',
                        filter_id: 'A1'
                    }]
                ], this.mockBackendUrlCalls());

                assert.equal('A1', controller.filterSelector().val());
                assert.equal('Address_A', controller.originSelector().val());

                assert.deepEqual(new creme.geolocation.Location(addresses['Address_A']), controller.origin());
                assert.deepEqual([
                    newAddress_C,
                    new creme.geolocation.Location(addresses['Address_D'])
                ], controller.neighbours());

                assert.equal(ngettext('%0$d of', '%0$d of', 2).format(2),
                      brick.element().find('.brick-geoaddress-counter').text());
                assert.equal(3, controller.mapController().markers().length);
                assert.equal(1, controller.mapController().shapes().length);

                done();
            }.bind(this), 0);
        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.PersonsNeighborhoodBrick(brick, {
        mapController: mapController,
        neighboursUrl: 'mock/neighbours'
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.NeighborhoodBrick (click neighbour, redirect)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var brick = this.createNeighboursBrick({
        origins: [
            {value: 'Address_A', label: 'Address A'}
        ],
        filters: {
            name: 'Group A',
            items: [
                {value: 'A1', label: 'Filter A1'},
                {value: 'empty', label: 'Empty'}
            ]
        }
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');
    var addresses = this.defaultAddressesAsDict();

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = this.controller;
        var done = assert.async();

        controller.mapController().on('marker-click', this.mockListener('marker-click'));

        assert.equal('mock/neighbours', controller.neighboursUrl());

        setTimeout(function() {
            assert.deepEqual([
                ['mock/neighbours', 'GET', {
                    address_id: 'Address_A',
                    filter_id: 'A1'
                }]
            ], this.mockBackendUrlCalls());
            assert.deepEqual([], this.mockRedirectCalls());
            assert.deepEqual([], this.mockListenerCalls('marker-click'));

            assert.equal('A1', controller.filterSelector().val());
            assert.equal('Address_A', controller.originSelector().val());

            assert.deepEqual(new creme.geolocation.Location(addresses['Address_A']), controller.origin());
            assert.deepEqual([
                new creme.geolocation.Location(addresses['Address_C']),
                new creme.geolocation.Location(addresses['Address_D'])
            ], controller.neighbours());

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

    this.controller = new creme.geolocation.PersonsNeighborhoodBrick(brick, {
        mapController: mapController,
        neighboursUrl: 'mock/neighbours'
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.NeighborhoodBrick (google, click origin)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var brick = this.createNeighboursBrick({
        origins: [
            {value: 'Address_A', label: 'Address A'}
        ],
        filters: {
            name: 'Group A',
            items: [
                {value: 'A1', label: 'Filter A1'},
                {value: 'empty', label: 'Empty'}
            ]
        }
    }).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');
    var addresses = this.defaultAddressesAsDict();

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var controller = this.controller;
        var done = assert.async();

        controller.mapController().on('marker-click', this.mockListener('marker-click'));

        assert.equal('mock/neighbours', controller.neighboursUrl());

        setTimeout(function() {
            assert.deepEqual([
                ['mock/neighbours', 'GET', {
                    address_id: 'Address_A',
                    filter_id: 'A1'
                }]
            ], this.mockBackendUrlCalls());
            assert.deepEqual([], this.mockRedirectCalls());
            assert.deepEqual([], this.mockListenerCalls('marker-click'));

            assert.equal('A1', controller.filterSelector().val());
            assert.equal('Address_A', controller.originSelector().val());

            assert.deepEqual(new creme.geolocation.Location(addresses['Address_A']), controller.origin());
            assert.deepEqual([
                new creme.geolocation.Location(addresses['Address_C']),
                new creme.geolocation.Location(addresses['Address_D'])
            ], controller.neighbours());

            this.triggerMarkerClick(controller.mapController().getMarker('Address_A'));

            setTimeout(function() {
                assert.deepEqual([], this.mockRedirectCalls());
                assert.deepEqual([
                    ['marker-click', {
                        id: 'Address_A',
                        extraData: {}
                    }]
                ], this.mockListenerCalls('marker-click').map(function(e) {
                    return [e[0], e[1]];
                }));

                done();
            }.bind(this), 0);
        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.PersonsNeighborhoodBrick(brick, {
        mapController: mapController,
        neighboursUrl: 'mock/neighbours'
    });

    stop(1);
});

QUnit.parametrize('creme.geolocation.brick.NeighborhoodBrick (google, collapse state)', [
    [new creme.geolocation.GoogleMapController()],
    [new creme.geolocation.LeafletMapController()]
], function(mapController, assert) {
    var brick = this.createNeighboursBrick({}).brick();
    var canvas = brick.element().find('.brick-geoaddress-canvas');

    this.bindTestOn(canvas, 'geomap-status-enabled', function() {
        var done = assert.async();

        setTimeout(function() {
            this.autoResizeFaker.reset();
            this.adjustMapToShapeFaker.reset();

            assert.equal(0, this.autoResizeFaker.count());
            assert.equal(0, this.adjustMapToShapeFaker.count());

            brick.setState({
                collapsed: true
            });

            assert.equal(0, this.autoResizeFaker.count());
            assert.equal(0, this.adjustMapToShapeFaker.count());

            brick.setState({
                collapsed: false
            });

            assert.equal(1, this.autoResizeFaker.count());
            assert.equal(1, this.adjustMapToShapeFaker.count());

            done();
        }.bind(this), 0);
    });

    this.controller = new creme.geolocation.PersonsNeighborhoodBrick(brick, {
        mapController: mapController,
        neighboursUrl: 'mock/neighbours'
    });

    this.autoResizeFaker = this.fakeMethod({
        instance: this.controller.mapController(),
        method: 'autoResize',
        follow: true
    });

    this.adjustMapToShapeFaker = this.fakeMethod({
        instance: this.controller.mapController(),
        method: 'adjustMapToShape',
        follow: true
    });

    stop(1);
});

}(jQuery, QUnit));
