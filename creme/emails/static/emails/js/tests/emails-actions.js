/* eslint operator-linebreak: ["error", "before"] */
/* global QUnitDetailViewMixin */

(function($) {

QUnit.module("creme.emails.brick.actions", new QUnitMixin(QUnitEventMixin,
                                                          QUnitAjaxMixin,
                                                          QUnitBrickMixin,
                                                          QUnitDialogMixin,
                                                          QUnitDetailViewMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        this.setMockBackendGET({
            'mock/emails/sync/link': function(url, data, options) {
                var html = ('<form action="${url}?${params}">'
                               + '<input type="submit" />'
                          + '</form>').template({
                              url: url,
                              params: _.encodeURLSearch(data)
                          });

                return backend.response(200, html);
            },
            'mock/emails/linkto': backend.response(200, '<form></form>')
        });

        this.setMockBackendPOST({
            'mock/emails/sync/link': backend.response(200, ''),
//            'mock/emails/sync/action': backend.response(200, ''),
            'mock/emails/sync/accept': backend.response(200, ''),
//            'mock/emails/sync/action/fail': backend.response(400, ''),
            'mock/emails/sync/accept/fail': backend.response(400, ''),
            'mock/emails/sync/accept/some_errors': backend.responseJSON(
                409, {count: 2, errors: ['A conflict error happened.']}
            ),
            'mock/emails/sync/delete': backend.response(200, ''),
            'mock/emails/sync/delete/some_errors': backend.responseJSON(
                409, {count: 2, errors: ['A conflict error happened.']}
            ),
            'mock/emails/sync/delete/fail': backend.response(400, ''),
            'mock/emails/linkto': backend.response(200, '')
        });
    },

    createEmailBrickTable: function(options) {
        options = $.extend({
            id: 'emails-test',
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

QUnit.test('creme.emails.brick.emailsync-accept-multi (empty selector)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emails_to_sync-brick'],
        deps: ['emails.emailtosync']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    assert.equal(false, brick.isLoading());
    this.assertClosedDialog();

    brick.action('emailsync-accept-multi', 'mock/emails/sync/accept').start();

    assert.equal(false, brick.isLoading());

    this.assertOpenedAlertDialog(gettext('No email is selected.'));
    this.closeDialog();

    assert.deepEqual([], this.mockBackendCalls());
});

QUnit.test('creme.emails.brick.emailsync-accept-multi', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emails_to_sync-brick'],
        deps: ['emails.emailtosync']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    assert.equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, ['1', '2']);
    assert.equal(2, selections.selected().length);

    brick.action('emailsync-accept-multi', 'mock/emails/sync/accept').start();

    this.assertOpenedConfirmDialog();
    this.acceptConfirmDialog();

    assert.equal(false, brick.isLoading());
    assert.deepEqual(
        this.mockBackendUrlCalls('mock/emails/sync/accept'),
        [
            ['POST', {ids: '2,3'}]
        ]
    );

    assert.deepEqual(
        this.mockBackendUrlCalls('mock/brick/all/reload'),
        [
            ['GET', {brick_id: ['emails-test'], extra_data: '{}'}]
        ]
    );
});

QUnit.test('creme.emails.brick.emailsync-accept-multi (error 400)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emails_to_sync-brick']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    assert.equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, ['1', '2']);
    assert.equal(2, selections.selected().length);

    brick.action('emailsync-accept-multi', 'mock/emails/sync/accept/fail').start();

    this.assertOpenedConfirmDialog();
    this.acceptConfirmDialog();

    assert.equal(false, brick.isLoading());
    assert.deepEqual(
        this.mockBackendUrlCalls('mock/emails/sync/accept/fail'),
        [
            ['POST', {ids: '2,3'}]
        ]
     );

    // TODO: improve this.assertOpenedDialog()?
    var dialogs = $('.ui-dialog');
    assert.equal(1, dialogs.length, 'is dialog opened');
    assert.equal(dialogs.first().find('span.header').text(), gettext('Bad Request'));
    assert.equal(dialogs.first().find('p.message').text(), gettext('Some errors occurred.'));

    this.closeDialog();

    assert.deepEqual(
        this.mockBackendUrlCalls('mock/brick/all/reload'),
        [
            ['GET', {brick_id: ['emails-test'], extra_data: '{}'}]
        ]
    );
});

