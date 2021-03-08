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
            'mock/listview/selection/multiple': backend.response(200, multiSelectionListHtml)
        });
    }
}));

QUnit.test('creme.listview.ListViewDialog (none)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        url: 'mock/listview/selection/none',
        selectionMode: 'none'
    });

    equal('none', dialog.selectionMode());
    equal(false, dialog.isSelectable());
    equal(false, dialog.isMultiple());
    equal(false, dialog.isSingle());

    equal(false, dialog.isOpened());
    equal(true, Object.isNone(dialog.controller()));
    deepEqual([], dialog.selected());

    deepEqual([], this.mockBackendUrlCalls('mock/listview/selection/none'));

    dialog.open();

    equal(true, dialog.isOpened());
    equal(1, dialog.buttons().find('button').length);

    var lines = dialog.content().find('tr.lv-row');
    var controller = dialog.controller();

    equal(false, Object.isNone(controller));
    equal(false, controller.isSelectionEnabled());
    equal(false, controller.isSingleSelectionMode());
    equal(false, controller.isMultipleSelectionMode());
    deepEqual([], dialog.selected());

    deepEqual([
        ['GET', {selection: 'none'}]
    ], this.mockBackendUrlCalls('mock/listview/selection/none'));

    $(lines[0]).trigger('click');

    deepEqual([], dialog.selected());

    lines.trigger('click');

    deepEqual([], dialog.selected());

    dialog.button('close').trigger('click');
    equal(false, dialog.isOpened());
});

QUnit.test('creme.listview.ListViewDialog (multiple)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        url: 'mock/listview/selection/multiple',
        selectionMode: 'multiple'
    });

    equal('multiple', dialog.selectionMode());
    equal(true, dialog.isSelectable());
    equal(true, dialog.isMultiple());
    equal(false, dialog.isSingle());

    equal(false, dialog.isOpened());
    equal(true, Object.isNone(dialog.controller()));
    deepEqual([], dialog.selected());

    deepEqual([], this.mockBackendUrlCalls('mock/listview/selection/multiple'));

    dialog.open();

    equal(true, dialog.isOpened());
    equal(2, dialog.buttons().find('button').length);

    var lines = dialog.content().find('tr.lv-row');
    var controller = dialog.controller();

    equal(false, Object.isNone(controller));
    equal(true, controller.isSelectionEnabled());
    equal(false, controller.isSingleSelectionMode());
    equal(true, controller.isMultipleSelectionMode());
    deepEqual([], dialog.selected());

    deepEqual([
        ['GET', {selection: 'multiple'}]
    ], this.mockBackendUrlCalls('mock/listview/selection/multiple'));

    $(lines[0]).trigger('click');

    deepEqual(['1'], dialog.selected());

    lines.trigger('click');

    deepEqual(['2', '3'], dialog.selected());
});

QUnit.test('creme.listview.ListViewDialog (multiple, close)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        url: 'mock/listview/selection/multiple',
        selectionMode: 'multiple'
    });

    dialog.onValidate(this.mockListener('validate'));
    dialog.open();

    equal(true, dialog.isOpened());
    equal(2, dialog.buttons().find('button').length);
    deepEqual([], dialog.selected());
    deepEqual([], this.mockListenerCalls('validate'));

    dialog.button('close').trigger('click');

    equal(false, dialog.isOpened());
    deepEqual([], this.mockListenerCalls('validate'));
});

QUnit.test('creme.listview.ListViewDialog (multiple, validate)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        url: 'mock/listview/selection/single',
        selectionMode: 'single'
    });

    dialog.onValidate(this.mockListener('validate'));
    dialog.open();

    var lines = dialog.content().find('tr.lv-row');

    equal(true, dialog.isOpened());
    equal(2, dialog.buttons().find('button').length);
    deepEqual([], dialog.selected());
    deepEqual([], this.mockListenerCalls('validate'));

    dialog.button('validate').trigger('click');

    this.assertOpenedAlertDialog(gettext("Please select at least one entity."));
    equal(true, dialog.isOpened());
    deepEqual([], this.mockListenerCalls('validate'));

    this.closeTopDialog();
    equal(true, dialog.isOpened());

    $(lines[0]).trigger('click');

    deepEqual(['1'], dialog.selected());

    dialog.button('validate').trigger('click');
    equal(false, dialog.isOpened());
    deepEqual([
        ['validate', ['1']]
    ], this.mockListenerCalls('validate'));
});

