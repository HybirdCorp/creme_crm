(function($) {

QUnit.module("creme.model.controller.js", new QUnitMixin(QUnitEventMixin, {
    assertItems: function(element, expected) {
        var items = $('li', element);
        var assert = this.assert;

        assert.equal(items.length, expected.length);

        items.each(function(index) {
            assert.equal($(this).html(), expected[index]);
        });
    }
}));


QUnit.test('creme.model.CollectionController.target', function(assert) {
    var model = new creme.model.Array(['a', 'b']);
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer();
    var controller = new creme.model.CollectionController();

    controller.renderer(renderer)
              .model(model)
              .redraw();

    assert.equal(undefined, controller.target());
    this.assertItems(element, []);

    controller.target(element);

    assert.equal(element, controller.target());
    this.assertItems(element, []);

    controller.redraw();

    this.assertItems(element, ['a', 'b']);
});

QUnit.test('creme.model.CollectionController.renderer', function(assert) {
    var model = new creme.model.Array(['a', 'b']);
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer();
    var controller = new creme.model.CollectionController();

    controller.model(model)
              .target(element)
              .redraw();

    assert.equal(undefined, controller.renderer());
    this.assertItems(element, []);

    controller.renderer(renderer);

    assert.equal(renderer, controller.renderer());
    this.assertItems(element, []);

    controller.redraw();

    this.assertItems(element, ['a', 'b']);
});

QUnit.test('creme.model.CollectionController.model', function(assert) {
    var model = new creme.model.Array(['a', 'b']);
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer();
    var controller = new creme.model.CollectionController();

    controller.renderer(renderer)
              .target(element)
              .redraw();

    assert.equal(undefined, controller.model());
    this.assertItems(element, []);

    controller.model(model);

    assert.equal(model, controller.model());
    this.assertItems(element, []);

    controller.redraw();

    this.assertItems(element, ['a', 'b']);

    controller.model(new creme.model.Array([1, 2, 3]));
    controller.redraw();

    this.assertItems(element, [1, 2, 3]);
});

QUnit.test('creme.model.SelectionController._cleanIndices', function(assert) {
    var model = new creme.model.Array([]);
    var controller = new creme.model.SelectionController().model(model);

    assert.deepEqual([], controller._cleanIndices([], 0, 0));
    assert.deepEqual([], controller._cleanIndices([], 0, 100));

    assert.deepEqual([[0, 0]], controller._cleanIndices([[0, 10]], 0, 0));
    assert.deepEqual([[0, 5]], controller._cleanIndices([[0, 10]], 0, 5));
    assert.deepEqual([[0, 10]], controller._cleanIndices([[0, 10]], 0, 100));

    assert.deepEqual([[0, 0], [5, 5], [10, 10]], controller._cleanIndices([0, 5, 10], 0, 100));
    assert.deepEqual([[0, 0]], controller._cleanIndices(["NaN"], 0, 100));

    assert.deepEqual([[0, 5]], controller._cleanIndices([[5, "NaN"]], 0, 100));
    assert.deepEqual([[0, 5]], controller._cleanIndices([["NaN", 5]], 0, 100));
    assert.deepEqual([[0, 0]], controller._cleanIndices([["NaN", "NaN"]], 0, 100));

    assert.deepEqual([[5, 10]], controller._cleanIndices([[0, 10]], 5, 100));
    assert.deepEqual([[50, 50]], controller._cleanIndices([[0, 10]], 50, 100));
    assert.deepEqual([[100, 100]], controller._cleanIndices([[0, 10]], 100, 100));

    assert.deepEqual([[0, 10]], controller._cleanIndices([[10, 0]], 0, 10));

    assert.deepEqual([[1, 2], [3, 4], [5, 10]], controller._cleanIndices([[10, 5], [4, 3], [1, 2]], 0, 10));
});

QUnit.test('creme.model.SelectionController._optimizeRanges', function(assert) {
    var model = new creme.model.Array([]);
    var controller = new creme.model.SelectionController().model(model);

    assert.deepEqual([], controller._optimizeRanges([]));
    assert.deepEqual([[0, 10]], controller._optimizeRanges([[0, 10]]));

    // disjointed
    assert.deepEqual([[0, 2], [4, 5]], controller._optimizeRanges([[0, 2], [4, 5]]));
    assert.deepEqual([[0, 2], [4, 5]], controller._optimizeRanges([[4, 5], [0, 2]]));

    // neighbors
    assert.deepEqual([[0, 5]], controller._optimizeRanges([[0, 2], [3, 5]]));
    assert.deepEqual([[1, 5]], controller._optimizeRanges([[1, 1], [1, 2], [3, 5]]));

    // override
    assert.deepEqual([[0, 5]], controller._optimizeRanges([[0, 2], [2, 5]]));
    assert.deepEqual([[0, 5]], controller._optimizeRanges([[0, 3], [2, 5]]));
    assert.deepEqual([[0, 5]], controller._optimizeRanges([[0, 2], [1, 5]]));

    // inclusion
    assert.deepEqual([[0, 4]], controller._optimizeRanges([[0, 4], [1, 3]]));
    assert.deepEqual([[0, 4]], controller._optimizeRanges([[0, 4], [1, 2], [2, 3], [4, 4]]));
});

QUnit.test('creme.model.SelectionController.select (default)', function(assert) {
    var model = new creme.model.Array([{value: 1}, {value: 5}, {value: 3}, {value: 8}, {value: 7}]);
    var controller = new creme.model.SelectionController().model(model);

    assert.equal(model, controller.model());
    assert.deepEqual([], controller.selected());
    assert.deepEqual([{value: 1}, {value: 5}, {value: 3}, {value: 8}, {value: 7}], controller.selectables());

    controller.select(58);
    assert.deepEqual([], controller.selected());

    controller.select(1);
    assert.deepEqual([{value: 5, selected: true}], controller.selected());

    controller.select(0);
    assert.deepEqual([{value: 1, selected: true}], controller.selected());

    controller.select(4);
    assert.deepEqual([{value: 7, selected: true}], controller.selected());

    controller.select([[2, 4]]);
    assert.deepEqual([{value: 3, selected: true}, {value: 8, selected: true}, {value: 7, selected: true}], controller.selected());

    controller.select([0, 2]);
    assert.deepEqual([{value: 1, selected: true}, {value: 3, selected: true}], controller.selected());

    // inverted range
    controller.select([[4, 2]]);
    assert.deepEqual([{value: 3, selected: true}, {value: 8, selected: true}, {value: 7, selected: true}], controller.selected());

    // function range
    controller.select(function(ctrl) {
        return [[1, ctrl.model().all().length - 2]];
    });
    assert.deepEqual([{value: 5, selected: true}, {value: 3, selected: true}, {value: 8, selected: true}], controller.selected());

    // multiple ranges
    controller.select([4, [3, 2], 1]);
    assert.deepEqual([{value: 5, selected: true},
               {value: 3, selected: true},
               {value: 8, selected: true},
               {value: 7, selected: true}], controller.selected());

    // duplicate
    controller.select([4, 4, 1, [1, 2], [1, 2]]);
    assert.deepEqual([{value: 5, selected: true},
               {value: 3, selected: true},
               {value: 7, selected: true}], controller.selected());
});

QUnit.test('creme.model.SelectionController.select (inclusive)', function(assert) {
    var model = new creme.model.Array([{value: 1}, {value: 5}, {value: 3}, {value: 8}, {value: 7}]);
    var controller = new creme.model.SelectionController().model(model);

    assert.equal(model, controller.model());
    assert.deepEqual([], controller.selected());
    assert.deepEqual([{value: 1}, {value: 5}, {value: 3}, {value: 8}, {value: 7}], controller.selectables());

    controller.select(58, true);
    assert.deepEqual([], controller.selected());

    controller.select(1, true);
    assert.deepEqual([{value: 5, selected: true}], controller.selected());

    controller.select([[2, 4]], true);
    assert.deepEqual([{value: 5, selected: true}, {value: 3, selected: true}, {value: 8, selected: true}, {value: 7, selected: true}], controller.selected());

    controller.select([0, 2], true);
    assert.deepEqual([{value: 1, selected: true},
               {value: 5, selected: true},
               {value: 3, selected: true},
               {value: 8, selected: true},
               {value: 7, selected: true}], controller.selected());
});

QUnit.test('creme.model.SelectionController.unselect (default)', function(assert) {
    var model = new creme.model.Array([{value: 1}, {value: 5}, {value: 3}]);
    var controller = new creme.model.SelectionController().model(model);

    assert.equal(model, controller.model());
    assert.deepEqual([], controller.selected());
    assert.deepEqual([{value: 1}, {value: 5}, {value: 3}], controller.selectables());

    controller.select([0, 2]);
    assert.deepEqual([{value: 1, selected: true}, {value: 3, selected: true}], controller.selected());

    controller.unselect(58);
    assert.deepEqual([{value: 1, selected: true}, {value: 3, selected: true}], controller.selected());

    controller.unselect(2);
    assert.deepEqual([{value: 1, selected: true}], controller.selected());
});

QUnit.test('creme.model.SelectionController.select (not selectable)', function(assert) {
    var model = new creme.model.Array([{value: 2}, {value: 5}, {value: 4}, {value: 3}]);
    var controller = new creme.model.SelectionController().model(model);
    var filter = function(item) { return (item.value % 2) === 0; };

    controller.selectionFilter(filter);

    assert.equal(model, controller.model());
    assert.deepEqual([], controller.selected());
    assert.deepEqual(true, filter({value: 2}));
    assert.deepEqual(false, filter({value: 3}));
    assert.deepEqual([{value: 2}, {value: 4}], controller.selectables());

    controller.select([58]);
    assert.deepEqual([], controller.selected());

    // not selectable
    controller.select([1]);
    assert.deepEqual([], controller.selected());

    // only update selectable ones
    controller.select([0, 1, 2, 3]);
    assert.deepEqual([{value: 2, selected: true}, {value: 4, selected: true}], controller.selected());

    controller.select([[0, 1]]);
    assert.deepEqual([{value: 2, selected: true}], controller.selected());

    controller.select([[0, 3]]);
    assert.deepEqual([{value: 2, selected: true}, {value: 4, selected: true}], controller.selected());
});

QUnit.test('creme.model.SelectionController.select (empty selection)', function(assert) {
    var model = new creme.model.Array([{value: 2, selected: false},
                                       {value: 5, selected: true},
                                       {value: 4, selected: false},
                                       {value: 3, selected: true}]);
    var controller = new creme.model.SelectionController().model(model);
    controller.on('change', this.mockListener('selection'));

    assert.deepEqual([{value: 5, selected: true}, {value: 3, selected: true}], controller.selected());

    controller.select([]);
    assert.deepEqual([], controller.selected());
    assert.deepEqual([['change']], this.mockListenerCalls('selection'));
});

QUnit.test('creme.model.SelectionController.select (update model)', function(assert) {
    var model = new creme.model.Array([{value: 2, selected: false},
                                       {value: 5, selected: false},
                                       {value: 4, selected: false},
                                       {value: 3, selected: false}]);
    model.bind('update', this.mockListener('update'));
    model.bind('remove', this.mockListener('removed'));
    model.bind('add', this.mockListener('added'));

    var controller = new creme.model.SelectionController().model(model);
    controller.on('change', this.mockListener('selection'));

    assert.equal(model, controller.model());
    assert.deepEqual([], controller.selected());

    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([], this.mockListenerCalls('update'));
    assert.deepEqual([], this.mockListenerCalls('selection'));

    // select out of bound index
    controller.select([58]);
    assert.deepEqual([], controller.selected());

    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([], this.mockListenerCalls('update'));
    assert.deepEqual([], this.mockListenerCalls('selection'), 'out of bound index');

    // select multiple items
    this.resetMockListenerCalls();
    controller.select([1, 3]);
    assert.deepEqual([{value: 5, selected: true}, {value: 3, selected: true}], controller.selected());

    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([['update', [{value: 5, selected: true}], 1, 1, [{value: 5, selected: true}], 'select'],
               ['update', [{value: 3, selected: true}], 3, 3, [{value: 3, selected: true}], 'select']], this.mockListenerCalls('update'), 'select [1,3]');
    assert.deepEqual([['change']], this.mockListenerCalls('selection'));

    // remove selected item
    this.resetMockListenerCalls();
    model.removeAt(1);

    assert.deepEqual([{value: 3, selected: true}], controller.selected());

    assert.deepEqual([['remove', [{value: 5, selected: true}], 1, 1, 'remove']], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([], this.mockListenerCalls('update'));
    assert.deepEqual([['change']], this.mockListenerCalls('selection'), 'remove');

    // append selected item
    this.resetMockListenerCalls();
    model.append({value: 12, selected: true});

    assert.deepEqual([{value: 3, selected: true}, {value: 12, selected: true}], controller.selected());

    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([['add', [{value: 12, selected: true}], 3, 3, 'insert']], this.mockListenerCalls('added'));
    assert.deepEqual([], this.mockListenerCalls('update'));
    assert.deepEqual([['change']], this.mockListenerCalls('selection'), 'append');

    // insert selected item
    this.resetMockListenerCalls();
    model.set({value: 15, selected: true}, 0);

    assert.deepEqual([{value: 15, selected: true}, {value: 3, selected: true}, {value: 12, selected: true}], controller.selected());

    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([['update', [{value: 15, selected: true}], 0, 0, [{value: 2, selected: false}], 'set']], this.mockListenerCalls('update'));
    assert.deepEqual([['change']], this.mockListenerCalls('selection'), 'set');
});

QUnit.test('creme.model.SelectionController.toggle', function(assert) {
    var model = new creme.model.Array([{value: 2}, {value: 5}, {value: 4}, {value: 3}]);
    model.bind('update', this.mockListener('update'));

    var controller = new creme.model.SelectionController().model(model);
    controller.on('change', this.mockListener('selection'));

    assert.equal(model, controller.model());
    assert.deepEqual([], controller.selected());

    assert.deepEqual([], this.mockListenerCalls('update'));
    assert.deepEqual([], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggle(1);
    assert.deepEqual([{value: 5, selected: true}], controller.selected());

    assert.deepEqual([['update', [{value: 5, selected: true}], 1, 1, [{value: 5, selected: true}], 'select']], this.mockListenerCalls('update'));
    assert.deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggle(1);
    assert.deepEqual([], controller.selected());

    assert.deepEqual([['update', [{value: 5, selected: false}], 1, 1, [{value: 5, selected: false}], 'select']], this.mockListenerCalls('update'));
    assert.deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggle(1, true);
    assert.deepEqual([{value: 5, selected: true}], controller.selected());

    assert.deepEqual([['update', [{value: 5, selected: true}], 1, 1, [{value: 5, selected: true}], 'select']], this.mockListenerCalls('update'));
    assert.deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggle(1, true);
    assert.deepEqual([{value: 5, selected: true}], controller.selected());

    assert.deepEqual([], this.mockListenerCalls('update'));
    assert.deepEqual([], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggle(1, false);
    assert.deepEqual([], controller.selected());

    assert.deepEqual([['update', [{value: 5, selected: false}], 1, 1, [{value: 5, selected: false}], 'select']], this.mockListenerCalls('update'));
    assert.deepEqual([['change']], this.mockListenerCalls('selection'));
});

QUnit.test('creme.model.SelectionController.toggleAll', function(assert) {
    var model = new creme.model.Array([{value: 2}, {value: 5}, {value: 4}]);
    model.bind('update', this.mockListener('update'));

    var controller = new creme.model.SelectionController().model(model);
    controller.on('change', this.mockListener('selection'));

    assert.equal(model, controller.model());
    assert.deepEqual([], controller.selected());
    assert.deepEqual([], this.mockListenerCalls('update'));
    assert.deepEqual([], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggleAll();
    assert.deepEqual([{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}], controller.selected());

    assert.deepEqual([['update', [{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}],
                          0, 2,
                          [{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}],
                          'select']
              ], this.mockListenerCalls('update'), 'toggle all select');
    assert.deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggleAll();
    assert.deepEqual([], controller.selected());

    assert.deepEqual([['update', [{value: 2, selected: false}, {value: 5, selected: false}, {value: 4, selected: false}],
                          0, 2,
                          [{value: 2, selected: false}, {value: 5, selected: false}, {value: 4, selected: false}],
                          'select']
              ], this.mockListenerCalls('update'), 'toggle all unselect');
    assert.deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggleAll(true);
    assert.deepEqual([{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}], controller.selected());

    assert.deepEqual([['update', [{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}],
                          0, 2,
                          [{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}],
                          'select']
              ], this.mockListenerCalls('update'), 'toggle all force select');
    assert.deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggle(2);
    assert.deepEqual([{value: 2, selected: true}, {value: 5, selected: true}], controller.selected());

    assert.deepEqual([['update', [{value: 4, selected: false}], 2, 2, [{value: 4, selected: false}], 'select']], this.mockListenerCalls('update'));
    assert.deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggleAll(true);
    assert.deepEqual([{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}], controller.selected());

    assert.deepEqual([['update', [{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}],
                          0, 2,
                          [{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}],
                          'select']
               ], this.mockListenerCalls('update'), 'toggle all select');

    assert.deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggleAll(false);
    assert.deepEqual([], controller.selected());

    assert.deepEqual([['update', [{value: 2, selected: false}, {value: 5, selected: false}, {value: 4, selected: false}],
                          0, 2,
                          [{value: 2, selected: false}, {value: 5, selected: false}, {value: 4, selected: false}],
                          'select']
               ], this.mockListenerCalls('update'), 'toggle all unselect');
    assert.deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggle(2);
    assert.deepEqual([{value: 4, selected: true}], controller.selected());

    assert.deepEqual([['update', [{value: 4, selected: true}], 2, 2, [{value: 4, selected: true}], 'select']], this.mockListenerCalls('update'));
    assert.deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggleAll(false);
    assert.deepEqual([], controller.selected());

    assert.deepEqual([['update', [{value: 2, selected: false}, {value: 5, selected: false}, {value: 4, selected: false}],
                          0, 2,
                          [{value: 2, selected: false}, {value: 5, selected: false}, {value: 4, selected: false}],
                          'select']
               ], this.mockListenerCalls('update'), 'toggle all unselect');
    assert.deepEqual([['change']], this.mockListenerCalls('selection'));
});

QUnit.test('creme.model.SelectionController.select/unselectAll', function(assert) {
    var model = new creme.model.Array([{value: 2}, {value: 5}, {value: 4}]);
    model.bind('update', this.mockListener('update'));

    var controller = new creme.model.SelectionController().model(model);
    controller.on('change', this.mockListener('selection'));

    controller.selectAll();
    assert.deepEqual([{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}], controller.selected());

    assert.deepEqual([['update', [{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}],
                          0, 2,
                          [{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}],
                          'select']
               ], this.mockListenerCalls('update'), 'toggle all select');

    this.resetMockListenerCalls();
    controller.unselectAll();
    assert.deepEqual([], controller.selected());

    assert.deepEqual([['update', [{value: 2, selected: false}, {value: 5, selected: false}, {value: 4, selected: false}],
                          0, 2,
                          [{value: 2, selected: false}, {value: 5, selected: false}, {value: 4, selected: false}],
                          'select']
               ], this.mockListenerCalls('update'), 'toggle all unselect');
    assert.deepEqual([['change']], this.mockListenerCalls('selection'));
});

QUnit.test('creme.model.SelectionController.model (change)', function(assert) {
    var model = new creme.model.Array([{value: 2}, {value: 5}, {value: 4}]);
    var modelB = new creme.model.Array([{value: 7}, {value: 13}]);
    model.bind('update', this.mockListener('update'));

    var controller = new creme.model.SelectionController();

    // no model
    assert.deepEqual([], controller.selectables());

    controller.model(model);
    assert.deepEqual([{value: 2}, {value: 5}, {value: 4}], controller.selectables());

    // other model
    controller.model(modelB);
    assert.deepEqual([{value: 7}, {value: 13}], controller.selectables());

    // remove model
    controller.model(null);
    assert.deepEqual([], controller.selectables());
});

}(jQuery));
