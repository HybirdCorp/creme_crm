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

    equal(options.length, expected.length, 'option count');

    options.each(function(index) {
        equal($(this).attr('value'), expected[index].value, 'option %d value'.format(index));
        equal($(this).html(), expected[index].label, 'option %d label'.format(index));

        if (expected.group) {
            equal($(this).parent().is('optgroup'), true, 'option %d has group'.format(index));
            equal($(this).parent().attr('label'), expected.group, 'option %d group label'.format(index));
        }
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

test('creme.model.ChoiceRenderer (empty model, add object)', function() {
    var model = new creme.model.Array();
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceRenderer(element, model).redraw();

    assertOptions(element, []);

    model.append([{value:{id:1, name:'a'}, label:'a'},
                  {value:{id:2, name:'b'}, label:'b'}]);

    assertOptions(element, [{value:$.toJSON({id:1, name:'a'}), label:'a'},
                            {value:$.toJSON({id:2, name:'b'}), label:'b'}]);
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

test('creme.model.ChoiceRenderer (filled, model, insert)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {value:2, label:'b'},
                                       {value:3, label:'c'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceRenderer(element, model).redraw();

    assertOptions(element, [{value:1, label:'a'},
                            {value:2, label:'b'},
                            {value:3, label:'c'}]);

    model.insert([{value:8, label:'x'},
                  {value:9, label:'y'}], 1);

    assertOptions(element, [{value:1, label:'a'},
                            {value:8, label:'x'},
                            {value:9, label:'y'},
                            {value:2, label:'b'},
                            {value:3, label:'c'}]);
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

test('creme.model.ChoiceRenderer (parse)', function() {
    deepEqual([], creme.model.ChoiceRenderer.parse($('<select></select>')));
    deepEqual([], creme.model.ChoiceRenderer.parse($('<select><options></options></select>')));

    deepEqual([{value:'1', label:'a', disabled:false, selected: false, tags: []},
               {value:'2', label:'b', disabled:false, selected: true, tags: ['tag1']},
               {value:'3', label:'c', disabled:true, selected: false, tags: ['tag2']}],
              creme.model.ChoiceRenderer.parse($('<select><options>' +
                                                     '<option value="1">a</option>' +
                                                     '<option value="2" tags="tag1" selected>b</option>' +
                                                     '<option value="3" tags="tag2" disabled>c</option>' +
                                                 '</options></select>')));
});

assertOptionGroups = function(element, expected) {
    var groups = $('optgroup', element);

    equal(groups.length, expected.length, 'optgroup count');

    groups.each(function(index) {
        equal($(this).attr('label'), expected[index], 'optgroup %d'.format(index));
    });
}

test('creme.model.ChoiceGroupRenderer (empty model, add)', function() {
    var model = new creme.model.Array();
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceGroupRenderer(element, model).redraw();

    assertOptionGroups(element, []);
    assertOptions(element, []);

    model.append([{value:1, label:'a'},
                  {value:2, label:'b'},
                  {group: 'group1', value:3, label:'c'},
                  {group: 'group1', value:4, label:'d'},
                  {group: 'group2', value:5, label:'e'}]);

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {value:2, label:'b'},
                            {group: 'group1', value:3, label:'c'},
                            {group: 'group1', value:4, label:'d'},
                            {group: 'group2', value:5, label:'e'}]);
});
test('creme.model.ChoiceGroupRenderer (filled model)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {value:2, label:'b'},
                                       {group: 'group1', value:3, label:'c'},
                                       {group: 'group1', value:4, label:'d'},
                                       {group: 'group2', value:5, label:'e'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceGroupRenderer(element, model).redraw();

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {value:2, label:'b'},
                            {group: 'group1', value:3, label:'c'},
                            {group: 'group1', value:4, label:'d'},
                            {group: 'group2', value:5, label:'e'}]);
});


test('creme.model.ChoiceGroupRenderer (filled, model, add)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {value:2, label:'b'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceGroupRenderer(element, model).redraw();

    assertOptionGroups(element, []);
    assertOptions(element, [{value:1, label:'a'},
                            {value:2, label:'b'}]);

    model.append([{group: 'group1', value:3, label:'c'},
                  {group: 'group1', value:4, label:'d'}]);

    assertOptionGroups(element, ['group1']);
    assertOptions(element, [{value:1, label:'a'},
                            {value:2, label:'b'},
                            {group: 'group1', value:3, label:'c'},
                            {group: 'group1', value:4, label:'d'}]);
});

test('creme.model.ChoiceGroupRenderer (filled, model, add, same group)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {group: 'group1', value:2, label:'b'},
                                       {group: 'group2', value:3, label:'c'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceGroupRenderer(element, model).redraw();

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group: 'group1', value:2, label:'b'},
                            {group: 'group2', value:3, label:'c'}]);

    model.append([{group: 'group1', value:8, label:'x'},
                  {group: 'group1', value:9, label:'y'}]);

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group: 'group1', value:2, label:'b'},
                            {group: 'group1', value:8, label:'x'},
                            {group: 'group1', value:9, label:'y'},
                            {group: 'group2', value:3, label:'c'}]);

    model.append([{group: 'group2', value:10, label:'z'}]);

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group: 'group1', value:2, label:'b'},
                            {group: 'group1', value:8, label:'x'},
                            {group: 'group1', value:9, label:'y'},
                            {group: 'group2', value:3, label:'c'},
                            {group: 'group2', value:10, label:'z'}]);
});

