(function($) {

QUnit.module("creme.listview.dialog", new QUnitMixin(QUnitEventMixin,
                                                     QUnitAjaxMixin,
                                                     QUnitDialogMixin,
                                                     QUnitListViewMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        var noneSelectionListHtml = this.createListViewHtml(this.defaultListViewHtmlOptions({
            title: 'No-Selection List',
            reloadurl: 'mock/listview/reload/none',
            mode: 'none'
        }));
        var singleSelectionListHtml = this.createListViewHtml(this.defaultListViewHtmlOptions({
            title: 'Single-Selection List',
            reloadurl: 'mock/listview/reload/single',
            mode: 'single'
        }));
        var multiSelectionListHtml = this.createListViewHtml(this.defaultListViewHtmlOptions({
            title: 'Multi-Selection List',
            subtitle: 'Sub-title',
            titlestats: '(1 / 3)',
            reloadurl: 'mock/listview/reload/multiple',
            mode: 'multiple'
        }));

        this.setListviewReloadResponse(noneSelectionListHtml, 'none');
        this.setListviewReloadResponse(singleSelectionListHtml, 'single');
        this.setListviewReloadResponse(multiSelectionListHtml, 'multiple');

        this.setMockBackendGET({
            'mock/listview/selection/none': backend.response(200, noneSelectionListHtml),
            'mock/listview/selection/single': backend.response(200, singleSelectionListHtml),
            'mock/listview/selection/multiple': backend.response(200, multiSelectionListHtml),
            'mock/listview/selection/invalid': backend.response(403, 'Not allowed')
        });
    }
}));

QUnit.test('creme.listview.ListViewDialog (none)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        url: 'mock/listview/selection/none',
        selectionMode: 'none'
    });

    assert.equal('none', dialog.selectionMode());
    assert.equal(false, dialog.isSelectable());
    assert.equal(false, dialog.isMultiple());
    assert.equal(false, dialog.isSingle());

    assert.equal(false, dialog.isOpened());
    assert.equal(true, Object.isNone(dialog.controller()));
    assert.deepEqual([], dialog.selected());

    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/selection/none'));

    dialog.open();

    assert.equal(true, dialog.isOpened());
    assert.equal(1, dialog.buttons().find('button').length);

    var lines = dialog.content().find('tr.lv-row');
    var controller = dialog.controller();

    assert.equal(false, Object.isNone(controller));
    assert.equal(false, controller.isSelectionEnabled());
    assert.equal(false, controller.isSingleSelectionMode());
    assert.equal(false, controller.isMultipleSelectionMode());
    assert.deepEqual([], dialog.selected());

    assert.deepEqual([
        ['GET', {selection: 'none'}]
    ], this.mockBackendUrlCalls('mock/listview/selection/none'));

    $(lines[0]).trigger('click');

    assert.deepEqual([], dialog.selected());

    lines.trigger('click');

    assert.deepEqual([], dialog.selected());

    dialog.button('close').trigger('click');
    assert.equal(false, dialog.isOpened());
});

QUnit.test('creme.listview.ListViewDialog (multiple)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        url: 'mock/listview/selection/multiple',
        selectionMode: 'multiple'
    });

    assert.equal('multiple', dialog.selectionMode());
    assert.equal(true, dialog.isSelectable());
    assert.equal(true, dialog.isMultiple());
    assert.equal(false, dialog.isSingle());

    assert.equal(false, dialog.isOpened());
    assert.equal(true, Object.isNone(dialog.controller()));
    assert.deepEqual([], dialog.selected());

    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/selection/multiple'));

    dialog.open();

    assert.equal(true, dialog.isOpened());
    assert.equal(2, dialog.buttons().find('button').length);

    var lines = dialog.content().find('tr.lv-row');
    var controller = dialog.controller();

    assert.equal(false, Object.isNone(controller));
    assert.equal(true, controller.isSelectionEnabled());
    assert.equal(false, controller.isSingleSelectionMode());
    assert.equal(true, controller.isMultipleSelectionMode());
    assert.deepEqual([], dialog.selected());

    assert.deepEqual([
        ['GET', {selection: 'multiple'}]
    ], this.mockBackendUrlCalls('mock/listview/selection/multiple'));

    $(lines[0]).trigger('click');

    assert.deepEqual(['1'], dialog.selected());

    lines.trigger('click');

    assert.deepEqual(['2', '3'], dialog.selected());
});

QUnit.test('creme.listview.ListViewDialog (multiple, close)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        url: 'mock/listview/selection/multiple',
        selectionMode: 'multiple'
    });

    dialog.onValidate(this.mockListener('validate'));
    dialog.open();

    assert.equal(true, dialog.isOpened());
    assert.equal(2, dialog.buttons().find('button').length);
    assert.deepEqual([], dialog.selected());
    assert.deepEqual([], this.mockListenerCalls('validate'));

    dialog.button('close').trigger('click');

    assert.equal(false, dialog.isOpened());
    assert.deepEqual([], this.mockListenerCalls('validate'));
});

QUnit.test('creme.listview.ListViewDialog (multiple, validate)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        url: 'mock/listview/selection/single',
        selectionMode: 'single'
    });

    dialog.onValidate(this.mockListener('validate'));
    dialog.open();

    var lines = dialog.content().find('tr.lv-row');

    assert.equal(true, dialog.isOpened());
    assert.equal(2, dialog.buttons().find('button').length);
    assert.deepEqual([], dialog.selected());
    assert.deepEqual([], this.mockListenerCalls('validate'));

    dialog.button('validate').trigger('click');

    this.assertOpenedAlertDialog(gettext("Please select at least one entity."));
    assert.equal(true, dialog.isOpened());
    assert.deepEqual([], this.mockListenerCalls('validate'));

    this.closeTopDialog();
    assert.equal(true, dialog.isOpened());

    $(lines[0]).trigger('click');

    assert.deepEqual(['1'], dialog.selected());

    dialog.button('validate').trigger('click');
    assert.equal(false, dialog.isOpened());
    assert.deepEqual([
        ['validate', ['1']]
    ], this.mockListenerCalls('validate'));
});

