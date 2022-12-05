(function($) {
QUnit.module("creme.listview.core", new QUnitMixin(QUnitEventMixin,
                                                   QUnitAjaxMixin,
                                                   QUnitDialogMixin,
                                                   QUnitListViewMixin, {
    beforeEach: function() {
        this.backend.options.enableUriSearch = true;
    },

    sortableListViewHtmlOptions: function(options) {
        return $.extend({
            columns: [
                this.createCheckAllColumnHtml(), {
                    title: this.createColumnTitleHtml('Name', {
                        name: 'regular_field-name', sorted: true
                    }),
                    search: this.createColumnSearchHtml('Name', {
                        name: 'search-regular_field-name', search: '', sorted: true
                    })
                }, {
                    title: this.createColumnTitleHtml('Phone', {
                        name: 'regular_field-phone', sortable: true
                    }),
                    search: this.createColumnSearchHtml('Phone', {
                        name: 'search-regular_field-phone', search: ''
                    })
                }
            ],
            rows: [
                [this.createCheckCellHtml('1'), this.createIdCellHtml('1'),
                 this.createCellHtml('regular_field-name', 'A', {sorted: true}),
                 this.createCellHtml('regular_field-phone', '060504030201')],
                [this.createCheckCellHtml('2'), this.createIdCellHtml('2'),
                 this.createCellHtml('regular_field-name', 'B', {sorted: true}),
                 this.createCellHtml('regular_field-phone', '070605040302')],
                [this.createCheckCellHtml('3'), this.createIdCellHtml('3'),
                 this.createCellHtml('regular_field-name', 'C', {sorted: true}),
                 this.createCellHtml('regular_field-phone', '070605040311')]
            ]
        }, options || {});
    }
}));

QUnit.test('creme.listview.core', function(assert) {
    var element = $(this.createListViewHtml({
        reloadurl: 'mock/listview/reload'
    })).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), false);
    equal(listview.count(), 0);
    equal(listview.pager().isBound(), false);
    equal(listview.header().isBound(), false);

    equal('mock/listview/reload', element.list_view('prop', 'reloadUrl'));

    listview.controller().reloadUrl('mock/listview/reload/alt');

    equal('mock/listview/reload/alt', element.list_view('prop', 'reloadUrl'));
    equal('mock/listview/reload/alt', listview.controller().reloadUrl());

    element.list_view('prop', 'reloadUrl', 'mock/listview/reload/alt/2');

    equal('mock/listview/reload/alt/2', element.list_view('prop', 'reloadUrl'));
    equal('mock/listview/reload/alt/2', listview.controller().reloadUrl());
});

QUnit.test('creme.listview.core (standalone)', function(assert) {
    var element = $(this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload'
    })).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);
    equal(listview.pager().isBound(), false);
    equal(listview.header().isBound(), false);

    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
    equal(listview.controller().reloadUrl(), 'mock/listview/reload');

    listview.controller().reload();

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

QUnit.test('creme.listview.core (dialog)', function(assert) {
    var dialog = new creme.dialog.Dialog({url: 'mock/html', backend: this.backend});
    var html = this.createListViewHtml({
        reloadurl: 'mock/listview/reload'
    });
    this.setListviewReloadResponse(this.createListViewHtml({
        reloadurl: 'mock/listview/reload?custom=4451'
    }));

    dialog.open();
//    dialog.content().parents('.ui-dialog-content:first');
    dialog.fill(html);

//    var listview = dialog.content().find('.ui-creme-listview:first').creme().widget();
    var listview = dialog.content().find('.ui-creme-listview').first().creme().widget();

    equal(listview.controller().reloadUrl(), 'mock/listview/reload');

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
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC']
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));

//    listview = dialog.content().find('.ui-creme-listview:first').creme().widget();
    listview = dialog.content().find('.ui-creme-listview').first().creme().widget();

    equal(listview.controller().reloadUrl(), 'mock/listview/reload?custom=4451');

    equal(listview.isStandalone(), false);
    equal(listview.count(), 0);
    equal(listview.pager().isBound(), false);
    equal(listview.header().isBound(), false);

    listview.controller().reload();

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
        }],
        ['POST', {
            "URI-SEARCH": {
                "custom": "4451"
            },
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

QUnit.test('creme.listview.core (not empty)', function(assert) {
    var element = $(this.createListViewHtml(this.defaultListViewHtmlOptions())).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), false);
    equal(listview.count(), 3);
    equal(listview.pager().isBound(), true);
    equal(listview.header().isBound(), true);

    var controller = listview.controller();
    equal(controller.isLoading(), false);
    equal(controller.hasSelectedRows(), false);
});

