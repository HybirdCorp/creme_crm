
QUnit.module("creme.bricks.table", $.extend({}, QUnitBrickMixin, {
    setupBrick: function() {
        
    },

    createBrickTableHtml: function(options) {
        options = $.extend({
            id: 'brick-for-test',
            title: 'Test it',
            columns: [],
            rows: [],
            deps: ['dep1']
        }, options || {});

        var renderRow = function(row) {
            return Array.isArray(row) ? '<tr>' + row.join('') + '</tr>' : row;
        };

        var quoteHtml = function(d) {
            return '&quot;' + d + '&quot;';
        }

        return (
            '<div class="brick ui-creme-widget" widget="brick" id="${id}" data-brick-deps="[${deps}]">'
                 + '<div class="brick-header">'
                     + '<div class="brick-title">${title}</div>'
                     + '<div class="brick-selection-indicator">'
                         + '<span class="brick-selection-title" data-title-format="%d entry on %d" data-plural-format="%d entries on %d"></span>'
                     + '</div>'
                 + '</div>'
                 + '<div class="brick-content">'
                     + '<table class="brick-table-content">'
                         + '<thead><tr>${columns}</tr></thead>'
                         + '<tbody>${rows}</tbody>'
                     + '</table>'
                 + '</div>'
             + '</div>').template({
                  id: options.id,
                  title: options.title,
                  deps: options.deps.map(quoteHtml).join(','),
                  columns: options.columns.join(''),
                  rows: options.rows.map(renderRow).join('')
               });
    },

    createBrickTable: function(options) {
        var html = this.createBrickTableHtml(options);

        var element = $(html).appendTo($('body'));
        var widget = creme.widget.create(element);
        var brick = widget.brick();

        equal(true, brick.isBound());
        equal(false, brick.isLoading());

        return widget;
    },

    selectionItemInfo: function(d) {
        return {
            selected: d.selected,
            ui: d.ui.get()
        };
    }
}));

QUnit.test('creme.bricks.Brick.table (bind/unbind)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="${id}"></div>').appendTo($('body'));

    brick.bind(element);

    equal(true, brick.isBound());
    equal(true, brick.table().isBound());

    this.assertRaises(function() {
        brick.table().bind(element);
    }, Error, 'Error: BrickTable is already bound');

    brick.unbind();

    equal(false, brick.isBound());
    equal(false, brick.table().isBound());

    this.assertRaises(function() {
        brick.table().unbind();
    }, Error, 'Error: BrickTable is not bound');
});

QUnit.test('creme.bricks.Brick.table (empty)', function(assert) {
    var widget = this.createBrickTable({
        columns: [
            '<th data-table-primary-column>Id</th>',
            '<th data-type="date">Created on</th>',
            '<th>Name</th>'
        ],
    });

    var brick = widget.brick();
    var element = brick.element();
    var selections = brick.table().selections();

    deepEqual([], selections.selectables());
    deepEqual([], selections.selected());

    equal('', element.find('.brick-selection-title').text());
});

QUnit.test('creme.bricks.Brick.table (toggle selection)', function(assert) {
    var widget = this.createBrickTable({
        columns: [
            '<th data-table-primary-column>Id</th>',
            '<th data-type="date">Created on</th>',
            '<th>Name</th>'
        ],
        rows: [
            '<tr><td data-selectable-selector-column>1</td><td data-type="date">2017-05-08</td><td>A</td></tr>',
            '<tr><td data-selectable-selector-column>2</td><td data-type="date">2017-05-07</td><td>B</td></tr>',
            '<tr><td data-selectable-selector-column>3</td><td data-type="date">2017-05-06</td><td>C</td></tr>',
        ]
    });

    var brick = widget.brick();
    var element = brick.element();
    var selections = brick.table().selections();

    equal(false, $('tr[data-row-index="1"]').is('.is-selected'));
    equal('', element.find('.brick-selection-title').text());

    deepEqual([
        {selected: false, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="2"]', element).get()},
    ], selections.selectables().map(this.selectionItemInfo));

    deepEqual([], selections.selected());

    $('tr[data-row-index="1"] td[data-selectable-selector-column]', element).click();

    equal(true, $('tr[data-row-index="1"]').is('.is-selected'));
    equal('1 entry on 3', element.find('.brick-selection-title').text());

    deepEqual([
        {selected: false, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="2"]', element).get()},
    ], selections.selectables().map(this.selectionItemInfo));

    deepEqual([
        {selected: true, ui: $('tr[data-row-index="1"]', element).get()},
    ], selections.selected().map(this.selectionItemInfo));

    $('tr[data-row-index="1"] td[data-selectable-selector-column]', element).click();

    equal(false, $('tr[data-row-index="1"]').is('.is-selected'));
    equal('', element.find('.brick-selection-title').text());

    deepEqual([
        {selected: false, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="2"]', element).get()},
    ], selections.selectables().map(this.selectionItemInfo));

    deepEqual([], selections.selected().map(this.selectionItemInfo));
});

