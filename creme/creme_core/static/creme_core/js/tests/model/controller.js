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

test('creme.model.SelectionController.select', function() {
    var model = new creme.model.Array([{value:1}, {value:5}, {value:3}])
    var controller = new creme.model.SelectionController().model(model);

    equal(model, controller.model());
    deepEqual([], controller.selected());
    deepEqual(true, controller.isItemSelectable());

    controller.select(['unknown']);
    deepEqual([], controller.selected());

    controller.select([1]);
    deepEqual([{value: 5, selected:true}], controller.selected());

    controller.select([0, 2]);
    deepEqual([{value: 1, selected:true}, {value:3, selected:true}], controller.selected());
});

test('creme.model.SelectionController.select (custom itemKey)', function() {
    var model = new creme.model.Array([{value:1}, {value:5}, {value:3}])
    var controller = new creme.model.SelectionController().model(model);

    var itemKey = function(item) {return item.value;};

    equal(model, controller.model());
    deepEqual([], controller.selected());
    deepEqual(2, itemKey({value:2}));
    deepEqual(true, controller.isItemSelectable());

    controller.select(['unknown'], itemKey);
    deepEqual([], controller.selected());

    controller.select([5], itemKey);
    deepEqual([{value: 5, selected:true}], controller.selected());

    controller.select([1, 3], itemKey);
    deepEqual([{value: 1, selected:true}, {value:3, selected:true}], controller.selected());
});

test('creme.model.SelectionController.select (not selectable)', function() {
    var model = new creme.model.Array([{value:2}, {value:5}, {value:4}, {value:3}])
    var controller = new creme.model.SelectionController().model(model);

    controller.isItemSelectable = function(item) {return (item.value % 2) === 0;};

    equal(model, controller.model());
    deepEqual([], controller.selected());
    deepEqual(true, controller.isItemSelectable({value: 2}));
    deepEqual(false, controller.isItemSelectable({value: 3}));

    controller.select(['unknown']);
    deepEqual([], controller.selected());

    // not selectable
    controller.select([1]);
    deepEqual([], controller.selected());

    // only update selectable ones
    controller.select([0, 1, 2, 3]);
    deepEqual([{value: 2, selected:true}, {value:4, selected:true}], controller.selected());
});

test('creme.model.SelectionController.select (update model)', function() {
    var model = new creme.model.Array([{value:2}, {value:5}, {value:4}, {value:3}])
    var controller = new creme.model.SelectionController().model(model);

    equal(model, controller.model());
    deepEqual([], controller.selected());

    controller.select(['unknown']);
    deepEqual([], controller.selected());

    controller.select([1, 3]);
    deepEqual([{value: 5, selected: true}, {value: 3, selected: true}], controller.selected());

    model.removeAt(1);

    deepEqual([{value: 3, selected: true}], controller.selected());
});

test('creme.model.SelectionController.toggle', function() {
    var model = new creme.model.Array([{value:2}, {value:5}, {value:4}, {value:3}])
    var controller = new creme.model.SelectionController().model(model);

    equal(model, controller.model());
    deepEqual([], controller.selected());

    controller.toggle(1);
    deepEqual([{value: 5, selected: true}], controller.selected());

    controller.toggle(1);
    deepEqual([], controller.selected());

    controller.toggle(1, true);
    deepEqual([{value: 5, selected: true}], controller.selected());

    controller.toggle(1, true);
    deepEqual([{value: 5, selected: true}], controller.selected());

    controller.toggle(1, false);
    deepEqual([], controller.selected());
});

test('creme.model.SelectionController.toggleAll', function() {
    var model = new creme.model.Array([{value:2}, {value:5}, {value:4}])
    var controller = new creme.model.SelectionController().model(model);

    equal(model, controller.model());
    deepEqual([], controller.selected());

    controller.toggleAll();
    deepEqual([{value:2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}], controller.selected());

    controller.toggleAll();
    deepEqual([], controller.selected());

    controller.toggleAll(true);
    deepEqual([{value:2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}], controller.selected());

    controller.toggle(2);
    deepEqual([{value:2, selected: true}, {value: 5, selected: true}], controller.selected());

    controller.toggleAll(true);
    deepEqual([{value:2, selected: true}, {value: 5, selected: true}, {value: 4, selected: true}], controller.selected());

    controller.toggleAll(false);
    deepEqual([], controller.selected());

    controller.toggle(2);
    deepEqual([{value: 4, selected: true}], controller.selected());

    controller.toggleAll(false);
    deepEqual([], controller.selected());
});