QUnit.test('creme.listview.core (jquery methods)', function(assert) {
    var element = $(this.createListViewHtml(this.defaultListViewHtmlOptions())).appendTo(this.qunitFixture());
    creme.widget.create(element);

    equal(0, element.list_view('selectedRowsCount'));
    deepEqual([], element.list_view('selectedRows'));
    equal('mock/listview/reload', element.list_view('prop', 'reloadUrl'));
    equal(false, element.list_view('prop', 'isLoading'));
    equal(true, Object.isSubClassOf(element.list_view('actionBuilders'), creme.component.FactoryRegistry));
    equal(true, Object.isSubClassOf(element.list_view('columnFilterBuilders'), creme.component.FactoryRegistry));

    this.assertRaises(function() {
        element.list_view('unknown');
    }, Error, 'Error: No such method "unknown" in jQuery plugin "list_view"');
});

QUnit.test('creme.listview.core (selectionMode)', function(assert) {
    creme.lv_widget.checkSelectionMode('none');
    creme.lv_widget.checkSelectionMode('single');
    creme.lv_widget.checkSelectionMode('multiple');

    this.assertRaises(function() {
        creme.lv_widget.checkSelectionMode('invalid');
    }, Error, 'Error: invalid listview selection mode invalid');
});

QUnit.test('creme.listview.core (prop, selectionMode)', function(assert) {
    var element = $(this.createListViewHtml(this.defaultListViewHtmlOptions())).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);
    var controller = listview.controller();

    equal('multiple', controller.selectionMode());
    equal('multiple', element.list_view('prop', 'selectionMode'));

    controller.selectionMode('single');
    equal('single', controller.selectionMode());
    equal('single', element.list_view('prop', 'selectionMode'));

    element.list_view('prop', 'selectionMode', 'none');
    equal('none', controller.selectionMode());
    equal('none', element.list_view('prop', 'selectionMode'));
});

QUnit.test('creme.listview.core (select)', function(assert) {
    var element = $(this.createListViewHtml(this.defaultListViewHtmlOptions())).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);
//    var table = element.find('table:first');
    var table = element.find('table').first();
    var controller = listview.controller();
    var lines = table.find('tr.lv-row');

    equal(listview.isStandalone(), false);
    equal(listview.count(), 3);

    equal(true, controller.isSelectionEnabled());
    equal(false, controller.isSingleSelectionMode());
    equal(true, controller.isMultipleSelectionMode());

    deepEqual(controller.selectedRows(), []);
//    deepEqual(creme.lv_widget.selectedLines(element), []);
    equal(controller.isLoading(), false);
    equal(controller.hasSelectedRows(), false);

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));

    $(lines[0]).trigger('click');
    $(lines[1]).trigger('click');

    equal(true, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.selectedRows(), ['1', '2']);
//    deepEqual(creme.lv_widget.selectedLines(element), ['1', '2']);
    equal(controller.hasSelectedRows(), true);

    $(lines[2]).trigger('click');

    equal(true, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(true, $(lines[2]).is('.selected'));
    deepEqual(controller.selectedRows(), ['1', '2', '3']);
//    deepEqual(creme.lv_widget.selectedLines(element), ['1', '2', '3']);
    equal(controller.hasSelectedRows(), true);

    $(lines[1]).trigger('click');

    equal(true, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(true, $(lines[2]).is('.selected'));
    deepEqual(controller.selectedRows(), ['1', '3']);
//    deepEqual(creme.lv_widget.selectedLines(element), ['1', '3']);
    equal(controller.hasSelectedRows(), true);
});

