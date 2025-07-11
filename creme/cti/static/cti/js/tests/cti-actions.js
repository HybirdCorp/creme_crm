(function($) {

QUnit.module("creme.cti.actions", new QUnitMixin(QUnitEventMixin,
                                                 QUnitAjaxMixin,
                                                 QUnitDialogMixin, {
    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendGET({
            'mock/cti/call/fail': backend.response(400, ''),
            'mock/cti/call': backend.response(200, '')
        });

        this.setMockBackendPOST({
            'mock/call/save/fail': backend.response(400, ''),
            'mock/call/save': backend.response(200, 'Call saved')
        });

        this.ctiActionListener = {
            'fail': this.mockListener('action-fail'),
            'cancel': this.mockListener('action-cancel'),
            'done': this.mockListener('action-done')
        };
    }
}));

QUnit.test('creme.cti.PhoneCallAction (call failed)', function(assert) {
    var action = new creme.cti.PhoneCallAction({
        ctiServerUrl: 'mock/cti/call/fail',
        saveCallUrl: 'mock/call/save',
        number: '007',
        callerId: 12
    }).on(this.ctiActionListener);

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Unable to start the phone call. Please check your CTI configuration."));
    this.closeDialog();

    assert.deepEqual([['fail']], this.mockListenerCalls('action-fail'));
    assert.deepEqual([
        ['GET', {n_tel: '007'}]
    ], this.mockBackendUrlCalls('mock/cti/call/fail'));
});

QUnit.test('creme.cti.PhoneCallAction (save failed)', function(assert) {
    var action = new creme.cti.PhoneCallAction({
        ctiServerUrl: 'mock/cti/call',
        saveCallUrl: 'mock/call/save/fail',
        number: '007',
        callerId: 12
    }).on(this.ctiActionListener);

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Failed to save the phone call."));
    this.closeDialog();

    assert.deepEqual([['fail']], this.mockListenerCalls('action-fail'));
    assert.deepEqual([
        ['GET', {n_tel: '007'}]
    ], this.mockBackendUrlCalls('mock/cti/call'));
    assert.deepEqual([
        ['POST', {entity_id: 12}]
    ], this.mockBackendUrlCalls('mock/call/save/fail'));
});

QUnit.test('creme.cti.PhoneCallAction (ok)', function(assert) {
    var action = new creme.cti.PhoneCallAction({
        ctiServerUrl: 'mock/cti/call',
        saveCallUrl: 'mock/call/save',
        number: '007',
        callerId: 12
    }).on(this.ctiActionListener);

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog(gettext("Call saved"));
    this.closeDialog();

    assert.deepEqual([['done']], this.mockListenerCalls('action-done'));
    assert.deepEqual([
        ['GET', {n_tel: '007'}]
    ], this.mockBackendUrlCalls('mock/cti/call'));
    assert.deepEqual([
        ['POST', {entity_id: 12}]
    ], this.mockBackendUrlCalls('mock/call/save'));
});

QUnit.test('creme.cti.phoneCall', function(assert) {
    var action = creme.cti.phoneCall('mock/cti/call', 'mock/call/save', '007', 12);

    this.assertOpenedDialog(gettext("Call saved"));
    this.closeDialog();

    assert.ok(action.isStatusDone());

    assert.deepEqual([
        ['GET', {n_tel: '007'}]
    ], this.mockBackendUrlCalls('mock/cti/call'));
    assert.deepEqual([
        ['POST', {entity_id: 12}]
    ], this.mockBackendUrlCalls('mock/call/save'));
});

}(jQuery));
