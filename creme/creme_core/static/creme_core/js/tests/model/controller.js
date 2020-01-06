(function($) {

QUnit.module("creme.model.controller.js", new QUnitMixin(QUnitEventMixin, {
    assertItems: function(element, expected) {
        var items = $('li', element);

        equal(items.length, expected.length);

        items.each(function(index) {
            equal($(this).html(), expected[index]);
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

    equal(undefined, controller.target());
    this.assertItems(element, []);

    controller.target(element);

    equal(element, controller.target());
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

    equal(undefined, controller.renderer());
    this.assertItems(element, []);

    controller.renderer(renderer);

    equal(renderer, controller.renderer());
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

    equal(undefined, controller.model());
    this.assertItems(element, []);

    controller.model(model);

    equal(model, controller.model());
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

    deepEqual([], controller._cleanIndices([], 0, 0));
    deepEqual([], controller._cleanIndices([], 0, 100));

    deepEqual([[0, 0]], controller._cleanIndices([[0, 10]], 0, 0));
    deepEqual([[0, 5]], controller._cleanIndices([[0, 10]], 0, 5));
    deepEqual([[0, 10]], controller._cleanIndices([[0, 10]], 0, 100));

    deepEqual([[5, 10]], controller._cleanIndices([[0, 10]], 5, 100));
    deepEqual([[50, 50]], controller._cleanIndices([[0, 10]], 50, 100));
    deepEqual([[100, 100]], controller._cleanIndices([[0, 10]], 100, 100));

    deepEqual([[0, 10]], controller._cleanIndices([[10, 0]], 0, 10));

    deepEqual([[1, 2], [3, 4], [5, 10]], controller._cleanIndices([[10, 5], [4, 3], [1, 2]], 0, 10));
});

QUnit.test('creme.model.SelectionController._optimizeRanges', function(assert) {
    var model = new creme.model.Array([]);
    var controller = new creme.model.SelectionController().model(model);

    deepEqual([], controller._optimizeRanges([]));
    deepEqual([[0, 10]], controller._optimizeRanges([[0, 10]]));

    // disjointed
    deepEqual([[0, 2], [4, 5]], controller._optimizeRanges([[0, 2], [4, 5]]));
    deepEqual([[0, 2], [4, 5]], controller._optimizeRanges([[4, 5], [0, 2]]));

    // neighbors
    deepEqual([[0, 5]], controller._optimizeRanges([[0, 2], [3, 5]]));
    deepEqual([[1, 5]], controller._optimizeRanges([[1, 1], [1, 2], [3, 5]]));

    // override
    deepEqual([[0, 5]], controller._optimizeRanges([[0, 2], [2, 5]]));
    deepEqual([[0, 5]], controller._optimizeRanges([[0, 3], [2, 5]]));
    deepEqual([[0, 5]], controller._optimizeRanges([[0, 2], [1, 5]]));

    // inclusion
    deepEqual([[0, 4]], controller._optimizeRanges([[0, 4], [1, 3]]));
    deepEqual([[0, 4]], controller._optimizeRanges([[0, 4], [1, 2], [2, 3], [4, 4]]));
});

QUnit.test('creme.model.SelectionController.select (default)', function(assert) {
    var model = new creme.model.Array([{value: 1}, {value: 5}, {value: 3}, {value: 8}, {value: 7}]);
    var controller = new creme.model.SelectionController().model(model);

    equal(model, controller.model());
    deepEqual([], controller.selected());
    deepEqual([{value: 1}, {value: 5}, {value: 3}, {value: 8}, {value: 7}], controller.selectables());

    controller.select(58);
    deepEqual([], controller.selected());

    controller.select(1);
    deepEqual([{value: 5, selected: true}], controller.selected());

    controller.select(0);
    deepEqual([{value: 1, selected: true}], controller.selected());

    controller.select(4);
    deepEqual([{value: 7, selected: true}], controller.selected());

    controller.select([[2, 4]]);
    deepEqual([{value: 3, selected: true}, {value: 8, selected: true}, {value: 7, selected: true}], controller.selected());

    controller.select([0, 2]);
    deepEqual([{value: 1, selected: true}, {value: 3, selected: true}], controller.selected());

    // inverted range
    controller.select([[4, 2]]);
    deepEqual([{value: 3, selected: true}, {value: 8, selected: true}, {value: 7, selected: true}], controller.selected());

    // function range
    controller.select(function(ctrl) {
        return [[1, ctrl.model().all().length - 2]];
    });
    deepEqual([{value: 5, selected: true}, {value: 3, selected: true}, {value: 8, selected: true}], controller.selected());

    // multiple ranges
    controller.select([4, [3, 2], 1]);
    deepEqual([{value: 5, selected: true},
               {value: 3, selected: true},
               {value: 8, selected: true},
               {value: 7, selected: true}], controller.selected());

    // duplicate
    controller.select([4, 4, 1, [1, 2], [1, 2]]);
    deepEqual([{value: 5, selected: true},
               {value: 3, selected: true},
               {value: 7, selected: true}], controller.selected());
});

QUnit.test('creme.model.SelectionController.select (inclusive)', function(assert) {
    var model = new creme.model.Array([{value: 1}, {value: 5}, {value: 3}, {value: 8}, {value: 7}]);
    var controller = new creme.model.SelectionController().model(model);

    equal(model, controller.model());
    deepEqual([], controller.selected());
    deepEqual([{value: 1}, {value: 5}, {value: 3}, {value: 8}, {value: 7}], controller.selectables());

    controller.select(58, true);
    deepEqual([], controller.selected());

    controller.select(1, true);
    deepEqual([{value: 5, selected: true}], controller.selected());

    controller.select([[2, 4]], true);
    deepEqual([{value: 5, selected: true}, {value: 3, selected: true}, {value: 8, selected: true}, {value: 7, selected: true}], controller.selected());

    controller.select([0, 2], true);
    deepEqual([{value: 1, selected: true},
               {value: 5, selected: true},
               {value: 3, selected: true},
               {value: 8, selected: true},
               {value: 7, selected: true}], controller.selected());
});

QUnit.test('creme.model.SelectionController.unselect (default)', function(assert) {
    var model = new creme.model.Array([{value: 1}, {value: 5}, {value: 3}]);
    var controller = new creme.model.SelectionController().model(model);

    equal(model, controller.model());
    deepEqual([], controller.selected());
    deepEqual([{value: 1}, {value: 5}, {value: 3}], controller.selectables());

    controller.select([0, 2]);
    deepEqual([{value: 1, selected: true}, {value: 3, selected: true}], controller.selected());

    controller.unselect(58);
    deepEqual([{value: 1, selected: true}, {value: 3, selected: true}], controller.selected());

    controller.unselect(2);
    deepEqual([{value: 1, selected: true}], controller.selected());
});

QUnit.test('creme.model.SelectionController.select (not selectable)', function(assert) {
    var model = new creme.model.Array([{value: 2}, {value: 5}, {value: 4}, {value: 3}]);
    var controller = new creme.model.SelectionController().model(model);
    var filter = function(item) { return (item.value % 2) === 0; };

    controller.selectionFilter(filter);

    equal(model, controller.model());
    deepEqual([], controller.selected());
    deepEqual(true, filter({value: 2}));
    deepEqual(false, filter({value: 3}));
    deepEqual([{value: 2}, {value: 4}], controller.selectables());

    controller.select([58]);
    deepEqual([], controller.selected());

    // not selectable
    controller.select([1]);
    deepEqual([], controller.selected());

    // only update selectable ones
    controller.select([0, 1, 2, 3]);
    deepEqual([{value: 2, selected: true}, {value: 4, selected: true}], controller.selected());

    controller.select([[0, 1]]);
    deepEqual([{value: 2, selected: true}], controller.selected());

    controller.select([[0, 3]]);
    deepEqual([{value: 2, selected: true}, {value: 4, selected: true}], controller.selected());
});

QUnit.test('creme.model.SelectionController.select (empty selection)', function(assert) {
    var model = new creme.model.Array([{value: 2, selected: false},
                                       {value: 5, selected: true},
                                       {value: 4, selected: false},
                                       {value: 3, selected: true}]);
    var controller = new creme.model.SelectionController().model(model);
    controller.on('change', this.mockListener('selection'));

    deepEqual([{value: 5, selected: true}, {value: 3, selected: true}], controller.selected());

    controller.select([]);
    deepEqual([], controller.selected());
    deepEqual([['change']], this.mockListenerCalls('selection'));
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

    equal(model, controller.model());
    deepEqual([], controller.selected());

    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('update'));
    deepEqual([], this.mockListenerCalls('selection'));

    // select out of bound index
    controller.select([58]);
    deepEqual([], controller.selected());

    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('update'));
    deepEqual([], this.mockListenerCalls('selection'), 'out of bound index');

    // select multiple items
    this.resetMockListenerCalls();
    controller.select([1, 3]);
    deepEqual([{value: 5, selected: true}, {value: 3, selected: true}], controller.selected());

    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([['update', [{value: 5, selected: true}], 1, 1, [{value: 5, selected: true}], 'select'],
               ['update', [{value: 3, selected: true}], 3, 3, [{value: 3, selected: true}], 'select']], this.mockListenerCalls('update'), 'select [1,3]');
    deepEqual([['change']], this.mockListenerCalls('selection'));

    // remove selected item
    this.resetMockListenerCalls();
    model.removeAt(1);

    deepEqual([{value: 3, selected: true}], controller.selected());

    deepEqual([['remove', [{value: 5, selected: true}], 1, 1, 'remove']], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'), 'remove');

    // append selected item
    this.resetMockListenerCalls();
    model.append({value: 12, selected: true});

    deepEqual([{value: 3, selected: true}, {value: 12, selected: true}], controller.selected());

    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([['add', [{value: 12, selected: true}], 3, 3, 'insert']], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'), 'append');

    // insert selected item
    this.resetMockListenerCalls();
    model.set({value: 15, selected: true}, 0);

    deepEqual([{value: 15, selected: true}, {value: 3, selected: true}, {value: 12, selected: true}], controller.selected());

    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([['update', [{value: 15, selected: true}], 0, 0, [{value: 2, selected: false}], 'set']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'), 'set');
});

QUnit.test('creme.model.SelectionController.toggle', function(assert) {
    var model = new creme.model.Array([{value: 2}, {value: 5}, {value: 4}, {value: 3}]);
    model.bind('update', this.mockListener('update'));

    var controller = new creme.model.SelectionController().model(model);
    controller.on('change', this.mockListener('selection'));

    equal(model, controller.model());
    deepEqual([], controller.selected());

    deepEqual([], this.mockListenerCalls('update'));
    deepEqual([], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggle(1);
    deepEqual([{value: 5, selected: true}], controller.selected());

    deepEqual([['update', [{value: 5, selected: true}], 1, 1, [{value: 5, selected: true}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggle(1);
    deepEqual([], controller.selected());

    deepEqual([['update', [{value: 5, selected: false}], 1, 1, [{value: 5, selected: false}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggle(1, true);
    deepEqual([{value: 5, selected: true}], controller.selected());

    deepEqual([['update', [{value: 5, selected: true}], 1, 1, [{value: 5, selected: true}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggle(1, true);
    deepEqual([{value: 5, selected: true}], controller.selected());

    deepEqual([], this.mockListenerCalls('update'));
    deepEqual([], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggle(1, false);
    deepEqual([], controller.selected());

    deepEqual([['update', [{value: 5, selected: false}], 1, 1, [{value: 5, selected: false}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));
});

QUnit.test('creme.model.SelectionController.toggleAll', function(assert) {
    var model = new creme.model.Array([{value: 2}, {value: 5}, {value: 4}]);
    model.bind('update', this.mockListener('update'));

    var controller = new creme.model.SelectionController().model(model);
    controller.on('change', this.mockListener('selection'));

    equal(model, controller.model());
    deepEqual([], controller.selected());
    deepEqual([], this.mockListenerCalls('update'));
    deepEqual([], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggleAll();
    deepEqual([{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}], controller.selected());

    deepEqual([['update', [{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}],
                          0, 2,
                          [{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}],
                          'select']
              ], this.mockListenerCalls('update'), 'toggle all select');
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggleAll();
    deepEqual([], controller.selected());

    deepEqual([['update', [{value: 2, selected: false}, {value: 5, selected: false}, {value: 4, selected: false}],
                          0, 2,
                          [{value: 2, selected: false}, {value: 5, selected: false}, {value: 4, selected: false}],
                          'select']
              ], this.mockListenerCalls('update'), 'toggle all unselect');
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggleAll(true);
    deepEqual([{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}], controller.selected());

    deepEqual([['update', [{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}],
                          0, 2,
                          [{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}],
                          'select']
              ], this.mockListenerCalls('update'), 'toggle all force select');
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggle(2);
    deepEqual([{value: 2, selected: true}, {value: 5, selected: true}], controller.selected());

    deepEqual([['update', [{value: 4, selected: false}], 2, 2, [{value: 4, selected: false}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggleAll(true);
    deepEqual([{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}], controller.selected());

    deepEqual([['update', [{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}],
                          0, 2,
                          [{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}],
                          'select']
               ], this.mockListenerCalls('update'), 'toggle all select');

    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggleAll(false);
    deepEqual([], controller.selected());

    deepEqual([['update', [{value: 2, selected: false}, {value: 5, selected: false}, {value: 4, selected: false}],
                          0, 2,
                          [{value: 2, selected: false}, {value: 5, selected: false}, {value: 4, selected: false}],
                          'select']
               ], this.mockListenerCalls('update'), 'toggle all unselect');
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggle(2);
    deepEqual([{value: 4, selected: true}], controller.selected());

    deepEqual([['update', [{value: 4, selected: true}], 2, 2, [{value: 4, selected: true}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockListenerCalls();
    controller.toggleAll(false);
    deepEqual([], controller.selected());

    deepEqual([['update', [{value: 2, selected: false}, {value: 5, selected: false}, {value: 4, selected: false}],
                          0, 2,
                          [{value: 2, selected: false}, {value: 5, selected: false}, {value: 4, selected: false}],
                          'select']
               ], this.mockListenerCalls('update'), 'toggle all unselect');
    deepEqual([['change']], this.mockListenerCalls('selection'));
});

QUnit.test('creme.model.SelectionController.select/unselectAll', function(assert) {
    var model = new creme.model.Array([{value: 2}, {value: 5}, {value: 4}]);
    model.bind('update', this.mockListener('update'));

    var controller = new creme.model.SelectionController().model(model);
    controller.on('change', this.mockListener('selection'));

    controller.selectAll();
    deepEqual([{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}], controller.selected());

    deepEqual([['update', [{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}],
                          0, 2,
                          [{value: 2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}],
                          'select']
               ], this.mockListenerCalls('update'), 'toggle all select');

    this.resetMockListenerCalls();
    controller.unselectAll();
    deepEqual([], controller.selected());

    deepEqual([['update', [{value: 2, selected: false}, {value: 5, selected: false}, {value: 4, selected: false}],
                          0, 2,
                          [{value: 2, selected: false}, {value: 5, selected: false}, {value: 4, selected: false}],
                          'select']
               ], this.mockListenerCalls('update'), 'toggle all unselect');
    deepEqual([['change']], this.mockListenerCalls('selection'));
});

QUnit.test('creme.model.SelectionController.model (change)', function(assert) {
    var model = new creme.model.Array([{value: 2}, {value: 5}, {value: 4}]);
    var modelB = new creme.model.Array([{value: 7}, {value: 13}]);
    model.bind('update', this.mockListener('update'));

    var controller = new creme.model.SelectionController();

    // no model
    deepEqual([], controller.selectables());

    controller.model(model);
    deepEqual([{value: 2}, {value: 5}, {value: 4}], controller.selectables());

    // other model
    controller.model(modelB);
    deepEqual([{value: 7}, {value: 13}], controller.selectables());

    // remove model
    controller.model(null);
    deepEqual([], controller.selectables());
});

}(jQuery));