QUnit.test('creme.listview.core (select, link)', function(assert) {
    var element = $(this.createListViewHtml(this.defaultListViewHtmlOptions({
        rows: [
            [this.createCheckCellHtml('1'), this.createIdCellHtml('1'),
             this.createCellHtml('regular_field-name',
               '<span class="outside-link">A</span><a><span class="inside-link">A-link</span></a>', {sorted: true})
            ],
            [this.createCheckCellHtml('2'), this.createIdCellHtml('2'),
             this.createCellHtml('regular_field-name', 'B', {sorted: true})
            ]
        ]
    }))).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);
//    var table = element.find('table:first');
    var table = element.find('table').first();
    var controller = listview.controller();
    var lines = table.find('tr.lv-row');

    equal(listview.isStandalone(), false);
    equal(listview.count(), 2);
    deepEqual(controller.selectedRows(), []);
    equal(controller.hasSelectedRows(), false);

    $(lines[0]).trigger('click');

    equal(true, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    deepEqual(controller.selectedRows(), ['1']);
    equal(controller.hasSelectedRows(), true);

    $(lines[0]).find('a').trigger('click');

    equal(true, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    deepEqual(controller.selectedRows(), ['1']);
    equal(controller.hasSelectedRows(), true);

    $(lines[0]).find('.outside-link').trigger('click');

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    deepEqual(controller.selectedRows(), []);
    equal(controller.hasSelectedRows(), false);

    $(lines[0]).find('.inside-link').trigger('click');

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    deepEqual(controller.selectedRows(), []);
    equal(controller.hasSelectedRows(), false);

    controller._selections.toggle(lines);

    equal(true, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    deepEqual(controller.selectedRows(), ['1', '2']);
    equal(controller.hasSelectedRows(), true);
});

QUnit.test('creme.listview.core (select, single)', function(assert) {
    var element = $(this.createListViewHtml(this.defaultListViewHtmlOptions({
        mode: 'single'
    }))).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);
//    var table = element.find('table:first');
    var table = element.find('table').first();
    var controller = listview.controller();
    var lines = table.find('tr.lv-row');

    equal(listview.isStandalone(), false);
    equal(listview.count(), 3);
    equal(table.find('tr.selectable').length, 3);

    equal(true, controller.isSelectionEnabled());
    equal(true, controller.isSingleSelectionMode());
    equal(false, controller.isMultipleSelectionMode());

    deepEqual(controller.selectedRows(), []);
    equal(controller.hasSelectedRows(), false);

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));

    $(lines[0]).trigger('click');
    $(lines[1]).trigger('click');

    equal(false, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.selectedRows(), ['2']);
    equal(controller.hasSelectedRows(), true);

    $(lines[2]).trigger('click');

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(true, $(lines[2]).is('.selected'));
    deepEqual(controller.selectedRows(), ['3']);
    equal(controller.hasSelectedRows(), true);

    $(lines[1]).trigger('click');

    equal(false, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.selectedRows(), ['2']);
    equal(controller.hasSelectedRows(), true);

    $(lines[1]).trigger('click');

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.selectedRows(), []);
    equal(controller.hasSelectedRows(), false);

    this.assertRaises(function() {
        controller._selections.toggle(lines);
    }, Error, 'Error: Unable to toggle/select more than one row at once');

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.selectedRows(), []);
    equal(controller.hasSelectedRows(), false);
});

QUnit.test('creme.listview.core (select, none)', function(assert) {
    var element = $(this.createListViewHtml(this.defaultListViewHtmlOptions({
        mode: 'none'
    }))).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);
//    var table = element.find('table:first');
    var table = element.find('table').first();
    var controller = listview.controller();
    var lines = table.find('tr.lv-row');

    equal(listview.isStandalone(), false);
    equal(listview.count(), 3);
    equal(lines.length, 3);
    equal(table.find('tr.lv-row.selectable').length, 0);

    equal(false, controller.isSelectionEnabled());
    equal(false, controller.isSingleSelectionMode());
    equal(false, controller.isMultipleSelectionMode());

    deepEqual(controller.selectedRows(), []);
    equal(controller.hasSelectedRows(), false);

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));

    $(lines[0]).trigger('click');
    $(lines[1]).trigger('click');

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));

    deepEqual(controller.selectedRows(), []);
    equal(controller.hasSelectedRows(), false);
});

QUnit.test('creme.listview.core (select all)', function(assert) {
    var element = $(this.createListViewHtml(this.defaultListViewHtmlOptions())).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);
//    var table = element.find('table:first');
    var table = element.find('table').first();
    var controller = listview.controller();
    var lines = table.find('tr.lv-row');

    equal(listview.isStandalone(), false);
    equal(listview.count(), 3);
    deepEqual(controller.selectedRows(), []);

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));

    table.find('[name="select_all"]').trigger('click');

    equal(true, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(true, $(lines[2]).is('.selected'));
    deepEqual(controller.selectedRows(), ['1', '2', '3']);

    table.find('[name="select_all"]').trigger('click');

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.selectedRows(), []);
});

QUnit.test('creme.listview.core (submitState)', function(assert) {
    var html = this.createListViewHtml(this.defaultListViewHtmlOptions());
    var element = $(html).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);
    var listener = {
        done: this.mockListener('submit-done'),
        fail: this.mockListener('submit-fail'),
        cancel: this.mockListener('submit-cancel'),
        'done fail cancel': this.mockListener('submit-complete')
    };

    this.setListviewReloadResponse(html);

    listview.controller().on('submit-state-start', this.mockListener('submit-state-start'))
                         .on('submit-state-done', this.mockListener('submit-state-done'))
                         .on('submit-state-complete', this.mockListener('submit-state-complete'));

    listview.controller().submitState({custom_a: 12}, listener);

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            custom_a: 12
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));

    deepEqual([
        ['done', html]
    ], this.mockListenerCalls('submit-done'));
    deepEqual([], this.mockListenerCalls('submit-fail'));
    deepEqual([], this.mockListenerCalls('submit-cancel'));
    deepEqual([
        ['done', html]
    ], this.mockListenerCalls('submit-complete'));

    var nextUrl = new creme.ajax.URL('mock/listview/reload').updateSearchData({
        sort_key: ['regular_field-name'],
        sort_order: ['ASC'],
        selection: ['multiple'],
        selected_rows: [''],
        q_filter: ['{}'],
        ct_id: ['67'],
        rows: ['10'],
        custom_a: 12
    });

    deepEqual([
        ['submit-state-start', nextUrl.href()]
    ], this.mockListenerCalls('submit-state-start'));
    deepEqual([
        ['submit-state-done', nextUrl.href(), html]
    ], this.mockListenerCalls('submit-state-done'));
    deepEqual([
        ['submit-state-complete', nextUrl.href(), html]
    ], this.mockListenerCalls('submit-state-complete'));
});

