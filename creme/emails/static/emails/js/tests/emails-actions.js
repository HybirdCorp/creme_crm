/* eslint operator-linebreak: ["error", "before"] */
(function($) {

QUnit.module("creme.emails.brick.actions", new QUnitMixin(QUnitEventMixin,
                                                          QUnitAjaxMixin,
                                                          QUnitBrickMixin,
                                                          QUnitDialogMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        this.setMockBackendGET({
            'mock/emails/sync/link': backend.response(200, '')
        });

        this.setMockBackendPOST({
            'mock/emails/sync/link': backend.response(200, ''),
            'mock/emails/sync/action': backend.response(200, ''),
            'mock/emails/sync/action/fail': backend.response(400, ''),
            'mock/emails/sync/delete': backend.response(200, ''),
            'mock/emails/sync/delete/fail': backend.response(400, '')
        });
    },

    createEmailBrickTable: function(options) {
        options = $.extend({
            classes: ['emails-email-brick'],
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

QUnit.test('creme.emails.brick.emailsync-link (empty selector)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emailsync-brick']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    brick.action('emailsync-link', 'mock/emails/sync/link', {}, {
        rtypes: ''
    }).start();

    equal(false, brick.isLoading());

    this.assertOpenedAlertDialog(gettext('Please select at least one entity.'));
    this.closeDialog();

    deepEqual([], this.mockBackendCalls());
});

QUnit.test('creme.emails.brick.emailsync-link', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emailsync-brick']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, ['1', '2']);
    equal(2, selections.selected().length);

    brick.action('emailsync-link', 'mock/emails/sync/link', {}, {
        rtypes: 'rtype.1,rtype.2'
    }).start();

    equal(false, brick.isLoading());

    deepEqual([
        ['GET', {persist: 'id', ids: ['2', '3'], rtype: 'rtype.1,rtype.2'}]
    ], this.mockBackendUrlCalls('mock/emails/sync/link'));

    this.assertOpenedDialog();
    this.submitFormDialog();
    this.assertClosedDialog();

    deepEqual([
        ['GET', {persist: 'id', ids: ['2', '3'], rtype: 'rtype.1,rtype.2'}],
        ['POST', {'URI-SEARCH': {persist: 'id', ids: ['2', '3'], rtype: 'rtype.1,rtype.2'}}]
    ], this.mockBackendUrlCalls('mock/emails/sync/link'));

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.brick.emailsync-link (link)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emailsync-brick'],
        header: [
            '<a data-action="emailsync-link" href="mock/emails/sync/link" __rtypes="rtype.1,rtype.2">'
               + '<script type="application/json" class="brick-action-data">'
                   + '{"data": {"rtypes": "rtype.1,rtype.2"}}'
               + '</script>'
          + '</a>'
        ]
    }).brick();

    var selections = brick.table().selections();
    var element = brick.element();
    var link = $('a[data-action="emailsync-link"]', element);

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, ['1', '2']);
    equal(2, selections.selected().length);

    link.click();

    equal(false, brick.isLoading());

    deepEqual([
        ['GET', {persist: 'id', ids: ['2', '3'], rtype: 'rtype.1,rtype.2'}]
    ], this.mockBackendUrlCalls('mock/emails/sync/link'));

    this.assertOpenedDialog();
    this.submitFormDialog();
    this.assertClosedDialog();

    deepEqual([
        ['GET', {persist: 'id', ids: ['2', '3'], rtype: 'rtype.1,rtype.2'}],
        ['POST', {'URI-SEARCH': {persist: 'id', ids: ['2', '3'], rtype: 'rtype.1,rtype.2'}}]
    ], this.mockBackendUrlCalls('mock/emails/sync/link'));

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.brick.emailsync-action (empty selector)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emailsync-brick']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    brick.action('emailsync-action', 'mock/emails/sync/action').start();

    equal(false, brick.isLoading());

    this.assertOpenedAlertDialog(gettext('Nothing is selected.'));
    this.closeDialog();

    deepEqual([], this.mockBackendCalls());
});