QUnit.test('creme.emails.brick.emailsync-accept-multi (partial error)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emails_to_sync-brick']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    assert.equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, ['1', '2']);
    assert.equal(2, selections.selected().length);

    brick.action('emailsync-accept-multi', 'mock/emails/sync/accept/some_errors').start();

    this.assertOpenedConfirmDialog();
    this.acceptConfirmDialog();

    assert.equal(false, brick.isLoading());
    assert.deepEqual(
        this.mockBackendUrlCalls('mock/emails/sync/accept/some_errors'),
        [
            ['POST', {ids: '2,3'}]
        ]
     );

    var dialogs = $('.ui-dialog');
    assert.equal(1, dialogs.length, 'is dialog opened');

    assert.equal(
        dialogs.first().find('span.header').text(),
        ngettext('%d email has been synchronised', '%d emails have been synchronised', 1).format(1)
        + ' - '
        + ngettext('%d email cannot be synchronised.', '%d emails cannot be synchronised.', 1).format(1)
    );
    assert.equal(dialogs.first().find('p.message').html(), '<ul><li>A conflict error happened.</li></ul>');

    this.closeDialog();

    assert.deepEqual(
        this.mockBackendUrlCalls('mock/brick/all/reload'),
        [
            ['GET', {brick_id: ['emails-test'], extra_data: '{}'}]
        ]
    );
});

QUnit.test('creme.emails.brick.emailsync-accept-multi (link)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emails_to_sync-brick'],
        header: [
            '<a data-action="emailsync-accept-multi" href="mock/emails/sync/accept"></a>'
        ]
    }).brick();

    var selections = brick.table().selections();
    var element = brick.element();
    var link = $('a[data-action="emailsync-accept-multi"]', element);

    this.assertBrickTableItems([], selections.selected());

    assert.equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, ['1', '2']);
    assert.equal(2, selections.selected().length);

    link.trigger('click');
    this.assertOpenedConfirmDialog();
    this.acceptConfirmDialog();

    assert.equal(false, brick.isLoading());
    assert.deepEqual(
        this.mockBackendUrlCalls('mock/emails/sync/accept'),
        [
            ['POST', {ids: '2,3'}]
        ]
    );

    assert.deepEqual(
        this.mockBackendUrlCalls('mock/brick/all/reload'),
        [
            ['GET', {brick_id: ['emails-test'], extra_data: '{}'}]
        ]
    );
});

QUnit.test('creme.emails.brick.emailsync-delete-multi (empty selector)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emails_to_sync-brick'],
        deps: ['emails.emailtosync']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    assert.equal(false, brick.isLoading());
    this.assertClosedDialog();

    brick.action('emailsync-delete-multi', 'mock/emails/sync/delete').start();

    assert.equal(false, brick.isLoading());

    this.assertOpenedAlertDialog(gettext('No email is selected.'));
    this.closeDialog();

    assert.deepEqual([], this.mockBackendCalls());
});

QUnit.test('creme.emails.brick.emailsync-delete-multi', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emails_to_sync-brick'],
        deps: ['emails.emailtosync']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    assert.equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, ['1', '2']);
    assert.equal(2, selections.selected().length);

    brick.action('emailsync-delete-multi', 'mock/emails/sync/delete').start();

    this.assertOpenedConfirmDialog();
    this.acceptConfirmDialog();

    assert.equal(false, brick.isLoading());
    assert.deepEqual(
        this.mockBackendUrlCalls('mock/emails/sync/delete'),
        [
            ['POST', {ids: '2,3'}]
        ]
    );

    assert.deepEqual(
        this.mockBackendUrlCalls('mock/brick/all/reload'),
        [
            ['GET', {brick_id: ['emails-test'], extra_data: '{}'}]
        ]
    );
});

