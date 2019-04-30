(function($) {

QUnit.module("creme.listview.core", new QUnitMixin(QUnitEventMixin,
                                                   QUnitAjaxMixin,
                                                   QUnitDialogMixin,
                                                   QUnitListViewMixin, {
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
    var element = $(this.createListViewHtml()).appendTo(this.qunitFixture());
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
    })).appendTo(this.qunitFixture());
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
    equal(controller.hasSelection(), false);
});

QUnit.test('creme.listview.core (select)', function(assert) {
    var element = $(this.createListViewHtml(this.defaultListViewHtmlOptions())).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);
    var table = element.find('table:first');
    var controller = listview.controller();
    var lines = table.find('tr.selectable');

    equal(listview.isStandalone(), false);
    equal(listview.count(), 3);

    deepEqual(controller.getSelectedEntitiesAsArray(), []);
    equal(controller.isLoading(), false);
    equal(controller.hasSelection(), false);

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));

    $(lines[0]).trigger($.Event('click'));
    $(lines[1]).trigger($.Event('click'));

    equal(true, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), ['1', '2']);
    equal(controller.hasSelection(), true);

    $(lines[2]).trigger($.Event('click'));

    equal(true, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(true, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), ['1', '2', '3']);
    equal(controller.hasSelection(), true);

    $(lines[1]).trigger($.Event('click'));

    equal(true, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(true, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), ['1', '3']);
    equal(controller.hasSelection(), true);
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
    var table = element.find('table:first');
    var controller = listview.controller();
    var lines = table.find('tr.selectable');

    equal(listview.isStandalone(), false);
    equal(listview.count(), 2);
    deepEqual(controller.getSelectedEntitiesAsArray(), []);
    equal(controller.hasSelection(), false);

    $(lines[0]).trigger($.Event('click'));

    equal(true, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), ['1']);
    equal(controller.hasSelection(), true);

    $(lines[0]).find('a').trigger($.Event('click'));

    equal(true, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), ['1']);
    equal(controller.hasSelection(), true);

    $(lines[0]).find('.outside-link').trigger($.Event('click'));

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), []);
    equal(controller.hasSelection(), false);

    $(lines[0]).find('.inside-link').trigger($.Event('click'));

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), []);
    equal(controller.hasSelection(), false);
});

QUnit.test('creme.listview.core (select, single)', function(assert) {
    var element = $(this.createListViewHtml(this.defaultListViewHtmlOptions({
        multiple: false
    }))).appendTo(this.qunitFixture());
    var listview = creme.widget.create(element);
    var table = element.find('table:first');
    var controller = listview.controller();
    var lines = table.find('tr.selectable');

    equal(listview.isStandalone(), false);
    equal(listview.count(), 3);
    deepEqual(controller.getSelectedEntitiesAsArray(), []);
    equal(controller.hasSelection(), false);

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));

    $(lines[0]).trigger($.Event('click'));
    $(lines[1]).trigger($.Event('click'));

    equal(false, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), ['2']);
    equal(controller.hasSelection(), true);

    $(lines[2]).trigger($.Event('click'));

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(true, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), ['3']);
    equal(controller.hasSelection(), true);

    $(lines[1]).trigger($.Event('click'));

    equal(false, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), ['2']);
    equal(controller.hasSelection(), true);

    $(lines[1]).trigger($.Event('click'));

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntitiesAsArray(), []);
    equal(controller.hasSelection(), false);
});

QUnit.test('creme.listview.core (select all)', function(assert) {
    var element = $(this.createListViewHtml(this.defaultListViewHtmlOptions())).appendTo(this.qunitFixture());
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

QUnit.test('creme.listview.core (filter on <input> enter)', function(assert) {
    var element = $(this.createListViewHtml({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload',
        columns: [this.createCheckAllColumnHtml(), {
                title: '<th class="sorted column sortable cl_lv">Name</th>',
                search: '<th class="sorted column sortable text">' +
                            '<input name="search-regular_field-name" title="Name" type="text" value="C">' +
                        '</th>'
            }
        ]
    })).appendTo(this.qunitFixture());
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
                title: '<th class="sorted column sortable cl_lv">Name</th>',
                search: '<th class="sorted column sortable text">' +
                            '<select name="search-regular_field-name" title="Name">' +
                                 '<option value="opt-A">A</option>' +
                                 '<option value="opt-B" selected>B</option>' +
                                 '<option value="opt-C">C</option>' +
                            '</select>' +
                        '</th>'
            }
        ]
    })).appendTo(this.qunitFixture());
    var table = element.find('table:first');
    var column_searchselect = table.find('.columns_bottom .column select');
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 0);
    equal(listview.pager().isBound(), false);
    equal(listview.header().isBound(), false);

    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
    equal(listview.controller().getReloadUrl(), 'mock/listview/reload');

    column_searchselect.trigger('change');

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            selected_rows: [''],
            selection: 'multiple',
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            'search-regular_field-name': ['opt-B']
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.core (toggle sort)', function(assert) {
    var element = $(this.createListViewHtml(this.sortableListViewHtmlOptions({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload'
    }))).appendTo(this.qunitFixture());

    var table = element.find('table:first');
    var column_name = table.find('.columns_top .column.sortable[data-column-key="regular_field-name"]');
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 3);

    column_name.find('button').click();

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            selected_rows: [''],
            selection: 'multiple',
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

    var table = element.find('table:first');
    var column_name = table.find('.columns_top .column.sortable[data-column-key="regular_field-name"]');
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 3);

    equal(true, column_name.find('button').is(':disabled'));
    column_name.find('button').click();

    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.core (sort another column)', function(assert) {
    var element = $(this.createListViewHtml(this.sortableListViewHtmlOptions({
        tableclasses: ['listview-standalone'],
        reloadurl: 'mock/listview/reload'
    }))).appendTo(this.qunitFixture());

    var table = element.find('table:first');
    var column_phone = table.find('.columns_top .column.sortable[data-column-key="regular_field-phone"]');
    var listview = creme.widget.create(element);

    equal(listview.isStandalone(), true);
    equal(listview.count(), 3);

    column_phone.find('button').click();

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            selected_rows: [''],
            selection: 'multiple',
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
                title: '<th class="sorted column sortable cl_lv">Name</th>',
                search: '<th class="sorted column sortable text">' +
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
                title: '<th class="sorted column sortable cl_lv">Name</th>',
                search: '<th class="sorted column sortable text">' +
                            '<input name="search-regular_field-name" title="Name" type="text" value="C">' +
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

    button.click();

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            selected_rows: [''],
            selection: 'multiple',
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            'search-regular_field-name': ['C'],
            custom_state: 12
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

}(jQuery));
