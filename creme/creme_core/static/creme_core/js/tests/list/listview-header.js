(function($) {

QUnit.module("creme.lv_widget.ListViewHeader", new QUnitMixin(QUnitEventMixin, QUnitAjaxMixin, QUnitDialogMixin, QUnitListViewMixin));

QUnit.test('creme.lv_widget.ListViewHeader.bind', function(assert) {
    var list = $(this.createListViewHtml()).appendTo(this.qunitFixture());
    var header = new creme.lv_widget.ListViewHeader();
//    var table = list.find('table:first');
    var table = list.find('table').first();

    equal(false, header.isBound());
    equal(false, header._isStandalone);
    equal(undefined, header._list);
    equal(undefined, header._floatAnchor);
    equal(false, table.is('floated'));
    equal(0, $('.floated-header-anchor').length);

    header.bind(table);

    equal(true, header.isBound());
    equal(1, header._list.length);
    equal(undefined, header._floatAnchor);
    equal(false, table.is('floated'));
    equal(0, $('.floated-header-anchor').length);
});

QUnit.test('creme.lv_widget.ListViewHeader.bind (already bound)', function(assert) {
    var list = $(this.createListViewHtml()).appendTo(this.qunitFixture());
//    var header = new creme.lv_widget.ListViewHeader().bind(list.find('table:first'));
    var header = new creme.lv_widget.ListViewHeader().bind(list.find('table').first());

    equal(true, header.isBound());
    this.assertRaises(function() {
        header.bind(list);
    }, Error, 'Error: ListViewHeader is already bound');
});

QUnit.test('creme.lv_widget.ListViewHeader.bind (standalone)', function(assert) {
    $(document).scrollTop(0);

    // attachment to body is need for a correct scrollTop position
    var list = $(this.createListViewHtml()).appendTo($('body'));

    try {
        var header = new creme.lv_widget.ListViewHeader({
            standalone: true,
            headTop: 35
        });
//        var table = list.find('table:first');
        var table = list.find('table').first();

        equal(true, header._isStandalone);
        equal(35, header._headTop);

        header.bind(table);

        equal(true, header.isBound());
        equal(1, header._list.length);
        equal(1, header._floatAnchor.length);
        equal(1, $('.floated-header-anchor').length);

        equal(false, table.is('.floated'));
    } finally {
        list.detach();
    }
});

QUnit.test('creme.lv_widget.ListViewHeader.bind (standalone, already floating)', function(assert) {
    var list = $(this.createListViewHtml()).appendTo(this.qunitFixture());
    var header = new creme.lv_widget.ListViewHeader({
        standalone: true,
        headTop: 35
    });
//    var table = list.find('table:first');
    var table = list.find('table').first();

    table.offset({top: -10});

    header.bind(table);

    equal(true, header.isBound());
    equal(1, header._list.length);
    equal(1, header._floatAnchor.length);
    equal(1, $('.floated-header-anchor').length);

    equal(true, table.is('.floated'));
});

QUnit.test('creme.lv_widget.ListViewHeader (enter first row)', function(assert) {
    var list = $(this.createListViewHtml(this.defaultListViewHtmlOptions())).appendTo(this.qunitFixture());
    var header = new creme.lv_widget.ListViewHeader();
//    var table = list.find('table:first');
    var table = list.find('table').first();

    header.bind(table);

    var lines = $(list).find('tr.selectable:first-child');

    equal(false, $('.listview.floatThead-table').is('.first-row-hovered'));
    equal(false, table.is('.first-row-hovered'));

    $(lines[1]).trigger($.Event("mouseenter"));

    equal(false, $('.listview.floatThead-table').is('.first-row-hovered'));
    equal(false, table.is('.first-row-hovered'));

    $(lines[2]).trigger($.Event("mouseenter"));

    equal(false, $('.listview.floatThead-table').is('.first-row-hovered'));
    equal(false, table.is('.first-row-hovered'));

    $(lines[0]).trigger($.Event("mouseenter"));

    equal(false, $('.listview.floatThead-table').is('.first-row-hovered'));
    equal(true, table.is('.first-row-hovered'));
});

QUnit.test('creme.lv_widget.ListViewHeader (enter first row, standalone)', function(assert) {
    var list = $(this.createListViewHtml(this.defaultListViewHtmlOptions())).appendTo(this.qunitFixture()); // 1-col + 3-rows
    var header = new creme.lv_widget.ListViewHeader({
        standalone: true,
        headTop: 35
    });
//    var table = list.find('table:first');
    var table = list.find('table').first();

    header.bind(table);

    var lines = $(list).find('tr.selectable:first-child');

    equal(false, $('.listview.floatThead-table').is('.first-row-hovered'));
    equal(false, table.is('.first-row-hovered'));

    $(lines[1]).trigger($.Event("mouseenter"));

    equal(false, $('.listview.floatThead-table').is('.first-row-hovered'));
    equal(false, table.is('.first-row-hovered'));

    $(lines[2]).trigger($.Event("mouseenter"));

    equal(false, $('.listview.floatThead-table').is('.first-row-hovered'));
    equal(false, table.is('.first-row-hovered'));

    $(lines[0]).trigger($.Event("mouseenter"));

    equal(true, $('.listview.floatThead-table').is('.first-row-hovered'));
    equal(true, table.is('.first-row-hovered'));
});

QUnit.test('creme.lv_widget.ListViewHeader (leave first row)', function(assert) {
    var list = $(this.createListViewHtml(this.defaultListViewHtmlOptions())).appendTo(this.qunitFixture());
    var header = new creme.lv_widget.ListViewHeader();
//    var table = list.find('table:first');
    var table = list.find('table').first();

    header.bind(table);

    var lines = $(list).find('tr.selectable:first-child');

    $(lines[0]).trigger($.Event("mouseenter"));

    equal(false, $('.listview.floatThead-table').is('.first-row-hovered'));
    equal(true, table.is('.first-row-hovered'));

    $(lines[0]).trigger($.Event("mouseleave"));

    equal(false, $('.listview.floatThead-table').is('.first-row-hovered'));
    equal(false, table.is('.first-row-hovered'));
});

QUnit.test('creme.lv_widget.ListViewHeader (leave first row, standalone)', function(assert) {
    var list = $(this.createListViewHtml(this.defaultListViewHtmlOptions())).appendTo(this.qunitFixture()); // 1-col + 3-rows
    var header = new creme.lv_widget.ListViewHeader({
        standalone: true,
        headTop: 35
    });
//    var table = list.find('table:first');
    var table = list.find('table').first();

    header.bind(table);

    var lines = $(list).find('tr.selectable:first-child');

    $(lines[0]).trigger($.Event("mouseenter"));

    equal(true, $('.listview.floatThead-table').is('.first-row-hovered'));
    equal(true, table.is('.first-row-hovered'));

    $(lines[0]).trigger($.Event("mouseleave"));

    equal(false, $('.listview.floatThead-table').is('.first-row-hovered'));
    equal(false, table.is('.first-row-hovered'));
});

QUnit.test('creme.lv_widget.ListViewHeader (selection change)', function(assert) {
    var list = $(
        this.createListViewHtml(this.defaultListViewHtmlOptions())
    ).appendTo(this.qunitFixture());
    var header = new creme.lv_widget.ListViewHeader();
//    var table = list.find('table:first');
    var table = list.find('table').first();

    header.bind(table);

    var lines = $(list).find('tr.selectable:first-child');

    equal(false, $('.listview.floatThead-table').is('.first-row-hovered'));
    equal(false, table.is('.first-row-selected'));

    $(lines[1]).trigger('row-selection-changed', {selected: true});

    equal(false, $('.listview.floatThead-table').is('.first-row-selected'));
    equal(false, table.is('.first-row-selected'));

    $(lines[2]).trigger('row-selection-changed', {selected: true});

    equal(false, $('.listview.floatThead-table').is('.first-row-selected'));
    equal(false, table.is('.first-row-selected'));

    $(lines[0]).trigger('row-selection-changed', {selected: true});

    equal(false, $('.listview.floatThead-table').is('.first-row-selected'));
    equal(true, table.is('.first-row-selected'));

    $(lines[0]).trigger('row-selection-changed', {selected: false});

    equal(false, $('.listview.floatThead-table').is('.first-row-selected'));
    equal(false, table.is('.first-row-selected'));
});

QUnit.test('creme.lv_widget.ListViewHeader (selection change, standalone)', function(assert) {
    var list = $(this.createListViewHtml(this.defaultListViewHtmlOptions())).appendTo(this.qunitFixture());
    var header = new creme.lv_widget.ListViewHeader({
        standalone: true,
        headTop: 35
    });
//    var table = list.find('table:first');
    var table = list.find('table').first();

    header.bind(table);

    var lines = $(list).find('tr.selectable:first-child');

    equal(false, $('.listview.floatThead-table').is('.first-row-selected'));
    equal(false, table.is('.first-row-selected'));

    $(lines[1]).trigger('row-selection-changed', {selected: true});

    equal(false, $('.listview.floatThead-table').is('.first-row-selected'));
    equal(false, table.is('.first-row-selected'));

    $(lines[2]).trigger('row-selection-changed', {selected: true});

    equal(false, $('.listview.floatThead-table').is('.first-row-selected'));
    equal(false, table.is('.first-row-selected'));

    $(lines[0]).trigger('row-selection-changed', {selected: true});

    equal(true, $('.listview.floatThead-table').is('.first-row-selected'));
    equal(true, table.is('.first-row-selected'));

    $(lines[0]).trigger('row-selection-changed', {selected: false});

    equal(false, $('.listview.floatThead-table').is('.first-row-selected'));
    equal(false, table.is('.first-row-selected'));
});

}(jQuery));
