(function($) {
"use strict";

QUnit.module("creme.MenuContainersController", new QUnitMixin(QUnitEventMixin,
                                                              QUnitAjaxMixin,
                                                              QUnitBrickMixin,
                                                              QUnitDialogMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true, delay: 0});
    },

    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendPOST({
            'mock/menu/reorder/level0/default/1': backend.response(200, ''),
            'mock/menu/reorder/level0/default/fail': backend.response(400, 'Invalid request')
        });
    },

    createMenuRootHtml: function(options) {
        options = $.extend({
            url: ''
        }, options || {});

        return (
            '<div class="menu-config-entry0" data-reorderable-menu-container-url="${url}">' +
                '<div class="menu-config-entry0-header">' +
                    '<span class="menu-config-entry0-header-title">Menu</span>' +
                '</div>' +
                '<div class="menu-config-entry0-content"></div>' +
            '</div>'
        ).template(options);
    },

    createMenuItemHtml: function(options) {
        options = $.extend({
            id: 'default',
            roots: []
        }, options || {});

        var html = (
            '<div class="menu-config-item">' +
                '<div class="menu-config-container">${roots}</div>' +
                '<div class="menu-config-actions"></div>' +
            '</div>'
        ).template({
            id: options.id,
            roots: (options.roots || []).map(this.createMenuRootHtml.bind(this)).join('')
        });

        return html;
    },

    createMenuEditorBrickHtml: function(options) {
        options = $.extend({
            items: []
        }, options || {});

        var content = options.items.map(this.createMenuItemHtml.bind(this)).join('');

        return this.createBrickHtml($.extend({
            content: content
        }, options));
    },

    createMenuEditorBrick: function(options) {
        var html = this.createMenuEditorBrickHtml(options);

        var element = $(html).appendTo(this.qunitFixture());
        var widget = creme.widget.create(element);
        var brick = widget.brick();

        this.assert.equal(true, brick.isBound());
        this.assert.equal(false, brick.isLoading());

        return widget;
    },

    getMenuRoot: function(brick, url) {
        return brick.element().find(
            '.menu-config-entry0[data-reorderable-menu-container-url="${url}"]'.template({url: url})
        ).get(0);
    }
}));

QUnit.test('creme.MenuContainersController (drag n drop, success, 2 roots nodes)', function(assert) {
    var brick = this.createMenuEditorBrick({
        id: 'creme_config-test',
        items: [{
            id: 'default',
            roots: [{
                url: 'mock/menu/reorder/level0/default/1'
            }, {
                url: 'mock/menu/reorder/level0/default/fail'
            }]
        }]
    }).brick();

    var controller = new creme.MenuContainersController(brick); /* eslint-disable-line */

    controller._onSort({
        item: this.getMenuRoot(brick, 'mock/menu/reorder/level0/default/1'),
        newIndex: 2
    });

    assert.deepEqual([
        ['mock/menu/reorder/level0/default/1', 'POST', {target: 3}],
        ['mock/brick/all/reload', 'GET', {brick_id: ['creme_config-test'], extra_data: "{}"}]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.MenuContainersController (drag n drop, success, 1 root node)', function(assert) {
    var brick = this.createMenuEditorBrick({
        id: 'creme_config-test',
        items: [{
            id: 'default',
            roots: [{url: 'mock/menu/reorder/level0/default/1'}]
        }]
    }).brick();

    var controller = new creme.MenuContainersController(brick); /* eslint-disable-line */

    controller._onSort({
        item: brick.element().find('.menu-config-entry0').get(0),
        newIndex: 2
    });

    assert.deepEqual([
        ['mock/menu/reorder/level0/default/1', 'POST', {target: 3}],
        ['mock/brick/all/reload', 'GET', {brick_id: ['creme_config-test'], extra_data: "{}"}]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.MenuContainersController (drag n drop, failure)', function(assert) {
    var brick = this.createMenuEditorBrick({
        id: 'creme_config-test',
        items: [{
            id: 'default',
            roots: [{url: 'mock/menu/reorder/level0/default/fail'}]
        }]
    }).brick();

    var controller = new creme.MenuContainersController(brick); /* eslint-disable-line */

    controller._onSort({
        item: brick.element().find('.menu-config-entry0').get(0),
        newIndex: 2
    });

    assert.deepEqual([
        ['mock/menu/reorder/level0/default/fail', 'POST', {target: 3}]
    ], this.mockBackendUrlCalls());

    this.assertOpenedAlertDialog("Invalid request");
    this.closeDialog();

    assert.deepEqual([
        ['mock/menu/reorder/level0/default/fail', 'POST', {target: 3}],
        ['mock/brick/all/reload', 'GET', {brick_id: ['creme_config-test'], extra_data: "{}"}]
    ], this.mockBackendUrlCalls());
});

}(jQuery));
