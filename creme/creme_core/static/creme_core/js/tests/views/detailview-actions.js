(function($) {

QUnit.module("creme.detailview.brick.actions", new QUnitMixin(QUnitEventMixin,
                                                              QUnitAjaxMixin,
                                                              QUnitBrickMixin,
                                                              QUnitDialogMixin,
                                                              QUnitListViewMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        var selectionListHtml = this.createListViewHtml(this.defaultListViewHtmlOptions({
            reloadurl: 'mock/listview/reload/selection-list'
        }));

        this.setListviewReloadResponse(selectionListHtml, 'selection-list');

        this.setMockBackendGET({
            'mock/merge/selection': backend.response(200, selectionListHtml),
            'mock/merge/selection/fail': backend.response(400, ''),
            'mock/relation/selector': backend.response(200, selectionListHtml)
        });

        this.setMockBackendPOST({
            'mock/merge': backend.response(200, ''),
            'mock/clone': backend.response(200, 'mock/clone-redir'),
            'mock/delete': backend.response(200, 'mock/trash'),
            'mock/restore': backend.response(200, 'mock/restore-redir'),
            'mock/relation/add': backend.response(200, ''),
            'mock/relation/add/fail': backend.response(400, 'Unable to add relation')
        });

        $('body').attr('data-save-relations-url', 'mock/relation/add');
        $('body').attr('data-select-relations-objects-url', 'mock/relation/selector');
    },

    createHatBarBrick: function(options) {
        options = $.extend({
            classes: ['brick-hat']
        }, options || {});

        return this.createBrickWidget(options);
    }
}));