QUnit.test('creme.listview.core (submitState, already loading)', function(assert) {
    var self = this;
    var html = this.createListViewHtml(this.defaultListViewHtmlOptions());
    var element = $(html).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);
    var listener = {
        done: this.mockListener('submit-done'),
        fail: this.mockListener('submit-fail'),
        cancel: this.mockListener('submit-cancel'),
        'done fail cancel': this.mockListener('submit-complete')
    };

    this.setListviewReloadResponse(html);

    this.backend.options.sync = false;
    this.backend.options.delay = 500;

    var controller = listview.controller();

    equal(false, controller.isLoading());

    controller.submitState({}, listener);

    stop(2);

    setTimeout(function() {
        equal(true, controller.isLoading());

        deepEqual([], self.mockListenerCalls('submit-done'));
        deepEqual([], self.mockListenerCalls('submit-fail'));
        deepEqual([], self.mockListenerCalls('submit-cancel'));
        deepEqual([], self.mockListenerCalls('submit-complete'));

        controller.submitState({}, listener);
        controller.submitState({}, listener);
        controller.submitState({}, listener);

        start();
    }, 200);

    setTimeout(function() {
        equal(false, controller.isLoading());

        deepEqual([
            ['done', html]
        ], self.mockListenerCalls('submit-done'));
        deepEqual([], self.mockListenerCalls('submit-fail'));
        deepEqual([
            ['cancel'], ['cancel'], ['cancel']
        ], self.mockListenerCalls('submit-cancel'));
        deepEqual([
            ['cancel'], ['cancel'], ['cancel'], ['done', html]
        ], self.mockListenerCalls('submit-complete'));

        start();
    }, 600);
});

QUnit.test('creme.listview.core (filter on <input> enter)', function(assert) {
    var element = $(this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        columns: [this.createCheckAllColumnHtml(), {
                title: '<th class="sorted lv-column sortable cl_lv">Name</th>',
                search: '<th class="sorted lv-column sortable text">' +
                            '<input name="search-regular_field-name" data-lv-search-widget="text" title="Name" type="text" value="C">' +
                        '</th>'
            }
        ]
    })).appendTo(this.qunitFixture());
//    var table = element.find('table:first');
    var table = element.find('table').first();
    var columnSearch = table.find('.lv-search-header .lv-column input[type="text"]');
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);
    equal(listview.pager().isBound(), false);
    equal(listview.header().isBound(), false);

    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
    equal(listview.controller().reloadUrl(), 'mock/listview/reload');

    columnSearch.trigger($.Event('keydown', {keyCode: 13, which: 13}));

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            'search-regular_field-name': ['C']
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.core (filter on <select> change)', function(assert) {
    var element = $(this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        columns: [this.createCheckAllColumnHtml(), {
                title: '<th class="sorted lv-column sortable cl_lv">Name</th>',
                search: '<th class="sorted lv-column sortable text">' +
                            '<select name="search-regular_field-name" data-lv-search-widget="select" title="Name">' +
                                 '<option value="opt-A">A</option>' +
                                 '<option value="opt-B" selected>B</option>' +
                                 '<option value="opt-C">C</option>' +
                            '</select>' +
                        '</th>'
            }
        ]
    })).appendTo(this.qunitFixture());
//    var table = element.find('table:first');
    var table = element.find('table').first();
    var columnSearch = table.find('.lv-search-header .lv-column select');
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);
    equal(listview.pager().isBound(), false);
    equal(listview.header().isBound(), false);

    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
    equal(listview.controller().reloadUrl(), 'mock/listview/reload');

    columnSearch.trigger('change');

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            'search-regular_field-name': ['opt-B']
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});


QUnit.test('creme.listview.core (unknown search widget)', function(assert) {
    var element = $(this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        columns: [this.createCheckAllColumnHtml(), {
                title: '<th class="sorted lv-column sortable cl_lv">Name</th>',
                search: '<th class="sorted lv-column sortable text">' +
                            '<input name="search-regular_field-name" data-lv-search-widget="unknown" title="Name" type="text" value="C">' +
                        '</th>'
            }
        ]
    })).appendTo(this.qunitFixture());
