(function($) {

QUnit.module("creme.listview.actions", new QUnitMixin(QUnitEventMixin,
                                                      QUnitAjaxMixin,
                                                      QUnitDialogMixin,
                                                      QUnitListViewMixin, {
    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendGET({
        });

        this.setMockBackendPOST({
            'mock/entity/update': backend.response(200, ''),
            'mock/entity/clone': backend.response(200, 'mock/entity/clone/redirection')
        });
    },

    createSingleRowActionsListView: function(options) {
        return this.createListView({
            columns: [this.createCheckAllColumnHtml()],
            rows: [
                [this.createCheckCellHtml('1'), this.createIdCellHtml('1'), this.createActionCellHtml({actions: options.rowactions || []})]
            ]
        });
    },

    createHeaderActionsListView: function(options) {
        return this.createListView({
            columns: [this.createCheckAllColumnHtml()],
            actions: [
                {action: 'merge-selection', url: "/mock/entity/merge", attrs: {'data-row-min': 2, 'data-row-max': 2}},
                {action: 'delete-selection', url: "mock/entity/delete", attrs: {'data-row-min': 1}},
                {action: 'addto-selection', url: "mock/entity/addto", attrs: {'data-row-max': 3}}
            ],
            rows: [
                [this.createCheckCellHtml('1'), this.createIdCellHtml('1')],
                [this.createCheckCellHtml('2'), this.createIdCellHtml('2')],
                [this.createCheckCellHtml('3'), this.createIdCellHtml('3')],
                [this.createCheckCellHtml('4'), this.createIdCellHtml('4')],
                [this.createCheckCellHtml('5'), this.createIdCellHtml('5')]
            ]
        });
    },

    assertHeaderActionPopoverLinks: function(expected, popover) {
        var popoverLinks = $('.listview-actions-container [data-action]', popover);

        var linkInfo = function() {
            var item = $(this);
            return {
                action: item.attr('data-action'),
                title: item.attr('title'),
                disabled: item.is('.is-disabled')
            };
        };

        deepEqual(expected, popoverLinks.map(linkInfo).get());
    }
}));

QUnit.test('creme.listview.DeleteSelectedAction (no selection)', function(assert) {
    var list = this.createListView().controller();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete'
    }).on(this.listviewActionListeners);

    equal(0, list.selectedRowsCount());
    deepEqual([], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Please select at least one entity."));

    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.DeleteSelectedAction (not confirmed)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2,3');

    equal(2, list.selectedRowsCount());
    deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.DeleteSelectedAction (error)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete/fail'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('1,2');

    equal(2, list.selectedRowsCount());
    deepEqual(['1', '2'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([], this.mockListenerCalls('action-fail'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.acceptConfirmDialog();

    this.assertOpenedAlertDialog(undefined, gettext('Bad Request'));

    deepEqual([], this.mockListenerCalls('action-fail'));
    deepEqual([
        ['POST', {ids: '1,2'}]
    ], this.mockBackendUrlCalls('mock/entity/delete/fail'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['fail']], this.mockListenerCalls('action-fail'));
    deepEqual([
        ['POST', {ids: '1,2'}]
    ], this.mockBackendUrlCalls('mock/entity/delete/fail'));
    deepEqual([
        ['POST', {
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            rows: ['10'],
            selected_rows: ['1,2'],
            q_filter: ['{}'],
            ct_id: ['67'],
            content: 1,
            selection: ['multiple']}]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.DeleteSelectedAction (not allowed)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete/nothing'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('1,2');

    equal(2, list.selectedRowsCount());
    deepEqual(['1', '2'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([], this.mockListenerCalls('action-fail'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/delete/nothing'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.acceptConfirmDialog();

    var header = ngettext(' %d entity cannot be deleted.', ' %d entities cannot be deleted.', 2).format(2);
    this.assertOpenedAlertDialog(undefined, header);

    deepEqual([], this.mockListenerCalls('action-fail'));
    deepEqual([
        ['POST', {ids: '1,2'}]
    ], this.mockBackendUrlCalls('mock/entity/delete/nothing'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['fail']], this.mockListenerCalls('action-fail'));
    deepEqual([
        ['POST', {ids: '1,2'}]
    ], this.mockBackendUrlCalls('mock/entity/delete/nothing'));
    deepEqual([
        ['POST', {
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            rows: ['10'],
            selected_rows: ['1,2'],
            q_filter: ['{}'],
            ct_id: ['67'],
            content: 1,
            selection: ['multiple']}]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.DeleteSelectedAction (partially allowed)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete/firstonly'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('1,2,3');

    equal(3, list.selectedRowsCount());
    deepEqual(['1', '2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();
    this.acceptConfirmDialog();

    var header = ngettext('%d entity have been deleted.', '%d entities have been deleted.', 1).format(1) +
                 ngettext(' %d entity cannot be deleted.', ' %d entities cannot be deleted.', 2).format(2);

    deepEqual([], this.mockListenerCalls('action-fail'));
    deepEqual([
        ['POST', {ids: '1,2,3'}]
    ], this.mockBackendUrlCalls('mock/entity/delete/firstonly'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.assertOpenedAlertDialog(undefined, header);
    this.closeDialog();

    deepEqual([['fail']], this.mockListenerCalls('action-fail'));
    deepEqual([
        ['POST', {ids: '1,2,3'}]
    ], this.mockBackendUrlCalls('mock/entity/delete/firstonly'));
    deepEqual([
        ['POST', {
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            rows: ['10'],
            selected_rows: ['1,2,3'],
            q_filter: ['{}'],
            ct_id: ['67'],
            content: 1,
            selection: ['multiple']}]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.DeleteSelectedAction (ok)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('1,2,3');

    equal(3, list.selectedRowsCount());
    deepEqual(['1', '2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();
    this.acceptConfirmDialog();

    deepEqual([
        ['POST', {ids: '1,2,3'}]
    ], this.mockBackendUrlCalls('mock/entity/delete'));
    deepEqual([['done']], this.mockListenerCalls('action-done'));
    deepEqual([
        ['POST', {
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            rows: ['10'],
            selected_rows: ['1,2,3'],
            q_filter: ['{}'],
            ct_id: ['67'],
            content: 1,
            selection: ['multiple']}]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.AddToSelectedAction (no selection)', function(assert) {
    var list = this.createListView().controller();
    var action = new creme.lv_widget.AddToSelectedAction(list, {
        url: 'mock/entity/addto'
    }).on(this.listviewActionListeners);

    equal(0, list.selectedRowsCount());
    deepEqual([], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Please select at least one entity."));
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/addto'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.AddToSelectedAction (cancel)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.AddToSelectedAction(list, {
        url: 'mock/entity/addto'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2,3');

    equal(2, list.selectedRowsCount());
    deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([
        ['GET', {ids: ['2', '3']}]
    ], this.mockBackendUrlCalls('mock/entity/addto'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([
        ['GET', {ids: ['2', '3']}]
    ], this.mockBackendUrlCalls('mock/entity/addto'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.AddToSelectedAction (submit fail + cancel)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.AddToSelectedAction(list, {
        url: 'mock/entity/addto'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2,3');

    equal(2, list.selectedRowsCount());
    deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();
    deepEqual([
        ['GET', {ids: ['2', '3']}]
    ], this.mockBackendUrlCalls('mock/entity/addto'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.assertOpenedDialog();
    deepEqual([
        ['GET', {ids: ['2', '3']}]
    ], this.mockBackendUrlCalls('mock/entity/addto'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.AddToSelectedAction (ok)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.AddToSelectedAction(list, {
        url: 'mock/entity/addto'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2,3');

    equal(2, list.selectedRowsCount());
    deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([
        ['GET', {ids: ['2', '3']}]
    ], this.mockBackendUrlCalls('mock/entity/addto'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.submitFormDialog({
        addto: 'ok'
    });

    this.assertClosedDialog();

    deepEqual([
        ['GET', {ids: ['2', '3']}],
        ['POST', {addto: ["ok"], ids: ['2', '3']}]
    ], this.mockBackendUrlCalls('mock/entity/addto'));
    deepEqual([['done']], this.mockListenerCalls('action-done'));
    deepEqual([
        ['POST', {
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            rows: ['10'],
            selected_rows: ['2,3'],
            q_filter: ['{}'],
            ct_id: ['67'],
            content: 1,
            selection: ['multiple']}]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.EditSelectedAction (no selection)', function(assert) {
    var list = this.createListView().controller();
    var action = new creme.lv_widget.EditSelectedAction(list, {
        url: 'mock/entity/edit'
    }).on(this.listviewActionListeners);

    equal(0, list.selectedRowsCount());
    deepEqual([], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Please select at least one entity."));
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.EditSelectedAction (cancel)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.EditSelectedAction(list, {
        url: 'mock/entity/edit'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2,3');

    equal(2, list.selectedRowsCount());
    deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    equal($('.ui-dialog .bulk-selection-summary').length, 1);
    equal($('.ui-dialog .bulk-selection-summary').text(), '2 entities are selected');

    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([['GET', {}]], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([['GET', {}]], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.EditSelectedAction (submit => partially fail => close)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.EditSelectedAction(list, {
        url: 'mock/entity/edit'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2,3');

    equal(2, list.selectedRowsCount());
    deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([['GET', {}]], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.submitFormDialog({
        field_value: ''
    });

    this.assertOpenedDialog();

    equal($('.ui-dialog .bulk-selection-summary').text(), '2 entities are selected');
    deepEqual([
        ['GET', {}],
        ['POST', {
            entities: ['2', '3'],
            _bulk_fieldname: ['mock/entity/edit/field-a'],
            field_value: ['']
        }]
    ], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.EditSelectedAction (ok)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.EditSelectedAction(list, {
        url: 'mock/entity/edit'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2,3');

    equal(2, list.selectedRowsCount());
    deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([['GET', {}]], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.submitFormDialog({
        field_value: 'ok'
    });

    this.assertClosedDialog();

    deepEqual([['done']], this.mockListenerCalls('action-done'));

    deepEqual([
        ['mock/entity/edit', 'GET', {}],
        ['mock/entity/edit', 'POST', {
            entities: ['2', '3'],
            _bulk_fieldname: ['mock/entity/edit/field-a'],
            field_value: ['ok']
        }],
        ['mock/listview/reload', 'POST', {
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            rows: ['10'],
            selected_rows: ['2,3'],
            q_filter: ['{}'],
            ct_id: ['67'],
            content: 1,
            selection: ['multiple']
        }]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.listview.EditSelectedAction (field change)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.EditSelectedAction(list, {
        url: 'mock/entity/edit'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2,3');

    equal(2, list.selectedRowsCount());
    deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    var dialog = this.assertOpenedDialog();

    deepEqual([['GET', {}]], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    equal(dialog.find('[name="_bulk_fieldname"]').length, 1);
    dialog.find('[name="_bulk_fieldname"]').val('mock/entity/edit/field-b').trigger('change');

    this.assertOpenedDialog();

    deepEqual([
        ['mock/entity/edit', 'GET', {}],
        ['mock/entity/edit/field-b', 'GET', {}]
    ], this.mockBackendUrlCalls());

    this.submitFormDialog({
        field_value: 'ok'
    });

    deepEqual([['done']], this.mockListenerCalls('action-done'));

    deepEqual([
        ['mock/entity/edit', 'GET', {}],
        ['mock/entity/edit/field-b', 'GET', {}],
        ['mock/entity/edit/field-b', 'POST', {
            entities: ['2', '3'],
            _bulk_fieldname: ['mock/entity/edit/field-b'],
            field_value: ['ok']
        }],
        ['mock/listview/reload', 'POST', {
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            rows: ['10'],
            selected_rows: ['2,3'],
            q_filter: ['{}'],
            ct_id: ['67'],
            content: 1,
            selection: ['multiple']
        }]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.listview.MergeSelectedAction (no selection)', function(assert) {
    var list = this.createListView().controller();
    var action = new creme.lv_widget.MergeSelectedAction(list, {
        url: '/mock/entity/merge'
    }).on(this.listviewActionListeners);

    equal(0, list.selectedRowsCount());
    deepEqual([], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Please select 2 entities."));
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.listview.MergeSelectedAction (invalid selection)', function(assert) {
    var list = this.createListView().controller();
    var action = new creme.lv_widget.MergeSelectedAction(list, {
        url: '/mock/entity/merge'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2');

    equal(1, list.selectedRowsCount());
    deepEqual(['2'], list.selectedRows());

    this.assertClosedDialog();

    // try with one selection
    action.start();

    this.assertOpenedAlertDialog(gettext("Please select 2 entities."));
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockRedirectCalls());

    this.resetMockListenerCalls();

    list.element().find('#selected_rows').val('1,2,3');

    equal(3, list.selectedRowsCount());
    deepEqual(['1', '2', '3'], list.selectedRows());

    this.assertClosedDialog();

    // retry with 3 selections
    action.start();

    this.assertOpenedAlertDialog(gettext("Please select 2 entities."));
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.listview.MergeSelectedAction (ok)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.MergeSelectedAction(list, {
        url: '/mock/entity/merge'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2,3');

    equal(2, list.selectedRowsCount());
    deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertClosedDialog();

    deepEqual(['/mock/entity/merge?id1=2&id2=3'], this.mockRedirectCalls());
});

QUnit.test('creme.listview.actionregistry', function(assert) {
    var list = this.createListView().controller();
    var registry = list.actionBuilders();

    ok(Object.isSubClassOf(registry, creme.component.FactoryRegistry));

    ok(registry.has('update'));
    ok(registry.has('delete'));
    ok(registry.has('clone'));
    ok(registry.has('form'));
    ok(registry.has('redirect'));
    ok(registry.has('popover'));

    ok(registry.has('submit-lv-state'));
    ok(registry.has('edit-selection'));
    ok(registry.has('delete-selection'));
    ok(registry.has('addto-selection'));
    ok(registry.has('merge-selection'));
});

QUnit.test('creme.listview.row-action (update)', function(assert) {
    var list = this.createSingleRowActionsListView({
        rowactions: [{action: 'update', url: "mock/entity/update", data: {a: 12}}]
    }).controller();

    this.assertClosedPopover();
    list.element().find('.row-actions-trigger').trigger('click');

    var popover = this.assertOpenedPopover();
    $('.listview-actions-container [data-action]', popover).trigger('click');

    this.assertClosedPopover();
    this.assertClosedDialog();

    deepEqual([
        ['POST', {a: 12}]
    ], this.mockBackendUrlCalls('mock/entity/update'));

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC']
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.row-action (delete, canceled)', function(assert) {
    var list = this.createSingleRowActionsListView({
        rowactions: [{action: 'delete', url: "mock/entity/delete", data: {id: 12}}]
    }).controller();

    this.assertClosedPopover();
    list.element().find('.row-actions-trigger').trigger('click');

    var popover = this.assertOpenedPopover();
    $('.listview-actions-container [data-action]', popover).trigger('click');

    this.assertClosedPopover();

    this.assertOpenedConfirmDialog(gettext('Are you sure ?'));
    this.closeDialog();

    deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.row-action (delete)', function(assert) {
    var list = this.createSingleRowActionsListView({
        rowactions: [{action: 'delete', url: "mock/entity/delete", data: {id: 12}}]
    }).controller();

    this.assertClosedPopover();
    list.element().find('.row-actions-trigger').trigger('click');

    var popover = this.assertOpenedPopover();
    $('.listview-actions-container [data-action]', popover).trigger('click');

    this.assertClosedPopover();

    this.assertOpenedConfirmDialog(gettext('Are you sure ?'));
    this.acceptConfirmDialog();

    deepEqual([
        ['POST', {id: 12}]
    ], this.mockBackendUrlCalls('mock/entity/delete'));

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC']
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.row-action (clone, canceled)', function(assert) {
    var list = this.createSingleRowActionsListView({
        rowactions: [{action: 'clone', url: "mock/entity/clone", data: {id: 12}}]
    }).controller();

    this.assertClosedPopover();
    list.element().find('.row-actions-trigger').trigger('click');

    var popover = this.assertOpenedPopover();
    $('.listview-actions-container [data-action]', popover).trigger('click');

    this.assertClosedPopover();

    this.assertOpenedConfirmDialog(gettext('Do you really want to clone this entity?'));
    this.closeDialog();

    deepEqual([], this.mockBackendUrlCalls('mock/entity/clone'));
    deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.listview.row-action (clone)', function(assert) {
    var list = this.createSingleRowActionsListView({
        rowactions: [{action: 'clone', url: "mock/entity/clone", data: {id: 12}}]
    }).controller();

    this.assertClosedPopover();
    list.element().find('.row-actions-trigger').trigger('click');

    var popover = this.assertOpenedPopover();
    $('.listview-actions-container [data-action]', popover).trigger('click');

    this.assertClosedPopover();

    this.assertOpenedConfirmDialog(gettext('Do you really want to clone this entity?'));
    this.acceptConfirmDialog();

    deepEqual([
        ['POST', {id: 12}]
    ], this.mockBackendUrlCalls('mock/entity/clone'));
    deepEqual(['mock/entity/clone/redirection'], this.mockRedirectCalls());
});

QUnit.test('creme.listview.row-action (form)', function(assert) {
    var list = this.createSingleRowActionsListView({
        rowactions: [{action: 'form', url: "mock/entity/edit"}]
    }).controller();

    this.assertClosedPopover();
    list.element().find('.row-actions-trigger').trigger('click');

    var popover = this.assertOpenedPopover();
    $('.listview-actions-container [data-action]', popover).trigger('click');

    this.assertClosedPopover();

    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/entity/edit'));

    var dialog = this.assertOpenedDialog();
    dialog.find('[name="field_value"]').val('12');

    this.submitFormDialog();

    deepEqual([
        ['mock/entity/edit', 'GET', {}],
        ['mock/entity/edit', 'POST', {
            _bulk_fieldname: ['mock/entity/edit/field-a'],
            field_value: ["12"]
        }],
        ['mock/listview/reload', 'POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC']
        }]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.listview.row-action (redirect)', function(assert) {
    var list = this.createSingleRowActionsListView({
        rowactions: [{action: 'redirect', url: "${location}?redirect#hatbar"}]
    }).controller();

    this.assertClosedPopover();
    list.element().find('.row-actions-trigger').trigger('click');

    var popover = this.assertOpenedPopover();
    $('.listview-actions-container [data-action]', popover).trigger('click');

    this.assertClosedPopover();

    deepEqual([
        (new creme.ajax.URL(window.location.href).relativeUrl() + '?redirect#hatbar')
    ], this.mockRedirectCalls());
});

QUnit.test('creme.listview.header-actions (no selection)', function(assert) {
    var widget = this.createHeaderActionsListView();
    var list = widget.controller();
//    var rows = widget.element.find('table:first tr.selectable');
    var rows = widget.element.find('table').first().find('tr.selectable');

    equal(5, rows.length);

    // open without selection
    equal(0, list.selectedRowsCount());
    deepEqual([], list.selectedRows());

    $('.header-actions-trigger', widget.element).trigger('click');

    var popover = this.assertOpenedPopover();

    this.assertHeaderActionPopoverLinks([
        {action: 'merge-selection',  disabled: true,  title: ngettext('Select %d row', 'Select %d rows', 2).format(2)},
        {action: 'delete-selection', disabled: true,  title: ngettext('Select at least %d row', 'Select at least %d rows', 1).format(1)},
        {action: 'addto-selection',  disabled: false, title: ''}
    ], popover);
});

QUnit.test('creme.listview.header-actions (open menu, 1 selection)', function(assert) {
    var widget = this.createHeaderActionsListView();
    var list = widget.controller();
//    var rows = widget.element.find('table:first tr.selectable');
    var rows = widget.element.find('table').first().find('tr.selectable');

    equal(5, rows.length);

    $(rows[0]).trigger('click');

    // open without selection
    equal(1, list.selectedRowsCount());
    deepEqual(['1'], list.selectedRows());

    $('.header-actions-trigger', widget.element).trigger('click');

    var popover = this.assertOpenedPopover();

    this.assertHeaderActionPopoverLinks([
        {action: 'merge-selection',  disabled: true,  title: ngettext('Select %d row', 'Select %d rows', 2).format(2)},
        {action: 'delete-selection', disabled: false,  title: ''},
        {action: 'addto-selection',  disabled: false, title: ''}
    ], popover);
});

QUnit.test('creme.listview.header-actions (open menu, 2 selections)', function(assert) {
    var widget = this.createHeaderActionsListView();
    var list = widget.controller();
//    var rows = widget.element.find('table:first tr.selectable');
    var rows = widget.element.find('table').first().find('tr.selectable');

    equal(5, rows.length);

    $(rows[0]).trigger('click');
    $(rows[2]).trigger('click');

    // open without selection
    deepEqual(['1', '3'], list.selectedRows());

    $('.header-actions-trigger', widget.element).trigger('click');

    var popover = this.assertOpenedPopover();

    this.assertHeaderActionPopoverLinks([
        {action: 'merge-selection',  disabled: false,  title: ''},
        {action: 'delete-selection', disabled: false,  title: ''},
        {action: 'addto-selection',  disabled: false, title: ''}
    ], popover);
});

QUnit.test('creme.listview.header-actions (open menu, all selections)', function(assert) {
    var widget = this.createHeaderActionsListView();
    var list = widget.controller();
//    var rows = widget.element.find('table:first tr.selectable');
    var rows = widget.element.find('table').first().find('tr.selectable');

    equal(5, rows.length);

    rows.trigger('click');

    // open without selection
    equal(5, list.selectedRowsCount());

    $('.header-actions-trigger', widget.element).trigger('click');

    var popover = this.assertOpenedPopover();

    this.assertHeaderActionPopoverLinks([
        {action: 'merge-selection',  disabled: true,  title: ngettext('Select %d row', 'Select %d rows', 2).format(2)},
        {action: 'delete-selection', disabled: false,  title: ''},
        {action: 'addto-selection',  disabled: true, title: ngettext('Select no more than %d row', 'Select no more than %d rows', 3).format(3)}
    ], popover);
});

QUnit.test('creme.listview.header-actions (open menu, click)', function(assert) {
    var widget = this.createHeaderActionsListView();
    var list = widget.controller();
//    var rows = widget.element.find('table:first tr.selectable');
    var rows = widget.element.find('table').first().find('tr.selectable');

    $(rows[0]).trigger('click');
    $(rows[2]).trigger('click');

    equal(2, list.selectedRowsCount());

    $('.header-actions-trigger', widget.element).trigger('click');
    var popover = this.assertOpenedPopover();

    popover.find('.listview-action [data-action="merge-selection"]').trigger('click');
    this.assertClosedPopover();

    this.assertClosedDialog();
    deepEqual(['/mock/entity/merge?id1=1&id2=3'], this.mockRedirectCalls());

    $('.header-actions-trigger', widget.element).trigger('click');
    popover = this.assertOpenedPopover();

    popover.find('.listview-action [data-action="delete-selection"]').trigger('click');
    this.assertClosedPopover();

    this.assertOpenedConfirmDialog(gettext('Are you sure ?'));
    this.closeDialog();

    $('.header-actions-trigger', widget.element).trigger('click');
    popover = this.assertOpenedPopover();

    popover.find('.listview-action [data-action="addto-selection"]').trigger('click');
    this.assertClosedPopover();

    this.assertOpenedDialog();
    deepEqual([
        ['GET', {ids: ['1', '3']}]
    ], this.mockBackendUrlCalls('mock/entity/addto'));
    this.closeDialog();
});

}(jQuery));
