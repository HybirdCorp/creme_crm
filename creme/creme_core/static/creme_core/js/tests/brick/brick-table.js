(function($) {

QUnit.module("creme.bricks.table", new QUnitMixin(QUnitEventMixin, QUnitAjaxMixin, QUnitBrickMixin, {
    _brickTableItemInfo: function(d) {
        return {
            selected: d.selected,
            ui: d.ui.get()
        };
    }
}));

QUnit.test('creme.bricks.Brick.table (bind/unbind)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="${id}"></div>').appendTo(this.qunitFixture());

    brick.bind(element);

    assert.equal(true, brick.isBound());
    assert.equal(true, brick.table().isBound());

    this.assertRaises(function() {
        brick.table().bind(element);
    }, Error, 'Error: BrickTable is already bound');

    brick.unbind();

    assert.equal(false, brick.isBound());
    assert.equal(false, brick.table().isBound());

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
        ]
    });

    var brick = widget.brick();
    var element = brick.element();
    var selections = brick.table().selections();

    assert.deepEqual([], selections.selectables());
    assert.deepEqual([], selections.selected());

    assert.equal('', element.find('.brick-selection-title').text());
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
            '<tr><td data-selectable-selector-column>3</td><td data-type="date">2017-05-06</td><td>C</td></tr>'
        ]
    });

    var brick = widget.brick();
    var element = brick.element();
    var selections = brick.table().selections();

    assert.equal(false, $('tr[data-row-index="1"]').is('.is-selected'));
    assert.equal('', element.find('.brick-selection-title').text());

    assert.deepEqual([
        {selected: false, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="2"]', element).get()}
    ], selections.selectables().map(this._brickTableItemInfo));

    assert.deepEqual([], selections.selected());

    $('tr[data-row-index="1"] td[data-selectable-selector-column]', element).trigger('click');

    assert.equal(true, $('tr[data-row-index="1"]').is('.is-selected'));
    assert.equal('1 entry on 3', element.find('.brick-selection-title').text());

    assert.deepEqual([
        {selected: false, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="2"]', element).get()}
    ], selections.selectables().map(this._brickTableItemInfo));

    assert.deepEqual([
        {selected: true, ui: $('tr[data-row-index="1"]', element).get()}
    ], selections.selected().map(this._brickTableItemInfo));

    $('tr[data-row-index="1"] td[data-selectable-selector-column]', element).trigger('click');

    assert.equal(false, $('tr[data-row-index="1"]').is('.is-selected'));
    assert.equal('', element.find('.brick-selection-title').text());

    assert.deepEqual([
        {selected: false, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="2"]', element).get()}
    ], selections.selectables().map(this._brickTableItemInfo));

    assert.deepEqual([], selections.selected().map(this._brickTableItemInfo));
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
            '<tr><td><input type="checkbox" /></td><td data-selectable-selector-column>3</td><td data-type="date">2017-05-06</td><td>C</td></tr>'
        ]
    });

    var brick = widget.brick();
    var element = brick.element();
    var selections = brick.table().selections();

    assert.equal(false, $('tr[data-row-index="0"]').is('.is-selected'));
    assert.equal(false, $('tr[data-row-index="1"]').is('.is-selected'));
    assert.equal(false, $('tr[data-row-index="2"]').is('.is-selected'));

    assert.deepEqual([
        {selected: false, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="2"]', element).get()}
    ], selections.selectables().map(this._brickTableItemInfo));

    assert.deepEqual([], selections.selected());

    $('.row-selector-all', element).trigger('click');

    assert.equal(true, $('tr[data-row-index="0"]').is('.is-selected'));
    assert.equal(true, $('tr[data-row-index="1"]').is('.is-selected'));
    assert.equal(true, $('tr[data-row-index="2"]').is('.is-selected'));
    assert.equal('3 entries on 3', element.find('.brick-selection-title').text());

    assert.deepEqual([
        {selected: true, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="2"]', element).get()}
    ], selections.selectables().map(this._brickTableItemInfo));

    assert.deepEqual([
        {selected: true, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="2"]', element).get()}
    ], selections.selected().map(this._brickTableItemInfo));

    $('.row-selector-all', element).trigger('click');

    assert.equal(false, $('tr[data-row-index="0"]').is('.is-selected'));
    assert.equal(false, $('tr[data-row-index="1"]').is('.is-selected'));
    assert.equal(false, $('tr[data-row-index="2"]').is('.is-selected'));
    assert.equal('', element.find('.brick-selection-title').text());

    assert.deepEqual([
        {selected: false, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="2"]', element).get()}
    ], selections.selectables().map(this._brickTableItemInfo));

    assert.deepEqual([], selections.selected().map(this._brickTableItemInfo));

    $('.row-selector-all', element).prop('checked', true).trigger('change');
    assert.equal('3 entries on 3', element.find('.brick-selection-title').text());

    assert.deepEqual([
        {selected: true, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="2"]', element).get()}
    ], selections.selectables().map(this._brickTableItemInfo));

    assert.deepEqual([
        {selected: true, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="2"]', element).get()}
    ], selections.selected().map(this._brickTableItemInfo));
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
            '<tr><td data-selectable-selector-column>3</td><td data-type="date">2017-05-06</td><td>C</td></tr>'
        ]
    });

    var brick = widget.brick();
    var element = brick.element();
    var selections = brick.table().selections();

    assert.equal(false, $('tr[data-row-index="1"]').is('.is-selected'));
    assert.equal('', element.find('.brick-selection-title').text());

    assert.deepEqual([
        {selected: false, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="2"]', element).get()}
    ], selections.selectables().map(this._brickTableItemInfo));

    assert.deepEqual([], selections.selected());

    brick.setLoadingState(true, 'Loading…');

    // selection is disabled on loading
    $('tr[data-row-index="1"] td[data-selectable-selector-column]', element).trigger('click');

    assert.equal('', element.find('.brick-selection-title').text());
    assert.deepEqual([], selections.selected());

    // toggle all is disabled on loading
    $('.row-selector-all', element).trigger('click');

    assert.equal('', element.find('.brick-selection-title').text());
    assert.deepEqual([], selections.selected());
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
            '<tr><td data-selectable-selector-column>3</td><td data-type="date">2017-05-06</td><td>C</td></tr>'
        ]
    });

    var brick = widget.brick();
    var element = brick.element();
    var selections = brick.table().selections();

    assert.equal(false, $('tr[data-row-index="0"]').is('.is-selected'));
    assert.equal(false, $('tr[data-row-index="1"]').is('.is-selected'));
    assert.equal(false, $('tr[data-row-index="2"]').is('.is-selected'));
    assert.equal('', element.find('.brick-selection-title').text());

    assert.deepEqual([
        {selected: false, ui: $('tr[data-row-index="0"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: false, ui: $('tr[data-row-index="2"]', element).get()}
    ], selections.selectables().map(this._brickTableItemInfo));

    assert.deepEqual([], selections.selected().map(this._brickTableItemInfo));

    selections.toggle(1, true);
    selections.toggle(2, true);

    assert.equal(false, $('tr[data-row-index="0"]').is('.is-selected'));
    assert.equal(true, $('tr[data-row-index="1"]').is('.is-selected'));
    assert.equal(true, $('tr[data-row-index="2"]').is('.is-selected'));

    assert.equal('2 entries on 3', element.find('.brick-selection-title').text());
    assert.deepEqual([
        {selected: true, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="2"]', element).get()}
    ], selections.selected().map(this._brickTableItemInfo));

    selections.toggleAll(false);

    assert.equal(false, $('tr[data-row-index="0"]').is('.is-selected'));
    assert.equal(false, $('tr[data-row-index="1"]').is('.is-selected'));
    assert.equal(false, $('tr[data-row-index="2"]').is('.is-selected'));
    assert.equal('', element.find('.brick-selection-title').text());

    assert.deepEqual([], selections.selected());
});