//    var table = element.find('table:first');
    var table = element.find('table').first();
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);
    equal(listview.pager().isBound(), false);
    equal(listview.header().isBound(), false);

    var columnSearch = table.find('.lv-search-header .lv-column input[type="text"]');
    equal(columnSearch.is('[data-lv-search-widget="unknown"]'), true);

    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
    equal(listview.controller().reloadUrl(), 'mock/listview/reload');

    columnSearch.trigger($.Event('keydown', {keyCode: 13, which: 13}));

    // Not bound, do nothing
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});


QUnit.parametrize('creme.listview.core (daterange search widget, keydown)', [
    '#id_search-regular_field-start',
    '#id_search-regular_field-end'
], function(daterange_input_id, assert) {
    var element = $(this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        columns: [this.createCheckAllColumnHtml(), {
                title: '<th class="sorted lv-column sortable cl_lv">Name</th>',
                search: (
                    '<th class="lv-column sortable search sorted">' +
                        '<div class="lv-search-daterange" data-lv-search-widget="daterange">' +
                            '<div class="date-start">' +
                                '<input class="lv-state-field" name="search-regular_field-start" id="id_search-regular_field-start" data-format="dd-mm-yy" value="19-06-2020"/>' +
                            '</div>' +
                            '<div class="date-end">' +
                                '<input class="lv-state-field" name="search-regular_field-end" id="id_search-regular_field-end" data-format="dd-mm-yy" value="20-06-2020"/>' +
                            '</div>' +
                        '</div>' +
                    '</th>'
                )
            }
        ]
    })).appendTo(this.qunitFixture());
//    var table = element.find('table:first');
    var table = element.find('table').first();
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);
    equal(listview.pager().isBound(), false);
    equal(listview.header().isBound(), false);

    var columnSearch = table.find('.lv-search-header .lv-column .lv-search-daterange');
    equal(columnSearch.is('[data-lv-search-widget="daterange"]'), true);

    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
    equal(listview.controller().reloadUrl(), 'mock/listview/reload');

    var dateInput = columnSearch.find(daterange_input_id);

    ok(dateInput.is('.hasDatepicker'));

    // enter key on date input
    dateInput.trigger($.Event('keydown', {keyCode: 13, which: 13}));

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            'search-regular_field-start': ['19-06-2020'],
            'search-regular_field-end': ['20-06-2020']
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});


QUnit.test('creme.listview.core (daterange search widget, change)', function(assert) {
    var element = $(this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        columns: [this.createCheckAllColumnHtml(), {
                title: '<th class="sorted lv-column sortable cl_lv">Name</th>',
                search: (
                    '<th class="lv-column sortable search sorted">' +
                        '<div class="lv-search-daterange" data-lv-search-widget="daterange">' +
                            '<div class="date-start">' +
                                '<input class="lv-state-field" name="search-regular_field-start" id="id_search-regular_field-start" data-format="dd-mm-yy" value="19-06-2020"/>' +
                            '</div>' +
                            '<div class="date-end">' +
                                '<input class="lv-state-field" name="search-regular_field-end" id="id_search-regular_field-end" data-format="dd-mm-yy" value="20-06-2020"/>' +
                            '</div>' +
                        '</div>' +
                    '</th>'
                )
            }
        ]
    })).appendTo(this.qunitFixture());
//    var table = element.find('table:first');
    var table = element.find('table').first();
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);
    equal(listview.pager().isBound(), false);
    equal(listview.header().isBound(), false);

    var columnSearch = table.find('.lv-search-header .lv-column .lv-search-daterange');
    equal(columnSearch.is('[data-lv-search-widget="daterange"]'), true);

    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
    equal(listview.controller().reloadUrl(), 'mock/listview/reload');

    // enter key on start date
    var start = columnSearch.find('#id_search-regular_field-start');

    ok(start.is('.hasDatepicker'));
    equal('dd-mm-yy', start.datepicker('option', 'dateFormat'));

    // show picker and select date
    start.datepicker('show');
    start.datepicker('setDate', '01-01-2020');

    // click on selected date => onSelect cb => change
    $('.ui-datepicker-current-day').trigger('click');

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            'search-regular_field-start': ['01-01-2020'],
            'search-regular_field-end': ['20-06-2020']
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});


QUnit.parametrize('creme.listview.core (daterange search widget, change, invalid)', [
    '12', '12-12', '35-12-2020'
], function(invalidValue, assert) {
    var element = $(this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        columns: [this.createCheckAllColumnHtml(), {
                title: '<th class="sorted lv-column sortable cl_lv">Name</th>',
                search: (
                    '<th class="lv-column sortable search sorted">' +
                        '<div class="lv-search-daterange" data-lv-search-widget="daterange">' +
                            '<div class="date-start">' +
                                '<input class="lv-state-field" name="search-regular_field-start" id="id_search-regular_field-start" data-format="dd-mm-yy" value="19-06-2020"/>' +
                            '</div>' +
                            '<div class="date-end">' +
                                '<input class="lv-state-field" name="search-regular_field-end" id="id_search-regular_field-end" data-format="dd-mm-yy" value="20-06-2020"/>' +
                            '</div>' +
                        '</div>' +
                    '</th>'
                )
            }
        ]
    })).appendTo(this.qunitFixture());
