(function($) {
"use strict";

QUnit.module("creme.MenuEditor", new QUnitMixin(QUnitEventMixin,
                                                QUnitAjaxMixin,
                                                QUnitDialogMixin,
                                                QUnitMouseMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true});
    },

    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendGET({
            'mock/menu/custom': backend.response(200, (
                '<form action="mock/menu/custom">' +
                    '<input name="value" />' +
                    '<input name="label" />' +
                '</form>'
            ))
        });

        this.setMockBackendPOST({
            'mock/group/reorder/0': backend.response(200, ''),
            'mock/group/reorder/0/fail': backend.response(400, 'Invalid request'),
            'mock/group/reorder/1': backend.response(200, ''),
            'mock/group/reorder/2': backend.response(200, ''),
            'mock/group/expand': backend.response(200, ''),
            'mock/menu/custom': function(url, data, options) {
                return backend.responseJSON(200, [{
                    label: data.label[0],
                    value: {id: data.value[0]}
                }]);
            }
        });
    },

    createJSONDataHtml: function(id, data) {
        var html = '<script type="application/json" class="${id}"><!-- ${data} --></script>'.template({
            id: id,
            data: Object.isString(data) ? data : JSON.stringify(data)
        });

        return html;
    },

    createMenuEditorWidgetHtml: function(options) {
        options = $.extend({
            id: 'test-menu-id'
        }, options || {});

        return (
            '<div class="menu-edit-widget" id="${id}">' +
                '${initialData}' +
                '${regularChoices}' +
                '<div class="menu-edit-entries-container">' +
                    '<div class="menu-edit-entries"></div>' +
                '</div>' +
                '<div class="menu-edit-widget-creations">' +
                    '<button class="ui-creme-actionbutton new-entries new-regular-entries" type="button">Add regular entries</button>' +
                    '${customButtons}' +
                '</div>' +
            '</div>'
        ).template({
            initialData: this.createJSONDataHtml('menu-edit-initial-data', options.initial || []),
            regularChoices: this.createJSONDataHtml('menu-edit-regular-choices', options.regularChoices || []),
            id: options.id,
            customButtons: (options.customButtons || []).map(function(button) {
                return (
                    '<button class="ui-creme-actionbutton new-entries new-extra-entry" type="button" data-url="${url}">${label}</button>'
                ).template(button);
            }).join('')
        });
    },

    createMenuItemHtml: function(options) {
        options = options || {};

        return (
            '<div class="menu-config-entry0" data-reorderable-menu-container-url="${url}">' +
                '<div class="menu-config-entry0-header">' +
                    '<span class="menu-config-entry0-header-title">${title}</span>' +
                '</div>' +
                '<div class="menu-config-entry0-content"><ul>' +
                    '${items}' +
                '</ul></div>' +
            '</div>'
        ).template({
            url: options.url,
            items: (options.items || []).map(function(item) {
                return '<li class="menu-config-entry0-${id}>${label}</li>'.template(item);
            }).join('')
        });
    },

    createMenuHtml: function(options) {
        options = options || {};

        return (
            '<div class="menu-config-container">${menus}</div>' +
            '<div class="menu-config-actions">${addRoot}${addSpecialRoot}</div>'
        ).template({
            items: (options.menus || []).map(this.createMenuEditorItemHtml.bind(this)).join(''),
            addRoot: this.createBrickActionHtml({
                url: '/mock/menu/add',
                action: 'add'
            }),
            addSpecialRoot: this.createBrickActionHtml({
                url: '/mock/menu/add/special',
                action: 'add'
            })
        });
    },

    createMenuBrickHtml: function(options) {
        options = $.extend({
            menu: {}
        }, options || {});

        var content = options.models.map(this.createMenuHtml.bind(this)).join('');

        return this.createBrickHtml($.extend({
            content: content
        }, options));
    },

    createMenuBrick: function(options) {
        var html = this.createMenuEditorBrickHtml(options);

        var element = $(html).appendTo(this.qunitFixture());
        var widget = creme.widget.create(element);
        var brick = widget.brick();

        this.assert.equal(true, brick.isBound());
        this.assert.equal(false, brick.isLoading());

        return widget;
    }
}));