QUnit.test('creme.bricks.Brick.table (toggle selection, row-index > 10 issue)', function(assert) {
    var widget = this.createBrickTable({
        columns: [
            '<th data-selectable-selector-column><input class="row-selector-all" type="checkbox" /></th>',
            '<th data-table-primary-column>Id</th>',
            '<th data-type="date">Created on</th>',
            '<th>Name</th>'
        ],
        rows: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13].map(function(day) {
            return '<tr><td data-selectable-selector-column>%d</td><td data-type="date">2017-05-08</td><td>A</td></tr>'.format(day);
        })
    });

    var brick = widget.brick();
    var element = brick.element();
    var selections = brick.table().selections();

    assert.equal('', element.find('.brick-selection-title').text());

    assert.deepEqual([], selections.selected().map(this._brickTableItemInfo));

    selections.toggle(1, true);
    selections.toggle(5, true);
    selections.toggle(10, true);
    selections.toggle(12, true);

    assert.equal(false, $('tr[data-row-index="0"]').is('.is-selected'));
    assert.equal(true, $('tr[data-row-index="1"]').is('.is-selected'));
    assert.equal(false, $('tr[data-row-index="4"]').is('.is-selected'));
    assert.equal(true, $('tr[data-row-index="5"]').is('.is-selected'));
    assert.equal(true, $('tr[data-row-index="10"]').is('.is-selected'));
    assert.equal(false, $('tr[data-row-index="11"]').is('.is-selected'));
    assert.equal(true, $('tr[data-row-index="12"]').is('.is-selected'));

    assert.equal('4 entries on 13', element.find('.brick-selection-title').text());
    assert.deepEqual([
        {selected: true, ui: $('tr[data-row-index="1"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="5"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="10"]', element).get()},
        {selected: true, ui: $('tr[data-row-index="12"]', element).get()}
    ], selections.selected().map(this._brickTableItemInfo));

    selections.toggleAll(false);

    assert.equal(false, $('tr[data-row-index="0"]').is('.is-selected'));
    assert.equal(false, $('tr[data-row-index="1"]').is('.is-selected'));
    assert.equal(false, $('tr[data-row-index="4"]').is('.is-selected'));
    assert.equal(false, $('tr[data-row-index="5"]').is('.is-selected'));
    assert.equal(false, $('tr[data-row-index="10"]').is('.is-selected'));
    assert.equal(false, $('tr[data-row-index="11"]').is('.is-selected'));
    assert.equal(false, $('tr[data-row-index="12"]').is('.is-selected'));

    assert.equal('', element.find('.brick-selection-title').text());

    assert.deepEqual([], selections.selected());
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
            '<tr><td>3</td><td data-type="date">2017-05-06</td><td>C</td></tr>'
        ]
    });

    var brick = widget.brick();
    var element = brick.element();

    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    $('th', element).trigger('click');

    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
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
            '<tr><td>3</td><td data-type="date">2017-05-06</td><td>C</td></tr>'
        ]
    };

    var widget = this.createBrickTable(options);
    var brick = widget.brick();
    var brick_id = brick.id();
    assert.equal('brick-creme_core-test', brick_id);
    assert.equal('creme_core-test', brick.type_id());

    this.setBrickReloadContent(brick_id, this.createBrickTableHtml(options));

    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    brick = $('#' + brick_id).creme().widget().brick();
    assert.equal(true, brick.isBound());

    // use brick.element() each time because it changes on reload.
    $('th[data-sort-field="created"]', brick.element()).trigger('click');

    assert.deepEqual([
        ['GET', {'creme_core-test_order': '-created', brick_id: ['creme_core-test'], extra_data: '{}'}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));

    brick = $('#' + brick_id).creme().widget().brick();
    assert.equal(true, brick.isBound());

    $('th[data-sort-field="name"]', brick.element()).trigger('click');

    assert.deepEqual([
        ['GET', {'creme_core-test_order': '-created', brick_id: ['creme_core-test'], extra_data: '{}'}],
        ['GET', {'creme_core-test_order': 'name', brick_id: ['creme_core-test'], extra_data: '{}'}]
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
            '<tr><td>3</td><td data-type="date">2017-05-06</td><td>C</td></tr>'
        ]
    };

    var widget = this.createBrickTable(options);
    var brick = widget.brick();

    this.setBrickReloadContent('brick-for-test', this.createBrickTableHtml(options));

    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    brick.setLoadingState(true, 'Loading…');

    // sorting is disabled on loading
    $('th[data-sort-field="created"]', brick.element()).trigger('click');

    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    // sorting is disabled on loading
    $('th[data-sort-field="name"]', brick.element()).trigger('click');

    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

}(jQuery));