//    var table = element.find('table:first');
    var table = element.find('table').first();
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);
    equal(listview.pager().isBound(), false);
    equal(listview.header().isBound(), false);

    var columnSearch = table.find('.lv-search-header .lv-column .lv-search-daterange');
    equal(columnSearch.is('[data-lv-search-widget="daterange"]'), true);

    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
    equal(listview.controller().reloadUrl(), 'mock/listview/reload');

    var start = columnSearch.find('#id_search-regular_field-start');
    var end = columnSearch.find('#id_search-regular_field-end');

    // enter key on date input
    start.val(invalidValue);
    start.trigger($.Event('keydown', {keyCode: 13, which: 13}));

    // ignore the call
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    end.val(invalidValue);
    end.trigger($.Event('keydown', {keyCode: 13, which: 13}));

    // ignore the call
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.core (custom search widget)', function(assert) {
    var element = $(this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        columns: [this.createCheckAllColumnHtml(), {
                title: '<th class="sorted lv-column sortable cl_lv">Name</th>',
                search: '<th class="sorted lv-column sortable text">' +
                            '<input name="search-regular_field-name" data-lv-search-widget="custom" title="Name" type="text" value="1.78">' +
                        '</th>'
            }
        ]
    })).appendTo(this.qunitFixture());
//    var table = element.find('table:first');
    var table = element.find('table').first();

    $(this.qunitFixture()).on('listview-setup-column-filters', '.ui-creme-listview', function(e, actions) {
        actions.register('custom', function(element, options, list) {
            $(element).on('keydown', function(e) {
                if (e.keyCode === list.submitOnKey()) {
                    e.preventDefault();
                    list.submitState({
                        custom: 10 * (parseFloat($(e.target).val()) || 0)
                    });
                }
            }).attr('data-custom-search', 'active');
        });
    });

    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);
    equal(listview.pager().isBound(), false);
    equal(listview.header().isBound(), false);

    var columnSearch = table.find('.lv-search-header .lv-column input[type="text"]');
    equal(columnSearch.is('[data-custom-search="active"]'), true);

    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
    equal(listview.controller().reloadUrl(), 'mock/listview/reload');

    columnSearch.trigger($.Event('keydown', {keyCode: 13, which: 13}));

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            'custom': 17.8
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.core (resetSearchState)', function(assert) {
    var html = this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        columns: [this.createCheckAllColumnHtml(), {
                title: '<th class="sorted lv-column sortable cl_lv">Name</th>',
                search: '<th class="sorted lv-column sortable text">' +
                            '<input class="lv-state-field" name="search-regular_field-name" data-lv-search-widget="text" title="Name" type="text" value="C">' +
                        '</th>'
            }
        ]
    });
    var element = $(html).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);
    var listener = {
        done: this.mockListener('submit-done'),
        fail: this.mockListener('submit-fail'),
        cancel: this.mockListener('submit-cancel'),
        'done fail cancel': this.mockListener('submit-complete')
    };

    this.setListviewReloadResponse(html);

    listview.controller().on('submit-state-start', this.mockListener('submit-state-start'))
                         .on('submit-state-done', this.mockListener('submit-state-done'))
                         .on('submit-state-complete', this.mockListener('submit-state-complete'));

    listview.controller().resetSearchState(listener);

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            'search-regular_field-name': [''],
            search: 'clear'
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));

    deepEqual([
        ['done', html]
    ], this.mockListenerCalls('submit-done'));
    deepEqual([], this.mockListenerCalls('submit-fail'));
    deepEqual([], this.mockListenerCalls('submit-cancel'));
    deepEqual([
        ['done', html]
    ], this.mockListenerCalls('submit-complete'));

    var nextUrl = new creme.ajax.URL('mock/listview/reload').updateSearchData({
        sort_key: ['regular_field-name'],
        sort_order: ['ASC'],
        selection: ['multiple'],
        selected_rows: [''],
        q_filter: ['{}'],
        ct_id: ['67'],
        'search-regular_field-name': [''],
        rows: ['10']
    });

    deepEqual([
        ['submit-state-start', nextUrl.href()]
    ], this.mockListenerCalls('submit-state-start'));
    deepEqual([
        ['submit-state-done', nextUrl.href(), html]
    ], this.mockListenerCalls('submit-state-done'));
    deepEqual([
        ['submit-state-complete', nextUrl.href(), html]
    ], this.mockListenerCalls('submit-state-complete'));
});