QUnit.test('creme.MenuEditor (missing initial data)', function(assert) {
    var element = $(this.createMenuEditorWidgetHtml({}));

    this.assertRaises(function() {
        return new creme.MenuEditor(element, {});
    }, Error, 'Error: MenuEditor missing options.initialSelector');

    this.assertRaises(function() {
        return new creme.MenuEditor(element, {initialSelector: 'nowhere'});
    }, Error);
});

QUnit.test('creme.MenuEditor (invalid initial data)', function(assert) {
    var element = $(this.createMenuEditorWidgetHtml({
        initial: 'invalid{"json"'
    }));

    this.assertRaises(function() {
        return new creme.MenuEditor(element, {
            initialSelector: '.menu-edit-initial-data',
            regularChoicesSelector: '.menu-edit-regular-choices'
        });
    });
});

QUnit.test('creme.MenuEditor (invalid regular entries)', function(assert) {
    var element = $(this.createMenuEditorWidgetHtml({
        regularChoices: 'invalid{"json"'
    }));

    this.assertRaises(function() {
        return new creme.MenuEditor(element, {
            initialSelector: '.menu-edit-initial-data',
            regularChoicesSelector: '.menu-edit-regular-choices'
        });
    });
});


QUnit.test('creme.MenuEditor (empty initial, empty regular entries)', function(assert) {
    var element = $(this.createMenuEditorWidgetHtml({
        initial: [],
        regularChoices: []
    }));

    var editor = new creme.MenuEditor(element, {
        initialSelector: '.menu-edit-initial-data',
        regularChoicesSelector: '.menu-edit-regular-choices'
    });

    assert.deepEqual(editor.value(), []);
    assert.deepEqual(editor.entries(), []);
    assert.equal(element.find('.new-regular-entries').length, 0);
});


QUnit.test('creme.MenuEditor (empty initial, regular entries)', function(assert) {
    var element = $(this.createMenuEditorWidgetHtml({
        initial: [],
        regularChoices: [
            ['Item A', 'item-a'],
            ['Item B', 'item-b']
        ]
    }));

    var editor = new creme.MenuEditor(element, {
        initialSelector: '.menu-edit-initial-data',
        regularChoicesSelector: '.menu-edit-regular-choices'
    });

    assert.deepEqual(editor.value(), []);
    assert.deepEqual(editor.entries(), []);
    assert.equal(element.find('.menu-edit-entry').length, 0);
    assert.equal(element.find('.new-regular-entries').length, 1);
});

QUnit.test('creme.MenuEditor (initial)', function(assert) {
    var element = $(this.createMenuEditorWidgetHtml({
        initial: [
            {label: "Item A", value: {id: "item-a"}},
            {label: "Item B", value: {id: "item-b"}}
        ]
    }));

    var editor = new creme.MenuEditor(element, {
        initialSelector: '.menu-edit-initial-data',
        regularChoicesSelector: '.menu-edit-regular-choices'
    });

    assert.deepEqual(editor.value(), [
        {id: "item-a"},
        {id: "item-b"}
    ]);
    assert.deepEqual(editor.entries(), [
        {id: "item-a"},
        {id: "item-b"}
    ]);

    assert.equal(element.find('.menu-edit-entry').length, 2);
    assert.deepEqual(element.find('.menu-edit-entry-item-a').data('value'), {id: "item-a"});
    assert.deepEqual(element.find('.menu-edit-entry-item-b').data('value'), {id: "item-b"});
});

