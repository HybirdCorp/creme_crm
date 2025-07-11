(function($) {

QUnit.module("creme.events.listview", new QUnitMixin(QUnitEventMixin,
                                                     QUnitAjaxMixin,
                                                     QUnitListViewMixin,
                                                     QUnitDialogMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        this.setMockBackendPOST({
            'mock/events/12/status': backend.response(200, ''),
            'mock/events/12/status/fail': backend.response(400, 'invalid response !')
        });
    }
}));

QUnit.test('creme.events.saveContactStatus', function(assert) {
    var element = $(
       '<select>' +
            '<option value="1" selected>A</option>' +
            '<option value="2">B</option>' +
            '<option value="3">C</option>' +
       '</select>');

    assert.deepEqual([], this.mockBackendUrlCalls('mock/events/12/status'));

    assert.equal('1', element.val());
    creme.events.saveContactStatus('mock/events/12/status', element);

    assert.deepEqual([['POST', {status: '1'}]], this.mockBackendUrlCalls('mock/events/12/status'));

    element.val('3');
    creme.events.saveContactStatus('mock/events/12/status', element);

    assert.deepEqual([
        ['POST', {status: '1'}],
        ['POST', {status: '3'}]
    ], this.mockBackendUrlCalls('mock/events/12/status'));
});

}(jQuery));
