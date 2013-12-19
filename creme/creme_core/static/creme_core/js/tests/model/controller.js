module("creme.model.controller.js", {
    setup: function() {
        this.resetMockCalls();
    },

    teardown: function() {
    },

    resetMockCalls: function() {
        this._eventListenerCalls = {};
    },

    mockListenerCalls: function(name)
    {
        if (this._eventListenerCalls[name] === undefined)
            this._eventListenerCalls[name] = [];

        return this._eventListenerCalls[name];
    },

    mockListener: function(name)
    {
        var self = this;
        return (function(name) {return function() {
            self.mockListenerCalls(name).push(Array.copy(arguments));
        }})(name);
    }
});

function assertRaises(block, expected, message)
{
    raises(block,
           function(error) {
                ok(error instanceof expected, 'error is ' + expected);
                equal(message, '' + error);
                return true;
           });
}

function assertItems(element, expected)
{
    var items = $('li', element);

    equal(items.length, expected.length);

    items.each(function(index) {
        equal($(this).html(), expected[index]);
    });
}

test('creme.model.CollectionController.target', function() {
    var model = new creme.model.Array(['a', 'b']);
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer();
    var controller = new creme.model.CollectionController();

    controller.renderer(renderer)
              .model(model)
              .redraw();

    equal(undefined, controller.target());
    assertItems(element, []);

    controller.target(element);

    equal(element, controller.target());
    assertItems(element, []);

    controller.redraw();

    assertItems(element, ['a', 'b']);
});

test('creme.model.CollectionController.renderer', function() {
    var model = new creme.model.Array(['a', 'b']);
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer();
    var controller = new creme.model.CollectionController();

    controller.model(model)
              .target(element)
              .redraw();

    equal(undefined, controller.renderer());
    assertItems(element, []);

    controller.renderer(renderer);

    equal(renderer, controller.renderer());
    assertItems(element, []);

    controller.redraw();

    assertItems(element, ['a', 'b']);
});

test('creme.model.CollectionController.model', function() {
    var model = new creme.model.Array(['a', 'b']);
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer();
    var controller = new creme.model.CollectionController();

    controller.renderer(renderer)
              .target(element)
              .redraw();

    equal(undefined, controller.model());
    assertItems(element, []);

    controller.model(model);

    equal(model, controller.model());
    assertItems(element, []);

    controller.redraw();

    assertItems(element, ['a', 'b']);

    controller.model(new creme.model.Array([1, 2, 3]));
    controller.redraw();

    assertItems(element, [1, 2, 3]);
});

test('creme.model.SelectionController.select (default)', function() {
    var model = new creme.model.Array([{value:1}, {value:5}, {value:3}, {value:8}, {value:7}])
    var controller = new creme.model.SelectionController().model(model);

    equal(model, controller.model());
    deepEqual([], controller.selected());
    deepEqual([{value:1}, {value:5}, {value:3}, {value:8}, {value:7}], controller.selectables());

    controller.select(58);
    deepEqual([], controller.selected());

    controller.select(1);
    deepEqual([{value: 5, selected:true}], controller.selected());

    controller.select([[2, 4]]);
    deepEqual([{value: 3, selected:true}, {value:8, selected:true}, {value:7, selected:true}], controller.selected());

    controller.select([0, 2]);
    deepEqual([{value: 1, selected:true}, {value:3, selected:true}], controller.selected());
});

test('creme.model.SelectionController.select (inclusive)', function() {
    var model = new creme.model.Array([{value:1}, {value:5}, {value:3}, {value:8}, {value:7}])
    var controller = new creme.model.SelectionController().model(model);

    equal(model, controller.model());
    deepEqual([], controller.selected());
    deepEqual([{value:1}, {value:5}, {value:3}, {value:8}, {value:7}], controller.selectables());

    controller.select(58, true);
    deepEqual([], controller.selected());

    controller.select(1, true);
    deepEqual([{value: 5, selected:true}], controller.selected());

    controller.select([[2, 4]], true);
    deepEqual([{value: 5, selected:true}, {value: 3, selected:true}, {value:8, selected:true}, {value:7, selected:true}], controller.selected());

    controller.select([0, 2], true);
    deepEqual([{value: 1, selected:true}, 
               {value: 5, selected:true}, 
               {value: 3, selected:true}, 
               {value: 8, selected:true}, 
               {value: 7, selected:true}], controller.selected());
});

