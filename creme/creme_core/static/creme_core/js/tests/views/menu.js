/* global QUnitWidgetMixin */

(function($) {
var ANYFORM_GROUPED_LINKS = [
    [{
        "label": "Group A",
        "links": [{
            "label": "A1",
            "url": "mock/any/A1"
        }, {
            "label": "A2",
            "url": "mock/any/A2"
        }, {
            "label": "A3 (disabled)"
        }]
    }, {
        "label": "Group B",
        "links": [{
            "label": "B1",
            "url": "mock/any/B1"
        }]
    }],
    [{
        "label": "Group C",
        "links": [{
            "label": "C1",
            "url": "mock/any/C1"
        }, {
            "label": "C2",
            "url": "mock/any/C2"
        }, {
            "label": "C3",
            "url": "mock/any/C3"
        }]
    }]
];

QUnit.module("creme.menu.js", new QUnitMixin(QUnitEventMixin,
                                             QUnitAjaxMixin,
                                             QUnitDialogMixin,
                                             QUnitWidgetMixin, {
    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendGET({
            'mock/A/quickform': backend.response(200, '<form action="mock/A/quickform/"></form>'),
            'mock/B/quickform': backend.response(200, '<form action="mock/B/quickform/"></form>')
        });

        this.setMockBackendPOST({
            'mock/A/quickform': backend.response(200, ''),
            'mock/B/quickform': backend.response(200, '')
        });
    },

    createMenuHtml: function(options) {
        options = $.extend({
            items: []
        }, options || {});

        var renderItem = function(item) {
            item = $.extend({
                level: 0,
                items: [],
                id: 'id',
                content: '<span></span>'
            }, item || {});

            var renderSubItem = function(item) {
                return renderItem($.extend({}, item, {level: (item.level || 0) + 1}));
            };

            return (
               '<li class="ui-creme-navigation-item-level${level} ui-creme-navigation-item-${id}">' +
                  '${content}' +
                  '${items}' +
               '</li>'
            ).template({
                content: item.content || '<span></span>',
                level: item.level,
                id: item.id,
                items: item.items ? '<ul>' + item.items.map(renderSubItem).join('') + '</ul>' : ''
            });
        };

        return (
            '<div class="header-menu">' +
                 '<ul class="ui-creme-navigation">${items}</ul>' +
            '</div>'
        ).template({
            items: options.items.map(renderItem).join('')
        });
    },

    createRegularMenuHtml: function() {
        return this.createMenuHtml({
            items: [{
                label: 'menu A',
                id: 'A',
                items: [
                    {id: 'A1', content: '<a href="mock/menu/A/A1">item A1</a>'},
                    {id: 'A2', content: '<a href="mock/menu/A/A2">item A2</a>'},
                    {id: 'A3', content: '<span>item A3 (disabled)</span>'}
                ]
            }, {
                label: 'menu B',
                id: 'B',
                items: [
                    {id: 'B1', content: '<a href="mock/menu/B/B1">item B1</a>'},
                    {id: 'B2', content: '<a href="mock/menu/B/B2">item B2</a>'}
                ]
            }]
        });
    },

    createQuickFormMenuHtml: function() {
        return this.createMenuHtml({
            items: [{
                label: 'menu A',
                id: 'A',
                items: [
                    {id: 'quickA', content: '<a class="quickform-menu-link" data-href="mock/A/quickform">quickform A</a>'},
                    {id: 'quickB', content: '<a class="quickform-menu-link" data-href="mock/B/quickform">quickform B</a>'}
                ]
            }]
        });
    },

    createAnyFormMenuHtml: function() {
        return this.createMenuHtml({
            items: [{
                label: 'menu A',
                id: 'A',
                items: [{
                    id: 'anyA',
                    content: '<a class="anyform-menu-link" data-grouped-links="[]">anyform A</a>'
                }, {
                    id: 'anyB',
                    content: (
                        '<a class="anyform-menu-link" data-grouped-links="' +
                            JSON.stringify(ANYFORM_GROUPED_LINKS).replace(/"/gi, '&quot;') +
                        '">anyform B</a>'
                    )
                }]
            }]
        });
    }
}));

QUnit.test('creme.menu.MenuController (bind)', function(assert) {
    var element = $(this.createRegularMenuHtml());
    var controller = new creme.menu.MenuController();

    assert.equal(false, controller.isBound());

    controller.bind(element);

    assert.equal(true, controller.isBound());
    this.assertRaises(function() {
        controller.bind(element);
    }, Error, 'Error: MenuController is already bound');
});

QUnit.test('creme.menu.MenuController (main menu, hover)', function(assert) {
    var element = $(this.createRegularMenuHtml());
    var controller = new creme.menu.MenuController().bind(element);

    assert.equal(true, controller.isBound());

    var menuA = element.find('li.ui-creme-navigation-item-A');
    var menuB = element.find('li.ui-creme-navigation-item-B');

    assert.equal(false, menuA.is('.ui-creme-navigation-activated'));
    assert.equal(false, menuB.is('.ui-creme-navigation-activated'));

    menuA.trigger('mouseenter');

    assert.equal(true, menuA.is('.ui-creme-navigation-activated'));
    assert.equal(false, menuB.is('.ui-creme-navigation-activated'));

    menuA.trigger('mouseleave');
    menuB.trigger('mouseenter');

    assert.equal(false, menuA.is('.ui-creme-navigation-activated'));
    assert.equal(true, menuB.is('.ui-creme-navigation-activated'));
});

QUnit.test('creme.menu.MenuController (main menu, click)', function(assert) {
    var element = $(this.createRegularMenuHtml());
    var controller = new creme.menu.MenuController().bind(element);

    assert.equal(true, controller.isBound());

    var menuA = element.find('.ui-creme-navigation-item-A');
    var menuB = element.find('.ui-creme-navigation-item-B');

    assert.equal(false, menuA.is('li.ui-creme-navigation-activated'));
    assert.equal(false, menuB.is('li.ui-creme-navigation-activated'));

    menuA.trigger('click');

    assert.equal(true, menuA.is('.ui-creme-navigation-activated'));
    assert.equal(false, menuB.is('.ui-creme-navigation-activated'));

    menuB.trigger('click');

    assert.equal(false, menuA.is('.ui-creme-navigation-activated'));
    assert.equal(true, menuB.is('.ui-creme-navigation-activated'));
});

QUnit.test('creme.menu.MenuController (submenu quickform)', function(assert) {
    var element = $(this.createQuickFormMenuHtml());
    var controller = new creme.menu.MenuController().bind(element);
    var quickA = element.find('.ui-creme-navigation-item-quickA a');

    assert.equal(true, controller.isBound());

    this.assertClosedDialog();
    assert.deepEqual([], this.mockBackendUrlCalls('mock/A/quickform'));

    quickA.trigger('click');

    this.assertOpenedDialog();
    assert.deepEqual([['GET', {}]], this.mockBackendUrlCalls('mock/A/quickform'));
});

QUnit.test('creme.menu.MenuController (quickform, close opened submenu)', function(assert) {
    var element = $(this.createQuickFormMenuHtml());
    var controller = new creme.menu.MenuController().bind(element);

    var menuA = element.find('.ui-creme-navigation-item-A');
    var quickA = element.find('.ui-creme-navigation-item-quickA a');

    assert.equal(true, controller.isBound());
    assert.equal(false, menuA.is('li.ui-creme-navigation-activated'));

    menuA.trigger('mouseenter');

    assert.equal(true, menuA.is('li.ui-creme-navigation-activated'));

    this.assertClosedDialog();

    quickA.trigger('click');

    this.assertOpenedDialog();
    assert.equal(false, menuA.is('li.ui-creme-navigation-activated'));
});

QUnit.test('creme.menu.MenuController (quickform, close opened dialog)', function(assert) {
    var element = $(this.createQuickFormMenuHtml());
    var controller = new creme.menu.MenuController().bind(element);

    var quickA = element.find('.ui-creme-navigation-item-quickA a');
    var quickB = element.find('.ui-creme-navigation-item-quickB a');

    assert.equal(true, controller.isBound());

    quickA.trigger('click');

    var dialog = this.assertOpenedDialog();
    assert.equal('mock/A/quickform/', dialog.find('form').attr('action'));

    assert.deepEqual([['mock/A/quickform', 'GET', {}]], this.mockBackendUrlCalls());

    quickB.trigger('click');

    dialog = this.assertOpenedDialog();
    assert.equal('mock/B/quickform/', dialog.find('form').attr('action'));

    assert.deepEqual([
        ['mock/A/quickform', 'GET', {}],
        ['mock/B/quickform', 'GET', {}]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.menu.MenuController (submenu anyform, empty)', function(assert) {
    var element = $(this.createAnyFormMenuHtml());
    var controller = new creme.menu.MenuController().bind(element);

    var anyA = element.find('.ui-creme-navigation-item-anyA a');

    assert.equal(true, controller.isBound());

    anyA.trigger('click');

    var dialog = this.assertOpenedDialog();
    this.equalHtml('<div class="create-all-form">', dialog.find('.ui-creme-dialog-frame'));
});

QUnit.test('creme.menu.MenuController (submenu anyform)', function(assert) {
    var element = $(this.createAnyFormMenuHtml());
    var controller = new creme.menu.MenuController().bind(element);

    var anyB = element.find('.ui-creme-navigation-item-anyB a');

    assert.equal(true, controller.isBound());

    anyB.trigger('click');

    var dialog = this.assertOpenedDialog();
    assert.deepEqual([], this.mockBackendUrlCalls());   // rendered in js

    this.equalHtml(
         '<div class="create-all-form">' +
            '<div class="create-group-container create-group-container-2-columned">' +
                '<div class="create-group">' +
                    '<div class="create-group-title">Group A</div>' +
                    '<a href="mock/any/A1" class="create-group-entry">A1</a>' +
                    '<a href="mock/any/A2" class="create-group-entry">A2</a>' +
                    '<span class="create-group-entry forbidden">A3 (disabled)</span>' +
                '</div>' +
                '<div class="create-group">' +
                    '<div class="create-group-title">Group B</div>' +
                    '<a href="mock/any/B1" class="create-group-entry">B1</a>' +
                '</div>' +
            '</div>' +
            '<div class="create-group-container create-group-container-1-columned">' +
                '<div class="create-group">' +
                    '<div class="create-group-title">Group C</div>' +
                    '<a href="mock/any/C1" class="create-group-entry">C1</a>' +
                    '<a href="mock/any/C2" class="create-group-entry">C2</a>' +
                    '<a href="mock/any/C3" class="create-group-entry">C3</a>' +
                '</div>' +
            '</div>' +
        '</div>', dialog.find('.ui-creme-dialog-frame'));
});

QUnit.test('creme.menu.MenuController (submenu anyform, close opened submenu)', function(assert) {
    var element = $(this.createAnyFormMenuHtml());
    var controller = new creme.menu.MenuController().bind(element);

    var menuA = element.find('.ui-creme-navigation-item-A');
    var anyA = element.find('.ui-creme-navigation-item-anyA a');

    assert.equal(true, controller.isBound());
    assert.equal(false, menuA.is('li.ui-creme-navigation-activated'));

    menuA.trigger('mouseenter');

    assert.equal(true, menuA.is('li.ui-creme-navigation-activated'));

    anyA.trigger('click');

    this.assertOpenedDialog();
    assert.equal(false, menuA.is('li.ui-creme-navigation-activated'));
});

QUnit.test('creme.menu.MenuController (submenu anyform, close opened dialog)', function(assert) {
    var element = $(this.createAnyFormMenuHtml());
    var controller = new creme.menu.MenuController().bind(element);

    var anyA = element.find('.ui-creme-navigation-item-anyA a');
    var anyB = element.find('.ui-creme-navigation-item-anyB a');

    assert.equal(true, controller.isBound());

    anyA.trigger('click');

    this.assertOpenedDialog();

    anyB.trigger('click');

    this.assertOpenedDialog();
});

}(jQuery));
