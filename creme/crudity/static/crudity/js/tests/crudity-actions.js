(function($) {

QUnit.module("creme.crudity.brick.actions", new QUnitMixin(QUnitEventMixin,
                                                           QUnitAjaxMixin,
                                                           QUnitBrickMixin,
                                                           QUnitDialogMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        this.setMockBackendPOST({
            'mock/crudity/validate': backend.response(200, ''),
            'mock/crudity/validate/fail': backend.response(400, ''),
            'mock/crudity/delete': backend.response(200, ''),
            'mock/crudity/delete/fail': backend.response(400, ''),
            'mock/crudity/waiting/sync': backend.responseJSON(200, ['a', 'b']),
            'mock/crudity/waiting/sync/fail': backend.response(400, 'Unable to sync actions')
        });
    },

    createCrudityBrickTable: function(options) {
        options = $.extend({
            classes: ['crudity-actions-brick'],
            columns: [
                '<th data-table-primary-column>Id</th>',
                '<th data-type="date">Created on</th>',
                '<th>Name</th>'
            ],
            rows: [
                '<tr><td data-selectable-selector-column><input value="1" type="check"></input></td><td data-type="date">2017-05-08</td><td>A</td></tr>',
                '<tr><td data-selectable-selector-column><input value="2" type="check"></input></td><td data-type="date">2017-05-07</td><td>B</td></tr>',
                '<tr><td data-selectable-selector-column><input value="3" type="check"></input></td><td data-type="date">2017-05-06</td><td>C</td></tr>'
            ]
        }, options || {});

        return this.createBrickTable(options);
    }
}));

QUnit.test('creme.crudity.brick.crudity-validate (empty selector)', function(assert) {
    var brick = this.createCrudityBrickTable().brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    brick.action('crudity-validate', 'mock/crudity/validate').start();

    equal(false, brick.isLoading());

    this.assertOpenedAlertDialog(gettext('Nothing is selected.'));
    this.closeDialog();

    deepEqual([], this.mockBackendCalls());
});

QUnit.test('creme.emails.brick.crudity-validate (fail)', function(assert) {
    var brick = this.createCrudityBrickTable().brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    this.toggleBrickTableRows(brick, [0, 1]);
    equal(2, selections.selected().length);

    brick.action('crudity-validate', 'mock/crudity/validate/fail').start();

    deepEqual([
        ['POST', {ids: ['1', '2']}]
    ], this.mockBackendUrlCalls('mock/crudity/validate/fail'));

    this.assertOpenedDialog(gettext('Bad Request'));
    this.closeDialog();

    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.brick.crudity-validate', function(assert) {
    var brick = this.createCrudityBrickTable().brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    this.toggleBrickTableRows(brick, [0, 1]);
    equal(2, selections.selected().length);

    brick.action('crudity-validate', 'mock/crudity/validate').start();

    deepEqual([
        ['POST', {ids: ['1', '2']}]
    ], this.mockBackendUrlCalls('mock/crudity/validate'));

    this.assertOpenedDialog(gettext('Process done'));
    this.closeDialog();

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.brick.crudity-validate-row', function(assert) {
    var brick = this.createCrudityBrickTable().brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    brick.action('crudity-validate-row', 'mock/crudity/validate', {}, {
        id: '157'
    }).start();

    deepEqual([
        ['POST', {ids: ['157']}]
    ], this.mockBackendUrlCalls('mock/crudity/validate'));


    this.assertOpenedDialog(gettext('Process done'));
    this.closeDialog();

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.brick.crudity-validate-row (fail)', function(assert) {
    var brick = this.createCrudityBrickTable().brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    brick.action('crudity-validate-row', 'mock/crudity/validate/fail', {}, {
        id: '157'
    }).start();

    deepEqual([
        ['POST', {ids: ['157']}]
    ], this.mockBackendUrlCalls('mock/crudity/validate/fail'));


    this.assertOpenedDialog(gettext('Bad Request'));
    this.closeDialog();

    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.crudity.brick.crudity-delete (empty selector)', function(assert) {
    var brick = this.createCrudityBrickTable().brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    brick.action('crudity-delete', 'mock/crudity/delete').start();

    equal(false, brick.isLoading());

    this.assertOpenedAlertDialog(gettext('Nothing is selected.'));
    this.closeDialog();

    deepEqual([], this.mockBackendCalls());
});

QUnit.test('creme.emails.brick.crudity-delete (fail)', function(assert) {
    var brick = this.createCrudityBrickTable().brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, [0, 1]);
    equal(2, selections.selected().length);

    brick.action('crudity-delete', 'mock/crudity/delete/fail').start();

    deepEqual([
        ['POST', {ids: ['1', '2']}]
    ], this.mockBackendUrlCalls('mock/crudity/delete/fail'));

    this.assertOpenedDialog(gettext('Bad Request'));
    this.closeDialog();

    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.brick.crudity-delete', function(assert) {
    var brick = this.createCrudityBrickTable().brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, [0, 1]);
    equal(2, selections.selected().length);

    brick.action('crudity-delete', 'mock/crudity/delete').start();

    deepEqual([
        ['POST', {ids: ['1', '2']}]
    ], this.mockBackendUrlCalls('mock/crudity/delete'));

    this.assertOpenedDialog(gettext('Process done'));
    this.closeDialog();

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.crudity.RefreshSyncStatusAction (fail)', function(assert) {
    var action = new creme.crudity.RefreshSyncStatusAction({url: 'mock/crudity/waiting/sync/fail'});

    action.onFail(this.mockListener('action-fail'))
          .onDone(this.mockListener('action-done'))
          .start();

    this.assertClosedDialog();

    deepEqual([
        ['POST', {}]
    ], this.mockBackendUrlCalls('mock/crudity/waiting/sync/fail'));

    deepEqual([['fail', 'Unable to sync actions']], this.mockListenerCalls('action-fail'));
    deepEqual([], this.mockListenerCalls('action-done'));
});