QUnit.test('creme.bricks.Brick.table (toggle all)', function(assert) {
    var widget = this.createBrickTable({
        columns: [
            '<th data-selectable-selector-column><input class="row-selector-all" type="checkbox" /></th>',
            '<th data-table-primary-column>Id</th>',
            '<th data-type="date">Created on</th>',
            '<th>Name</th>'
        ],
        rows: [
            '<tr><td><input type="checkbox" /></td><td data-selectable-selector-column>1</td><td data-type="date">2017-05-08</td><td>A</td></tr>',
            '<tr><td><input type="checkbox" /></td><td data-selectable-selector-column>2</td><td data-type="date">2017-05-07</td><td>B</td></tr>',
            '<tr><td><input type="checkbox" /></td><td data-selectable-selector-column>3</td><td data-type="date">2017-05-06</td><td>C</td></tr>',
        ]
    });

    var brick = widget.brick();
    var element = brick.element();
    var selections = brick.table().selections();

    equal(false, $('tr[data-row-index="0"]').is('.is-selected'));
    equal(false, $('tr[data-row-index="1"]').is('.is-selected'));
    equal(false, $('tr[data-row-index="2"]').is('.is-selected'));

    deepEqual([
        {selected: false, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="2"]', element).get()},
    ], selections.selectables().map(this.selectionItemInfo));

    deepEqual([], selections.selected());

    $('.row-selector-all', element).click();

    equal(true, $('tr[data-row-index="0"]').is('.is-selected'));
    equal(true, $('tr[data-row-index="1"]').is('.is-selected'));
    equal(true, $('tr[data-row-index="2"]').is('.is-selected'));
    equal('3 entries on 3', element.find('.brick-selection-title').text());

    deepEqual([
        {selected: true, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="2"]', element).get()},
    ], selections.selectables().map(this.selectionItemInfo));

    deepEqual([
        {selected: true, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="2"]', element).get()},
    ], selections.selected().map(this.selectionItemInfo));

    $('.row-selector-all', element).click();

    equal(false, $('tr[data-row-index="0"]').is('.is-selected'));
    equal(false, $('tr[data-row-index="1"]').is('.is-selected'));
    equal(false, $('tr[data-row-index="2"]').is('.is-selected'));
    equal('', element.find('.brick-selection-title').text());

    deepEqual([
        {selected: false, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="2"]', element).get()},
    ], selections.selectables().map(this.selectionItemInfo));

    deepEqual([], selections.selected().map(this.selectionItemInfo));

    $('.row-selector-all', element).prop('checked', true).trigger('change');
    equal('3 entries on 3', element.find('.brick-selection-title').text());

    deepEqual([
        {selected: true, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="2"]', element).get()},
    ], selections.selectables().map(this.selectionItemInfo));

    deepEqual([
        {selected: true, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="2"]', element).get()},
    ], selections.selected().map(this.selectionItemInfo));
});

QUnit.test('creme.bricks.Brick.table (toggle selection, loading)', function(assert) {
    var widget = this.createBrickTable({
        columns: [
            '<th data-selectable-selector-column><input class="row-selector-all" type="checkbox" /></th>',
            '<th data-table-primary-column>Id</th>',
            '<th data-type="date">Created on</th>',
            '<th>Name</th>'
        ],
        rows: [
            '<tr><td data-selectable-selector-column>1</td><td data-type="date">2017-05-08</td><td>A</td></tr>',
            '<tr><td data-selectable-selector-column>2</td><td data-type="date">2017-05-07</td><td>B</td></tr>',
            '<tr><td data-selectable-selector-column>3</td><td data-type="date">2017-05-06</td><td>C</td></tr>',
        ]
    });

    var brick = widget.brick();
    var element = brick.element();
    var selections = brick.table().selections();

    equal(false, $('tr[data-row-index="1"]').is('.is-selected'));
    equal('', element.find('.brick-selection-title').text());

    deepEqual([
        {selected: false, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="2"]', element).get()},
    ], selections.selectables().map(this.selectionItemInfo));

    deepEqual([], selections.selected());

    brick.setLoadingState(true, 'Loading...');

    // selection is disabled on loading
    $('tr[data-row-index="1"] td[data-selectable-selector-column]', element).click();

    equal('', element.find('.brick-selection-title').text());
    deepEqual([], selections.selected());

    // toggle all is disabled on loading
    $('.row-selector-all', element).click();

    equal('', element.find('.brick-selection-title').text());
    deepEqual([], selections.selected());
});

