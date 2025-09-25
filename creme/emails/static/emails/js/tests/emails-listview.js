(function($) {

QUnit.module("creme.emails.listview.actions", new QUnitMixin(QUnitEventMixin,
                                                             QUnitAjaxMixin,
                                                             QUnitListViewMixin,
                                                             QUnitDialogMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        this.setMockBackendPOST({
            'mock/emails/resend': backend.response(200, ''),
            'mock/emails/resend/fail': backend.response(400, 'invalid response !')
        });
    }
}));

QUnit.test('creme.emails.ResendEMailsAction (no selection)', function(assert) {
    var list = this.createListView().controller();
    var action = new creme.emails.ResendEMailsAction(list, {
        url: 'mock/emails/resend'
    }).on(this.listviewActionListeners);

    assert.equal(0, list.selectedRowsCount());
    assert.deepEqual([], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Please select at least one email."));
    this.closeDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.emails.ResendEMailsAction (not confirmed)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.emails.ResendEMailsAction(list, {
        url: 'mock/emails/resend'
    }).on(this.listviewActionListeners);

    this.setListviewSelection(list, ['2', '3']);

    assert.equal(2, list.selectedRowsCount());
    assert.deepEqual(['2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    assert.deepEqual([], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/emails/resend'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.emails.ResendEMailsAction (error)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.emails.ResendEMailsAction(list, {
        url: 'mock/emails/resend/fail'
    }).on(this.listviewActionListeners);

    this.setListviewSelection(list, ['1', '2']);

    assert.equal(2, list.selectedRowsCount());
    assert.deepEqual(['1', '2'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    assert.deepEqual([], this.mockListenerCalls('action-fail'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/emails/resend'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.acceptConfirmDialog();

    this.assertOpenedAlertDialog(undefined, gettext('Bad Request'));

    assert.deepEqual([], this.mockListenerCalls('action-fail'));
    assert.deepEqual([
        ['POST', {ids: '1,2'}]
    ], this.mockBackendUrlCalls('mock/emails/resend/fail'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    assert.deepEqual([['fail']], this.mockListenerCalls('action-fail'));
    assert.deepEqual([
        ['POST', {ids: '1,2'}]
    ], this.mockBackendUrlCalls('mock/emails/resend/fail'));
    assert.deepEqual([
        ['POST', {
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            content: 1,
            rows: ['10'],
            selected_rows: ['1,2'],
            q_filter: ['{}'],
            ct_id: ['67'],
            selection: ['multiple']}]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.emails.ResendEMailsAction (ok)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.emails.ResendEMailsAction(list, {
        url: 'mock/emails/resend'
    }).on(this.listviewActionListeners);

    this.setListviewSelection(list, ['1', '2', '3']);

    assert.equal(3, list.selectedRowsCount());
    assert.deepEqual(['1', '2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();
    this.acceptConfirmDialog();

    assert.deepEqual([
        ['POST', {ids: '1,2,3'}]
    ], this.mockBackendUrlCalls('mock/emails/resend'));
    assert.deepEqual([['done']], this.mockListenerCalls('action-done'));
    assert.deepEqual([
        ['POST', {
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            content: 1,
            rows: ['10'],
            selected_rows: ['1,2,3'],
            q_filter: ['{}'],
            ct_id: ['67'],
            selection: ['multiple']}]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.emails.listview.actions (email-resend)', function(assert) {
    var list = this.createDefaultListView().controller();
    var registry = list.actionBuilders();

    var builder = registry.get('email-resend');

    assert.ok(Object.isFunc(builder));
    var action = builder('mock/emails/resend', {
        selection: ['3']
    }).on(this.listviewActionListeners);

    this.setListviewSelection(list, ['1', '2']);

    assert.equal(2, list.selectedRowsCount());
    assert.deepEqual(['1', '2'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();
    this.acceptConfirmDialog();

    assert.deepEqual([
        ['POST', {ids: '1,2,3'}]
    ], this.mockBackendUrlCalls('mock/emails/resend'));
    assert.deepEqual([['done']], this.mockListenerCalls('action-done'));
    assert.deepEqual([
        ['POST', {
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            content: 1,
            rows: ['10'],
            selected_rows: ['1,2'],
            q_filter: ['{}'],
            ct_id: ['67'],
            selection: ['multiple']}]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.emails.listview.actions (email-resend-selection)', function(assert) {
    var list = this.createDefaultListView().controller();
    var registry = list.actionBuilders();

    var builder = registry.get('email-resend-selection');

    assert.ok(Object.isFunc(builder));
    var action = builder(
        'mock/emails/resend'
    ).on(this.listviewActionListeners);

    this.setListviewSelection(list, ['1', '2', '3']);

    assert.equal(3, list.selectedRowsCount());
    assert.deepEqual(['1', '2', '3'], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();
    this.acceptConfirmDialog();

    assert.deepEqual([
        ['POST', {ids: '1,2,3'}]
    ], this.mockBackendUrlCalls('mock/emails/resend'));
    assert.deepEqual([['done']], this.mockListenerCalls('action-done'));
    assert.deepEqual([
        ['POST', {
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            content: 1,
            rows: ['10'],
            selected_rows: ['1,2,3'],
            q_filter: ['{}'],
            ct_id: ['67'],
            selection: ['multiple']}]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

}(jQuery));