QUnit.test('creme.MenuEditor (add regular entry, cancel)', function(assert) {
    var element = $(this.createMenuEditorWidgetHtml({
        regularChoices: [
            ['item-a', 'Item A'],
            ['item-b', 'Item B'],
            ['item-c', 'Item C']
        ]
    }));

    var editor = new creme.MenuEditor(element, {
        initialSelector: '.menu-edit-initial-data',
        regularChoicesSelector: '.menu-edit-regular-choices'
    });

    assert.deepEqual(editor.value(), []);
    assert.deepEqual(0, element.find('.menu-edit-entry').length);

    element.find('.new-regular-entries').trigger('click');

    var dialog = this.assertOpenedDialog();

    var select = dialog.find('.menu-edit-regular-entries select[name="entry_type"]');
    assert.deepEqual(select.val(), []);
    assert.deepEqual([
        {text: 'Item A', value: 'item-a'},
        {text: 'Item B', value: 'item-b'},
        {text: 'Item C', value: 'item-c'}
    ], select.find('option').map(function() {
        return {text: $(this).text(), value: $(this).attr('value')};
    }).get());

    this.closeDialog();
    assert.equal(0, element.find('.menu-edit-entry').length);
});

QUnit.test('creme.MenuEditor (add regular entry, submit)', function(assert) {
    var element = $(this.createMenuEditorWidgetHtml({
        regularChoices: [
            ['item-a', 'Item A'],
            ['item-b', 'Item B'],
            ['item-c', 'Item C']
        ]
    }));

    var editor = new creme.MenuEditor(element, {
        initialSelector: '.menu-edit-initial-data',
        regularChoicesSelector: '.menu-edit-regular-choices'
    });

    assert.deepEqual(editor.value(), []);
    assert.deepEqual(0, element.find('.menu-edit-entry').length);

    element.find('.new-regular-entries').trigger('click');

    var dialog = this.assertOpenedDialog();

    var select = dialog.find('.menu-edit-regular-entries select[name="entry_type"]');
    assert.deepEqual(select.val(), []);
    assert.deepEqual([
        {text: 'Item A', value: 'item-a'},
        {text: 'Item B', value: 'item-b'},
        {text: 'Item C', value: 'item-c'}
    ], select.find('option').map(function() {
        return {text: $(this).text(), value: $(this).attr('value')};
    }).get());

    select.val(['item-a', 'item-c']);

    this.submitFormDialog();

    assert.deepEqual(editor.value(), [{id: 'item-a'}, {id: 'item-c'}]);
    assert.equal(2, element.find('.menu-edit-entry').length);
    assert.deepEqual([
        {
            classes: 'menu-edit-entry menu-edit-entry-item-a',
            value: {id: "item-a"},
            text: 'Item A'
        },
        {
            classes: 'menu-edit-entry menu-edit-entry-item-c',
            value: {id: "item-c"},
            text: 'Item C'
        }
    ], element.find('.menu-edit-entry').map(function() {
        return {
            classes: $(this).attr('class'),
            value: $(this).data('value'),
            text: $(this).find('span').text()
        };
    }).get());
});

QUnit.test('creme.MenuEditor (add regular entry, initial)', function(assert) {
    var element = $(this.createMenuEditorWidgetHtml({
        initial: [
            {label: 'Item A', value: {id: 'item-a'}},
            {label: 'Item C', value: {id: 'item-c'}}
        ],
        regularChoices: [
            ['item-a', 'Item A'],
            ['item-b', 'Item B'],
            ['item-c', 'Item C']
        ]
    }));

    var editor = new creme.MenuEditor(element, {
        initialSelector: '.menu-edit-initial-data',
        regularChoicesSelector: '.menu-edit-regular-choices'
    });

    assert.deepEqual(editor.value(), [{id: 'item-a'}, {id: 'item-c'}]);
    assert.deepEqual(2, element.find('.menu-edit-entry').length);
    assert.deepEqual([
        {
            classes: 'menu-edit-entry menu-edit-entry-item-a',
            value: {id: "item-a"},
            text: 'Item A'
        },
        {
            classes: 'menu-edit-entry menu-edit-entry-item-c',
            value: {id: "item-c"},
            text: 'Item C'
        }
    ], element.find('.menu-edit-entry').map(function() {
        return {
            classes: $(this).attr('class'),
            value: $(this).data('value'),
            text: $(this).find('span').text()
        };
    }).get());

    element.find('.new-regular-entries').trigger('click');

    var dialog = this.assertOpenedDialog();

    var select = dialog.find('.menu-edit-regular-entries select[name="entry_type"]');
    assert.deepEqual(select.val(), []);
    assert.deepEqual([
        {text: 'Item B', value: 'item-b'}
    ], select.find('option').map(function() {
        return {text: $(this).text(), value: $(this).attr('value')};
    }).get());

    select.val(['item-b']);

    this.submitFormDialog();

    assert.deepEqual(editor.value(), [{id: 'item-a'}, {id: 'item-c'}, {id: 'item-b'}]);
    assert.equal(3, element.find('.menu-edit-entry').length);
    assert.deepEqual([
        {
            classes: 'menu-edit-entry menu-edit-entry-item-a',
            value: {id: "item-a"},
            text: 'Item A'
        },
        {
            classes: 'menu-edit-entry menu-edit-entry-item-c',
            value: {id: "item-c"},
            text: 'Item C'
        },
        {
            classes: 'menu-edit-entry menu-edit-entry-item-b',
            value: {id: "item-b"},
            text: 'Item B'
        }
    ], element.find('.menu-edit-entry').map(function() {
        return {
            classes: $(this).attr('class'),
            value: $(this).data('value'),
            text: $(this).find('span').text()
        };
    }).get());
});

