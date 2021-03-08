(function($) {

QUnit.module("creme.bricks.actions", new QUnitMixin(QUnitEventMixin,
                                                    QUnitAjaxMixin,
                                                    QUnitBrickMixin,
                                                    QUnitDialogMixin,
                                                    QUnitListViewMixin, {
    beforeEach: function() {
        var backend = this.backend;
        var selectionListHtml = this.createListViewHtml(this.defaultListViewHtmlOptions({
            reloadurl: 'mock/listview/reload/selection-list'
        }));

        this.setListviewReloadResponse(selectionListHtml, 'selection-list');

        this.setMockBackendGET({
            'mock/relation/selector': backend.response(200, selectionListHtml)
        });

        this.setMockBackendPOST({
            'mock/relation/add': backend.response(200, ''),
            'mock/relation/add/fail': backend.response(400, 'Unable to add relation')
        });

        this.brickActionListeners = {
            start: this.mockListener('action-start'),
            cancel: this.mockListener('action-cancel'),
            fail: this.mockListener('action-fail'),
            done: this.mockListener('action-done')
        };

        this.brickActionLinkListeners = {
            'action-link-start': this.mockListener('action-link-start'),
            'action-link-cancel': this.mockListener('action-link-cancel'),
            'action-link-fail': this.mockListener('action-link-fail'),
            'action-link-done': this.mockListener('action-link-done')
        };

        $('body').attr('data-save-relations-url', 'mock/relation/add');
        $('body').attr('data-select-relations-objects-url', 'mock/relation/selector');
    }
}));

QUnit.test('creme.bricks.Brick.action (toggle collapse)', function(assert) {
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test"></div>').appendTo(this.qunitFixture());
    var brick = new creme.bricks.Brick({
                    deferredStateSaveDelay: 0
                });

    equal(false, brick.isBound());

    brick.action('collapse').on(this.brickActionListeners).start();
    equal(false, element.is('.is-collapsed'));
    deepEqual([['cancel', 'brick is not bound', brick]], this.mockListenerCalls('action-cancel'));

    this.resetMockListenerCalls();

    brick.bind(element);
    equal(true, brick.isBound());
    equal(false, element.is('.is-collapsed'));

    brick.action('collapse').on(this.brickActionListeners).start();
    equal(true, element.is('.is-collapsed'));
    deepEqual([['done']], this.mockListenerCalls('action-done'));

    brick.action('collapse').on(this.brickActionListeners).start();
    equal(false, element.is('.is-collapsed'));
    deepEqual([['done'], ['done']], this.mockListenerCalls('action-done'));
});

QUnit.test('creme.bricks.Brick.action (toggle content-reduced)', function(assert) {
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test"></div>').appendTo(this.qunitFixture());
    var brick = new creme.bricks.Brick({
                    deferredStateSaveDelay: 0
                });

    equal(false, brick.isBound());

    brick.action('reduce-content').on(this.brickActionListeners).start();
    equal(false, element.is('.is-content-reduced'));
    deepEqual([['cancel', 'brick is not bound', brick]], this.mockListenerCalls('action-cancel'));

    this.resetMockListenerCalls();

    brick.bind(element);
    equal(true, brick.isBound());
    equal(false, element.is('.is-content-reduced'));

    brick.action('reduce-content').on(this.brickActionListeners).start();
    equal(true, element.is('.is-content-reduced'));
    deepEqual([['done']], this.mockListenerCalls('action-done'));

    brick.action('reduce-content').on(this.brickActionListeners).start();
    equal(false, element.is('.is-content-reduced'));
    deepEqual([['done'], ['done']], this.mockListenerCalls('action-done'));
});

QUnit.test('creme.bricks.Brick.action (form, canceled)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('form').on(this.brickActionListeners).start();

    equal(false, brick.isLoading());
    this.assertOpenedDialog();
    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.closeDialog();

    equal(false, brick.isLoading());
    this.assertClosedDialog();
    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));  // closing popup cancels the action.
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.action (form, submit)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    equal(true, brick.isBound());
    equal(false, brick.isLoading());
    this.assertClosedDialog();

    brick.action('form', 'mock/form').on(this.brickActionListeners).start();

    equal(false, brick.isLoading());
    this.assertOpenedDialog();
    deepEqual([], this.mockListenerCalls('action-done'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.submitFormDialog();

    equal(false, brick.isLoading());
    deepEqual([['done', {content: '', data: '', type: 'text/html'}, 'text/html']], this.mockFormSubmitCalls('action-done'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
    deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.bricks.Brick.action (form, submit, redirect)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    equal(true, brick.isBound());
    equal(false, brick.isLoading());
    this.assertClosedDialog();

    brick.action('form', 'mock/form/redirect').on(this.brickActionListeners).start();

    equal(false, brick.isLoading());
    this.assertOpenedDialog();
    deepEqual([], this.mockListenerCalls('action-done'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.submitFormDialog();

    equal(false, brick.isLoading());
    deepEqual([['done', {content: 'mock/redirect', data: 'mock/redirect', type: 'text/plain'}, 'text/plain']], this.mockFormSubmitCalls('action-done'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
    deepEqual(['mock/redirect'], this.mockRedirectCalls());
});

QUnit.test('creme.bricks.Brick.action (form-refresh, canceled)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    equal(true, brick.isBound());
    equal(false, brick.isLoading());
    this.assertClosedDialog();

    brick.action('form-refresh').on(this.brickActionListeners).start();
    equal(false, brick.isLoading());
    this.assertOpenedDialog();
    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.closeDialog();

    equal(false, brick.isLoading());
    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));  // closing popup cancels the action.
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.action (form-refresh, submit)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('form-refresh', 'mock/form').on(this.brickActionListeners).start();

    equal(false, brick.isLoading());
    this.assertOpenedDialog();
    deepEqual([], this.mockListenerCalls('action-done'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.submitFormDialog();

    equal(false, brick.isLoading());
    deepEqual([['done', {content: '', data: '', type: 'text/html'}, 'text/html']], this.mockFormSubmitCalls('action-done'));

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.action (refresh)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    brick.action('refresh').on(this.brickActionListeners).start();
    equal(false, brick.isLoading());

    deepEqual([['done']], this.mockListenerCalls('action-done').map(function(e) { return e.slice(0, 1); }));

    deepEqual([
        ['mock/brick/all/reload', 'GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}, {dataType: "json", delay: 0,  enableUriSearch: false, sync: true}]
    ], this.mockBackendCalls());
});

QUnit.test('creme.bricks.Brick.action (add, submit)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('add', 'mock/form').on(this.brickActionListeners).start();

    equal(false, brick.isLoading());
    this.assertOpenedDialog();
    deepEqual([], this.mockListenerCalls('action-done'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.submitFormDialog();

    equal(false, brick.isLoading());
    deepEqual([['done', {content: '', data: '', type: 'text/html'}, 'text/html']], this.mockFormSubmitCalls('action-done'));

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.action (edit, submit)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('edit', 'mock/form').on(this.brickActionListeners).start();

    equal(false, brick.isLoading());
    this.assertOpenedDialog();
    deepEqual([], this.mockListenerCalls('action-done'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.submitFormDialog();

    equal(false, brick.isLoading());
    deepEqual([['done', {content: '', data: '', type: 'text/html'}, 'text/html']], this.mockFormSubmitCalls('action-done'));

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.action (link, submit)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('link', 'mock/form').on(this.brickActionListeners).start();

    equal(false, brick.isLoading());
    this.assertOpenedDialog();
    deepEqual([], this.mockListenerCalls('action-done'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.submitFormDialog();

    equal(false, brick.isLoading());
    deepEqual([['done', {content: '', data: '', type: 'text/html'}, 'text/html']], this.mockFormSubmitCalls('action-done'));

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.action (delete, not confirmed)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('delete', 'mock/brick/delete').on(this.brickActionListeners).start();
    equal(false, brick.isLoading());
    this.assertOpenedDialog();
    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/delete'));

    this.closeDialog();

    equal(false, brick.isLoading());
    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/delete'));
});

QUnit.test('creme.bricks.Brick.action (delete, confirmed)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('delete', 'mock/brick/delete').on(this.brickActionListeners).start();
    equal(false, brick.isLoading());
    this.assertOpenedDialog();
    deepEqual([], this.mockListenerCalls('action-done'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/delete'));

    this.acceptConfirmDialog();

    equal(false, brick.isLoading());
    deepEqual([['done', '']], this.mockListenerCalls('action-done'));
    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/brick/delete'));
    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.action (delete, confirmed, failed)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('delete', 'mock/brick/delete/fail').on(this.brickActionListeners).start();
    equal(false, brick.isLoading());
    deepEqual([], this.mockListenerCalls('action-fail'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/delete/fail'));

    // confirm dialog
    this.assertOpenedDialog();
    this.acceptConfirmDialog();

    // warning dialog
    this.assertOpenedAlertDialog();
    this.closeDialog();

    equal(false, brick.isLoading());
    deepEqual([['fail', '']], this.mockListenerCalls('action-fail').map(function(d) { return d.slice(0, 2); }));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/delete/fail'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.action (update)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('update', 'mock/brick/update').on(this.brickActionListeners).start();
    equal(false, brick.isLoading());
    this.assertClosedDialog();
    deepEqual([['done', '']], this.mockListenerCalls('action-done'));
    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/brick/update'));
    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.action (update, failed)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('update', 'mock/error').on(this.brickActionListeners).start();
    equal(false, brick.isLoading());

    // warning dialog
    this.assertOpenedAlertDialog(gettext('HTTP - Error 500'));
    this.closeDialog();

    deepEqual([['fail', 'HTTP - Error 500']], this.mockListenerCalls('action-fail').map(function(d) { return d.slice(0, 2); }));
    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/error'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.action (update, with confirmation, not confirmed)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('update', 'mock/brick/update', {confirm: true}).on(this.brickActionListeners).start();

    this.assertOpenedConfirmDialog(gettext('Are you sure ?'));

    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/update'));

    this.closeDialog();

    equal(false, brick.isLoading());
    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/update'));
});

QUnit.test('creme.bricks.Brick.action (update, with confirmation, confirmed)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('update', 'mock/brick/update', {confirm: true}).on(this.brickActionListeners).start();

    this.assertOpenedConfirmDialog(gettext('Are you sure ?'));

    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/update'));

    this.acceptConfirmDialog();

    deepEqual([['done', '']], this.mockListenerCalls('action-done'));
    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/brick/update'));
    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.action (update, with custom confirmation, confirmed)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('update', 'mock/brick/update', {confirm: 'Are you really sure ?'}).on(this.brickActionListeners).start();

    this.assertOpenedConfirmDialog('Are you really sure ?');

    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/update'));

    this.acceptConfirmDialog();

    deepEqual([['done', '']], this.mockListenerCalls('action-done'));
    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/brick/update'));
    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.action (update, with message on success)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('update', 'mock/brick/update', {messageOnSuccess: 'Action done !'}).on(this.brickActionListeners).start();

    equal(false, brick.isLoading());

    this.assertOpenedDialog('Action done !');

    deepEqual([], this.mockListenerCalls('action-done'));
    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/brick/update'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.closeDialog();

    deepEqual([['done', '']], this.mockListenerCalls('action-done'));
    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/brick/update'));
    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.action (update, message + reload on success)', function(assert) {
    var current_url = window.location.href;
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('update', 'mock/brick/update', {
        messageOnSuccess: 'Action done !',
        reloadOnSuccess: true
    }).on(this.brickActionListeners).start();

    equal(false, brick.isLoading());

    this.assertOpenedDialog('Action done !');

    deepEqual([], this.mockListenerCalls('action-done'));
    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/brick/update'));
    deepEqual([], this.mockReloadCalls());

    this.closeDialog();

    deepEqual([['done', '']], this.mockListenerCalls('action-done'));
    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/brick/update'));
    deepEqual([current_url], this.mockReloadCalls());
});

QUnit.test('creme.bricks.Brick.action (update, message + reload on fail)', function(assert) {
    var current_url = window.location.href;
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('update', 'mock/error', {
        reloadOnFail: true
    }).on(this.brickActionListeners).start();

    this.assertOpenedAlertDialog();

    deepEqual([], this.mockListenerCalls('action-fail'));
    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/error'));
    deepEqual([], this.mockReloadCalls());

    this.closeDialog();

    deepEqual([['fail', 'HTTP - Error 500']], this.mockListenerCalls('action-fail').map(function(d) { return d.slice(0, 2); }));
    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/error'));
    deepEqual([current_url], this.mockReloadCalls());
});

QUnit.test('creme.bricks.Brick.action (update-redirect)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('update-redirect', 'mock/brick/update', {}, {next: 'mock/next'})
         .on(this.brickActionListeners).start();

    equal(false, brick.isLoading());
    this.assertClosedDialog();
    deepEqual([['done', 'mock/next']], this.mockListenerCalls('action-done'));
    deepEqual([['POST', {next: 'mock/next'}]], this.mockBackendUrlCalls('mock/brick/update'));
    deepEqual(['mock/next'], this.mockRedirectCalls());
});

QUnit.test('creme.bricks.Brick.action (update-redirect, no redirection)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('update-redirect', 'mock/brick/update')
         .on(this.brickActionListeners).start();

    equal(false, brick.isLoading());
    this.assertClosedDialog();
    deepEqual([['done', '']], this.mockListenerCalls('action-done'));
    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/brick/update'));
    deepEqual([''], this.mockRedirectCalls());
});

QUnit.test('creme.bricks.Brick.action (update-redirect, failed)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('update-redirect', 'mock/brick/update/fail', {}, {next: 'mock/next'})
         .on(this.brickActionListeners).start();

    equal(false, brick.isLoading());

    // warning dialog
    this.assertOpenedAlertDialog();
    this.closeDialog();

    deepEqual([['fail', '']], this.mockListenerCalls('action-fail').map(function(d) { return d.slice(0, 2); }));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/update/fail'));
    deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.bricks.Brick.action (update-redirect, with confirmation, not confirmed)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('update-redirect', 'mock/brick/update', {confirm: true}, {next: 'mock/next'})
         .on(this.brickActionListeners).start();

    equal(false, brick.isLoading());
    this.assertOpenedDialog();
    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/update'));
    deepEqual([], this.mockRedirectCalls());

    this.closeDialog();

    equal(false, brick.isLoading());
    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/update'));
    deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.bricks.Brick.action (update-redirect, with confirmation, confirmed)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('update-redirect', 'mock/brick/update', {confirm: true}, {next: 'mock/next'}).on(this.brickActionListeners).start();
    equal(false, brick.isLoading());
    this.assertOpenedDialog();
    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/update'));
    deepEqual([], this.mockRedirectCalls());

    this.acceptConfirmDialog();

    deepEqual([['done', 'mock/next']], this.mockListenerCalls('action-done'));
    deepEqual([['POST', {next: 'mock/next'}]], this.mockBackendUrlCalls('mock/brick/update'));
    deepEqual(['mock/next'], this.mockRedirectCalls());
});

QUnit.test('creme.bricks.Brick.action (redirect)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('redirect', 'mock/redirect').on(this.brickActionListeners).start();
    equal(false, brick.isLoading());
    deepEqual([['done']], this.mockListenerCalls('action-done'));
    deepEqual(['mock/redirect'], this.mockRedirectCalls());
});

QUnit.test('creme.bricks.Brick.action (redirect template)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();
    var location = window.location.href.replace(/.*?:\/\/[^\/]*/g, '');

    this.assertClosedDialog();

    brick.action('redirect', 'mock/redirect/${id}?source=${location}', {}, {
        id: 157
    }).on(this.brickActionListeners).start();

    equal(false, brick.isLoading());
    deepEqual([['done']], this.mockListenerCalls('action-done'));
    deepEqual(['mock/redirect/157?source=' + location], this.mockRedirectCalls());
});

QUnit.test('creme.bricks.Brick.action (view)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('view', 'mock/view').on(this.brickActionListeners).start();
    equal(false, brick.isLoading());
    deepEqual([], this.mockListenerCalls('action-done'));
    deepEqual([['GET', {}]], this.mockBackendUrlCalls('mock/view'));

    this.assertOpenedDialog();
    this.closeDialog();

    deepEqual([['done']], this.mockListenerCalls('action-done'));
    deepEqual([['GET', {}]], this.mockBackendUrlCalls('mock/view'));
});

QUnit.test('creme.bricks.Brick.action (view, failed)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('view', 'mock/view/fail').on(this.brickActionListeners).start();
    equal(false, brick.isLoading());
    deepEqual([], this.mockListenerCalls('action-done'));
    deepEqual([], this.mockBackendUrlCalls('mock/view/fail'));

    this.assertOpenedDialog();
    this.closeDialog();

    deepEqual([['done']], this.mockListenerCalls('action-done'));
    deepEqual([], this.mockBackendUrlCalls('mock/view/fail'));
});

QUnit.test('creme.bricks.Brick.action (add relationships, no selection)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    brick.action('add-relationships', '', {}, {
        subject_id: '74',
        rtype_id: 'rtypes.1',
        ctype_id: '5',
        addto_url: 'mock/relation/add',
        selector_url: 'mock/relation/selector'
    }).on(this.brickActionListeners).start();

    deepEqual([
        ['GET', {subject_id: '74', rtype_id: 'rtypes.1', objects_ct_id: '5', selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/relation/selector'));

    var list = this.assertOpenedListViewDialog().find('.ui-creme-listview').list_view();

    deepEqual([], list.selectedRows());

    this.validateListViewSelectionDialog();

    this.assertOpenedAlertDialog(gettext('Please select at least one entity.'));
    this.assertOpenedListViewDialog();

    deepEqual([], this.mockListenerCalls('action-cancel'));

    this.closeTopDialog();
    this.assertOpenedListViewDialog();

    deepEqual([], this.mockListenerCalls('action-cancel'));

    this.closeDialog();

    deepEqual([
        ['mock/relation/selector', 'GET', {subject_id: '74', rtype_id: 'rtypes.1', objects_ct_id: '5', selection: 'single'}]
    ], this.mockBackendUrlCalls());

    deepEqual({
        'action-start': [['start']],
        'action-cancel': [['cancel']]
    }, this.mockListenerCalls());
});

QUnit.test('creme.bricks.Brick.action (add relationships, single, multiple selection)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();
    brick.action('add-relationships', 'mock/relation/add', {}, {
        subject_id: '74',
        rtype_id: 'rtypes.1',
        ctype_id: '5',
        selector_url: 'mock/relation/selector',
        selection: 'single'
    }).on(this.brickActionListeners).start();

    deepEqual([
        ['GET', {subject_id: '74', rtype_id: 'rtypes.1', objects_ct_id: '5', selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/relation/selector'));

    var list = this.assertOpenedListViewDialog().find('.ui-creme-listview').list_view();

    this.setListviewSelection(list, ['2', '3']);
    deepEqual(['2', '3'], list.selectedRows());

    this.validateListViewSelectionDialog();

    this.assertOpenedAlertDialog(gettext('Please select only one entity.'));
    this.assertOpenedListViewDialog();

    this.closeTopDialog();
    this.assertOpenedListViewDialog();

    this.closeDialog();

    deepEqual([
        ['mock/relation/selector', 'GET', {subject_id: '74', rtype_id: 'rtypes.1', objects_ct_id: '5', selection: 'single'}]
    ], this.mockBackendUrlCalls());

    deepEqual([], this.mockRedirectCalls());

    deepEqual({
        'action-start': [['start']],
        'action-cancel': [['cancel']]
    }, this.mockListenerCalls());
});

QUnit.test('creme.bricks.Brick.action (add relationships, single)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();
    brick.action('add-relationships', 'mock/relation/add', {}, {
        subject_id: '74',
        rtype_id: 'rtypes.1',
        ctype_id: '5',
        selector_url: 'mock/relation/selector'
    }).on(this.brickActionListeners).start();

    deepEqual([
        ['GET', {subject_id: '74', rtype_id: 'rtypes.1', objects_ct_id: '5', selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/relation/selector'));

    var list = this.assertOpenedListViewDialog().find('.ui-creme-listview').list_view();

    this.setListviewSelection(list, ['2']);
    deepEqual(['2'], list.selectedRows());

    this.validateListViewSelectionDialog();
    this.assertClosedDialog();

    deepEqual([
        ['mock/relation/selector', 'GET', {subject_id: '74', rtype_id: 'rtypes.1', objects_ct_id: '5', selection: 'single'}],
        ['mock/relation/add', 'POST', {entities: ['2'], predicate_id: 'rtypes.1', subject_id: '74'}]
    ], this.mockBackendUrlCalls());

    deepEqual([], this.mockRedirectCalls());

    deepEqual({
        'action-start': [['start']],
        'action-done': [['done']]
    }, this.mockListenerCalls());
});

// TODO: test "list_title" option
QUnit.test('creme.bricks.Brick.action (add relationships, q_filter)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();
    var rtype_id = 'creme_core-subject_test_predicate';
    var sel_url = 'mock/relation/selector';
    var q_filter = '{"op":"AND","val":[["first_name","John"]]}';

    brick.action('add-relationships', 'mock/relation/add', {}, {
        subject_id: '74',
        rtype_id: rtype_id,
        ctype_id: '5',
        selector_url: sel_url,
        q_filter: q_filter
    }).on(this.brickActionListeners).start();

    deepEqual([
        ['GET',
         {subject_id: '74',
          rtype_id: rtype_id,
          objects_ct_id: '5',
          selection: 'single',
          q_filter: q_filter
         }
        ]
    ], this.mockBackendUrlCalls(sel_url));
});

QUnit.test('creme.bricks.Brick.action (add relationships, single, fail)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();
    brick.action('add-relationships', 'mock/relation/add/fail', {}, {
        subject_id: '74',
        rtype_id: 'rtypes.1',
        ctype_id: '5',
        selector_url: 'mock/relation/selector'
    }).on(this.brickActionListeners).start();

    deepEqual([
        ['GET', {subject_id: '74', rtype_id: 'rtypes.1', objects_ct_id: '5', selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/relation/selector'));

    var list = this.assertOpenedListViewDialog().find('.ui-creme-listview').list_view();

    this.setListviewSelection(list, ['2']);
    deepEqual(['2'], list.selectedRows());

    this.validateListViewSelectionDialog();
    this.assertClosedDialog();

    deepEqual([
        ['mock/relation/selector', 'GET', {subject_id: '74', rtype_id: 'rtypes.1', objects_ct_id: '5', selection: 'single'}],
        ['mock/relation/add/fail', 'POST', {entities: ['2'], predicate_id: 'rtypes.1', subject_id: '74'}]
    ], this.mockBackendUrlCalls());

    deepEqual([], this.mockRedirectCalls());

    deepEqual(['fail'],
             this.mockListenerCalls('action-fail').map(function(d) { return d[0]; }));
});

QUnit.test('creme.bricks.Brick.action (add relationships, single, reload)', function(assert) {
    var current_url = window.location.href;
    var brick = this.createBrickWidget('brick-for-test').brick();
    brick.action('add-relationships', 'mock/relation/add', {}, {
        subject_id: '74',
        rtype_id: 'rtypes.1',
        ctype_id: '5',
        selector_url: 'mock/relation/selector',
        reloadOnSuccess: true
    }).on(this.brickActionListeners).start();

    deepEqual([
        ['GET', {subject_id: '74', rtype_id: 'rtypes.1', objects_ct_id: '5', selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/relation/selector'));

    var list = this.assertOpenedListViewDialog().find('.ui-creme-listview').list_view();

    this.setListviewSelection(list, ['2']);
    deepEqual(['2'], list.selectedRows());

    this.validateListViewSelectionDialog();
    this.assertClosedDialog();

    deepEqual([
        ['mock/relation/selector', 'GET', {subject_id: '74', rtype_id: 'rtypes.1', objects_ct_id: '5', selection: 'single'}],
        ['mock/relation/add', 'POST', {entities: ['2'], predicate_id: 'rtypes.1', subject_id: '74'}]
    ], this.mockBackendUrlCalls());

    deepEqual([current_url], this.mockReloadCalls());

    deepEqual({
        'action-start': [['start']],
        'action-done': [['done']]
    }, this.mockListenerCalls());
});


QUnit.test('creme.bricks.Brick.action (add relationships, single, reload, fail)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();
    brick.action('add-relationships', 'mock/relation/add/fail', {}, {
        subject_id: '74',
        rtype_id: 'rtypes.1',
        ctype_id: '5',
        selector_url: 'mock/relation/selector',
        reloadOnSuccess: true
    }).on(this.brickActionListeners).start();

    deepEqual([
        ['GET', {subject_id: '74', rtype_id: 'rtypes.1', objects_ct_id: '5', selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/relation/selector'));

    var list = this.assertOpenedListViewDialog().find('.ui-creme-listview').list_view();

    this.setListviewSelection(list, ['2']);
    deepEqual(['2'], list.selectedRows());

    this.validateListViewSelectionDialog();
    this.assertClosedDialog();

    deepEqual([
        ['mock/relation/selector', 'GET', {subject_id: '74', rtype_id: 'rtypes.1', objects_ct_id: '5', selection: 'single'}],
        ['mock/relation/add/fail', 'POST', {entities: ['2'], predicate_id: 'rtypes.1', subject_id: '74'}]
    ], this.mockBackendUrlCalls());

    deepEqual([], this.mockRedirectCalls());
    deepEqual(['fail'], this.mockListenerCalls('action-fail').map(function(d) { return d[0]; }));
});

QUnit.test('creme.bricks.Brick.action (add relationships, multiple)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();
    brick.action('add-relationships', 'mock/relation/add', {}, {
        subject_id: '74',
        rtype_id: 'rtypes.1',
        ctype_id: '5',
        selector_url: 'mock/relation/selector',
        multiple: true
    }).on(this.brickActionListeners).start();

    deepEqual([
        ['GET', {subject_id: '74', rtype_id: 'rtypes.1', objects_ct_id: '5', selection: 'multiple'}]
    ], this.mockBackendUrlCalls('mock/relation/selector'));

    var list = this.assertOpenedListViewDialog().find('.ui-creme-listview').list_view();

    this.setListviewSelection(list, ['2', '3']);

    equal(2, list.selectedRowsCount());
    deepEqual(['2', '3'], list.selectedRows());

    this.validateListViewSelectionDialog();
    this.assertClosedDialog();

    deepEqual([
        ['mock/relation/selector', 'GET', {subject_id: '74', rtype_id: 'rtypes.1', objects_ct_id: '5', selection: 'multiple'}],
        ['mock/relation/add', 'POST', {entities: ['2', '3'], predicate_id: 'rtypes.1', subject_id: '74'}]
    ], this.mockBackendUrlCalls());

    deepEqual({
        'action-start': [['start']],
        'action-done': [['done']]
    }, this.mockListenerCalls());
});

QUnit.test('creme.bricks.Brick.action (unknown)', function(assert) {
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test"></div>');
    var brick = new creme.bricks.Brick();

    equal(false, brick.isBound());

    brick.action('unknown-action').on(this.brickActionListeners).start();
    deepEqual([['cancel', 'brick is not bound', brick]], this.mockListenerCalls('action-cancel'));

    this.resetMockListenerCalls();

    brick.bind(element);
    equal(true, brick.isBound());

    brick.action('unknown-action').on(this.brickActionListeners).start();
    deepEqual([['fail', 'no such action "unknown-action"', brick]], this.mockListenerCalls('action-fail'));
});

QUnit.test('creme.bricks.Brick.action (loading)', function(assert) {
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test"></div>');
    var brick = new creme.bricks.Brick();

    brick.bind(element);
    brick.setLoadingState(true, 'Loading test...');

    equal(true, brick.isBound());
    equal(true, brick.isLoading());

    brick.action('collapse').on(this.brickActionListeners).start();
    deepEqual([['cancel', 'brick is in loading state', brick]], this.mockListenerCalls('action-cancel'));
});

QUnit.test('creme.bricks.Brick.action (link, no data)', function(assert) {
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test"></div>');
    var collapse = $('<a data-action="collapse"></a>');

    element.append(collapse);
    var brick = new creme.bricks.Brick({
                    deferredStateSaveDelay: 0
                }).bind(element);

    equal(true, brick.isBound());
    equal(false, element.is('.is-collapsed'));
    equal(1, brick._actionLinks.length);

    brick._actionLinks[0].on(this.brickActionLinkListeners);

    collapse.trigger('click');
    equal(true, element.is('.is-collapsed'));
    deepEqual([['action-link-done', []]],
              this.mockListenerCalls('action-link-done').map(function(d) { return d.slice(0, 2); }));

    collapse.trigger('click');
    equal(false, element.is('.is-collapsed'));
    deepEqual([['action-link-done', []], ['action-link-done', []]],
              this.mockListenerCalls('action-link-done').map(function(d) { return d.slice(0, 2); }));
});

QUnit.test('creme.bricks.Brick.action (link, unknown)', function(assert) {
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test"></div>');
    var a = $('<a data-action="unknown"></a>').appendTo(element);
    var brick = new creme.bricks.Brick({
                    deferredStateSaveDelay: 0
                }).bind(element);

    equal(true, brick.isBound());
    equal(false, element.is('.is-collapsed'));
    equal(1, brick._actionLinks.length);

    var actionlink = brick._actionLinks[0];
    equal(true, actionlink.isBound());
    equal(true, actionlink.isDisabled());

    actionlink.on(this.brickActionLinkListeners);
    a.trigger('click');

    deepEqual({}, this.mockListenerCalls());
});

QUnit.test('creme.bricks.Brick.action (link, loading state)', function(assert) {
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test"></div>');
    var collapse = $('<a data-action="collapse"></a>').appendTo(element);

    var brick = new creme.bricks.Brick({
                    deferredStateSaveDelay: 0
                }).bind(element);

    brick.setLoadingState(true, 'Loading test...');

    equal(true, brick.isBound());
    equal(true, brick.isLoading());
    equal(false, element.is('.is-collapsed'));
    equal(1, brick._actionLinks.length);

    brick._actionLinks[0].on(this.brickActionLinkListeners);

    collapse.trigger('click');

    equal(false, element.is('.is-collapsed'));
    deepEqual({}, this.mockListenerCalls()); // call in this case !

    brick.setLoadingState(false);
    collapse.trigger('click');

    equal(true, element.is('.is-collapsed'));
    deepEqual([['action-link-done', []]],
              this.mockListenerCalls('action-link-done').map(function(d) { return d.slice(0, 2); }));
});

QUnit.test('creme.bricks.Brick.action (link, async)', function(assert) {
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test"></div>');
    var action = $('<a data-action="form" class="is-async-action" href="mock/brick/update"></a>').appendTo(element);

    var brick = new creme.bricks.Brick().bind(element);
    equal(true, brick.isBound());
    equal(false, brick.isLoading());
    equal(1, brick._actionLinks.length);
    this.assertClosedDialog();

    brick._actionLinks[0].on(this.brickActionLinkListeners)
                         .onComplete(this.mockListener('action-link-complete'));

    action.trigger('click');

    equal(true, brick.isLoading());
    this.assertOpenedDialog();
    deepEqual([['action-link-start', "mock/brick/update", {}, {}]],
              this.mockListenerCalls('action-link-start').map(function(d) { return d.slice(0, 4); }));
    deepEqual([], this.mockListenerCalls('action-link-complete'));

    this.closeDialog();

    equal(false, brick.isLoading());
    this.assertClosedDialog();
    deepEqual([['action-link-start', "mock/brick/update", {}, {}]],
              this.mockListenerCalls('action-link-start').map(function(d) { return d.slice(0, 4); }));
    deepEqual([['action-link-cancel', []]],
              this.mockListenerCalls('action-link-complete').map(function(d) { return d.slice(0, 2); }));
});

QUnit.test('creme.bricks.Brick.action (popover)', function(assert) {
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test"></div>');
    var action = $(
       '<a data-action="popover" >' +
           '<summary>Filter A Details</summary><details><h3>Filter by "A"</h3></details>' +
       '</a>'
    ).appendTo(element);

    var brick = new creme.bricks.Brick().bind(element);

    equal(true, brick.isBound());
    equal(false, brick.isLoading());
    equal(1, brick._actionLinks.length);

    brick._actionLinks[0].on(this.brickActionLinkListeners);

    action.trigger('click');

    var popover = this.assertOpenedPopover();
    this.assertPopoverTitle('Filter A Details');
    equal(popover.find('.popover-content').html(), '<h3>Filter by "A"</h3>');
});

QUnit.test('creme.bricks.Brick.registry', function(assert) {
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test"></div>');
    var brick = new creme.bricks.Brick().bind(element);
    var registry = brick.getActionBuilders();

    ok(Object.isSubClassOf(registry, creme.component.FactoryRegistry));

    ok(registry.has('view'));
    ok(registry.has('redirect'));

    ok(registry.has('refresh'));
    ok(registry.has('collapse'));
    ok(registry.has('reduce_content'));

    ok(registry.has('form'));
    ok(registry.has('form_refresh'));

    ok(registry.has('add'));
    ok(registry.has('edit'));
    ok(registry.has('link'));
    ok(registry.has('delete'));
    ok(registry.has('update'));
    ok(registry.has('update_redirect'));
    ok(registry.has('popover'));

    ok(registry.has('add_relationships'));
});

}(jQuery));