test('creme.model.ChoiceGroupRenderer (filled, model, insert, same group)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {group:'group1', value:2, label:'b'},
                                       {group:'group2', value:3, label:'c'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceGroupRenderer(element, model).redraw();

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:2, label:'b'},
                            {group:'group2', value:3, label:'c'}]);

    model.insert([{group:'group1', value:8, label:'x'},
                  {group:'group1', value:9, label:'y'}], 1);

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:8, label:'x'},
                            {group:'group1', value:9, label:'y'},
                            {group:'group1', value:2, label:'b'},
                            {group:'group2', value:3, label:'c'}]);
});

test('creme.model.ChoiceGroupRenderer (filled, model, insert, other group)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {group:'group1', value:2, label:'b'},
                                       {group:'group2', value:3, label:'c'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceGroupRenderer(element, model).redraw();

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:2, label:'b'},
                            {group:'group2', value:3, label:'c'}]);

    model.insert([{group:'group1', value:8, label:'x'},
                  {group:'group1', value:9, label:'y'}], 1);

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:8, label:'x'},
                            {group:'group1', value:9, label:'y'},
                            {group:'group1', value:2, label:'b'},
                            {group:'group2', value:3, label:'c'}]);
});

test('creme.model.ChoiceGroupRenderer (filled, model, remove)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {value:2, label:'b'},
                                       {group:'group2', value:3, label:'c'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceGroupRenderer(element, model).redraw();

    assertOptionGroups(element, ['group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {value:2, label:'b'},
                            {group:'group2', value:3, label:'c'}]);

    model.removeAt(1);

    assertOptionGroups(element, ['group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group2', value:3, label:'c'}]);

    model.removeAt(0);

    assertOptionGroups(element, ['group2']);
    assertOptions(element, [{group:'group2', value:3, label:'c'}]);
});

test('creme.model.ChoiceGroupRenderer (filled, model, remove, empty group)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {group:'group1', value:2, label:'b'},
                                       {group:'group2', value:3, label:'c'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceGroupRenderer(element, model).redraw();

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:2, label:'b'},
                            {group:'group2', value:3, label:'c'}]);

    model.removeAt(1);

    assertOptionGroups(element, ['group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group2', value:3, label:'c'}]);

    model.removeAt(1);

    assertOptionGroups(element, []);
    assertOptions(element, [{value:1, label:'a'}]);
});

test('creme.model.ChoiceGroupRenderer (filled, model, remove, group)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {group:'group1', value:2, label:'b'},
                                       {group:'group1', value:2.5, label:'b.5'},
                                       {group:'group2', value:3, label:'c'},
                                       {group:'group2', value:4, label:'d'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceGroupRenderer(element, model).redraw();

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:2, label:'b'},
                            {group:'group1', value:2.5, label:'b.5'},
                            {group:'group2', value:3, label:'c'},
                            {group:'group2', value:4, label:'d'}]);

    model.removeAt(1);

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:2.5, label:'b.5'},
                            {group:'group2', value:3, label:'c'},
                            {group:'group2', value:4, label:'d'}]);

    model.removeAt(2);

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:2.5, label:'b.5'},
                            {group:'group2', value:4, label:'d'}]);

    model.removeAt(2);

    assertOptionGroups(element, ['group1']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:2.5, label:'b.5'}]);
});