QUnit.test('creme.listview.core (toggle sort)', function(assert) {
    var element = $(this.createListViewHtml(this.sortableListViewHtmlOptions({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload'
    }))).appendTo(this.qunitFixture());

//    var table = element.find('table:first');
    var table = element.find('table').first();
    var column_name = table.find('.lv-columns-header .lv-column.sortable[data-column-key="regular_field-name"]');
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 3);

    column_name.find('button').trigger('click');

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['DESC'],
            'search-regular_field-name': [''],
            'search-regular_field-phone': ['']
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.core (toggle sort, disabled)', function(assert) {
    var element = $(this.createListViewHtml(this.sortableListViewHtmlOptions({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        columns: [
            this.createCheckAllColumnHtml(), {
                title: this.createColumnTitleHtml('Name', {
                    name: 'regular_field-name', sorted: true, disabled: true
                }),
                search: this.createColumnSearchHtml('Name', {
                    name: 'regular_field-name', search: '', sorted: true
                })
            }, {
                title: this.createColumnTitleHtml('Phone', {
                    name: 'regular_field-phone', sortable: true
                }),
                search: this.createColumnSearchHtml('Phone', {
                    name: 'regular_field-phone', search: ''
                })
            }
        ]
    }))).appendTo(this.qunitFixture());

//    var table = element.find('table:first');
    var table = element.find('table').first();
    var column_name = table.find('.lv-columns-header .lv-column.sortable[data-column-key="regular_field-name"]');
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 3);

    equal(true, column_name.find('button').is(':disabled'));
    column_name.find('button').trigger('click');

    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.core (sort another column)', function(assert) {
    var element = $(this.createListViewHtml(this.sortableListViewHtmlOptions({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload'
    }))).appendTo(this.qunitFixture());

//    var table = element.find('table:first');
    var table = element.find('table').first();
    var column_phone = table.find('.lv-columns-header .lv-column.sortable[data-column-key="regular_field-phone"]');
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 3);

    column_phone.find('button').trigger('click');

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-phone'],
            sort_order: ['ASC'],
            'search-regular_field-name': [''],
            'search-regular_field-phone': ['']
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.core (hatbar buttons, unknow action)', function(assert) {
    var element = $(this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        hatbarbuttons: [
            {action: 'invalid'}
        ],
        reloadurl: 'mock/listview/reload',
        columns: [this.createCheckAllColumnHtml(), {
                title: '<th class="sorted lv-column sortable cl_lv">Name</th>',
                search: '<th class="sorted lv-column sortable text">' +
                            '<input name="regular_field-name" title="Name" type="text" value="C">' +
                        '</th>'
            }
        ]
    })).appendTo(this.qunitFixture());

    var listview = creme.widget.create(element);
    var button = element.find('.list-header-buttons a[data-action]');

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);

    equal(1, button.length);
    equal(true, button.is('.is-disabled'));
});

QUnit.test('creme.listview.core (hatbar buttons, submit-lv-state)', function(assert) {
    var element = $(this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        hatbarbuttons: [
            {action: 'submit-lv-state', data: {custom_state: 12}}
        ],
        reloadurl: 'mock/listview/reload',
        columns: [this.createCheckAllColumnHtml(), {
                title: '<th class="sorted lv-column sortable cl_lv">Name</th>',
                search: '<th class="sorted lv-column sortable text">' +
                            '<input class="lv-state-field" name="search-regular_field-name" title="Name" type="text" value="C">' +
                        '</th>'
            }
        ]
    })).appendTo(this.qunitFixture());

    var listview = creme.widget.create(element);
    var button = element.find('.list-header-buttons a[data-action]');

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);

    equal(1, button.length);
    equal(false, button.is('.is-disabled'));

    button.trigger('click');

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            'search-regular_field-name': ['C'],
            custom_state: 12
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.core (hatbar buttons, reset-lv-search)', function(assert) {
    var element = $(this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        hatbarbuttons: [
            {action: 'reset-lv-search'}
        ],
        reloadurl: 'mock/listview/reload',
        columns: [this.createCheckAllColumnHtml(), {
                title: '<th class="sorted lv-column sortable cl_lv">Name</th>',
                search: '<th class="sorted lv-column sortable text">' +
                            '<input class="lv-state-field" name="search-regular_field-name" title="Name" type="text" value="C">' +
                        '</th>'
            }
        ]
    })).appendTo(this.qunitFixture());

    var listview = creme.widget.create(element);
    var button = element.find('.list-header-buttons a[data-action]');

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);

    equal(1, button.length);
    equal(false, button.is('.is-disabled'));

    button.trigger('click');

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            'search-regular_field-name': [''],
            search: 'clear'
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.core (hatbar controls, entityfilter, change)', function(assert) {
    var html = this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        hatbarcontrols: [{
            name: 'filter',
            group: 'filters',
            options: [
                '<option value="filter-a">Filter A</option>',
                '<option value="filter-b">Filter B</option>'
            ]
        }]
    });

    var element = $(html).appendTo(this.qunitFixture());
    var filter = element.find('.list-control-group.list-filters select');

    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);
    equal(1, filter.length);

    filter.val('filter-b').trigger('change');

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            filter: 'filter-b'
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.core (hatbar controls, entityfilter, delete)', function(assert) {
    var html = this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        hatbarcontrols: [{
            name: 'filter',
            group: 'filters',
            options: [
                '<option value="filter-a">Filter A</option>',
                '<option value="filter-b">Filter B</option>'
            ],
            actions: [
                {url: 'mock/listview/filter/delete', action: 'delete', data: {id: 'filter-b'}}
            ]
        }]
    });

    var element = $(html).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);
    var link = element.find('.list-control-group.list-filters a[data-action="delete"]');

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);
    equal(1, link.length);
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/filter/delete'));

    link.trigger('click');

    this.assertOpenedConfirmDialog(gettext('Are you sure ?'));
    this.acceptConfirmDialog();

    deepEqual([
        ['POST', {
            id: 'filter-b'
        }]
    ], this.mockBackendUrlCalls('mock/listview/filter/delete'));

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            filter: ['filter-a']
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.core (hatbar controls, entityfilter, info)', function(assert) {
    var html = this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        hatbarcontrols: [{
            name: 'filter',
            group: 'filters',
            options: [
                '<option value="filter-a">Filter A</option>',
                '<option value="filter-b">Filter B</option>'
            ],
            actions: [
                {action: 'popover', html: '<summary>Filter A Details</summary><details><h3>Filter by "A"</h3></details>'}
            ]
        }]
    });

    var element = $(html).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);
    var link = element.find('.list-control-group.list-filters a[data-action="popover"]');

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);
    equal(1, link.length);

    link.trigger('click');

    var popover = this.assertOpenedPopover();
    this.assertPopoverTitle('Filter A Details');
    equal(popover.find('.popover-content').html(), '<h3>Filter by "A"</h3>');
});

