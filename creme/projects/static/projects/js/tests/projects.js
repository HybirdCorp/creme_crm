/* global QUnitDetailViewMixin */
(function($) {

QUnit.module("creme.projects.hatmenubar.actions", new QUnitMixin(QUnitEventMixin,
                                                                 QUnitAjaxMixin,
                                                                 QUnitListViewMixin,
                                                                 QUnitDialogMixin,
                                                                 QUnitDetailViewMixin, {
    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendPOST({
            'mock/projects/12/close': backend.response(200, ''),
            'mock/projects/12/close/fail': backend.response(400, 'Unable to close project')
        });
    }
}));

QUnit.test('creme.projects.hatmenubar.close (not confirmed)', function(assert) {
    var widget = this.createHatMenuBar({
        buttons: [
            this.createHatMenuActionButton({
                url: 'mock/projects/12/close',
                action: 'projects-hatmenubar-close'
            })
        ]
    });

    $(widget.element).find('a.menu_button').trigger('click');

    this.assertOpenedConfirmDialog(gettext('Do you really want to close this project?'));

    this.closeDialog();

    deepEqual([], this.mockBackendUrlCalls('/mock/projects/12/close'));
    deepEqual([], this.mockReloadCalls());
});

QUnit.test('creme.projects.hatmenubar.close (fail)', function(assert) {
    var widget = this.createHatMenuBar({
        buttons: [
            this.createHatMenuActionButton({
                url: 'mock/projects/12/close/fail',
                action: 'projects-hatmenubar-close'
            })
        ]
    });

    $(widget.element).find('a.menu_button').trigger('click');

    this.assertOpenedConfirmDialog(gettext('Do you really want to close this project?'));

    this.acceptConfirmDialog();

    this.assertOpenedAlertDialog('Unable to close project');
    this.closeDialog();

    deepEqual([], this.mockBackendUrlCalls('mock/projects/12/close'));
    deepEqual([], this.mockReloadCalls());
});

QUnit.test('creme.projects.hatmenubar.close', function(assert) {
    var current_url = window.location.href;
    var widget = this.createHatMenuBar({
        buttons: [
            this.createHatMenuActionButton({
                url: 'mock/projects/12/close',
                action: 'projects-hatmenubar-close'
            })
        ]
    });

    $(widget.element).find('a.menu_button').trigger('click');

    this.assertOpenedConfirmDialog(gettext('Do you really want to close this project?'));

    this.acceptConfirmDialog();

    this.assertClosedDialog();
    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/projects/12/close'));
    deepEqual([current_url], this.mockReloadCalls());
});

QUnit.test('creme.projects.listview.actions (projects-close, cancel)', function(assert) {
    var list = this.createDefaultListView().controller();
    var registry = list.actionBuilders();

    var builder = registry.get('projects-close');

    ok(Object.isFunc(builder));
    var action = builder('mock/projects/12/close');

    action.start();

    this.assertOpenedConfirmDialog(gettext('Do you really want to close this project?'));
    this.closeDialog();

    deepEqual([], this.mockBackendUrlCalls('mock/projects/12/close'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.projects.listview.actions (projects-close, ok)', function(assert) {
    var list = this.createDefaultListView().controller();
    var registry = list.actionBuilders();

    var builder = registry.get('projects-close');

    ok(Object.isFunc(builder));
    var action = builder('mock/projects/12/close');

    action.start();

    this.assertOpenedConfirmDialog(gettext('Do you really want to close this project?'));

    this.acceptConfirmDialog();

    this.assertClosedDialog();

    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/projects/12/close'));
    deepEqual([
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

QUnit.test('creme.projects.listview.actions (projects-close, fail)', function(assert) {
    var list = this.createDefaultListView().controller();
    var registry = list.actionBuilders();

    var builder = registry.get('projects-close');

    ok(Object.isFunc(builder));
    var action = builder('mock/projects/12/close/fail');

    action.start();

    this.assertOpenedConfirmDialog(gettext('Do you really want to close this project?'));

    this.acceptConfirmDialog();

    this.assertOpenedAlertDialog('Unable to close project');
    this.closeDialog();

    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/projects/12/close/fail'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

}(jQuery));
