(function($) {

QUnit.module("creme.billing.listview.actions", new QUnitMixin(QUnitEventMixin,
                                                              QUnitAjaxMixin,
                                                              QUnitListViewMixin,
                                                              QUnitDialogMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        this.setMockBackendPOST({
            'mock/invoice/12/number': backend.response(200, ''),
            'mock/invoice/12/number/fail': backend.response(400, 'Unable to generate invoice number')
        });
    }
}));

QUnit.test('creme.billing.ExportDocumentAction (no format)', function(assert) {
    var action = new creme.billing.ExportDocumentAction({
        url: 'mock/export/12'
    }).on(this.listviewActionListeners);

    action.start();

    this.assertOpenedAlertDialog(gettext("No such export format for billing documents."));
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.billing.ExportDocumentAction (single format)', function(assert) {
    var action = new creme.billing.ExportDocumentAction({
        url: 'mock/export/12',
        formats: [{value: 'pdf'}]
    }).on(this.listviewActionListeners);

    action.start();

    this.assertClosedDialog();

    deepEqual([['done']], this.mockListenerCalls('action-done'));
    deepEqual(['/mock/export/12?format=pdf'], this.mockRedirectCalls());
});

QUnit.test('creme.billing.ExportDocumentAction (multiple formats, cancel choice)', function(assert) {
    var action = new creme.billing.ExportDocumentAction({
        url: 'mock/export/12',
        formats: [{value: 'pdf'}, {value: 'html'}, {value: 'xml'}]
    }).on(this.listviewActionListeners);

    action.start();

    this.assertOpenedDialog();

    equal('pdf', $('.ui-dialog select').val());
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.billing.ExportDocumentAction (multiple formats, choose one)', function(assert) {
    var action = new creme.billing.ExportDocumentAction({
        url: 'mock/export/12',
        formats: [{value: 'pdf'}, {value: 'html'}, {value: 'xml'}]
    }).on(this.listviewActionListeners);

    action.start();

    this.assertOpenedDialog();

    $('.ui-dialog select').val('html');
    this.acceptConfirmDialog();

    deepEqual([['done']], this.mockListenerCalls('action-done'));
    deepEqual(['/mock/export/12?format=html'], this.mockRedirectCalls());
});

QUnit.test('creme.billing.listview.actions (billing-invoice-number, ok)', function(assert) {
    var list = this.createDefaultListView();
    var registry = list.getActionBuilders();

    var builder = registry.get('billing-invoice-number');

    ok(Object.isFunc(builder));
    var action = builder('mock/invoice/12/number', {
        confirm: 'Are you sure ?'
    });

    action.start();

    this.assertOpenedConfirmDialog('Are you sure ?');
    this.acceptConfirmDialog();

    this.assertClosedDialog();

    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/invoice/12/number'));
    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            selected_rows: [''],
            selection: 'multiple',
            sort_key: ['regular_field-name'],
            sort_order: ['ASC']
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});


QUnit.test('creme.billing.listview.actions (billing-invoice-number, fail)', function(assert) {
    var list = this.createDefaultListView();
    var registry = list.getActionBuilders();

    var builder = registry.get('billing-invoice-number');

    ok(Object.isFunc(builder));
    var action = builder('mock/invoice/12/number/fail', {
        confirm: 'Are you sure ?'
    });

    action.start();

    this.assertOpenedConfirmDialog('Are you sure ?');
    this.acceptConfirmDialog();

    this.assertOpenedAlertDialog('Unable to generate invoice number');
    this.closeDialog();

    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/invoice/12/number/fail'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

}(jQuery));
