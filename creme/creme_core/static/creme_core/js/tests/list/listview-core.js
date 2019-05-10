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
            rows: ['10'],
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
        reloadurl: 'mock/listview/reload',
        status: {
            q_filter: '{a: 12}'
        }
    });
    this.setListviewReloadContent('{a: 12}', this.createListViewHtml({
        reloadurl: 'mock/listview/reload?custom=4451'
    }));

    dialog.open();
    dialog.content().parents('.ui-dialog-content:first');
    dialog.fill(html);

    var listview = dialog.content().find('.ui-creme-listview:first').creme().widget();

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
            q_filter: ['{a: 12}'],
            rows: ['10'],
            selected_rows: [''],
            selection: 'multiple',
            sort_key: ['regular_field-name'],
            sort_order: ['ASC']
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));

    listview = dialog.content().find('.ui-creme-listview:first').creme().widget();

    equal(listview.controller().getReloadUrl(), 'mock/listview/reload?custom=4451');

    equal(listview.isStandalone(), false);
    equal(listview.count(), 0);
    equal(listview.pager().isBound(), false);
    equal(listview.header().isBound(), false);

    listview.controller().reload();

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{a: 12}'],
            rows: ['10'],
            selected_rows: [''],
            selection: 'multiple',
            sort_key: ['regular_field-name'],
            sort_order: ['ASC']
        }],
        ['POST', {
            "URI-SEARCH": {
                "custom": "4451"
            },
            ct_id: ['67'],
            q_filter: ['{}'],
            rows: ['10'],
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

    deepEqual(controller.getSelectedEntities(), []);
    equal(controller.isLoading(), false);
    equal(controller.hasSelection(), false);

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));

    $(lines[0]).click();
    $(lines[1]).click();

    equal(true, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntities(), ['1', '2']);
    equal(controller.hasSelection(), true);

    $(lines[2]).click();

    equal(true, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(true, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntities(), ['1', '2', '3']);
    equal(controller.hasSelection(), true);

    $(lines[1]).click();

    equal(true, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(true, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntities(), ['1', '3']);
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
    deepEqual(controller.getSelectedEntities(), []);
    equal(controller.hasSelection(), false);

    $(lines[0]).click();

    equal(true, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    deepEqual(controller.getSelectedEntities(), ['1']);
    equal(controller.hasSelection(), true);

    $(lines[0]).find('a').click();

    equal(true, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    deepEqual(controller.getSelectedEntities(), ['1']);
    equal(controller.hasSelection(), true);

    $(lines[0]).find('.outside-link').click();

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    deepEqual(controller.getSelectedEntities(), []);
    equal(controller.hasSelection(), false);

    $(lines[0]).find('.inside-link').click();

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    deepEqual(controller.getSelectedEntities(), []);
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
    deepEqual(controller.getSelectedEntities(), []);
    equal(controller.hasSelection(), false);

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));

    $(lines[0]).click();
    $(lines[1]).click();

    equal(false, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntities(), ['2']);
    equal(controller.hasSelection(), true);

    $(lines[2]).click();

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(true, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntities(), ['3']);
    equal(controller.hasSelection(), true);

    $(lines[1]).click();

    equal(false, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntities(), ['2']);
    equal(controller.hasSelection(), true);

    $(lines[1]).click();

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntities(), []);
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
    deepEqual(controller.getSelectedEntities(), []);

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));

    table.find('[name="select_all"]').click();

    equal(true, $(lines[0]).is('.selected'));
    equal(true, $(lines[1]).is('.selected'));
    equal(true, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntities(), ['1', '2', '3']);

    table.find('[name="select_all"]').click();

    equal(false, $(lines[0]).is('.selected'));
    equal(false, $(lines[1]).is('.selected'));
    equal(false, $(lines[2]).is('.selected'));
    deepEqual(controller.getSelectedEntities(), []);
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
            rows: ['10'],
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
            rows: ['10'],
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
            rows: ['10'],
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
            rows: ['10'],
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
            rows: ['10'],
            selected_rows: [''],
            selection: 'multiple',
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            'search-regular_field-name': ['C'],
            custom_state: 12
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

    filter.val('filter-b').change();

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            rows: ['10'],
            selected_rows: [''],
            selection: 'multiple',
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

    link.click();

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
            rows: ['10'],
            selected_rows: [''],
            selection: 'multiple',
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            filter: ['filter-a']
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
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

    selector.val('view-b').change();

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            rows: ['10'],
            selected_rows: [''],
            selection: 'multiple',
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

    link.click();

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
            rows: ['10'],
            selected_rows: [''],
            selection: 'multiple',
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

    selector.val('25').change();

    deepEqual([
        ['POST', {
            ct_id: ['67'],
            q_filter: ['{}'],
            selected_rows: [''],
            selection: 'multiple',
            sort_key: ['regular_field-name'],
            sort_order: ['ASC'],
            rows: '25'
        }]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});

}(jQuery));
