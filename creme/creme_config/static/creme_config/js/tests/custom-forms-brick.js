(function($) {
"use strict";

QUnit.module("creme.FormGroupsController", new QUnitMixin(QUnitEventMixin,
                                                          QUnitAjaxMixin,
                                                          QUnitBrickMixin,
                                                          QUnitDialogMixin,
                                                          QUnitMouseMixin, {
    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendPOST({
            'mock/group/reorder/0': backend.response(200, ''),
            'mock/group/reorder/0/fail': backend.response(400, 'Invalid request'),
            'mock/group/reorder/1': backend.response(200, ''),
            'mock/group/reorder/2': backend.response(200, ''),
            'mock/group/expand': backend.response(200, '')
        });
    },

    createJSONDataHtml: function(data) {
        var html = '<script type="application/json" id="brick-config-choices">${data}</script>'.template({
            data: JSON.stringify(data)
        });

        return html;
    },

    createFormFieldGroupHtml: function(options) {
        options = $.extend({
            reorderUrl: '',
            fields: []
        }, options || {});

        return (
            '<tr data-reorderable-form-group-url="${reorderUrl}">' +
                '<td class="customform-config-block-container">' +
                    '<div class="customform-config-block customform-config-block-layout-regular">' +
                        '<div class="customform-config-block-header">' +
                            '<span class="customform-config-block-header-title">{{group.name}}</span>' +
                        '</div>' +
                        '<div class="customform-config-block-content">' +
                            '<table><tbody>${fields}</tbody></table>' +
                        '</div>' +
                    '</div>' +
                '</td>' +
             '</tr>'
        ).template({
            reorderUrl: options.reorderUrl,
            fields: options.fields.map(function(field) {
                return '<tr><td data-table-primary-column>${name}</td></tr>'.template(field);
            }).join('')
        });
    },

    createFormGroupsItemHtml: function(options) {
        options = $.extend({
            collapsed: true,
            ctypeId: 'ctype-a',
            ctypeName: 'Type A',
            groups: []
        }, options || {});

        return (
           '<div class="brick-list-item customform-config-ctype ${state}">' +
               '<div class="customform-config-ctype-title">' +
                    '<span>${ctypeName}</span>' +
                    '<a class="customform-config-show-details" href="#" data-ct-id="${ctypeId}">Show</a>' +
                    '<a class="customform-config-hide-details" href="#" data-ct-id="${ctypeId}">Hide</a>' +
               '</div>' +
               '<div class="customform-config-ctype-content">' +
                    '<p class="help-instructions">Drag and drop the groups to order them.</p>' +
                    '<div class="customform-config-descriptor">' +
                        '<div class="customform-config-descriptor-title">' +
                            '<span>Creation form</span>' +
                        '</div>' +
                        '<div class="customform-config-items">' +
                            '<div class="customform-config-item customform-config-collapsed">' +
                                '<div class="customform-config-item-title">' +
                                    '<div class="toggle-icon-container toggle-icon-expand" data-item-id="${itemId}" title="Show this form"><div class="toggle-icon"></div></div>' +
                                    '<div class="toggle-icon-container toggle-icon-collapse" title="Hide this form"><div class="toggle-icon"></div></div>' +
                                    'Default form' +
                                 '</div>' +
                                '<div class="customform-config-item-content">' +
                                    '<div class="customform-config-fields">' +
                                        '<table><tbody class="customform-config-blocks">' +
                                            '${groups}' +
                                        '</tbody></table>' +
                                        '<div class="customform-config-fields-actions"></div>' +
                                    '</div>' +
                                    '<div class="customform-config-errors"></div>' +
                                '</div>' +
                            '</div>' +
                        '</div>' +
                    '</div>' +
               '</div>' +

           '</div>'
        ).template({
            state: options.collapsed ? 'customform-config-collapsed' : '',
            ctypeId: options.ctypeId,
            ctypeName: options.ctypeName,
            itemId: options.itemId,
            groups: options.groups.map(this.createFormFieldGroupHtml.bind(this)).join('')
        });
    },

    createFormGroupsBrickHtml: function(options) {
        options = $.extend({
            models: []
        }, options || {});

        var content = options.models.map(this.createFormGroupsItemHtml.bind(this)).join('');

        return this.createBrickHtml($.extend({
            content: content
        }, options));
    },

    createFormGroupsBrick: function(options) {
        var html = this.createFormGroupsBrickHtml(options);

        var element = $(html).appendTo(this.qunitFixture());
        var widget = creme.widget.create(element);
        var brick = widget.brick();

        this.assert.equal(true, brick.isBound());
        this.assert.equal(false, brick.isLoading());

        return widget;
    }
}));

QUnit.test('creme.FormGroupsController (invalid expand url)', function(assert) {
    this.assertRaises(function() {
        return new creme.FormGroupsController({});
    }, Error, 'Error: FormGroupsController expandUrl is not set');
});

QUnit.test('creme.FormGroupsController (bind)', function(assert) {
    var brick = this.createFormGroupsBrick({}).brick();
    var controller = new creme.FormGroupsController({
        expandUrl: 'mock/group/expand'
    });

    assert.equal(controller.isBound(), false);
    controller.bind(brick);
    assert.equal(controller.isBound(), true);

    this.assertRaises(function() {
        controller.bind(brick);
    }, Error, 'Error: FormGroupsController is already bound');
});

QUnit.test('creme.FormGroupsController (items)', function(assert) {
    var ctypeIdA = 12;
    var ctypeIdB = 25;
    var brick = this.createFormGroupsBrick({
        models: [{
            collapsed: true,
            ctypeId: ctypeIdA,
            ctypeName: 'Type A',
            itemId: 42,
            groups: [{
                reorderUrl: 'mock/group/reorder/0',
                fields: [{name: 'a-field-a'}, {name: 'a-field-b'}]
            }, {
                reorderUrl: 'mock/group/reorder/1',
                fields: [{name: 'a-field-c'}]
            }]
        }, {
            collapsed: true,
            ctypeId: ctypeIdB,
            ctypeName: 'Type B',
            itemId: 43,
            groups: [{
                reorderUrl: 'mock/group/reorder/2',
                fields: [{name: 'b-field-a'}, {name: 'b-field-b'}]
            }]
        }]
    }).brick();
    var controller = new creme.FormGroupsController({
        expandUrl: 'mock/group/expand'
    });

    controller.bind(brick);
    assert.equal(controller.isBound(), true);

    var ctypeElements = controller.ctypes();
    assert.equal(ctypeElements.length, 2);

    assert.equal(controller.ctype(ctypeIdA).length, 1);
    assert.equal(controller.ctype(ctypeIdB).length, 1);
    assert.equal(controller.ctype('unknown').length, 0);
});

QUnit.test('creme.FormGroupsController (toggle content type)', function(assert) {
    var ctypeIdA = 12;
    var ctypeIdB = 25;
    var brick = this.createFormGroupsBrick({
        models: [{
            ctypeId: ctypeIdA,
            ctypeName: 'Type A',
            collapsed: true,
            itemId: 42
        }, {
            ctypeId: ctypeIdB,
            ctypeName: 'Type B',
            collapsed: false,
            itemId: 43
        }]
    }).brick();
    var controller = new creme.FormGroupsController({
        expandUrl: 'mock/group/expand'
    });

    controller.bind(brick);

    assert.equal(controller.ctype(ctypeIdA).is('.customform-config-collapsed'), true);
    assert.equal(controller.ctype(ctypeIdB).is('.customform-config-collapsed'), false);

    assert.deepEqual([], this.mockBackendUrlCalls('mock/group/expand'));

    controller.ctype(ctypeIdA).find('.customform-config-show-details').trigger('click');

    assert.equal(controller.ctype(ctypeIdA).is('.customform-config-collapsed'), false);
    assert.equal(controller.ctype(ctypeIdB).is('.customform-config-collapsed'), true);

    assert.deepEqual([
        ['POST', {action: 'show', ct_id: ctypeIdA}]
    ], this.mockBackendUrlCalls('mock/group/expand'));

    controller.ctype(ctypeIdA).find('.customform-config-hide-details').trigger('click');

    assert.equal(controller.ctype(ctypeIdA).is('.customform-config-collapsed'), true);
    assert.equal(controller.ctype(ctypeIdB).is('.customform-config-collapsed'), true);

    assert.deepEqual([
        ['POST', {action: 'show', ct_id: ctypeIdA}],
        ['POST', {action: 'hide', ct_id: ctypeIdA}]
    ], this.mockBackendUrlCalls('mock/group/expand'));
});

QUnit.test('creme.FormGroupsController (toggle custom form item)', function(assert) {
    var ctypeId = 12;
    var itemId = 63;
    var brick = this.createFormGroupsBrick({
        models: [{
            ctypeId: ctypeId,
            ctypeName: 'Type A',
            collapsed: false,
            itemId: itemId
        }]
    }).brick();
    var controller = new creme.FormGroupsController({
        expandUrl: 'mock/group/expand'
    });

    controller.bind(brick);
    assert.deepEqual([], this.mockBackendUrlCalls('mock/group/expand'));
    assert.equal(controller.ctype(ctypeId).find('.customform-config-item').is('.customform-config-collapsed'), true);

    controller.ctype(ctypeId).find('.toggle-icon-expand').trigger('click');
    assert.equal(controller.ctype(ctypeId).find('.customform-config-item').is('.customform-config-collapsed'), false);
    assert.deepEqual([
        ['POST', {action: 'show', item_id: itemId}]
    ], this.mockBackendUrlCalls('mock/group/expand'));
});

QUnit.test('creme.FormGroupsController (reorder groups)', function(assert) {
    var ctypeIdA = 6;
    var ctypeIdB = 42;
    var brick = this.createFormGroupsBrick({
        models: [{
            collapsed: true,
            ctypeId: ctypeIdA,
            ctypeName: 'Type A',
            itemId: 42,
            groups: [{
                reorderUrl: 'mock/group/reorder/0',
                fields: [{name: 'a-field-a'}, {name: 'field-b'}]
            }, {
                reorderUrl: 'mock/group/reorder/1',
                fields: [{name: 'a-field-c'}]
            }]
        }, {
            collapsed: true,
            ctypeId: ctypeIdB,
            ctypeName: 'Type B',
            itemId: 43,
            groups: [{
                reorderUrl: 'mock/group/reorder/2',
                fields: [{name: 'b-field-a'}, {name: 'b-field-b'}]
            }]
        }]
    }).brick();
    var controller = new creme.FormGroupsController({
        expandUrl: 'mock/group/expand'
    });

    controller.bind(brick);
    assert.equal(controller.isBound(), true);
    assert.equal(controller.ctypes().length, 2);

    assert.deepEqual([], this.mockBackendCalls());

    var groups = controller.ctype(ctypeIdA).find('.customform-config-blocks');
    var group = groups.find('[data-reorderable-form-group-url="mock/group/reorder/0"]');

    groups.sortable('instance')._trigger('update', this.fakeMouseEvent('mouseup'), {
        item: group
    });

    assert.deepEqual([
        [
            'mock/group/reorder/0', 'POST',
            {target: group.index()},
            {delay: 0, enableUriSearch: false, sync: true}
        ],
        [
            'mock/brick/all/reload',
            'GET',
            {brick_id: ['creme_core-test'], extra_data: '{}'},
            {dataType: 'json', delay: 0, enableUriSearch: false, sync: true}
          ]
    ], this.mockBackendCalls().map(function(e) {
        var request = _.omit(e[3], 'progress');
        return [e[0], e[1], e[2], request];
    }));
});


QUnit.test('creme.FormGroupsController (reorder groups, failure)', function(assert) {
    var ctypeIdA = 6;
    var ctypeIdB = 42;
    var brick = this.createFormGroupsBrick({
        models: [{
            collapsed: true,
            ctypeId: ctypeIdA,
            ctypeName: 'Type A',
            itemId: 42,
            groups: [{
                reorderUrl: 'mock/group/reorder/0/fail',
                fields: [{name: 'a-field-a'}, {name: 'field-b'}]
            }, {
                reorderUrl: 'mock/group/reorder/1',
                fields: [{name: 'a-field-c'}]
            }]
        }, {
            collapsed: true,
            ctypeId: ctypeIdB,
            ctypeName: 'Type B',
            itemId: 43,
            groups: [{
                reorderUrl: 'mock/group/reorder/2',
                fields: [{name: 'b-field-a'}, {name: 'b-field-b'}]
            }]
        }]
    }).brick();
    var controller = new creme.FormGroupsController({
        expandUrl: 'mock/group/expand'
    });

    controller.bind(brick);
    assert.equal(controller.isBound(), true);
    assert.equal(controller.ctypes().length, 2);

    assert.deepEqual([], this.mockBackendCalls());

    var groups = controller.ctype(ctypeIdA).find('.customform-config-blocks');
    var group = groups.find('[data-reorderable-form-group-url="mock/group/reorder/0/fail"]');

    groups.sortable('instance')._trigger('update', this.fakeMouseEvent('mouseup'), {
        item: group
    });

    assert.deepEqual([
        ['mock/group/reorder/0/fail', 'POST', {target: group.index()}, {delay: 0, enableUriSearch: false, sync: true}],
        [
            'mock/brick/all/reload', 'GET',
             {"brick_id": ["creme_core-test"], "extra_data": "{}"},
             {dataType: "json", delay: 0, enableUriSearch: false, sync: true}
        ]
    ], this.mockBackendCalls().map(function(e) {
        var request = _.omit(e[3], 'progress');
        return [e[0], e[1], e[2], request];
    }));
});

QUnit.test('creme.FormGroupsController (toggle item)', function(assert) {
    var ctypeIdA = 12;
    var brick = this.createFormGroupsBrick({
        models: [{
            ctypeId: ctypeIdA,
            ctypeName: 'Type A',
            collapsed: true,
            itemId: 42
        }]
    }).brick();
    var controller = new creme.FormGroupsController({
        expandUrl: 'mock/group/expand'
    });

    controller.bind(brick);

    var item = controller.ctype(ctypeIdA).find('.customform-config-item').first();
    assert.equal(item.is('.customform-config-collapsed'), true);

    item.find('.toggle-icon-expand').trigger('click');
    assert.equal(item.is('.customform-config-collapsed'), false);

    item.find('.toggle-icon-collapse').trigger('click');
    assert.equal(item.is('.customform-config-collapsed'), true);
});

}(jQuery));