QUnit.test('creme.bricks.Brick.table (toggle selection, controller)', function(assert) {
    var widget = this.createBrickTable({
        columns: [
            '<th data-selectable-selector-column><input class="row-selector-all" type="checkbox" /></th>',
            '<th data-table-primary-column>Id</th>',
            '<th data-type="date">Created on</th>',
            '<th>Name</th>'
        ],
        rows: [
            '<tr><td data-selectable-selector-column>1</td><td data-type="date">2017-05-08</td><td>A</td></tr>',
            '<tr><td data-selectable-selector-column>2</td><td data-type="date">2017-05-07</td><td>B</td></tr>',
            '<tr><td data-selectable-selector-column>3</td><td data-type="date">2017-05-06</td><td>C</td></tr>',
        ]
    });

    var brick = widget.brick();
    var element = brick.element();
    var selections = brick.table().selections();

    equal(false, $('tr[data-row-index="0"]').is('.is-selected'));
    equal(false, $('tr[data-row-index="1"]').is('.is-selected'));
    equal(false, $('tr[data-row-index="2"]').is('.is-selected'));
    equal('', element.find('.brick-selection-title').text());

    deepEqual([
        {selected: false, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="2"]', element).get()},
    ], selections.selectables().map(this.selectionItemInfo));

    deepEqual([], selections.selected().map(this.selectionItemInfo));

    selections.toggle(1, true);
    selections.toggle(2, true);

    equal(false, $('tr[data-row-index="0"]').is('.is-selected'));
    equal(true, $('tr[data-row-index="1"]').is('.is-selected'));
    equal(true, $('tr[data-row-index="2"]').is('.is-selected'));

    equal('2 entries on 3', element.find('.brick-selection-title').text());
    deepEqual([
        {selected: true, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="2"]', element).get()},
    ], selections.selected().map(this.selectionItemInfo));

    selections.toggleAll(false);

    equal(false, $('tr[data-row-index="0"]').is('.is-selected'));
    equal(false, $('tr[data-row-index="1"]').is('.is-selected'));
    equal(false, $('tr[data-row-index="2"]').is('.is-selected'));
    equal('', element.find('.brick-selection-title').text());

    deepEqual([], selections.selected());
});

QUnit.test('creme.bricks.Brick.table (not sortable)', function(assert) {
    var widget = this.createBrickTable({
        columns: [
            '<th data-table-primary-column>Id</th>',
            '<th data-type="date">Created on</th>',
            '<th>Name</th>'
        ],
        rows: [
            '<tr><td>1</td><td data-type="date">2017-05-08</td><td>A</td></tr>',
            '<tr><td>2</td><td data-type="date">2017-05-07</td><td>B</td></tr>',
            '<tr><td>3</td><td data-type="date">2017-05-06</td><td>C</td></tr>',
        ]
    });

    var brick = widget.brick();
    var element = brick.element();

    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    $('th', element).click();

    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.table (toggle sort)', function(assert) {
    var options = {
        columns: [
            '<th data-table-primary-column>Id</th>',
            '<th data-type="date" class="brick-table-sortable" data-sort-field="created">Created on</th>',
            '<th class="brick-table-sortable" data-sort-field="name" data-sort-order="desc">Name</th>'
        ],
        rows: [
            '<tr><td>1</td><td data-type="date">2017-05-08</td><td>A</td></tr>',
            '<tr><td>2</td><td data-type="date">2017-05-07</td><td>B</td></tr>',
            '<tr><td>3</td><td data-type="date">2017-05-06</td><td>C</td></tr>',
        ]
    };

    var widget = this.createBrickTable(options);
    var brick = widget.brick();

    this.setBrickReloadContent('brick-for-test', this.createBrickTableHtml(options));

    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    brick = $('#brick-for-test').creme().widget().brick();
    equal(true, brick.isBound());

    // use brick.element() each time because it changes on reload.
    $('th[data-sort-field="created"]', brick.element()).click();

    deepEqual([
        {'brick-for-test_order': '-created', brick_id: ['brick-for-test'], extra_data: '{}'}
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));

    brick = $('#brick-for-test').creme().widget().brick();
    equal(true, brick.isBound());

    $('th[data-sort-field="name"]', brick.element()).click();

    deepEqual([
        {'brick-for-test_order': '-created', brick_id: ['brick-for-test'], extra_data: '{}'},
        {'brick-for-test_order': 'name', brick_id: ['brick-for-test'], extra_data: '{}'}
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.table (toggle sort, loading)', function(assert) {
    var options = {
        columns: [
            '<th data-table-primary-column>Id</th>',
            '<th data-type="date" class="brick-table-sortable" data-sort-field="created">Created on</th>',
            '<th class="brick-table-sortable" data-sort-field="name" data-sort-order="desc">Name</th>'
        ],
        rows: [
            '<tr><td>1</td><td data-type="date">2017-05-08</td><td>A</td></tr>',
            '<tr><td>2</td><td data-type="date">2017-05-07</td><td>B</td></tr>',
            '<tr><td>3</td><td data-type="date">2017-05-06</td><td>C</td></tr>',
        ]
    };

    var widget = this.createBrickTable(options);
    var brick = widget.brick();

    this.setBrickReloadContent('brick-for-test', this.createBrickTableHtml(options));

    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    brick.setLoadingState(true, 'Loading...');

    // sorting is disabled on loading
    $('th[data-sort-field="created"]', brick.element()).click();

    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    // sorting is disabled on loading
    $('th[data-sort-field="name"]', brick.element()).click();

    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});