QUnit.test('creme.emails.brick.emailsync-action', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emailsync-brick']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, ['1', '2']);
    equal(2, selections.selected().length);

    brick.action('emailsync-action', 'mock/emails/sync/action').start();

    equal(false, brick.isLoading());
    deepEqual([
        ['POST', {ids: ['2', '3']}]
    ], this.mockBackendUrlCalls('mock/emails/sync/action'));

    this.assertOpenedDialog(gettext('Process done'));
    this.closeDialog();

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.brick.emailsync-action (fail)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emailsync-brick']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, ['1', '2']);
    equal(2, selections.selected().length);

    brick.action('emailsync-action', 'mock/emails/sync/action/fail').start();

    equal(false, brick.isLoading());
    deepEqual([
        ['POST', {ids: ['2', '3']}]
    ], this.mockBackendUrlCalls('mock/emails/sync/action/fail'));

    this.assertOpenedDialog(gettext('Bad Request'));
    this.closeDialog();

    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.brick.emailsync-action (link)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emailsync-brick'],
        header: [
            '<a data-action="emailsync-action" href="mock/emails/sync/action"></a>'
        ]
    }).brick();

    var selections = brick.table().selections();
    var element = brick.element();
    var link = $('a[data-action="emailsync-action"]', element);

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, ['1', '2']);
    equal(2, selections.selected().length);

    link.click();

    equal(false, brick.isLoading());
    deepEqual([
        ['POST', {ids: ['2', '3']}]
    ], this.mockBackendUrlCalls('mock/emails/sync/action'));

    this.assertOpenedDialog(gettext('Process done'));
    this.closeDialog();

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.brick.emailsync-delete (empty selection)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emailsync-brick']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    brick.action('emailsync-delete', 'mock/emails/sync/delete').start();

    equal(false, brick.isLoading());

    this.assertOpenedAlertDialog(gettext('Nothing is selected.'));
    this.closeDialog();

    deepEqual([], this.mockBackendCalls());
});

QUnit.test('creme.emails.brick.emailsync-delete', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emailsync-brick']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, ['1', '2']);
    equal(2, selections.selected().length);

    brick.action('emailsync-delete', 'mock/emails/sync/delete').start();

    equal(false, brick.isLoading());
    deepEqual([
        ['POST', {ids: '2,3'}]
    ], this.mockBackendUrlCalls('mock/emails/sync/delete'));

    this.assertOpenedDialog(gettext('Process done'));
    this.closeDialog();

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.brick.emailsync-delete (fail)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emailsync-brick']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, ['1', '2']);
    equal(2, selections.selected().length);

    brick.action('emailsync-delete', 'mock/emails/sync/delete/fail').start();

    equal(false, brick.isLoading());
    deepEqual([
        ['POST', {ids: '2,3'}]
    ], this.mockBackendUrlCalls('mock/emails/sync/delete/fail'));

    this.assertOpenedDialog(gettext('Bad Request'));
    this.closeDialog();

    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.brick.emailsync-delete (link)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emailsync-brick'],
        header: [
            '<a data-action="emailsync-delete" href="mock/emails/sync/delete"></a>'
        ]
    }).brick();

    var selections = brick.table().selections();
    var element = brick.element();
    var link = $('a[data-action="emailsync-delete"]', element);

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, ['1', '2']);
    equal(2, selections.selected().length);

    link.click();

    equal(false, brick.isLoading());
    deepEqual([
        ['POST', {ids: '2,3'}]
    ], this.mockBackendUrlCalls('mock/emails/sync/delete'));

    this.assertOpenedDialog(gettext('Process done'));
    this.closeDialog();

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.brick.email-toggle-image', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-email-brick'],
        header: [
            '<a data-action="email-toggle-images"></a>'
        ],
        content: [
            '<iframe data-html-field src="/mock/emails/content"></iframe>'
        ]
    }).brick();

    var element = brick.element();
    var link = $('a[data-action="email-toggle-images"]', element);

    equal('/mock/emails/content', $('iframe', element).attr('src'));

    link.click();

    equal('/mock/emails/content?external_img=on', $('iframe', element).attr('src'));

    link.click();

    equal('/mock/emails/content', $('iframe', element).attr('src'));
});

}(jQuery));
