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
                              params: creme.ajax.param(data)
                          });

                return backend.response(200, html);
            },
            'mock/emails/linkto': backend.response(200, '<form></form>')
        });

        this.setMockBackendPOST({
            'mock/emails/sync/link': backend.response(200, ''),
            'mock/emails/sync/action': backend.response(200, ''),
            'mock/emails/sync/action/fail': backend.response(400, ''),
            'mock/emails/sync/delete': backend.response(200, ''),
            'mock/emails/sync/delete/fail': backend.response(400, ''),
            'mock/emails/linkto': backend.response(200, '')
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

QUnit.test('creme.emails.brick.emailsync-link (multi, empty selector)', function(assert) {
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

QUnit.test('creme.emails.brick.emailsync-link (multi)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emailsync-brick'],
        deps: ['creme_core.relation.rtype.1']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, ['1', '2']);
    equal(2, selections.selected().length);

    brick.action('emailsync-link', 'mock/emails/sync/link', {}, {
        rtypes: ['rtype.1', 'rtype.2']
    }).start();

    equal(false, brick.isLoading());

    deepEqual([
        ['GET', {ids: ['2', '3'], rtype: ['rtype.1', 'rtype.2']}]
    ], this.mockBackendUrlCalls('mock/emails/sync/link'));

    this.assertOpenedDialog();
    this.submitFormDialog();
    this.assertClosedDialog();

    deepEqual([
        ['GET', {ids: ['2', '3'], rtype: ['rtype.1', 'rtype.2']}],
        ['POST', {
            'URI-SEARCH': {ids: ['2', '3'], rtype: ['rtype.1', 'rtype.2']},
            ids: ['2', '3'],
            rtype: ['rtype.1', 'rtype.2']
        }]
    ], this.mockBackendUrlCalls('mock/emails/sync/link'));

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.brick.emailsync-link (single)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emailsync-brick'],
        deps: ['creme_core.relation.rtype.1']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    brick.action('emailsync-link', 'mock/emails/sync/link', {}, {
        rtypes: ['rtype.1', 'rtype.2'],
        id: 13
    }).start();

    equal(false, brick.isLoading());

    deepEqual([
        ['GET', {ids: [13], rtype: ['rtype.1', 'rtype.2']}]
    ], this.mockBackendUrlCalls('mock/emails/sync/link'));

    this.assertOpenedDialog();
    this.submitFormDialog();
    this.assertClosedDialog();

    deepEqual([
        ['GET', {ids: [13], rtype: ['rtype.1', 'rtype.2']}],
        ['POST', {
            'URI-SEARCH': {ids: "13", rtype: ['rtype.1', 'rtype.2']},
            ids: [13],
            rtype: ['rtype.1', 'rtype.2']
        }]
    ], this.mockBackendUrlCalls('mock/emails/sync/link'));

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.brick.emailsync-link (multi, link)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emailsync-brick'],
        deps: ['creme_core.relation.rtype.1'],
        header: [
            '<a data-action="emailsync-link" href="mock/emails/sync/link">'
               + '<script type="application/json" class="brick-action-data"><!--'
                   + '{"data": {"rtypes": ["rtype.1", "rtype.2"]}}'
               + '--></script>'
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

    link.trigger('click');

    equal(false, brick.isLoading());

    deepEqual([
        ['GET', {ids: ['2', '3'], rtype: ['rtype.1', 'rtype.2']}]
    ], this.mockBackendUrlCalls('mock/emails/sync/link'));

    this.assertOpenedDialog();
    this.submitFormDialog();
    this.assertClosedDialog();

    deepEqual([
        ['GET', {ids: ['2', '3'], rtype: ['rtype.1', 'rtype.2']}],
        ['POST', {
            'URI-SEARCH': {ids: ['2', '3'], rtype: ['rtype.1', 'rtype.2']},
            ids: ['2', '3'],
            rtype: ['rtype.1', 'rtype.2']
        }]
    ], this.mockBackendUrlCalls('mock/emails/sync/link'));

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.brick.emailsync-link (row, link)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emailsync-brick'],
        deps: ['creme_core.relation.rtype.1'],
        rows: [
            '<tr>'
              + '<td data-selectable-selector-column><input value="1" type="check"></input></td>'
              + '<td data-type="date">2017-05-08</td>'
              + '<td>'
                  + '<a data-action="emailsync-link" href="mock/emails/sync/link">'
                      + '<script type="application/json" class="brick-action-data"><!--'
                          + '{"data": {"rtypes": ["rtype.1", "rtype.2"], "id": 137}}'
                      + '--></script>'
                  + '</a>'
              + '</td>'
          + '</tr>'
        ]
    }).brick();

    var element = brick.element();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    $('a[data-action="emailsync-link"]', element).trigger('click');

    equal(false, brick.isLoading());

    deepEqual([
        ['GET', {ids: [137], rtype: ['rtype.1', 'rtype.2']}]
    ], this.mockBackendUrlCalls('mock/emails/sync/link'));

    this.assertOpenedDialog();
    this.submitFormDialog();
    this.assertClosedDialog();

    deepEqual([
        ['GET', {ids: [137], rtype: ['rtype.1', 'rtype.2']}],
        ['POST', {
            'URI-SEARCH': {ids: "137", rtype: ['rtype.1', 'rtype.2']},
            ids: [137],
            rtype: ['rtype.1', 'rtype.2']
        }]
    ], this.mockBackendUrlCalls('mock/emails/sync/link'));

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.brick.emailsync-action (empty selector)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emailsync-brick'],
        deps: ['creme_core.relation.rtype.1']
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
        classes: ['emails-emailsync-brick'],
        deps: ['creme_core.relation.rtype.1']
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

    link.trigger('click');

    equal(false, brick.isLoading());
    deepEqual([
        ['POST', {ids: ['2', '3']}]
    ], this.mockBackendUrlCalls('mock/emails/sync/action'));

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


QUnit.test('creme.emails.brick.emailsync-delete (canceled)', function(assert) {
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

    this.assertOpenedConfirmDialog();
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

    this.assertOpenedConfirmDialog();
    this.acceptConfirmDialog();

    equal(false, brick.isLoading());
    deepEqual([
        ['POST', {ids: '2,3'}]
    ], this.mockBackendUrlCalls('mock/emails/sync/delete'));

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.brick.emailsync-delete (single)', function(assert) {
    var brick = this.createEmailBrickTable({
        classes: ['emails-emailsync-brick']
    }).brick();
    var selections = brick.table().selections();

    this.assertBrickTableItems([], selections.selected());

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    this.toggleBrickTableRows(brick, ['1', '2']);
    equal(2, selections.selected().length);

    brick.action('emailsync-delete', 'mock/emails/sync/delete', {}, {
        id: 13
    }).start();

    this.assertOpenedConfirmDialog();
    this.acceptConfirmDialog();

    equal(false, brick.isLoading());
    deepEqual([
        ['POST', {ids: '13'}]
    ], this.mockBackendUrlCalls('mock/emails/sync/delete'));

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

    this.assertOpenedConfirmDialog();
    this.acceptConfirmDialog();

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

    link.trigger('click');

    this.assertOpenedConfirmDialog();
    this.acceptConfirmDialog();

    equal(false, brick.isLoading());
    deepEqual([
        ['POST', {ids: '2,3'}]
    ], this.mockBackendUrlCalls('mock/emails/sync/delete'));

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

    link.trigger('click');

    equal('/mock/emails/content?external_img=on', $('iframe', element).attr('src'));

    link.trigger('click');

    equal('/mock/emails/content', $('iframe', element).attr('src'));
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

    deepEqual([
        ['GET', {rtype: ['rtype.1', 'rtype.5', 'rtype.78'], ids: '12'}]
    ], this.mockBackendUrlCalls('mock/emails/linkto'));

    this.assertOpenedDialog();
    deepEqual([], this.mockListenerCalls('action-done'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.submitFormDialog();

    this.assertClosedDialog();
    deepEqual([['done']], this.mockListenerCalls('action-done'));

    deepEqual([
        ['GET', {rtype: ['rtype.1', 'rtype.5', 'rtype.78'], ids: '12'}],
        ['POST', {
            rtype: ['rtype.1', 'rtype.5', 'rtype.78'],
            ids: ['12']
        }]
    ], this.mockBackendUrlCalls('mock/emails/linkto'));

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
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

    deepEqual([
        ['GET', {rtype: ['rtype.1', 'rtype.5', 'rtype.78'], ids: '12'}]
    ], this.mockBackendUrlCalls('mock/emails/linkto'));

    this.assertOpenedDialog();
    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.closeDialog();
    this.assertClosedDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));

    deepEqual([
        ['GET', {rtype: ['rtype.1', 'rtype.5', 'rtype.78'], ids: '12'}]
    ], this.mockBackendUrlCalls('mock/emails/linkto'));

    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.emails.hatmenubar.emails-hatmenubar-linkto', function(assert) {
    this.createBrickWidget({
        deps: ['creme_core.relation']
    }).brick();

    var widget = this.createHatMenuBar({
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

    deepEqual([
        ['GET', {rtype: ['rtype.1', 'rtype.5', 'rtype.78'], ids: '12'}]
    ], this.mockBackendUrlCalls('mock/emails/linkto'));

    this.assertOpenedDialog();
    deepEqual([], this.mockListenerCalls('action-done'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.submitFormDialog();

    this.assertClosedDialog();

    deepEqual([
        ['GET', {rtype: ['rtype.1', 'rtype.5', 'rtype.78'], ids: '12'}],
        ['POST', {
            rtype: ['rtype.1', 'rtype.5', 'rtype.78'],
            ids: ['12']
        }]
    ], this.mockBackendUrlCalls('mock/emails/linkto'));

    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

}(jQuery));
