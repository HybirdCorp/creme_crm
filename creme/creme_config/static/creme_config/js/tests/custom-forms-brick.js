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
//           '<div class="brick-list-item customform-config-item customform-config-${state}">' +
           '<div class="brick-list-item customform-config-ctype ${state}">' +
//               '<div class="customform-config-group-title">' +
               '<div class="customform-config-ctype-title">' +
                    '<span>${ctypeName}</span>' +
                    '<a class="customform-config-show-details" href="#" data-ct-id="${ctypeId}">Show</a>' +
                    '<a class="customform-config-hide-details" href="#">Hide</a>' +
               '</div>' +
//               '<div class="customform-config-group brick-table">' +
//                    '<table class="brick-table-content"><tbody>' +
//                        '<tr>' +
//                            '<td class="customform-config-ctype-label">${ctypeName}</td>' +
//                            '<td class="customform-config-fields">' +
//                                '<table><tbody class="customform-config-blocks">' +
//                                    '${groups}' +
//                                '</tbody></table>' +
//                                '<div class="customform-config-fields-actions"></div>' +
//                            '</td>' +
//                            '<td class="customform-config-errors"></td>' +
//                        '</tr>' +
//                    '</tbody></table>' +
//               '</div>' +
               '<div class="customform-config-ctype-content">' +
                    '<p class="help-instructions">Drag and drop the groups to order them.</p>' +
                    '<div class="customform-config-descriptor">' +
                        '<div class="customform-config-descriptor-title">' +
                            '<span>Creation form</span>' +
                        '</div>' +
                        '<div class="customform-config-items">' +
                            '<div class="customform-config-item customform-config-item-collapsed">' +
                                '<div class="customform-config-item-title">' +
                                    '<div class="toggle-icon-container toggle-icon-expand" title="Show this form"><div class="toggle-icon"></div></div>' +
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
//            state: options.collapsed ? 'collapsed' : 'expanded',
            state: options.collapsed ? 'customform-config-collapsed' : '',
            ctypeId: options.ctypeId,
            ctypeName: options.ctypeName,
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

        equal(true, brick.isBound());
        equal(false, brick.isLoading());

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

    equal(controller.isBound(), false);
    controller.bind(brick);
    equal(controller.isBound(), true);

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
//            ctypeId: 'ctype-a',
            ctypeId: ctypeIdA,
            ctypeName: 'Type A',
            groups: [{
                reorderUrl: 'mock/group/reorder/0',
                fields: [{name: 'a-field-a'}, {name: 'a-field-b'}]
            }, {
                reorderUrl: 'mock/group/reorder/1',
                fields: [{name: 'a-field-c'}]
            }]
        }, {
            collapsed: true,
//            ctypeId: 'ctype-b',
            ctypeId: ctypeIdB,
            ctypeName: 'Type B',
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

    equal(controller.isBound(), true);
//    equal(controller.items().length, 2);
    var ctypeElements = controller.ctypes();
    equal(ctypeElements.length, 2);

//    equal(controller.item('ctype-a').length, 1);
//    equal(controller.item('ctype-b').length, 1);
//    equal(controller.item('unknown').length, 0);
    equal(controller.ctype(ctypeIdA).length, 1);
    equal(controller.ctype(ctypeIdB).length, 1);
    equal(controller.ctype('unknown').length, 0);
});

QUnit.test('creme.FormGroupsController (toggle content type)', function(assert) {
    var ctypeIdA = 12;
    var ctypeIdB = 25;
    var brick = this.createFormGroupsBrick({
        models: [{
//            ctypeId: 'ctype-a',
            ctypeId: ctypeIdA,
            ctypeName: 'Type A',
            collapsed: true
        }, {
//            ctypeId: 'ctype-b',
            ctypeId: ctypeIdB,
            ctypeName: 'Type B',
            collapsed: false
        }]
    }).brick();
    var controller = new creme.FormGroupsController({
        expandUrl: 'mock/group/expand'
    });

    controller.bind(brick);

//    equal(controller.item('ctype-a').is('.customform-config-collapsed'), true);
//    equal(controller.item('ctype-b').is('.customform-config-collapsed'), false);
    equal(controller.ctype(ctypeIdA).is('.customform-config-collapsed'), true);
    equal(controller.ctype(ctypeIdB).is('.customform-config-collapsed'), false);

    deepEqual([], this.mockBackendUrlCalls('mock/group/expand'));

//    controller.item('ctype-a').find('.customform-config-show-details').click();
    controller.ctype(ctypeIdA).find('.customform-config-show-details').click();

//    equal(controller.item('ctype-a').is('.customform-config-collapsed'), false);
//    equal(controller.item('ctype-b').is('.customform-config-collapsed'), true);
    equal(controller.ctype(ctypeIdA).is('.customform-config-collapsed'), false);
    equal(controller.ctype(ctypeIdB).is('.customform-config-collapsed'), true);

    deepEqual([
//        ['POST', {ct_id: 'ctype-a'}]
        ['POST', {ct_id: ctypeIdA}]
    ], this.mockBackendUrlCalls('mock/group/expand'));

//    brick.element().find('.customform-config-hide-details[data-ct-id="ctype-a"]').click();
//    controller.item('ctype-a').find('.customform-config-hide-details').click();
    controller.ctype(ctypeIdA).find('.customform-config-hide-details').click();

//    equal(controller.item('ctype-a').is('.customform-config-collapsed'), true);
//    equal(controller.item('ctype-b').is('.customform-config-collapsed'), true);
    equal(controller.ctype(ctypeIdA).is('.customform-config-collapsed'), true);
    equal(controller.ctype(ctypeIdB).is('.customform-config-collapsed'), true);

    deepEqual([
//        ['POST', {ct_id: 'ctype-a'}],
        ['POST', {ct_id: ctypeIdA}],
        ['POST', {ct_id: '0'}]
    ], this.mockBackendUrlCalls('mock/group/expand'));
});

