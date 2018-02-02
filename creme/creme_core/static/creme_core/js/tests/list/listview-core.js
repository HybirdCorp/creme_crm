QUnit.module("creme.listview.core", new QUnitMixin(QUnitEventMixin, QUnitAjaxMixin, QUnitListViewMixin));

QUnit.test('creme.listview.core', function(assert) {
    var element = $(this.createListViewHtml()).appendTo(this.anchor);
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), false);
    equal(listview.count(), 0);
    equal(listview.pager().isBound(), false);
    equal(listview.header().isBound(), false);
});

QUnit.test('creme.listview.core (standalone)', function(assert) {
    var element = $(this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload'
    })).appendTo(this.anchor);
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);
    equal(listview.pager().isBound(), false);
    equal(listview.header().isBound(), false);

    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
    equal(listview.controller().getReloadUrl(), 'mock/listview/reload');

    listview.controller().reload();

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            selected_rows: [''],
            selection: 'multiple',
            sort_field: ['regular_field-name'],
            sort_order: ['']
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.core (dialog)', function(assert) {
    var dialog = new creme.dialog.Dialog({url: 'mock/html', backend: this.backend});
    var html = this.createListViewHtml({
        reloadurl: 'mock/listview/reload'
    });

    dialog.open();
    dialog.content().parents('.ui-dialog-content:first').attr('id', '448712');
    dialog.fill(html);

    var listview = dialog.content().find('.ui-creme-listview:first').creme().widget();

    this.setListviewReloadContent('list', html);
    equal(listview.controller().getReloadUrl(), 'mock/listview/reload');

    equal(listview.isStandalone(), false);
    equal(listview.count(), 0);
    equal(listview.pager().isBound(), false);
    equal(listview.header().isBound(), false);
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    listview.controller().reload();

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            selected_rows: [''],
            selection: 'multiple',
            sort_field: ['regular_field-name'],
            sort_order: [''],
            whoami: '448712'
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.core (not empty)', function(assert) {
    var element = $(this.createListViewHtml(this.defaultListViewHtmlOptions())).appendTo(this.anchor);
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), false);
    equal(listview.count(), 3);
    equal(listview.pager().isBound(), true);
    equal(listview.header().isBound(), true);
});

QUnit.test('creme.listview.core (select)', function(assert) {
    var element = $(this.createListViewHtml(this.defaultListViewHtmlOptions())).appendTo(this.anchor);
    var listview = creme.widget.create(element);
    var table = element.find('table:first');
    var controller = listview.controller();
    var lines = table.find('tr.selectable');

    equal(listview.isStandalone(), false);
    equal(listview.count(), 3);
    deepEqual(controller.getSelectedEntitiesAsArray(), []);

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));

    $(lines[0]).trigger($.Event('click'));
    $(lines[1]).trigger($.Event('click'));

    equal(true, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), ['1', '2']);

    $(lines[2]).trigger($.Event('click'));

    equal(true, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(true, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), ['1', '2', '3']);

    $(lines[1]).trigger($.Event('click'));

    equal(true, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(true, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), ['1', '3']);
});

QUnit.test('creme.listview.core (select, link)', function(assert) {
    var element = $(this.createListViewHtml(this.defaultListViewHtmlOptions({
        rows: [
            [this.createCheckCellHtml('1'), this.createIdCellHtml('1'),
             this.createCellHtml('regular_field-name',
               '<span class="outside-link">A</span><a><span class="inside-link">A-link</span></a>', {sorted: true})
            ],
            [this.createCheckCellHtml('2'), this.createIdCellHtml('2'), this.createCellHtml('regular_field-name', 'B', {sorted: true})]
        ]
    }))).appendTo(this.anchor);
    var listview = creme.widget.create(element);
    var table = element.find('table:first');
    var controller = listview.controller();
    var lines = table.find('tr.selectable');

    equal(listview.isStandalone(), false);
    equal(listview.count(), 2);
    deepEqual(controller.getSelectedEntitiesAsArray(), []);

    $(lines[0]).trigger($.Event('click'));

    equal(true, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), ['1']);

    $(lines[0]).find('a').trigger($.Event('click'));

    equal(true, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), ['1']);

    $(lines[0]).find('.outside-link').trigger($.Event('click'));

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), []);

    $(lines[0]).find('.inside-link').trigger($.Event('click'));

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), []);
});

QUnit.test('creme.listview.core (select, single)', function(assert) {
    var element = $(this.createListViewHtml(this.defaultListViewHtmlOptions({
        multiple: false
    }))).appendTo(this.anchor);
    var listview = creme.widget.create(element);
    var table = element.find('table:first');
    var controller = listview.controller();
    var lines = table.find('tr.selectable');

    equal(listview.isStandalone(), false);
    equal(listview.count(), 3);
    deepEqual(controller.getSelectedEntitiesAsArray(), []);

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));

    $(lines[0]).trigger($.Event('click'));
    $(lines[1]).trigger($.Event('click'));

    equal(false, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), ['2']);

    $(lines[2]).trigger($.Event('click'));

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(true, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), ['3']);

    $(lines[1]).trigger($.Event('click'));

    equal(false, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), ['2']);

    $(lines[1]).trigger($.Event('click'));

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), []);
});

QUnit.test('creme.listview.core (select all)', function(assert) {
    var element = $(this.createListViewHtml(this.defaultListViewHtmlOptions())).appendTo(this.anchor);
    var listview = creme.widget.create(element);
    var table = element.find('table:first');
    var controller = listview.controller();
    var lines = table.find('tr.selectable');

    equal(listview.isStandalone(), false);
    equal(listview.count(), 3);
    deepEqual(controller.getSelectedEntitiesAsArray(), []);

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));

    table.find('[name="select_all"]').trigger($.Event('click'));

    equal(true, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(true, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), ['1', '2', '3']);

    table.find('[name="select_all"]').trigger($.Event('click'));

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), []);
});

QUnit.test('creme.listview.core (reload on enter)', function(assert) {
    var element = $(this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        columns: [this.createCheckAllColumnHtml(), {
                title: '<th class="sorted column sortable cl_lv">Name</th>',
                search: '<th class="sorted column sortable text">' +
                            '<input name="regular_field-name" title="Name" type="text" value="C">' +
                        '</th>'
            }
        ]
    })).appendTo(this.anchor);
    var table = element.find('table:first');
    var column_searchinput = table.find('.columns_bottom .column input[type="text"]');
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);
    equal(listview.pager().isBound(), false);
    equal(listview.header().isBound(), false);

    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
    equal(listview.controller().getReloadUrl(), 'mock/listview/reload');

    column_searchinput.trigger($.Event('keydown', {keyCode: 13, which: 13}));

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            selected_rows: [''],
            selection: 'multiple',
            sort_field: ['regular_field-name'],
            sort_order: [''],
            'regular_field-name': ['C']
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

/* TODO : create test after sort refactor !
QUnit.test('creme.listview.core (toggle sort)', function(assert) {
    var element = $(this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        columns: [
            this.createCheckAllColumnHtml(),
            '<th class="sorted column sortable cl_lv">Name</th>',
            '<th class="column sortable cl_lv">Date</th>'
        ]
    })).appendTo(this.anchor);
    var table = element.find('table:first');
    var column_name = table.find('')
});
*/