QUnit.test('creme.MenuEditor (add regular entry, all used)', function(assert) {
    var element = $(this.createMenuEditorWidgetHtml({
        initial: [
            {label: 'Item A', value: {id: 'item-a'}},
            {label: 'Item B', value: {id: 'item-b'}}
        ],
        regularChoices: [
            ['item-a', 'Item A'],
            ['item-b', 'Item B']
        ]
    }));

    var editor = new creme.MenuEditor(element, {
        initialSelector: '.menu-edit-initial-data',
        regularChoicesSelector: '.menu-edit-regular-choices'
    });

    assert.deepEqual(editor.value(), [{id: 'item-a'}, {id: 'item-b'}]);

    element.find('.new-regular-entries').trigger('click');

    this.assertOpenedDialog(gettext('All menu entries are already used.'));
});

QUnit.test('creme.MenuEditor (remove regular entry)', function(assert) {
    var element = $(this.createMenuEditorWidgetHtml({
        initial: [
            {label: 'Item A', value: {id: 'item-a'}},
            {label: 'Item B', value: {id: 'item-b'}}
        ],
        regularChoices: [
            ['item-a', 'Item A'],
            ['item-b', 'Item B'],
            ['item-c', 'Item C']
        ]
    }));

    var editor = new creme.MenuEditor(element, {
        initialSelector: '.menu-edit-initial-data',
        regularChoicesSelector: '.menu-edit-regular-choices'
    });

    assert.deepEqual(editor.value(), [{id: 'item-a'}, {id: 'item-b'}]);

    element.find('.menu-edit-entry-item-b button').trigger('click');

    assert.deepEqual(editor.value(), [{id: 'item-a'}]);
});

QUnit.test('creme.MenuEditor (add special entry)', function(assert) {
    var element = $(this.createMenuEditorWidgetHtml({
        initial: [
            {label: 'Item A', value: {id: 'item-a'}}
        ],
        regularChoices: [
            ['item-a', 'Item A'],
            ['item-b', 'Item B']
        ],
        customButtons: [
            {url: 'mock/menu/custom', label: 'Custom item'}
        ]
    }));

    var editor = new creme.MenuEditor(element, {
        initialSelector: '.menu-edit-initial-data',
        regularChoicesSelector: '.menu-edit-regular-choices'
    });

    assert.deepEqual(editor.value(), [{id: 'item-a'}]);

    element.find('.new-extra-entry').trigger('click');

    var dialog = this.assertOpenedDialog();

    dialog.find('[name="label"]').val('Custom Item');
    dialog.find('[name="value"]').val('item-custom');

    this.submitFormDialog();

    assert.deepEqual(editor.value(), [{id: 'item-a'}, {id: 'item-custom'}]);
});

}(jQuery));