test('creme.model.ChoiceGroupRenderer (filled, model, update, same group)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {group:'group1', value:2, label:'b'},
                                       {group:'group1', value:2.5, label:'b.5'},
                                       {group:'group2', value:3, label:'c'},
                                       {group:'group2', value:4, label:'d'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceGroupRenderer(element, model).redraw();

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:2, label:'b'},
                            {group:'group1', value:2.5, label:'b.5'},
                            {group:'group2', value:3, label:'c'},
                            {group:'group2', value:4, label:'d'}]);

    model.set({group:'group1', value:57, label:'b.57'}, 2);

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:2, label:'b'},
                            {group:'group1', value:57, label:'b.57'},
                            {group:'group2', value:3, label:'c'},
                            {group:'group2', value:4, label:'d'}]);
});

test('creme.model.ChoiceGroupRenderer (filled, model, update, other group)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {group:'group1', value:2, label:'b'},
                                       {group:'group1', value:2.5, label:'b.5'},
                                       {group:'group2', value:3, label:'c'},
                                       {group:'group2', value:4, label:'d'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceGroupRenderer(element, model).redraw();

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:2, label:'b'},
                            {group:'group1', value:2.5, label:'b.5'},
                            {group:'group2', value:3, label:'c'},
                            {group:'group2', value:4, label:'d'}]);

    model.set({group:'group2', value:57, label:'b.57'}, 2);

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:2, label:'b'},
                            {group:'group2', value:3, label:'c'},
                            {group:'group2', value:4, label:'d'},
                            {group:'group2', value:57, label:'b.57'}]);

    model.set({group:'group1', value:4, label:'d'}, 3);

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:2, label:'b'},
                            {group:'group1', value:4, label:'d'},
                            {group:'group2', value:3, label:'c'},
                            {group:'group2', value:57, label:'b.57'}]);

    model.set({group:'group2', value:4, label:'d'}, 2);

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:2, label:'b'},
                            {group:'group2', value:4, label:'d'},
                            {group:'group2', value:3, label:'c'},
                            {group:'group2', value:57, label:'b.57'}]);
});

test('creme.model.ChoiceGroupRenderer (filled, model, update, create group)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {group:'group1', value:2, label:'b'},
                                       {group:'group1', value:3, label:'c'},
                                       {group:'group2', value:4, label:'d'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceGroupRenderer(element, model).redraw();

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:2, label:'b'},
                            {group:'group1', value:3, label:'c'},
                            {group:'group2', value:4, label:'d'}]);

    model.set({group:'group3', value:57, label:'c'}, 2);

    assertOptionGroups(element, ['group1', 'group2', 'group3']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:2, label:'b'},
                            {group:'group2', value:4, label:'d'},
                            {group:'group3', value:57, label:'c'}]);
});

test('creme.model.ChoiceGroupRenderer (filled, model, update, remove group)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {group:'group1', value:2, label:'b'},
                                       {group:'group1', value:3, label:'c'},
                                       {group:'group2', value:4, label:'d'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceGroupRenderer(element, model).redraw();

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:2, label:'b'},
                            {group:'group1', value:3, label:'c'},
                            {group:'group2', value:4, label:'d'}]);

    model.set({value:57, label:'c'}, 2);

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:2, label:'b'},
                            {group:'group2', value:4, label:'d'},
                            {value:57, label:'c'}]);
});

test('creme.model.ChoiceGroupRenderer (filled, model, update, other group, empty)', function() {
    var model = new creme.model.Array([{value:1, label:'a'},
                                       {group:'group1', value:2, label:'b'},
                                       {group:'group2', value:3, label:'c'},
                                       {group:'group2', value:4, label:'d'}]);
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.ChoiceGroupRenderer(element, model).redraw();

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:2, label:'b'},
                            {group:'group2', value:3, label:'c'},
                            {group:'group2', value:4, label:'d'}]);

    model.set({group:'group2', value:57, label:'b.57'}, 1);

    assertOptionGroups(element, ['group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group2', value:3, label:'c'},
                            {group:'group2', value:4, label:'d'},
                            {group:'group2', value:57, label:'b.57'}]);

    model.set({group:'group1', value:4, label:'d'}, 2);

    assertOptionGroups(element, ['group1', 'group2']);
    assertOptions(element, [{value:1, label:'a'},
                            {group:'group1', value:4, label:'d'},
                            {group:'group2', value:3, label:'c'},
                            {group:'group2', value:57, label:'b.57'}]);
});