test('creme.model.SelectionController.unselect (default)', function() {
    var model = new creme.model.Array([{value:1}, {value:5}, {value:3}])
    var controller = new creme.model.SelectionController().model(model);

    equal(model, controller.model());
    deepEqual([], controller.selected());
    deepEqual([{value:1}, {value:5}, {value:3}], controller.selectables());

    controller.select([0, 2]);
    deepEqual([{value: 1, selected:true}, {value:3, selected:true}], controller.selected());

    controller.unselect(58);
    deepEqual([{value: 1, selected:true}, {value:3, selected:true}], controller.selected());

    controller.unselect(2);
    deepEqual([{value: 1, selected:true}], controller.selected());
});

/*
test('creme.model.SelectionController.select (custom itemKey)', function() {
    var model = new creme.model.Array([{value:1}, {value:5}, {value:3}])
    var controller = new creme.model.SelectionController().model(model);

    var itemKey = function(item) {return item.value;};

    equal(model, controller.model());
    deepEqual([], controller.selected());
    deepEqual(2, itemKey({value:2}));
    deepEqual([{value:1}, {value:5}, {value:3}], controller.selectables());

    controller.select(['unknown'], itemKey);
    deepEqual([], controller.selected());

    controller.select([5], itemKey);
    deepEqual([{value: 5, selected:true}], controller.selected());

    controller.select([1, 3], itemKey);
    deepEqual([{value: 1, selected:true}, {value:3, selected:true}], controller.selected());
});
*/

test('creme.model.SelectionController.select (not selectable)', function() {
    var model = new creme.model.Array([{value:2}, {value:5}, {value:4}, {value:3}])
    var controller = new creme.model.SelectionController().model(model);
    var filter = function(item) {return (item.value % 2) === 0;};

    controller.selectionFilter(filter);

    equal(model, controller.model());
    deepEqual([], controller.selected());
    deepEqual(true, filter({value: 2}));
    deepEqual(false, filter({value: 3}));
    deepEqual([{value:2}, {value:4}], controller.selectables());

    controller.select([58]);
    deepEqual([], controller.selected());

    // not selectable
    controller.select([1]);
    deepEqual([], controller.selected());

    // only update selectable ones
    controller.select([0, 1, 2, 3]);
    deepEqual([{value: 2, selected:true}, {value:4, selected:true}], controller.selected());

    controller.select([[0, 1]]);
    deepEqual([{value: 2, selected:true}], controller.selected());

    controller.select([[0, 3]]);
    deepEqual([{value: 2, selected:true}, {value:4, selected:true}], controller.selected());
});