QUnit.test('creme.emails.brick.emailsync-delete-multi (error 400)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emails_to_sync-brick']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    assert.equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, ['1', '2']);
    assert.equal(2, selections.selected().length);

    brick.action('emailsync-delete-multi', 'mock/emails/sync/delete/fail').start();

    this.assertOpenedConfirmDialog();
    this.acceptConfirmDialog();

    assert.equal(false, brick.isLoading());
    assert.deepEqual(
        this.mockBackendUrlCalls('mock/emails/sync/delete/fail'),
        [
            ['POST', {ids: '2,3'}]
        ]
     );

    // TODO: improve this.assertOpenedDialog()?
    var dialogs = $('.ui-dialog');
    assert.equal(1, dialogs.length, 'is dialog opened');
    assert.equal(dialogs.first().find('span.header').text(), gettext('Bad Request'));
    assert.equal(dialogs.first().find('p.message').text(), gettext('Some errors occurred.'));

    this.closeDialog();

    assert.deepEqual(
        this.mockBackendUrlCalls('mock/brick/all/reload'),
        [
            ['GET', {brick_id: ['emails-test'], extra_data: '{}'}]
        ]
    );
});

QUnit.test('creme.emails.brick.emailsync-delete-multi (partial error)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emails_to_sync-brick']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    assert.equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, ['1', '2']);
    assert.equal(2, selections.selected().length);

    brick.action('emailsync-delete-multi', 'mock/emails/sync/delete/some_errors').start();

    this.assertOpenedConfirmDialog();
    this.acceptConfirmDialog();

    assert.equal(false, brick.isLoading());
    assert.deepEqual(
        this.mockBackendUrlCalls('mock/emails/sync/delete/some_errors'),
        [
            ['POST', {ids: '2,3'}]
        ]
     );

    var dialogs = $('.ui-dialog');
    assert.equal(1, dialogs.length, 'is dialog opened');

    assert.equal(
        dialogs.first().find('span.header').text(),
        ngettext('%d email has been deleted', '%d emails have been deleted', 1).format(1)
        + ' - '
        + ngettext('%d email cannot be deleted.', '%d emails cannot be deleted.', 1).format(1)
    );
    assert.equal(dialogs.first().find('p.message').html(), '<ul><li>A conflict error happened.</li></ul>');

    this.closeDialog();

    assert.deepEqual(
        this.mockBackendUrlCalls('mock/brick/all/reload'),
        [
            ['GET', {brick_id: ['emails-test'], extra_data: '{}'}]
        ]
    );
});

QUnit.test('creme.emails.brick.emailsync-delete-multi (link)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emails_to_sync-brick'],
        header: [
            '<a data-action="emailsync-delete-multi" href="mock/emails/sync/delete"></a>'
        ]
    }).brick();

    var selections = brick.table().selections();
    var element = brick.element();
    var link = $('a[data-action="emailsync-delete-multi"]', element);

    this.assertBrickTableItems([], selections.selected());

    assert.equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, ['1', '2']);
    assert.equal(2, selections.selected().length);

    link.trigger('click');
    this.assertOpenedConfirmDialog();
    this.acceptConfirmDialog();

    assert.equal(false, brick.isLoading());
    assert.deepEqual(
        this.mockBackendUrlCalls('mock/emails/sync/delete'),
        [
            ['POST', {ids: '2,3'}]
        ]
    );

    assert.deepEqual(
        this.mockBackendUrlCalls('mock/brick/all/reload'),
        [
            ['GET', {brick_id: ['emails-test'], extra_data: '{}'}]
        ]
    );
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

    assert.equal('/mock/emails/content', $('iframe', element).attr('src'));

    link.trigger('click');

    assert.equal('/mock/emails/content?external_img=on', $('iframe', element).attr('src'));

    link.trigger('click');

    assert.equal('/mock/emails/content', $('iframe', element).attr('src'));
});