QUnit.test('creme.listview.core (hatbar controls, view, change)', function(assert) {
    var html = this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        hatbarcontrols: [{
            name: 'hfilter',
            group: 'views',
            options: [
                '<option value="view-a">View A</option>',
                '<option value="view-b">View B</option>'
            ]
        }]
    });

    var element = $(html).appendTo(this.qunitFixture());
    var selector = element.find('.list-control-group.list-views select');

    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);
    equal(1, selector.length);

    selector.val('view-b').trigger('change');

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            hfilter: 'view-b'
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.core (hatbar controls, view, delete)', function(assert) {
    var html = this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        hatbarcontrols: [{
            name: 'hfilter',
            group: 'views',
            options: [
                '<option value="view-a">View A</option>',
                '<option value="view-b">View B</option>'
            ],
            actions: [
                {url: 'mock/listview/view/delete', action: 'delete', data: {id: 'view-b'}}
            ]
        }]
    });

    var element = $(html).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);
    var link = element.find('.list-control-group.list-views a[data-action="delete"]');

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);
    equal(1, link.length);
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/view/delete'));

    link.trigger('click');

    this.assertOpenedConfirmDialog(gettext('Are you sure ?'));
    this.acceptConfirmDialog();

    deepEqual([
        ['POST', {
            id: 'view-b'
        }]
    ], this.mockBackendUrlCalls('mock/listview/view/delete'));

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            rows: ['10'],
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            hfilter: ['view-a']
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.core (pagesize selector)', function(assert) {
    var html = this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload'
    });

    var element = $(html).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);
    var selector = element.find('.list-pagesize-selector');

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);
    equal(1, selector.length);
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    selector.val('25').trigger('change');

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            rows: '25'
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.core (page link)', function(assert) {
    var html = this.createListViewHtml(this.defaultListViewHtmlOptions({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        pager: '<a class="pager-link link-a" data-page="4"></a>'
    }));

    var element = $(html).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);
    var link = element.find('.link-a');

    equal(listview.isStandalone(), true);
    equal(listview.count(), 3);

    equal(1, link.length);
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    link.trigger('click');

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            content: 1,
            selected_rows: [''],
            selection: ['multiple'],
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            rows: ['10'],
            page: '4'
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.core (serializeState)', function(assert) {
    var html = this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        selectionMode: 'multiple'
    });

    var element = $(html).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);
    var controller = listview.controller();

    deepEqual({
        ct_id: ['67'],
        q_filter: ['{}'],
        selected_rows: [''],
        selection: ['multiple'],
        sort_key: ['regular_field-name'],
        sort_order: ['ASC'],
        rows: ['10']
    }, controller.state());

    listview.controller().stateField('selection').val('single');
    listview.controller().stateField('sort_order').val('DESC');
    listview.controller().stateField('rows').val('25');

    deepEqual({
        ct_id: ['67'],
        q_filter: ['{}'],
        selected_rows: [''],
        selection: ['single'],
        sort_key: ['regular_field-name'],
        sort_order: ['DESC'],
        rows: ['25']
    }, controller.state());
});

}(jQuery));