QUnit.test('creme.listview.ListViewDialog (single)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        url: 'mock/listview/selection/single'
    });

    assert.equal('single', dialog.selectionMode());
    assert.equal(true, dialog.isSelectable());
    assert.equal(false, dialog.isMultiple());
    assert.equal(true, dialog.isSingle());

    assert.equal(false, dialog.isOpened());
    assert.equal(true, Object.isNone(dialog.controller()));
    assert.deepEqual([], dialog.selected());

    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/selection/single'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/listview/reload/single'));

    dialog.open();

    assert.equal(true, dialog.isOpened());
    assert.equal(2, dialog.buttons().find('button').length);

    var lines = dialog.content().find('tr.lv-row');
    var controller = dialog.controller();

    assert.equal(false, Object.isNone(controller));
    assert.equal(true, controller.isSelectionEnabled());
    assert.equal(true, controller.isSingleSelectionMode());
    assert.equal(false, controller.isMultipleSelectionMode());
    assert.deepEqual([], dialog.selected());

    assert.deepEqual([
        ['GET', {selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/listview/selection/single'));

    $(lines[0]).trigger('click');

    assert.deepEqual(['1'], dialog.selected());

    lines.trigger('click');

    assert.deepEqual(['3'], dialog.selected());
});

QUnit.test('creme.listview.ListViewDialog (single, close)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        url: 'mock/listview/selection/single',
        selectionMode: 'single'
    });

    dialog.onValidate(this.mockListener('validate'));
    dialog.open();

    assert.equal(true, dialog.isOpened());
    assert.equal(2, dialog.buttons().find('button').length);
    assert.deepEqual([], dialog.selected());
    assert.deepEqual([], this.mockListenerCalls('validate'));

    dialog.button('close').trigger('click');

    assert.equal(false, dialog.isOpened());
    assert.deepEqual([], this.mockListenerCalls('validate'));
});

QUnit.test('creme.listview.ListViewDialog (single, validate)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        url: 'mock/listview/selection/multiple',
        selectionMode: 'multiple'
    });

    dialog.onValidate(this.mockListener('validate'));
    dialog.open();

    var lines = dialog.content().find('tr.lv-row');

    assert.equal(true, dialog.isOpened());
    assert.equal(2, dialog.buttons().find('button').length);
    assert.deepEqual([], dialog.selected());
    assert.deepEqual([], this.mockListenerCalls('validate'));

    dialog.button('validate').trigger('click');

    this.assertOpenedAlertDialog(gettext("Please select at least one entity."));
    assert.equal(true, dialog.isOpened());
    assert.deepEqual([], this.mockListenerCalls('validate'));

    this.closeTopDialog();
    assert.equal(true, dialog.isOpened());

    $(lines[0]).trigger('click');

    assert.deepEqual(['1'], dialog.selected());

    dialog.button('validate').trigger('click');
    assert.equal(false, dialog.isOpened());
    assert.deepEqual([
        ['validate', ['1']]
    ], this.mockListenerCalls('validate'));
});

QUnit.test('creme.listview.ListViewDialog (single, invalid)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        url: 'mock/listview/selection/invalid',
        selectionMode: 'single'
    });

    dialog.open();

    assert.equal(true, dialog.isOpened());
    assert.equal(1, dialog.buttons().find('button').length);
    assert.deepEqual([], dialog.selected());
    assert.deepEqual([], this.mockListenerCalls('validate'));

    dialog.button('close').trigger('click');

    assert.equal(false, dialog.isOpened());
    assert.deepEqual([], this.mockListenerCalls('validate'));
});

QUnit.test('creme.listview.ListViewDialog (multiple, invalid)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        url: 'mock/listview/selection/invalid',
        selectionMode: 'multiple'
    });

    dialog.open();

    assert.equal(true, dialog.isOpened());
    assert.equal(1, dialog.buttons().find('button').length);
    assert.deepEqual([], dialog.selected());
    assert.deepEqual([], this.mockListenerCalls('validate'));

    dialog.button('close').trigger('click');

    assert.equal(false, dialog.isOpened());
    assert.deepEqual([], this.mockListenerCalls('validate'));
});

QUnit.test('creme.listview.ListViewDialog (empty title)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        url: 'mock/listview/selection/multiple'
    });

    dialog.open();

    assert.equal(true, Object.isEmpty(dialog.options.title));
    this.assertDialogTitle('Multi-Selection List − Sub-title (1 / 3)');
    assert.equal(0, dialog.content().find('.list-title:not(.hidden)').length);
});

QUnit.test('creme.listview.ListViewDialog (with title)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        title: 'My title',
        url: 'mock/listview/selection/multiple'
    });

    dialog.open();

    assert.equal(false, Object.isEmpty(dialog.options.title));
    this.assertDialogTitle('My title − Sub-title (1 / 3)');
    assert.equal(1, dialog.content().find('.list-title.hidden').length);
});

QUnit.test('creme.listview.ListViewDialog (with title, disabled)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        title: 'My title',
        url: 'mock/listview/selection/multiple',
        useListTitle: false
    });

    dialog.open();

    assert.equal(false, Object.isEmpty(dialog.options.title));
    this.assertDialogTitle('My title');
    assert.equal(1, dialog.content().find('.list-title:not(.hidden)').length);
});

}(jQuery));
