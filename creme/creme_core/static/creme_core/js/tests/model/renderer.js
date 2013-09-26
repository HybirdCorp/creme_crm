module("creme.model.renderer.js", {
    setup: function() {
    },

    teardown: function() {
    }
});

assertItems = function(element, expected) {
    var items = $('li', element);

    equal(items.length, expected.length);

    items.each(function(index) {
        equal($(this).html(), expected[index]);
    });
}

test('creme.model.ListRenderer.constructor', function() {
    var model = new creme.model.Array();
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer(element, model);

    equal(model, renderer.model());
    equal(element, renderer.target());

    var renderer = new creme.model.ListRenderer();

    equal(undefined, renderer.model());
    equal(undefined, renderer.target());
});

test('creme.model.ListRenderer (empty model)', function() {
    var model = new creme.model.Array();
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer(element, model);

    equal($('li', element).length, 0);
});

test('creme.model.ListRenderer (filled model)', function() {
    var model = new creme.model.Array(['a', 'b']);
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer(element, model);

    assertItems(element, []);

    renderer.redraw();
    assertItems(element, ['a', 'b']);
});

test('creme.model.ListRenderer (empty model, add)', function() {
    var model = new creme.model.Array();
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer(element, model).redraw();

    assertItems(element, []);

    model.append(['a', 'b']);
    assertItems(element, ['a', 'b']);
});

test('creme.model.ListRenderer (filled, model, add)', function() {
    var model = new creme.model.Array(['a', 'b']);
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer(element, model).redraw();

    assertItems(element, ['a', 'b']);

    model.append(['c', 'd']);
    assertItems(element, ['a', 'b', 'c', 'd']);
});

test('creme.model.ListRenderer (remove)', function() {
    var model = new creme.model.Array(['a', 'b', 'c', 'd']);
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer(element, model).redraw();

    assertItems(element, ['a', 'b', 'c', 'd']);

    model.removeAt(1);
    assertItems(element, ['a', 'c', 'd']);

    model.removeAt(2);
    assertItems(element, ['a', 'c']);
});

test('creme.model.ListRenderer (update)', function() {
    var model = new creme.model.Array(['a', 'b', 'c', 'd']);
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer(element, model).redraw();

    assertItems(element, ['a', 'b', 'c', 'd']);

    model.set('g', 1);
    assertItems(element, ['a', 'g', 'c', 'd']);

    model.set('k', 2);
    assertItems(element, ['a', 'g', 'k', 'd']);
});

test('creme.model.ListRenderer (switch model)', function() {
    var model = new creme.model.Array();
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer(element, model).redraw();

    equal($('option', element).length, 0);

    model.append(['a', 'b']);
    assertItems(element, ['a', 'b']);

    var model = new creme.model.Array(['x', 'y', 'z'])

    renderer.model(model).redraw();
    assertItems(element, ['x', 'y', 'z']);
});

test('creme.model.ListRenderer (reset model)', function() {
    var model = new creme.model.Array(['a', 'b', 'c', 'd']);
    var element = $('<ul></ul>');
    var renderer = new creme.model.ListRenderer(element, model).redraw();

    assertItems(element, ['a', 'b', 'c', 'd']);

    model.reset(['g', 'k']);
    assertItems(element, ['g', 'k']);

    model.reset(['x', 'y', 'z', 'a']);
    assertItems(element, ['x', 'y', 'z', 'a']);
});

assertOptions = function(element, expected) {
    var options = $('option', element);

    equal(options.length, expected.length);

    options.each(function(index) {
        equal($(this).attr('value'), expected[index].value);
        equal($(this).html(), expected[index].label);
    });
}

test('creme.model.ChoiceRenderer.constructor', function() {
    var model = new creme.model.Array();
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceRenderer(element, model).redraw();

    equal(model, renderer.model());
    equal(element, renderer.target());

    var renderer = new creme.model.ChoiceRenderer();

    equal(undefined, renderer.model());
    equal(undefined, renderer.target());
});

test('creme.model.ChoiceRenderer (empty model)', function() {
    var model = new creme.model.Array();
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceRenderer(element, model).redraw();

    equal($('option', element).length, 0);
});