test('creme.model.ChoiceGroupRenderer (parse)', function() {
    deepEqual([{group: undefined, value:'1', label:'a', disabled:false, selected: false, tags: []},
               {group: 'group1', value:'2', label:'b', disabled:false, selected: true, tags: ['tag1']},
               {group: 'group2', value:'3', label:'c', disabled:true, selected: false, tags: ['tag2']},
               {group: 'group2', value:'4', label:'d', disabled:false, selected: false, tags: []},
               {group: undefined, value:'5', label:'e', disabled:false, selected: false, tags: []},
               {group: undefined, value:'6', label:'f', disabled:false, selected: false, tags: []}],
              creme.model.ChoiceGroupRenderer.parse($('<select><options>' +
                                                     '<option value="1">a</option>' +
                                                     '<optgroup label="group1">' +
                                                         '<option value="2" tags="tag1" selected>b</option>' +
                                                     '</optgroup>' +
                                                     '<optgroup label="group2">' +
                                                         '<option value="3" tags="tag2" disabled>c</option>' +
                                                         '<option value="4">d</option>' +
                                                     '</optgroup>' +
                                                     '<option value="5">e</option>' +
                                                     '<option value="6">f</option>' +
                                                 '</options></select>')));
});

test('creme.model.ChoiceRenderer.parse (no converter)', function() {
    var element = $('<select><options>' +
                        '<option value="[1, 2]">a</option>' +
                        '<option value="[3, 4]">b</option>' +
                        '<option value="[5, 6]">c</option>' +
                    '</options></select>');
    var options = new creme.model.ChoiceRenderer.parse(element);

    deepEqual(options, [{value:'[1, 2]', label:'a', disabled:false, selected:true, tags:[]},
                        {value:'[3, 4]', label:'b', disabled:false, selected:false, tags:[]},
                        {value:'[5, 6]', label:'c', disabled:false, selected:false, tags:[]},]);

    element = $('<select><options>' +
                    '<option value="[1, 2]">a</option>' +
                    '<option value="[3, 4]" selected>b</option>' +
                    '<option value="[5, 6]" disabled>c</option>' +
                '</options></select>');
    options = new creme.model.ChoiceRenderer.parse(element);

    deepEqual(options, [{value:'[1, 2]', label:'a', disabled:false, selected:false, tags:[]},
                        {value:'[3, 4]', label:'b', disabled:false, selected:true, tags:[]},
                        {value:'[5, 6]', label:'c', disabled:true, selected:false, tags:[]},]);

});

test('creme.model.ChoiceRenderer.parse (converter)', function() {
    var element = $('<select><options>' +
            '<option value="[1, 2]">a</option>' +
            '<option value="[3, 4]">b</option>' +
            '<option value="[5, 6]">c</option>' +
        '</options></select>');
    var options = new creme.model.ChoiceRenderer.parse(element, new creme.utils.JSON().decode);

    deepEqual(options, [{value:[1, 2], label:'a', disabled:false, selected:true, tags:[]},
                        {value:[3, 4], label:'b', disabled:false, selected:false, tags:[]},
                        {value:[5, 6], label:'c', disabled:false, selected:false, tags:[]},]);

    element = $('<select><options>' +
                    '<option value="[1, 2]">a</option>' +
                    '<option value="[3, 4]" selected>b</option>' +
                    '<option value="[5, 6]" disabled>c</option>' +
                '</options></select>');
    options = new creme.model.ChoiceRenderer.parse(element, new creme.utils.JSON().decode);

    deepEqual(options, [{value:[1, 2], label:'a', disabled:false, selected:false, tags:[]},
                        {value:[3, 4], label:'b', disabled:false, selected:true, tags:[]},
                        {value:[5, 6], label:'c', disabled:true, selected:false, tags:[]},]);
});
