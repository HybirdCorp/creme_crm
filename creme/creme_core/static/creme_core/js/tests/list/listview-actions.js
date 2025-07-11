(function($) {

QUnit.module("creme.listview.actions", new QUnitMixin(QUnitEventMixin,
                                                      QUnitAjaxMixin,
                                                      QUnitDialogMixin,
                                                      QUnitListViewMixin, {
    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendGET({
            'mock/entity/export': backend.response(200, '')
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

        this.assert.deepEqual(expected, popoverLinks.map(linkInfo).get());
    }
}));

QUnit.test('creme.listview.DeleteSelectedAction (no selection)', function(assert) {
    var list = this.createListView().controller();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete'
    }).on(this.listviewActionListeners);

    assert.equal(0, list.selectedRowsCount());
    assert.deepEqual([], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Please select at least one entity."));

    assert.deepEqual([], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.DeleteSelectedAction (not confirmed)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2,3');

    assert.equal(2, list.selectedRowsCount());
    assert.deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    assert.deepEqual([], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.DeleteSelectedAction (error)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete/fail'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('1,2');

    assert.equal(2, list.selectedRowsCount());
    assert.deepEqual(['1', '2'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    assert.deepEqual([], this.mockListenerCalls('action-fail'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.acceptConfirmDialog();

    this.assertOpenedAlertDialog(undefined, gettext('Bad Request'));

    assert.deepEqual([], this.mockListenerCalls('action-fail'));
    assert.deepEqual([
        ['POST', {ids: '1,2'}]
    ], this.mockBackendUrlCalls('mock/entity/delete/fail'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    assert.deepEqual([['fail']], this.mockListenerCalls('action-fail'));
    assert.deepEqual([
        ['POST', {ids: '1,2'}]
    ], this.mockBackendUrlCalls('mock/entity/delete/fail'));
    assert.deepEqual([
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

    assert.equal(2, list.selectedRowsCount());
    assert.deepEqual(['1', '2'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    assert.deepEqual([], this.mockListenerCalls('action-fail'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/entity/delete/nothing'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.acceptConfirmDialog();

    var header = ngettext(' %d entity cannot be deleted.', ' %d entities cannot be deleted.', 2).format(2);
    this.assertOpenedAlertDialog(undefined, header);

    assert.deepEqual([], this.mockListenerCalls('action-fail'));
    assert.deepEqual([
        ['POST', {ids: '1,2'}]
    ], this.mockBackendUrlCalls('mock/entity/delete/nothing'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    assert.deepEqual([['fail']], this.mockListenerCalls('action-fail'));
    assert.deepEqual([
        ['POST', {ids: '1,2'}]
    ], this.mockBackendUrlCalls('mock/entity/delete/nothing'));
    assert.deepEqual([
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

    assert.equal(3, list.selectedRowsCount());
    assert.deepEqual(['1', '2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();
    this.acceptConfirmDialog();

    var header = ngettext('%d entity has been deleted.', '%d entities have been deleted.', 1).format(1) +
                 ngettext(' %d entity cannot be deleted.', ' %d entities cannot be deleted.', 2).format(2);

    assert.deepEqual([], this.mockListenerCalls('action-fail'));
    assert.deepEqual([
        ['POST', {ids: '1,2,3'}]
    ], this.mockBackendUrlCalls('mock/entity/delete/firstonly'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.assertOpenedAlertDialog(undefined, header);
    this.closeDialog();

    assert.deepEqual([['fail']], this.mockListenerCalls('action-fail'));
    assert.deepEqual([
        ['POST', {ids: '1,2,3'}]
    ], this.mockBackendUrlCalls('mock/entity/delete/firstonly'));
    assert.deepEqual([
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

    assert.equal(3, list.selectedRowsCount());
    assert.deepEqual(['1', '2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();
    this.acceptConfirmDialog();

    assert.deepEqual([
        ['POST', {ids: '1,2,3'}]
    ], this.mockBackendUrlCalls('mock/entity/delete'));
    assert.deepEqual([['done']], this.mockListenerCalls('action-done'));
    assert.deepEqual([
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

    assert.equal(0, list.selectedRowsCount());
    assert.deepEqual([], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Please select at least one entity."));
    this.closeDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/entity/addto'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.AddToSelectedAction (cancel)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.AddToSelectedAction(list, {
        url: 'mock/entity/addto'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2,3');

    assert.equal(2, list.selectedRowsCount());
    assert.deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    assert.deepEqual([], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([
        ['GET', {ids: ['2', '3']}]
    ], this.mockBackendUrlCalls('mock/entity/addto'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([
        ['GET', {ids: ['2', '3']}]
    ], this.mockBackendUrlCalls('mock/entity/addto'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.AddToSelectedAction (submit fail + cancel)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.AddToSelectedAction(list, {
        url: 'mock/entity/addto'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2,3');

    assert.equal(2, list.selectedRowsCount());
    assert.deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();
    assert.deepEqual([
        ['GET', {ids: ['2', '3']}]
    ], this.mockBackendUrlCalls('mock/entity/addto'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.assertOpenedDialog();
    assert.deepEqual([
        ['GET', {ids: ['2', '3']}]
    ], this.mockBackendUrlCalls('mock/entity/addto'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.AddToSelectedAction (ok)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.AddToSelectedAction(list, {
        url: 'mock/entity/addto'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2,3');

    assert.equal(2, list.selectedRowsCount());
    assert.deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    assert.deepEqual([
        ['GET', {ids: ['2', '3']}]
    ], this.mockBackendUrlCalls('mock/entity/addto'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.submitFormDialog({
        addto: 'ok'
    });

    this.assertClosedDialog();

    assert.deepEqual([
        ['GET', {ids: ['2', '3']}],
        ['POST', {addto: ["ok"], ids: ['2', '3']}]
    ], this.mockBackendUrlCalls('mock/entity/addto'));
    assert.deepEqual([['done']], this.mockListenerCalls('action-done'));
    assert.deepEqual([
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

    assert.equal(0, list.selectedRowsCount());
    assert.deepEqual([], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Please select at least one entity."));
    this.closeDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/entity/edit'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.EditSelectedAction (cancel)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.EditSelectedAction(list, {
        url: 'mock/entity/edit'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2,3');

    assert.equal(2, list.selectedRowsCount());
    assert.deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    assert.equal($('.ui-dialog .help-sign').length, 1);
    assert.equal($('.ui-dialog .help-sign').text(), '2 entities are selected');

    assert.deepEqual([], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([['GET', {entities: '2.3'}]], this.mockBackendUrlCalls('mock/entity/edit'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([['GET', {entities: '2.3'}]], this.mockBackendUrlCalls('mock/entity/edit'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.EditSelectedAction (submit => partially fail => close)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.EditSelectedAction(list, {
        url: 'mock/entity/edit'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2,3');

    assert.equal(2, list.selectedRowsCount());
    assert.deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    assert.equal($('.ui-dialog .help-sign').text(), '2 entities are selected');
    assert.deepEqual([['GET', {entities: '2.3'}]], this.mockBackendUrlCalls('mock/entity/edit'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.submitFormDialog({
        field_value: ''
    });

    this.assertOpenedDialog();

    assert.equal($('.ui-dialog .help-sign').text(), '2 entities are selected');
    assert.deepEqual([
        ['GET', {
            entities: '2.3'
        }],
        ['POST', {
            entities: ['2', '3'],
            _bulk_fieldname: ['mock/entity/edit/field-a'],
            field_value: ['']
        }]
    ], this.mockBackendUrlCalls('mock/entity/edit'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.EditSelectedAction (ok)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.EditSelectedAction(list, {
        url: 'mock/entity/edit'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2,3');

    assert.equal(2, list.selectedRowsCount());
    assert.deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    assert.equal($('.ui-dialog .help-sign').text(), '2 entities are selected');
    assert.deepEqual([['GET', {entities: '2.3'}]], this.mockBackendUrlCalls('mock/entity/edit'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.submitFormDialog({
        field_value: 'ok'
    });

    // The dialog is still open to show the summary
    this.assertOpenedDialog();
    assert.equal($('.ui-dialog .ui-creme-dialog-frame').text(), '2 entitie(s) have been updated !');
    assert.deepEqual([], this.mockListenerCalls('action-done'));

    this.closeDialog();

    assert.deepEqual([['done']], this.mockListenerCalls('action-done'));

    assert.deepEqual([
        ['mock/entity/edit', 'GET', {
            entities: '2.3'
        }],
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

    assert.equal(2, list.selectedRowsCount());
    assert.deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    var dialog = this.assertOpenedDialog();

    assert.deepEqual([['GET', {entities: '2.3'}]], this.mockBackendUrlCalls('mock/entity/edit'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    assert.equal(dialog.find('[name="_bulk_fieldname"]').length, 1);
    dialog.find('[name="_bulk_fieldname"]').val('mock/entity/edit/field-b').trigger('change');

    this.assertOpenedDialog();

    assert.deepEqual([
        ['mock/entity/edit', 'GET', {
            entities: '2.3'
        }],
        ['mock/entity/edit/field-b', 'GET', {
            entities: '2.3'
        }]
    ], this.mockBackendUrlCalls());

    this.submitFormDialog({
        field_value: 'ok'
    });

    // The dialog is still open to show the summary
    this.assertOpenedDialog();
    assert.equal($('.ui-dialog .ui-creme-dialog-frame').text(), '2 entitie(s) have been updated !');
    assert.deepEqual([], this.mockListenerCalls('action-done'));

    this.closeDialog();

    assert.deepEqual([['done']], this.mockListenerCalls('action-done'));
    assert.deepEqual([
        ['mock/entity/edit', 'GET', {
            entities: '2.3'
        }],
        ['mock/entity/edit/field-b', 'GET', {
            entities: '2.3'
        }],
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

    assert.equal(0, list.selectedRowsCount());
    assert.deepEqual([], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Please select 2 entities."));
    this.closeDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.listview.MergeSelectedAction (invalid selection)', function(assert) {
    var list = this.createListView().controller();
    var action = new creme.lv_widget.MergeSelectedAction(list, {
        url: '/mock/entity/merge'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2');

    assert.equal(1, list.selectedRowsCount());
    assert.deepEqual(['2'], list.selectedRows());

    this.assertClosedDialog();

    // try with one selection
    action.start();

    this.assertOpenedAlertDialog(gettext("Please select 2 entities."));
    this.closeDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockRedirectCalls());

    this.resetMockListenerCalls();

    list.element().find('#selected_rows').val('1,2,3');

    assert.equal(3, list.selectedRowsCount());
    assert.deepEqual(['1', '2', '3'], list.selectedRows());

    this.assertClosedDialog();

    // retry with 3 selections
    action.start();

    this.assertOpenedAlertDialog(gettext("Please select 2 entities."));
    this.closeDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.listview.MergeSelectedAction (ok)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.lv_widget.MergeSelectedAction(list, {
        url: '/mock/entity/merge'
    }).on(this.listviewActionListeners);

    list.element().find('#selected_rows').val('2,3');

    assert.equal(2, list.selectedRowsCount());
    assert.deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertClosedDialog();

    assert.deepEqual(['/mock/entity/merge?id1=2&id2=3'], this.mockRedirectCalls());
});

QUnit.test('creme.listview.ExportAction (no formats)', function(assert) {
    var list = this.createDefaultListView().controller();

    var action = new creme.lv_widget.ExportAction(list, {
        url: '/mock/entity/merge'
    }).on(this.listviewActionListeners);

    action.start();

    var dialog = this.assertOpenedDialog();

    assert.deepEqual([
        {value: '', name: 'No backend found'}
    ], dialog.find('select option').map(function() {
        return {name: $(this).text(), value: $(this).attr('value')};
    }).get());

    this.closeDialog();

    assert.deepEqual([], this.mockListenerCalls('action-fail'));
    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockListenerCalls('action-done'));

    assert.deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.listview.ExportAction (cancel)', function(assert) {
    var list = this.createDefaultListView().controller();

    var action = new creme.lv_widget.ExportAction(list, {
        url: '/mock/entity/export',
        formats: [
             ['csv', 'CSV File format']
        ]
    }).on(this.listviewActionListeners);

    action.start();

    var dialog = this.assertOpenedDialog();

    assert.deepEqual([
        {value: 'csv', name: 'CSV File format'}
    ], dialog.find('select option').map(function() {
        return {name: $(this).text(), value: $(this).attr('value')};
    }).get());

    dialog.find('button[name="cancel"]').trigger('click');

    this.assertClosedDialog();

    assert.deepEqual([], this.mockListenerCalls('action-fail'));
    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockListenerCalls('action-done'));

    assert.deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.listview.ExportAction (ok)', function(assert) {
    var list = this.createDefaultListView().controller();

    var action = new creme.lv_widget.ExportAction(list, {
        url: '/mock/entity/export',
        formats: [
             ['csv', 'CSV File format']
        ]
    }).on(this.listviewActionListeners);

    action.start();

    var dialog = this.assertOpenedDialog();

    assert.deepEqual([
        {value: 'csv', name: 'CSV File format'}
    ], dialog.find('select option').map(function() {
        return {name: $(this).text(), value: $(this).attr('value')};
    }).get());

    dialog.find('button[name="ok"]').trigger('click');

    this.assertClosedDialog();

    assert.deepEqual([], this.mockListenerCalls('action-fail'));
    assert.deepEqual([], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([['done']], this.mockListenerCalls('action-done'));

    assert.deepEqual(['/mock/entity/export?type=csv'], this.mockRedirectCalls());
});

QUnit.test('creme.listview.actionregistry', function(assert) {
    var list = this.createListView().controller();
    var registry = list.actionBuilders();

    assert.ok(Object.isSubClassOf(registry, creme.component.FactoryRegistry));

    assert.ok(registry.has('update'));
    assert.ok(registry.has('delete'));
    assert.ok(registry.has('clone'));
    assert.ok(registry.has('form'));
    assert.ok(registry.has('redirect'));
    assert.ok(registry.has('popover'));

    assert.ok(registry.has('submit-lv-state'));
    assert.ok(registry.has('reset-lv-search'));
    assert.ok(registry.has('edit-selection'));
    assert.ok(registry.has('delete-selection'));
    assert.ok(registry.has('addto-selection'));
    assert.ok(registry.has('merge-selection'));
    assert.ok(registry.has('export-as'));
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

    assert.deepEqual([
        ['POST', {a: 12}]
    ], this.mockBackendUrlCalls('mock/entity/update'));

    assert.deepEqual([
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

    this.assertOpenedConfirmDialog(gettext('Are you sure?'));
    this.closeDialog();

    assert.deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
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

    this.assertOpenedConfirmDialog(gettext('Are you sure?'));
    this.acceptConfirmDialog();

    assert.deepEqual([
        ['POST', {id: 12}]
    ], this.mockBackendUrlCalls('mock/entity/delete'));

    assert.deepEqual([
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

    assert.deepEqual([], this.mockBackendUrlCalls('mock/entity/clone'));
    assert.deepEqual([], this.mockRedirectCalls());
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

    assert.deepEqual([
        ['POST', {id: 12}]
    ], this.mockBackendUrlCalls('mock/entity/clone'));
    assert.deepEqual(['mock/entity/clone/redirection'], this.mockRedirectCalls());
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

    assert.deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/entity/edit'));

    var dialog = this.assertOpenedDialog();
    dialog.find('[name="field_value"]').val('12');

    this.submitFormDialog();

    assert.deepEqual([
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

    assert.deepEqual([
        (_.toRelativeURL(window.location.href).fullPath() + '?redirect#hatbar')
    ], this.mockRedirectCalls());
});

QUnit.test('creme.listview.header-actions (no selection)', function(assert) {
    var widget = this.createHeaderActionsListView();
    var list = widget.controller();
    var rows = widget.element.find('table').first().find('tr.selectable');

    assert.equal(5, rows.length);

    // open without selection
    assert.equal(0, list.selectedRowsCount());
    assert.deepEqual([], list.selectedRows());

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
    var rows = widget.element.find('table').first().find('tr.selectable');

    assert.equal(5, rows.length);

    $(rows[0]).trigger('click');

    // open without selection
    assert.equal(1, list.selectedRowsCount());
    assert.deepEqual(['1'], list.selectedRows());

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
    var rows = widget.element.find('table').first().find('tr.selectable');

    assert.equal(5, rows.length);

    $(rows[0]).trigger('click');
    $(rows[2]).trigger('click');

    // open without selection
    assert.deepEqual(['1', '3'], list.selectedRows());

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
    var rows = widget.element.find('table').first().find('tr.selectable');

    assert.equal(5, rows.length);

    rows.trigger('click');

    // open without selection
    assert.equal(5, list.selectedRowsCount());

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
    var rows = widget.element.find('table').first().find('tr.selectable');

    $(rows[0]).trigger('click');
    $(rows[2]).trigger('click');

    assert.equal(2, list.selectedRowsCount());

    $('.header-actions-trigger', widget.element).trigger('click');
    var popover = this.assertOpenedPopover();

    popover.find('.listview-action [data-action="merge-selection"]').trigger('click');
    this.assertClosedPopover();

    this.assertClosedDialog();
    assert.deepEqual(['/mock/entity/merge?id1=1&id2=3'], this.mockRedirectCalls());

    $('.header-actions-trigger', widget.element).trigger('click');
    popover = this.assertOpenedPopover();

    popover.find('.listview-action [data-action="delete-selection"]').trigger('click');
    this.assertClosedPopover();

    this.assertOpenedConfirmDialog(gettext('Are you sure?'));
    this.closeDialog();

    $('.header-actions-trigger', widget.element).trigger('click');
    popover = this.assertOpenedPopover();

    popover.find('.listview-action [data-action="addto-selection"]').trigger('click');
    this.assertClosedPopover();

    this.assertOpenedDialog();
    assert.deepEqual([
        ['GET', {ids: ['1', '3']}]
    ], this.mockBackendUrlCalls('mock/entity/addto'));
    this.closeDialog();
});

}(jQuery));