test('creme.model.ChoiceRenderer (filled model)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {value:2, label:'b'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceRenderer(element, model).redraw();

    assertOptions(element, [{value:1, label:'a'},
                            {value:2, label:'b'}]);
});

test('creme.model.ChoiceRenderer (empty model, add)', function() {
    var model = new creme.model.Array();
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceRenderer(element, model).redraw();

    assertOptions(element, []);

    model.append([{value:1, label:'a'},
                  {value:2, label:'b'}]);

    assertOptions(element, [{value:1, label:'a'},
                            {value:2, label:'b'}]);
});

test('creme.model.ChoiceRenderer (filled, model, add)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {value:2, label:'b'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceRenderer(element, model).redraw();

    assertOptions(element, [{value:1, label:'a'},
                            {value:2, label:'b'}]);

    model.append([{value:3, label:'c'},
                  {value:4, label:'d'}]);

    assertOptions(element, [{value:1, label:'a'},
                            {value:2, label:'b'},
                            {value:3, label:'c'},
                            {value:4, label:'d'}]);
});

test('creme.model.ChoiceRenderer (remove)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {value:2, label:'b'},
                                       {value:3, label:'c'},
                                       {value:4, label:'d'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceRenderer(element, model).redraw();

    assertOptions(element, [{value:1, label:'a'},
                            {value:2, label:'b'},
                            {value:3, label:'c'},
                            {value:4, label:'d'}]);

    model.removeAt(1);

    assertOptions(element, [{value:1, label:'a'},
                            {value:3, label:'c'},
                            {value:4, label:'d'}]);

    model.removeAt(2);

    assertOptions(element, [{value:1, label:'a'},
                            {value:3, label:'c'}]);
});

test('creme.model.ChoiceRenderer (update)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {value:2, label:'b'},
                                       {value:3, label:'c'},
                                       {value:4, label:'d'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceRenderer(element, model).redraw();

    assertOptions(element, [{value:1, label:'a'},
                            {value:2, label:'b'},
                            {value:3, label:'c'},
                            {value:4, label:'d'}]);

    model.set({value:58, label:'g'}, 1);

    assertOptions(element, [{value:1, label:'a'},
                            {value:58, label:'g'},
                            {value:3, label:'c'},
                            {value:4, label:'d'}]);

    model.set({value:12, label:'k'}, 2);

    assertOptions(element, [{value:1, label:'a'},
                            {value:58, label:'g'},
                            {value:12, label:'k'},
                            {value:4, label:'d'}]);
});

test('creme.model.ChoiceRenderer (switch model)', function() {
    var model = new creme.model.Array();
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceRenderer(element, model).redraw();

    equal($('option', element).length, 0);

    model.append([{value:1, label:'a'},
                  {value:2, label:'b'}]);

    assertOptions(element, [{value:1, label:'a'},
                            {value:2, label:'b'}]);

    var model = new creme.model.Array([{value:8, label:'x'},
                                       {value:7, label:'y'},
                                       {value:6, label:'z'}])

    renderer.model(model).redraw();

    assertOptions(element, [{value:8, label:'x'},
                            {value:7, label:'y'},
                            {value:6, label:'z'}]);
});

test('creme.model.ChoiceRenderer (reset model)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {value:2, label:'b'},
                                       {value:3, label:'c'},
                                       {value:4, label:'d'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceRenderer(element, model).redraw();

    assertOptions(element, [{value:1, label:'a'},
                            {value:2, label:'b'},
                            {value:3, label:'c'},
                            {value:4, label:'d'}]);

    model.reset([{value:58, label:'g'},
                 {value:12, label:'k'}]);

    assertOptions(element, [{value:58, label:'g'},
                            {value:12, label:'k'}]);

    model.reset([{value:1, label:'x'},
                 {value:2, label:'y'},
                 {value:3, label:'z'},
                 {value:4, label:'a'}]);

    assertOptions(element, [{value:1, label:'x'},
                            {value:2, label:'y'},
                            {value:3, label:'z'},
                            {value:4, label:'a'}]);
});