test('creme.model.SelectionController.select (update model)', function() {
    var model = new creme.model.Array([{value:2, selected: false},
                                       {value:5, selected: false},
                                       {value:4, selected: false},
                                       {value:3, selected: false}]);
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

    controller.select([58]);
    deepEqual([], controller.selected());

    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('update'));
    deepEqual([], this.mockListenerCalls('selection'));

    this.resetMockCalls();
    controller.select([1, 3]);
    deepEqual([{value: 5, selected: true}, {value: 3, selected: true}], controller.selected());

    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([['update', [{value: 5, selected: true}], 1, 1, [{value: 5, selected: true}], 'select'], 
               ['update', [{value: 3, selected: true}], 3, 3, [{value: 3, selected: true}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockCalls();
    model.removeAt(1);

    deepEqual([{value: 3, selected: true}], controller.selected());

    deepEqual([['remove', [{value: 5, selected: true}], 1, 1, 'remove']], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'), 'remove');

    this.resetMockCalls();
    model.append({value: 12, selected: true});

    deepEqual([{value: 3, selected: true}, {value: 12, selected: true}], controller.selected());

    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([['add', [{value: 12, selected: true}], 3, 3, 'insert']], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'), 'append');

    this.resetMockCalls();
    model.set({value: 15, selected: true}, 0);

    deepEqual([{value: 15, selected: true}, {value: 3, selected: true}, {value: 12, selected: true}], controller.selected());

    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([['update', [{value: 15, selected: true}], 0, 0, [{value: 2, selected: false}], 'set']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'), 'set');
});

test('creme.model.SelectionController.toggle', function() {
    var model = new creme.model.Array([{value:2}, {value:5}, {value:4}, {value:3}])
    model.bind('update', this.mockListener('update'));

    var controller = new creme.model.SelectionController().model(model);
    controller.on('change', this.mockListener('selection'));

    equal(model, controller.model());
    deepEqual([], controller.selected());

    deepEqual([], this.mockListenerCalls('update'));
    deepEqual([], this.mockListenerCalls('selection'));

    this.resetMockCalls();
    controller.toggle(1);
    deepEqual([{value: 5, selected: true}], controller.selected());

    deepEqual([['update', [{value: 5, selected: true}], 1, 1, [{value: 5, selected: true}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockCalls();
    controller.toggle(1);
    deepEqual([], controller.selected());

    deepEqual([['update', [{value: 5, selected: false}], 1, 1, [{value: 5, selected: false}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockCalls();
    controller.toggle(1, true);
    deepEqual([{value: 5, selected: true}], controller.selected());

    deepEqual([['update', [{value: 5, selected: true}], 1, 1, [{value: 5, selected: true}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockCalls();
    controller.toggle(1, true);
    deepEqual([{value: 5, selected: true}], controller.selected());

    deepEqual([], this.mockListenerCalls('update'));
    deepEqual([], this.mockListenerCalls('selection'));

    this.resetMockCalls();
    controller.toggle(1, false);
    deepEqual([], controller.selected());

    deepEqual([['update', [{value: 5, selected: false}], 1, 1, [{value: 5, selected: false}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));
});

test('creme.model.SelectionController.toggleAll', function() {
    var model = new creme.model.Array([{value:2}, {value:5}, {value:4}])
    model.bind('update', this.mockListener('update'));

    var controller = new creme.model.SelectionController().model(model);
    controller.on('change', this.mockListener('selection'));

    equal(model, controller.model());
    deepEqual([], controller.selected());
    deepEqual([], this.mockListenerCalls('update'));
    deepEqual([], this.mockListenerCalls('selection'));

    this.resetMockCalls();
    controller.toggleAll();
    deepEqual([{value:2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}], controller.selected());

    deepEqual([['update', [{value: 2, selected: true}], 0, 0, [{value: 2, selected: true}], 'select'],
               ['update', [{value: 5, selected: true}], 1, 1, [{value: 5, selected: true}], 'select'], 
               ['update', [{value: 4, selected: true}], 2, 2, [{value: 4, selected: true}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockCalls();
    controller.toggleAll();
    deepEqual([], controller.selected());

    deepEqual([['update', [{value: 2, selected: false}], 0, 0, [{value: 2, selected: false}], 'select'],
               ['update', [{value: 5, selected: false}], 1, 1, [{value: 5, selected: false}], 'select'], 
               ['update', [{value: 4, selected: false}], 2, 2, [{value: 4, selected: false}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockCalls();
    controller.toggleAll(true);
    deepEqual([{value:2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}], controller.selected());

    deepEqual([['update', [{value: 2, selected: true}], 0, 0, [{value: 2, selected: true}], 'select'],
               ['update', [{value: 5, selected: true}], 1, 1, [{value: 5, selected: true}], 'select'], 
               ['update', [{value: 4, selected: true}], 2, 2, [{value: 4, selected: true}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockCalls();
    controller.toggle(2);
    deepEqual([{value:2, selected: true}, {value: 5, selected: true}], controller.selected());

    deepEqual([['update', [{value: 4, selected: false}], 2, 2, [{value: 4, selected: false}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockCalls();
    controller.toggleAll(true);
    deepEqual([{value:2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}], controller.selected());

    deepEqual([['update', [{value: 4, selected: true}], 2, 2, [{value: 4, selected: true}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockCalls();
    controller.toggleAll(false);
    deepEqual([], controller.selected());

    deepEqual([['update', [{value: 2, selected: false}], 0, 0, [{value: 2, selected: false}], 'select'],
               ['update', [{value: 5, selected: false}], 1, 1, [{value: 5, selected: false}], 'select'], 
               ['update', [{value: 4, selected: false}], 2, 2, [{value: 4, selected: false}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockCalls();
    controller.toggle(2);
    deepEqual([{value: 4, selected: true}], controller.selected());

    deepEqual([['update', [{value: 4, selected: true}], 2, 2, [{value: 4, selected: true}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));

    this.resetMockCalls();
    controller.toggleAll(false);
    deepEqual([], controller.selected());

    deepEqual([['update', [{value: 4, selected: false}], 2, 2, [{value: 4, selected: false}], 'select']], this.mockListenerCalls('update'));
    deepEqual([['change']], this.mockListenerCalls('selection'));
});