QUnit.test('creme.crudity.RefreshSyncStatusAction (fail, warning)', function(assert) {
    var action = new creme.crudity.RefreshSyncStatusAction({url: 'mock/crudity/waiting/sync/fail', warnOnFail: true});

    action.onFail(this.mockListener('action-fail'))
          .onDone(this.mockListener('action-done'))
          .start();

    deepEqual([
        ['POST', {}]
    ], this.mockBackendUrlCalls('mock/crudity/waiting/sync/fail'));

    this.assertOpenedAlertDialog('Unable to sync actions');

    deepEqual([], this.mockListenerCalls('action-fail'));
    deepEqual([], this.mockListenerCalls('action-done'));

    this.closeDialog();

    deepEqual([['fail', 'Unable to sync actions']], this.mockListenerCalls('action-fail'));
    deepEqual([], this.mockListenerCalls('action-done'));
});

QUnit.test('creme.crudity.RefreshSyncStatusAction (done, no deps)', function(assert) {
    var action = new creme.crudity.RefreshSyncStatusAction({url: 'mock/crudity/waiting/sync'});

    action.onFail(this.mockListener('action-fail'))
          .onDone(this.mockListener('action-done'))
          .start();

    deepEqual([
        ['POST', {}]
    ], this.mockBackendUrlCalls('mock/crudity/waiting/sync'));

    this.assertClosedDialog();

    deepEqual([], this.mockListenerCalls('action-fail'));
    deepEqual([[
        'done', ['a', 'b']
    ]], this.mockListenerCalls('action-done'));

    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.crudity.RefreshSyncStatusAction (done, with deps)', function(assert) {
    this.createCrudityBrickTable({
        id: 'brick-A',
        attributes: {'data-crudity-backend': 'a'},
        deps: ['brick-B', 'brick-C']
    });

    this.createCrudityBrickTable({
        id: 'brick-B',
        attributes: {'data-crudity-backend': 'b'},
        deps: ['brick-D']
    });

    this.createCrudityBrickTable({
        id: 'brick-C'
    });

    this.createCrudityBrickTable({
        id: 'brick-D',
        attributes: {'data-crudity-backend': 'c'}
    });

    var action = new creme.crudity.RefreshSyncStatusAction({url: 'mock/crudity/waiting/sync'});

    action.onFail(this.mockListener('action-fail'))
          .onDone(this.mockListener('action-done'))
          .start();

    deepEqual([
        ['POST', {}]
    ], this.mockBackendUrlCalls('mock/crudity/waiting/sync'));

    deepEqual([
        ['GET', {"brick_id": ["brick-A", "brick-B"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.assertClosedDialog();

    deepEqual([], this.mockListenerCalls('action-fail'));
    deepEqual([[
        'done', ['a', 'b']
    ]], this.mockListenerCalls('action-done'));
});

QUnit.test('creme.crudity.CrudityHatController (bind)', function(assert) {
    var controller = new creme.crudity.CrudityHatController();
    var element = $('<div>');

    equal(false, controller.isBound());

    controller.bind(element);

    equal(true, controller.isBound());

    this.assertRaises(function() {
        controller.bind(element);
    }, Error, 'Error: CrudityHatController is already bound');
});

QUnit.test('creme.crudity.CrudityHatController (refresh)', function(assert) {
    var mockBackendUrlCalls = this.mockBackendUrlCalls.bind(this);

    var controller = new creme.crudity.CrudityHatController();
    var element = $('<div><a data-action="crudity-hatbar-refresh" href="mock/crudity/waiting/sync"></a</div>');

    controller.bind(element);
    controller.refresh(200);

    deepEqual([], mockBackendUrlCalls('mock/crudity/waiting/sync'));

    stop(1);

    setTimeout(function() {
        start();
        deepEqual([
            ['POST', {}]
        ], mockBackendUrlCalls('mock/crudity/waiting/sync'));
    }, 300);
});

QUnit.test('creme.crudity.CrudityHatController (refresh, canceled)', function(assert) {
    var mockBackendUrlCalls = this.mockBackendUrlCalls.bind(this);

    var controller = new creme.crudity.CrudityHatController();
    var element = $('<div><a data-action="crudity-hatbar-refresh" href="mock/crudity/waiting/sync"></a</div>');

    controller.bind(element);
    controller.refresh(300);

    deepEqual([], mockBackendUrlCalls('mock/crudity/waiting/sync'));

    controller.refresh(300);

    stop(2);

    setTimeout(function() {
        start();
        deepEqual([], mockBackendUrlCalls('mock/crudity/waiting/sync'));
        controller.refresh(300);
    }, 100);

    setTimeout(function() {
        start();
        deepEqual([
            ['POST', {}]
        ], mockBackendUrlCalls('mock/crudity/waiting/sync'));
    }, 500);
});

}(jQuery));