QUnit.test('creme.listview.ListViewDialog (single)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        url: 'mock/listview/selection/single'
    });

    equal('single', dialog.selectionMode());
    equal(true, dialog.isSelectable());
    equal(false, dialog.isMultiple());
    equal(true, dialog.isSingle());

    equal(false, dialog.isOpened());
    equal(true, Object.isNone(dialog.controller()));
    deepEqual([], dialog.selected());

    deepEqual([], this.mockBackendUrlCalls('mock/listview/selection/single'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload/single'));

    dialog.open();

    equal(true, dialog.isOpened());
    equal(2, dialog.buttons().find('button').length);

    var lines = dialog.content().find('tr.lv-row');
    var controller = dialog.controller();

    equal(false, Object.isNone(controller));
    equal(true, controller.isSelectionEnabled());
    equal(true, controller.isSingleSelectionMode());
    equal(false, controller.isMultipleSelectionMode());
    deepEqual([], dialog.selected());

    deepEqual([
        ['GET', {selection: 'single'}]
    ], this.mockBackendUrlCalls('mock/listview/selection/single'));

    $(lines[0]).trigger('click');

    deepEqual(['1'], dialog.selected());

    lines.trigger('click');

    deepEqual(['3'], dialog.selected());
});

QUnit.test('creme.listview.ListViewDialog (single, close)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        url: 'mock/listview/selection/single',
        selectionMode: 'single'
    });

    dialog.onValidate(this.mockListener('validate'));
    dialog.open();

    equal(true, dialog.isOpened());
    equal(2, dialog.buttons().find('button').length);
    deepEqual([], dialog.selected());
    deepEqual([], this.mockListenerCalls('validate'));

    dialog.button('close').trigger('click');

    equal(false, dialog.isOpened());
    deepEqual([], this.mockListenerCalls('validate'));
});

QUnit.test('creme.listview.ListViewDialog (single, validate)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        url: 'mock/listview/selection/multiple',
        selectionMode: 'multiple'
    });

    dialog.onValidate(this.mockListener('validate'));
    dialog.open();

    var lines = dialog.content().find('tr.lv-row');

    equal(true, dialog.isOpened());
    equal(2, dialog.buttons().find('button').length);
    deepEqual([], dialog.selected());
    deepEqual([], this.mockListenerCalls('validate'));

    dialog.button('validate').trigger('click');

    this.assertOpenedAlertDialog(gettext("Please select at least one entity."));
    equal(true, dialog.isOpened());
    deepEqual([], this.mockListenerCalls('validate'));

    this.closeTopDialog();
    equal(true, dialog.isOpened());

    $(lines[0]).trigger('click');

    deepEqual(['1'], dialog.selected());

    dialog.button('validate').trigger('click');
    equal(false, dialog.isOpened());
    deepEqual([
        ['validate', ['1']]
    ], this.mockListenerCalls('validate'));
});

QUnit.test('creme.listview.ListViewDialog (empty title)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        url: 'mock/listview/selection/multiple'
    });

    dialog.open();

    equal(true, Object.isEmpty(dialog.options.title));
    this.assertDialogTitle('Multi-Selection List − Sub-title (1 / 3)');
    equal(0, dialog.content().find('.list-title:not(.hidden)').length);
});

QUnit.test('creme.listview.ListViewDialog (with title)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        title: 'My title',
        url: 'mock/listview/selection/multiple'
    });

    dialog.open();

    equal(false, Object.isEmpty(dialog.options.title));
    this.assertDialogTitle('My title − Sub-title (1 / 3)');
    equal(1, dialog.content().find('.list-title.hidden').length);
});

QUnit.test('creme.listview.ListViewDialog (with title, disabled)', function(assert) {
    var dialog = new creme.lv_widget.ListViewDialog({
        title: 'My title',
        url: 'mock/listview/selection/multiple',
        useListTitle: false
    });

    dialog.open();

    equal(false, Object.isEmpty(dialog.options.title));
    this.assertDialogTitle('My title');
    equal(1, dialog.content().find('.list-title:not(.hidden)').length);
});

}(jQuery));
