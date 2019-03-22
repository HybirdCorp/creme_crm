(function($) {

QUnit.module("creme.listview.actions", new QUnitMixin(QUnitEventMixin, QUnitAjaxMixin, QUnitDialogMixin, QUnitListViewMixin));

QUnit.test('creme.listview.DeleteSelectedAction (no selection)', function(assert) {
    var list = this.createListView();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete'
    }).on(this.listviewActionListeners);

    equal(0, list.countEntities());
    deepEqual([], list.getSelectedEntitiesAsArray());

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
    var list = this.createDefaultListView();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

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
    var list = this.createDefaultListView();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete/fail'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('1,2');

    equal(2, list.countEntities());
    deepEqual(['1', '2'], list.getSelectedEntitiesAsArray());

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
            selected_rows: ['1,2'],
            q_filter: ['{}'],
            ct_id: ['67'],
            selection: 'multiple'}]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.DeleteSelectedAction (not allowed)', function(assert) {
    var list = this.createDefaultListView();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete/nothing'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('1,2');

    equal(2, list.countEntities());
    deepEqual(['1', '2'], list.getSelectedEntitiesAsArray());

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
            selected_rows: ['1,2'],
            q_filter: ['{}'],
            ct_id: ['67'],
            selection: 'multiple'}]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.DeleteSelectedAction (partially allowed)', function(assert) {
    var list = this.createDefaultListView();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete/firstonly'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('1,2,3');

    equal(3, list.countEntities());
    deepEqual(['1', '2', '3'], list.getSelectedEntitiesAsArray());

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
            selected_rows: ['1,2,3'],
            q_filter: ['{}'],
            ct_id: ['67'],
            selection: 'multiple'}]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.DeleteSelectedAction (ok)', function(assert) {
    var list = this.createDefaultListView();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('1,2,3');

    equal(3, list.countEntities());
    deepEqual(['1', '2', '3'], list.getSelectedEntitiesAsArray());

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
            selected_rows: ['1,2,3'],
            q_filter: ['{}'],
            ct_id: ['67'],
            selection: 'multiple'}]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.AddToSelectedAction (no selection)', function(assert) {
    var list = this.createListView();
    var action = new creme.lv_widget.AddToSelectedAction(list, {
        url: 'mock/entity/addto'
    }).on(this.listviewActionListeners);

    equal(0, list.countEntities());
    deepEqual([], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Please select at least one entity."));
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/addto'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.AddToSelectedAction (cancel)', function(assert) {
    var list = this.createDefaultListView();
    var action = new creme.lv_widget.AddToSelectedAction(list, {
        url: 'mock/entity/addto'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

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
    var list = this.createDefaultListView();
    var action = new creme.lv_widget.AddToSelectedAction(list, {
        url: 'mock/entity/addto'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

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
    var list = this.createDefaultListView();
    var action = new creme.lv_widget.AddToSelectedAction(list, {
        url: 'mock/entity/addto'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

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
            selected_rows: ['2,3'],
            q_filter: ['{}'],
            ct_id: ['67'],
            selection: 'multiple'}]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.EditSelectedAction (no selection)', function(assert) {
    var list = this.createListView();
    var action = new creme.lv_widget.EditSelectedAction(list, {
        url: 'mock/entity/edit'
    }).on(this.listviewActionListeners);

    equal(0, list.countEntities());
    deepEqual([], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Please select at least one entity."));
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.EditSelectedAction (cancel)', function(assert) {
    var list = this.createDefaultListView();
    var action = new creme.lv_widget.EditSelectedAction(list, {
        url: 'mock/entity/edit'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([['GET', {}]], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([['GET', {}]], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.EditSelectedAction (submit => form error => close)', function(assert) {
    var list = this.createDefaultListView();
    var action = new creme.lv_widget.EditSelectedAction(list, {
        url: 'mock/entity/edit'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();
    deepEqual([['GET', {}]], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.assertOpenedDialog();

    equal(0, $('.ui-dialog .bulk-selection-summary').length);
    deepEqual([['GET', {}]], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.EditSelectedAction (submit => partially fail => close)', function(assert) {
    var list = this.createDefaultListView();
    var action = new creme.lv_widget.EditSelectedAction(list, {
        url: 'mock/entity/edit'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([['GET', {}]], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.submitFormDialog({
        edit: 'summary'
    });

    this.assertOpenedDialog();

    equal(1, $('.ui-dialog .bulk-selection-summary').length);
    deepEqual([
        ['GET', {}],
        ['POST', {
            entities: ['2', '3'],
            edit: ['summary']}]
    ], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['done']], this.mockListenerCalls('action-done'));
    deepEqual([
        ['POST', {
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            selected_rows: ['2,3'],
            q_filter: ['{}'],
            ct_id: ['67'],
            selection: 'multiple'}]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.EditSelectedAction (ok)', function(assert) {
    var list = this.createDefaultListView();
    var action = new creme.lv_widget.EditSelectedAction(list, {
        url: 'mock/entity/edit'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([['GET', {}]], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.submitFormDialog({
        edit: 'ok'
    });

    this.assertClosedDialog();

    deepEqual([
        ['GET', {}],
        ['POST', {
            entities: ['2', '3'],
            edit: ['ok']}]
    ], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([['done']], this.mockListenerCalls('action-done'));
    deepEqual([
        ['POST', {
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            selected_rows: ['2,3'],
            q_filter: ['{}'],
            ct_id: ['67'],
            selection: 'multiple'}]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.MergeSelectedAction (no selection)', function(assert) {
    var list = this.createListView();
    var action = new creme.lv_widget.MergeSelectedAction(list, {
        url: 'mock/entity/merge'
    }).on(this.listviewActionListeners);

    equal(0, list.countEntities());
    deepEqual([], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Please select 2 entities."));
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.listview.MergeSelectedAction (invalid selection)', function(assert) {
    var list = this.createListView();
    var action = new creme.lv_widget.MergeSelectedAction(list, {
        url: 'mock/entity/merge'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2');

    equal(1, list.countEntities());
    deepEqual(['2'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    // try with one selection
    action.start();

    this.assertOpenedAlertDialog(gettext("Please select 2 entities."));
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockRedirectCalls());

    this.resetMockListenerCalls();

    $(list).find('#selected_rows').val('1,2,3');

    equal(3, list.countEntities());
    deepEqual(['1', '2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    // retry with 3 selections
    action.start();

    this.assertOpenedAlertDialog(gettext("Please select 2 entities."));
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.listview.MergeSelectedAction (ok)', function(assert) {
    var list = this.createDefaultListView();
    var action = new creme.lv_widget.MergeSelectedAction(list, {
        url: 'mock/entity/merge'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertClosedDialog();

    deepEqual(['/mock/entity/merge?id1=2&id2=3'], this.mockRedirectCalls());
});

QUnit.test('creme.listview.actionregistry', function(assert) {
    var list = this.createListView();
    var registry = list.getActionBuilders();

    ok(Object.isSubClassOf(registry, creme.action.ActionBuilderRegistry));

    ok(registry.has('update'));
    ok(registry.has('delete'));
    ok(registry.has('clone'));
    ok(registry.has('form'));
    ok(registry.has('redirect'));

    ok(registry.has('edit-selection'));
    ok(registry.has('delete-selection'));
    ok(registry.has('addto-selection'));
    ok(registry.has('merge-selection'));
});

}(jQuery));
