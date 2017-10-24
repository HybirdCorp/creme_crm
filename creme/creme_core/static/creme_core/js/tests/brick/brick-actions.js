
QUnit.module("creme.bricks.actions", $.extend({}, QUnitBrickMixin, {
    setupBrick: function() {
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
    },

    createBrickWidget: function(id, content, title) {
        var html = (
            '<div class="brick ui-creme-widget" widget="brick" id="${id}" data-brick-deps="[&quot;dep1&quot;]">'
                 + '<div class="brick-header">'
                     + '<div class="brick-title">${title}</div>'
                 + '</div>'
                 + '<div>${content}</div>'
             + '</div>').template({
                 id: id,
                 content: content || '',
                 title: title || ''
             });

        var element = $(html).appendTo($('body'));
        var widget = creme.widget.create(element);
        var brick = widget.brick();

        equal(true, brick.isBound());
        equal(false, brick.isLoading());

        return widget;
    },

    assertClosedDialog: function() {
        equal(0, $('.ui-dialog').length, 'is dialog not opened');
    },

    assertOpenedDialog: function() {
        equal(1, $('.ui-dialog').length, 'is dialog opened');
    },

    assertOpenedAlertDialog: function() {
        equal(1, $('.ui-dialog .ui-creme-dialog-warn').length, 'is alert dialog opened');
    },

    closeDialog: function() {
        equal(1, $('.ui-dialog').length, 'single form dialog allowed');
        $('.ui-dialog-content').dialog('close');
    },

    submitFormDialog: function() {
        equal(1, $('.ui-dialog').length, 'single form dialog allowed');
        equal(1, $('.ui-dialog button[name="send"]').length, 'single form submit button allowed');

        $('.ui-dialog button[name="send"]').click();
    },

    acceptConfirmDialog: function() {
        equal(1, $('.ui-dialog').length, 'single confirm dialog allowed');
        equal(1, $('.ui-dialog button[name="ok"]').length, 'single confirm ok button allowed');

        $('.ui-dialog button[name="ok"]').click();
    }
}));

QUnit.test('creme.bricks.Brick.action (toggle collapse)', function(assert) {
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test"></div>').appendTo($('body'));
    var brick = new creme.bricks.Brick({
                    deferredStateSaveDelay: 0
                });

    equal(false, brick.isBound());

    brick.action('collapse').on(this.brickActionListeners).start();
    equal(false, element.is('.is-collapsed'));
    deepEqual([['cancel', 'brick is not bound', brick]], this.mockListenerCalls('action-cancel'));

    this.resetMockCalls();

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
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test"></div>').appendTo($('body'));
    var brick = new creme.bricks.Brick({
                    deferredStateSaveDelay: 0
                });

    equal(false, brick.isBound());

    brick.action('reduce-content').on(this.brickActionListeners).start();
    equal(false, element.is('.is-content-reduced'));
    deepEqual([['cancel', 'brick is not bound', brick]], this.mockListenerCalls('action-cancel'));

    this.resetMockCalls();

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
    deepEqual([['done', '']], this.mockListenerCalls('action-done'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
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
    deepEqual([['done', '']], this.mockListenerCalls('action-done'));

    deepEqual([
        {"brick_id": ["brick-for-test"], "extra_data": "{}"}
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
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
    deepEqual([['done', '']], this.mockListenerCalls('action-done'));

    deepEqual([
        {"brick_id": ["brick-for-test"], "extra_data": "{}"}
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
    deepEqual([['done', '']], this.mockListenerCalls('action-done'));

    deepEqual([
        {"brick_id": ["brick-for-test"], "extra_data": "{}"}
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
    deepEqual([['done', '']], this.mockListenerCalls('action-done'));

    deepEqual([
        {"brick_id": ["brick-for-test"], "extra_data": "{}"}
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
    deepEqual([{}], this.mockBackendUrlCalls('mock/brick/delete'));
    deepEqual([
        {"brick_id": ["brick-for-test"], "extra_data": "{}"}
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
    deepEqual([{}], this.mockBackendUrlCalls('mock/brick/update'));
    deepEqual([
        {"brick_id": ["brick-for-test"], "extra_data": "{}"}
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.action (update, failed)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('update', 'mock/brick/update/fail').on(this.brickActionListeners).start();
    equal(false, brick.isLoading());

    // warning dialog
    this.assertOpenedAlertDialog();
    this.closeDialog();

    deepEqual([['fail', '']], this.mockListenerCalls('action-fail').map(function(d) { return d.slice(0, 2); }));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/update/fail'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.action (update, with confirmation, not confirmed)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('update', 'mock/brick/update', {confirm: true}).on(this.brickActionListeners).start();
    equal(false, brick.isLoading());
    this.assertOpenedDialog();
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
    equal(false, brick.isLoading());
    this.assertOpenedDialog();
    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/update'));

    this.acceptConfirmDialog();

    deepEqual([['done', '']], this.mockListenerCalls('action-done'));
    deepEqual([{}], this.mockBackendUrlCalls('mock/brick/update'));
    deepEqual([
        {"brick_id": ["brick-for-test"], "extra_data": "{}"}
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.action (update-redirect)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('update-redirect', 'mock/brick/update', {}, {next: 'mock/next'})
         .on(this.brickActionListeners).start();

    equal(false, brick.isLoading());
    this.assertClosedDialog();
    deepEqual([['done', 'mock/next']], this.mockListenerCalls('action-done'));
    deepEqual([{next: 'mock/next'}], this.mockBackendUrlCalls('mock/brick/update'));
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
    deepEqual([{}], this.mockBackendUrlCalls('mock/brick/update'));
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
    deepEqual([{next: 'mock/next'}], this.mockBackendUrlCalls('mock/brick/update'));
    deepEqual(['mock/next'], this.mockRedirectCalls());
});

QUnit.test('creme.bricks.Brick.action (view)', function(assert) {
    var brick = this.createBrickWidget('brick-for-test').brick();

    this.assertClosedDialog();

    brick.action('view', 'mock/view').on(this.brickActionListeners).start();
    equal(false, brick.isLoading());
    deepEqual([], this.mockListenerCalls('action-done'));
    deepEqual([{}], this.mockBackendUrlCalls('mock/view'));

    this.assertOpenedDialog();
    this.closeDialog();

    deepEqual([['done']], this.mockListenerCalls('action-done'));
    deepEqual([{}], this.mockBackendUrlCalls('mock/view'));
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

QUnit.test('creme.bricks.Brick.action (unknown)', function(assert) {
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test"></div>');
    var brick = new creme.bricks.Brick();

    equal(false, brick.isBound());

    brick.action('unknown-action').on(this.brickActionListeners).start();
    deepEqual([['cancel', 'brick is not bound', brick]], this.mockListenerCalls('action-cancel'));

    this.resetMockCalls();

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

    collapse.click();
    equal(true, element.is('.is-collapsed'));
    deepEqual([['action-link-done', []]],
              this.mockListenerCalls('action-link-done').map(function(d) { return d.slice(0, 2); }));

    collapse.click();
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
    a.click();

    deepEqual([['action-link-cancel', []]],
            this.mockListenerCalls('action-link-cancel').map(function(d) { return d.splice(0, 2); }));
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

    collapse.click();

    equal(false, element.is('.is-collapsed'));
    deepEqual({}, this.mockListenerCalls()); // call in this case !

    brick.setLoadingState(false);
    collapse.click();

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

    action.click();

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