QUnit.test('creme.FormGroupsController (reorder groups)', function(assert) {
    var ctypeIdA = 6;
    var ctypeIdB = 42;
    var brick = this.createFormGroupsBrick({
        models: [{
            collapsed: true,
//            ctypeId: 'ctype-a',
            ctypeId: ctypeIdA,
            ctypeName: 'Type A',
            groups: [{
                reorderUrl: 'mock/group/reorder/0',
                fields: [{name: 'a-field-a'}, {name: 'field-b'}]
            }, {
                reorderUrl: 'mock/group/reorder/1',
                fields: [{name: 'a-field-c'}]
            }]
        }, {
            collapsed: true,
//            ctypeId: 'ctype-b',
            ctypeId: ctypeIdB,
            ctypeName: 'Type B',
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

    equal(controller.isBound(), true);
//    equal(controller.items().length, 2);
    equal(controller.ctypes().length, 2);

    deepEqual([], this.mockBackendCalls());

//    var groups = controller.item('ctype-a').find('.customform-config-blocks');
    var groups = controller.ctype(ctypeIdA).find('.customform-config-blocks');
    var group = groups.find('[data-reorderable-form-group-url="mock/group/reorder/0"]');

    groups.sortable('instance')._trigger('update', this.fakeMouseEvent('mouseup'), {
        item: group
    });

    deepEqual([
        [
            'mock/group/reorder/0', 'POST',
            {target: group.index()},
            {delay: 0, enableUriSearch: false, sync: true}
        ],
        [
            'mock/brick/all/reload',
            'GET',
            {brick_id: ['brick-for-test'], extra_data: '{}'},
            {dataType: 'json', delay: 0, enableUriSearch: false, sync: true}
          ]
    ], this.mockBackendCalls());
});


QUnit.test('creme.FormGroupsController (reorder groups, failure)', function(assert) {
    var ctypeIdA = 6;
    var ctypeIdB = 42;
    var brick = this.createFormGroupsBrick({
        models: [{
            collapsed: true,
//            ctypeId: 'ctype-a',
            ctypeId: ctypeIdA,
            ctypeName: 'Type A',
            groups: [{
                reorderUrl: 'mock/group/reorder/0/fail',
                fields: [{name: 'a-field-a'}, {name: 'field-b'}]
            }, {
                reorderUrl: 'mock/group/reorder/1',
                fields: [{name: 'a-field-c'}]
            }]
        }, {
            collapsed: true,
//            ctypeId: 'ctype-b',
            ctypeId: ctypeIdB,
            ctypeName: 'Type B',
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

    equal(controller.isBound(), true);
//    equal(controller.items().length, 2);
    equal(controller.ctypes().length, 2);

    deepEqual([], this.mockBackendCalls());

//    var groups = controller.item('ctype-a').find('.customform-config-blocks');
    var groups = controller.ctype(ctypeIdA).find('.customform-config-blocks');
    var group = groups.find('[data-reorderable-form-group-url="mock/group/reorder/0/fail"]');

    groups.sortable('instance')._trigger('update', this.fakeMouseEvent('mouseup'), {
        item: group
    });

    deepEqual([
        ['mock/group/reorder/0/fail', 'POST', {target: group.index()}, {delay: 0, enableUriSearch: false, sync: true}],
        ['mock/brick/all/reload', 'GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}, {dataType: "json", delay: 0, enableUriSearch: false, sync: true}]
    ], this.mockBackendCalls());
});

QUnit.test('creme.FormGroupsController (toggle item)', function(assert) {
    var ctypeIdA = 12;
    var brick = this.createFormGroupsBrick({
        models: [{
            ctypeId: ctypeIdA,
            ctypeName: 'Type A',
            collapsed: true
        }]
    }).brick();
    var controller = new creme.FormGroupsController({
        expandUrl: 'mock/group/expand'
    });

    controller.bind(brick);

//    var item = controller.ctype(ctypeIdA).find('.customform-config-item:first');
    var item = controller.ctype(ctypeIdA).find('.customform-config-item').first();
    equal(item.is('.customform-config-item-collapsed'), true);

    item.find('.toggle-icon-expand').click();
    equal(item.is('.customform-config-item-collapsed'), false);

    item.find('.toggle-icon-collapse').click();
    equal(item.is('.customform-config-item-collapsed'), true);
});

}(jQuery));
