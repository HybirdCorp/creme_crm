/* eslint operator-linebreak: ["error", "before"] */
/* global QUnitDetailViewMixin QUnitWidgetMixin */

(function($) {

QUnit.module("creme.persons.actions", new QUnitMixin(QUnitEventMixin,
                                                     QUnitAjaxMixin,
                                                     QUnitBrickMixin,
                                                     QUnitDialogMixin,
                                                     QUnitWidgetMixin,
                                                     QUnitDetailViewMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        this.setMockBackendPOST({
            'mock/relation/add': backend.response(200, ''),
            'mock/relation/add/default': backend.response(200, ''),
            'mock/relation/add/fail': backend.response(400, 'Unable to add relation')
        });

        this.mockActionListeners = {
            start: this.mockListener('action-start'),
            cancel: this.mockListener('action-cancel'),
            fail: this.mockListener('action-fail'),
            done: this.mockListener('action-done')
        };

        $('body').attr('data-save-relations-url', 'mock/relation/add/default');
    }
}));

QUnit.test('creme.persons.BecomeAction (no orga)', function(assert) {
    var action = new creme.persons.BecomeAction({
        rtype: 'rtype.12',
        subject: '79'
    }).on(this.mockActionListeners);

    action.start();

    this.assertClosedDialog();

    assert.deepEqual([], this.mockBackendUrlCalls());

    assert.deepEqual({
        'action-start': [['start']],
        'action-cancel': [['cancel']]
    }, this.mockListenerCalls());
});

QUnit.test('creme.persons.BecomeAction (single orga)', function(assert) {
    var action = new creme.persons.BecomeAction({
        rtype: 'rtype.12',
        subject: '79',
        url: 'mock/relation/add',
        organisations: [{value: '8', label: 'Orga #8'}]
    }).on(this.mockActionListeners);

    action.start();

    this.assertClosedDialog();

    assert.deepEqual([
        ['mock/relation/add', 'POST', {entities: '8', predicate_id: 'rtype.12', subject_id: '79'}]
    ], this.mockBackendUrlCalls());

    assert.deepEqual({
        'action-start': [['start']],
        'action-done': [['done']]
    }, this.mockListenerCalls());
});

QUnit.test('creme.persons.BecomeAction (single orga, default url)', function(assert) {
    var action = new creme.persons.BecomeAction({
        rtype: 'rtype.12',
        subject: '79',
        organisations: [{value: '8', label: 'Orga #8'}]
    }).on(this.mockActionListeners);

    action.start();

    this.assertClosedDialog();

    assert.deepEqual([
        ['mock/relation/add/default', 'POST', {entities: '8', predicate_id: 'rtype.12', subject_id: '79'}]
    ], this.mockBackendUrlCalls());

    assert.deepEqual({
        'action-start': [['start']],
        'action-done': [['done']]
    }, this.mockListenerCalls());
});

QUnit.test('creme.persons.BecomeAction (single orga, failed)', function(assert) {
    var action = new creme.persons.BecomeAction({
        rtype: 'rtype.12',
        subject: '79',
        url: 'mock/relation/add/fail',
        organisations: [{value: '8', label: 'Orga #8'}]
    }).on(this.mockActionListeners);

    action.start();

    this.assertOpenedDialog();
    assert.deepEqual([
        ['mock/relation/add/fail', 'POST', {entities: '8', predicate_id: 'rtype.12', subject_id: '79'}]
    ], this.mockBackendUrlCalls());
    assert.deepEqual({
        'action-start': [['start']]
    }, this.mockListenerCalls());

    this.closeDialog();

    assert.deepEqual({
        'action-start': [['start']],
        'action-fail': [['fail', 'Unable to add relation']]
    }, this.mockListenerCalls());
});

QUnit.test('creme.persons.BecomeAction (multi orga, canceled)', function(assert) {
    var action = new creme.persons.BecomeAction({
        rtype: 'rtype.12',
        subject: '79',
        url: 'mock/relation/add',
        organisations: [
            {value: '8', label: 'Orga #8'}, {value: '9', label: 'Orga #9'}
        ]
    }).on(this.mockActionListeners);

    action.start();

    var dialog = this.assertOpenedDialog();

    this.assertDialogTitle(gettext('Organisation'));
    assert.ok(dialog.html().indexOf(gettext('Select the concerned organisation.')) !== -1);
    assert.deepEqual({
        'action-start': [['start']]
    }, this.mockListenerCalls());

    this.closeDialog();

    assert.deepEqual([], this.mockBackendUrlCalls());
    assert.deepEqual({
        'action-start': [['start']],
        'action-cancel': [['cancel']]
    }, this.mockListenerCalls());
});