QUnit.test('creme.detailview.brick.detailview-merge (empty selector)', function(assert) {
    var brick = this.createHatBarBrick().brick();

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    brick.action('creme_core-detailview-merge', 'mock/merge', {}, {
        id: '157',
        selection_url: 'mock/merge/selection'
    }).start();

    deepEqual([
        ['GET', {id1: '157', selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/merge/selection'));

    var dialog = this.assertOpenedDialog();
    var list = dialog.find('.ui-creme-listview').data('list_view');

    deepEqual([], list.selectedRows());

    this.validateListViewSelectionDialog(dialog);

    this.assertOpenedDialogs(2);
    this.assertOpenedAlertDialog(gettext('Please select at least one entity.'));
    this.assertOpenedListViewDialog();

    this.closeTopDialog();
    this.assertOpenedDialog();

    this.closeDialog();

    deepEqual([
        ['mock/merge/selection', 'GET', {id1: '157', selection: 'single'}]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.detailview.brick.detailview-merge (multiple selections)', function(assert) {
    var brick = this.createHatBarBrick().brick();

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    brick.action('creme_core-detailview-merge', 'mock/merge', {}, {
        id: '157',
        selection_url: 'mock/merge/selection'
    }).start();

    deepEqual([
        ['GET', {id1: '157', selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/merge/selection'));

    var dialog = this.assertOpenedDialog();
    var list = dialog.find('.ui-creme-listview').data('list_view');

    this.setListviewSelection(list, ['2', '3']);

    equal(2, list.selectedRowsCount());
    deepEqual(['2', '3'], list.selectedRows());

    this.validateListViewSelectionDialog();

    this.assertOpenedDialogs(2);
    this.assertOpenedAlertDialog(gettext('Please select only one entity.'));
    this.assertOpenedListViewDialog();

    this.closeTopDialog();
    this.assertOpenedDialog();

    this.closeDialog();

    deepEqual([
        ['mock/merge/selection', 'GET', {id1: '157', selection: 'single'}]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.detailview.brick.detailview-merge (single selection)', function(assert) {
    var brick = this.createHatBarBrick().brick();

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    brick.action('creme_core-detailview-merge', 'mock/merge', {}, {
        id: '157',
        selection_url: 'mock/merge/selection'
    }).start();

    deepEqual([
        ['GET', {id1: '157', selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/merge/selection'));

    var dialog = this.assertOpenedDialog();
    var list = dialog.find('.ui-creme-listview').data('list_view');

    this.setListviewSelection(list, ['2']);

    equal(1, list.selectedRowsCount());
    deepEqual(['2'], list.selectedRows());

    this.validateListViewSelectionDialog();
    this.assertClosedDialog();

    deepEqual([
        '/mock/merge?id1=157&id2=2'
    ], this.mockRedirectCalls());
});

QUnit.test('creme.detailview.brick.detailview-merge (cancel)', function(assert) {
    var brick = this.createHatBarBrick().brick();

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    brick.action('creme_core-detailview-merge', 'mock/merge', {}, {
        id: '157',
        selection_url: 'mock/merge/selection'
    }).on('cancel', this.mockListener('cancel')).start();

    deepEqual([
        ['GET', {id1: '157', selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/merge/selection'));

    var dialog = this.assertOpenedDialog();
    this.findDialogButtonsByLabel(gettext('Cancel'), dialog).click();
    this.assertClosedDialog();

    deepEqual([['cancel']], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.detailview.brick.detailview-merge (fail)', function(assert) {
    var brick = this.createHatBarBrick().brick();

    equal(false, brick.isLoading());
    this.assertClosedDialog();

    brick.action('creme_core-detailview-merge', 'mock/merge/fail', {}, {
        id: '157',
        selection_url: 'mock/merge/selection/fail'
    }).on('cancel', this.mockListener('cancel')).start();

    deepEqual([
        ['GET', {id1: '157', selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/merge/selection/fail'));

    var dialog = this.assertOpenedDialog();
    equal(0, dialog.find('.ui-creme.listview').length);

    this.closeDialog();
    this.assertClosedDialog();

    deepEqual([['cancel']], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.detailview.brick.detailview-clone', function(assert) {
    var brick = this.createHatBarBrick().brick();

    brick.action('creme_core-detailview-clone', 'mock/clone').start();
    this.assertClosedDialog();

    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/clone'));
    deepEqual(['mock/clone-redir'], this.mockRedirectCalls());
});

QUnit.test('creme.detailview.brick.detailview-delete', function(assert) {
    var brick = this.createHatBarBrick().brick();

    brick.action('creme_core-detailview-delete', 'mock/delete').start();
    this.assertClosedDialog();

    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/delete'));
    deepEqual(['mock/trash'], this.mockRedirectCalls());
});

QUnit.test('creme.detailview.brick.detailview-restore', function(assert) {
    var brick = this.createHatBarBrick().brick();

    brick.action('creme_core-detailview-restore', 'mock/restore').start();
    this.assertClosedDialog();

    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/restore'));
    deepEqual(['mock/restore-redir'], this.mockRedirectCalls());
});

/*
QUnit.test('creme.relations.addRelationTo (multiple)', function(assert) {
    creme.relations.addRelationTo('74', 'rtypes.1', '5', {
        multiple: true
    });

    deepEqual([
        ['GET', {subject_id: '74', rtype_id: 'rtypes.1', objects_ct_id: '5'}]
    ], this.mockBackendUrlCalls('mock/relation/selector'));

    var list = this.assertOpenedListViewDialog().data('list_view');

    this.setListviewSelection(list, ['2', '3']);

    equal(2, list.selectedRowsCount());
    deepEqual(['2', '3'], list.selectedRows());

    this.submitListViewSelectionDialog(list);
    this.assertClosedDialog();

    deepEqual([
        ['GET', {subject_id: '74', rtype_id: 'rtypes.1', objects_ct_id: '5'}],
        ['POST', {entities: ['2', '3'], predicate_id: 'rtypes.1', subject_id: '74'}]
    ], this.mockBackendUrlCalls());
});
*/

/*
QUnit.test('creme.relations.addRelationTo (no select url)', function(assert) {
    $('body').removeAttr('data-select-relations-objects-url');

    var action = creme.relations.addRelationTo('74', 'rtypes.1', '5');

    equal(true, action.isStatusFail());
    this.assertClosedDialog();

    deepEqual([], this.mockBackendUrlCalls('mock/relation/selector'));
});
*/

/*
QUnit.test('creme.relations.addRelationTo (no addto url)', function(assert) {
    $('body').removeAttr('data-save-relations-url');

    var action = creme.relations.addRelationTo('74', 'rtypes.1', '5');

    equal(true, action.isStatusFail());
    this.assertClosedDialog();

    deepEqual([], this.mockBackendUrlCalls('mock/relation/selector'));
});
*/

}(jQuery));
