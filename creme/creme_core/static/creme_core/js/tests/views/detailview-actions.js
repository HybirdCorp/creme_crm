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
            id: 'selection-list'
        }));

        this.setListviewReloadContent('selection-list', selectionListHtml);

        this.setMockBackendGET({
            'mock/merge/selection': backend.response(200, selectionListHtml),
            'mock/merge/selection/fail': backend.response(400, '')
        });

        this.setMockBackendPOST({
            'mock/merge': backend.response(200, ''),
            'mock/clone': backend.response(200, 'mock/clone-redir'),
            'mock/delete': backend.response(200, 'mock/trash'),
            'mock/restore': backend.response(200, 'mock/restore-redir')
        });
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
        ['GET', {id1: '157', whoami: '1000'}]
    ], this.mockBackendUrlCalls('mock/merge/selection'));

    var list = this.assertOpenedListViewDialog().data('list_view');

    deepEqual([], list.getSelectedEntitiesAsArray());

    this.submitListViewSelectionDialog(list);

    this.assertOpenedAlertDialog(gettext('Please select at least one entity.'));
    this.assertOpenedListViewDialog();

    this.closeTopDialog();
    this.assertOpenedListViewDialog();

    this.closeDialog();

    deepEqual([
        ['GET', {id1: '157', whoami: '1000'}]
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
        ['GET', {id1: '157', whoami: '1000'}]
    ], this.mockBackendUrlCalls('mock/merge/selection'));

    var list = this.assertOpenedListViewDialog().data('list_view');

    this.setListviewSelection(list, ['2', '3']);

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

    this.submitListViewSelectionDialog(list);

    this.assertOpenedAlertDialog(gettext('Please select only one entity.'));
    this.assertOpenedListViewDialog();

    this.closeTopDialog();
    this.assertOpenedListViewDialog();

    this.closeDialog();

    deepEqual([
        ['GET', {id1: '157', whoami: '1000'}]
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
        ['GET', {id1: '157', whoami: '1000'}]
    ], this.mockBackendUrlCalls('mock/merge/selection'));

    var list = this.assertOpenedListViewDialog().data('list_view');

    this.setListviewSelection(list, ['2']);

    equal(1, list.countEntities());
    deepEqual(['2'], list.getSelectedEntitiesAsArray());

    this.submitListViewSelectionDialog(list);
    this.assertClosedDialog();

    deepEqual([
        'mock/merge?id1=157&id2=2'
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
        ['GET', {id1: '157', whoami: '1000'}]
    ], this.mockBackendUrlCalls('mock/merge/selection'));

    this.assertOpenedListViewDialog();
    this.findDialogButtonsByLabel(gettext('Cancel')).click();
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
    }).on('fail', this.mockListener('fail')).start();

    deepEqual([
        ['GET', {id1: '157', whoami: '1000'}]
    ], this.mockBackendUrlCalls('mock/merge/selection/fail'));

    this.assertOpenedAlertDialog(gettext('Error during loading the page.'));
    this.closeDialog();

    deepEqual([['fail', '']],
        this.mockListenerCalls('fail').map(function(e) {
            return e.slice(0, 2);
        }));
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

}(jQuery));