QUnit.test('creme.persons.BecomeAction (multi orga, failed)', function(assert) {
    var action = new creme.persons.BecomeAction({
        rtype: 'rtype.12',
        subject: '79',
        url: 'mock/relation/add/fail',
        organisations: [
            {value: '8', label: 'Orga #8'}, {value: '9', label: 'Orga #9'}
        ]
    }).on(this.mockActionListeners);

    action.start();

    var dialog = this.assertOpenedDialog();

    this.assertDialogTitle(gettext('Organisation'));
    assert.ok(dialog.html().indexOf(gettext('Select the concerned organisation.')) !== -1);
    assert.equal('8', dialog.find('select').val());
    assert.deepEqual({
        'action-start': [['start']]
    }, this.mockListenerCalls());

    dialog.find('select').val('9');
    this.acceptConfirmDialog();

    this.assertOpenedDialog();
    assert.deepEqual([
        ['mock/relation/add/fail', 'POST', {entities: '9', predicate_id: 'rtype.12', subject_id: '79'}]
    ], this.mockBackendUrlCalls());
    assert.deepEqual({
        'action-start': [['start']]
    }, this.mockListenerCalls());

    this.closeDialog();

    assert.deepEqual([
        ['mock/relation/add/fail', 'POST', {entities: '9', predicate_id: 'rtype.12', subject_id: '79'}]
    ], this.mockBackendUrlCalls());
    assert.deepEqual({
        'action-start': [['start']],
        'action-fail': [['fail', 'Unable to add relation']]
    }, this.mockListenerCalls());
});

QUnit.test('creme.persons.BecomeAction (multi orga, ok)', function(assert) {
    var action = new creme.persons.BecomeAction({
        rtype: 'rtype.12',
        subject: '79',
        url: 'mock/relation/add',
        organisations: [
            {value: '8', label: 'Orga #8'}, {value: '9', label: 'Orga #9'}
        ]
    }).on(this.mockActionListeners);

    action.start();

    var dialog = this.assertOpenedDialog();

    this.assertDialogTitle(gettext('Organisation'));
    assert.ok(dialog.html().indexOf(gettext('Select the concerned organisation.')) !== -1);
    assert.equal('8', dialog.find('select').val());
    assert.deepEqual({
        'action-start': [['start']]
    }, this.mockListenerCalls());

    dialog.find('select').val('9');
    this.acceptConfirmDialog();

    this.assertClosedDialog();
    assert.deepEqual([
        ['mock/relation/add', 'POST', {entities: '9', predicate_id: 'rtype.12', subject_id: '79'}]
    ], this.mockBackendUrlCalls());
    assert.deepEqual({
        'action-start': [['start']],
        'action-done': [['done']]
    }, this.mockListenerCalls());
    assert.deepEqual([], this.mockReloadCalls());
});

QUnit.test('persons-hatmenubar-become', function(assert) {
    var widget = this.createButtonsBrick({
        buttons: [
            this.createHatMenuActionButton({
                action: 'persons-hatmenubar-become',
                url: 'mock/relation/add',
                data: {
                    subject_id: '74',
                    rtype_id: 'rtype.1',
                    organisations: [
                        {value: '8', label: 'Orga #8'},
                        {value: '9', label: 'Orga #9'}
                    ]
                }
            })
        ]
    });

    this.assertActive(widget.element);
    this.assertReady(widget.element);

/* TODO: (genglert) fix this part?
    assert.deepEqual(1, widget.delegate._actionlinks.length);

    var link = widget.delegate._actionlinks[0];

    assert.equal(true, link.isBound());
    assert.equal(false, link.isDisabled());
*/

    $(widget.element).find('a.menu_button').trigger('click');

    var dialog = this.assertOpenedDialog();

    this.assertDialogTitle(gettext('Organisation'));
    assert.ok(dialog.html().indexOf(gettext('Select the concerned organisation.')) !== -1);
    assert.equal('8', dialog.find('select').val());

    dialog.find('select').val('9');
    this.acceptConfirmDialog();

    this.assertClosedDialog();
    assert.deepEqual([
        ['mock/relation/add', 'POST', {entities: '9', predicate_id: 'rtype.1', subject_id: '74'}],
        ['mock/brick/all/reload', 'GET', {'brick_id': ['creme_core-test'], 'extra_data': '{}'}]
    ], this.mockBackendUrlCalls());
});

}(jQuery));