QUnit.test('creme.emails.LinkEMailToAction', function(assert) {
    this.createBrickWidget({
        deps: ['creme_core.relation']
    }).brick();

    var action = new creme.emails.LinkEMailToAction({
        url: 'mock/emails/linkto',
        rtypes: ['rtype.1', 'rtype.5', 'rtype.78'],
        ids: '12'
    }).on({
        'cancel': this.mockListener('action-cancel'),
        'done': this.mockListener('action-done')
    });

    action.start();

    assert.deepEqual([
        ['GET', {rtype: ['rtype.1', 'rtype.5', 'rtype.78'], ids: '12'}]
    ], this.mockBackendUrlCalls('mock/emails/linkto'));

    this.assertOpenedDialog();
    assert.deepEqual([], this.mockListenerCalls('action-done'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.submitFormDialog();

    this.assertClosedDialog();
    assert.deepEqual([['done']], this.mockListenerCalls('action-done'));

    assert.deepEqual([
        ['GET', {rtype: ['rtype.1', 'rtype.5', 'rtype.78'], ids: '12'}],
        ['POST', {
            rtype: ['rtype.1', 'rtype.5', 'rtype.78'],
            ids: ['12']
        }]
    ], this.mockBackendUrlCalls('mock/emails/linkto'));

    assert.deepEqual([
        ['GET', {"brick_id": ["creme_core-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.LinkEMailToAction (cancel)', function(assert) {
    this.createBrickWidget({
        deps: ['creme_core.relation']
    }).brick();

    var action = new creme.emails.LinkEMailToAction({
        url: 'mock/emails/linkto',
        rtypes: ['rtype.1', 'rtype.5', 'rtype.78'],
        ids: '12'
    }).on({
        'cancel': this.mockListener('action-cancel'),
        'done': this.mockListener('action-done')
    });

    action.start();

    assert.deepEqual([
        ['GET', {rtype: ['rtype.1', 'rtype.5', 'rtype.78'], ids: '12'}]
    ], this.mockBackendUrlCalls('mock/emails/linkto'));

    this.assertOpenedDialog();
    assert.deepEqual([], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.closeDialog();
    this.assertClosedDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));

    assert.deepEqual([
        ['GET', {rtype: ['rtype.1', 'rtype.5', 'rtype.78'], ids: '12'}]
    ], this.mockBackendUrlCalls('mock/emails/linkto'));

    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.hatmenubar.emails-hatmenubar-linkto', function(assert) {
    this.createBrickWidget({
        deps: ['creme_core.relation']
    }).brick();

    var widget = this.createButtonsBrick({
        buttons: [
            this.createHatMenuActionButton({
                url: 'mock/emails/linkto',
                action: 'emails-hatmenubar-linkto',
                data: {
                    rtypes: ['rtype.1', 'rtype.5', 'rtype.78'],
                    ids: '12'
                }
            })
        ]
    });

    $(widget.element).find('a.menu_button').trigger('click');

    assert.deepEqual([
        ['GET', {rtype: ['rtype.1', 'rtype.5', 'rtype.78'], ids: '12'}]
    ], this.mockBackendUrlCalls('mock/emails/linkto'));

    this.assertOpenedDialog();
    assert.deepEqual([], this.mockListenerCalls('action-done'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.submitFormDialog();

    this.assertClosedDialog();

    assert.deepEqual([
        ['GET', {rtype: ['rtype.1', 'rtype.5', 'rtype.78'], ids: '12'}],
        ['POST', {
            rtype: ['rtype.1', 'rtype.5', 'rtype.78'],
            ids: ['12']
        }]
    ], this.mockBackendUrlCalls('mock/emails/linkto'));

    assert.deepEqual([
        ['GET', {"brick_id": ["creme_core-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

}(jQuery));
