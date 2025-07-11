(function($) {

QUnit.module("creme.activities.listview.actions", new QUnitMixin(QUnitEventMixin,
                                                                 QUnitAjaxMixin,
                                                                 QUnitListViewMixin,
                                                                 QUnitDialogMixin, {
}));

QUnit.test('creme.activities.ExportAsICalAction (no selection)', function(assert) {
    var list = this.createListView().controller();
    var action = new creme.activities.ExportAsICalAction(list, {
        url: 'mock/activities/export/ical'
    }).on(this.listviewActionListeners);

    assert.equal(0, list.selectedRowsCount());
    assert.deepEqual([], list.selectedRows());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Please select at least a line in order to export."));
    this.closeDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.activities.ExportAsICalAction (ok)', function(assert) {
    var list = this.createDefaultListView().controller();
    var action = new creme.activities.ExportAsICalAction(list, {
        url: '/mock/activities/export/ical'
    }).on(this.listviewActionListeners);

    this.setListviewSelection(list, ['1', '2', '3']);

    assert.equal(3, list.selectedRowsCount());
    assert.deepEqual(['1', '2', '3'], list.selectedRows());

    action.start();

    assert.deepEqual([['done']], this.mockListenerCalls('action-done'));
    assert.deepEqual(['/mock/activities/export/ical?id=1&id=2&id=3'], this.mockRedirectCalls());
});

}(jQuery));
