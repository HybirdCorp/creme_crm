QUnit.module("creme.billing.listview.actions", new QUnitMixin(QUnitEventMixin,
                                                              QUnitAjaxMixin,
                                                              QUnitListViewMixin,
                                                              QUnitDialogMixin));

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
    deepEqual(['mock/export/12?format=pdf'], this.mockRedirectCalls());
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
    deepEqual(['mock/export/12?format=html'], this.mockRedirectCalls());
});
