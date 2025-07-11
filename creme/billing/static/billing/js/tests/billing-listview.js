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

QUnit.test('creme.billing.listview.actions (billing-number, ok)', function(assert) {
    var list = this.createDefaultListView().controller();
    var registry = list.actionBuilders();

    var builder = registry.get('billing-number');

    assert.ok(Object.isFunc(builder));
    var action = builder('mock/invoice/12/number', {
        confirm: 'Are you sure?'
    });

    action.start();

    this.assertOpenedConfirmDialog('Are you sure?');
    this.acceptConfirmDialog();

    this.assertClosedDialog();

    assert.deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/invoice/12/number'));
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


QUnit.test('creme.billing.listview.actions (billing-number, fail)', function(assert) {
    var list = this.createDefaultListView().controller();
    var registry = list.actionBuilders();

    var builder = registry.get('billing-number');

    assert.ok(Object.isFunc(builder));
    var action = builder('mock/invoice/12/number/fail', {
        confirm: 'Are you sure?'
    });

    action.start();

    this.assertOpenedConfirmDialog('Are you sure?');
    this.acceptConfirmDialog();

    this.assertOpenedAlertDialog('Unable to generate invoice number');
    this.closeDialog();

    assert.deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/invoice/12/number/fail'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

}(jQuery));
